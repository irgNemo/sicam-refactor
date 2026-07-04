# Sprint 1D - Blood Microservice Integrity Verification

## Fecha de validacion

2026-07-01 16:49:46 -06:00

## Alcance

Validacion tecnica liviana del microservicio de segmentacion de sangre despues de la conversion a monorepo.

Directorio de trabajo validado:

```text
apps/segmentation-blood
```

No se ejecuto segmentacion real, no se levanto el servicio, no se cargaron modelos pesados y no se modifico codigo fuente.

## Referencia Git

- Rama: `master`
- Commit: `139db10`

## Entorno Python detectado

Entorno usado para la validacion:

```text
C:\Users\israe\miniconda3\envs\sicam\python.exe
Python 3.10.20
```

Versiones relevantes disponibles en el entorno:

```text
torch=2.12.1+cpu
cuda=False
natsort=8.4.0
numba=0.65.1
```

## Archivo principal del servicio

Archivo principal FastAPI:

```text
main.py
```

`main.py` define `app = FastAPI(...)` y registra el router de segmentacion con:

```python
app.include_router(segmentacion_router, prefix="/api/v1")
```

Tambien define un `lifespan` que precarga el modelo Cellpose al arrancar el servidor mediante `_obtener_modelo()`.

## Comando esperado para levantar el servicio

Comando inferido por la estructura FastAPI del proyecto:

```powershell
python -m uvicorn main:app --reload --port 8002
```

Este comando no se ejecuto durante Sprint 1D porque arrancar el servicio ejecutaria el `lifespan` y podria cargar Cellpose.

## Dependencias principales

Dependencias declaradas en `requirements.txt`:

```text
fastapi
uvicorn[standard]
python-multipart
numpy
opencv-python-headless
scikit-image
scikit-learn
```

El archivo tambien indica:

```text
# cellpose: instalar con --> pip install -e ./cellpose
```

El codigo fuente vendorizado de `cellpose/` esta presente bajo:

```text
segmentacion_core/cellpose/
```

## Modelos o pesos externos

No se detectaron modelos o pesos pesados versionables dentro de `apps/segmentation-blood` durante esta validacion.

El modelo Cellpose se obtiene de forma lazy en:

```text
segmentacion_core/sicam_master.py
```

Funcion relevante:

```text
_obtener_modelo()
```

Esta funcion no se ejecuto durante la validacion.

## Comandos ejecutados

### Revision de estructura y documentacion

```powershell
if (Test-Path README.md) { Get-Content README.md } else { 'README.md not found' }
Get-Content requirements.txt
rg --files
Select-String -Path docs/13_architecture_baseline.md -Pattern 'segmentation-blood|cellpose|modelos externos|Sprint 1|pesos|artefactos' -Context 1,2
```

Resultado:

- `README.md` no existe.
- `requirements.txt` existe.
- La estructura incluye `main.py`, `app/`, `app/routers/`, `app/services/`, `app/utils/` y `segmentacion_core/`.
- La baseline confirma que `apps/segmentation-blood` contiene codigo de segmentacion y que no debe arrancarse si eso implica cargar modelos pesados.

### Revision de archivos de entrada

```powershell
Get-Content main.py
Get-Content app/routers/segmentacion.py
Get-Content app/services/segmentador.py
Get-Content segmentacion_core/sicam_master.py
Get-Content segmentacion_core/dependencies.txt
```

Resultado:

- `main.py` es el punto de entrada FastAPI.
- `app/routers/segmentacion.py` define `POST /api/v1/segmentar`.
- `app/services/segmentador.py` delega en `segmentacion_core.sicam_master.segmentar_desde_bytes`.
- `segmentacion_core/sicam_master.py` usa import lazy de `cellpose` dentro de `_obtener_modelo()`.
- `segmentacion_core/dependencies.txt` lista dependencias historicas adicionales del codigo heredado.

