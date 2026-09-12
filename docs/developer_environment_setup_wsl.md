# Developer Environment Setup - WSL

## 1. Objetivo

Esta guia documenta la instalacion inicial de SICAM en una maquina nueva con
WSL2 y Ubuntu. Esta basada en el repositorio observado en `master`, commit
`4045393`, y separa la instalacion unica del arranque cotidiano documentado en
`docs/30_developer_startup_and_test_data.md`.

La guia no instala ni actualiza componentes por si sola. Los comandos son una
secuencia propuesta para ejecutar despues de esta validacion. El modelo SALIVA
ya esta presente y verificado estaticamente; su carga y el startup real se
validaran despues de instalar el entorno Python.

## 2. Estado auditado

Fecha de auditoria: 2026-09-10.

```text
branch: master
HEAD: 4045393 Add saliva morphometric characterization backend
working tree inicial: limpio
remote: https://github.com/irgNemo/sicam-refactor.git
WSL: version 2
distribucion observada: Ubuntu 26.04 LTS
arquitectura: x86_64
repo: /home/israel/repos/sicam-refactor
```

El repositorio esta en el filesystem Linux de WSL (`/home/...`), ubicacion
preferida para I/O y file watching de Python, Git y Vite. Evitar moverlo a
`/mnt/c/...` salvo que exista una necesidad concreta.

Estado observado de la maquina:

- `git`, `curl`, `wget`, Python del sistema y el comando `code` existen;
- Miniconda/Conda no esta instalado en `~/miniconda3` ni inicializado;
- Node y npm no estan instalados dentro de WSL;
- no existen los `.env` locales;
- no existe `node_modules`;
- no existe `db.sqlite3`;
- el modelo SALIVA esta presente, verificado e ignorado por Git;
- el modelo BLOOD `cpsam` aun no esta provisionado.

## 3. Arquitectura local

```text
Vue/Vite :5173
  -> Django REST :8000
       -> SALIVA FastAPI :8001
       -> BLOOD FastAPI :8002
       -> SQLite local
```

Caracterizacion vive dentro del backend Django. No requiere otro proceso,
puerto ni ambiente.

| Componente | Ambiente | Runtime recomendado | Fuente de dependencias | Puerto | Estado auditado |
|---|---|---|---|---:|---|
| Django | `sicam` | Python 3.10.20 | `apps/web/Backend/requirements.txt` | 8000 | Codigo listo; ambiente ausente |
| SALIVA | `sicam` | Python 3.10.20 | `apps/segmentation-saliva/requirements.txt` | 8001 | Modelo presente y verificado; ambiente ausente |
| BLOOD | `sicam-blood` | Python 3.10.21 | `apps/segmentation-blood/requirements.txt` y `pyproject.toml` | 8002 | Dependency gap resuelto; modelo pendiente de provision |
| Frontend | nvm | Node 24.17.0, npm 11.13.0 | `package-lock.json` lockfile v3 | 5173 | Node y `node_modules` ausentes |

Los puertos son convenciones de los comandos de desarrollo. Django configura
las URLs de los microservicios con esos valores por defecto; Vite usa 5173 por
defecto y el `.env.example` del frontend apunta a Django en 8000.

## 4. Inventario de archivos de dependencias

Encontrados:

```text
README.md
apps/web/Backend/README_DEVELOPMENT.md
apps/web/Backend/requirements.txt
apps/web/Backend/.env.example
apps/web/Frontend/README.md
apps/web/Frontend/package.json
apps/web/Frontend/package-lock.json
apps/web/Frontend/.env.example
apps/segmentation-saliva/README.md
apps/segmentation-saliva/app/README.md
apps/segmentation-saliva/segmentacion_core/README.md
apps/segmentation-saliva/requirements.txt
apps/segmentation-blood/requirements.txt
apps/segmentation-blood/pyproject.toml
apps/segmentation-blood/segmentacion_core/dependencies.txt
docs/18_environment_and_dependencies.md
docs/30_developer_startup_and_test_data.md
```

No se encontraron:

```text
environment.yml
environment.yaml
setup.py
setup.cfg
Pipfile
Pipfile.lock
poetry.lock
.nvmrc
.node-version
.python-version
Dockerfile
docker-compose*.yml
```

No existe lockfile Python ni definicion Conda versionada. La instalacion de
Python no es completamente reproducible mientras varios requirements sigan sin
pin.

## 5. Python y ambientes Conda

```text
RECOMMENDED_CONDA_ENVS = sicam, sicam-blood
```

### `sicam`

- Python `3.10.20`.
- Ejecuta Django y SALIVA.
- Instala `apps/web/Backend/requirements.txt` y
  `apps/segmentation-saliva/requirements.txt`.
- Esta combinacion fue la validada historicamente y no presenta un conflicto
  directo entre sus requisitos actuales.

### `sicam-blood`

- Python `3.10.21`.
- Ejecuta exclusivamente BLOOD.
- Instala `apps/segmentation-blood/requirements.txt`, que instala tambien el
  paquete local definido en `apps/segmentation-blood/pyproject.toml` mediante
  `-e .`.
- El aislamiento es obligatorio para reproducir la correccion documentada del
  conflicto nativo/OpenMP entre PyTorch y scikit-image.

No se recomienda un tercer ambiente `sicam-web` en el estado actual: anade otra
instalacion que mantener sin que el repositorio documente una incompatibilidad
entre Django y SALIVA.

Python 3.10 se conserva por evidencia:

- Django 5.0 soporta Python 3.10-3.12;
- el `pyproject.toml` BLOOD exige Python `>=3.10`;
- existen wheels Linux x86_64 CPython 3.10 para el par PyTorch auditado;
- los ambientes que pasaron los smokes anteriores usaron 3.10.20 y 3.10.21;
- mover a 3.11+ cambiaria simultaneamente Python y resoluciones cientificas no
  pinneadas.

## 6. Requirements Python

### Backend Django

Todos estan pinneados:

```text
Django==5.0.1
djangorestframework==3.14.0
django-cors-headers==4.3.1
django-environ==0.12.0
psycopg2-binary==2.9.9
Pillow==10.2.0
requests==2.31.0
django-extensions==3.2.3
pytest==7.4.4
pytest-django==4.7.0
pytest-cov==4.1.0
```

`psycopg2-binary` soporta PostgreSQL opcional. Pillow se usa para imagenes y
caracterizacion. Requests es el cliente de los dos microservicios. Pytest y
pytest-django corresponden a la suite actual.

No se encontro un import runtime no declarado en este componente.

### SALIVA

Todos estan sin pin:

```text
fastapi
uvicorn[standard]
python-multipart
numpy
opencv-python-headless
matplotlib
scikit-image
scikit-learn
tqdm
numba
torch
natsort
```

El arbol heredado contiene imports opcionales o de UI para PyQt5, PySide2,
MXNet, Google Cloud y openpyxl. No pertenecen a la ruta actual
`app.main -> segmentar_pipeline` y no deben instalarse para el servicio API sin
una tarea dedicada.

El comentario de `requirements.txt` que sugiere instalar `cellpose` desde PyPI
no coincide con el import efectivo. El runtime usa la copia vendorizada bajo
`segmentacion_core/cellpose`; instalar Cellpose externo no es un paso de esta
guia.

Riesgos:

- todas las versiones cientificas quedan abiertas;
- `torch` no fija CPU ni la version validada;
- una resolucion futura puede cambiar NumPy, SciPy, scikit-image, Numba o
  PyTorch sin cambios en Git.

### BLOOD

Declarados sin pin salvo donde se indica:

```text
fastapi
uvicorn[standard]
python-multipart
numpy
opencv-python-headless
scikit-image
scikit-learn
tqdm
scipy
-e .
fastremap
fill-voids
roifile
natsort
segment-anything @ https://github.com/facebookresearch/segment-anything/archive/dca509fe793f601edb92606367a655c15ac00fdf.zip
--extra-index-url https://download.pytorch.org/whl/cpu
torchvision==0.27.1+cpu
```

`pyproject.toml` expone la copia vendorizada como paquete top-level `cellpose`
y declara Python `>=3.10`. `torchvision==0.27.1+cpu` corresponde a
`torch==2.12.1`; la combinacion historica validada fue 2.12.1+cpu /
0.27.1+cpu.

Segment Anything queda fijado a
`dca509fe793f601edb92606367a655c15ac00fdf`. La evidencia en
`docs/47_hotfix_16b_blood_cellpose_runtime.md` registra que el dry-run oficial
resolvio ese commit y que esa misma revision se instalo en el entorno BLOOD
auditado.

Dependencias pesadas: PyTorch, torchvision, scikit-image, OpenCV, SciPy,
scikit-learn, Segment Anything y el modelo `cpsam`.

Riesgos:

- casi todo el stack esta sin pin;
- el codigo principal usa DBSCAN desde scikit-learn;
- el vendorizado importa tifffile de forma directa, obtenido transitivamente;
- modulos opcionales/contrib importan matplotlib, GUI, Dask, imagecodecs,
  zarr y formatos especiales; no pertenecen al startup/inferencia principal.

### Dependency gap resuelto

```text
DEPENDENCY GAP BLOOD = RESOLVED
```

`segmentacion_core/cellpose/io.py` ejecuta
`from natsort import natsorted` en la ruta real de startup:
`main.py -> _obtener_modelo -> cellpose.models -> plot -> io`.
`apps/segmentation-blood/requirements.txt` ahora declara `natsort` siguiendo el
estilo sin pin del manifiesto. Los entornos historicos registran
`natsort==8.4.0`, pero esa version se conserva como evidencia y no se fija
aisladamente mientras el resto del stack cientifico permanezca abierto.

## 7. Requisitos de WSL y Ubuntu

En Windows PowerShell, instalar o verificar WSL2:

```powershell
wsl --install -d Ubuntu
wsl --update
wsl --set-version Ubuntu 2
wsl --list --verbose
wsl -d Ubuntu
```

`wsl --install` puede pedir reiniciar Windows. Si Ubuntu ya existe, no volver
a instalarla; ejecutar solo las verificaciones y la actualizacion. La columna
`VERSION` debe mostrar `2`.

Dentro de Ubuntu:

```bash
pwd
uname -m
```

Arquitectura observada y soportada por los artefactos elegidos:

```text
Linux x86_64
```

Paquetes base requeridos en una WSL nueva:

```bash
sudo apt update
sudo apt install -y ca-certificates curl git
```

Recomendado si pip no encuentra wheels y necesita compilar alguna dependencia:

```bash
sudo apt install -y build-essential
```

No esta demostrado como requisito de la ruta normal basada en wheels. `wget`
es opcional. `libgl1` no se requiere por evidencia actual porque el proyecto
declara `opencv-python-headless`. PostgreSQL tampoco es requisito para
desarrollo local.

## 8. Miniconda en WSL

Se recomienda el instalador oficial, versionado y especifico para x86_64:

```text
Miniconda3-py310_26.7.1-1-Linux-x86_64.sh
SHA-256: fb1af4c45e6e73fe193c2398b4346b1e45522f729cdfccfdb18f6c765954dbd9
```

Comandos propuestos:

```bash
cd /tmp
curl --fail --location --output Miniconda3-py310_26.7.1-1-Linux-x86_64.sh \
  https://repo.anaconda.com/miniconda/Miniconda3-py310_26.7.1-1-Linux-x86_64.sh
echo "fb1af4c45e6e73fe193c2398b4346b1e45522f729cdfccfdb18f6c765954dbd9  Miniconda3-py310_26.7.1-1-Linux-x86_64.sh" \
  | sha256sum --check
bash Miniconda3-py310_26.7.1-1-Linux-x86_64.sh -b -p ~/miniconda3
~/miniconda3/bin/conda init bash
source ~/.bashrc
conda config --set auto_activate_base false
conda --version
conda info
```

Conda 26.7.1 exige aceptar explicitamente los terminos de sus dos canales
predeterminados antes del primer `conda create`. Esta aceptacion es una
decision del usuario y no agrega ni sustituye canales:

```bash
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r
```

Resultado esperado: `conda` disponible desde Bash y ningun `(base)` activado
automaticamente al abrir una terminal nueva.

Si el checksum falla, eliminar solo el instalador descargado y repetir desde la
fuente oficial. No ejecutar un archivo cuyo checksum no coincida.

Referencia oficial:
`https://www.anaconda.com/docs/getting-started/miniconda/install/linux-install`.

## 9. Creacion de ambientes

### Django + SALIVA

```bash
cd ~/repos/sicam-refactor
conda create -n sicam python=3.10.20 pip -y
conda activate sicam
python --version
python -m pip install --upgrade pip
python -m pip install torch==2.12.1+cpu \
  --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r apps/web/Backend/requirements.txt
python -m pip install -r apps/segmentation-saliva/requirements.txt
python -m pip check
```

La preinstalacion explicita de PyTorch conserva la variante CPU validada. El
requirements SALIVA contiene `torch` sin version; pip debe reconocer la version
ya satisfecha y no sustituirla. Revisar siempre la salida y `pip check`.

### BLOOD

Secuencia propuesta con el dependency gap ya resuelto en Git:

```bash
cd ~/repos/sicam-refactor
conda create -n sicam-blood python=3.10.21 pip -y
conda activate sicam-blood
python --version
python -m pip install --upgrade pip
python -m pip install torch==2.12.1+cpu torchvision==0.27.1+cpu \
  --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r apps/segmentation-blood/requirements.txt
python -m pip check
python -c "import cellpose; print(cellpose.__file__)"
```

El ultimo comando debe resolver a:

```text
.../apps/segmentation-blood/segmentacion_core/cellpose/__init__.py
```

Si apunta a `site-packages/cellpose` externo, detener la validacion: el paquete
vendorizado no quedo instalado como se espera.

## 10. Node, npm y frontend

`package.json` admite `^20.19.0 || >=22.12.0`. Se recomienda Node `24.17.0`
porque es la version exacta registrada en la validacion previa; incluye npm
`11.13.0`.

El `package-lock.json` existe, usa lockfile v3 y coincide con dependencias,
devDependencies y engines raiz de `package.json`. Por ello se debe usar
`npm ci`.

Instalar nvm 0.40.7 y Node dentro de WSL:

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.7/install.sh | bash
source ~/.bashrc
nvm --version
nvm install 24.17.0
nvm alias default 24.17.0
nvm use 24.17.0
node --version
npm --version
```

Instalar exactamente el lockfile y validar:

```bash
cd ~/repos/sicam-refactor/apps/web/Frontend
npm ci
npm run build
```

Scripts reales:

```text
npm run dev      -> vite
npm run build    -> vite build
npm run preview  -> vite preview
npm run lint     -> eslint . --fix --cache
```

`npm run lint` modifica archivos al aplicar fixes; no debe usarse como chequeo
read-only inadvertido.

## 11. Base de datos

Django usa SQLite por defecto:

```text
ENGINE=django.db.backends.sqlite3
NAME=apps/web/Backend/db.sqlite3
```

SQLite es suficiente para desarrollo. No requiere instalar un servicio ni
crear usuario/BD. El archivo se crea al aplicar migraciones y esta ignorado por
Git. Las migraciones versionadas actuales son `0001` a `0006`.

PostgreSQL es opcional. El driver `psycopg2-binary==2.9.9` ya esta declarado.
Solo si se decide usar PostgreSQL se requieren el servicio y las variables
`DB_*`; esa ruta queda fuera de la instalacion minima.

Procedimiento inicial, despues de instalar el ambiente:

```bash
cd ~/repos/sicam-refactor/apps/web/Backend
conda activate sicam
cp .env.example .env
python manage.py migrate
python manage.py check
```

No usar `makemigrations` como paso de instalacion.

Datos demo oficiales e idempotentes:

```bash
python manage.py seed_demo_data
```

Tambien admite `--image` y `--image-dir`; consultar `docs/30` antes de usar
imagenes propias. No usar datos clinicos reales.

## 12. Variables de entorno

### Django

| Variable | Obligatoria | Default actual / ejemplo seguro |
|---|---|---|
| `SECRET_KEY` | No en desarrollo; si en produccion | `django-insecure-change-this-in-production` en el ejemplo |
| `DEBUG` | No | `True` |
| `ALLOWED_HOSTS` | No | `localhost,127.0.0.1,0.0.0.0` |
| `DB_ENGINE` | No | `django.db.backends.sqlite3` |
| `DB_NAME` | No | `<Backend>/db.sqlite3` |
| `DB_USER` | No para SQLite | vacio |
| `DB_PASSWORD` | No para SQLite | vacio; no versionar valores reales |
| `DB_HOST` | No para SQLite | vacio |
| `DB_PORT` | No para SQLite | vacio |
| `CORS_ALLOWED_ORIGINS` | No | localhost/127.0.0.1 en 5173 y 3000 |
| `SALIVA_SEGMENTATION_SERVICE_URL` | No | `http://localhost:8001` |
| `SALIVA_SERVICE_TIMEOUT` | No | `30` segundos |
| `BLOOD_SEGMENTATION_SERVICE_URL` | No | `http://localhost:8002` |
| `BLOOD_SERVICE_TIMEOUT` | No | `240` segundos |
| `LANGUAGE_CODE` | No | `es-mx` |
| `TIME_ZONE` | No | `America/Mexico_City` |

El archivo local es `apps/web/Backend/.env`, copiado desde `.env.example` y
excluido por `.gitignore`.

