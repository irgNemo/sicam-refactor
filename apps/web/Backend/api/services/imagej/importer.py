"""Preflight and transactional import of manual SALIVA annotations."""
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
import re
import uuid

from django.core.exceptions import ValidationError
from django.core.files import File
from django.db import IntegrityError, OperationalError, transaction

from api.models import AnalisisPred, Caso, ImageJImportRecord, MuestraSaliva, Paciente, ResultadoSegmentacion
from .contracts import (CONTRACT_VERSION, CONVERTER_VERSION, ImportProblem,
                        import_keys, patient_key, sha256_file, sha256_path)
from .geometry import convert_pair
from .spreadsheet import read_patients

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png'}
MASK_EXTENSIONS = {'.tif', '.tiff'}


@dataclass
class Pair:
    patient_key: str
    image: Path | None
    mask: Path | None
    status: str


def discover(source, layout):
    root = Path(source)
    if not root.is_dir() or root.is_symlink():
        raise ImportProblem('INVALID_SOURCE')
    folder_root = root / 'pacientes' if layout == 'official' else root
    if not folder_root.is_dir() or folder_root.is_symlink():
        raise ImportProblem('INVALID_LAYOUT')
    directories = sorted((p for p in folder_root.iterdir() if p.is_dir()), key=lambda p: p.name)
    keys = [patient_key(p.name) for p in directories]
    if len(set(keys)) != len(keys):
        raise ImportProblem('PATIENT_FOLDER_AMBIGUOUS')
    if any(p.is_symlink() for p in folder_root.iterdir()):
        raise ImportProblem('UNSAFE_SOURCE_PATH')
    pairs = []
    for directory in directories:
        leaf = directory
        if layout == 'legacy-repeated':
            leaf = directory / directory.name
            if not leaf.is_dir() or leaf.is_symlink() or len(list(directory.iterdir())) != 1:
                raise ImportProblem('INVALID_LAYOUT')
        if any(p.is_dir() or p.is_symlink() for p in leaf.iterdir()):
            raise ImportProblem('INVALID_LAYOUT')
        by_stem = defaultdict(lambda: {'image': [], 'mask': []})
        for path in sorted(leaf.iterdir()):
            suffix = path.suffix.lower()
            if suffix in IMAGE_EXTENSIONS | MASK_EXTENSIONS:
                by_stem[path.stem]['image' if suffix in IMAGE_EXTENSIONS else 'mask'].append(path)
        folded = Counter(stem.casefold() for stem in by_stem)
        for stem, files in sorted(by_stem.items()):
            images, masks = files['image'], files['mask']
            if len(images) > 1 or len(masks) > 1 or folded[stem.casefold()] > 1:
                status = 'AMBIGUOUS_PAIR'
            elif not images:
                status = 'MASK_WITHOUT_IMAGE'
            elif not masks:
                status = 'IMAGE_WITHOUT_MASK'
            else:
                status = 'EXACT_MATCH'
            pairs.append(Pair(directory.name, images[0] if images else None, masks[0] if masks else None, status))
    return directories, pairs


def resolve_domain(row, namespace, *, lock=False):
    patients = Paciente.objects
    if lock:
        patients = patients.select_for_update()
    patient = patients.filter(external_id_namespace=namespace, external_patient_id=row.external_id).first()
    if patient:
        if patient_key(patient.initials) != patient_key(row.initials) or patient.fecha_nacimiento != row.birth_date:
            raise ImportProblem('PATIENT_DATA_CONFLICT')
    else:
        patient = Paciente(identity_mode=Paciente.PSEUDONYMIZED, external_id_namespace=namespace,
                           external_patient_id=row.external_id, initials=row.initials,
                           fecha_nacimiento=row.birth_date,
                           identificacion='ext:' + uuid.uuid5(uuid.NAMESPACE_URL, repr((namespace, row.external_id))).hex)
        try:
            patient.full_clean()
        except ValidationError:
            raise ImportProblem('PATIENT_DATA_CONFLICT') from None
    case = analysis = None
    if patient.pk:
        cases = Caso.objects.filter(paciente=patient)
        if lock:
            cases = cases.select_for_update()
        case = cases.filter(case_number=1).first()
        if case is None:
            candidates = list(cases.filter(titulo='Caso 1'))
            if len(candidates) > 1 or any(c.case_number is not None for c in candidates):
                raise ImportProblem('CASE_AMBIGUOUS')
            case = candidates[0] if candidates else None
        if case:
            analyses = list(AnalisisPred.objects.filter(id_caso_fk=case))
            if len(analyses) > 1 or any(a.id_paciente_fk_id != patient.pk or a.estado == 2 for a in analyses):
                raise ImportProblem('ANALYSIS_AMBIGUOUS')
            analysis = analyses[0] if analyses else None
    return patient, case, analysis


