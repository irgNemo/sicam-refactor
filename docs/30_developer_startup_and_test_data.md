# Developer Startup and Minimum Test Data

## Proposito

Esta guia es el manual operativo canonico para levantar localmente el monorepo
`sicam-refactor`, preparar datos minimos y validar el flujo actual:

```text
Frontend Vue -> Django REST -> microservicios FastAPI -> persistencia en Django
```

Componentes ejecutables actuales:

- Frontend Vue/Vite en `apps/web/Frontend`.
- Backend Django en `apps/web/Backend`.
- Microservicio FastAPI SALIVA en `apps/segmentation-saliva`.
- Microservicio FastAPI BLOOD/SANGRE en `apps/segmentation-blood`.

La caracterizacion no es un microservicio separado. Vive dentro del backend
Django y usa resultados de segmentacion persistidos; no reejecuta Cellpose.

No se incluyen datos clinicos reales, modelos pesados, `db.sqlite3`, `media/`,
secretos ni credenciales.

## Convencion de rutas

En esta guia:

```text
<REPO>
```

representa la raiz local de `sicam-refactor`.

Ejemplo:

```powershell
cd "<REPO>\apps\web\Backend"
```

No hardcodear rutas personales en documentacion, scripts o configuracion
versionada.

## Requisitos previos

- Windows con `cmd.exe` o PowerShell.
- Conda/Miniconda.
- Entorno `sicam` para Django y SALIVA.
- Entorno `sicam-blood` para BLOOD/SANGRE.
- Node compatible con `apps/web/Frontend/package.json`:

```text
^20.19.0 || >=22.12.0
```

Versiones observadas durante la ultima actualizacion del manual:

| Herramienta | Version observada |
|---|---|
| `sicam` Python | `Python 3.10.20` |
| `sicam-blood` Python | `Python 3.10.21` |
| Node | `v24.17.0` |
| npm | `11.13.0` |

Los comandos rapidos usan `conda run -n <env> ...` porque funcionan tanto en
`cmd.exe` como en PowerShell cuando `conda` esta en `PATH`.

Si `conda` no se reconoce en PowerShell, usar el ejecutable explicito:

```powershell
& "$env:USERPROFILE\miniconda3\Scripts\conda.exe" run -n sicam python --version
```

Si se usa `cmd.exe`, usar:

```cmd
"%USERPROFILE%\miniconda3\Scripts\conda.exe" run -n sicam python --version
```

Evitar ejecutar varios `conda run` en paralelo desde la misma sesion
automatizada; Conda puede colisionar con archivos temporales. Para operar SICAM,
usar una terminal por servicio.

## Estado real del dominio

El flujo de datos actual es:

```text
Paciente -> Caso -> AnalisisPred -> MuestraSaliva/MuestraSangre
-> ResultadoSegmentacion -> RevisionSegmentacion
-> ResultadoCaracterizacion
```

Modelos principales:

| Modelo | Relacion | Uso |
|---|---|---|
| `Paciente` | raiz | Datos basicos de paciente. |
| `Caso` | `paciente -> Paciente` | Agrupa analisis de un paciente. |
| `AnalisisPred` | `id_paciente_fk -> Paciente`, `id_caso_fk -> Caso` | Contenedor de muestras. |
| `MuestraSaliva` | `analisis -> AnalisisPred` | Imagen de saliva. |
| `MuestraSangre` | `analisis -> AnalisisPred` | Imagen de sangre. |
| `ResultadoSegmentacion` | `muestra` o `muestra_sangre` | Guarda respuesta cruda y normalizada. |
| `RevisionSegmentacion` | `resultado_segmentacion -> ResultadoSegmentacion` | BORRADOR/VALIDADA experto. |
| `ResultadoCaracterizacion` | `resultado_segmentacion -> ResultadoSegmentacion` | Caracterizacion del resultado efectivo. |

Campos minimos para datos demo:

| Modelo | Campos obligatorios |
|---|---|
| `Paciente` | `nombre`, `apellido`, `fecha_nacimiento`, `identificacion` |
| `Caso` | `paciente`, `titulo` |
| `AnalisisPred` | `id_paciente_fk`, `id_caso_fk` |
| `MuestraSaliva` | `analisis`, `imagen` |
| `MuestraSangre` | `analisis`, `imagen` |

