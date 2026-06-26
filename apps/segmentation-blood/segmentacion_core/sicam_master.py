import numpy as np
import cv2
import skimage.transform
from sklearn.cluster import DBSCAN

# ── Parámetros de detección ──
UMBRAL_ZSCORE_CELULA = 8      # z-score mínimo para considerar célula candidata
UMBRAL_ZSCORE_PIXEL  = 3      # z-score de píxel para filtrar brillantes
MIN_PIXELES_CLUSTER  = 5      # mínimo píxeles antes de entrar a DBSCAN
MIN_PUNTOS_CLUSTER   = 6      # mínimo puntos por cluster para ser válido
CIRCULARIDAD_MINIMA  = 0.5    # filtro de forma (0=línea, 1=círculo perfecto)
DBSCAN_EPS           = 2.5    # radio de vecindad fijo
DBSCAN_MIN_SAMPLES   = 4      # mínimo puntos para ser núcleo en DBSCAN

# ── Modelo cargado una sola vez al arrancar el servidor ──
_modelo = None


def _obtener_modelo():
    """
    Carga Cellpose en CPU la primera vez y lo reutiliza en todos los requests.

    El import de cellpose está AQUÍ (lazy) a propósito:
    - Evita que PyTorch se inicialice al importar el módulo
    - Previene el deadlock de multiprocessing/fork con Uvicorn
    - main.py llama a esta función en el lifespan para precargar al arrancar
    """
    global _modelo
    if _modelo is None:
        from cellpose import models  # import lazy — no mover al top del archivo
        print("[sicam_master] Cargando modelo Cellpose en CPU...")
        _modelo = models.CellposeModel(gpu=False)
        print("[sicam_master] Modelo listo.")
    return _modelo


# ============================================================
# FASE 1 — Preprocesamiento + Cellpose
# ============================================================

def _preprocesar(img_rgb: np.ndarray) -> np.ndarray:
    """
    Preprocesamiento optimizado para CPU en imágenes de sangre.

    Pasos:
        1. Resize a 224x224  (velocidad en CPU)
        2. Conversión a grises
        3. Corrección gamma  (levanta zonas oscuras / bajo contraste)
        4. CLAHE             (realza bordes de membranas)
        5. Unsharp masking   (refuerza bordes de alta frecuencia)
    """
    # 1. Resize
    img_reducida = skimage.transform.resize(img_rgb, (224, 224, 3), anti_aliasing=True)
    img_reducida = (img_reducida * 255).astype(np.uint8)

    # 2. Grises
    img_gris = cv2.cvtColor(img_reducida, cv2.COLOR_RGB2GRAY)

    # 3. Gamma (gamma < 1.0 aclara zonas oscuras)
    gamma = 0.8
    tabla = np.array([
        np.clip(pow(i / 255.0, gamma) * 255.0, 0, 255)
        for i in range(256)
    ], dtype=np.uint8).reshape(1, 256)
    img_gamma = cv2.LUT(img_gris, tabla)

    # 4. CLAHE
    clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8, 8))
    img_clahe = clahe.apply(img_gamma)

    # 5. Unsharp masking
    gaussian  = cv2.GaussianBlur(img_clahe, (3, 3), 0)
    img_final = cv2.addWeighted(img_clahe, 1.5, gaussian, -0.5, 0)

    return img_final


def _segmentar_celulas(img_rgb: np.ndarray) -> np.ndarray:
    """
    Segmenta células usando Cellpose.

    Returns:
        masks_orig: Máscara de IDs escalada al tamaño original (H x W, int32).
                    0 = fondo, 1..N = ID de cada célula.
    """
    h_orig, w_orig = img_rgb.shape[:2]

    img_prep = _preprocesar(img_rgb)
    modelo   = _obtener_modelo()

    # channels=[0,0] porque la imagen preprocesada es en grises
    masks_224, _, _ = modelo.eval(img_prep, diameter=None, channels=[0, 0])

    # Escalar al tamaño original (nearest neighbor preserva IDs enteros)
    if masks_224.shape != (h_orig, w_orig):
        masks_orig = skimage.transform.resize(
            masks_224,
            (h_orig, w_orig),
            order=0,
            preserve_range=True,
            anti_aliasing=False
        ).astype(np.int32)
    else:
        masks_orig = masks_224.astype(np.int32)

    print(f"[sicam_master] Células detectadas: {masks_orig.max()}")
    return masks_orig


# ============================================================
# FASE 2 — Z-score + DBSCAN + circularidad
# ============================================================

def _zscore_robusto_celula(pixeles: np.ndarray) -> float:
    """Z-score robusto de la célula completa (mediana + MAD)."""
    mediana = np.median(pixeles)
    mad     = np.median(np.abs(pixeles - mediana))
    if mad == 0:
        mad = 1e-9
    return float(0.6745 * (np.max(pixeles) - mediana) / mad)