def check_existing(keys, row, namespace, dataset, image_hash, mask_hash, basename):
    # Mapping is durable by external ID, not initials/folder. Renamed initials do
    # not create new patients; changed data is a conflict in resolve_domain.
    record = ImageJImportRecord.objects.filter(logical_key=keys['logical_key']).first()
    if record and record.image_sha256 != image_hash:
        raise ImportProblem('IMAGE_CHANGED_CONFLICT')
    record = record or ImageJImportRecord.objects.filter(sample_key=keys['sample_key']).first()
    if record:
        if patient_key(record.paciente.initials) != patient_key(row.initials) or record.paciente.fecha_nacimiento != row.birth_date:
            raise ImportProblem('PATIENT_DATA_CONFLICT')
        if record.mask_sha256 != mask_hash:
            raise ImportProblem('MASK_CHANGED_CONFLICT')
        if record.converter_version != CONVERTER_VERSION or record.contract_version != CONTRACT_VERSION:
            raise ImportProblem('CONVERTER_VERSION_CONFLICT')
        if record.logical_basename != basename:
            raise ImportProblem('SAME_IMAGE_NEW_NAME')
        if record.annotation_key != keys['annotation_key'] or record.status != 'READY':
            raise ImportProblem('IMPORT_INTEGRITY_CONFLICT')
        if (record.paciente.external_id_namespace != namespace or record.paciente.external_patient_id != row.external_id
                or record.caso.paciente_id != record.paciente_id or record.caso.case_number != 1
                or record.muestra.analisis.id_caso_fk_id != record.caso_id
                or record.muestra.analisis.id_paciente_fk_id != record.paciente_id
                or record.resultado.muestra_id != record.muestra_id
                or record.resultado.base_origin != 'MANUAL' or record.resultado.estado != 'COMPLETADO'):
            raise ImportProblem('IMPORT_INTEGRITY_CONFLICT')
        try:
            for field, expected in ((record.muestra.imagen, image_hash), (record.source_mask_file, mask_hash)):
                with field.storage.open(field.name, 'rb') as file:
                    if sha256_file(file) != expected:
                        raise ImportProblem('IMPORT_INTEGRITY_CONFLICT')
        except OSError:
            raise ImportProblem('IMPORT_INTEGRITY_CONFLICT') from None
        return record
    # A folder rebound to a different hospital ID is not a new subject silently.
    if ImageJImportRecord.objects.filter(dataset_key=dataset, patient_namespace=namespace, patient_key=patient_key(row.key)).exclude(external_patient_id=row.external_id).exists():
        raise ImportProblem('PATIENT_DATA_CONFLICT')
    if ImageJImportRecord.objects.filter(image_sha256=image_hash).exists():
        raise ImportProblem('DUPLICATE_IMAGE_CONFLICT')
    return None


def save_copy(field, source, expected_hash, created):
    # UUID-owned name, routed through the ImageField's upload_to/storage. Track
    # it before saving as FileSystemStorage may leave a partial file on failure.
    requested = field.field.generate_filename(field.instance, uuid.uuid4().hex + source.suffix.lower())
    if field.storage.exists(requested):
        raise ImportProblem('STORAGE_NAME_COLLISION')
    created.append((field.storage, requested))
    with source.open('rb') as file:
        actual = field.storage.save(requested, File(file), max_length=field.field.max_length)
    field.name = actual
    field._committed = True
    if actual != requested:
        # A storage backend may rename. Only the returned file belongs to us.
        created[-1] = (field.storage, actual)
    with field.storage.open(field.name, 'rb') as file:
        if sha256_file(file) != expected_hash:
            raise ImportProblem('STORAGE_HASH_MISMATCH')