## Inicio rapido del sistema completo

Orden operativo recomendado:

1. Microservicio SALIVA.
2. Microservicio BLOOD/SANGRE.
3. Backend Django.
4. Frontend Vue/Vite.

Django puede arrancar antes que los microservicios, pero este orden deja todo
disponible antes de usar la interfaz. En una instalacion con PostgreSQL externo,
PostgreSQL debe estar disponible antes de iniciar Django.

### Tabla rapida

| Orden | Servicio | Entorno | Puerto | Verificacion |
|---|---|---|---|---|
| 1 | SALIVA FastAPI | `sicam` | `8001` | `http://127.0.0.1:8001/docs` |
| 2 | BLOOD FastAPI | `sicam-blood` | `8002` | `http://127.0.0.1:8002/docs` |
| 3 | Django REST | `sicam` | `8000` | `http://127.0.0.1:8000/api/` |
| 4 | Vue/Vite | Node/npm | `5173` | `http://localhost:5173` |

### Terminal 1 - Segmentacion SALIVA

```powershell
cd "<REPO>\apps\segmentation-saliva"
conda run -n sicam python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

Opcion de desarrollo con recarga:

```powershell
conda run -n sicam python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

Verificar:

```text
http://127.0.0.1:8001/docs
```

### Terminal 2 - Segmentacion BLOOD/SANGRE

```powershell
cd "<REPO>\apps\segmentation-blood"
conda run -n sicam-blood python -m uvicorn main:app --host 127.0.0.1 --port 8002
```

Verificar:

```text
http://127.0.0.1:8002/docs
```

El primer arranque requiere que el modelo externo `cpsam` ya exista en:

```text
%USERPROFILE%\.cellpose\models\cpsam
```

### Terminal 3 - Backend Django

```powershell
cd "<REPO>\apps\web\Backend"
conda run -n sicam python manage.py runserver 127.0.0.1:8000
```

Verificar:

```text
http://127.0.0.1:8000/api/
http://127.0.0.1:8000/api/pacientes/
http://127.0.0.1:8000/api/analisis/
```

La raiz `http://127.0.0.1:8000/` puede responder 404 sin indicar que el
backend este caido; validar contra endpoints `/api/`.

### Terminal 4 - Frontend Vue/Vite

```powershell
cd "<REPO>\apps\web\Frontend"
npm run dev
```

Verificar:

```text
http://localhost:5173
```

Antes del primer `npm run dev`, crear el archivo local `.env` como se indica en
la seccion de Frontend. Reiniciar Vite despues de crear o modificar `.env`.

## Variables de entorno

### Backend

Archivo de ejemplo:

```text
apps/web/Backend/.env.example
```

Crear `.env` local:

```powershell
cd "<REPO>\apps\web\Backend"
Copy-Item .env.example .env
```

Variables relevantes para desarrollo:

```text
SECRET_KEY=django-insecure-change-this-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000
SALIVA_SEGMENTATION_SERVICE_URL=http://localhost:8001
SALIVA_SERVICE_TIMEOUT=30
BLOOD_SEGMENTATION_SERVICE_URL=http://localhost:8002
BLOOD_SERVICE_TIMEOUT=240
LANGUAGE_CODE=es-mx
TIME_ZONE=America/Mexico_City
```

No commitear `.env`.

### Frontend

Archivo de ejemplo:

```text
apps/web/Frontend/.env.example
```

Crear `.env` local:

```powershell
cd "<REPO>\apps\web\Frontend"
Copy-Item .env.example .env
```

Variable requerida:

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Vite no carga `.env.example` automaticamente. `VITE_API_BASE_URL` debe apuntar
al backend Django. Si se crea o modifica `.env` mientras Vite ya esta corriendo,
detener y reiniciar `npm run dev`.

## Preparacion del backend Django

Directorio:

```powershell
cd "<REPO>\apps\web\Backend"
```

Instalar dependencias si hace falta:

```powershell
conda run -n sicam python -m pip install -r requirements.txt
```

Aplicar migraciones:

```powershell
conda run -n sicam python manage.py migrate
```

Migraciones actuales de `api`:

```text
0001_initial.py
0002_resultadosegmentacion.py
0003_resultadosegmentacion_resultado_normalizado.py
0004_revisionsegmentacion_and_more.py
0005_alter_resultadosegmentacion_muestra_muestrasangre_and_more.py
0006_resultadocaracterizacion_and_more.py
```

