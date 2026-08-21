class SampleType:
    SALIVA = 'SALIVA'
    BLOOD = 'SANGRE'


SAMPLE_TYPE_ALIASES = {
    'SALIVA': SampleType.SALIVA,
    'SANGRE': SampleType.BLOOD,
    'BLOOD': SampleType.BLOOD,
}


SEGMENTATION_TYPE_CONFIG = {
    SampleType.SALIVA: {
        'sample_type': SampleType.SALIVA,
        'allowed_labels': ('membrana', 'nucleo', 'micronucleo'),
        'supports_segmentation': True,
        'supports_expert_review': True,
        'normalizer': 'default_polygon_objects',
    },
    SampleType.BLOOD: {
        'sample_type': SampleType.BLOOD,
        'allowed_labels': ('membrana', 'micronucleo'),
        'supports_segmentation': False,
        'supports_expert_review': True,
        'normalizer': 'default_polygon_objects',
    },
}


def normalize_sample_type(sample_type):
    if sample_type is None:
        return SampleType.SALIVA

    return SAMPLE_TYPE_ALIASES.get(str(sample_type).upper(), str(sample_type).upper())


def get_segmentation_type_config(sample_type):
    normalized_type = normalize_sample_type(sample_type)
    return SEGMENTATION_TYPE_CONFIG.get(normalized_type)


def get_allowed_revision_labels(sample_type):
    config = get_segmentation_type_config(sample_type)
    if not config:
        return ()
    return config['allowed_labels']
