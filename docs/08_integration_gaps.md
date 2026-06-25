# 08 - Integration Gaps

## Summary

The documentation describes SICAM as an integrated platform, but the code currently consists of three mostly independent applications.

The main gap is orchestration:

```text
Django backend does not yet orchestrate saliva/blood segmentation services and persist their outputs as first-class domain data.
```

## Gap 1: Backend does not call segmentation microservices

Existing microservices:

```text
Segmentacion_web: POST /segmentar
segmentacion_sangre: POST /api/v1/segmentar
```

Current Django backend has no observed client code for these services.

### Required Integration

```text
Sample uploaded
  ↓
Django determines sample type
  ↓
Django calls the correct microservice
  ↓
Django stores returned polygons/counts
  ↓
Frontend displays editable segmentation
```

## Gap 2: Backend only models saliva samples

Current model:

```text
MuestraSaliva
```

Required:

```text
ImagenMuestra
- sample_type: SALIVA | BLOOD
```

## Gap 3: Frontend does not let user select sample type

The documents state that the user must specify saliva or blood because each type has a different processing pipeline.

The current upload flow posts to `/api/muestras/` and maps to `MuestraSaliva`, so blood is not represented.

## Gap 4: Segmentation output is not persisted as JSON

Microservices return:

```json
{
  "objetos": [
    {
      "id": 1,
      "tipo": "membrana",
      "puntos": [[10, 20]]
    }
  ]
}
```

Backend currently stores:

- counts in `ResultadoAnalisis`
- mask image files in `AnalisisMascara`

It does not store editable polygons.

## Gap 5: No validation workflow

Documents describe interactive validation and correction by specialist.

Current code lacks:

- validated flag
- reviewer
- edited object persistence
- revision history
- undo/redo persistence
- distinction between automatic and manual result

## Gap 6: Characterization missing from implementation

The academic documents describe calculation of:

- area
- perimeter
- roundness/circularity
- centroid
- mean intensity
- distance nucleus-micronucleus
- area fraction
- intensity fraction

The frontend has a placeholder for characterization, and the backend has no characterization model or endpoint.

## Gap 7: Report generation missing from implementation

The documents describe PDF and CSV generation.

Current code has UI buttons for export, but no backend report generation or file model was observed.

## Gap 8: Authentication/roles not implemented as described

Documents describe controlled doctor access.

Current Django project includes default Django auth apps but no observed custom endpoints or doctor model.

Missing:

- Doctor profile
- Admin-created doctor workflow
- Login endpoint
- Token/session API
- Route protection
- Frontend auth state

## Gap 9: Configuration not externalized

Hardcoded values exist in backend and frontend:

```text
Django SECRET_KEY
Django DB credentials
CORS_ALLOW_ALL_ORIGINS
Frontend API URL
```

Microservice URLs are not centrally configured.

## Gap 10: Duplicated code in microservices

Both microservices contain similar:

```text
app/routers/segmentacion.py
app/services/segmentador.py
app/utils/poligonos.py
segmentacion_core/cellpose/
```

Recommendation: extract shared code and schemas.

## Gap 11: API contracts are implicit

There is no OpenAPI schema customization, no shared type definitions, and no contract document used by Django/frontend/microservices.

This is risky because Codex or developers may accidentally change field names like:

```text
objetos
tipo
puntos
membrana
nucleo
micronucleo
```

## Gap 12: State names are not fully aligned

Academic/domain language:

```text
Paciente
Caso clínico
Muestra
Segmentación
Caracterización
Reporte
```

Current implementation:

```text
Paciente
Caso
AnalisisPred
MuestraSaliva
ResultadoAnalisis
AnalisisMascara
```

Recommendation: define a canonical ubiquitous language and apply it consistently.
