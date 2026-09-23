"""Recovered morphological pipeline; scientific operations preserved (Sprint 18A)."""
import hashlib
import logging
from importlib.metadata import version
from pathlib import Path

import numpy as np
import skimage.color
import skimage.exposure
import skimage.transform
import skimage.segmentation
import skimage.measure
import skimage.morphology
import skimage.filters
import scipy.ndimage as ndi

STRATEGY = "ALT_CPSAM_MORPHOLOGICAL_V1"
CELLPOSE_VERSION = "4.0.8"
CELLPOSE_MODEL = "cpsam"
ALGORITHM_VERSION = "1.0"
MODEL_SIZE = 1233587898
MODEL_SHA256 = "e1440429eb384f95afe32bcba6510f90d518eaedc917ede549bed6804004abe2"
logger = logging.getLogger("uvicorn.error")
_modelo_membranas = None


def verificar_artefacto(path: Path):
    """Fail before model construction: no implicit download or model fallback."""
    if not path.is_file() or path.stat().st_size != MODEL_SIZE:
        raise RuntimeError(f"cpsam ausente o con tamaño incompatible: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as model_file:
        for chunk in iter(lambda: model_file.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != MODEL_SHA256:
        raise RuntimeError(f"SHA-256 de cpsam incompatible: {path}")


def _get_modelo(gpu: bool = False):
    global _modelo_membranas
    if gpu:
        raise ValueError("ALT v1 usa exclusivamente CPU")
    if _modelo_membranas is None:
        actual_version = version("cellpose")
        if actual_version != CELLPOSE_VERSION:
            raise RuntimeError(f"Cellpose requerido: {CELLPOSE_VERSION}; instalado: {actual_version}")
        from cellpose import models

        if CELLPOSE_MODEL not in models.MODEL_NAMES:
            raise RuntimeError("La API instalada no reconoce cpsam")
        model_path = (Path(models.MODEL_DIR) / CELLPOSE_MODEL).resolve()
        verificar_artefacto(model_path)
        # Absolute verified cpsam path avoids both name fallback and cwd shadowing.
        modelo = models.CellposeModel(pretrained_model=str(model_path), gpu=False)
        if Path(modelo.pretrained_model).resolve() != model_path:
            raise RuntimeError("Cellpose no cargó el artefacto cpsam solicitado")
        _modelo_membranas = modelo
        logger.info(
            "strategy=%s cellpose_version=%s model=%s algorithm_version=%s path=%s",
            STRATEGY, actual_version, CELLPOSE_MODEL, ALGORITHM_VERSION, model_path,
        )
    return _modelo_membranas


def inicializar_modelo(gpu: bool = False):
    """Preload once during the FastAPI lifespan, before accepting requests."""
    _get_modelo(gpu=gpu)


# ================================================================
# NUCLEOS PRINCIPALES (analisis morfologico clasico, sin red extra)
# ================================================================
def extraer_nucleos_principales(img_rgb, membranas_finales):
    """
    Detecta y segmenta los nucleos principales dentro de cada membrana validada
    utilizando transformadas de distancia, umbralizacion adaptativa y geometria.
    """
    img_gray = skimage.color.rgb2gray(img_rgb)
    mascara_nucleos = np.zeros_like(membranas_finales)
    regiones_membrana = skimage.measure.regionprops(membranas_finales)

    for region in regiones_membrana:
        min_row, min_col, max_row, max_col = region.bbox

        recorte_gris = img_gray[min_row:max_row, min_col:max_col]
        recorte_mascara = (membranas_finales[min_row:max_row, min_col:max_col] == region.label)

        # Suavizado gaussiano para homogeneizar la textura intracelular
        recorte_suave = skimage.filters.gaussian(recorte_gris, sigma=1.0, preserve_range=True)
        pixeles_celula = recorte_suave[recorte_mascara]

        if len(pixeles_celula) < 100:
            continue

        # Segmentacion inicial por umbralizacion (Otsu multinivel o simple)
        try:
            umbrales = skimage.filters.threshold_multiotsu(pixeles_celula, classes=3)
            limite_nucleo = umbrales[0]
        except Exception:
            limite_nucleo = skimage.filters.threshold_otsu(pixeles_celula) * 0.95

        mascara_oscura = (recorte_suave < limite_nucleo) & recorte_mascara
        distancia = ndi.distance_transform_edt(mascara_oscura)

        if distancia.max() < 3:
            continue

        area_celula = np.sum(recorte_mascara)

        # Aislamiento de centros de masa (semillas)
        mascara_distancia = distancia > (distancia.max() * 0.45)
        mascara_distancia_limpia = skimage.morphology.remove_small_objects(mascara_distancia, min_size=10)

        regiones_etiquetadas = skimage.measure.label(mascara_distancia_limpia)
        propiedades_regiones = skimage.measure.regionprops(regiones_etiquetadas)

        mascara_final_celula = np.zeros_like(recorte_mascara, dtype=bool)

        if propiedades_regiones:
            propiedades_regiones.sort(key=lambda m: m.area, reverse=True)
            area_maxima = propiedades_regiones[0].area

            # Filtro global: Rechazo de celulas presumiblemente anucleadas (ruido de fondo)
            if area_maxima < (area_celula * 0.003):
                continue

            for region_candidata in propiedades_regiones:
                if region_candidata.area >= area_maxima * 0.30:
                    region_aislada = (regiones_etiquetadas == region_candidata.label)

                    # Reconstruccion morfologica por dilatacion ajustada al mapa de distancias
                    radio_dilatacion = int(distancia.max() * 0.55)
                    region_dilatada = skimage.morphology.dilation(region_aislada, skimage.morphology.disk(radio_dilatacion))
                    region_recortada = region_dilatada & mascara_oscura

                    temp_label = skimage.measure.label(region_recortada)
                    temp_props = skimage.measure.regionprops(temp_label)

                    if temp_props:
                        p = temp_props[0]

                        # Filtro topologico: Exclusion de pliegues en la membrana exterior
                        bordes_celula = skimage.segmentation.find_boundaries(recorte_mascara, mode='inner')
                        pixeles_borde = np.sum(region_recortada & bordes_celula)

                        if pixeles_borde > 30 and p.eccentricity > 0.80:
                            continue

                        # Filtro fotometrico: Verificacion de contraste real vs region celular completa
                        intensidad_nucleo = np.mean(recorte_gris[region_recortada])
                        intensidad_region_celular = np.mean(recorte_gris[recorte_mascara])

                        if (intensidad_region_celular - intensidad_nucleo) < 0.06:
                            continue

                        # Validacion geometrica final
                        if p.area > 35 and p.eccentricity < 0.92 and p.solidity > 0.70:
                            region_convexa = skimage.morphology.convex_hull_image(region_recortada)
                            mascara_final_celula |= region_convexa

        mascara_final_celula = mascara_final_celula & recorte_mascara
        mascara_nucleos[min_row:max_row, min_col:max_col][mascara_final_celula] = region.label

    return mascara_nucleos


# ================================================================
# MICRONUCLEOS (analisis de densidad optica citoplasmatica)
# ================================================================
def extraer_micronucleos(img_rgb, membranas_finales, nucleos_finales):
    """
    Identifica micronucleos evaluando densidades opticas citoplasmaticas.
    Aplica limites estrictos basados en la proporcion 1/16 a 1/3 del nucleo de la membrana local.
    """
    img_gray = skimage.color.rgb2gray(img_rgb)
    mascara_mn = np.zeros_like(membranas_finales)
    regiones_membrana = skimage.measure.regionprops(membranas_finales)

    for region in regiones_membrana:
        min_row, min_col, max_row, max_col = region.bbox

        recorte_gris = img_gray[min_row:max_row, min_col:max_col]
        recorte_mascara = (membranas_finales[min_row:max_row, min_col:max_col] == region.label)
        recorte_nucleo_principal = (nucleos_finales[min_row:max_row, min_col:max_col] == region.label)

        # Validacion logica: No se pueden calcular proporciones relativas sin un nucleo principal
        if not np.any(recorte_nucleo_principal):
            continue

        area_nucleo_principal = np.sum(recorte_nucleo_principal)
        intensidad_nucleo_principal = np.mean(recorte_gris[recorte_nucleo_principal])
        intensidad_region_celular = np.mean(recorte_gris[recorte_mascara])

        recorte_suave = skimage.filters.gaussian(recorte_gris, sigma=1.0, preserve_range=True)
        pixeles_celula = recorte_suave[recorte_mascara]

        try:
            umbrales = skimage.filters.threshold_multiotsu(pixeles_celula, classes=3)
            limite_nucleo = umbrales[0]
        except Exception:
            limite_nucleo = skimage.filters.threshold_otsu(pixeles_celula) * 0.95

        # Aislamiento de material denso excluyendo el nucleo principal
        mascara_oscura = (recorte_suave < limite_nucleo) & recorte_mascara
        candidatos_crudos = mascara_oscura & ~recorte_nucleo_principal

        # Supresion de ruido digital de alta frecuencia
        candidatos_filtrados = skimage.morphology.remove_small_objects(candidatos_crudos, min_size=800)

        etiquetas_mn = skimage.measure.label(candidatos_filtrados)
        propiedades_mn = skimage.measure.regionprops(etiquetas_mn)

        # Limite matematico estricto basado en la proporcion biologica del MN (1/16 a 1/3)
        area_minima_mn = max(800, area_nucleo_principal / 16.0)
        area_maxima_mn = area_nucleo_principal / 3.0

        mascara_final_celula_mn = np.zeros_like(recorte_mascara, dtype=bool)

        for candidato in propiedades_mn:
            if area_minima_mn <= candidato.area <= area_maxima_mn:

                # Relacion de aspecto para descartar anomalias lineales (pliegues)
                aspect_ratio = 1.0
                if candidato.minor_axis_length > 0:
                    aspect_ratio = candidato.major_axis_length / candidato.minor_axis_length

                if aspect_ratio < 2.5 and candidato.eccentricity < 0.90 and candidato.solidity > 0.70:
                    mascara_candidato = (etiquetas_mn == candidato.label)

                    intensidad_candidato = np.mean(recorte_gris[mascara_candidato])

                    # Validacion de tincion: La intensidad debe asemejarse al nucleo principal
                    if intensidad_candidato > (intensidad_nucleo_principal + 0.12):
                        continue

                    if (intensidad_region_celular - intensidad_candidato) < 0.05:
                        continue

                    bordes_celula = skimage.segmentation.find_boundaries(recorte_mascara, mode='inner')
                    if np.sum(mascara_candidato & bordes_celula) < 5:

                        mn_convexo = skimage.morphology.convex_hull_image(mascara_candidato)
                        mascara_final_celula_mn |= mn_convexo

        mascara_mn[min_row:max_row, min_col:max_col][mascara_final_celula_mn] = region.label

    return mascara_mn


# ================================================================
# PIPELINE COMPLETO (reemplaza a SegmentadorMembranas + segmentar_nucleos
# + segmentar_micronucleos del flujo anterior)
# ================================================================
def segmentar_todo(img_rgb: np.ndarray) -> dict:
    """
    Recibe una imagen RGB (numpy array) y regresa un diccionario con las 3
    mascaras de etiquetas (membranas, nucleos, micronucleos), cada una como
    array uint16 con el label de la membrana y fondo = 0.
    Varios componentes nucleares/MN pueden compartir el mismo label.

    Mantiene el mismo contrato de salida que el pipeline viejo para que
    segmentacion.py y poligonos.py no requieran cambios.
    """
    modelo = _get_modelo()

    tamano_original = img_rgb.shape[:2]
    TAMANO_NORMALIZADO = (512, 512)
    img_reducida = skimage.transform.resize(img_rgb, TAMANO_NORMALIZADO, anti_aliasing=True)

    img_gray = skimage.color.rgb2gray(img_reducida) if img_reducida.ndim == 3 else img_reducida

    # Preprocesamiento: ajuste global de contraste y rango dinamico
    img_inv = 1.0 - img_gray
    p1, p99 = np.percentile(img_inv, (1, 99))

    # Filtro anti-ruido: exige >=10% de contraste real antes de estirar
    limite_superior = max(p99, p1 + 0.10)

    img_estirada = skimage.exposure.rescale_intensity(img_inv, in_range=(p1, limite_superior))
    img_lista_cellpose = (img_estirada * 255).astype(np.uint8)

    # Fase 1: inferencia de membranas con cpsam
    resultados = modelo.eval(
        img_lista_cellpose,
        diameter=80,
        flow_threshold=0.5,
        cellprob_threshold=-0.5,
        resample=False,
    )
    membranas_brutas = resultados[0]

    membranas_filtradas_tamano = skimage.morphology.remove_small_objects(membranas_brutas, min_size=200)

    # Reescalar la mascara al tamano original de la imagen (nearest-neighbor
    # para no interpolar los IDs de las etiquetas)
    membranas_finales = skimage.transform.resize(
        membranas_filtradas_tamano,
        tamano_original,
        order=0,
        anti_aliasing=False,
        preserve_range=True,
    ).astype(np.uint16)

    logger.debug(f" Fase 1 (membranas brutas, tras resize): {len(np.unique(membranas_finales)) - 1} objetos")

    # Fase 2: nucleos principales
    nucleos_finales = extraer_nucleos_principales(img_rgb, membranas_finales)

    logger.debug(f" Fase 2 (nucleos detectados): {len(np.unique(nucleos_finales)) - 1} objetos")

    # Fase 3: se descartan las membranas sin nucleo detectado (celulas anucleadas)
    membranas_validadas = np.zeros_like(membranas_finales)
    etiquetas_con_nucleo = np.unique(nucleos_finales[nucleos_finales > 0])
    for etiqueta in etiquetas_con_nucleo:
        membranas_validadas[membranas_finales == etiqueta] = etiqueta
    membranas_finales = membranas_validadas

    logger.debug(f" Fase 3 (membranas validadas, con nucleo): {len(np.unique(membranas_finales)) - 1} objetos")

    # Fase 4: micronucleos
    mn_finales = extraer_micronucleos(img_rgb, membranas_finales, nucleos_finales)

    logger.debug(f" Fase 4 (micronucleos detectados): {len(np.unique(mn_finales)) - 1} objetos")

    return {
        "membranas": membranas_finales.astype(np.uint16),
        "nucleos": nucleos_finales.astype(np.uint16),
        "micronucleos": mn_finales.astype(np.uint16),
    }