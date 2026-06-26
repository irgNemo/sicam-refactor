import numpy as np
from segmentacion_core.model.micronuclei import Micronuclei
from segmentacion_core.model.cytoplasm import Cytoplasm


def _extraer_elementos_cytoplasm(masks_cytoplasm, cytoplasm_data):
    elementos = []

    total = int(masks_cytoplasm.max())

    for i in range(total):
        celula_id = i + 1
        pos = np.where(masks_cytoplasm == celula_id)

        if len(pos[0]) == 0:
            continue

        x_min, x_max = np.min(pos[1]), np.max(pos[1])
        y_min, y_max = np.min(pos[0]), np.max(pos[0])

        mask_individual = np.where(
            masks_cytoplasm[y_min:y_max, x_min:x_max] == celula_id,
            celula_id,
            0
        ).astype("uint8")

        elemento = Cytoplasm(mask=mask_individual, pos_x=x_min, pos_y=y_min)

        if i < len(cytoplasm_data):
            data = cytoplasm_data[i]
            elemento.color_nuclei = data.color_nuclei
            elemento.area = data.area

        elementos.append(elemento)

    return elementos


def _crear_mascara_micronucleos(elementos, shape):
    mask_final = np.zeros(shape, dtype="uint8")

    for micro in elementos:
        if micro.micronucleis is None:
            continue

        if not isinstance(micro.micronucleis, np.ndarray):
            continue

        h, w = micro.micronucleis.shape

        y_end = min(micro.pos_y + h, shape[0])
        x_end = min(micro.pos_x + w, shape[1])

        mask_final[micro.pos_y:y_end, micro.pos_x:x_end] = np.where(
            micro.micronucleis[: y_end - micro.pos_y, : x_end - micro.pos_x] > 0,
            255,
            mask_final[micro.pos_y:y_end, micro.pos_x:x_end],
        )

    return mask_final


# =============================
# FUNCIÓN QUE USA TU SERVICE
# =============================
def segmentar_micronucleos(imagen_rgb, masks_cytoplasm, cytoplasm_data):

    elementos_cytoplasm = _extraer_elementos_cytoplasm(masks_cytoplasm, cytoplasm_data)

    elementos_validos = []

    for cyto in elementos_cytoplasm:

        if getattr(cyto, "color_nuclei", None) is None:
            continue

        micro = Micronuclei(
            mask=cyto.mask,
            pos_x=cyto.pos_x,
            pos_y=cyto.pos_y
        )

        n_micro = micro.is_a_element(
            img=imagen_rgb,
            cytoplasm=cyto
        )

        if n_micro > 0:
            elementos_validos.append(micro)

    mask_micro = _crear_mascara_micronucleos(elementos_validos, imagen_rgb.shape[:2])

    return mask_micro