Despues de `git pull`, ejecutar normalmente:

```powershell
conda run -n sicam python manage.py migrate
conda run -n sicam python manage.py check
```

Si se agregan migraciones en un sprint futuro, deben aplicarse antes de usar la
UI.

Crear superusuario opcional:

```powershell
conda run -n sicam python manage.py createsuperuser
```

Base de datos local por defecto: SQLite (`db.sqlite3`). En despliegue objetivo
puede usarse PostgreSQL configurando variables `DB_*`; PostgreSQL no es un
servicio obligatorio para el desarrollo local actual.

## Preparacion del entorno BLOOD

Crear el entorno aislado si no existe:

```powershell
conda create -n sicam-blood python=3.10 pip -y
```

Verificar version:

```powershell
conda run -n sicam-blood python --version
```

Instalar dependencias desde el directorio del microservicio:

```powershell
cd "<REPO>\apps\segmentation-blood"
conda run -n sicam-blood python -m pip install -r requirements.txt
```

`sicam-blood` debe mantenerse como runtime separado para BLOOD/SANGRE. El
runtime `sicam` se conserva para Django y SALIVA.

## Datos minimos reproducibles

Metodo recomendado:

```powershell
cd "<REPO>\apps\web\Backend"
conda run -n sicam python manage.py seed_demo_data
```

El comando crea o reutiliza:

- `Paciente` ficticio con `identificacion=SICAM-DEMO-001`;
- `Caso` ficticio;
- `AnalisisPred`;
- `MuestraSaliva`;
- imagen sintetica minima dentro de `MEDIA_ROOT`.

El comando es seguro para ejecuciones repetidas:

- no elimina datos;
- no sobrescribe datos existentes;
- no descarga archivos;
- no agrega imagenes al repositorio;
- no usa datos clinicos reales.

Usar una imagen local propia de prueba:

```powershell
conda run -n sicam python manage.py seed_demo_data --image "C:\ruta\local\imagen_demo.png"
```

Poblar galeria con varias imagenes locales de saliva:

```powershell
conda run -n sicam python manage.py seed_demo_data --image-dir "C:\DatosSICAM\saliva"
```

Combinar `--image` y `--image-dir`:

```powershell
conda run -n sicam python manage.py seed_demo_data --image "C:\DatosSICAM\saliva\extra.png" --image-dir "C:\DatosSICAM\saliva"
```

`--image-dir` procesa archivos directos del directorio, sin busqueda recursiva,
en orden alfabetico. Extensiones soportadas:

```text
.jpg
.jpeg
.png
.tif
.tiff
```

El comando mantiene idempotencia por nombre base de archivo dentro del
`AnalisisPred` demo. Si se ejecuta otra vez con la misma carpeta, no crea
duplicados. Si se agrega una imagen nueva, solo crea la nueva `MuestraSaliva`.

Archivos con extensiones no soportadas se ignoran y se contabilizan en el
resumen. Una carpeta vacia no produce error.

Las imagenes se copian a `apps/web/Backend/media/` mediante `ImageField`.
`media/` es local, esta ignorada por Git y no debe versionarse.

## Carga manual desde frontend

Flujo funcional en la UI:

1. Abrir `Registro`.
2. Crear un paciente.
3. Crear un caso y dejar marcada la opcion de crear analisis automaticamente.
4. Ir a `Agregar Imagenes`.
5. Seleccionar tipo de muestra, paciente, caso y analisis.
6. Subir una o mas imagenes.
7. Volver a `Segmentacion`.
8. Buscar el paciente en el sidebar.
9. Seleccionar el caso.
10. Confirmar que la galeria muestra imagenes.

Endpoints Django REST usados por el frontend:

```text
POST /api/pacientes/
POST /api/casos/
POST /api/analisis/
POST /api/muestras/
POST /api/muestras-sangre/
```

## Almacenamiento de archivos subidos

Configuracion actual:

```text
MEDIA_URL=/media/
MEDIA_ROOT=apps/web/Backend/media
```

En desarrollo, `config/urls.py` sirve `MEDIA_URL` cuando `DEBUG=True`.

No versionar:

