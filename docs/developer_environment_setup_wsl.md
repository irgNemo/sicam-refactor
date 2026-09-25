# SICAM — Instalación inicial en WSL

## Alcance y fuentes

Guía canónica para instalar desde una WSL nueva. Auditada el 2026-09-25 contra
`master`, HEAD `1487569e9bd525aaf1a76d3e4bdf5bfff0781990`.
La migración Windows → WSL ya fue validada; no está pendiente instalar los
ambientes de la máquina usada en ese cierre. En una máquina nueva sí deben
completarse los pasos siguientes.

Para operar una instalación existente, usar el
[manual de arranque y datos de prueba](30_developer_startup_and_test_data.md).
Esta guía no es un registro de comandos ejecutados hoy: la revisión 18C.1 es
exclusivamente documental, sin instalaciones, descargas ni inferencias.

## 1. Arquitectura y ambientes

```text
Vue/Vite :5173
   -> Django REST :8000 -> SQLite local
        +-> SALIVA CURRENT :8001
        +-> BLOOD          :8002
        +-> SALIVA ALT     :8003
```

Characterization vive en Django, sin proceso ni ambiente adicional. SALIVA
permite elegir CURRENT o ALT desde frontend. BLOOD no tiene selector y no
admite estrategias SALIVA.

| Componente | Directorio desde la raíz | Ambiente | Python / runtime | Puerto |
|---|---|---|---|---:|
| Django | `apps/web/Backend` | `sicam` | 3.10.20 | 8000 |
| SALIVA CURRENT | `apps/segmentation-saliva` | `sicam` | 3.10.20, Cellpose vendorizado | 8001 |
| BLOOD | `apps/segmentation-blood` | `sicam-blood` | 3.10.21, Cellpose vendorizado empaquetado | 8002 |
| SALIVA ALT | `apps/segmentation-saliva-alt` | `sicam-saliva-alt` | 3.10.20, Cellpose PyPI 4.0.8 | 8003 |
| Vue/Vite | `apps/web/Frontend` | nvm | Node 24.17.0 / npm 11.13.0 | 5173 |

El baseline es CPU. No mezclar los tres ambientes Python: BLOOD fue aislado por
conflictos nativos/OpenMP, y ALT necesita Cellpose externo distinto al
vendorizado. No instalar Cellpose PyPI en `sicam` ni `sicam-blood` como arreglo.

## 2. WSL y repositorio

Desde Windows PowerShell, sólo si todavía no existe la distribución:

```powershell
wsl --install -d Ubuntu
```

Verificar o actualizar WSL2:

```powershell
wsl --update
wsl --list --verbose
wsl --set-version Ubuntu 2
wsl -d Ubuntu
```

Usar el nombre real de la distribución si difiere de `Ubuntu`. El entorno
validado es Ubuntu 26.04 LTS, WSL2, Linux x86_64. Dentro de Ubuntu:

```bash
uname -m
sudo apt update
sudo apt install -y ca-certificates curl git
mkdir -p ~/repos
cd ~/repos
git clone https://github.com/irgNemo/sicam-refactor.git
cd sicam-refactor
git status --short
```

Si ya hay checkout, usarlo sin volver a clonar ni descartar cambios. Mantener
el repositorio bajo el filesystem Linux (`~/repos`), no bajo `/mnt/c`, para I/O
y file watching. Se requiere acceso al remoto. `build-essential` sólo es
necesario si una dependencia necesita compilación nativa; el baseline se
instaló con wheels. PostgreSQL y GPU no son requisitos del setup local.

## 3. Miniconda y nvm

Instalador Miniconda del baseline validado, para Linux x86_64. En una WSL sin
Miniconda, descargar, verificar y después ejecutar:

```bash
cd /tmp
curl --fail --location --output Miniconda3-py310_26.7.1-1-Linux-x86_64.sh \
  https://repo.anaconda.com/miniconda/Miniconda3-py310_26.7.1-1-Linux-x86_64.sh
echo 'fb1af4c45e6e73fe193c2398b4346b1e45522f729cdfccfdb18f6c765954dbd9  Miniconda3-py310_26.7.1-1-Linux-x86_64.sh' | sha256sum --check
```

Continuar sólo si el checksum coincide y `~/miniconda3` no contiene ya una
instalación:

```bash
bash /tmp/Miniconda3-py310_26.7.1-1-Linux-x86_64.sh -b -p ~/miniconda3
~/miniconda3/bin/conda init bash
source ~/.bashrc
conda config --set auto_activate_base false
conda --version
```

Si Conda solicita aceptación de términos para los canales predeterminados,
el usuario debe revisarlos y aceptarlos antes de crear ambientes:

```bash
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r
```

nvm y Node del baseline, dentro de WSL:

```bash
curl --fail --location https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.7/install.sh -o /tmp/sicam-nvm-install.sh
bash /tmp/sicam-nvm-install.sh
source ~/.bashrc
nvm install 24.17.0
nvm alias default 24.17.0
nvm use 24.17.0
node --version
npm --version
```

Esperado: Node `v24.17.0`, npm `11.13.0`. No usar ejecutables de Windows para
instalar dependencias en este checkout WSL. Para VS Code: `code .` desde la
raíz del repo con la extensión WSL instalada en Windows.

## 4. Dependencias Python

### Django y SALIVA CURRENT — sicam

```bash
cd ~/repos/sicam-refactor
conda create -n sicam python=3.10.20 pip -y
conda activate sicam
python --version
python -m pip install --upgrade pip
python -m pip install torch==2.12.1+cpu --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r apps/web/Backend/requirements.txt
python -m pip install -r apps/segmentation-saliva/requirements.txt
python -m pip check
```

Django fija sus dependencias (incluidos Django 5.0.1, Pillow 10.2.0 y pytest).
CURRENT usa `segmentacion_core/cellpose`, no Cellpose PyPI. El comentario
heredado que sugiere `pip install cellpose` en sus requirements no describe
el runtime actual; no ejecutarlo. `torch` está sin pin en ese manifiesto:
preinstalar la variante CPU validada y comprobar que pip la conserve.

### BLOOD — sicam-blood

```bash
conda create -n sicam-blood python=3.10.21 pip -y
conda activate sicam-blood
cd ~/repos/sicam-refactor/apps/segmentation-blood
python --version
python -m pip install --upgrade pip
python -m pip install torch==2.12.1+cpu torchvision==0.27.1+cpu \
  --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt
python -m pip check
python -c "import cellpose; print(cellpose.__file__)"
```

**Ejecutar la instalación desde `apps/segmentation-blood`**: `requirements.txt`
contiene `-e .`, que instala el `pyproject.toml` local. El último comando debe
resolver a `apps/segmentation-blood/segmentacion_core/cellpose/__init__.py`.
No instalar desde la raíz del monorepo con un `-e .` apuntando a otro directorio.

`natsort` ya está declarado: el dependency gap previo está resuelto.
Segment Anything está fijado en el requirements a la fuente oficial:

```text
https://github.com/facebookresearch/segment-anything/archive/dca509fe793f601edb92606367a655c15ac00fdf.zip
```

No sustituirlo por la rama móvil `main`. El vendorizado usa `cpsam`; no
sustituirlo por un paquete Cellpose externo.

### SALIVA ALT — sicam-saliva-alt

Secuencia del [README ALT](../apps/segmentation-saliva-alt/README.md):

```bash
conda create -n sicam-saliva-alt python=3.10.20 pip -y
conda activate sicam-saliva-alt
cd ~/repos/sicam-refactor/apps/segmentation-saliva-alt
python -m pip install -r requirements.txt
python -m pip check
```

Este comando instala runtime **y aplica constraints**, porque la primera
directiva del requirements es `-c constraints.txt`. No omitir ese archivo:
fija también dependencias transitivas. El runtime fija Cellpose 4.0.8,
Torch 2.12.1+cpu y torchvision 0.27.1+cpu, con índice adicional CPU.

Tests opcionales:

```bash
python -m pip install -r requirements-test.txt
python -m pytest -q
```

`requirements-test.txt` incluye `-r requirements.txt` (y por ello sus constraints)
y añade pytest/httpx. Los constraints por sí solos no instalan paquetes de tests.
No instalar estas dependencias en los otros ambientes.

### Límite de reproducibilidad

CURRENT y BLOOD mantienen dependencias científicas sin pin; no hay lockfile
Python global ni definición Conda versionada. Por tanto, los comandos recrean
la instalación documentada, pero no garantizan igualdad de todas las versiones
resueltas en fechas futuras. ALT sí dispone de constraints. Si `pip check`
falla, resolver el conflicto antes de arrancar; no actualizar paquetes al azar.
Esta tarea documental no modifica requirements ni intenta cerrar ese riesgo.

## 5. Modelos externos

### CURRENT: membranas_500_125

El loader `apps/segmentation-saliva/app/services/segmentador.py` construye
exactamente esta ruta relativa al directorio del microservicio:

```text
apps/segmentation-saliva/segmentacion_core/membranas_500_125
```

Obtener una copia confiable del equipo anterior o almacenamiento autorizado.
No hay una URL pública de descarga documentada para este modelo personalizado.
Reemplazar la ruta de origen en el comando:

