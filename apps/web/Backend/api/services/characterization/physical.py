"""SALIVA 2.2: additive physical representation of the unchanged 2.1 result.

Compatibility is owned by acquisition. No image resampling, reassociation,
redefinition of pixel geometry or texture normalization occurs here.
"""
import copy
import hashlib
import json
import math

from PIL import Image

from api.services.acquisition import physical_compatibility
from .geometry import polygon_perimeter

VERSION = '2.2'
# All measured object features (including texture diagnostics) and dimensional
# summary features. Counts, classifications and statuses are not measurements.
FEATURE_DIMENSIONS = {
    'area_px2': 'AREA', 'mean_nucleus_area_px2': 'AREA',
    'perimeter_px': 'LENGTH', 'distance_to_nucleus_px': 'LENGTH',
    'centroid_px': 'COORDINATE',
    'circularity': 'DIMENSIONLESS', 'eccentricity': 'DIMENSIONLESS',
    'area_fraction_to_nucleus': 'DIMENSIONLESS',
    'intensity_fraction_to_nucleus': 'DIMENSIONLESS',
    'mean_nucleus_circularity': 'DIMENSIONLESS',
    'genotoxicity_index': 'DIMENSIONLESS', 'cytotoxicity_index': 'DIMENSIONLESS',
    'nuclei_association_rate': 'DIMENSIONLESS',
    'micronuclei_membrane_association_rate': 'DIMENSIONLESS',
    'micronuclei_nucleus_association_rate': 'DIMENSIONLESS',
    'mean_gray_intensity': 'INTENSITY', 'std_gray_intensity': 'INTENSITY',
    **{key: 'TEXTURE_PIXEL_DOMAIN' for key in (
        'contrast', 'homogeneity', 'energy', 'correlation', 'entropy',
        'valid_angles', 'valid_pairs',
    )},
}
PHYSICAL_FIELDS = {
    'area_px2': 'area_um2', 'mean_nucleus_area_px2': 'mean_nucleus_area_um2',
    'perimeter_px': 'perimeter_um', 'distance_to_nucleus_px': 'distance_to_nucleus_um',
    'centroid_px': 'centroid_um',
}


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=False, allow_nan=False).encode('utf-8')).hexdigest()


def calibration_context(sample, *, lock=False):
    """Snapshot current compatibility; caller holds the result transaction.

    Lock mutable calibration status during persistence. Historical reads use
    only their saved JSON; this function is used for new results/currentness.
    """
    from api.models import AcquisitionProfile, AcquisitionSeries, Calibration
    if sample is not None and sample.acquisition_series_id and lock:
        series = AcquisitionSeries.objects.get(pk=sample.acquisition_series_id)
        # Same parent-first order as acquisition domain saves; also serializes
        # the permitted one-time association of a calibration to an empty series.
        AcquisitionProfile.objects.select_for_update().get(pk=series.acquisition_profile_id)
        series = AcquisitionSeries.objects.get(pk=series.pk)
        if series.calibration_id:
            Calibration.objects.select_for_update().get(pk=series.calibration_id)
        AcquisitionSeries.objects.select_for_update().get(pk=series.pk)
    compatibility = physical_compatibility(sample) if sample is not None else {
        'compatible_for_physical_units': False, 'status': 'NO_ACQUISITION_SERIES',
        'acquisition_series_id': None, 'source_dimensions': None,
    }
    available = compatibility['compatible_for_physical_units']
    dimensions = compatibility.get('source_dimensions')
    # The authority can return early (e.g. no series). Record original image
    # dimensions for pixel-only results as well; failure follows 2.1 warnings.
    if dimensions is None and sample is not None and sample.imagen:
        try:
            with sample.imagen.storage.open(sample.imagen.name, 'rb') as stream:
                with Image.open(stream) as image:
                    dimensions = {'width': image.width, 'height': image.height}
        except (OSError, ValueError, SyntaxError, Image.DecompressionBombError):
            pass
    context = {
        'physical_units_available': available,
        'physical_status': compatibility['status'],
        'physical_unavailable_reason': None if available else compatibility['status'],
        'physical_measurements_status': None,
        'acquisition_series_id': compatibility.get('acquisition_series_id'),
        'image_dimensions_px': dimensions,
        'calibration': None,
    }
    if available:
        calibration = Calibration.objects.get(pk=compatibility['calibration_id'])
        context['calibration'] = {
            'calibration_id': calibration.pk, 'label': calibration.label,
            'status': compatibility['calibration_status'],
            'acquisition_profile_id': calibration.acquisition_profile_id,
            'acquisition_series_id': sample.acquisition_series_id,
            'scale_x_um_per_px': compatibility['scale_x_um_per_px'],
            'scale_y_um_per_px': compatibility['scale_y_um_per_px'],
            'source_width_px': calibration.source_width_px,
            'source_height_px': calibration.source_height_px,
            'compatibility_status': compatibility['status'],
            'method': calibration.method, 'algorithm_version': calibration.algorithm_version,
            'provenance': copy.deepcopy(calibration.provenance),
        }
        context['physical_measurements_status'] = (
            'PROVISIONAL_CALIBRATION' if compatibility['calibration_status'] == 'PROVISIONAL'
            else 'VALIDATED_CALIBRATION'
        )
    return context


