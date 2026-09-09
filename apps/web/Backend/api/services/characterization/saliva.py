import copy
import math

from .geometry import (
    POINT_INSIDE,
    POINT_ON_BOUNDARY,
    classify_point_in_polygon,
    is_self_intersecting_polygon,
    polygon_area,
    polygon_centroid,
    polygon_circularity,
    polygon_perimeter,
)
from .intensity import (
    load_grayscale_image,
    mean_gray_intensity,
    points_fit_image,
)


SALIVA_LABELS = ('membrana', 'nucleo', 'micronucleo')
SCHEMA_VERSION = '2.0'

ASSOCIATED = 'ASSOCIATED'
UNASSOCIATED = 'UNASSOCIATED'
AMBIGUOUS = 'AMBIGUOUS'

ANUCLEATED = 'ANUCLEATED'
MONONUCLEATED = 'MONONUCLEATED'
BINUCLEATED = 'BINUCLEATED'
TRINUCLEATED = 'TRINUCLEATED'
MULTINUCLEATED = 'MULTINUCLEATED'


def characterize_saliva_result(effective_result, source, image_path=None):
    effective_copy = copy.deepcopy(effective_result)
    objects = _get_objects(effective_copy)
    warnings = []
    grayscale_image, image_warning = _load_optional_image(image_path)
    if image_warning:
        warnings.append(image_warning)

    measured = [
        _measure_object(item, grayscale_image, warnings)
        for item in objects
        if isinstance(item, dict)
    ]

    membranes = [item for item in measured if item['label'] == 'membrana']
    nuclei = [item for item in measured if item['label'] == 'nucleo']
    micronuclei = [
        item for item in measured if item['label'] == 'micronucleo'
    ]

    valid_membranes = _spatially_valid(membranes)
    associated_nuclei, unassociated_nuclei, ambiguous_nuclei = (
        _associate_to_membranes(
            nuclei,
            valid_membranes,
            'UNASSOCIATED_NUCLEUS',
            warnings,
        )
    )
    associated_micronuclei, unassociated_micronuclei, ambiguous_micronuclei = (
        _associate_to_membranes(
            micronuclei,
            valid_membranes,
            'UNASSOCIATED_MICRONUCLEUS',
            warnings,
        )
    )

    cells = _build_cells(
        membranes,
        associated_nuclei,
        associated_micronuclei,
    )

    summary = _build_summary(
        membranes=membranes,
        nuclei=nuclei,
        micronuclei=micronuclei,
        associated_nuclei=associated_nuclei,
        associated_micronuclei=associated_micronuclei,
        unassociated_nuclei=unassociated_nuclei,
        unassociated_micronuclei=unassociated_micronuclei,
        ambiguous_nuclei=ambiguous_nuclei,
        ambiguous_micronuclei=ambiguous_micronuclei,
        cells=cells,
    )

    return {
        'version': SCHEMA_VERSION,
        'schema_version': SCHEMA_VERSION,
        'sample_type': 'SALIVA',
        'source': source,
        'summary': summary,
        'cells': cells,
        'unassociated': {
            'nuclei': [_public_unassociated(item) for item in unassociated_nuclei],
            'micronuclei': [
                _public_unassociated(item)
                for item in unassociated_micronuclei
            ],
        },
        'ambiguous': {
            'nuclei': [_public_ambiguous(item) for item in ambiguous_nuclei],
            'micronuclei': [
                _public_ambiguous(item)
                for item in ambiguous_micronuclei
            ],
        },
        'warnings': warnings,
    }


def _load_optional_image(image_path):
    if not image_path:
        return None, _warning(
            'IMAGE_UNAVAILABLE',
            None,
            'La imagen original no estuvo disponible para calcular intensidad.',
        )

    try:
        return load_grayscale_image(image_path), None
    except Exception:
        return None, _warning(
            'IMAGE_UNAVAILABLE',
            None,
            'No se pudo abrir la imagen original para calcular intensidad.',
        )


