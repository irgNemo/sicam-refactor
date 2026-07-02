# SICAM - Entorno y dependencias

## Proposito

Este documento consolida el estado actual del entorno de desarrollo y las dependencias del monorepo `sicam-refactor` despues de las validaciones de Sprint 1A, 1B, 1C y 1D.

Su objetivo es servir como referencia operativa para instalar, validar y continuar el refactor sin introducir funcionalidades nuevas ni modificar logica de segmentacion.

## Alcance

Componentes cubiertos:

- `apps/web/Backend`
- `apps/web/Frontend`
- `apps/segmentation-saliva`
- `apps/segmentation-blood`

Este documento no reemplaza los `requirements.txt`, `package.json` ni reportes de sprint. Resume el estado real validado y documenta advertencias e inconsistencias.

## Entorno recomendado

### Python

Entorno usado en validacion:

```text
C:\Users\israe\miniconda3\envs\sicam\python.exe
Python 3.10.20
```

Advertencia conocida:

```text
C:\Python314\python.exe
```

Ese Python global fue detectado en la terminal, pero no contiene las dependencias necesarias del proyecto. Para validaciones Python debe usarse explicitamente el entorno `sicam`.

### Node y npm

Versiones usadas en validacion frontend:

```text
Node v24.17.0
npm 11.13.0
```

En PowerShell, `npm --version` puede fallar por `ExecutionPolicy` al intentar cargar `npm.ps1`. En Windows se recomienda usar:

```powershell
npm.cmd --version
npm.cmd run build
```

## Estructura de componentes

```text
apps/
  web/
    Backend/
    Frontend/
  segmentation-saliva/
  segmentation-blood/
```

Arquitectura objetivo:

```text
Frontend Vue -> Django REST -> microservicios FastAPI -> persistencia en Django
```

## Backend Django

Ruta:

```text
apps/web/Backend
```

Archivo de dependencias:

```text
apps/web/Backend/requirements.txt
```

### Runtime obligatorio

- `Django==5.0.1`
- `djangorestframework==3.14.0`
- `django-cors-headers==4.3.1`
- `django-environ==0.12.0`
- `psycopg2-binary==2.9.9`
- `Pillow==10.2.0`
- `requests==2.31.0`

### Desarrollo y validacion

- `django-extensions==3.2.3`
- `pytest==7.4.4`
- `pytest-django==4.7.0`
- `pytest-cov==4.1.0`

### Configuracion

Archivo de ejemplo:

```text
apps/web/Backend/.env.example
```

Variables relevantes:

- `SECRET_KEY`
- `DEBUG`
- `ALLOWED_HOSTS`
- `DB_ENGINE`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
- `CORS_ALLOWED_ORIGINS`
- `SALIVA_SEGMENTATION_SERVICE_URL`
- `SALIVA_SERVICE_TIMEOUT`
- `BLOOD_SEGMENTATION_SERVICE_URL`
- `BLOOD_SERVICE_TIMEOUT`
- `LANGUAGE_CODE`
- `TIME_ZONE`

### Validacion liviana recomendada

Desde `apps/web/Backend`:

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' manage.py check
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -m pytest
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' manage.py test
```

Resultado de Sprint 1A:

```text
PASS WITH WARNINGS
```

Advertencia: `python manage.py test` encontro `0 test(s)`, pero `pytest` ejecuto pruebas existentes.

## Frontend Vue/Vite

Ruta:

```text
apps/web/Frontend
```

Archivo de dependencias:

```text
apps/web/Frontend/package.json
```

### Runtime obligatorio

- `axios`
- `vue`

### Desarrollo y validacion

- `@eslint/js`
- `@vitejs/plugin-vue`
- `eslint`
- `eslint-plugin-vue`
- `globals`
- `vite`
- `vite-plugin-vue-devtools`

### Configuracion

Archivo de ejemplo:

```text
apps/web/Frontend/.env.example
```

Variable principal:

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
```

El frontend usa:

```text
apps/web/Frontend/src/services/apiClient.js
```

para centralizar la base URL mediante:

```text
import.meta.env.VITE_API_BASE_URL
```

### Validacion recomendada

Desde `apps/web/Frontend`:

```powershell
npm.cmd install
npm.cmd run build
```

Si `node_modules/` ya existe, no es necesario reinstalar para una validacion liviana.

Resultado de Sprint 1B:

```text
PASS WITH WARNINGS
```

Advertencias:

- `npm --version` puede fallar por `ExecutionPolicy`; usar `npm.cmd`.
- El build puede fallar dentro del sandbox por permisos de lectura; fuera del sandbox paso correctamente.
- `node_modules/` y `dist/` deben permanecer fuera de Git.

