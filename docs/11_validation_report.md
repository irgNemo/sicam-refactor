# 11 - Technical Validation Report

## Scope

Validation date: 2026-06-26

This report documents a minimal technical validation of the current refactored SICAM repository.

No source code, Django models, endpoints, segmentation logic or folder structure were changed.

## Environment Used

Conda environment:

```text
C:\Users\israe\miniconda3\envs\sicam
```

Python:

```text
Python 3.10.20
```

Node:

```text
v24.17.0
```

npm:

```text
11.13.0
```

## Initial Repository Status

Command:

```powershell
git status --short
```

Result:

```text
 M .gitignore
 M PHASE_0_SUMMARY.md
 M README.md
 M docs/02_backend_django_inventory.md
 M docs/03_frontend_vue_inventory.md
 M docs/08_integration_gaps.md
 M docs/09_refactor_priorities.md
 M docs/10_codex_master_context.md
?? PHASE_2_SUMMARY.md
```

These changes existed before this validation iteration, except for this new report.

## Backend Django

Path:

```text
apps/web/Backend
```

### Requirements Review

Command:

```powershell
Get-Content apps/web/Backend/requirements.txt
```

Relevant declared dependencies:

```text
Django==6.0.0
djangorestframework==3.14.0
django-cors-headers==4.3.0
django-environ==0.11.0
psycopg2-binary==2.9.9
Pillow==10.0.0
requests==2.31.0
pytest==7.4.0
pytest-django==4.5.2
pytest-cov==4.1.0
```

### Dependency Installation Attempt

Command:

```powershell
& "C:\Users\israe\miniconda3\envs\sicam\python.exe" -m pip install -r requirements.txt
```

Result:

```text
Failed.
Django==6.0.0 requires Python >=3.12.
The SICAM conda env uses Python 3.10.20.
```

Important finding:

```text
requirements.txt is incompatible with the intended Python 3.10 conda env because it pins Django==6.0.0.
```

The env already had Django installed:

```text
Django 5.0.1
```

### Minimal Dependency Fix Installed In Environment

Command:

```powershell
& "C:\Users\israe\miniconda3\envs\sicam\python.exe" -m pip install django-environ==0.11.0
```

Result:

```text
Successfully installed django-environ-0.11.0
```

Warning:

```text
django-environ==0.11.0 is yanked due to an interpolation bug.
```

### `manage.py check`

Command:

```powershell
& "C:\Users\israe\miniconda3\envs\sicam\python.exe" manage.py check
```

Initial result:

```text
Failed.
django.core.exceptions.ImproperlyConfigured:
Environment variable 't9' recursively references itself (eventually)
```

Cause:

`settings.py` has a default `SECRET_KEY` containing `$t9`. `django-environ==0.11.0` tries to interpolate `$t9`, triggering the known interpolation bug.

Retest command with temporary environment variable:

```powershell
$env:SECRET_KEY='validation-secret-key'
& "C:\Users\israe\miniconda3\envs\sicam\python.exe" manage.py check
```

Result:

```text
System check identified no issues (0 silenced).
```

### `manage.py test`

Command:

```powershell
$env:SECRET_KEY='validation-secret-key'
& "C:\Users\israe\miniconda3\envs\sicam\python.exe" manage.py test
```

Result:

```text
Found 0 test(s).
System check identified no issues (0 silenced).
Ran 0 tests in 0.000s
OK
```

### `pytest`

Command:

```powershell
& "C:\Users\israe\miniconda3\envs\sicam\python.exe" -m pytest
```

Result:

```text
No tests ran.
```

Focused command:

```powershell
$env:SECRET_KEY='validation-secret-key'
& "C:\Users\israe\miniconda3\envs\sicam\python.exe" -m pytest api/services/segmentation/tests.py
```

Result:

```text
20 collected
13 passed
5 failed
2 skipped
```

Failure cause:

```text
django.conf.settings was not configured for pytest.
```

Retest command:

```powershell
$env:SECRET_KEY='validation-secret-key'
$env:DJANGO_SETTINGS_MODULE='config.settings'
& "C:\Users\israe\miniconda3\envs\sicam\python.exe" -m pytest api/services/segmentation/tests.py
```

Result:

```text
20 collected
16 passed
2 failed
2 skipped
```

Remaining failures:

- `TestFactory.test_get_segmentation_client_sangre`
- `TestFactory.test_get_segmentation_client_not_found`

Observed causes:

- Test expects `SANGRE` timeout `45`, but returned client has timeout `30`.
- Test expects unknown/unconfigured service to raise `SegmentationServiceError`, but the current factory behavior did not raise under the test mock setup.

No code was changed to fix these.

## Frontend Vue

Path:

```text
apps/web/Frontend
```

### Package Review

Command:

```powershell
Get-Content apps/web/Frontend/package.json
```

Scripts:

```json
{
  "dev": "vite",
  "build": "vite build",
  "preview": "vite preview",
  "lint": "eslint . --fix --cache"
}
```

### Dependency Installation

Command:

```powershell
cmd /c npm install
```

Result:

```text
added 240 packages
```

### Build

Command:

```powershell
cmd /c npm run build
```

Initial sandboxed result:

```text
Failed.
Cannot read directory "../../../../../../..": Acceso denegado.
Could not resolve vite.config.js.
```

Retest outside sandbox:

```powershell
cmd /c npm run build
```

Result:

```text
vite v7.3.0 building client environment for production...
70 modules transformed.
dist/index.html
dist/assets/index-*.css
dist/assets/index-*.js
built successfully
```

Frontend status:

```text
Build passed.
```

Generated artifacts:

```text
apps/web/Frontend/node_modules/
apps/web/Frontend/dist/
```

Both are generated local artifacts and should remain ignored.

## Microservice: Saliva Segmentation

Path:

```text
apps/segmentation-saliva
```

### Runtime Discovery

Files reviewed:

```text
README.md
app/main.py
app/routers/segmentacion.py
app/services/segmentador.py
segmentacion_core/seg_membranas.py
```

README run command:

```powershell
python -m uvicorn app.main:app --reload --port 8001
```

Dependency file status:

```text
No requirements.txt or pyproject.toml found.
```

README mentions manual dependencies:

```text
uvicorn
cellpose
python-multipart
matplotlib
```

### Lightweight Validation

Command:

```powershell
& "C:\Users\israe\miniconda3\envs\sicam\python.exe" -m py_compile app/main.py app/routers/segmentacion.py app/services/segmentador.py app/utils/poligonos.py
```

Result:

```text
Passed.
```

Import/start status:

```text
Not started.
```

Reason:

`app/services/segmentador.py` instantiates `SegmentadorMembranas` at import time. That loads Cellpose/model code immediately:

```python
segmentador_mem = SegmentadorMembranas(
    BASE_DIR / "segmentacion_core" / "membranas_500_125",
    gpu=False
)
```

This is not a lightweight import, so it was not executed during this validation.

Additional observation:

```text
apps/segmentation-saliva/segmentacion_core/cellpose exists.
apps/segmentation-saliva/segmentacion_core/membranas_500_125 exists.
```

## Microservice: Blood Segmentation

Path:

```text
apps/segmentation-blood
```

### Requirements Review

Command:

```powershell
Get-Content apps/segmentation-blood/requirements.txt
```

Declared dependencies:

```text
fastapi
uvicorn[standard]
python-multipart
numpy
opencv-python-headless
scikit-image
scikit-learn
```

Note:

```text
Cellpose is not installed by requirements.txt.
The file comments: "cellpose: instalar con --> pip install -e ./cellpose"
```

### Dependency Installation

Command:

```powershell
& "C:\Users\israe\miniconda3\envs\sicam\python.exe" -m pip install -r requirements.txt
```

Result:

```text
Successfully installed FastAPI/Uvicorn and scientific dependencies declared in requirements.txt.
```

Key installed versions:

```text
fastapi 0.138.1
uvicorn 0.49.0
numpy 2.2.6
opencv-python-headless 4.13.0.92
scikit-image 0.25.2
scikit-learn 1.7.2
```

### Lightweight Validation

Command:

```powershell
& "C:\Users\israe\miniconda3\envs\sicam\python.exe" -c "import fastapi, uvicorn, numpy, cv2, skimage, sklearn; print('declared microservice deps import ok')"
```

Result:

```text
declared microservice deps import ok
```