def _measure_object(item, grayscale_image, warnings):
    object_id = item.get('id')
    label = item.get('label')
    source = item.get('source') if isinstance(item.get('source'), dict) else {}
    points = _extract_points(item)
    public = {
        'id': object_id,
        'label': label,
        'source_raw_id': source.get('raw_id'),
        'source_raw_type': source.get('raw_type'),
        'metrics': _empty_metrics(),
        'association_status': None,
        'candidate_membrane_ids': [],
        '_points': points,
        '_valid_for_spatial': False,
    }

    if label not in SALIVA_LABELS:
        return public

    if points is None:
        warnings.append(_warning(
            'INVALID_POINTS',
            object_id,
            'El objeto no contiene un poligono valido.',
        ))
        return public

    try:
        perimeter = polygon_perimeter(points)
    except ValueError as exc:
        warnings.append(_warning('INVALID_POINTS', object_id, str(exc)))
        return public

    public['metrics']['perimeter_px'] = perimeter

    try:
        self_intersecting = is_self_intersecting_polygon(points)
    except ValueError as exc:
        warnings.append(_warning('INVALID_POINTS', object_id, str(exc)))
        return public

    if self_intersecting:
        warnings.append(_warning(
            'SELF_INTERSECTING_POLYGON',
            object_id,
            'El poligono tiene autointersecciones.',
        ))
        return public

    area = polygon_area(points)
    public['metrics']['area_px2'] = area
    if area == 0:
        warnings.append(_warning(
            'DEGENERATE_POLYGON',
            object_id,
            'El poligono tiene area cero.',
        ))
        return public

    centroid = polygon_centroid(points)
    public['metrics']['centroid_px'] = centroid

    circularity, warning_code = polygon_circularity(area, perimeter)
    public['metrics']['circularity'] = circularity
    if warning_code:
        warnings.append(_warning(
            warning_code,
            object_id,
            'La circularidad calculada excede la tolerancia numerica.',
        ))

    if grayscale_image is not None:
        if points_fit_image(points, grayscale_image):
            public['metrics']['mean_gray_intensity'] = (
                mean_gray_intensity(points, grayscale_image)
            )
        else:
            warnings.append(_warning(
                'COORDINATE_SPACE_MISMATCH',
                object_id,
                'Los puntos del objeto no coinciden con la imagen original.',
            ))

    public['_valid_for_spatial'] = centroid is not None and area > 0
    return public


def _extract_points(item):
    geometry = item.get('geometry')
    if not isinstance(geometry, dict):
        return None
    if geometry.get('type') != 'polygon':
        return None
    points = geometry.get('points')
    if not isinstance(points, list):
        return None
    return copy.deepcopy(points)


def _empty_metrics():
    return {
        'area_px2': None,
        'perimeter_px': None,
        'centroid_px': None,
        'circularity': None,
        'mean_gray_intensity': None,
    }


def _spatially_valid(items):
    return [item for item in items if item['_valid_for_spatial']]


def _associate_to_membranes(items, membranes, unassociated_code, warnings):
    associated = []
    unassociated = []
    ambiguous = []

    for item in items:
        if not item['_valid_for_spatial']:
            item['association_status'] = UNASSOCIATED
            unassociated.append(item)
            warnings.append(_warning(
                unassociated_code,
                item['id'],
                'El objeto no pudo asociarse a una membrana.',
            ))
            continue

        containing = []
        for membrane in membranes:
            location = classify_point_in_polygon(
                item['metrics']['centroid_px'],
                membrane['_points'],
            )
            if location in (POINT_INSIDE, POINT_ON_BOUNDARY):
                containing.append(membrane)
            if location == POINT_ON_BOUNDARY:
                warnings.append(_warning(
                    'POINT_ON_BOUNDARY',
                    item['id'],
                    'El centroide del objeto cae sobre el borde de una membrana.',
                    membrane_id=membrane['id'],
                ))

        if len(containing) == 1:
            item['association_status'] = ASSOCIATED
            item['membrane_id'] = containing[0]['id']
            associated.append(item)
        elif len(containing) == 0:
            item['association_status'] = UNASSOCIATED
            unassociated.append(item)
            warnings.append(_warning(
                unassociated_code,
                item['id'],
                'El objeto no pertenece a ninguna membrana.',
            ))
        else:
            item['association_status'] = AMBIGUOUS
            item['candidate_membrane_ids'] = [
                membrane['id'] for membrane in containing
            ]
            ambiguous.append(item)
            warnings.append(_warning(
                'AMBIGUOUS_MEMBRANE_ASSOCIATION',
                item['id'],
                'El objeto cae en mas de una membrana.',
                candidate_membrane_ids=item['candidate_membrane_ids'],
            ))

    return associated, unassociated, ambiguous


