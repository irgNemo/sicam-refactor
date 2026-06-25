# 04 - Saliva Microservice Inventory

## Project

```text
Segmentacion_web
```

## Purpose

Segment saliva microscopy images into:

- Membranes
- Nuclei
- Micronuclei

## Framework

- FastAPI

## Entry Point

```text
app/main.py
```

Current application:

```python
app = FastAPI()
app.include_router(segmentacion_router)
```

## Endpoint

```http
POST /segmentar
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
segmentar_pipeline(bytes)
  ↓
obtener_poligonos_desde_mascara(membranas)
obtener_poligonos_desde_mascara(nucleos)
obtener_poligonos_desde_mascara(micronucleos)
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
      "tipo": "nucleo",
      "puntos": [[20, 30], [22, 35], [25, 38]]
    },
    {
      "id": 1,
      "tipo": "micronucleo",
      "puntos": [[40, 50], [42, 51], [43, 53]]
    }
  ]
}
```

## Core Pipeline

Defined in:

```text
app/services/segmentador.py
```

### Pipeline

```text
file bytes
  ↓
cv2.imdecode
  ↓
BGR to RGB
  ↓
SegmentadorMembranas.segmentar
  ↓
segmentar_nucleos
  ↓
segmentar_micronucleos
  ↓
return masks
```

## Membrane Segmentation

Defined in:

```text
segmentacion_core/seg_membranas.py
```

Uses:

```python
models.CellposeModel(
    gpu=False,
    pretrained_model="segmentacion_core/membranas_500_125"
)
```

Evaluation parameters:

```text
diameter = 125
channels = [1, 0]
flow_threshold = 0.4
cellprob_threshold = 0.0
```

Post-processing:

- `filtrar_con_cytoplasm_original`
- Uses `Cytoplasm.is_a_element`
- Invalid detections are removed from the mask

## Nucleus Segmentation

Defined in:

```text
segmentacion_core/seg_nucleos.py
```

Process:

```text
cytoplasm masks
  ↓
extract cytoplasm objects
  ↓
create Nuclei object per cytoplasm
  ↓
Nuclei.is_a_element(img, cytoplasm)
  ↓
compose final nuclei mask
```

## Micronucleus Segmentation

Defined in:

```text
segmentacion_core/seg_micronucleos.py
```

Process:

```text
cytoplasm masks + cytoplasm metadata
  ↓
extract cytoplasm objects
  ↓
skip cytoplasms without color_nuclei
  ↓
Micronuclei.is_a_element(img, cytoplasm)
  ↓
compose final micronuclei mask
```

## Polygon Utility

Defined in:

```text
app/utils/poligonos.py
```

Purpose:

- Converts integer instance masks into polygon objects.
- Excludes background ID 0.
- Uses OpenCV `findContours`.
- Simplifies contours using `approxPolyDP`.

Default simplification:

```text
epsilon = 1.5
```

## Runtime Behavior

The membrane model is loaded at module import time:

```python
segmentador_mem = SegmentadorMembranas(...)
```

Benefit:

- Avoids reloading model per request.

Risk:

- Slow import/startup.
- Harder to handle startup errors cleanly.
- No explicit FastAPI lifespan lifecycle.

## Current Gaps

- No health endpoint.
- No version endpoint.
- No formal Pydantic response model.
- No request size validation.
- No structured logging.
- No correlation/request ID.
- No timeout handling.
- No async threadpool handling for heavy CPU/ML work.
- No batch endpoint.
- No shared schema with blood microservice.

## Refactor Recommendations

### Add explicit API version

```text
/api/v1/segmentar
```

### Add response model

```python
class PolygonObject(BaseModel):
    id: int
    tipo: Literal["membrana", "nucleo", "micronucleo"]
    puntos: list[list[int]]

class SegmentationResponse(BaseModel):
    objetos: list[PolygonObject]
```

### Add FastAPI lifespan

Use a lifespan handler to load models on startup, equivalent to the blood microservice approach.

### Add common package

Extract duplicated utilities into:

```text
sicam_segmentation_common/
├── schemas.py
├── polygon_utils.py
├── image_io.py
└── errors.py
```
