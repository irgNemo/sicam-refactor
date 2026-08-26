import math

from .types import get_segmentation_type_config, normalize_sample_type


def normalize_segmentation_result(raw_result, sample_type="SALIVA"):
    if not isinstance(raw_result, dict):
        raise ValueError("El resultado de segmentacion debe ser un objeto JSON")

    sample_type = normalize_sample_type(sample_type)
    config = get_segmentation_type_config(sample_type)
    if not config or config.get("normalizer") != "default_polygon_objects":
        raise ValueError(f"Tipo de muestra no soportado: {sample_type}")

    raw_objects = raw_result.get("objetos", [])
    if raw_objects is None:
        raw_objects = []

    if not isinstance(raw_objects, list):
        raise ValueError("El campo objetos debe ser una lista")

    normalized_objects = []
    counts_by_label = {}

    for index, raw_object in enumerate(raw_objects, start=1):
        normalized_object = _normalize_polygon_object(raw_object, index)
        normalized_objects.append(normalized_object)

        label = normalized_object["label"]
        counts_by_label[label] = counts_by_label.get(label, 0) + 1

    return {
        "version": "1.1",
        "sample_type": sample_type,
        "objects": normalized_objects,
        "summary": {
            "total_objects": len(normalized_objects),
            "counts_by_label": counts_by_label,
        },
    }


def _normalize_polygon_object(raw_object, fallback_id):
    if not isinstance(raw_object, dict):
        return {
            "id": fallback_id,
            "label": "desconocido",
            "geometry": None,
            "source": {
                "raw_id": None,
                "raw_type": None,
                "raw_object": raw_object,
            },
        }

    label = raw_object.get("tipo") or raw_object.get("label") or "desconocido"
    points = raw_object.get("puntos")

    geometry = None
    if points is not None:
        geometry = {
            "type": "polygon",
            "points": points,
        }

    return {
        "id": fallback_id,
        "label": label,
        "geometry": geometry,
        "source": {
            "raw_id": raw_object.get("id"),
            "raw_type": raw_object.get("tipo"),
        },
    }


def validate_normalized_segmentation_result(normalized_result, sample_type):
    sample_type = normalize_sample_type(sample_type)
    config = get_segmentation_type_config(sample_type)
    if not config:
        raise ValueError(f"Tipo de muestra no soportado: {sample_type}")

    if not isinstance(normalized_result, dict):
        raise ValueError("El resultado normalizado debe ser un objeto JSON")

    objects = normalized_result.get("objects")
    if not isinstance(objects, list):
        raise ValueError("resultado_normalizado.objects debe ser una lista")

    allowed_labels = set(config["allowed_labels"])
    for index, item in enumerate(objects):
        _validate_normalized_object(item, index, allowed_labels)

    return True


def _validate_normalized_object(item, index, allowed_labels):
    if not isinstance(item, dict):
        raise ValueError(f"objects[{index}] debe ser un objeto JSON")

    label = item.get("label")
    if label not in allowed_labels:
        raise ValueError(f"objects[{index}].label no es valido")

    geometry = item.get("geometry")
    if not isinstance(geometry, dict):
        raise ValueError(f"objects[{index}].geometry debe ser un objeto JSON")

    if geometry.get("type") != "polygon":
        raise ValueError(f"objects[{index}].geometry.type debe ser polygon")

    points = geometry.get("points")
    if not isinstance(points, list):
        raise ValueError(f"objects[{index}].geometry.points debe ser una lista")

    if len(points) < 3:
        raise ValueError(
            f"objects[{index}].geometry.points debe tener al menos 3 puntos"
        )

    for point_index, point in enumerate(points):
        if not isinstance(point, list) or len(point) != 2:
            raise ValueError(
                f"objects[{index}].geometry.points[{point_index}] debe tener dos coordenadas"
            )

        if not all(_is_finite_number(coordinate) for coordinate in point):
            raise ValueError(
                f"objects[{index}].geometry.points[{point_index}] debe contener numeros finitos"
            )


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )
