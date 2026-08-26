# Hotfix Sprint 16B-ENV - Blood Cellpose Runtime

## Fecha

2026-08-24 17:09:06 -06:00

## Proposito

Restaurar de forma reproducible el runtime de `apps/segmentation-blood` usando la copia vendorizada de Cellpose ubicada en:

```text
apps/segmentation-blood/segmentacion_core/cellpose
```

No se instalo `cellpose` externo desde PyPI, no se copio Cellpose desde saliva y no se modifico el algoritmo cientifico de sangre.

## Causa original

El microservicio de sangre falla al arrancar porque `sicam_master.py` importa:

```python
from cellpose import models
```

pero el entorno `sicam` no tenia un paquete top-level `cellpose`.

La copia vendorizada de blood si puede funcionar como top-level `cellpose` si `apps/segmentation-blood/segmentacion_core` esta en `PYTHONPATH`.

## Packaging local creado

Se creo:

```text
apps/segmentation-blood/pyproject.toml
```

Mapeo aplicado:

```toml
[tool.setuptools]
packages = ["cellpose", "cellpose.contrib"]
package-dir = { "cellpose" = "segmentacion_core/cellpose" }
```

La distribucion local se llama:

```text
sicam-segmentation-blood-cellpose-vendor
```

pero el import Python expuesto sigue siendo:

```python
import cellpose
```

## Instalacion editable local

Dry-run seguro:

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -m pip install --dry-run --no-build-isolation -e .
```

Resultado:

```text
Would install sicam-segmentation-blood-cellpose-vendor-0.1.0
```

Instalacion ejecutada:

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -m pip install --no-build-isolation -e .
```

Resultado:

```text
Successfully installed sicam-segmentation-blood-cellpose-vendor-0.1.0
```

## Verificacion de aislamiento

Comando:

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -c "import cellpose; print(cellpose.__file__)"
```

Resultado:

```text
C:\Users\israe\OneDrive - Universidad de Guadalajara\Documents\SICAM\sicam-refactor\apps\segmentation-blood\segmentacion_core\cellpose\__init__.py
```

Conclusion: `import cellpose` apunta al vendorizado BLOOD, no a PyPI ni a saliva.

## Dependencias runtime instaladas

Se hizo dry-run antes de instalar:

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -m pip install --dry-run fastremap fill-voids roifile
```

Resultado:

```text
Would install fastremap-1.20.0 fill_voids-2.1.2 roifile-2025.12.12
```

No propuso cambiar `torch`, `numpy`, `numba` ni `llvmlite`.

Instalacion ejecutada:

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -m pip install fastremap fill-voids roifile
```

Versiones instaladas:

```text
fastremap 1.20.0
fill_voids 2.1.2
roifile 2025.12.12
```

## Torchvision

`torchvision` no estaba instalado. Un dry-run sin version exacta propuso:

```text
Would install setuptools-78.1.0 torch-2.13.0+cpu torchvision-0.28.0+cpu
```

Eso activo la stop condition porque reemplazaria `torch 2.12.1+cpu`.

Luego se verifico:

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -m pip install --dry-run torchvision==0.27.1 --index-url https://download.pytorch.org/whl/cpu
```

Resultado:

```text
Requirement already satisfied: torch==2.12.1
Would install torchvision-0.27.1+cpu
```

Instalacion ejecutada:

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -m pip install torchvision==0.27.1 --index-url https://download.pytorch.org/whl/cpu
```

Versiones resultantes:

```text
torch 2.12.1+cpu
torchvision 0.27.1+cpu
torch.cuda.is_available() = False
```

No se instalo CUDA.

## Segment Anything

El vendorizado BLOOD importa SAM en:

```text
apps/segmentation-blood/segmentacion_core/cellpose/vit_sam.py
```

Import requerido:

```python
from segment_anything import sam_model_registry
```

La fuente preferida es la implementacion oficial:

```text
https://github.com/facebookresearch/segment-anything
```

Se intento dry-run con:

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -m pip install --dry-run git+https://github.com/facebookresearch/segment-anything.git
```

Resultado: el proceso quedo detenido durante la clonacion y fue interrumpido.

Se intento dry-run con ZIP oficial:

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -m pip install --dry-run --no-deps https://github.com/facebookresearch/segment-anything/archive/refs/heads/main.zip
```

Resultado: fallo por timeout de lectura desde `codeload.github.com`.

Se consulto el paquete PyPI `segment-anything`, pero no se instalo porque no demuestra en esta auditoria que sea la fuente oficial `facebookresearch/segment-anything`.

Estado actual:

```text
segment_anything = no instalado
```

## Imagecodecs

`imagecodecs` no se instalo.

Motivo: no esta en el camino principal `sicam_master -> cellpose.models -> CellposeModel -> eval`. Aparece en codigo `contrib/distributed_segmentation.py`, que no forma parte del startup/inferencia actual.

## Estado de cpsam

Variable:

```text
CELLPOSE_LOCAL_MODELS_PATH = None
```

Path esperado:

```text
C:\Users\israe\.cellpose\models\cpsam
```

Estado:

```text
exists = False
```

No se descargo `cpsam`.

URL codificada por el vendorizado:

```text
https://huggingface.co/mouseland/cellpose-sam/resolve/main/cpsam
```

## Nuevo blocker critico

Despues de instalar el packaging local, `fastremap`, `fill_voids`, `roifile` y `torchvision`, el import:

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -X faulthandler -c "import cellpose.models as m; print('models import ok', m.__file__)"
```

falla con excepcion fatal de Windows:

```text
Windows fatal exception: code 0xc06d007f
```

Stack relevante:

```text
cellpose/models.py
-> cellpose/plot.py
-> from skimage.segmentation import find_boundaries
-> skimage/segmentation/slic_superpixels.py
-> skimage/color/colorconv.py
```

Validacion aislada:

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -X faulthandler -c "from skimage.segmentation import find_boundaries; print('find_boundaries ok')"
```

Resultado:

```text
Windows fatal exception: code 0xc06d007f
```

Versiones actuales:

```text
scikit-image 0.25.2
numpy 2.2.6
scipy 1.15.3
```

Conclusion: el startup queda bloqueado por una incompatibilidad/abort nativo al importar `skimage.segmentation`, antes de llegar a `segment_anything` y antes de construir `CellposeModel(gpu=False)`.

## CellposeModel

No se probo:

```python
models.CellposeModel(gpu=False)
```

Motivo: `from cellpose import models` no llega a completarse por el blocker critico de `skimage.segmentation`.

Por tanto:

```text
CellposeModel(gpu=False) = FAIL / no ejecutado por blocker previo
uvicorn startup = no ejecutado
/docs = no validado
```

## Requirements actualizado

Se actualizo:

```text
apps/segmentation-blood/requirements.txt
```

Cambios principales:

- se elimino la instruccion obsoleta `pip install -e ./cellpose`;
- se agrego `-e .` para instalar el vendorizado BLOOD como top-level `cellpose`;
- se agregaron dependencias runtime: `fastremap`, `fill-voids`, `roifile`;
- se documento `segment-anything` desde fuente oficial GitHub;
- se fijo `torchvision==0.27.1+cpu` con indice CPU de PyTorch para proteger `torch 2.12.1+cpu`;
- no se agrego `cellpose` externo.

## Tests y validaciones

Ejecutado:

```powershell
python -c "import cellpose; print(cellpose.__file__)"
```

Resultado: PASS.

Ejecutado:

```powershell
python -c "from cellpose import models; print(models.__file__)"
```

Resultado: FAIL por excepcion fatal en `skimage.segmentation`.

No se ejecuto `python -m pytest` porque el import base del runtime queda bloqueado por una excepcion fatal nativa.

## Riesgos restantes

- Resolver el abort nativo de `skimage.segmentation` sin romper `numpy`, `scipy`, `numba` ni `llvmlite`.
- Instalar `segment_anything` desde la fuente oficial de Meta cuando la descarga/clonacion sea estable o cuando se provea una copia local confiable.
- Descargar exactamente `cpsam` si se aprueba la descarga del modelo.
- Validar despues `models.CellposeModel(gpu=False)`.
- Levantar `uvicorn main:app --reload --port 8002` solo despues de que el import y la construccion del modelo pasen.

## Estado Git observado

Nuevos/modificados en este hotfix:

```text
M  apps/segmentation-blood/requirements.txt
?? apps/segmentation-blood/pyproject.toml
?? docs/47_hotfix_16b_blood_cellpose_runtime.md
```

Tambien existen cambios previos de Sprint 16A/16B en backend y docs que no pertenecen a este hotfix.

## Fase D - Runtime BLOOD aislado `sicam-blood`

Fecha:

```text
2026-08-25
```

Decision aplicada:

```text
segmentation-blood usa un entorno independiente `sicam-blood`.
No se clono `sicam`.
No se reparo `sicam` in-place.
No se modifico saliva.
```

### Creacion y estado inicial del entorno

Entorno creado/verificado:

```powershell
& 'C:\Users\israe\miniconda3\Scripts\conda.exe' create -n sicam-blood python=3.10 pip -y
& 'C:\Users\israe\miniconda3\Scripts\conda.exe' run -n sicam-blood python --version
& 'C:\Users\israe\miniconda3\Scripts\conda.exe' run -n sicam-blood python -m pip --version
& 'C:\Users\israe\miniconda3\Scripts\conda.exe' list -n sicam-blood
```

Resultados:

```text
Python 3.10.21
pip 26.2.1
```

El entorno inicial contenia solo Python, pip, setuptools/wheel y runtime base de conda. No contenia `numpy`, `scipy`, `scikit-image`, `torch` ni `torchvision`.

### Stack cientifico instalado por pip

Dry-run:

```powershell
& 'C:\Users\israe\miniconda3\Scripts\conda.exe' run -n sicam-blood python -m pip install --dry-run numpy==2.2.6 scipy==1.15.3 scikit-image==0.25.2 pillow networkx imageio tifffile lazy-loader packaging
```

Resultado:

```text
Would install ImageIO-2.37.4 lazy-loader-0.5 networkx-3.4.2 numpy-2.2.6 pillow-12.3.0 scikit-image-0.25.2 scipy-1.15.3 tifffile-2025.5.10
```

Instalacion:

```powershell
& 'C:\Users\israe\miniconda3\Scripts\conda.exe' run -n sicam-blood python -m pip install numpy==2.2.6 scipy==1.15.3 scikit-image==0.25.2 pillow networkx imageio tifffile lazy-loader packaging
```

Validaciones:

```text
numpy 2.2.6 PASS
scipy 1.15.3 PASS
scikit-image 0.25.2 PASS
rgb2gray PASS
find_boundaries PASS
```

Comandos relevantes:

```powershell
& 'C:\Users\israe\miniconda3\Scripts\conda.exe' run -n sicam-blood python -X faulthandler -c "from skimage.color import rgb2gray; print('rgb2gray PASS')"
& 'C:\Users\israe\miniconda3\Scripts\conda.exe' run -n sicam-blood python -X faulthandler -c "from skimage.segmentation import find_boundaries; print('find_boundaries PASS')"
```

### PyTorch CPU-only

Dry-run:

```powershell
& 'C:\Users\israe\miniconda3\Scripts\conda.exe' run -n sicam-blood python -m pip install --dry-run torch==2.12.1+cpu torchvision==0.27.1+cpu --index-url https://download.pytorch.org/whl/cpu
```

Resultado:

```text
Would install torch-2.12.1+cpu torchvision-0.27.1+cpu
Would install setuptools-78.1.0
```

Observacion: `torch 2.12.1+cpu` requiere `setuptools<82`, por lo que pip reemplazo `setuptools 84.0.0` por `setuptools 78.1.0`. No propuso cambiar `numpy`, `scipy` ni `scikit-image`.

Instalacion:

```powershell
& 'C:\Users\israe\miniconda3\Scripts\conda.exe' run -n sicam-blood python -m pip install torch==2.12.1+cpu torchvision==0.27.1+cpu --index-url https://download.pytorch.org/whl/cpu
```

Resultado:

```text
torch 2.12.1+cpu
torchvision 0.27.1+cpu
torch.cuda.is_available() = False
```

### Test critico OpenMP

Comandos:

```powershell
& 'C:\Users\israe\miniconda3\Scripts\conda.exe' run -n sicam-blood python -X faulthandler -c "import torch; from skimage.segmentation import find_boundaries; print(torch.__version__); print('torch -> skimage PASS')"
& 'C:\Users\israe\miniconda3\Scripts\conda.exe' run -n sicam-blood python -X faulthandler -c "from skimage.segmentation import find_boundaries; import torch; print(torch.__version__); print('skimage -> torch PASS')"
```

Resultados:

```text
torch -> skimage PASS
skimage -> torch PASS
```

Smoke numerico:

```powershell
& 'C:\Users\israe\miniconda3\Scripts\conda.exe' run -n sicam-blood python -c "import torch; import numpy as np; from scipy import linalg; a=np.array([[2.,1.],[1.,2.]]); print(linalg.inv(a)); print(torch.ones(2,2) @ torch.ones(2,2)); print('numeric smoke PASS')"
```

Resultado:

```text
numeric smoke PASS
```

Conclusion: el aislamiento en `sicam-blood` resolvio el conflicto nativo/OpenMP observado en `sicam`.

### Dependencias Cellpose BLOOD

Dry-run:

```powershell
& 'C:\Users\israe\miniconda3\Scripts\conda.exe' run -n sicam-blood python -m pip install --dry-run fastremap fill-voids roifile
```

Resultado:

```text
Would install fastremap-1.20.0 fill_voids-2.1.2 roifile-2025.12.12
```

Instalacion:

```powershell
& 'C:\Users\israe\miniconda3\Scripts\conda.exe' run -n sicam-blood python -m pip install fastremap fill-voids roifile
```

Versiones:

```text
fastremap 1.20.0
fill-voids 2.1.2
roifile 2025.12.12
```

Tambien se instalaron dependencias ya declaradas o requeridas por el camino de import del vendorizado:

```text
tqdm 4.70.0
opencv-python-headless 5.0.0.93
natsort 8.4.0
```

Despues de estas instalaciones se repitio el test OpenMP y siguio en PASS para ambos ordenes de import.

### Cellpose vendorizado BLOOD

Instalacion editable local:

```powershell
cd apps/segmentation-blood
& 'C:\Users\israe\miniconda3\Scripts\conda.exe' run -n sicam-blood python -m pip install --no-deps --no-build-isolation -e .
```

Resultado:

```text
Successfully installed sicam-segmentation-blood-cellpose-vendor-0.1.0
```

Verificacion:

```powershell
& 'C:\Users\israe\miniconda3\Scripts\conda.exe' run -n sicam-blood python -c "import cellpose; print(cellpose.__file__)"
```

Resultado:

```text
C:\Users\israe\OneDrive - Universidad de Guadalajara\Documents\SICAM\sicam-refactor\apps\segmentation-blood\segmentacion_core\cellpose\__init__.py
```

Conclusion: `import cellpose` resuelve al vendorizado BLOOD.

### Segment Anything

Antes de instalar Segment Anything, `from cellpose import models` fallo con:

```text
ModuleNotFoundError: No module named 'segment_anything'
```

Dry-run oficial:

```powershell
& 'C:\Users\israe\miniconda3\Scripts\conda.exe' run -n sicam-blood python -m pip install --dry-run git+https://github.com/facebookresearch/segment-anything.git
```

Resultado:

```text
Resolved https://github.com/facebookresearch/segment-anything.git to commit dca509fe793f601edb92606367a655c15ac00fdf
Would install segment_anything-1.0
```

No propuso cambiar `torch`, `torchvision`, `numpy`, `scipy` ni `scikit-image`.

Instalacion:

```powershell
& 'C:\Users\israe\miniconda3\Scripts\conda.exe' run -n sicam-blood python -m pip install git+https://github.com/facebookresearch/segment-anything.git
```

Resultado:

```text
Successfully installed segment_anything-1.0
```

Path:

```text
C:\Users\israe\miniconda3\envs\sicam-blood\lib\site-packages\segment_anything\__init__.py
```

### Import de `cellpose.models`

Comando:

```powershell
& 'C:\Users\israe\miniconda3\Scripts\conda.exe' run -n sicam-blood python -X faulthandler -c "from cellpose import models; print(models.__file__); print('cellpose.models PASS')"
```

Resultado:

```text
C:\Users\israe\OneDrive - Universidad de Guadalajara\Documents\SICAM\sicam-refactor\apps\segmentation-blood\segmentacion_core\cellpose\models.py
cellpose.models PASS
```

Despues de instalar Segment Anything se repitio el test OpenMP:

```text
torch -> skimage PASS
skimage -> torch PASS
```

### Estado de `cpsam`

Path esperado:

```text
C:\Users\israe\.cellpose\models\cpsam
```

Estado:

```text
exists = False
```

URL exacta codificada por el vendorizado:

```text
https://huggingface.co/mouseland/cellpose-sam/resolve/main/cpsam
```

Se intento construir el modelo sin inferencia:

```powershell
& 'C:\Users\israe\miniconda3\Scripts\conda.exe' run -n sicam-blood python -X faulthandler -c "from cellpose import models; model = models.CellposeModel(gpu=False); print('CellposeModel PASS'); print('gpu', model.gpu); print('pretrained_model', model.pretrained_model)"
```

Resultado:

```text
El proceso permanecio activo varios minutos sin salida visible.
C:\Users\israe\.cellpose\models\cpsam no aparecio en disco durante la espera.
El proceso fue interrumpido manualmente para mantener el diagnostico controlado.
```

Conclusion:

```text
CellposeModel(gpu=False) = FAIL / bloqueado por descarga o inicializacion de cpsam
```

No se ejecuto segmentacion real.

### Uvicorn y `/docs`

No se ejecuto:

```powershell
conda run -n sicam-blood python -m uvicorn main:app --port 8002
```

Motivo: el startup real de BLOOD depende de `_obtener_modelo()`, que construye `CellposeModel(gpu=False)`. Como `cpsam` no existe y la construccion quedo bloqueada, no se intento arrancar el servicio.

Estado:

```text
uvicorn startup = no ejecutado
/docs = no validado
```

### Estado final de paquetes en `sicam-blood`

Paquetes principales:

```text
numpy 2.2.6
scipy 1.15.3
scikit-image 0.25.2
pillow 12.3.0
networkx 3.4.2
imageio 2.37.4
tifffile 2025.5.10
lazy-loader 0.5
packaging 26.3
torch 2.12.1+cpu
torchvision 0.27.1+cpu
fastremap 1.20.0
fill-voids 2.1.2
roifile 2025.12.12
tqdm 4.70.0
natsort 8.4.0
opencv-python-headless 5.0.0.93
segment_anything 1.0
sicam-segmentation-blood-cellpose-vendor 0.1.0 editable
```

Validacion:

```powershell
& 'C:\Users\israe\miniconda3\Scripts\conda.exe' run -n sicam-blood python -m pip check
```

Resultado:

```text
No broken requirements found.
```

### Blocker restante

El blocker nativo/OpenMP quedo resuelto en `sicam-blood`.

El blocker restante es externo al codigo:

```text
Falta disponer de C:\Users\israe\.cellpose\models\cpsam.
La descarga o inicializacion automatica desde Hugging Face no completo dentro del tiempo observado.
```

Siguiente paso recomendado:

```text
Proveer `cpsam` por un mecanismo controlado, verificando que corresponde exactamente a:
https://huggingface.co/mouseland/cellpose-sam/resolve/main/cpsam

Despues repetir:
1. from cellpose import models
2. models.CellposeModel(gpu=False)
3. uvicorn main:app --port 8002 sin --reload
4. /docs
```

## Fase E - Provisionamiento controlado de `cpsam` y startup real

Fecha:

```text
2026-08-25 13:08:24 -06:00
```

### Contrato confirmado

El vendorizado BLOOD referencia exactamente:

```text
Modelo: cpsam
URL: https://huggingface.co/mouseland/cellpose-sam/resolve/main/cpsam
Destino final: C:\Users\israe\.cellpose\models\cpsam
Temporal de descarga: C:\Users\israe\.cellpose\models\cpsam.download
```

No se instalo `cellpose` externo desde PyPI, no se sustituyo el modelo y no se modificaron algoritmos.

### Descarga controlada

Se uso `curl.exe` con descarga explicita y reanudable hacia:

```text
C:\Users\israe\.cellpose\models\cpsam.download
```

La descarga inicial y una reanudacion fallaron por cierre prematuro de respuesta, conservando el archivo parcial. Despues se ejecuto una descarga resumible hasta completar el tamano esperado.

Resultado final del temporal:

```text
Length: 1233587898 bytes
Content-Type observado: application/octet-stream
HTTP final observado: 206
```

Validacion de cabecera:

```text
HEAD_HEX: 50 4B 03 04 ...
HEAD_ASCII: PK...cpsam8_0_2100_8_402175188/data.pkl...
```

Conclusion: el archivo descargado corresponde a un artefacto binario compatible con formato zip/serializado de PyTorch. No corresponde a HTML, JSON, texto ni puntero Git LFS.

SHA-256:

```text
E1440429EB384F95AFE32BCBA6510F90D518EAEDC917EDE549BED6804004ABE2
```

### Promocion atomica

Despues de validar tamano, cabecera y hash, se promovio:

```text
Origen: C:\Users\israe\.cellpose\models\cpsam.download
Destino: C:\Users\israe\.cellpose\models\cpsam
```

Resultado final:

```text
Path: C:\Users\israe\.cellpose\models\cpsam
Length: 1233587898 bytes
SHA-256: E1440429EB384F95AFE32BCBA6510F90D518EAEDC917EDE549BED6804004ABE2
```

### Carga de Cellpose vendorizado

Comando:

```powershell
& 'C:\Users\israe\miniconda3\Scripts\conda.exe' run -n sicam-blood python -X faulthandler -c "import time; from cellpose import models; print('models_file', models.__file__); t=time.perf_counter(); model = models.CellposeModel(gpu=False); dt=time.perf_counter()-t; print('CellposeModel PASS'); print('gpu', model.gpu); print('pretrained_model', model.pretrained_model); print('load_seconds', round(dt, 2))"
```

Resultado:

```text
models_file C:\Users\israe\OneDrive - Universidad de Guadalajara\Documents\SICAM\sicam-refactor\apps\segmentation-blood\segmentacion_core\cellpose\models.py
CellposeModel PASS
gpu False
pretrained_model C:\Users\israe\.cellpose\models\cpsam
load_seconds 3.11
```

Conclusion:

```text
CellposeModel(gpu=False) = PASS
GPU/CUDA = False
Modelo usado = C:\Users\israe\.cellpose\models\cpsam
Descargas adicionales durante la carga = no observadas
```

### Estado de cache local

Listado observado:

```text
cpsam       1233587898 bytes
tmp_lt6aj_u  201564160 bytes
```

`tmp_lt6aj_u` parece un temporal heredado de una descarga interrumpida anterior. No se elimino porque esta fase no autoriza borrar artefactos locales fuera del repositorio.

### Dependencias runtime web

Antes del startup real, el entorno `sicam-blood` no tenia:

```text
fastapi
uvicorn
python-multipart
scikit-learn
```

Se instalaron en el entorno aislado `sicam-blood` para permitir el arranque del microservicio:

```powershell
& 'C:\Users\israe\miniconda3\Scripts\conda.exe' run -n sicam-blood python -m pip install fastapi "uvicorn[standard]" python-multipart scikit-learn
```

Versiones instaladas principales:

```text
fastapi 0.141.1
uvicorn 0.52.4
python-multipart 0.0.32
scikit-learn 1.7.2
```

No se modifico `requirements.txt` en esta fase.

### Import de `main`

Comando:

```powershell
& 'C:\Users\israe\miniconda3\Scripts\conda.exe' run -n sicam-blood python -c "import main; print('main import PASS')"
```

Resultado:

```text
main import PASS
```

### Startup real de `segmentation-blood`

Comando ejecutado desde:

```text
apps/segmentation-blood
```

Comando:

```powershell
& 'C:\Users\israe\miniconda3\Scripts\conda.exe' run -n sicam-blood python -m uvicorn main:app --host 127.0.0.1 --port 8002
```

Resultado:

```text
uvicorn startup = PASS
```

Validacion de `/docs`:

```text
GET http://127.0.0.1:8002/docs
HTTP/1.1 200 OK
content-type: text/html; charset=utf-8
```

Validacion de OpenAPI:

```text
GET http://127.0.0.1:8002/openapi.json
OPENAPI_STATUS: 200
SEGMENTAR_VISIBLE: True
```

El endpoint expuesto es:

```text
POST /api/v1/segmentar
```

No se ejecuto segmentacion real.

### Segundo startup

Despues de detener el primer proceso, se ejecuto un arranque controlado adicional y se midio el tiempo hasta que `/docs` respondio `200`.

Resultado:

```text
STARTUP_STATUS: PASS
DOCS_STATUS: 200
READY_SECONDS: 12.79
```

El proceso fue detenido al finalizar la comprobacion.

### Advertencias

- PowerShell muestra una advertencia no fatal al intentar cargar `profile.ps1` porque la ejecucion de scripts esta deshabilitada.
- La cache local contiene `tmp_lt6aj_u`, probablemente temporal de descarga anterior; no se elimino.
- La instalacion de dependencias web se hizo en el entorno local `sicam-blood`, sin cambio documental de `requirements.txt` en esta fase.

### Conclusion de Fase E

```text
cpsam provisionado = PASS
CellposeModel(gpu=False) = PASS
uvicorn startup = PASS
/docs = PASS
POST /api/v1/segmentar visible = PASS
segmentation-blood startup real = PASS
```

Blocker actual:

```text
No queda blocker tecnico de startup identificado para segmentation-blood.
Queda pendiente validar segmentacion real de sangre con imagen y modelo operativo en una fase separada.
```

## Fase F - Timeout BLOOD y smoke E2E real

Fecha:

```text
2026-08-26
```

### Motivo del hotfix

Una ejecucion directa real de `segmentation-blood` con `sangre_01.jpeg` tardo:

```text
116.174261 segundos
```

El backend Django conservaba:

```text
BLOOD_SERVICE_TIMEOUT=30
```

Ese valor era insuficiente para inferencia CPU real con Cellpose/SAM. Se amplio
unicamente el timeout de BLOOD:

```text
BLOOD_SERVICE_TIMEOUT=240
```

`SALIVA_SERVICE_TIMEOUT` permanecio en:

```text
30
```

### Validaciones de backend

Comandos ejecutados:

```powershell
python manage.py check
python manage.py makemigrations --check
python -m pytest
python manage.py test
git diff --check
```

Resultados:

```text
manage.py check = PASS
makemigrations --check = PASS, No changes detected
pytest = 141 passed, 2 skipped
manage.py test = 116 tests, OK
git diff --check = PASS, con advertencias CRLF de working copy
```

### Smoke real con `sangre_01.jpeg`

Archivo externo usado:

```text
C:\Users\israe\OneDrive - Universidad de Guadalajara\Documents\SICAM\imagenes\Sangre\sangre_01.jpeg
```

Validacion de archivo:

```text
decode = PASS
shape = (1280, 719, 3)
bytes = 66048
```

E2E por Django:

```text
POST /api/muestras-sangre/2/segmentar/
HTTP 200
time_total = 120.840785 s
ResultadoSegmentacion id = 13
```

Resultado:

```text
raw objetos = 351
raw labels = membrana:350, micronucleo:1
raw duplicate ids = 1:2
normalizado version = 1.1
normalizado total = 351
normalizado labels = membrana:350, micronucleo:1
normalizado ids unicos = 351
historial = PASS
effective = PASS, fuente AUTOMATICO
```

### Smoke real con `sangre_02.jpeg`

Archivo externo usado:

```text
C:\Users\israe\OneDrive - Universidad de Guadalajara\Documents\SICAM\imagenes\Sangre\sangre_02.jpeg
```

Validacion de archivo:

```text
decode = PASS
shape = (1280, 719, 3)
bytes = 36476
```

Directo FastAPI:

```text
POST /api/v1/segmentar
HTTP 200
time_total = 123.069527 s
raw objetos = 282
raw labels = membrana:280, micronucleo:2
raw duplicate ids = 2:2, 3:2
labels invalidos = 0
```

E2E por Django:

```text
POST /api/muestras-sangre/3/segmentar/
HTTP 200
time_total = 120.761650 s
ResultadoSegmentacion id = 14
```

Resultado:

```text
raw objetos = 282
raw labels = membrana:280, micronucleo:2
raw duplicate ids = 2:2, 3:2
normalizado version = 1.1
normalizado total = 282
normalizado labels = membrana:280, micronucleo:2
normalizado ids unicos = 282
historial = PASS
effective = PASS, fuente AUTOMATICO
```

### Limpieza

Se eliminaron los objetos temporales creados durante el smoke:

```text
ResultadoSegmentacion = 13, 14
MuestraSangre = 2, 3
media temporal =
  muestras/sangre/2026/08/smoke16b_timeout_sangre_01.jpeg
  muestras/sangre/2026/08/smoke16b_timeout_sangre_02.jpeg
```

No se eliminaron:

```text
imagenes fuente externas
C:\Users\israe\.cellpose\models\cpsam
C:\Users\israe\.cellpose\models\tmp_lt6aj_u
```

### Conclusion de Fase F

```text
BLOOD timeout 240 = PASS
segmentation-blood directo sangre_02 = PASS
Django E2E sangre_01 = PASS
Django E2E sangre_02 = PASS
persistencia = PASS
normalizacion 1.1 = PASS
historial = PASS
effective = PASS
cleanup = PASS
```

Deuda futura:

```text
Evaluar ejecucion asincrona de segmentacion BLOOD debido al tiempo de inferencia CPU.
```