```text
apps/web/Backend/media/
db.sqlite3
```

## Microservicio de saliva

Proposito: segmentar imagenes de saliva.

Directorio:

```powershell
cd "<REPO>\apps\segmentation-saliva"
```

Entorno:

```text
sicam
```

Instalacion:

```powershell
conda run -n sicam python -m pip install -r requirements.txt
```

Entrypoint:

```text
app.main:app
```

Comando de ejecucion:

```powershell
conda run -n sicam python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

Puerto:

```text
8001
```

Verificacion:

```text
http://127.0.0.1:8001/docs
http://127.0.0.1:8001/openapi.json
```

Endpoint consumido por Django:

```text
POST /segmentar
```

Django envia multipart con campo:

```text
file
```

### Modelo externo SALIVA

El microservicio de saliva espera:

```text
apps/segmentation-saliva/segmentacion_core/membranas_500_125
```

Este artefacto es externo y esta ignorado por Git. No debe agregarse al
repositorio sin decision explicita. Si falta, el servicio puede fallar al
arrancar o al ejecutar segmentacion real.

## Microservicio BLOOD/SANGRE

Proposito: segmentar imagenes de sangre.

Directorio:

```powershell
cd "<REPO>\apps\segmentation-blood"
```

Entorno:

```text
sicam-blood
```

`sicam-blood` existe separado de `sicam` por un conflicto binario/OpenMP
detectado durante la recuperacion del runtime BLOOD. No ejecutar BLOOD en el
entorno `sicam`.

Instalacion:

```powershell
conda run -n sicam-blood python -m pip install -r requirements.txt
```

`requirements.txt` instala tambien el Cellpose vendorizado via `-e .`.
`pyproject.toml` expone:

```text
apps/segmentation-blood/segmentacion_core/cellpose
```

como paquete importable `cellpose`.

No instalar `cellpose` externo desde PyPI para BLOOD salvo una decision tecnica
explicita.

Entrypoint:

```text
main:app
```

Comando de ejecucion:

```powershell
conda run -n sicam-blood python -m uvicorn main:app --host 127.0.0.1 --port 8002
```

Puerto:

```text
8002
```

Verificacion:

```text
http://127.0.0.1:8002/docs
http://127.0.0.1:8002/openapi.json
```

Endpoint real del microservicio:

```text
POST /api/v1/segmentar
```

Django envia multipart con campo:

```text
file
```

### Dependencias BLOOD especiales

BLOOD usa:

- Cellpose vendorizado en `segmentacion_core/cellpose`.
- `segment-anything` desde la implementacion oficial
  `facebookresearch/segment-anything`.
- PyTorch/torchvision CPU-only.
- Modelo externo `cpsam`.

En `docs/47_hotfix_16b_blood_cellpose_runtime.md` se registro que el dry-run de
`segment-anything` resolvio el repositorio oficial a:

```text
dca509fe793f601edb92606367a655c15ac00fdf
```

### Modelo externo BLOOD `cpsam`

Ubicacion estandar validada:

```text
%USERPROFILE%\.cellpose\models\cpsam
```

URL oficial validada:

```text
https://huggingface.co/mouseland/cellpose-sam/resolve/main/cpsam
```

SHA-256 validado:

```text
E1440429EB384F95AFE32BCBA6510F90D518EAEDC917EDE549BED6804004ABE2
```

Tamano observado:

```text
1233587898 bytes
```

Es aproximadamente 1.23 GB. No versionar `cpsam` ni modelos pesados.

Referencia de startup observada en `docs/47`: el modelo cargo en unos segundos
y el servicio alcanzo `/docs`; estos tiempos son referencias locales, no una
garantia.

## Frontend Vue/Vite

Proposito: interfaz de registro, segmentacion, edicion experta, historial y
caracterizacion.

Directorio:

```powershell
cd "<REPO>\apps\web\Frontend"
```

Instalacion:

```powershell
npm install
```

Configuracion local:

```powershell
Copy-Item .env.example .env
```

Verificar en `.env`:

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Ejecucion:

```powershell
npm run dev
```

Puerto esperado:

```text
http://localhost:5173
```

Validacion de build:

```powershell
npm run build
```

## Caracterizacion

La caracterizacion pertenece al backend Django.

No requiere:

- un quinto servicio;
- `uvicorn` adicional;
- nuevo puerto;
- nuevo entorno Conda;
- ejecucion de Cellpose.

Endpoints relacionados:

```text
POST /api/resultados-segmentacion/{id}/caracterizar/
GET /api/resultados-segmentacion/{id}/caracterizaciones/
```

La caracterizacion usa el resultado efectivo:

- revision `VALIDADA`, si existe;
- resultado automatico, si no existe revision validada.

## Verificacion en API y frontend

Despues de ejecutar `seed_demo_data`, validar:

```text
GET http://127.0.0.1:8000/api/pacientes/
GET http://127.0.0.1:8000/api/casos/
GET http://127.0.0.1:8000/api/analisis/
GET http://127.0.0.1:8000/api/muestras/
GET http://127.0.0.1:8000/api/muestras-sangre/
```

En frontend:

1. Abrir `Segmentacion`.
2. Buscar `Demo SICAM` o `SICAM-DEMO-001`.
3. Seleccionar el caso demo.
4. Confirmar que la galeria muestra imagenes.

## Ejecucion de segmentacion

Desde frontend:

1. Seleccionar tipo `Saliva` o `Sangre`.
2. Seleccionar la muestra en la galeria.
3. Presionar `Ejecutar segmentacion`.
4. Django llama:

```text
POST /api/muestras/{id}/segmentar/
POST /api/muestras-sangre/{id}/segmentar/
```

5. Django orquesta el microservicio correspondiente:

```text
POST http://localhost:8001/segmentar
POST http://localhost:8002/api/v1/segmentar
```

6. Si la respuesta es valida, Django crea un `ResultadoSegmentacion`.

La inferencia BLOOD en CPU tardo aproximadamente 120 segundos por imagen durante
smoke tests reales. Django usa `BLOOD_SERVICE_TIMEOUT=240` para dar margen.

## Consulta de resultados historicos

Endpoints:

```text
GET /api/muestras/{id}/resultados-segmentacion/
GET /api/muestras-sangre/{id}/resultados-segmentacion/
```

El frontend los consume al seleccionar muestra y despues de una segmentacion
exitosa.

## Diagnostico visual del overlay

Cuando exista `resultado_normalizado`, el frontend muestra:

- total de objetos;
- conteo por etiqueta;
- lista compacta de objetos;
- overlay SVG;
- controles por etiqueta;
- diagnostico textual de escala.

Para validar alineacion:

1. Seleccionar una muestra con resultado normalizado.
2. Activar `Diagnostico visual`.
3. Revisar:
   - borde base del SVG;
   - caja visible real de la imagen;
   - bounding box de poligonos visibles.

## Caracterizacion desde la UI

Flujo actual:

1. Abrir `Caracterizacion`.
2. Mantener o seleccionar paciente/caso desde el `SideBar`.
3. Elegir `Saliva` o `Sangre`.
4. Seleccionar una muestra.
5. Seleccionar un resultado de segmentacion `COMPLETADO`.
6. Presionar `Caracterizar`.
7. Revisar la caracterizacion vigente.

La UI no muestra diagnostico clinico ni exporta reportes en este sprint.

## Detener servicios

En cada terminal donde haya un servidor activo:

```text
Ctrl+C
```

Servicios habituales:

- SALIVA `uvicorn`;
- BLOOD `uvicorn`;
- Django `runserver`;
- Vite `npm run dev`.

## Solucion de problemas frecuentes

### `conda` no se reconoce

Usar la ruta explicita del ejecutable:

```powershell
& "$env:USERPROFILE\miniconda3\Scripts\conda.exe" run -n sicam python --version
```

Si se usa `cmd.exe`:

```cmd
"%USERPROFILE%\miniconda3\Scripts\conda.exe" run -n sicam python --version
```

### La galeria muestra cero imagenes

Verificar:

```powershell
cd "<REPO>\apps\web\Backend"
conda run -n sicam python manage.py seed_demo_data
```

Y confirmar:

```text
GET /api/analisis/
```

Debe existir al menos un `AnalisisPred` con muestras.

### La imagen no carga en frontend

Verificar:

- Django corre con `DEBUG=True`;
- `MEDIA_URL=/media/`;
- el archivo existe en `apps/web/Backend/media/`;
- el navegador puede abrir la URL de `imagen` que devuelve la API.

### `Ejecutar segmentacion` falla con servicio SALIVA no disponible

Verificar:

- `SALIVA_SEGMENTATION_SERVICE_URL=http://localhost:8001`;
- FastAPI de saliva esta corriendo;
- `http://127.0.0.1:8001/docs` abre;
- existe `apps/segmentation-saliva/segmentacion_core/membranas_500_125`.

