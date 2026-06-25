# 05 - Blood Microservice Inventory

## Project

```text
segmentacion_sangre
```

## Purpose

Segment blood microscopy images into:

- Cell/membrane masks
- Micronucleus masks

## Framework

- FastAPI

## Entry Point

```text
main.py
```

## Application Metadata

```text
title: Microservicio Segmentación Sangre
description: Segmentación de imágenes de sangre para análisis de micronúcleos
version: 1.0.0
```

## Endpoint

```http
POST /api/v1/segmentar
Content-Type: multipart/form-data
```

Input field:

```text
file
```

## Endpoint Flow

```text
UploadFile
  ↓
read bytes
  ↓
run_in_threadpool(segmentar_pipeline, bytes)
  ↓
obtener_poligonos_desde_mascara(celulas, "membrana")
obtener_poligonos_desde_mascara(micronucleos, "micronucleo")
  ↓
return { objetos: [...] }
```

## Output Contract

```json
{
  "objetos": [
    {
      "id": 1,
      "tipo": "membrana",
      "puntos": [[10, 20], [12, 25], [15, 28]]
    },
    {
      "id": 1,
      "tipo": "micronucleo",
      "puntos": [[40, 50], [42, 51], [43, 53]]
    }
  ]
}
```

## Startup Lifecycle

The service uses FastAPI lifespan to preload Cellpose:

```text
startup
  ↓
run_in_threadpool(_obtener_modelo)
  ↓
model ready
```

This is a good pattern because it avoids loading the model on every request.

## Core File

```text
segmentacion_core/sicam_master.py
```

## Core Constants

```text
UMBRAL_ZSCORE_CELULA = 8
UMBRAL_ZSCORE_PIXEL = 3
MIN_PIXELES_CLUSTER = 5
MIN_PUNTOS_CLUSTER = 6
CIRCULARIDAD_MINIMA = 0.5
DBSCAN_EPS = 2.5
DBSCAN_MIN_SAMPLES = 4
```

## Model Loading

The Cellpose model is lazily initialized and cached globally:

```python
_modelo = None

def _obtener_modelo():
    global _modelo
    if _modelo is None:
        from cellpose import models
        _modelo = models.CellposeModel(gpu=False)
    return _modelo
```

## Processing Pipeline

### 1. Decode Image

```text
bytes
  ↓
np.frombuffer
  ↓
cv2.imdecode
  ↓
BGR to RGB
```

### 2. Preprocessing

```text
RGB image
  ↓
resize to 224x224
  ↓
grayscale
  ↓
gamma correction, gamma = 0.8
  ↓
CLAHE, clipLimit = 4.0, tileGridSize = (8, 8)
  ↓
unsharp masking
```

### 3. Cell Segmentation

Uses Cellpose on the preprocessed grayscale image:

```text
channels = [0, 0]
diameter = None
```

The 224x224 mask is resized back to original dimensions using nearest-neighbor interpolation to preserve integer IDs.

### 4. Micronucleus Detection

For each cell:

```text
cell pixels
  ↓
robust z-score using median + MAD
  ↓
filter candidate cells by UMBRAL_ZSCORE_CELULA
  ↓
filter bright pixels by UMBRAL_ZSCORE_PIXEL
  ↓
DBSCAN on bright-pixel coordinates
  ↓
filter clusters by minimum points
  ↓
filter clusters by circularity
  ↓
assign micronucleus ID
```

### 5. Return Masks

```python
{
    "celulas": masks_celulas.astype(np.uint16),
    "micronucleos": masks_micronucleos.astype(np.uint16),
}
```

## Concurrency Design

The endpoint uses:

```python
await run_in_threadpool(segmentar_pipeline, contenido)
```

This prevents heavy synchronous CPU/ML processing from blocking the FastAPI event loop.

## Important Implementation Note

DBSCAN is configured with:

```text
n_jobs = 1
```

The code comment states this avoids multiprocessing/fork deadlocks inside Uvicorn. This should be preserved unless the deployment model is redesigned.

## Current Gaps

- No formal Pydantic response model.
- No health endpoint.
- No model metadata endpoint.
- No request validation beyond image decoding.
- No structured error codes.
- No configurable thresholds through environment or settings file.
- No test fixtures for blood images.
- No benchmark script.

## Refactor Recommendations

### Extract configuration

Move constants into a settings object:

```python
class BloodSegmentationSettings(BaseSettings):
    umbral_zscore_celula: float = 8
    umbral_zscore_pixel: float = 3
    min_pixeles_cluster: int = 5
    min_puntos_cluster: int = 6
    circularidad_minima: float = 0.5
    dbscan_eps: float = 2.5
    dbscan_min_samples: int = 4
```

### Standardize response schema

Use the same schema as saliva.

### Add health endpoint

```http
GET /api/v1/health
```

Response:

```json
{
  "status": "ok",
  "model_loaded": true,
  "service": "blood-segmentation"
}
```