## Microservicio de saliva

Ruta:

```text
apps/segmentation-saliva
```

Archivo de dependencias:

```text
apps/segmentation-saliva/requirements.txt
```

Archivo principal FastAPI:

```text
app/main.py
```

Comando esperado de desarrollo:

```powershell
python -m uvicorn app.main:app --reload --port 8001
```

Este comando no debe ejecutarse durante validaciones livianas si puede cargar modelos o ejecutar inicializacion pesada.

### Runtime obligatorio declarado

- `fastapi`
- `uvicorn[standard]`
- `python-multipart`
- `numpy`
- `opencv-python-headless`
- `matplotlib`
- `scikit-image`
- `scikit-learn`

### Dependencias remediadas durante Sprint 1C

- `tqdm`
- `numba`
- `torch`
- `natsort`

### Dependencias pesadas o especiales

#### `torch`

`torch` fue instalado para validacion local como CPU-only:

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -m pip install torch --index-url https://download.pytorch.org/whl/cpu
```

Version validada:

```text
torch=2.12.1+cpu
cuda=False
```

No se instalo CUDA, `torchvision`, `torchaudio`, dependencias GPU ni modelos.

#### `numba`

`numba` fue instalado con conda-forge por ser dependencia compilada:

```powershell
& 'C:\Users\israe\miniconda3\Scripts\conda.exe' install -n sicam -c conda-forge numba -y
```

Version validada:

```text
numba=0.65.1
```

### Modelos y artefactos externos

`segmentacion_core/membranas_500_125` existe localmente y esta ignorado por Git:

```text
segmentacion_core/membranas_500_125
```

Debe tratarse como modelo o artefacto pesado externo. No debe agregarse al repositorio sin decision explicita.

### `cellpose/` vendorizado

El codigo `segmentacion_core/cellpose/` esta versionado temporalmente para preservar el estado heredado.

Reglas:

- No modificar `cellpose/` sin autorizacion explicita.
- No reemplazarlo por `cellpose` externo sin una tarea dedicada.
- No descargar modelos automaticamente.

### Validacion liviana recomendada

Desde `apps/segmentation-saliva`:

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -m compileall -q app segmentacion_core
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -c "import segmentacion_core.seg_membranas; print('seg_membranas import ok')"
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -c "import app.utils.poligonos; import segmentacion_core.model.cytoplasm; import segmentacion_core.model.nuclei; import segmentacion_core.model.micronuclei; import segmentacion_core.seg_nucleos; import segmentacion_core.seg_micronucleos; print('imports livianos ok')"
```

Resultado despues de remediaciones:

```text
PASS WITH WARNINGS
```

Advertencias:

- No se ejecuto segmentacion real.
- No se levanto FastAPI.
- No se cargo explicitamente `membranas_500_125`.
- La validacion solo garantiza sintaxis e imports livianos.

## Microservicio de sangre

Ruta:

```text
apps/segmentation-blood
```

Archivo de dependencias:

```text
apps/segmentation-blood/requirements.txt
```

Archivo principal FastAPI:

```text
main.py
```

Comando esperado:

```powershell
python -m uvicorn main:app --reload --port 8002
```

Este comando no se ejecuto en Sprint 1D porque `main.py` define un `lifespan` que precarga Cellpose mediante `_obtener_modelo()`.

### Runtime obligatorio declarado

- `fastapi`
- `uvicorn[standard]`
- `python-multipart`
- `numpy`
- `opencv-python-headless`
- `scikit-image`
- `scikit-learn`

### Dependencias disponibles por el entorno validado

Durante Sprint 1D se confirmo:

```text
torch=2.12.1+cpu
cuda=False
natsort=8.4.0
numba=0.65.1
```

Estas dependencias quedaron disponibles en `sicam` por las remediaciones del microservicio de saliva.

### Dependencias heredadas o inciertas

`apps/segmentation-blood/segmentacion_core/dependencies.txt` lista dependencias historicas:

- `pytorch`
- `pyqtgraph`
- `PyQt6`
- `numpy`
- `scipy`
- `natsort`
- `tifffile`
- `imagecodecs`
- `roifile`
- `fastremap`
- `fill_voids`

Observacion: no todas estas dependencias estan declaradas en `requirements.txt`, y no esta confirmado que todas sean runtime real del microservicio FastAPI actual. Deben revisarse antes de agregarlas.

### `cellpose/` vendorizado

`segmentacion_core/cellpose/` esta presente y versionado como codigo heredado liviano.

Reglas:

