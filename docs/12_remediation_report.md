# 12 - Minimal Remediation Report

## Scope

Remediation date: 2026-06-26

This iteration addressed configuration, dependency and test issues found in `docs/11_validation_report.md`.

No Django models, API endpoints, frontend UI, business logic, segmentation algorithms or folder structure were changed.

## Files Changed

```text
apps/web/Backend/requirements.txt
apps/web/Backend/config/settings.py
apps/web/Backend/pytest.ini
apps/web/Backend/api/services/segmentation/tests.py
apps/segmentation-saliva/requirements.txt
docs/12_remediation_report.md
```

Note: the root Git repository represents some `apps/` paths as gitlinks, so `git status` from the root may not show file-level changes inside those paths.

## Remediations Applied

### 1. Django version vs Python version mismatch

Problem:

```text
apps/web/Backend/requirements.txt pinned Django==6.0.0.
The intended conda env uses Python 3.10.20.
Django 6 requires Python >=3.12.
```

Change:

```text
Django==5.0.1
django-cors-headers==4.3.1
Pillow==10.2.0
pytest==7.4.4
pytest-django==4.7.0
```

Result:

```text
Backend requirements install successfully in C:\Users\israe\miniconda3\envs\sicam.
```

### 2. `django-environ` / `SECRET_KEY` interpolation issue

Problem:

```text
django-environ==0.11.0 is yanked and interpolated `$t9` in the default SECRET_KEY.
```

Changes:

```text
django-environ==0.12.0
SECRET_KEY default changed to a value without `$`.
```

Result:

```text
python manage.py check no longer requires a temporary SECRET_KEY override.
```

### 3. pytest Django settings configuration

Problem:

```text
pytest did not know DJANGO_SETTINGS_MODULE unless passed manually.
```

Change:

```text
apps/web/Backend/pytest.ini
```

Content:

```ini
[pytest]
DJANGO_SETTINGS_MODULE = config.settings
python_files = tests.py test_*.py *_tests.py
```

Result:

```text
pytest uses config.settings from pytest.ini.
```

### 4. Segmentation client test failures

Problem:

The factory tests patched:

```python
django.conf.settings
```

But `factory.py` imports `settings` directly:

```python
from django.conf import settings
```

So the tests did not patch the object actually used by `get_segmentation_client`.

Change:

```python
@patch('api.services.segmentation.factory.settings')
```

Result:

```text
api/services/segmentation/tests.py passes.
```

### 5. Missing dependency specification for saliva microservice

Problem:

```text
apps/segmentation-saliva had no requirements.txt or pyproject.toml.
```

Change:

```text
apps/segmentation-saliva/requirements.txt
```

Included lightweight/runtime dependencies:

```text
fastapi
uvicorn[standard]
python-multipart
numpy
opencv-python-headless
matplotlib
scikit-image
scikit-learn
```

Intentional exclusion:

```text
cellpose
```

Cellpose/model dependencies must be provisioned explicitly to avoid large downloads or model setup during basic validation.

### 6. `node_modules` and `dist`

Current ignore status:

```text
.gitignore includes node_modules/ and dist/.
apps/web/Frontend/.gitignore also includes node_modules and dist.
```

No additional ignore change was required.

Root `git check-ignore` cannot evaluate `apps/web/Frontend/node_modules` because `apps/web` is represented as a gitlink in the root repository.

### 7. Microservice validation without loading Cellpose models

No microservice was started.

Safe validation used:

```text
python -m py_compile ...
import lightweight dependencies
import blood main.app without executing lifespan
```

Still avoided:

```text
uvicorn app.main:app
actual /segmentar requests
Cellpose model loading
large model or dataset downloads
```

## Commands Executed

### Backend dependency install

```powershell
& "C:\Users\israe\miniconda3\envs\sicam\python.exe" -m pip install -r requirements.txt
```

Result:

```text
Successfully installed/confirmed backend dependencies.
django-environ upgraded to 0.12.0.
```

### Backend checks

```powershell
& "C:\Users\israe\miniconda3\envs\sicam\python.exe" manage.py check
```

Result:

```text
System check identified no issues (0 silenced).
```

```powershell
& "C:\Users\israe\miniconda3\envs\sicam\python.exe" manage.py test
```

Result:

```text
Found 0 test(s).
System check identified no issues (0 silenced).
Ran 0 tests in 0.000s
OK
```

```powershell
& "C:\Users\israe\miniconda3\envs\sicam\python.exe" -m pytest
```

Result:

```text
20 collected
18 passed
2 skipped
```

### Saliva dependency install

```powershell
& "C:\Users\israe\miniconda3\envs\sicam\python.exe" -m pip install -r requirements.txt
```

Result:

```text
Lightweight saliva dependencies installed/confirmed.
Cellpose intentionally not installed.
```

### Microservice lightweight checks

```powershell
& "C:\Users\israe\miniconda3\envs\sicam\python.exe" -c "import fastapi, uvicorn, numpy, cv2, skimage, sklearn, matplotlib; print('saliva lightweight deps import ok')"
```

Result:

```text
saliva lightweight deps import ok
```

```powershell
& "C:\Users\israe\miniconda3\envs\sicam\python.exe" -c "import importlib.util; print(importlib.util.find_spec('cellpose'))"
```

Result:

```text
None
```

```powershell
& "C:\Users\israe\miniconda3\envs\sicam\python.exe" -m py_compile app/main.py app/routers/segmentacion.py app/services/segmentador.py app/utils/poligonos.py
```

Result:

```text
Passed for apps/segmentation-saliva.
```

```powershell
& "C:\Users\israe\miniconda3\envs\sicam\python.exe" -m py_compile main.py app/routers/segmentacion.py app/services/segmentador.py app/utils/poligonos.py segmentacion_core/sicam_master.py
```

Result:

```text
Passed for apps/segmentation-blood.
```

### Frontend build

```powershell
cmd /c npm run build
```

Result:

```text
vite v7.3.0 building client environment for production...
70 modules transformed.
built successfully.
```

## Remaining Warnings

- PowerShell still reports profile script execution restrictions during escalated commands.
- `manage.py test` finds `0` Django tests.
- `cellpose` is still not installed in the `sicam` environment.
- Microservices are still not started during validation because startup can load Cellpose models.
- Root Git status may not expose nested `apps/` file changes due gitlink layout.

## Final Validation Summary

```text
Backend manage.py check: PASS
Backend manage.py test: PASS, 0 tests discovered
Backend pytest: PASS, 18 passed / 2 skipped
Frontend npm run build: PASS
Saliva lightweight dependency import: PASS
Saliva py_compile: PASS
Blood py_compile: PASS
Cellpose installed: NO
Microservices started: NO, intentionally avoided
```

## Recommended Next Iteration

1. Decide how to provision `cellpose` and local model assets without automatic large downloads.
2. Add a documented lightweight health/startup mode for both microservices that does not preload models.
3. Add real Django tests for the current API endpoints.
4. Rerun validation after Cellpose/runtime provisioning.
5. Then proceed to implement `POST /api/muestras/{id}/segmentar/`.
