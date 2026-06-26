# Phase 2 - Segmentation Microservice Clients Summary

**Date:** June 24-25, 2026
**Scope:** Django service clients for segmentation microservices
**Status:** Completed as infrastructure; not yet wired into public Django endpoints.

## Overview

This phase added a Django-side service layer for calling the existing FastAPI segmentation microservices.

The clients live in:

```text
apps/web/Backend/api/services/segmentation/
```

They provide:

- a shared abstract client;
- saliva and blood clients;
- custom exceptions;
- a factory/helper API;
- response validation;
- unit-test examples;
- usage documentation.

## Files Present

```text
api/services/
├── __init__.py
└── segmentation/
    ├── __init__.py
    ├── base_client.py
    ├── saliva_client.py
    ├── blood_client.py
    ├── exceptions.py
    ├── factory.py
    ├── tests.py
    └── USAGE.md
```

## Supported Microservices

### Saliva

Configured from:

```env
SALIVA_SEGMENTATION_SERVICE_URL=http://localhost:8001
SALIVA_SERVICE_TIMEOUT=30
```

Client endpoint:

```http
POST /segmentar
```

Expected response contract:

```json
{
  "objetos": [
    {
      "id": 1,
      "tipo": "membrana",
      "puntos": [[10, 20], [12, 25]]
    }
  ]
}
```

Expected object types include:

```text
membrana
nucleo
micronucleo
```

### Blood

Configured from:

```env
BLOOD_SEGMENTATION_SERVICE_URL=http://localhost:8002
BLOOD_SERVICE_TIMEOUT=30
```

Client endpoint:

```http
POST /api/v1/segmentar
```

Expected object types include:

```text
membrana
micronucleo
```

## Public Client API

```python
from api.services.segmentation import get_segmentation_client, segment_image

client = get_segmentation_client("SALIVA")
result = segment_image("SALIVA", image_bytes, filename="sample.jpg")
```

Supported sample type keys in the current factory:

```text
SALIVA
SANGRE
```

## Error Handling

The client layer defines specific exceptions:

```text
SegmentationServiceError
SegmentationTimeoutError
SegmentationConnectionError
InvalidSegmentationResponseError
```

These are infrastructure exceptions only. They are not yet mapped to Django API responses because no public segmentation endpoint has been added.

## Current Boundary

This phase did **not** change:

- Django models;
- migrations;
- existing routers;
- existing endpoints;
- frontend behavior;
- segmentation algorithms inside the FastAPI services.

This phase did **not** add:

```http
POST /api/muestras/{id}/segmentar/
```

## Pending Integration

The next backend integration step is to wire the client layer into a Django action or service flow:

```text
Uploaded sample
  -> Django determines sample type
  -> Django calls segment_image(...)
  -> Django stores returned objetos JSON
  -> Django returns status/result to frontend
```

Still pending:

- create `POST /api/muestras/{id}/segmentar/`;
- persist raw segmentation JSON;
- store counts derived from segmentation;
- support saliva and blood through a generalized `ImagenMuestra` model;
- expose validation/editing workflows;
- implement characterization and reports.

## Validation Status

The files and tests exist in the repository, but a full test run should be repeated after dependencies are installed in the current environment.

This phase should not be interpreted as proof that the microservices are reachable, that Django can call them in a running environment, or that a frontend flow exists. It only adds the Django client layer needed for that future integration.

Suggested commands:

```bash
cd apps/web/Backend
pytest api/services/segmentation/tests.py
```

## Bottom Line

Segmentation clients exist and are ready to be integrated, but SICAM does not yet execute segmentation through a Django API endpoint or persist segmentation JSON.

Recommended next iteration before functional changes: run minimal technical validation of Django, Vue and both FastAPI services, then add `POST /api/muestras/{id}/segmentar/` with focused tests.
