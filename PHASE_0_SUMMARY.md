# Phase 0 - Configuration and Repository Sanitation Summary

**Date:** June 24-25, 2026
**Scope:** repository baseline, Django configuration, frontend API configuration
**Status:** Completed for baseline sanitation; integration work remains pending.

## Purpose

Phase 0 stabilized the current SICAM refactor workspace without changing Django models, existing endpoints, or segmentation logic.

This phase should be read as technical sanitation, not functional integration of the three source repositories.

It also does not certify that all services build, start or pass tests in the current machine. That validation remains a separate pending step.

## Completed Work

### Repository sanitation

- Removed generated/local files detected in the workspace:
  - `__pycache__/`
  - `*.pyc`
  - `.pytest_cache/`
  - `db.sqlite3`
  - `debug.log`
  - temporary files matching the configured patterns
- Updated `.gitignore` for Python, Django, SQLite databases, logs, Node/Vite artifacts, local env files and temporary files.

### Backend Django configuration

`apps/web/Backend/config/settings.py` now reads configuration from environment variables through `django-environ`.

Externalized or configurable values include:

- `SECRET_KEY`
- `DEBUG`
- `ALLOWED_HOSTS`
- database settings
- `CORS_ALLOWED_ORIGINS`
- `LANGUAGE_CODE`
- `TIME_ZONE`
- segmentation service URLs and timeouts

`apps/web/Backend/.env.example` exists and documents local defaults.

### Frontend Vue configuration

The frontend no longer hardcodes the Django API base URL in Vue components.

Current state:

- `apps/web/Frontend/src/services/apiClient.js` centralizes Axios.
- `apiClient` uses `import.meta.env.VITE_API_BASE_URL`.
- `apps/web/Frontend/.env.example` exists.
- Vue components call relative API paths such as `/api/pacientes/` through `apiClient`.

## Existing Django Endpoints Preserved

```text
GET/POST /api/pacientes/
GET      /api/pacientes/{id}/
GET      /api/pacientes/{id}/casos/

GET/POST /api/casos/
GET      /api/casos/{id}/
GET      /api/casos/{id}/analisis/

GET/POST /api/analisis/
GET      /api/analisis/{id}/
POST     /api/analisis/{id}/cambiar_estado/

GET/POST /api/muestras/
GET      /api/muestras/{id}/
```

No model, serializer, viewset, router, endpoint or migration was intentionally changed during this sanitation pass.

## Important Clarification

Some earlier notes mentioned a health endpoint. In the current checked state, `api.views.saludo` exists, but no `/api/health/` route is registered in `api/urls.py`.

Treat `/api/health/` as pending unless a later change adds the route.

## Environment Variables

### Backend

See `apps/web/Backend/.env.example`.

Key variables:

```env
SECRET_KEY=django-insecure-change-this-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000
SALIVA_SEGMENTATION_SERVICE_URL=http://localhost:8001
SALIVA_SERVICE_TIMEOUT=30
BLOOD_SEGMENTATION_SERVICE_URL=http://localhost:8002
BLOOD_SERVICE_TIMEOUT=30
LANGUAGE_CODE=es-mx
TIME_ZONE=America/Mexico_City
```

SQLite is the local default unless database variables are changed.

### Frontend

See `apps/web/Frontend/.env.example`.

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## Validation Performed

- Confirmed no hardcoded `http://127.0.0.1:8000` remains in `apps/web/Frontend/src`.
- Confirmed generated/local files from the sanitation list were removed.
- Confirmed `src/services/apiClient.js` parses with `node --check`.
- Attempted frontend build; it could not run because `node_modules`/`vite` were not installed locally.

## Still Pending

- Run minimal technical validation for backend, frontend and both microservices.
- Install frontend dependencies and run `npm run build`.
- Run Django checks/tests after backend dependencies are installed.
- Start or smoke-test both FastAPI segmentation services.
- Add a routed health endpoint if desired.
- Integrate segmentation clients into a Django endpoint.
- Persist segmentation JSON.
- Generalize `MuestraSaliva` to a broader `ImagenMuestra`.
- Implement validation, characterization and reports.
- Document deployment commands and runtime requirements.
