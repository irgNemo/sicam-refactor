import numpy as np
from pathlib import Path
import cv2

# ===== importar tu core =====
from segmentacion_core.seg_membranas import SegmentadorMembranas
from segmentacion_core.seg_nucleos import segmentar_nucleos
from segmentacion_core.seg_micronucleos import segmentar_micronucleos

from segmentacion_core.cellpose import models


# ===== rutas absolutas =====
BASE_DIR = Path(__file__).resolve().parents[2]
CORE_DIR = BASE_DIR / "segmentacion_core"


# ===== cargar modelos una sola vez =====
segmentador_mem = SegmentadorMembranas(
    BASE_DIR / "segmentacion_core" / "membranas_500_125",
    gpu=False
)

# si nucleos/micronucleos usan modelo propio, cárgalo aquí


# ===== util =====
def leer_imagen_bytes(file_bytes: bytes):
    np_arr = np.frombuffer(file_bytes, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    if img is None:
        raise ValueError("No se pudo decodificar la imagen")

    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    return img_rgb


# ===== pipeline completo =====
def segmentar_pipeline(file_bytes: bytes):
    img = leer_imagen_bytes(file_bytes)

    masks_mem = segmentador_mem.segmentar(img)

    masks_nuc, cytoplasm_data = segmentar_nucleos(img, masks_mem)

    masks_mic = segmentar_micronucleos(img, masks_mem, cytoplasm_data)

    return {
        "membranas": masks_mem.astype(np.uint16),
        "nucleos": masks_nuc.astype(np.uint16),
        "micronucleos": masks_mic.astype(np.uint16),
    }
