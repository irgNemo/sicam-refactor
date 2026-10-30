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
from .geometry import polygon_perimeter, polygon_convex_hull_area, minimum_polygon_distance

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


# ---------------------------------------------------------------------------
# Sprint 18U-C1 — Characterization 2.3 extension
# ---------------------------------------------------------------------------

VERSION_23 = '2.3'

# Dimensional classification for new 2.3 metrics (informational only).
FEATURE_DIMENSIONS_23 = {
    'elongation_index': 'DIMENSIONLESS',
    'convex_solidity': 'DIMENSIONLESS',
    'mn_nucleus_perimeter_ratio_px': 'DIMENSIONLESS',
    'mn_nucleus_perimeter_ratio_physical': 'DIMENSIONLESS',
    'mn_nucleus_min_distance_px': 'LENGTH',
}

# 2.3 pixel→physical mapping (for min distance only; ratios are dimensionless).
PHYSICAL_FIELDS_23 = {
    'mn_nucleus_min_distance_px': 'mn_nucleus_min_distance_um',
}

_NUMERICAL_EPSILON_23 = 1e-12


def extend_23_metrics(physical_result, effective, context, version=VERSION_23):
    """Add Characterization 2.3 metrics to an already-complete 2.2 result.

    This function is the **sole producer** of all six 2.3 metrics.  It starts
    from a deep copy of the 2.2 result and never mutates its input.  It does
    not recompute raster moments or modify any existing 2.2 field.

    New metrics
    -----------
    Per nucleus and MN:
        elongation_index          1 − sqrt(clamp(1 − ecc², 0, 1))
        convex_solidity           area_px2 / convex_hull_area_px2

    Per MN (relation to associated nucleus):
        mn_nucleus_perimeter_ratio_px        perimeter_mn_px / perimeter_nucleus_px
        mn_nucleus_perimeter_ratio_physical  perimeter_mn_um / perimeter_nucleus_um
        mn_nucleus_min_distance_px           minimum closed-set polygon distance (px)
        mn_nucleus_min_distance_um           same after per-coordinate transform (µm)
    """
    result = copy.deepcopy(physical_result)

    # Build polygon lookup from effective segmentation (same pattern as 2.2).
    points_by_id = {
        item.get('id'): item['geometry'].get('points')
        for item in (effective['resultado'].get('objects') or [])
        if isinstance(item, dict) and isinstance(item.get('geometry'), dict)
    }

    available = context is not None and context.get('physical_units_available', False)
    if available:
        cal = context['calibration']
        sx = float(cal['scale_x_um_per_px'])
        sy = float(cal['scale_y_um_per_px'])
    else:
        sx = sy = None

    # ------------------------------------------------------------------
    # Per-object metrics: elongation_index and convex_solidity
    # ------------------------------------------------------------------
    def add_object_metrics(metrics, object_id):
        # A. Elongation Index — derived from stored eccentricity (no re-rasterisation)
        ecc = metrics.get('eccentricity')
        if ecc is None:
            metrics['elongation_index'] = None
        else:
            ratio = max(0.0, min(1.0, 1.0 - float(ecc) * float(ecc)))
            metrics['elongation_index'] = 1.0 - math.sqrt(ratio)

        # B. Convex Solidity — uses stored area_px2 + convex hull of polygon
        area = metrics.get('area_px2')
        if area is None or area <= 0:
            metrics['convex_solidity'] = None
            return
        points = points_by_id.get(object_id)
        if not points or len(points) < 3:
            metrics['convex_solidity'] = None
            return
        hull_area = polygon_convex_hull_area(points)
        if hull_area is None or hull_area <= _NUMERICAL_EPSILON_23:
            metrics['convex_solidity'] = None
            return
        metrics['convex_solidity'] = area / hull_area

    # ------------------------------------------------------------------
    # Per-MN relation metrics
    # ------------------------------------------------------------------
    def _nucleus_metrics_lookup(cell_list):
        """Return {nucleus_id: metrics_dict} for all cells in the result."""
        lkp = {}
        for cell in cell_list:
            for nuc in cell.get('nuclei', []):
                lkp[nuc['id']] = nuc['metrics']
        return lkp

    nucleus_metrics = _nucleus_metrics_lookup(result.get('cells', []))

    def add_relation_metrics(mn, mn_points):
        nucleus_id = mn.get('nucleus_id')
        mn_metrics = mn['metrics']

        if nucleus_id is None:
            mn_metrics['mn_nucleus_perimeter_ratio_px'] = None
            mn_metrics['mn_nucleus_perimeter_ratio_physical'] = None
            mn_metrics['mn_nucleus_min_distance_px'] = None
            mn_metrics['mn_nucleus_min_distance_um'] = None
            return

        nuc_m = nucleus_metrics.get(nucleus_id)
        nuc_points = points_by_id.get(nucleus_id)

        # C. Pixel perimeter ratio
        p_mn = mn_metrics.get('perimeter_px')
        p_nuc = nuc_m.get('perimeter_px') if nuc_m else None
        if p_mn is not None and p_nuc and p_nuc > 0:
            mn_metrics['mn_nucleus_perimeter_ratio_px'] = p_mn / p_nuc
        else:
            mn_metrics['mn_nucleus_perimeter_ratio_px'] = None

        # D. Physical perimeter ratio
        if available:
            p_mn_um = mn_metrics.get('perimeter_um')
            p_nuc_um = nuc_m.get('perimeter_um') if nuc_m else None
            if p_mn_um is not None and p_nuc_um and p_nuc_um > 0:
                mn_metrics['mn_nucleus_perimeter_ratio_physical'] = p_mn_um / p_nuc_um
            else:
                mn_metrics['mn_nucleus_perimeter_ratio_physical'] = None
        else:
            mn_metrics['mn_nucleus_perimeter_ratio_physical'] = None

        # E. Pixel minimum separation
        if mn_points and nuc_points and len(mn_points) >= 3 and len(nuc_points) >= 3:
            try:
                mn_metrics['mn_nucleus_min_distance_px'] = minimum_polygon_distance(
                    mn_points, nuc_points
                )
            except (ValueError, TypeError):
                mn_metrics['mn_nucleus_min_distance_px'] = None
        else:
            mn_metrics['mn_nucleus_min_distance_px'] = None

        # F. Physical minimum separation (per-coordinate transform — not average scale)
        if available and mn_points and nuc_points and len(mn_points) >= 3 and len(nuc_points) >= 3:
            try:
                mn_phys = [[x * sx, y * sy] for x, y in mn_points]
                nuc_phys = [[x * sx, y * sy] for x, y in nuc_points]
                mn_metrics['mn_nucleus_min_distance_um'] = minimum_polygon_distance(
                    mn_phys, nuc_phys
                )
            except (ValueError, TypeError):
                mn_metrics['mn_nucleus_min_distance_um'] = None
        else:
            mn_metrics['mn_nucleus_min_distance_um'] = None

    # ------------------------------------------------------------------
    # Walk result structure — mirrors extend_physical_result() traversal
    # ------------------------------------------------------------------
    for cell in result.get('cells', []):
        for nuc in cell.get('nuclei', []):
            add_object_metrics(nuc['metrics'], nuc['id'])
        for mn in cell.get('micronuclei', []):
            add_object_metrics(mn['metrics'], mn['id'])
            add_relation_metrics(mn, points_by_id.get(mn['id']))

    for group in ('unassociated', 'ambiguous'):
        for items in result.get(group, {}).values():
            for item in items:
                add_object_metrics(item['metrics'], item['id'])
                # Unassociated/ambiguous MN may still have nucleus_id if
                # the nucleus is in the group too; relation metrics are set
                # to null only when nucleus_id is None (handled inside).
                if item.get('label') == 'micronucleo':
                    add_relation_metrics(item, points_by_id.get(item['id']))

    # ------------------------------------------------------------------
    # Reset version fields to 2.3
    # ------------------------------------------------------------------
    effective_hash, key = fingerprint(effective, context if context is not None else {}, version)
    result['version'] = version
    result['schema_version'] = version
    result['characterization_version'] = version
    result['provenance'] = {
        **result.get('provenance', {}),
        'fingerprint': key,
        'effective_segmentation_hash': effective_hash,
        'pixel_algorithm_version': '2.1',
        'GLCM_PHYSICAL_DISTANCE_NORMALIZATION': 'PENDING_SCIENTIFIC_DECISION',
        'IMPORTANT_PENDING_18S_A2': True,
    }
    return result