def _build_cells(membranes, nuclei, micronuclei):
    nuclei_by_membrane = _group_by_membrane(nuclei)
    micronuclei_by_membrane = _group_by_membrane(micronuclei)
    cells = []

    for membrane in sorted(membranes, key=lambda item: item['id'] or 0):
        cell_nuclei = sorted(
            nuclei_by_membrane.get(membrane['id'], []),
            key=lambda item: item['id'] or 0,
        )
        cell_micronuclei = sorted(
            micronuclei_by_membrane.get(membrane['id'], []),
            key=lambda item: item['id'] or 0,
        )

        public_nuclei = [_public_nucleus(item) for item in cell_nuclei]
        public_micronuclei = []
        for ordinal, micronucleus in enumerate(cell_micronuclei, start=1):
            associated_nucleus = _nearest_nucleus(micronucleus, cell_nuclei)
            public_micronuclei.append(
                _public_micronucleus(
                    micronucleus,
                    associated_nucleus,
                    membrane['id'],
                    ordinal,
                )
            )

        cells.append({
            'membrane_id': membrane['id'],
            'source_raw_id': membrane['source_raw_id'],
            'display_label': f"Celula {membrane['id']}",
            'metrics': membrane['metrics'],
            'association_status': ASSOCIATED if membrane['_valid_for_spatial'] else UNASSOCIATED,
            'nuclear_class': _nuclear_class(len(cell_nuclei)),
            'nuclei_count': len(cell_nuclei),
            'micronuclei_count': len(cell_micronuclei),
            'nuclei': public_nuclei,
            'micronuclei': public_micronuclei,
        })

    return cells


def _group_by_membrane(items):
    grouped = {}
    for item in items:
        grouped.setdefault(item.get('membrane_id'), []).append(item)
    return grouped


def _nearest_nucleus(micronucleus, nuclei):
    if not nuclei:
        return None

    centroid = micronucleus['metrics']['centroid_px']
    distances = [
        (_distance(centroid, nucleus['metrics']['centroid_px']), nucleus)
        for nucleus in nuclei
    ]
    distances.sort(key=lambda item: (item[0], item[1]['id'] or 0))
    return distances[0][1]


def _distance(first, second):
    if first is None or second is None:
        return None
    return math.dist(first, second)


def _nuclear_class(nuclei_count):
    if nuclei_count == 0:
        return ANUCLEATED
    if nuclei_count == 1:
        return MONONUCLEATED
    if nuclei_count == 2:
        return BINUCLEATED
    if nuclei_count == 3:
        return TRINUCLEATED
    return MULTINUCLEATED


def _build_summary(
    *,
    membranes,
    nuclei,
    micronuclei,
    associated_nuclei,
    associated_micronuclei,
    unassociated_nuclei,
    unassociated_micronuclei,
    ambiguous_nuclei,
    ambiguous_micronuclei,
    cells,
):
    total_membranes = len(membranes)
    total_nuclei = len(nuclei)
    total_micronuclei = len(micronuclei)
    binucleated = sum(
        1 for cell in cells if cell['nuclear_class'] == BINUCLEATED
    )
    trinucleated = sum(
        1 for cell in cells if cell['nuclear_class'] == TRINUCLEATED
    )

    cytotoxicity = (
        (binucleated + trinucleated) / total_membranes
        if total_membranes
        else None
    )

    return {
        'total_membranes': total_membranes,
        'total_nuclei': total_nuclei,
        'total_micronuclei': total_micronuclei,
        'anucleated_cells': sum(
            1 for cell in cells if cell['nuclear_class'] == ANUCLEATED
        ),
        'mononucleated_cells': sum(
            1 for cell in cells if cell['nuclear_class'] == MONONUCLEATED
        ),
        'binucleated_cells': binucleated,
        'trinucleated_cells': trinucleated,
        'multinucleated_cells': sum(
            1 for cell in cells if cell['nuclear_class'] == MULTINUCLEATED
        ),
        'cells_with_nucleus': sum(
            1 for cell in cells if cell['nuclei_count'] > 0
        ),
        'cells_with_2plus_micronuclei': sum(
            1 for cell in cells if cell['micronuclei_count'] >= 2
        ),
        'genotoxicity_index': (
            total_micronuclei / total_membranes
            if total_membranes
            else None
        ),
        'genotoxicity_status': (
            'VALID' if total_membranes else 'NOT_COMPUTABLE'
        ),
        'cytotoxicity_index': cytotoxicity,
        'cytotoxicity_status': _cytotoxicity_status(
            total_membranes,
            unassociated_nuclei,
            ambiguous_nuclei,
        ),
        'mean_nucleus_area_px2': _mean_metric(nuclei, 'area_px2'),
        'mean_nucleus_circularity': _mean_metric(nuclei, 'circularity'),
        'unassociated_nuclei': len(unassociated_nuclei),
        'unassociated_micronuclei': len(unassociated_micronuclei),
        'ambiguous_nuclei': len(ambiguous_nuclei),
        'ambiguous_micronuclei': len(ambiguous_micronuclei),
        'association_quality': _association_quality(
            associated_nuclei,
            associated_micronuclei,
            total_nuclei,
            total_micronuclei,
        ),
    }