def fingerprint(effective, context, version=VERSION):
    # No timestamps/ORM metadata: the source snapshot includes the full object
    # payload (IDs, order, provenance and geometry), even for mutable auto bases.
    effective_hash = canonical_hash(effective['resultado'])
    return effective_hash, canonical_hash({
        'characterization_version': version, 'effective_segmentation_hash': effective_hash,
        'physical_context': context,
    })


def physical_distance(first, second, sx, sy):
    return math.hypot((first[0] - second[0]) * sx, (first[1] - second[1]) * sy)


def extend_physical_result(pixel_result, effective, context, version=VERSION):
    result = copy.deepcopy(pixel_result)
    result.update(copy.deepcopy(context))
    result.update(version=version, schema_version=VERSION, characterization_version=version)
    effective_hash, key = fingerprint(effective, context, version)
    result['provenance'] = {
        'effective_segmentation_hash': effective_hash, 'fingerprint': key,
        'pixel_algorithm_version': '2.1',
        'GLCM_PHYSICAL_DISTANCE_NORMALIZATION': 'PENDING_SCIENTIFIC_DECISION',
        'IMPORTANT_PENDING_18S_A2': True,
    }
    if not context['physical_units_available']:
        return result
    calibration = context['calibration']
    sx, sy = float(calibration['scale_x_um_per_px']), float(calibration['scale_y_um_per_px'])
    points_by_id = {
        item.get('id'): item['geometry'].get('points')
        for item in (effective['resultado'].get('objects') or [])
        if isinstance(item, dict) and isinstance(item.get('geometry'), dict)
    }

    def convert(metrics, object_id):
        # Validity/nullability decisions are entirely inherited from 2.1.
        for key, dimension in FEATURE_DIMENSIONS.items():
            if key not in metrics or key not in PHYSICAL_FIELDS:
                continue
            value = metrics[key]
            target = PHYSICAL_FIELDS[key]
            metrics[target] = None
            if value is None:
                continue
            if dimension == 'AREA':
                metrics[target] = value * sx * sy
            elif dimension == 'COORDINATE':
                metrics[target] = [value[0] * sx, value[1] * sy]
            elif key == 'perimeter_px':
                points = points_by_id[object_id]
                metrics[target] = polygon_perimeter([[x * sx, y * sy] for x, y in points])
            # Distance is filled below using the *existing* associated nucleus.

    for cell in result['cells']:
        convert(cell['metrics'], cell['membrane_id'])
        nuclei = {item['id']: item for item in cell['nuclei']}
        for item in cell['nuclei'] + cell['micronuclei']:
            convert(item['metrics'], item['id'])
        for item in cell['micronuclei']:
            if item['metrics']['distance_to_nucleus_px'] is not None:
                nucleus = nuclei[item['nucleus_id']]
                item['metrics']['distance_to_nucleus_um'] = physical_distance(
                    item['metrics']['centroid_px'], nucleus['metrics']['centroid_px'], sx, sy)
    for group in ('unassociated', 'ambiguous'):
        for items in result[group].values():
            for item in items:
                convert(item['metrics'], item['id'])
    convert(result['summary'], None)
    return result