### `ModuleNotFoundError: cellpose` en BLOOD

Instalar dependencias desde `apps/segmentation-blood`:

```powershell
conda run -n sicam-blood python -m pip install -r requirements.txt
```

`pyproject.toml` debe exponer el Cellpose vendorizado como paquete `cellpose`.
No instalar `cellpose` externo desde PyPI como arreglo rapido.

### `cpsam` faltante

Verificar:

```text
%USERPROFILE%\.cellpose\models\cpsam
```

Si falta, provisionar el modelo por mecanismo controlado usando la URL oficial
validada y verificar SHA-256 antes de operar.

### Conflicto OpenMP en BLOOD

No ejecutar BLOOD en el entorno `sicam`. Usar `sicam-blood`.

No recomendar `KMP_DUPLICATE_LIB_OK=TRUE` como solucion operativa. Aunque el
legacy lo contiene, el runtime recuperado se aislo en `sicam-blood` para evitar
depender de ese parche.

### BLOOD tarda varios minutos

La inferencia BLOOD en CPU puede tardar alrededor de 120 segundos por imagen.
Django tiene `BLOOD_SERVICE_TIMEOUT=240`. Si se rebasa ese tiempo, revisar carga
del equipo, tamano de imagen y disponibilidad de `cpsam`.

### El overlay no aparece

