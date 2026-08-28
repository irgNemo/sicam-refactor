import copy

from django.db import transaction

from api.services.segmentation.effective import (
    FUENTE_AUTOMATICO,
    FUENTE_VALIDADA,
    resolve_effective_segmentation,
)
from api.services.segmentation.types import SampleType

from .saliva import characterize_saliva_result
from .types import (
    CAPABILITY_COUNTS,
    CAPABILITY_CYTOTOXICITY_INDEX,
    CAPABILITY_GENOTOXICITY_INDEX,
    STATUS_AVAILABLE,
    STATUS_BLOCKED_SCIENTIFIC_RULE,
    STATUS_NOT_DEFINED,
    WARNING_BLOOD_CHARACTERIZATION_NOT_DEFINED,
    CHARACTERIZATION_ALGORITHM_VERSION,
)


def characterize_resultado_segmentacion(resultado_or_id):
    caracterizacion, _created = get_or_create_resultado_caracterizacion(
        resultado_or_id
    )
    return caracterizacion


def get_or_create_resultado_caracterizacion(resultado_or_id):
    from api.models import ResultadoCaracterizacion, ResultadoSegmentacion

    if isinstance(resultado_or_id, ResultadoSegmentacion):
        resultado_id = resultado_or_id.pk
    else:
        resultado_id = resultado_or_id

    with transaction.atomic():
        resultado = ResultadoSegmentacion.objects.select_for_update().get(
            pk=resultado_id
        )
        effective = resolve_effective_segmentation(resultado)
        revision_id = _get_effective_revision_id(effective)

        existing = ResultadoCaracterizacion.objects.filter(
            resultado_segmentacion=resultado,
            revision_segmentacion_id=revision_id,
            source_type=effective['fuente'],
            algorithm_version=CHARACTERIZATION_ALGORITHM_VERSION,
        ).order_by('created_at', 'id_resultado_caracterizacion').first()

        if existing:
            return existing, False

        resultado_json = characterize_effective_segmentation(
            effective,
            sample_type=resultado.tipo_muestra,
        )

        caracterizacion = ResultadoCaracterizacion(
            resultado_segmentacion=resultado,
            revision_segmentacion_id=revision_id,
            source_type=effective['fuente'],
            sample_type=resultado.tipo_muestra,
            algorithm_version=CHARACTERIZATION_ALGORITHM_VERSION,
            resultado_json=resultado_json,
        )
        caracterizacion.full_clean()
        caracterizacion.save()
        return caracterizacion, True


def characterize_effective_segmentation(effective, sample_type=SampleType.SALIVA):
    if not isinstance(effective, dict):
        raise ValueError('El resultado efectivo debe ser un objeto JSON')

    effective_result = copy.deepcopy(effective.get('resultado'))
    source = _build_source(effective)

    if sample_type == SampleType.SALIVA:
        characterization = characterize_saliva_result(effective_result, source)
    elif sample_type == SampleType.BLOOD:
        characterization = _characterize_blood_counts_only(
            effective_result,
            source,
        )
    else:
        raise ValueError(f'Tipo de muestra no soportado: {sample_type}')

    return {
        'version': CHARACTERIZATION_ALGORITHM_VERSION,
        **characterization,
    }


def is_characterization_current(characterization):
    effective = resolve_effective_segmentation(
        characterization.resultado_segmentacion
    )

    if (
        characterization.algorithm_version
        != CHARACTERIZATION_ALGORITHM_VERSION
    ):
        return False

    if characterization.source_type != effective['fuente']:
        return False

    if effective['fuente'] == FUENTE_AUTOMATICO:
        return characterization.revision_segmentacion_id is None

    if effective['fuente'] == FUENTE_VALIDADA:
        return (
            characterization.revision_segmentacion_id
            == effective['revision']['id_revision_segmentacion']
        )

    return False


def _build_source(effective):
    revision = effective.get('revision')
    return {
        'type': effective.get('fuente'),
        'resultado_segmentacion_id': effective.get('resultado_segmentacion_id'),
        'revision_segmentacion_id': (
            revision.get('id_revision_segmentacion')
            if isinstance(revision, dict)
            else None
        ),
        'numero_revision': (
            revision.get('numero_revision')
            if isinstance(revision, dict)
            else None
        ),
    }


def _get_effective_revision_id(effective):
    if effective['fuente'] != FUENTE_VALIDADA:
        return None

    revision = effective.get('revision')
    if not isinstance(revision, dict):
        raise ValueError('La fuente VALIDADA requiere metadata de revision')

    return revision.get('id_revision_segmentacion')


def _characterize_blood_counts_only(effective_result, source):
    objects = _get_objects(effective_result)
    counts = _count_labels(objects, ('membrana', 'micronucleo'))
    return {
        'sample_type': SampleType.BLOOD,
        'source': source,
        'counts': counts,
        'indices': {},
        'characterization_capabilities': {
            CAPABILITY_COUNTS: STATUS_AVAILABLE,
            CAPABILITY_GENOTOXICITY_INDEX: STATUS_NOT_DEFINED,
            CAPABILITY_CYTOTOXICITY_INDEX: STATUS_NOT_DEFINED,
        },
        'blocked': [
            {
                'code': STATUS_NOT_DEFINED,
                'metric': 'blood_characterization',
                'reason': WARNING_BLOOD_CHARACTERIZATION_NOT_DEFINED,
            }
        ],
        'warnings': [WARNING_BLOOD_CHARACTERIZATION_NOT_DEFINED],
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
