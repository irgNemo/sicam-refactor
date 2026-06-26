# 09 - Refactor Priorities

## Priority Model

Use four practical refactor phases:

```text
Phase 0: Stabilize
Phase 1: Integrate
Phase 2: Generalize
Phase 3: Extend
```

## Current Phase Status

### Phase 0 - Stabilize

Status: mostly completed for repository/configuration sanitation.

Done:

- `.gitignore` cleaned up.
- Generated/local files removed.
- Backend `.env.example` exists.
- Django settings use environment variables.
- Frontend `.env.example` exists.
- Frontend API base URL moved to `VITE_API_BASE_URL`.
- Frontend Axios calls centralized in `src/services/apiClient.js`.

Still useful in Phase 0 follow-up:

- Install dependencies in the active environment and run builds/tests.
- Add routed health/readiness endpoints.
- Add minimal smoke tests.
- Document local run/deployment commands for all services.

### Phase 1 - Integrate Segmentation Services

Status: partially completed.

Done:

- Django service clients exist:

```text
apps/web/Backend/api/services/segmentation/
├── base_client.py
├── saliva_client.py
├── blood_client.py
├── exceptions.py
├── factory.py
├── tests.py
└── USAGE.md
```

Still pending:

1. Add backend endpoint:

```http
POST /api/muestras/{id}/segmentar/
```

2. Use `segment_image(...)` from `api.services.segmentation`.
3. Persist segmentation response JSON.
4. Return segmentation status and counts to frontend.
5. Add API-level error handling for unavailable microservices.

Recommended deliverables:

```text
ResultadoSegmentacion model or equivalent JSON persistence
POST /api/muestras/{id}/segmentar/
API response contract for segmentation status/result
```

## Phase 2 - Generalize Samples and Domain Model

Status: pending.

Goals:

- Support saliva and blood in one coherent model.
- Reduce duplicated domain structures.

Tasks:

1. Replace or extend `MuestraSaliva` with `ImagenMuestra`.
2. Add canonical sample type values:

```text
SALIVA
SANGRE
```

3. Refactor upload frontend to select sample type.
4. Add a migration strategy.
5. Align serializer/API names without breaking existing endpoints prematurely.

Deliverables:

```text
ImagenMuestra model or compatibility layer
Sample type selection UI
Migration plan
Backward-compatible API strategy
```

## Phase 3 - Validation, Characterization and Reports

Status: pending.

Goals:

- Implement the workflow described in SICAM documents.

Tasks:

1. Add segmentation editor persistence.
2. Add validation status.
3. Add reviewer/audit metadata.
4. Add characterization calculation endpoint.
5. Add CSV export.
6. Add PDF report generation.

Deliverables:

```text
Validated segmentation flow
Characterization module
CSV/PDF export
```

## High-Impact Low-Risk Next Work

These are good next tasks for Codex:

### 1. Run minimal technical validation

Before adding functional integration, validate the current baseline:

```text
Backend Django: install dependencies, run manage.py check, run focused tests
Frontend Vue: install dependencies, run npm run build
Saliva service: start service and smoke-test POST /segmentar
Blood service: start service and smoke-test POST /api/v1/segmentar
```

Document any failures as environment/setup issues or code issues.

### 2. Add Django segmentation endpoint

Add a narrow DRF action:

```http
POST /api/muestras/{id}/segmentar/
```

Constraints:

- Use existing segmentation clients.
- Do not change existing endpoints.
- Do not generalize models in the same step unless explicitly requested.
- Return clear API errors for timeout/connection/invalid response.

### 3. Add segmentation JSON persistence

Introduce a migration-backed persistence model or field for raw `objetos` JSON.

Do not collapse this into `ResultadoAnalisis` without a clear migration plan.

### 4. Add sample type plan

Before changing models, document how `MuestraSaliva` will evolve into `ImagenMuestra`.

### 5. Add smoke tests

Cover:

- existing API routes;
- frontend build after dependency install;
- segmentation client tests with mocked HTTP;
- future segmentation endpoint.

## Refactors to Avoid Initially

Do not start with:

- full architecture rewrite;
- replacing Vue components with a new UI framework;
- rewriting Cellpose logic;
- merging both microservices before Django orchestration works;
- changing all model names at once;
- introducing Celery before a synchronous orchestration endpoint exists.

## Suggested Next Codex Prompt

```text
You are validating the SICAM refactored repository.

Task:
1. Do not modify source code.
2. Install/use existing dependencies only if approved.
3. Run minimal backend, frontend and microservice checks.
4. Report exact commands, failures and next fixes.
5. Do not add functional changes.
```

## Suggested Functional Prompt After Validation

```text
You are refactoring the SICAM Django backend.

Task:
1. Add POST /api/muestras/{id}/segmentar/.
2. Use api.services.segmentation.segment_image().
3. Preserve existing endpoints.
4. Do not rename models.
5. Persist or return segmentation JSON only as explicitly requested.
6. Add focused tests.
```

## Later Prompt

```text
Plan the migration from MuestraSaliva to ImagenMuestra.
Do not modify models yet.
Document backward compatibility, data migration, endpoint impact and frontend changes.
```