### Frontend

| Variable | Obligatoria | Ejemplo seguro |
|---|---|---|
| `VITE_API_BASE_URL` | Si para la configuracion documentada | `http://127.0.0.1:8000` |

El archivo local es `apps/web/Frontend/.env`, copiado desde `.env.example` y
excluido por su `.gitignore`.

### BLOOD Cellpose

| Variable | Obligatoria | Default actual |
|---|---|---|
| `CELLPOSE_LOCAL_MODELS_PATH` | No | `~/.cellpose/models` |

`main.py` fija internamente `KMP_DUPLICATE_LIB_OK=TRUE` antes de importar el
stack cientifico. No es una variable que el desarrollador deba agregar al
`.env`.

SALIVA no lee variables de entorno propias en su ruta FastAPI actual.

## 13. Modelos externos y archivos ignorados

### SALIVA

Ruta obligatoria y verificada:

```text
~/repos/sicam-refactor/apps/segmentation-saliva/segmentacion_core/membranas_500_125
```

El loader en `apps/segmentation-saliva/app/services/segmentador.py` calcula
`BASE_DIR = Path(__file__).resolve().parents[2]` y construye exactamente
`BASE_DIR / "segmentacion_core" / "membranas_500_125"`. La comprobacion fue
estatica; no se importo `app.main` ni se intento cargar el modelo.

Metadatos obtenidos directamente del archivo presente:

```text
SALIVA_MODEL_SIZE_BYTES=26551763
SALIVA_MODEL_SHA256=fa6ac42f593ac7b86d665e48e69161f427fcb11ec9dd5c02fa4a2722245d0f2c
SALIVA_MODEL_SOURCE=Trusted copy from previous SICAM development workstation
```

Git lo excluye mediante:

```text
.gitignore:105:membranas_*
```

Procedimiento reproducible para provisionarlo en otra maquina desde la misma
copia confiable. En la fuente, obtener primero:

```bash
sha256sum <RUTA_CONFIABLE>/membranas_500_125
stat --format='%s' <RUTA_CONFIABLE>/membranas_500_125
```

Copiarlo a la ruta exacta de WSL:

```bash
install -m 600 <RUTA_CONFIABLE>/membranas_500_125 ~/repos/sicam-refactor/apps/segmentation-saliva/segmentacion_core/membranas_500_125
```

Despues de copiar, repetir en el destino:

```bash
sha256sum ~/repos/sicam-refactor/apps/segmentation-saliva/segmentacion_core/membranas_500_125
stat --format='%s' ~/repos/sicam-refactor/apps/segmentation-saliva/segmentacion_core/membranas_500_125
```

El destino debe medir `26551763` bytes y producir el SHA-256 documentado. El
artefacto SALIVA deja de ser un blocker previo a la instalacion. La validacion
de carga y startup permanece pendiente hasta instalar el entorno.

### BLOOD

Ruta por defecto:

```text
~/.cellpose/models/cpsam
```

Ruta alternativa: directorio definido por `CELLPOSE_LOCAL_MODELS_PATH`.

El vendorizado crea el directorio y descarga automaticamente el modelo durante
el startup si falta. Para evitar una descarga implicita de 1.23 GB, se recomienda
provisionarlo antes:

```bash
mkdir -p ~/.cellpose/models
curl --fail --location \
  --output ~/.cellpose/models/cpsam \
  https://huggingface.co/mouseland/cellpose-sam/resolve/main/cpsam
echo "e1440429eb384f95afe32bcba6510f90d518eaedc917ede549bed6804004abe2  $HOME/.cellpose/models/cpsam" \
  | sha256sum --check
stat --format='%n %s bytes' ~/.cellpose/models/cpsam
```

Evidencia documentada:

```text
SHA-256: E1440429EB384F95AFE32BCBA6510F90D518EAEDC917EDE549BED6804004ABE2
tamano observado: 1233587898 bytes
```

El cache esta fuera del repositorio. Los patrones globales tambien excluyen
`models/`, caches y pesos comunes dentro del repo.

## 14. CPU y GPU

### Requisito minimo: CPU

CPU es la configuracion minima y actualmente implementada:

- SALIVA construye `SegmentadorMembranas(..., gpu=False)`;
- BLOOD construye `CellposeModel(gpu=False)`;
- el stack anterior se valido con `torch.cuda.is_available() = False`.

Verificacion:

```bash
python -c "import torch; print(torch.__version__); print(torch.cuda.is_available())"
```

El resultado minimo esperado termina en `False`.

### Configuracion opcional: NVIDIA/CUDA en WSL

El codigo actual no habilita GPU aunque PyTorch detecte CUDA. Habilitarla exige
una tarea funcional separada para cambiar y probar la configuracion de ambos
servicios.

Si esa tarea se aprueba despues:

1. confirmar GPU NVIDIA compatible;
2. instalar/actualizar el driver NVIDIA en Windows con soporte WSL2;
3. no instalar un driver Linux NVIDIA dentro de WSL;
4. verificar `nvidia-smi` desde WSL;
5. elegir la combinacion Torch/CUDA desde la matriz oficial compatible con el
   codigo y los modelos;
6. validar cada microservicio de forma aislada antes del E2E.

No instalar CUDA arbitrariamente ni mezclar esta ruta con el setup minimo CPU.
Referencia oficial: `https://docs.nvidia.com/cuda/wsl-user-guide/`.

## 15. Directorios locales

| Ruta | Uso | Creacion |
|---|---|---|
| `apps/web/Backend/media/` | uploads y mascaras | Django storage al guardar; puede crearse manualmente |
| `apps/web/Backend/db.sqlite3` | BD local | `migrate` |
| `apps/web/Frontend/node_modules/` | dependencias frontend | `npm ci` |
| `apps/web/Frontend/dist/` | build | `npm run build` |
| `apps/segmentation-saliva/segmentacion_core/membranas_500_125` | modelo SALIVA | provision manual |
| `~/.cellpose/models/` | cache/modelo BLOOD | provision manual o startup Cellpose |
| `apps/web/Backend/staticfiles/` | posible collectstatic | no se usa en startup; `STATIC_ROOT` no esta definido |

`media`, bases SQLite, `node_modules`, `dist`, caches, `.env`, modelos y
pesos estan excluidos de Git por los `.gitignore` aplicables.

## 16. Validacion de instalacion

### Backend

```bash
cd ~/repos/sicam-refactor/apps/web/Backend
conda activate sicam
python manage.py check
python manage.py showmigrations
python -m pytest -q
python manage.py test
```

Pytest usa `config.settings`, crea una base de prueba y los tests de
caracterizacion usan imagenes temporales. Las llamadas HTTP unitarias estan
mockeadas. Dos pruebas de integracion con servicios reales estan marcadas
`skip`; requieren servicios e imagen `test_image.jpg`.

### SALIVA

Validacion sin arrancar el modelo:

```bash
cd ~/repos/sicam-refactor/apps/segmentation-saliva
conda activate sicam
python -m pip check
python -m compileall -q app segmentacion_core
python -m uvicorn --version
```

Startup real, solo despues de provisionar el modelo:

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

Verificar desde otra terminal:

```bash
curl --fail http://127.0.0.1:8001/docs >/dev/null
curl --fail http://127.0.0.1:8001/openapi.json >/dev/null
```

No existe endpoint de health dedicado. Importar `app.main` carga el modelo
SALIVA, por lo que no es un smoke liviano.

### BLOOD

Validacion previa al modelo:

```bash
cd ~/repos/sicam-refactor/apps/segmentation-blood
conda activate sicam-blood
python -m pip check
python -m compileall -q app segmentacion_core main.py
python -c "import cellpose; print(cellpose.__file__)"
python -c "import torch; from skimage.segmentation import find_boundaries; print('torch -> skimage PASS')"
python -c "from skimage.segmentation import find_boundaries; import torch; print('skimage -> torch PASS')"
```

Startup real, despues de instalar los requirements y provisionar `cpsam`:

```bash
python -m uvicorn main:app --host 127.0.0.1 --port 8002
```

El lifespan precarga Cellpose; `/docs` no estara disponible hasta que termine.
Verificar:

```bash
curl --fail http://127.0.0.1:8002/docs >/dev/null
curl --fail http://127.0.0.1:8002/openapi.json >/dev/null
```

No existe endpoint de health dedicado.

### Frontend

```bash
cd ~/repos/sicam-refactor/apps/web/Frontend
nvm use 24.17.0
npm ci
npm run build
npm run dev -- --host 127.0.0.1 --port 5173
```

Abrir `http://127.0.0.1:5173`.

## 17. Arranque completo cotidiano

Una vez terminada y validada la instalacion, usar cuatro terminales.

Terminal 1, SALIVA:

```bash
cd ~/repos/sicam-refactor/apps/segmentation-saliva
conda activate sicam
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

Terminal 2, BLOOD:

```bash
cd ~/repos/sicam-refactor/apps/segmentation-blood
conda activate sicam-blood
python -m uvicorn main:app --host 127.0.0.1 --port 8002
```

Terminal 3, Django:

```bash
cd ~/repos/sicam-refactor/apps/web/Backend
conda activate sicam
python manage.py runserver 127.0.0.1:8000
```

Terminal 4, frontend:

```bash
cd ~/repos/sicam-refactor/apps/web/Frontend
nvm use 24.17.0
npm run dev -- --host 127.0.0.1 --port 5173
```

Django y frontend pueden usarse sin ambos microservicios para pantallas que no
segmenten. SALIVA es necesario al segmentar saliva; BLOOD, al segmentar sangre.

## 18. Validacion end-to-end

Checklist posterior a la instalacion:

1. `python manage.py check` no reporta errores.
2. `npm run build` termina correctamente.
3. SALIVA responde en `/docs` y `/openapi.json`.
4. BLOOD termina de cargar `cpsam` y responde en `/docs` y `/openapi.json`.
5. Django responde en `http://127.0.0.1:8000/api/`.
6. El frontend abre en `http://127.0.0.1:5173`.
7. `seed_demo_data` crea o reutiliza los datos sinteticos.
8. Una segmentacion SALIVA llega a `POST /segmentar` y se persiste.
9. Una segmentacion BLOOD llega a `POST /api/v1/segmentar` y se persiste.
10. Historial, resultado efectivo y caracterizacion cargan desde Django.

BLOOD tardo cerca de 120 segundos por imagen en CPU durante smokes previos; el
timeout Django actual es 240 segundos.

## 19. Secuencia exacta propuesta

Esta es la secuencia completa para una WSL recien instalada. El modelo SALIVA
ya esta provisionado y verificado en la maquina auditada. La carga y la
validacion runtime se ejecutaran despues de instalar los ambientes.

1. Instalar paquetes base con los comandos de la seccion 7.
2. Instalar y verificar Miniconda con la seccion 8.
3. Instalar nvm 0.40.7 y Node 24.17.0 con la seccion 10.
4. Crear `sicam`, preinstalar Torch CPU y aplicar los requirements de Django y
   SALIVA segun la seccion 9.
5. Crear `sicam-blood`, instalar el par Torch CPU y aplicar su requirements.
6. Provisionar `membranas_500_125` desde una fuente aprobada y verificar su
   procedencia.
7. Descargar o copiar `cpsam`, comprobar SHA-256 y tamano.
8. Copiar ambos `.env.example` a `.env`; mantener SQLite.
9. Ejecutar `npm ci`.
10. Ejecutar migraciones Django y `manage.py check`.
11. Ejecutar las validaciones livianas de backend, SALIVA, BLOOD y frontend.
12. Levantar las cuatro terminales de la seccion 17.
13. Ejecutar el checklist E2E de la seccion 18.

## 20. Troubleshooting y estado de riesgos

| Clasificacion | Hallazgo | Accion requerida |
|---|---|---|
| `RESOLVED` | BLOOD importa `natsort` en startup | Declarado sin pin en `requirements.txt`; 8.4.0 queda como evidencia historica |
| `RESOLVED` | Modelo SALIVA `membranas_500_125` | Presente, ignorado por Git y documentado con fuente, tamano y SHA-256 |
| `RESOLVED` | Modelo BLOOD `~/.cellpose/models/cpsam` | Presente; tamano y SHA-256 coinciden con los valores documentados |
| `VERSION AMBIGUITY` | SALIVA no pinnea ninguna dependencia | Capturar versiones resueltas tras una instalacion validada y planear lockfile |
| `VERSION AMBIGUITY` | BLOOD deja casi todo sin pin | Capturar versiones resueltas tras una instalacion validada y planear lockfile |
| `RESOLVED` | Segment Anything usaba `main` movil | Fijado al commit validado `dca509fe793f601edb92606367a655c15ac00fdf` |
| `DOCUMENTATION GAP` | El comentario SALIVA sugiere Cellpose PyPI, pero usa vendorizado | Corregirlo junto con la futura tarea de dependencias |
| `DOCUMENTATION GAP` | `README.md` describe integraciones ya implementadas como pendientes | Actualizar por separado; no afecta el setup tecnico |
| `DOCUMENTATION GAP` | `README_DEVELOPMENT.md` anuncia `/api/health/`, ruta no registrada | No usar ese endpoint hasta corregir la documentacion o implementar la ruta |
| `RESOLVED` | Ubuntu 26.04 WSL no tenia smoke registrado | Imports, tests, build y cuatro servicios validados el 2026-09-10 |