Command:

```powershell
& "C:\Users\israe\miniconda3\envs\sicam\python.exe" -m py_compile main.py app/routers/segmentacion.py app/services/segmentador.py app/utils/poligonos.py segmentacion_core/sicam_master.py
```

Result:

```text
Passed.
```

Command:

```powershell
& "C:\Users\israe\miniconda3\envs\sicam\python.exe" -c "import main; print(type(main.app).__name__, main.app.title)"
```

Result:

```text
FastAPI Microservicio Segmentacion Sangre
```

Service start status:

```text
Not started.
```

Reason:

`main.py` uses a lifespan hook that preloads Cellpose on server startup:

```python
await run_in_threadpool(_obtener_modelo)
```

Starting Uvicorn would attempt model initialization. That was intentionally avoided.

Additional observation:

```text
cellpose is not installed in the SICAM conda env.
```

## Generated Files Cleanup

`py_compile` generated `__pycache__/` directories in the microservice folders.

They were removed after validation.

Verification:

```powershell
Get-ChildItem -Force -Recurse -Directory -Include __pycache__ apps/segmentation-saliva,apps/segmentation-blood
```

Result:

```text
No remaining __pycache__ directories in the checked microservice paths.
```

## Warnings

- PowerShell reports that profile script execution is disabled:

```text
No se puede cargar ... WindowsPowerShell\profile.ps1 porque la ejecucion de scripts esta deshabilitada.
```

This warning appeared during escalated commands and is an environment/profile warning, not a project code failure.

- `requirements.txt` for backend pins Django 6.0.0, but the intended conda env uses Python 3.10.20.
- `django-environ==0.11.0` is yanked and caused a real interpolation problem with the default `SECRET_KEY`.
- Frontend build only succeeded outside the filesystem sandbox.
- Microservices were not started because startup/import paths may load Cellpose models.

## Changes Made During Validation

No source files were changed.

Environment/local changes:

- Installed `django-environ==0.11.0` into the `sicam` conda env.
- Installed blood microservice dependencies into the `sicam` conda env.
- Ran `npm install` in `apps/web/Frontend`.
- Generated `apps/web/Frontend/dist/` via `npm run build`.
- Removed generated Python `__pycache__/` directories created by `py_compile`.

Repository changes:

- Added this report:

```text
docs/11_validation_report.md
```

## Summary

### Passed

- Frontend dependencies installed.
- Frontend production build passed.
- Backend `manage.py check` passed when `SECRET_KEY` is provided explicitly.
- Backend `manage.py test` passed with zero discovered Django tests when `SECRET_KEY` is provided explicitly.
- Blood microservice declared dependencies import successfully.
- Blood microservice app imports successfully without running lifespan/model preload.
- Saliva and blood microservice files pass syntax compilation.

### Failed / Blocked

- Backend `requirements.txt` cannot be installed as-is in Python 3.10 because `Django==6.0.0` requires Python >=3.12.
- Backend default `SECRET_KEY` fails with `django-environ==0.11.0` due interpolation of `$t9`.
- Segmentation client pytest suite has 2 remaining failures with `DJANGO_SETTINGS_MODULE=config.settings`.
- Saliva microservice cannot be safely imported as a lightweight check because it instantiates the segmenter/model at import time.
- Blood microservice was not started because startup preloads Cellpose.
- Cellpose is not installed in the `sicam` conda env.

## Recommended Next Iteration

1. Decide backend dependency strategy:
   - either use Python >=3.12 for Django 6;
   - or change `requirements.txt` to match Python 3.10 and current Django 5.x.
2. Replace or upgrade `django-environ==0.11.0`, or change the default `SECRET_KEY` to avoid `$` interpolation.
3. Add `pytest.ini` or equivalent pytest configuration for Django settings.
4. Fix segmentation factory tests or factory behavior around `SANGRE` timeout and missing service config.
5. Add a `requirements.txt` or `environment.yml` for `apps/segmentation-saliva`.
6. Decide how Cellpose/model dependencies should be installed and documented without automatic heavy downloads.
7. Add lightweight health endpoints or startup modes for microservices that do not preload models.
8. After these fixes, rerun full validation and then proceed to `POST /api/muestras/{id}/segmentar/`.