def _detectar_micronucleos(img_gris: np.ndarray, masks: np.ndarray) -> np.ndarray:
    """
    Detecta micronúcleos dentro de las células segmentadas.

    Pipeline por célula candidata:
        1. Z-score robusto → selecciona células con píxeles anormalmente brillantes.
        2. Filtra píxeles muy brillantes dentro de la célula (z_pixel > umbral).
        3. DBSCAN sobre coordenadas de esos píxeles → detecta clusters.
        4. Filtro de circularidad → descarta clusters no redondos.

    Returns:
        Máscara uint16 donde cada micronúcleo tiene un ID único (0 = fondo).
    """
    h, w = img_gris.shape
    micronucleos_mask = np.zeros((h, w), dtype=np.uint16)
    id_mic = 0

    ids_celulas = np.unique(masks)
    ids_celulas = ids_celulas[ids_celulas != 0]
    print(f"[sicam_master] Células a analizar: {len(ids_celulas)}")

    # Paso 1: filtrar candidatas por z-score
    candidatas = []
    for cell_id in ids_celulas:
        pixeles = img_gris[(masks == cell_id)]
        if _zscore_robusto_celula(pixeles) > UMBRAL_ZSCORE_CELULA:
            candidatas.append(cell_id)

    print(f"[sicam_master] Células candidatas (z > {UMBRAL_ZSCORE_CELULA}): {len(candidatas)}")

    # Paso 2: DBSCAN + circularidad por candidata
    for cell_id in candidatas:
        coords       = np.argwhere(masks == cell_id)
        intensidades = img_gris[coords[:, 0], coords[:, 1]]

        # Filtrar solo píxeles muy brillantes dentro de la célula
        mediana  = np.median(intensidades)
        mad      = np.median(np.abs(intensidades - mediana)) + 1e-9
        z_pixs   = 0.6745 * (intensidades - mediana) / mad
        coords_b = coords[z_pixs > UMBRAL_ZSCORE_PIXEL]

        if len(coords_b) < MIN_PIXELES_CLUSTER:
            continue

        # n_jobs=1 es obligatorio dentro de un servidor async (Uvicorn).
        # n_jobs=-1 lanza subprocesos con fork que generan deadlock.
        dbscan    = DBSCAN(eps=DBSCAN_EPS, min_samples=DBSCAN_MIN_SAMPLES, n_jobs=1)
        etiquetas = dbscan.fit_predict(coords_b)

        for label in set(etiquetas):
            if label == -1:
                continue

            cluster_coords = coords_b[etiquetas == label].astype(int)

            if len(cluster_coords) < MIN_PUNTOS_CLUSTER:
                continue

            # Filtro de circularidad
            cm = np.zeros((h, w), dtype=np.uint8)
            cm[cluster_coords[:, 0], cluster_coords[:, 1]] = 1
            contornos, _ = cv2.findContours(cm, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            if not contornos:
                continue

            area      = cv2.contourArea(contornos[0])
            perimetro = cv2.arcLength(contornos[0], True)
            if perimetro == 0:
                continue

            if (4 * np.pi * area / perimetro ** 2) < CIRCULARIDAD_MINIMA:
                continue

            # Cluster válido → ID único
            id_mic += 1
            micronucleos_mask[cluster_coords[:, 0], cluster_coords[:, 1]] = id_mic

    print(f"[sicam_master] Micronúcleos detectados: {id_mic}")
    return micronucleos_mask


# ============================================================
# PUNTO DE ENTRADA para el microservicio
# ============================================================

def segmentar_desde_bytes(file_bytes: bytes) -> dict:
    """
    Punto de entrada del microservicio.

    Recibe los bytes de la imagen y ejecuta el pipeline completo:
        bytes → RGB → Cellpose → z-score/DBSCAN → máscaras

    No guarda nada en disco. Todo vive en memoria.

    Args:
        file_bytes: Bytes de la imagen (PNG, JPG, TIFF, etc.)

    Returns:
        {
            "celulas":      np.ndarray uint16  (H x W, ID por célula),
            "micronucleos": np.ndarray uint16  (H x W, ID por micronúcleo),
        }
    """
    # Decodificar bytes → RGB
    np_arr  = np.frombuffer(file_bytes, np.uint8)
    img_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    if img_bgr is None:
        raise ValueError("No se pudo decodificar la imagen. Verifica el formato.")

    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    print(f"[sicam_master] Imagen recibida: {img_rgb.shape}")

    # Fase 1: segmentar células con Cellpose
    masks_celulas = _segmentar_celulas(img_rgb)

    # Fase 2: detectar micronúcleos
    img_gris           = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
    masks_micronucleos = _detectar_micronucleos(img_gris, masks_celulas)

    return {
        "celulas":      masks_celulas.astype(np.uint16),
        "micronucleos": masks_micronucleos.astype(np.uint16),
    }