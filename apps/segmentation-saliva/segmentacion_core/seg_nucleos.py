import numpy as np
from segmentacion_core.model.nuclei import Nuclei
from segmentacion_core.model.cytoplasm import Cytoplasm


# ================================
# EXTRAER CITOPLASMAS (igual que tu código)
# ================================
def extraer_elementos_cytoplasm(masks_cytoplasm):
    elementos = []

    for i in range(masks_cytoplasm.max()):
        celula_id = i + 1
        pos_x_y = np.where(masks_cytoplasm == celula_id)

        if len(pos_x_y[0]) == 0:
            continue

        x_min = np.min(pos_x_y[1])
        x_max = np.max(pos_x_y[1])
        y_min = np.min(pos_x_y[0])
        y_max = np.max(pos_x_y[0])

        mask_individual = np.where(
            masks_cytoplasm[y_min:y_max, x_min:x_max] == celula_id,
            celula_id,
            0
        ).astype("uint8")

        elemento = Cytoplasm(mask=mask_individual, pos_x=x_min, pos_y=y_min)
        elementos.append(elemento)

    return elementos


# ================================
# DETECCIÓN DE NÚCLEOS (núcleo científico intacto)
# ================================
def detectar_nucleos(imagen_rgb, masks_cytoplasm):

    elementos_cytoplasm = extraer_elementos_cytoplasm(masks_cytoplasm)

    elementos_nuclei = []
    for cyto in elementos_cytoplasm:
        nuclei = Nuclei(mask=cyto.mask, pos_x=cyto.pos_x, pos_y=cyto.pos_y)
        elementos_nuclei.append(nuclei)

    elementos_validos = []

    for nuclei, cyto in zip(elementos_nuclei, elementos_cytoplasm):
        n_nucleos = nuclei.is_a_element(img=imagen_rgb, cytoplasm=cyto)

        if n_nucleos > 0:
            elementos_validos.append(nuclei)

    return elementos_validos, elementos_cytoplasm


# ================================
# CREAR MÁSCARA FINAL
# ================================
def crear_mascara_nucleos(elementos_nuclei, shape):

    masks_nuclei = np.zeros(shape, dtype="uint16")

    for nuclei in elementos_nuclei:
        if nuclei.nucleis is not None and isinstance(nuclei.nucleis, np.ndarray):

            y_end = min(nuclei.pos_y + nuclei.nucleis.shape[0], shape[0])
            x_end = min(nuclei.pos_x + nuclei.nucleis.shape[1], shape[1])

            y_slice = slice(nuclei.pos_y, y_end)
            x_slice = slice(nuclei.pos_x, x_end)

            mask_h = y_end - nuclei.pos_y
            mask_w = x_end - nuclei.pos_x

            masks_nuclei[y_slice, x_slice] = np.where(
                nuclei.nucleis[:mask_h, :mask_w] > 0,
                nuclei.nucleis[:mask_h, :mask_w],
                masks_nuclei[y_slice, x_slice]
            )

    return masks_nuclei


# ================================
# FUNCIÓN PRINCIPAL DEL SERVICIO
# ================================
def segmentar_nucleos(imagen_rgb, masks_cytoplasm):

    elementos_nuclei, elementos_cytoplasm = detectar_nucleos(
        imagen_rgb,
        masks_cytoplasm
    )

    masks_nucleos = crear_mascara_nucleos(
        elementos_nuclei,
        imagen_rgb.shape[:2]
    )

    return masks_nucleos.astype(np.uint16), elementos_cytoplasm
