# Sprint 1C - Saliva Microservice Integrity Verification

## Fecha de validacion

2026-06-26 21:04:54 -06:00

## Alcance

Validacion tecnica liviana del microservicio de segmentacion de saliva despues de la conversion a monorepo.

Directorio de trabajo validado:

```text
apps/segmentation-saliva
```

No se ejecuto segmentacion real, no se cargaron modelos pesados, no se descargaron modelos y no se modifico codigo fuente.

## Referencia Git

- Rama: `master`
- Commit: `6e1a39e`

## Entorno Python detectado

Python activo inicialmente en la terminal:

```text
C:\Python314\python.exe
3.14.6
```

Entorno usado para la validacion efectiva:

```text
C:\Users\israe\miniconda3\envs\sicam\python.exe
3.10.20
```

## Archivo principal del servicio

Archivo principal FastAPI:

```text
app/main.py
```

Contenido relevante:

```python
from fastapi import FastAPI
from app.routers.segmentacion import router as segmentacion_router

app = FastAPI()

app.include_router(segmentacion_router)
```

## Comando esperado para levantar el servicio

Segun `README.md`, el comando esperado en desarrollo es:

```powershell
python -m uvicorn app.main:app --reload --port 8001
```

Para esta validacion no se levanto el servicio, porque importar `app.main` conduce al pipeline de segmentacion y puede intentar preparar dependencias/modelos.

## Dependencias principales

Dependencias declaradas en `requirements.txt`:

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

El archivo declara explicitamente que Cellpose/model dependencies no se instalan automaticamente para evitar descargas pesadas.

## Modelos o pesos externos

`segmentacion_core/membranas_500_125` esta presente en disco:

```text
segmentacion_core/membranas_500_125
```

Tamano observado:

```text
26551763 bytes
```

Estado Git:

```text
.gitignore:105:membranas_* segmentacion_core/membranas_500_125
```

Conclusion: el modelo/artefacto esta presente localmente y correctamente ignorado. No se agrego a Git.

## Comandos ejecutados

### Revision de estructura y documentacion

```powershell
Get-Content README.md
Get-Content requirements.txt
rg --files
Select-String -Path docs/13_architecture_baseline.md -Pattern 'segmentation-saliva|membranas_500_125|cellpose|modelos externos|Sprint 1' -Context 1,2
```

Resultado:

- `README.md` existe y documenta uso de `uvicorn`.
- `requirements.txt` existe.
- La estructura incluye `app/`, `app/routers/`, `app/services/`, `app/utils/` y `segmentacion_core/`.
- `docs/13_architecture_baseline.md` confirma que `membranas_500_125` debe tratarse como artefacto externo no versionado.

### Confirmacion de ubicacion y entorno

```powershell
Get-Location
python -c "import sys,platform; print(sys.executable); print(platform.python_version())"
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -c "import sys,platform; print(sys.executable); print(platform.python_version())"
```

Resultado:

- Ubicacion confirmada: `apps/segmentation-saliva`.
- Python global: `C:\Python314\python.exe`, `3.14.6`.
- Python usado: `C:\Users\israe\miniconda3\envs\sicam\python.exe`, `3.10.20`.

### Verificacion de `membranas_500_125`

```powershell
Test-Path segmentacion_core/membranas_500_125
git check-ignore -v segmentacion_core/membranas_500_125
Get-ChildItem segmentacion_core/membranas_500_125 -Force
```

Resultado:

- `segmentacion_core/membranas_500_125`: presente.
- Ignorado por `.gitignore`.
- No fue agregado a Git.

### Sintaxis Python

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -m compileall -q app segmentacion_core
```

Resultado dentro del sandbox:

```text
FAIL
PermissionError: [WinError 5] Acceso denegado: 'segmentacion_core\\model\\__pycache__\\micronuclei.cpython-310.pyc...'
```

Clasificacion: permisos/escritura de cache.

Resultado fuera del sandbox:

```text
PASS
```

Conclusion: no se detectaron errores de sintaxis.

### Uvicorn

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -m uvicorn --version
```