- No modificar `cellpose/` sin autorizacion explicita.
- No descargar modelos automaticamente.
- No levantar el servicio durante validaciones livianas si eso carga Cellpose.

### Validacion liviana recomendada

Desde `apps/segmentation-blood`:

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -m compileall -q app segmentacion_core main.py
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -c "import fastapi, uvicorn, numpy, cv2, skimage, sklearn; print('imports base ok')"
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -c "import app.utils.poligonos; import segmentacion_core.sicam_master; print('imports livianos ok')"
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -c "import main; print('main import ok')"
```

Resultado de Sprint 1D:

```text
PASS WITH WARNINGS
```

Advertencias:

- Importar `main` no ejecuta el `lifespan`.
- No se llamo `_obtener_modelo()`.
- No se ejecuto `segmentar_desde_bytes()`.
- No se levanto el servicio.
- No se cargo Cellpose.

## Politica de modelos y pesos externos

Los modelos, pesos y artefactos pesados deben manejarse mediante una estrategia externa, por ejemplo:

- almacenamiento institucional;
- release assets;
- carpeta local documentada;
- mecanismo de descarga controlado y aprobado.

Reglas:

- No agregar modelos/pesos a Git sin decision explicita.
- No descargar modelos automaticamente durante validaciones.
- No ejecutar segmentacion real en validaciones de integridad liviana.
- Mantener `membranas_500_125` como artefacto externo ignorado.
- Mantener caches y generados fuera de Git: `__pycache__/`, `*.pyc`, `.pytest_cache/`, `node_modules/`, `dist/`, `media/`.

## Comandos de instalacion recomendados

### Backend

```powershell
cd apps/web/Backend
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -m pip install -r requirements.txt
```

### Frontend

```powershell
cd apps/web/Frontend
npm.cmd install
```

### Saliva

```powershell
cd apps/segmentation-saliva
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -m pip install -r requirements.txt
```

Para PyTorch CPU-only, usar explicitamente:

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -m pip install torch --index-url https://download.pytorch.org/whl/cpu
```

Para `numba`, preferir conda-forge:

```powershell
& 'C:\Users\israe\miniconda3\Scripts\conda.exe' install -n sicam -c conda-forge numba
```

### Sangre

```powershell
cd apps/segmentation-blood
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -m pip install -r requirements.txt
```

Advertencia: `requirements.txt` de sangre podria no reflejar aun todas las dependencias runtime heredadas. No agregar dependencias historicas sin validacion.

## Comandos que deben evitarse en validacion liviana

Evitar:

```powershell
python -m uvicorn app.main:app --reload --port 8001
python -m uvicorn main:app --reload --port 8002
```

Motivo: pueden cargar Cellpose, modelos o inicializaciones pesadas.

Evitar tambien:

- ejecutar endpoints `/segmentar`;
- llamar `segmentar_pipeline()`;
- llamar `segmentar_desde_bytes()`;
- llamar `_obtener_modelo()`;
- descargar modelos;
- instalar CUDA o dependencias GPU sin sprint explicito.

## Advertencias conocidas

- El entorno global `C:\Python314\python.exe` no corresponde al entorno validado.
- En Windows, usar `npm.cmd` evita bloqueos por `npm.ps1`.
- `apps/segmentation-saliva/README.md` menciona el entorno historico `cellseg`; el entorno actual validado es `sicam`.
- `apps/segmentation-blood` no tiene `README.md`.
- `apps/segmentation-blood/requirements.txt` podria estar incompleto respecto a dependencias heredadas.
- `cellpose/` esta vendorizado temporalmente y debe evaluarse si conviene reemplazarlo por dependencia externa formal.
- `torch` en `requirements.txt` no garantiza CPU-only por si solo; usar el indice oficial CPU de PyTorch.
- `pip install -r requirements.txt` podria instalar `torch` desde el indice por defecto si no se usa el comando CPU-only indicado.

## Relacion con proximos sprints

Sprint 1 deja validacion tecnica liviana de:

- backend Django;
- frontend Vue/Vite;
- microservicio de saliva;
- microservicio de sangre.

Siguientes iteraciones recomendadas:

- Consolidar o ajustar `requirements.txt` con aprobacion explicita, especialmente en `apps/segmentation-blood`.
- Definir estrategia formal para modelos/pesos externos.
- Definir si `cellpose/` seguira vendorizado o sera dependencia externa.
- Continuar con Sprint 2: endpoint Django `POST /api/muestras/{id}/segmentar/`.
- Mantener la regla de no cambiar modelos Django, endpoints existentes ni logica de segmentacion sin sprint dedicado.