def _cytotoxicity_status(total_membranes, unassociated_nuclei, ambiguous_nuclei):
    if total_membranes == 0:
        return 'NOT_COMPUTABLE'
    if unassociated_nuclei or ambiguous_nuclei:
        return 'PARTIAL'
    return 'VALID'


def _mean_metric(items, metric_name):
    values = [
        item['metrics'].get(metric_name)
        for item in items
        if item['metrics'].get(metric_name) is not None
    ]
    if not values:
        return None
    return sum(values) / len(values)


def _association_quality(
    associated_nuclei,
    associated_micronuclei,
    total_nuclei,
    total_micronuclei,
):
    micronuclei_with_nucleus = [
        item for item in associated_micronuclei
        if item.get('nucleus_id') is not None
    ]
    return {
        'nuclei_associated': len(associated_nuclei),
        'nuclei_total': total_nuclei,
        'nuclei_association_rate': _rate(len(associated_nuclei), total_nuclei),
        'micronuclei_associated_to_membrane': len(associated_micronuclei),
        'micronuclei_associated_to_nucleus': len(micronuclei_with_nucleus),
        'micronuclei_total': total_micronuclei,
        'micronuclei_membrane_association_rate': _rate(
            len(associated_micronuclei),
            total_micronuclei,
        ),
        'micronuclei_nucleus_association_rate': _rate(
            len(micronuclei_with_nucleus),
            total_micronuclei,
        ),
    }


def _rate(value, total):
    if total == 0:
        return None
    return value / total


def _public_nucleus(item):
    return {
        'id': item['id'],
        'source_raw_id': item['source_raw_id'],
        'metrics': item['metrics'],
        'association_status': item['association_status'],
    }


def _public_micronucleus(item, nucleus, membrane_id, ordinal):
    item['nucleus_id'] = nucleus['id'] if nucleus else None
    distance = _distance(
        item['metrics']['centroid_px'],
        nucleus['metrics']['centroid_px'] if nucleus else None,
    )

    area_fraction = None
    intensity_fraction = None
    if nucleus and nucleus['metrics']['area_px2']:
        area_fraction = (
            item['metrics']['area_px2'] /
            nucleus['metrics']['area_px2']
        )
    if (
        nucleus and
        item['metrics']['mean_gray_intensity'] is not None and
        nucleus['metrics']['mean_gray_intensity']
    ):
        intensity_fraction = (
            item['metrics']['mean_gray_intensity'] /
            nucleus['metrics']['mean_gray_intensity']
        )

    metrics = {
        **item['metrics'],
        'distance_to_nucleus_px': distance,
        'area_fraction_to_nucleus': area_fraction,
        'intensity_fraction_to_nucleus': intensity_fraction,
    }

    return {
        'id': item['id'],
        'source_raw_id': item['source_raw_id'],
        'nucleus_id': item['nucleus_id'],
        'display_label': f'{membrane_id}.{ordinal}',
        'metrics': metrics,
        'association_status': item['association_status'],
    }


def _public_unassociated(item):
    payload = {
        'id': item['id'],
        'source_raw_id': item['source_raw_id'],
        'metrics': item['metrics'],
        'association_status': item['association_status'],
    }
    if item['label'] == 'micronucleo':
        payload['nucleus_id'] = None
        payload['metrics'] = {
            **payload['metrics'],
            'distance_to_nucleus_px': None,
            'area_fraction_to_nucleus': None,
            'intensity_fraction_to_nucleus': None,
        }
    return payload


def _public_ambiguous(item):
    payload = _public_unassociated(item)
    payload['candidate_membrane_ids'] = item.get('candidate_membrane_ids', [])
    return payload


def _warning(code, object_id, message, **extra):
    warning = {
        'code': code,
        'object_id': object_id,
        'message': message,
    }
    warning.update(extra)
    return warning


def _get_objects(effective_result):
    if not isinstance(effective_result, dict):
        raise ValueError('El resultado efectivo debe ser un objeto JSON')

    objects = effective_result.get('objects')
    if objects is None:
        return []
    if not isinstance(objects, list):
        raise ValueError('resultado.objects debe ser una lista')
    return objects