### Confirmacion de ubicacion y entorno

```powershell
Get-Location
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -c "import sys,platform; print(sys.executable); print(platform.python_version())"
git branch --show-current
git rev-parse --short HEAD
```

Resultado:

- Ubicacion confirmada: `apps/segmentation-blood`.
- Python: `C:\Users\israe\miniconda3\envs\sicam\python.exe`, `3.10.20`.
- Rama: `master`.
- Commit: `139db10`.

### Sintaxis Python

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -m compileall -q app segmentacion_core main.py
```

Resultado:

```text
PASS
```

### Imports base

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -c "import fastapi, uvicorn, numpy, cv2, skimage, sklearn; print('imports base ok')"
```

Resultado:

```text
imports base ok
```

Conclusion: PASS.

### Imports livianos internos

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -c "import app.utils.poligonos; import segmentacion_core.sicam_master; print('imports livianos ok')"
```

Resultado:

```text
imports livianos ok
```

Conclusion: PASS.

### Import de `main`

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -c "import main; print('main import ok')"
```

Resultado:

```text
main import ok
```

Conclusion: PASS.

Advertencia: este import no ejecuta el `lifespan` de FastAPI, por lo que no precarga Cellpose.

### Versiones relevantes

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -c "import torch, natsort, numba; print('torch='+torch.__version__); print('cuda='+str(torch.cuda.is_available())); print('natsort='+natsort.__version__); print('numba='+numba.__version__)"
```

Resultado:

```text
torch=2.12.1+cpu
cuda=False
natsort=8.4.0
numba=0.65.1
```

Conclusion: PASS.

## Errores o advertencias

- No existe `README.md` en `apps/segmentation-blood`.
- El comando de arranque no se ejecuto porque activaria el `lifespan` y podria cargar Cellpose.
- No se ejecuto `segmentar_desde_bytes()`.
- No se llamo `_obtener_modelo()`.
- No se ejecuto segmentacion real.
- No se validaron pesos/modelos externos en runtime.
- `__pycache__/` fue generado por las validaciones, pero permanece ignorado.

## Artefactos ignorados

`git status --ignored --short apps/segmentation-blood` reporto caches ignorados:

```text
!! apps/segmentation-blood/__pycache__/
!! apps/segmentation-blood/app/__pycache__/
!! apps/segmentation-blood/app/routers/__pycache__/
!! apps/segmentation-blood/app/services/__pycache__/
!! apps/segmentation-blood/app/utils/__pycache__/
!! apps/segmentation-blood/segmentacion_core/__pycache__/
!! apps/segmentation-blood/segmentacion_core/cellpose/__pycache__/
!! apps/segmentation-blood/segmentacion_core/cellpose/contrib/__pycache__/
```

No se agregaron caches, modelos ni pesos a Git.

## Cambios realizados

- No se modifico codigo fuente.
- No se modificaron algoritmos de segmentacion.
- No se modifico `cellpose/`.
- No se agregaron ni borraron modelos o pesos.
- No se descargaron modelos.
- No se modifico backend Django.
- No se modifico frontend.
- No se modifico el microservicio de saliva.
- No se agregaron dependencias.
- Se creo este reporte documental: `docs/17_sprint_1d_blood_microservice_validation.md`.

## Conclusion

PASS WITH WARNINGS

El microservicio de sangre conserva una estructura coherente, tiene dependencias principales declaradas, pasa verificacion de sintaxis e imports livianos, e importa `main.py` sin ejecutar el `lifespan`.

La validacion queda con advertencias porque no se levanto el servicio, no se cargo Cellpose y no se ejecuto segmentacion real.

## Siguiente paso recomendado

Cerrar Sprint 1D como validacion liviana aprobada con advertencias. La siguiente iteracion recomendada es consolidar el reporte de Sprint 1 completo o continuar con una validacion de integracion controlada sin ejecutar segmentacion pesada.
