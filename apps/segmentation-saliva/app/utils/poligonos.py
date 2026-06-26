import numpy as np
import cv2
import json


def obtener_poligonos_desde_mascara(mascara, tipo_objeto, epsilon=1.5):
    """
    Convierte una máscara de segmentación en objetos geométricos unificados.

    mascara: array NumPy donde cada objeto tiene un ID distinto
    tipo_objeto: "membrana" | "nucleo" | "micronucleo"
    epsilon: nivel de simplificación del polígono
    """

    objetos = []

    # Obtener IDs únicos, excluyendo el fondo (0)
    ids = np.unique(mascara)
    ids = ids[ids != 0]

    for obj_id in ids:
        # Crear imagen binaria para cada objeto
        binaria = np.zeros(mascara.shape, dtype=np.uint8)
        binaria[mascara == obj_id] = 255

        # Detectar contornos
        contornos, _ = cv2.findContours(
            binaria,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        for contorno in contornos:
            contorno_simplificado = cv2.approxPolyDP(
                contorno,
                epsilon,
                True
            )

            puntos = contorno_simplificado.squeeze()

            # Validar polígono
            if puntos.ndim == 2 and len(puntos) >= 3:
                objetos.append({
                    "id": int(obj_id),
                    "tipo": tipo_objeto,
                    "puntos": puntos.tolist()
                })

    return objetos
