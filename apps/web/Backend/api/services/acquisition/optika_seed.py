"""Explicit project decision from 18S-A.1, not a new engine measurement."""
import hashlib
from decimal import Decimal
from pathlib import Path

from django.core.files import File
from django.core.management.base import CommandError
from django.db import transaction

from api.models import AcquisitionProfile, Calibration, CalibrationReference

PROFILE = dict(name='OPTIKA 40x', microscope_manufacturer='OPTIKA', microscope_model='B-1000FLHBO',
               camera_manufacturer='OPTIKA', camera_model='C-B25+', adapter_model='M-114',
               objective_magnification=Decimal('40'), image_width_px=4928, image_height_px=4928,
               image_mode='RGB', binning_x=None, binning_y=None)
LABEL = 'CAL-OPTIKA-40X-PROVISIONAL-001'
SX, SY = Decimal('0.055233934048'), Decimal('0.055010060892')
PROVENANCE = {
    'seed_key': 'optika-40x-18s-a1-v1',
    'consensus_method': 'unweighted consensus of CIRCLE_150 and CIRCLE_70',
    'grid_status': 'AMBIGUOUS_GRID_PERIODICITY', 'scientific_status': 'PROVISIONAL_ONLY',
    'important_pending_18s_a2': True,
    'circle_150': {'sx': '0.054382897123', 'sy': '0.054261143289'},
    'circle_70': {'sx': '0.056084970972', 'sy': '0.055758978496'},
    'provisional_consensus': {'sx': str(SX), 'sy': str(SY)},
    'auxiliary_isotropic_scale': '0.0551219974698993',
}
REFERENCES = [
    ('Cal_DIV0.01mm_40x.jpg', '262835496b50f13d1dadcb934c2dda765b1f2055848b0b02d6ffffa446ac1d33', 'GRADUATED_GRID', 10, 'AMBIGUOUS_GRID_PERIODICITY', None, None),
    ('Cal_0.15mm_40x (1).jpg', 'd9daee7d4bc1790c004110d2febda32c7874a837c7298a85c1c739a3fb96c58b', 'CIRCLE', 150, 'MEASURED', '0.054382897123', '0.054261143289'),
    ('Cal_0.07mm_40x (1).jpg', 'a3665c451b17ec42eb4713c5894ce66ca357305c39c67c6dd36e767f00ef3998', 'CIRCLE', 70, 'MEASURED', '0.056084970972', '0.055758978496'),
]


def file_hash(path):
    hasher = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


def reference_values(spec):
    filename, sha, pattern, dimension, status, sx, sy = spec
    return dict(source_filename=filename, source_sha256=sha, pattern_type=pattern,
                source_width_px=4928, source_height_px=4928, known_dimension_um=Decimal(dimension),
                measurement_status=status, measured_scale_x_um_per_px=Decimal(sx) if sx else None,
                measured_scale_y_um_per_px=Decimal(sy) if sy else None,
                diagnostics={'review_version': '18S-A.1', 'scientific_status': 'PROVISIONAL_ONLY',
                             'used_for_consensus': status == 'MEASURED'})


def seed_optika(source_dir=None, *, institution):
    if not institution.pk or not institution.active:
        raise CommandError("ACTIVE_INSTITUTION_REQUIRED")
    paths = {}
    if source_dir is not None:
        for spec in REFERENCES:
            path = Path(source_dir) / spec[0]
            if path.exists():
                if file_hash(path) != spec[1]:
                    raise CommandError('SOURCE_HASH_MISMATCH: no se creó ni modificó la calibración.')
                paths[spec[0]] = path
    saved_files = []
    try:
        with transaction.atomic():
            physical = {key: value for key, value in PROFILE.items() if key != 'name'}
            matches = list(AcquisitionProfile.objects.select_for_update().filter(institution=institution, **physical))
            if len(matches) > 1:
                raise CommandError('AMBIGUOUS_EXISTING_PROFILE')
            if not matches and AcquisitionProfile.objects.filter(institution=institution, name=PROFILE['name']).exists():
                raise CommandError('EXISTING_PROFILE_CONFLICT')
            profile = matches[0] if matches else AcquisitionProfile.objects.create(institution=institution, **PROFILE)
            values = dict(acquisition_profile=profile, label=LABEL, status='PROVISIONAL',
                          scale_x_um_per_px=SX, scale_y_um_per_px=SY, source_width_px=4928, source_height_px=4928,
                          method='AUTOMATIC_MULTI_REFERENCE', algorithm_version='calibration-provisional-v1/18S-A.1',
                          provenance=PROVENANCE)
            existing = list(Calibration.objects.filter(acquisition_profile__institution=institution, label=LABEL))
            same_provenance = list(Calibration.objects.filter(acquisition_profile=profile, provenance=PROVENANCE))
            candidates = {c.pk:c for c in existing + same_provenance}
            if candidates:
                if len(candidates) != 1:
                    raise CommandError('AMBIGUOUS_EXISTING_CALIBRATION')
                calibration = next(iter(candidates.values()))
                if any(getattr(calibration, key) != value for key, value in values.items()):
                    raise CommandError('EXISTING_CALIBRATION_CONFLICT')
                references = list(calibration.references.all())
                if len(references) != 3:
                    raise CommandError('EXISTING_REFERENCE_CONFLICT')
                for spec in REFERENCES:
                    matched = [r for r in references if r.source_sha256 == spec[1]]
                    if len(matched) != 1 or any(getattr(matched[0], k) != v for k,v in reference_values(spec).items()):
                        raise CommandError('EXISTING_REFERENCE_CONFLICT')
                    if matched[0].source_image:
                        with matched[0].source_image.open('rb') as stream:
                            if hashlib.sha256(stream.read()).hexdigest() != spec[1]:
                                raise CommandError('STORED_EVIDENCE_HASH_MISMATCH')
                    elif spec[0] in paths:
                        raise CommandError('EXISTING_METADATA_ONLY: no se reemplaza evidencia inmutable.')
                return {'status': 'ALREADY_PRESENT', 'profile_id': profile.pk, 'calibration_id': calibration.pk, 'references': 3}
            calibration = Calibration.objects.create(**values)
            for spec in REFERENCES:
                reference = CalibrationReference(calibration=calibration, **reference_values(spec))
                if spec[0] in paths:
                    with paths[spec[0]].open('rb') as stream:
                        reference.source_image = File(stream, name=spec[0])
                        reference.save()
                    saved_files.append((reference.source_image.storage, reference.source_image.name))
                else:
                    reference.save()
            return {'status': 'CREATED', 'profile_id': profile.pk, 'calibration_id': calibration.pk, 'references': 3}
    except Exception:
        for storage, name in saved_files:
            storage.delete(name)
        raise
