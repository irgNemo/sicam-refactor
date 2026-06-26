import numpy as np
import cv2
from segmentacion_core.cellpose import models
from segmentacion_core.model.cytoplasm import Cytoplasm


# ================================
# FILTRO ORIGINAL (sin cambios)
# ================================
def filtrar_con_cytoplasm_original(masks):
    ids = np.unique(masks)[1:]
    masks_limpia = masks.copy()

    for celula_id in ids:
        posiciones = np.where(masks == celula_id)
        if len(posiciones[0]) == 0:
            continue

        y_min, y_max = np.min(posiciones[0]), np.max(posiciones[0])
        x_min, x_max = np.min(posiciones[1]), np.max(posiciones[1])

        h_cell = y_max - y_min
        w_cell = x_max - x_min

        dummy_mask = np.zeros((h_cell, w_cell), dtype=np.uint8)
        obj_cytoplasm = Cytoplasm(mask=dummy_mask, pos_x=x_min, pos_y=y_min)

        es_valida = obj_cytoplasm.is_a_element(shape=masks.shape)

        if not es_valida:
            masks_limpia[masks == celula_id] = 0

    return masks_limpia


# ================================
# CLASE SERVICIO
# ================================
class SegmentadorMembranas:

    def __init__(self, modelo_path, gpu=False):
        self.modelo = models.CellposeModel(
            gpu=gpu,
            pretrained_model=str(modelo_path)
        )

    def segmentar(self, imagen_rgb: np.ndarray) -> np.ndarray:

        masks, flows, styles = self.modelo.eval(
            imagen_rgb,
            diameter=125,
            channels=[1, 0],
            flow_threshold=0.4,
            cellprob_threshold=0.0
        )

        masks_finales = filtrar_con_cytoplasm_original(masks)

        return masks_finales.astype(np.uint16)