```bash
install -m 600 /ruta/confiable/membranas_500_125 \
  ~/repos/sicam-refactor/apps/segmentation-saliva/segmentacion_core/membranas_500_125
cd ~/repos/sicam-refactor/apps/segmentation-saliva/segmentacion_core
echo 'fa6ac42f593ac7b86d665e48e69161f427fcb11ec9dd5c02fa4a2722245d0f2c  membranas_500_125' | sha256sum --check
stat --format='%s bytes' membranas_500_125
```

Esperado: **26551763 bytes**. Está dentro del checkout por exigencia del loader,
pero ignorado por `membranas_*`: no se versiona. CURRENT carga el modelo al
importar su aplicación; no importar `app.main` para un chequeo liviano.

### BLOOD y ALT: cpsam compartido

Ambos resuelven por defecto `~/.cellpose/models/cpsam`, fuera del repo, y
admiten el directorio alternativo `CELLPOSE_LOCAL_MODELS_PATH`. Si se usa esa
variable, exportarla con la misma ruta absoluta en las terminales de ambos
servicios. No es una variable que Django deba propagar.

Artefacto validado, idéntico entre Windows y WSL:

```text
tamaño: 1233587898 bytes
SHA-256: e1440429eb384f95afe32bcba6510f90d518eaedc917ede549bed6804004abe2
```

Puede reutilizarse una copia confiable ya existente en ese cache, sin duplicar
el archivo ni incluirlo en Git. Verificarla antes de arrancar:

```bash
stat --format='%s bytes' ~/.cellpose/models/cpsam
echo "e1440429eb384f95afe32bcba6510f90d518eaedc917ede549bed6804004abe2  $HOME/.cellpose/models/cpsam" | sha256sum --check
```

Sólo si falta, descargar de la URL que declara el vendorizado BLOOD. Usar un
archivo temporal para no reemplazar un cache válido con una descarga parcial:

```bash
curl --fail --location --output /tmp/sicam-cpsam.download \
  https://huggingface.co/mouseland/cellpose-sam/resolve/main/cpsam
echo 'e1440429eb384f95afe32bcba6510f90d518eaedc917ede549bed6804004abe2  /tmp/sicam-cpsam.download' | sha256sum --check
stat --format='%s bytes' /tmp/sicam-cpsam.download
```

Continuar sólo si coinciden tamaño y checksum:

```bash
mkdir -p ~/.cellpose/models
install -m 600 /tmp/sicam-cpsam.download ~/.cellpose/models/cpsam
```

BLOOD puede descargar implícitamente el modelo si falta: provisionarlo evita
esa espera/salida de red durante startup. ALT exige versión, tamaño y hash
correctos antes de cargar; falla si faltan y no descarga ni hace fallback.
Ambos precargan durante lifespan; esperar `Application startup complete`.
La existencia de un proceso Uvicorn todavía no indica disponibilidad de `/docs`.

## 6. Configuración, base y frontend

En una instalación nueva, crear cada `.env` sólo si aún no existe:

```bash
cd ~/repos/sicam-refactor/apps/web/Backend
[ -f .env ] || cp .env.example .env
cd ~/repos/sicam-refactor/apps/web/Frontend
[ -f .env ] || cp .env.example .env
```

Revisar los valores locales; no sobrescribir configuraciones previas. Los
`.env.example` fueron auditados en lectura y permanecen intactos.

### Django

Archivo local: `apps/web/Backend/.env`. Nombres y defaults operativos reales de
`config/settings.py` y `.env.example`:

| Variable | Default / ejemplo local |
|---|---|
| `SALIVA_SEGMENTATION_SERVICE_URL` | `http://127.0.0.1:8001` |
| `SALIVA_SERVICE_TIMEOUT` | `30` segundos |
| `SALIVA_ALT_SEGMENTATION_SERVICE_URL` | `http://127.0.0.1:8003` |
| `SALIVA_ALT_SERVICE_TIMEOUT` | `240` segundos |
| `BLOOD_SEGMENTATION_SERVICE_URL` | `http://localhost:8002` |
| `BLOOD_SERVICE_TIMEOUT` | `240` segundos |
| `DEBUG` | `True`, sólo desarrollo |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1,0.0.0.0` |
| `CORS_ALLOWED_ORIGINS` | localhost y 127.0.0.1 en 5173 y 3000 |
| `LANGUAGE_CODE` | `es-mx` |
| `TIME_ZONE` | `America/Mexico_City` |

BLOOD puede configurarse localmente con `http://127.0.0.1:8002` si localhost no
resuelve al listener IPv4; el default versionado sigue siendo localhost.
`SECRET_KEY` del ejemplo es sólo de desarrollo. Mantener secretos fuera de Git.
Django agrupa CURRENT/BLOOD en `SEGMENTATION_SERVICES` (SALIVA/SANGRE) y ALT en
`SALIVA_ALT_SEGMENTATION_SERVICE`.