Diagnostico rapido:

- `ModuleNotFoundError: natsort` en BLOOD: confirmar que se instalaron los
  requirements actualizados dentro de `sicam-blood`.
- SALIVA falla al importar: comprobar tamano y SHA-256 contra los valores documentados.
- BLOOD intenta descargar al arrancar: `cpsam` no esta en el cache esperado.
- `find_boundaries` aborta o hay conflicto OpenMP: confirmar que se usa
  `sicam-blood`, nunca `sicam`.
- Vite no ve cambios o trabaja lento: confirmar que el repo permanece bajo
  `/home/...`, no `/mnt/c/...`.
- Django no muestra imagenes: comprobar `DEBUG=True`, `MEDIA_ROOT` y el
  archivo local bajo `media/`.

## 21. VS Code

Usar VS Code instalado en Windows con la extension WSL/Remote Development.
Desde Ubuntu:

```bash
cd ~/repos/sicam-refactor
code .
```

La ruta observada del comando `code` corresponde a la integracion de VS Code
Windows. No instalar una segunda copia Linux salvo necesidad concreta.

## 22. Resultado de instalacion validado

Instalacion ejecutada en Ubuntu 26.04 WSL2 el 2026-09-10.

| Componente | Version / estado resuelto | Validacion |
|---|---|---|
| Miniconda | Conda 26.7.1 | checksum del instalador, `conda info`, base no autoactiva |
| `sicam` | Python 3.10.20 | `pip check` PASS |
| Django | 5.0.1 | migrate/check PASS; pytest 172 passed, 2 skipped; Django tests 147 PASS |
| SALIVA | FastAPI 0.141.1, Uvicorn 0.52.4 | modelo cargado; `/docs` y `/openapi.json` HTTP 200 |
| `sicam-blood` | Python 3.10.21 | `pip check` PASS |
| BLOOD | Torch 2.12.1+cpu, torchvision 0.27.1+cpu | ambos ordenes Torch/scikit-image PASS; startup HTTP 200 |
| Node | 24.17.0 mediante nvm 0.40.7 | version y smoke 5173 PASS |
| npm | 11.13.0 | `npm ci` PASS |
| Frontend | Vite 7.3.0 | build PASS; HTTP 200 |
| SQLite | migraciones hasta `api.0006` | migraciones aplicadas; datos demo sinteticos creados |
| `cpsam` | 1233587898 bytes | SHA-256 verificado |
| `membranas_500_125` | 26551763 bytes | SHA-256 verificado; startup SALIVA PASS |

Versiones cientificas abiertas resueltas durante esta instalacion:

```text
fastapi=0.141.1
uvicorn=0.52.4
numpy=2.2.6
opencv-python-headless=5.0.0.93
scikit-image=0.25.2
scikit-learn=1.7.2
scipy=1.15.3
tqdm=4.70.0
natsort=8.4.0
matplotlib=3.10.9        # sicam / SALIVA
numba=0.67.0             # sicam / SALIVA
fastremap=1.20.0         # sicam-blood
fill-voids=2.1.2         # sicam-blood
roifile=2025.12.12       # sicam-blood
segment-anything=1.0     # commit fijado en requirements
```

La conectividad efectiva de Django se obtiene de
`settings.SEGMENTATION_SERVICES`: claves `SALIVA` y `SANGRE`, cada una con
`url` y `timeout`. Con los cuatro servicios simultaneos, Django alcanzo ambos
microservicios con HTTP 200 y CORS autorizo `http://127.0.0.1:5173`.

Advertencias no bloqueantes:

- los requirements cientificos parcialmente sin pin pueden resolver versiones
  diferentes en una instalacion futura;
- `npm ci` reporto 18 vulnerabilidades: 2 low, 4 moderate y 12 high; no se
  ejecuto `npm audit fix`;
- Conda anuncio 26.7.2, pero se conservo 26.7.1;
- `build-essential` no fue necesario porque todos los artefactos requeridos se
  instalaron mediante wheels o builds Python sin compilador del sistema.

```text
SICAM WSL ENVIRONMENT = READY WITH WARNINGS
```
