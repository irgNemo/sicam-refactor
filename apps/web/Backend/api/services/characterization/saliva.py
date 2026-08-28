from .types import (
    CAPABILITY_BINUCLEATE_TRINUCLEATE,
    CAPABILITY_COUNTS,
    CAPABILITY_CYTOTOXICITY_INDEX,
    CAPABILITY_GENOTOXICITY_INDEX,
    STATUS_AVAILABLE,
    STATUS_BLOCKED_SCIENTIFIC_RULE,
    WARNING_SALIVA_SPATIAL_ASSOCIATION_BLOCKED,
)


SALIVA_LABELS = ('membrana', 'nucleo', 'micronucleo')


def characterize_saliva_result(effective_result, source):
    objects = _get_objects(effective_result)
    counts = _count_labels(objects, SALIVA_LABELS)
    membranes = counts['membrana']
    micronuclei = counts['micronucleo']

    return {
        'sample_type': 'SALIVA',
        'source': source,
        'counts': counts,
        'indices': {
            'genotoxicity_index': (
                micronuclei / membranes if membranes else None
            ),
            'cytotoxicity_index': None,
        },
        'characterization_capabilities': {
            CAPABILITY_COUNTS: STATUS_AVAILABLE,
            CAPABILITY_GENOTOXICITY_INDEX: STATUS_AVAILABLE,
            CAPABILITY_BINUCLEATE_TRINUCLEATE: (
                STATUS_BLOCKED_SCIENTIFIC_RULE
            ),
            CAPABILITY_CYTOTOXICITY_INDEX: STATUS_BLOCKED_SCIENTIFIC_RULE,
        },
        'blocked': [
            {
                'code': STATUS_BLOCKED_SCIENTIFIC_RULE,
                'metric': 'binucleate_trinucleate',
                'reason': WARNING_SALIVA_SPATIAL_ASSOCIATION_BLOCKED,
            },
            {
                'code': STATUS_BLOCKED_SCIENTIFIC_RULE,
                'metric': 'cytotoxicity_index',
                'reason': WARNING_SALIVA_SPATIAL_ASSOCIATION_BLOCKED,
            },
        ],
        'warnings': [WARNING_SALIVA_SPATIAL_ASSOCIATION_BLOCKED],
    }


def _get_objects(effective_result):
    if not isinstance(effective_result, dict):
        raise ValueError('El resultado efectivo debe ser un objeto JSON')

    objects = effective_result.get('objects')
    if objects is None:
        return []
    if not isinstance(objects, list):
        raise ValueError('resultado.objects debe ser una lista')
    return objects


def _count_labels(objects, labels):
    counts = {label: 0 for label in labels}
    for item in objects:
        if not isinstance(item, dict):
            continue
        label = item.get('label')
        if label in counts:
            counts[label] += 1
    return counts
