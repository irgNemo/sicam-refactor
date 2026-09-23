import numpy as np
import cv2

from segmentacion_core.seg_pipeline_v2 import segmentar_todo


def leer_imagen_bytes(file_bytes: bytes):
    if not file_bytes:
        raise ValueError("No se pudo decodificar la imagen")
    np_arr = np.frombuffer(file_bytes, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    if img is None:
        raise ValueError("No se pudo decodificar la imagen")

    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    return img_rgb


def segmentar_pipeline(file_bytes: bytes):
    img = leer_imagen_bytes(file_bytes)
    resultado = segmentar_todo(img)
    return resultado