def persist_pair(pair, row, namespace, dataset, image_hash, mask_hash, keys, raw, normalized, metadata):
    created = []
    try:
        with transaction.atomic():
            existing = check_existing(keys, row, namespace, dataset, image_hash, mask_hash, pair.image.stem)
            if existing:
                return 'ALREADY_IMPORTED'
            patient, case, analysis = resolve_domain(row, namespace, lock=True)
            # Detect source edits between preflight/conversion and persistence.
            if sha256_path(pair.image) != image_hash or sha256_path(pair.mask) != mask_hash:
                raise ImportProblem('SOURCE_CHANGED_DURING_IMPORT')
            if not patient.pk:
                patient.save()
            if case is None:
                case = Caso.objects.create(paciente=patient, titulo='Caso 1', case_number=1)
            elif case.case_number is None:
                case.case_number = 1
                case.save(update_fields=['case_number'])
            if analysis is None:
                analysis = AnalisisPred.objects.create(id_paciente_fk=patient, id_caso_fk=case)
            sample = MuestraSaliva(analisis=analysis)
            save_copy(sample.imagen, pair.image, image_hash, created)
            sample.save()
            record_id = uuid.uuid4()
            raw['import_metadata'] = {'record_id': str(record_id), 'contract_version': CONTRACT_VERSION, 'converter_version': CONVERTER_VERSION}
            for obj in normalized['objects']:
                obj['source']['import_record_id'] = str(record_id)
            result = ResultadoSegmentacion.objects.create(muestra=sample, tipo_muestra='SALIVA', base_origin='MANUAL', segmentation_strategy=None,
                                                         estado='COMPLETADO', respuesta_json=raw, resultado_normalizado=normalized)
            record = ImageJImportRecord(id=record_id, dataset_key=dataset, patient_namespace=namespace,
                                        external_patient_id=row.external_id, patient_key=patient_key(row.key), case_number=1,
                                        logical_basename=pair.image.stem, image_sha256=image_hash, mask_sha256=mask_hash,
                                        converter_version=CONVERTER_VERSION, contract_version=CONTRACT_VERSION,
                                        paciente=patient, caso=case, muestra=sample, resultado=result, metadata=metadata, **keys)
            save_copy(record.source_mask_file, pair.mask, mask_hash, created)
            record.full_clean()
            record.save()
        return 'IMPORTED'
    except Exception:
        cleanup_failed = False
        for storage, name in reversed(created):
            try:
                storage.delete(name)
            except OSError:
                cleanup_failed = True
        if cleanup_failed:
            raise ImportProblem('STORAGE_CLEANUP_REQUIRED') from None
        raise