SQLite es el default: `apps/web/Backend/db.sqlite3`. No definir `DB_*` para ese
caso. PostgreSQL es opcional mediante `DB_ENGINE`, `DB_NAME`, `DB_USER`,
`DB_PASSWORD`, `DB_HOST`, `DB_PORT`; su driver ya está en requirements.

```bash
cd ~/repos/sicam-refactor/apps/web/Backend
conda activate sicam
python manage.py migrate
python manage.py showmigrations
python manage.py check
```

Aplicar todas las migraciones versionadas, sin una lista rígida ni
`makemigrations` durante instalación. Existe `0007_saliva_segmentation_strategy`:
backfill CURRENT para históricos SALIVA, provenance NULL para BLOOD.
El comando `showmigrations` debe mostrar las migraciones aplicadas.
Superusuario opcional: `python manage.py createsuperuser`.

### Frontend

`apps/web/Frontend/.env` necesita:

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Vite no carga `.env.example`; reiniciarlo si cambia `.env`. El frontend llama
Django, no directamente los puertos de segmentación.

```bash
cd ~/repos/sicam-refactor/apps/web/Frontend
nvm use 24.17.0
npm ci
npm run build
```

`npm ci` respeta el `package-lock.json` versionado. No ejecutar `npm audit fix`
ni `npm install axios`: Axios ya está declarado. No hay script `npm test`;
la suite frontend se ejecuta con `node --test tests/*.test.mjs`.
`npm run lint` usa `--fix --cache` y modifica archivos; para revisión sin fixes:
`node_modules/.bin/eslint .`.

## 7. Validación sin inferencias

En cada ambiente Python, ejecutar `python --version` y `python -m pip check`.
No importar las aplicaciones FastAPI para comprobar sólo rutas. Confirmar
los entrypoints desde la raíz del repo:

```bash
cd ~/repos/sicam-refactor
ls apps/web/Backend/manage.py apps/web/Frontend/package.json \
  apps/segmentation-saliva/app/main.py \
  apps/segmentation-blood/main.py \
  apps/segmentation-saliva-alt/app/main.py
```

En `sicam-blood`, `python -c "import cellpose; print(cellpose.__file__)"`
comprueba el empaquetado sin construir el modelo. En `sicam-saliva-alt`:

```bash
python -c "from importlib.metadata import version; print(version('cellpose'))"
```

Debe indicar `4.0.8`. No depender de `cellpose.__version__`, que ese paquete
no expone. Pruebas backend (usan base de prueba y HTTP simulado):

```bash
cd ~/repos/sicam-refactor/apps/web/Backend
conda activate sicam
python -m pytest -q
python manage.py test
```

Los tests opcionales ALT usan modelo simulado. Pasar estos checks no sustituye
una inferencia real ni validación científica. Ningún comando de esta sección
debe descargar modelos.

## 8. Primer arranque y operación

Seguir el [manual cotidiano](30_developer_startup_and_test_data.md) para los
**cinco procesos** completos, checks HTTP, apagado y selección del subconjunto
necesario. Allí se detallan también `seed_demo_data`, carga manual y smoke UI.

BLOOD usa inequívocamente **`main:app`**, desde `apps/segmentation-blood`.
CURRENT y ALT usan `app.main:app` en sus respectivos directorios.

ALT observó unos 170–180 s en CPU con una micrografía de 4928×4928. BLOOD puede
ser lento en CPU. Son referencias de muestras concretas, no SLA ni garantías.
Characterization no necesita microservicio adicional cuando ya hay resultados
y las imágenes requeridas disponibles.

## 9. Riesgos y evidencia

- Resueltos: `natsort` BLOOD declarado, Segment Anything fijado a commit,
  modelos verificados y migración Windows → WSL validada.
- Pendiente como requisito de cada máquina nueva: conseguir la copia autorizada
  del modelo CURRENT y provisionar cpsam. No son bloqueos del código actual.
- Limitación real: dependencias científicas CURRENT/BLOOD parcialmente sin pin.
- No versionar `.env`, SQLite, `media/`, pesos, cachés, `node_modules/` ni `dist/`.
- Mantener CPU; GPU no está habilitado por estos comandos ni requiere instalar
  CUDA para desarrollo local.

Evidencia histórica de instalación: [handoff de migración](CODEX_HANDOFF_SICAM.md).
Evidencia ALT/backend/frontend: [18A](58_sprint_18a_alt_saliva_segmentation_service.md),
[18B](59_sprint_18b_backend_saliva_segmentation_strategies.md),
[18C](60_sprint_18c_frontend_saliva_strategy_selector.md).
Esos registros no sustituyen las instrucciones operativas de esta guía.
