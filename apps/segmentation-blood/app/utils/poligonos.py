import numpy as np
import cv2


def obtener_poligonos_desde_mascara(mascara: np.ndarray, tipo_objeto: str, epsilon: float = 1.5) -> list:
    """
    Convierte una máscara de segmentación en una lista de objetos geométricos.

    Args:
        mascara:      Array NumPy donde cada objeto tiene un ID distinto (fondo = 0).
        tipo_objeto:  Etiqueta del tipo. Ej: "celula", "micronucleo".
        epsilon:      Nivel de simplificación del polígono (approxPolyDP).

    Returns:
        [
            { "id": int, "tipo": str, "puntos": [[x, y], ...] },
            ...
        ]
    """
    objetos = []

    ids = np.unique(mascara)
    ids = ids[ids != 0]

    for obj_id in ids:
        binaria = np.zeros(mascara.shape, dtype=np.uint8)
        binaria[mascara == obj_id] = 255

        contornos, _ = cv2.findContours(
            binaria,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        for contorno in contornos:
            contorno_simplificado = cv2.approxPolyDP(contorno, epsilon, True)
            puntos = contorno_simplificado.squeeze()

            if puntos.ndim == 2 and len(puntos) >= 3:
                objetos.append({
                    "id":     int(obj_id),
                    "tipo":   tipo_objeto,
                    "puntos": puntos.tolist()
                })

    return objetos