def run_import(*, source, patients_file, dataset_key, patient_namespace, case_number=1,
               dry_run=False, patient=None, limit=None, strict=False,
               layout='official', patients_format='standard'):
    if case_number != 1:
        raise ImportProblem('ONLY_CASE_1_SUPPORTED')
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,63}', patient_namespace):
        raise ImportProblem('INVALID_PATIENT_NAMESPACE')
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,99}', dataset_key):
        raise ImportProblem('INVALID_DATASET_KEY')
    if limit is not None and limit < 1:
        raise ImportProblem('INVALID_LIMIT')
    records = read_patients(Path(patients_file), patients_format)
    folders, pairs = discover(source, layout)
    selected = {patient_key(k) for k in (patient or [])}
    if selected - {patient_key(p.name) for p in folders}:
        raise ImportProblem('PATIENT_NOT_FOUND')
    selected_folders = [p for p in folders if not selected or patient_key(p.name) in selected]
    pairs = [p for p in pairs if not selected or patient_key(p.patient_key) in selected]
    if limit:
        pairs = pairs[:limit]
    aliases = {patient_key(p.name): f'PATIENT_{i:03}' for i, p in enumerate(folders, 1)}
    summary = {'dry_run': dry_run, 'patients_discovered': len(selected_folders),
               'patients_matched': sum(len(records.get(patient_key(p.name), [])) == 1 for p in selected_folders),
               'pairs': len(pairs), 'patients_would_create': 0, 'patients_would_reuse': 0,
               'cases_would_create': 0, 'cases_would_reuse': 0, 'ready': 0, 'already_imported': 0,
               'conflicts': 0, 'topology_failures': 0, 'mask_errors': 0, 'dimension_errors': 0,
               'counts': {'membrana': 0, 'nucleo': 0, 'micronucleo': 0}, 'rows': []}
    domain_seen = set()
    batch_hashes = set()
    for index, pair in enumerate(pairs, 1):
        report = {'patient': aliases[patient_key(pair.patient_key)], 'pair': f'PAIR_{index:03}'}
        try:
            candidates = records.get(patient_key(pair.patient_key), [])
            if not candidates:
                raise ImportProblem('PATIENT_NOT_FOUND')
            if len(candidates) != 1:
                raise ImportProblem('PATIENT_MATCH_AMBIGUOUS')
            row = candidates[0]
            if pair.status != 'EXACT_MATCH':
                raise ImportProblem(pair.status)
            image_hash, mask_hash = sha256_path(pair.image), sha256_path(pair.mask)
            keys = import_keys(dataset_key, patient_namespace, row.external_id, 1, pair.image.stem, image_hash, mask_hash)
            existing = check_existing(keys, row, patient_namespace, dataset_key, image_hash, mask_hash, pair.image.stem)
            if existing:
                patient_obj, case = existing.paciente, existing.caso
            else:
                patient_obj, case, _analysis = resolve_domain(row, patient_namespace)
            if image_hash in batch_hashes:
                raise ImportProblem('DUPLICATE_IMAGE_CONFLICT')
            batch_hashes.add(image_hash)
            raw, normalized, metadata = convert_pair(pair.image, pair.mask)
            # Files must remain stable while decoded, also in dry-run.
            if sha256_path(pair.image) != image_hash or sha256_path(pair.mask) != mask_hash:
                raise ImportProblem('SOURCE_CHANGED_DURING_IMPORT')
            if existing:
                report['status'] = 'ALREADY_IMPORTED'
                summary['already_imported'] += 1
            else:
                report['patient_action'] = 'WOULD_REUSE_PATIENT' if patient_obj.pk else 'WOULD_CREATE_PATIENT'
                report['case_action'] = 'WOULD_REUSE_CASE' if case else 'WOULD_CREATE_CASE'
                if row.external_id not in domain_seen:
                    summary['patients_would_reuse' if patient_obj.pk else 'patients_would_create'] += 1
                    summary['cases_would_reuse' if case else 'cases_would_create'] += 1
                    domain_seen.add(row.external_id)
                report['status'] = 'WOULD_IMPORT' if dry_run else persist_pair(pair, row, patient_namespace, dataset_key, image_hash, mask_hash, keys, raw, normalized, metadata)
                summary['ready'] += 1
            report['counts'] = normalized['summary']['counts_by_label']
            for label, count in report['counts'].items():
                summary['counts'][label] += count
        except ImportProblem as exc:
            report.update(status=exc.code, detail=exc.detail)
        except (IntegrityError, OperationalError):
            report.update(status='DB_ERROR', detail='Retry preflight; no automatic overwrite.')
        except OSError:
            report.update(status='STORAGE_ERROR', detail='')
        except ValidationError:
            report.update(status='IMPORT_VALIDATION_ERROR', detail='')
        summary['rows'].append(report)
        code = report['status']
        summary['conflicts'] += int('CONFLICT' in code or 'AMBIGUOUS' in code)
        summary['topology_failures'] += int(code == 'UNSUPPORTED_POLYGON_TOPOLOGY')
        summary['mask_errors'] += int(code == 'UNEXPECTED_MASK_VALUE')
        summary['dimension_errors'] += int(code == 'DIMENSION_MISMATCH')
        if strict and code not in ('WOULD_IMPORT', 'IMPORTED', 'ALREADY_IMPORTED'):
            break
    summary['errors'] = sum(r['status'] not in ('WOULD_IMPORT', 'IMPORTED', 'ALREADY_IMPORTED') for r in summary['rows'])
    return summary
