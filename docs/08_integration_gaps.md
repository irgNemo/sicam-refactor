# 08 - Integration Gaps

## Summary

SICAM now has a cleaner repository baseline, externalized configuration, a centralized frontend API client, and Django-side clients for the segmentation microservices.

The main remaining gap is still orchestration:

```text
Django does not yet expose an endpoint that receives a stored sample,
calls the correct segmentation microservice, persists the returned JSON,
and returns a segmentation status/result to the frontend.
```

## Already Addressed

The following items should no longer be treated as open gaps:

- The repository has a monorepo-style structure with `apps/web`, `apps/segmentation-saliva` and `apps/segmentation-blood`.
- Frontend API base URL is no longer hardcoded in Vue components.
- `apps/web/Frontend/src/services/apiClient.js` exists.
- `apps/web/Frontend/.env.example` exists.
- `apps/web/Backend/.env.example` exists.
- Django settings use environment variables through `django-environ`.
- Segmentation service URLs are configured in `SEGMENTATION_SERVICES`.
- Django HTTP clients for saliva and blood segmentation exist in `api/services/segmentation/`.

## Gap 0: Minimal technical validation is still pending

Before functional integration, the current workspace still needs a minimal validation pass:

- backend Django dependency install, checks and focused tests;
- frontend dependency install and build;
- saliva microservice startup/endpoint smoke test;
- blood microservice startup/endpoint smoke test;
- basic documentation of runtime commands and environment variables.

This is separate from implementing new functionality.

## Gap 1: Django endpoint does not trigger segmentation

Existing microservice endpoints:

```text
Segmentacion_web: POST /segmentar
segmentacion_sangre: POST /api/v1/segmentar
```

Django clients now exist, but no public Django endpoint uses them yet.

Missing endpoint:

```http
POST /api/muestras/{id}/segmentar/
```

Required flow:

```text
Sample uploaded
  -> Django loads sample
  -> Django determines sample type
  -> Django calls the correct segmentation client
  -> Django stores returned polygons/counts
  -> Frontend displays segmentation result
```

## Gap 2: Backend only models saliva samples

Current model:

```text
MuestraSaliva
```

Required model direction:

```text
ImagenMuestra
- sample_type: SALIVA | SANGRE
```

The current upload flow posts to `/api/muestras/` and maps to `MuestraSaliva`, so blood is not represented in Django.

## Gap 3: Frontend does not let user select sample type

The UI currently uploads images through `POST /api/muestras/`.

Missing:

- sample type selector;
- API payload support for sample type;
- filtering/display behavior for saliva versus blood samples.

This should wait until the backend can represent sample type.

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

Current backend models store:

- counts in `ResultadoAnalisis`;
- mask image files in `AnalisisMascara`.

They do not store editable polygons or raw segmentation output.

## Gap 5: No validation workflow

Documents describe interactive validation and correction by a specialist.

Current code lacks:

- validated flag;
- reviewer;
- edited object persistence;
- revision history;
- undo/redo persistence;
- distinction between automatic and manual result.

## Gap 6: Characterization missing from implementation

The academic/domain documents describe calculation of:

- area;
- perimeter;
- roundness/circularity;
- centroid;
- mean intensity;
- distance nucleus-micronucleus;
- area fraction;
- intensity fraction.

The frontend has a placeholder for characterization, and the backend has no characterization model or endpoint.

## Gap 7: Report generation missing from implementation

The documents describe PDF and CSV generation.

Current code has UI buttons for export, but no backend report generation or file model has been implemented.

## Gap 8: Authentication/roles not implemented as described

Documents describe controlled doctor access.

Current Django project includes default Django auth apps but no observed custom endpoints or doctor model.

Missing:

- doctor profile;
- admin-created doctor workflow;
- login endpoint;
- token/session API;
- route protection;
- frontend auth state.

## Gap 9: Health/readiness endpoints are incomplete

The backend has a simple `saludo` function in `api.views`, but no health route is registered in `api/urls.py`.

Health/readiness endpoints for Django and both FastAPI services should be formalized later.

## Gap 9.1: Deployment documentation is incomplete

There is no single validated runbook covering:

- how to run Django;
- how to run Vue/Vite;
- how to run both FastAPI segmentation services;
- required environment variables per service;
- expected ports;
- local smoke-test commands;
- production/deployment assumptions.

## Gap 10: Duplicated code in microservices

Both microservices contain similar structures:

```text
app/routers/segmentacion.py
app/services/segmentador.py
app/utils/poligonos.py
segmentacion_core/cellpose/
```

Recommendation: do not merge them yet. First make Django orchestration work, then consider extracting shared schemas/utilities.

## Gap 11: API contracts are implicit

There is no shared schema package or contract document enforced across Django, frontend and microservices.

Important fields to preserve:

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
Caso clinico
Muestra
Segmentacion
Caracterizacion
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

Recommendation: define canonical names before adding new models, but avoid mass renaming in the next integration step.