Verificar:

- existe `ResultadoSegmentacion`;
- el resultado incluye `resultado_normalizado`;
- `resultado_normalizado.objects` contiene objetos con `geometry.type="polygon"`;
- cada geometria tiene al menos tres puntos validos.

### Caracterizacion no aparece

Verificar:

- existe un `ResultadoSegmentacion` con `estado="COMPLETADO"`;
- el endpoint `POST /api/resultados-segmentacion/{id}/caracterizar/` responde;
- el endpoint `GET /api/resultados-segmentacion/{id}/caracterizaciones/`
  devuelve una caracterizacion con `vigente=true`.

No levantar ningun servicio adicional para caracterizacion.

## Validaciones recomendadas

Backend:

```powershell
cd "<REPO>\apps\web\Backend"
conda run -n sicam python manage.py check
conda run -n sicam python manage.py makemigrations --check
conda run -n sicam python -m pytest
conda run -n sicam python manage.py test
```

Frontend:

```powershell
cd "<REPO>\apps\web\Frontend"
npm run build
```

SALIVA liviano:

```powershell
cd "<REPO>\apps\segmentation-saliva"
conda run -n sicam python -m compileall -q app segmentacion_core
conda run -n sicam python -m uvicorn --version
```

BLOOD liviano, sin cargar Cellpose:

```powershell
cd "<REPO>\apps\segmentation-blood"
conda run -n sicam-blood python -m compileall -q app segmentacion_core
conda run -n sicam-blood python -c "import main; print('blood main import ok')"
conda run -n sicam-blood python -m uvicorn --version
```

No usar estas validaciones livianas como sustituto de smoke tests reales cuando
se cambien dependencias runtime o algoritmos.

## Politica de archivos locales y pesados

No versionar:

- `.env`;
- `db.sqlite3`;
- `media/`;
- `node_modules/`;
- `dist/`;
- caches;
- imagenes clinicas reales;
- `membranas_500_125`;
- `cpsam`;
- modelos, pesos o artefactos pesados.

## Regla de mantenimiento del manual

Revisar este documento cuando cambie cualquiera de:

- servicio ejecutable;
- puerto;
- entorno;
- entrypoint;
- dependencia runtime;
- modelo externo;
- variable de entorno;
- migracion requerida;
- orden de inicializacion;
- comando de ejecucion.

## Notas de seguridad

- No usar datos clinicos reales para demos.
- No commitear `.env`.
- No commitear `db.sqlite3`.
- No commitear `media/`.
- No commitear modelos, pesos ni artefactos pesados.
- No modificar `cellpose/` sin autorizacion explicita.
