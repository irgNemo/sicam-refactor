def normalize_segmentation_result(raw_result, sample_type="SALIVA"):
    if not isinstance(raw_result, dict):
        raise ValueError("El resultado de segmentacion debe ser un objeto JSON")

    if sample_type != "SALIVA":
        raise ValueError(f"Tipo de muestra no soportado: {sample_type}")

    raw_objects = raw_result.get("objetos", [])
    if raw_objects is None:
        raw_objects = []

    if not isinstance(raw_objects, list):
        raise ValueError("El campo objetos debe ser una lista")

    normalized_objects = []
    counts_by_label = {}

    for index, raw_object in enumerate(raw_objects, start=1):
        normalized_object = _normalize_saliva_object(raw_object, index)
        normalized_objects.append(normalized_object)

        label = normalized_object["label"]
        counts_by_label[label] = counts_by_label.get(label, 0) + 1

    return {
        "version": "1.0",
        "sample_type": sample_type,
        "objects": normalized_objects,
        "summary": {
            "total_objects": len(normalized_objects),
            "counts_by_label": counts_by_label,
        },
    }


def _normalize_saliva_object(raw_object, fallback_id):
    if not isinstance(raw_object, dict):
        return {
            "id": fallback_id,
            "label": "desconocido",
            "geometry": None,
            "source": {
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
        "id": raw_object.get("id", fallback_id),
        "label": label,
        "geometry": geometry,
        "source": {
            "raw_type": raw_object.get("tipo"),
        },
    }
