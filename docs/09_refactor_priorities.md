# 09 - Refactor Priorities

## Priority Model

Use four refactor phases:

```text
Phase 0: Stabilize
Phase 1: Integrate
Phase 2: Generalize
Phase 3: Extend
```

## Phase 0 - Stabilize Configuration and Baseline

### Goals

- Make the project reproducible.
- Avoid leaking secrets.
- Give Codex clear execution commands.

### Tasks

1. Add `.env.example`.
2. Move Django settings to environment variables.
3. Move frontend API URL to `VITE_API_BASE_URL`.
4. Add README execution instructions per service.
5. Add health endpoints to microservices.
6. Add minimal smoke tests.

### Deliverables

```text
.env.example
README.md
docs/development_setup.md
```

## Phase 1 - Integrate Segmentation Services

### Goals

- Django should orchestrate segmentation.
- Frontend should call Django, not microservices directly.

### Tasks

1. Add service clients in Django:

```text
api/clients/saliva_segmentation_client.py
api/clients/blood_segmentation_client.py
```

2. Add backend endpoint:

```http
POST /api/muestras/{id}/segmentar/
```

3. Persist segmentation response JSON.
4. Return segmentation status and counts to frontend.
5. Add error handling for unavailable microservices.

### Deliverables

```text
SegmentationClient
SegmentationResult model
Segment sample endpoint
```

## Phase 2 - Generalize Samples and Domain Model

### Goals

- Support saliva and blood in one coherent model.
- Reduce duplicated domain structures.

### Tasks

1. Replace or extend `MuestraSaliva` with `ImagenMuestra`.
2. Add `tipo_muestra` enum:

```text
SALIVA
BLOOD
```

3. Refactor upload frontend to select sample type.
4. Add migration strategy.
5. Align model names.

### Deliverables

```text
ImagenMuestra model
Sample type selection UI
Migration plan
```

## Phase 3 - Validation, Characterization and Reports

### Goals

- Implement the workflow described in SICAM documents.

### Tasks

1. Add segmentation editor persistence.
2. Add validation status.
3. Add characterization calculation endpoint.
4. Add CSV export.
5. Add PDF report generation.

### Deliverables

```text
Validated segmentation flow
Characterization module
CSV/PDF export
```

## High-Impact Low-Risk Refactors

These are good first tasks for Codex:

### 1. Centralize frontend API client

Create:

```text
src/services/apiClient.js
```

Replace all hardcoded Axios calls.

### 2. Add backend environment settings

Use:

```python
os.environ.get(...)
```

or `django-environ`.

### 3. Add Pydantic response models to microservices

Formalize:

```text
PolygonObject
SegmentationResponse
```

### 4. Add `/health` endpoints

For Django and both FastAPI services.

### 5. Add sample type enum

Even before replacing `MuestraSaliva`, introduce canonical sample type values.

## Refactors to Avoid Initially

Do not start with:

- Full architecture rewrite.
- Replacing Vue components with a new UI framework.
- Rewriting Cellpose logic.
- Merging both microservices before integration works.
- Changing all model names at once.
- Introducing Celery before a synchronous orchestration endpoint exists.

## Suggested First Codex Prompt

```text
You are refactoring the SICAM Django backend.
Read docs/01_repository_inventory.md through docs/10_codex_master_context.md first.

Task:
1. Add environment-based settings for SECRET_KEY, DEBUG, ALLOWED_HOSTS, database credentials and CORS.
2. Preserve current behavior in development.
3. Create .env.example.
4. Do not change models or endpoints.
5. Show a summary of changed files.
```

## Suggested Second Codex Prompt

```text
You are refactoring the SICAM Vue frontend.
Read docs/03_frontend_vue_inventory.md and docs/10_codex_master_context.md first.

Task:
1. Create src/services/apiClient.js using VITE_API_BASE_URL.
2. Replace hardcoded http://127.0.0.1:8000 references in components.
3. Preserve existing UI behavior.
4. Do not introduce Vue Router or Pinia yet.
```