Resultado:

```text
Running uvicorn 0.49.0 with CPython 3.10.20 on Windows
```

Conclusion: PASS.

### Imports base

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -c "import fastapi, uvicorn, numpy, cv2, matplotlib, skimage, sklearn; print('imports base ok')"
```

Resultado:

```text
imports base ok
```

Conclusion: PASS.

### Imports livianos internos

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -c "import app.utils.poligonos; import segmentacion_core.model.cytoplasm; import segmentacion_core.model.nuclei; import segmentacion_core.model.micronuclei; import segmentacion_core.seg_nucleos; import segmentacion_core.seg_micronucleos; print('imports livianos ok')"
```

Resultado:

```text
imports livianos ok
```

Conclusion: PASS.

### Import controlado de `seg_membranas`

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -c "import segmentacion_core.seg_membranas; print('seg_membranas import ok')"
```

Resultado:

```text
ModuleNotFoundError: No module named 'tqdm'
```

Conclusion: FAIL.

Clasificacion: dependencia faltante.

## Dependencias faltantes o no instaladas detectadas

Se inspeccionaron imports del codigo vendorizado de `cellpose/` y se verifico disponibilidad en el entorno `sicam`.

Resultado observado:

```text
tqdm=False
torch=False
natsort=False
imageio=True
roifile=False
scipy=True
numba=False
tifffile=True
mxnet=False
fastapi=True
uvicorn=True
python_multipart=True
```

Bloqueo inmediato:

- `tqdm` falta y bloquea `import segmentacion_core.seg_membranas`.

Posibles dependencias adicionales a resolver en una iteracion futura:

- `natsort`
- `numba`
- `torch`
- `roifile`
- `mxnet`, solo si alguna ruta heredada lo requiere realmente.

`torch` y cualquier dependencia asociada a modelos deben tratarse como dependencia pesada o especial antes de instalarse.

## Errores o advertencias

- `compileall` fallo dentro del sandbox por permisos al escribir `__pycache__`, pero paso fuera del sandbox.
- `segmentacion_core.seg_membranas` no puede importarse por falta de `tqdm`.
- `app.main` no se importo intencionalmente porque su cadena de imports llega a `app.services.segmentador`, que instancia `SegmentadorMembranas` al importarse.
- `membranas_500_125` esta presente localmente, pero debe seguir ignorado y tratado como modelo/artefacto externo.
- No se valido arranque real del servicio ni endpoint `/segmentar`, porque eso puede cargar modelos y ejecutar inicializacion pesada.

## Cambios realizados

- No se modifico codigo fuente.
- No se modificaron algoritmos de segmentacion.
- No se modifico `cellpose/`.
- No se agregaron ni borraron modelos o pesos.
- No se agrego `membranas_500_125` a Git.
- No se descargaron modelos.
- No se modifico backend Django.
- No se modifico frontend.
- No se modifico el microservicio de sangre.
- No se agregaron dependencias.
- Se creo este reporte documental: `docs/16_sprint_1c_saliva_microservice_validation.md`.

## Conclusion

FAIL

El microservicio de saliva conserva una estructura coherente, cuenta con archivo principal FastAPI y pasa validaciones livianas de sintaxis e imports parciales. Sin embargo, no queda validado completamente porque `segmentacion_core.seg_membranas` falla al importarse por una dependencia faltante: `tqdm`.

## Correccion minima propuesta

En una siguiente iteracion, revisar y completar `apps/segmentation-saliva/requirements.txt` con dependencias runtime necesarias para el `cellpose/` vendorizado, empezando por:

- `tqdm`
- `natsort`
- `numba`

Antes de agregar o instalar `torch`, Cellpose externo u otras dependencias pesadas, definir una decision explicita para evitar descargas o cambios de entorno no controlados.

## Siguiente paso recomendado

Resolver dependencias livianas faltantes del microservicio de saliva con aprobacion explicita y repetir Sprint 1C. Despues continuar con Sprint 1D para el microservicio de sangre.
