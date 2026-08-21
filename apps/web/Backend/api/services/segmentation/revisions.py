import copy
import math

from rest_framework import serializers

from .types import SampleType, get_allowed_revision_labels

ALLOWED_REVISION_LABELS = get_allowed_revision_labels(SampleType.SALIVA)
REVISION_SNAPSHOT_VERSION = '1.0'


def build_revision_snapshot_from_normalized(resultado_segmentacion):
    sample_type = resultado_segmentacion.tipo_muestra
    normalized = resultado_segmentacion.resultado_normalizado
    if not isinstance(normalized, dict):
        raise serializers.ValidationError(
            'El resultado normalizado debe ser un objeto JSON'
        )

    raw_objects = normalized.get('objects')
    if raw_objects is None:
        raw_objects = []
    if not isinstance(raw_objects, list):
        raise serializers.ValidationError(
            'resultado_normalizado.objects debe ser una lista'
        )

    revision_object_ids = assign_revision_object_ids(raw_objects)
    snapshot = {
        'version': REVISION_SNAPSHOT_VERSION,
        'base_result_id': resultado_segmentacion.id_resultado_segmentacion,
        'objects': [
            _build_automatic_revision_object(raw_object, revision_object_id)
            for raw_object, revision_object_id
            in zip(raw_objects, revision_object_ids)
        ],
    }
    validate_revision_snapshot(snapshot, sample_type=sample_type)
    return snapshot


def assign_revision_object_ids(raw_objects):
    reserved_original_ids = {
        raw_object.get('id')
        for raw_object in raw_objects
        if (
            isinstance(raw_object, dict)
            and _is_positive_int(raw_object.get('id'))
        )
    }
    used_ids = set()
    next_candidate = 1
    revision_ids = []

    for raw_object in raw_objects:
        original_id = (
            raw_object.get('id')
            if isinstance(raw_object, dict)
            else None
        )

        if _is_positive_int(original_id) and original_id not in used_ids:
            revision_id = original_id
        else:
            while (
                next_candidate in used_ids
                or next_candidate in reserved_original_ids
            ):
                next_candidate += 1
            revision_id = next_candidate

        revision_ids.append(revision_id)
        used_ids.add(revision_id)

    return revision_ids


def clone_revision_snapshot(revision):
    snapshot = copy.deepcopy(revision.resultado_editado)
    validate_revision_snapshot(
        snapshot,
        sample_type=revision.resultado_segmentacion.tipo_muestra
    )
    return snapshot


def validate_revision_snapshot(snapshot, sample_type=SampleType.SALIVA):
    if not isinstance(snapshot, dict):
        raise serializers.ValidationError(
            'resultado_editado debe ser un objeto JSON'
        )

    objects = snapshot.get('objects')
    if not isinstance(objects, list):
        raise serializers.ValidationError(
            'resultado_editado.objects debe ser una lista'
        )

    seen_ids = set()
    allowed_labels = get_allowed_revision_labels(sample_type)
    for index, revision_object in enumerate(objects):
        _validate_revision_object(
            revision_object,
            index,
            seen_ids,
            allowed_labels,
        )

    return True


def calculate_revision_summary(snapshot, sample_type=SampleType.SALIVA):
    validate_revision_snapshot(snapshot, sample_type=sample_type)

    counts_by_label = {
        label: 0
        for label in get_allowed_revision_labels(sample_type)
    }

    for revision_object in snapshot['objects']:
        counts_by_label[revision_object['label']] += 1

    return {
        'counts_by_label': counts_by_label,
        'total_objects': len(snapshot['objects']),
    }


def _build_automatic_revision_object(raw_object, revision_object_id):
    if not isinstance(raw_object, dict):
        raise serializers.ValidationError(
            'Los objetos normalizados deben ser objetos JSON'
        )

    return {
        'id': revision_object_id,
        'label': raw_object.get('label'),
        'geometry': copy.deepcopy(raw_object.get('geometry')),
        'provenance': {
            'origin': 'automatic',
            'base_object_id': raw_object.get('id'),
        },
    }


def _validate_revision_object(revision_object, index, seen_ids, allowed_labels):
    if not isinstance(revision_object, dict):
        raise serializers.ValidationError(
            f'objects[{index}] debe ser un objeto JSON'
        )

    object_id = revision_object.get('id')
    if not _is_positive_int(object_id):
        raise serializers.ValidationError(
            f'objects[{index}].id debe ser un entero positivo'
        )
    if object_id in seen_ids:
        raise serializers.ValidationError(
            f'objects[{index}].id esta duplicado'
        )
    seen_ids.add(object_id)

    label = revision_object.get('label')
    if label not in allowed_labels:
        raise serializers.ValidationError(
            f'objects[{index}].label no es valido'
        )

    _validate_geometry(revision_object.get('geometry'), index)
    _validate_provenance(revision_object.get('provenance'), index)


def _validate_geometry(geometry, object_index):
    if not isinstance(geometry, dict):
        raise serializers.ValidationError(
            f'objects[{object_index}].geometry debe ser un objeto JSON'
        )

    if geometry.get('type') != 'polygon':
        raise serializers.ValidationError(
            f'objects[{object_index}].geometry.type debe ser polygon'
        )

    points = geometry.get('points')
    if not isinstance(points, list):
        raise serializers.ValidationError(
            f'objects[{object_index}].geometry.points debe ser una lista'
        )

    if len(points) < 3:
        raise serializers.ValidationError(
            f'objects[{object_index}].geometry.points debe tener al menos 3 puntos'
        )

    for point_index, point in enumerate(points):
        if not isinstance(point, list) or len(point) != 2:
            raise serializers.ValidationError(
                f'objects[{object_index}].geometry.points[{point_index}] debe tener dos coordenadas'
            )

        if not all(_is_finite_number(coordinate) for coordinate in point):
            raise serializers.ValidationError(
                f'objects[{object_index}].geometry.points[{point_index}] debe contener numeros finitos'
            )


def _validate_provenance(provenance, object_index):
    if not isinstance(provenance, dict):
        raise serializers.ValidationError(
            f'objects[{object_index}].provenance debe ser un objeto JSON'
        )

    origin = provenance.get('origin')
    base_object_id = provenance.get('base_object_id')

    if origin == 'automatic':
        if not _is_positive_int(base_object_id):
            raise serializers.ValidationError(
                f'objects[{object_index}].provenance.base_object_id debe ser entero positivo para objetos automaticos'
            )
        return

    if origin == 'manual':
        if base_object_id is not None:
            raise serializers.ValidationError(
                f'objects[{object_index}].provenance.base_object_id debe ser null para objetos manuales'
            )
        return

    raise serializers.ValidationError(
        f'objects[{object_index}].provenance.origin no es valido'
    )


def _is_positive_int(value):
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )
