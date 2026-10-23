"""Application orchestration around the unchanged calibration engine."""
import hashlib
import json
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.files import File
from django.db import transaction
from rest_framework.exceptions import ValidationError

from api.models import AcquisitionProfile, Calibration, CalibrationReference
from api.services.calibration.engine import ENGINE_VERSION, measure_image, consensus, percent_difference


def decimal_scale(value):
    return Decimal(str(value)).quantize(Decimal('0.000000000000001'))


def profile_snapshot(profile):
    return {field: getattr(profile, field) for field in profile.physical_fields}


def automatic_calibration(profile, references, *, label='', expected_token=None, persist=False, actor=None):
    snapshot = profile_snapshot(profile)
    if not profile.objective_magnification:
        raise ValidationError({'acquisition_profile': 'Indique el objetivo del perfil antes de medir.'})
    saved_files = []
    try:
        with TemporaryDirectory(prefix='sic am-calibration-'.replace(' ', '')) as directory:
            results, paths = [], []
            for index, entry in enumerate(references):
                upload = entry['file']
                path = Path(directory) / f'reference_{index}{Path(upload.name).suffix.lower()}'
                with path.open('wb') as stream:
                    for chunk in upload.chunks():
                        stream.write(chunk)
                paths.append(path)
                pattern = entry['pattern_type'].lower()
                metadata = {
                    'pattern_type': pattern, 'objective_magnification': float(profile.objective_magnification),
                    'expected_dimensions_px': [profile.image_width_px, profile.image_height_px],
                    'acquisition': json.loads(json.dumps(snapshot, default=str)),
                    'known_diameter_um' if pattern == 'circle' else 'division_um': float(entry['known_dimension_um']),
                }
                if entry.get('grid_reference'):
                    metadata['grid_reference'] = entry['grid_reference']
                result = measure_image(path, metadata)
                result['source_file'] = Path(upload.name).name
                results.append(result)
            measured = [r for r in results if r['measurement_status'] == 'MEASURED']
            combined = consensus(results)
            warnings = [warning for r in results for warning in r.get('warnings', [])]
            sx = sy = None
            method = None
            if len(measured) == 1:
                sx, sy = (measured[0][f'scale_{axis}_um_per_px'] for axis in ('x', 'y'))
                method = 'SINGLE_REFERENCE'
                warnings.append('SINGLE_MEASURED_REFERENCE')
            elif len(measured) > 1 and combined['status'] == 'PROVISIONAL_ONLY':
                sx, sy = (combined[f'provisional_median_scale_{axis}'] for axis in ('x', 'y'))
                method = 'ENGINE_MEDIAN_CONSENSUS'
            for result in results:
                if result['measurement_status'] != 'MEASURED':
                    warnings.append(f"{result['source_file']}: {result['measurement_status']}")
            # Structural source errors cannot be persisted as a partially valid batch.
            invalid_source = any(r['measurement_status'] in ('SOURCE_DIMENSION_MISMATCH', 'INVALID_SOURCE_IMAGE', 'REAL_CALIBRATION_FILES_MISSING') for r in results)
            mode_mismatch = bool(profile.image_mode and any(r.get('source_mode') != profile.image_mode for r in results))
            if invalid_source or mode_mismatch:
                sx = sy = None
                warnings.append('SOURCE_PROFILE_MISMATCH')
            review = {
                'usable': sx is not None and sy is not None,
                'status': 'PROVISIONAL' if sx is not None else 'NO_USABLE_SCALE',
                'scale_x_um_per_px': str(decimal_scale(sx)) if sx is not None else None,
                'scale_y_um_per_px': str(decimal_scale(sy)) if sy is not None else None,
                'anisotropy_percent': percent_difference(sx, sy) if sx is not None else None,
                'consensus_method': method, 'engine_consensus': combined,
                'results': results, 'warnings': warnings, 'important_pending_18s_a2': True,
                'engine_version': ENGINE_VERSION,
            }
            token = hashlib.sha256(json.dumps({'profile': snapshot, 'review': review}, sort_keys=True, default=str, allow_nan=False).encode()).hexdigest()
            review['source_token'] = token
            if not persist:
                return {'review': review}
            if not review['usable']:
                raise ValidationError({'detail': 'No existe una escala técnicamente utilizable.', 'review': review})
            if expected_token != token:
                raise ValidationError({'detail': 'Las referencias o el perfil cambiaron. Ejecute nuevamente la medición.'})
            with transaction.atomic():
                locked = AcquisitionProfile.objects.select_for_update().get(pk=profile.pk)
                if profile_snapshot(locked) != snapshot:
                    raise ValidationError({'detail': 'El perfil cambió durante la medición.'})
                calibration = Calibration.objects.create(created_by=actor, updated_by=actor,
                    acquisition_profile=locked, label=label, status=Calibration.PROVISIONAL,
                    scale_x_um_per_px=decimal_scale(sx), scale_y_um_per_px=decimal_scale(sy),
                    source_width_px=locked.image_width_px, source_height_px=locked.image_height_px,
                    method='AUTOMATIC_MULTI_REFERENCE' if len(references) > 1 else 'AUTOMATIC_SINGLE_REFERENCE',
                    algorithm_version=ENGINE_VERSION, provenance=review,
                )
                for entry, result, path in zip(references, results, paths):
                    reference = CalibrationReference(
                        created_by=actor, updated_by=actor,
                        calibration=calibration, pattern_type=entry['pattern_type'],
                        source_filename=Path(entry['file'].name).name, source_sha256=result['sha256'],
                        source_width_px=result['source_width_px'], source_height_px=result['source_height_px'],
                        known_dimension_um=entry['known_dimension_um'], measurement_status=result['measurement_status'],
                        measured_scale_x_um_per_px=decimal_scale(result['scale_x_um_per_px']) if result['measurement_status'] == 'MEASURED' else None,
                        measured_scale_y_um_per_px=decimal_scale(result['scale_y_um_per_px']) if result['measurement_status'] == 'MEASURED' else None,
                        diagnostics=result,
                    )
                    with path.open('rb') as stream:
                        reference.source_image = File(stream, name=path.name)
                        reference.save()
                    saved_files.append((reference.source_image.storage, reference.source_image.name))
                return {'calibration': calibration, 'review': review}
    except Exception:
        for storage, name in saved_files:
            storage.delete(name)
        raise
