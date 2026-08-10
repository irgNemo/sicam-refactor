# Developer Startup and Minimum Test Data

## Proposito

Esta guia documenta como levantar localmente el monorepo `sicam-refactor` y como poblar datos minimos para validar el flujo:

```text
Frontend Vue -> Django REST -> microservicio FastAPI de saliva -> persistencia en Django
```

El objetivo es poder mostrar al menos una muestra en la galeria del frontend y habilitar la validacion manual del overlay SVG.

No se incluyen datos clinicos reales, modelos pesados, `db.sqlite3`, `media/`, secretos ni credenciales.

## Ruta del repositorio

Ruta usada durante esta iteracion:

```text
C:\Users\israe\OneDrive - Universidad de Guadalajara\Documents\SICAM\sicam-refactor
```

## Requisitos previos

- Windows con PowerShell.
- Conda con el entorno local:

```text
C:\Users\israe\miniconda3\envs\sicam
```

- Python esperado:

```text
Python 3.10.x
```

- Node compatible con `apps/web/Frontend/package.json`:

```text
^20.19.0 || >=22.12.0
```

- Dependencias instaladas para:
  - `apps/web/Backend`
  - `apps/web/Frontend`
  - `apps/segmentation-saliva`

## Estructura real del dominio

El flujo de datos actual no debe asumirse; segun el codigo vigente es:

```text
Paciente -> Caso -> AnalisisPred -> MuestraSaliva -> ResultadoSegmentacion
```

Modelos principales:

| Modelo | Relacion | Uso |
|---|---|---|
| `Paciente` | raiz | Datos basicos de paciente. |
| `Caso` | `paciente -> Paciente` | Agrupa analisis de un paciente. |
| `AnalisisPred` | `id_paciente_fk -> Paciente`, `id_caso_fk -> Caso` | Contenedor que expone `muestras_saliva` al frontend. |
| `MuestraSaliva` | `analisis -> AnalisisPred` | Guarda la imagen subida. |
| `ResultadoSegmentacion` | `muestra -> MuestraSaliva` | Guarda `respuesta_json` y `resultado_normalizado`. |

Campos minimos para datos demo:

| Modelo | Campos obligatorios |
|---|---|
| `Paciente` | `nombre`, `apellido`, `fecha_nacimiento`, `identificacion` |
| `Caso` | `paciente`, `titulo` |
| `AnalisisPred` | `id_paciente_fk`, `id_caso_fk` |
| `MuestraSaliva` | `analisis`, `imagen` |

## Variables de entorno

### Backend

Archivo de ejemplo:

```text
apps/web/Backend/.env.example
```

Para desarrollo local se puede copiar a `.env`:

```powershell
Copy-Item .env.example .env
```

Variables relevantes:

```text
SECRET_KEY=django-insecure-change-this-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000
SALIVA_SEGMENTATION_SERVICE_URL=http://localhost:8001
SALIVA_SERVICE_TIMEOUT=30
BLOOD_SEGMENTATION_SERVICE_URL=http://localhost:8002
BLOOD_SERVICE_TIMEOUT=30
```

No commitear `.env`.

### Frontend

Archivo de ejemplo:

```text
apps/web/Frontend/.env.example
```

Variable requerida:

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## Preparacion del backend

Desde:

```powershell
cd "C:\Users\israe\OneDrive - Universidad de Guadalajara\Documents\SICAM\sicam-refactor\apps\web\Backend"
```

Usar Python del entorno `sicam`:

```powershell
& "C:\Users\israe\miniconda3\envs\sicam\python.exe" --version
```

Instalar dependencias si hace falta:

```powershell
& "C:\Users\israe\miniconda3\envs\sicam\python.exe" -m pip install -r requirements.txt
```

Aplicar migraciones:

```powershell
& "C:\Users\israe\miniconda3\envs\sicam\python.exe" manage.py migrate
```

Crear superusuario opcional:

```powershell
& "C:\Users\israe\miniconda3\envs\sicam\python.exe" manage.py createsuperuser
```

Arrancar Django:

```powershell
& "C:\Users\israe\miniconda3\envs\sicam\python.exe" manage.py runserver 127.0.0.1:8000
```

Puerto esperado:

```text
http://127.0.0.1:8000
```

Comprobaciones:

```text
http://127.0.0.1:8000/api/
http://127.0.0.1:8000/api/pacientes/
http://127.0.0.1:8000/api/analisis/
```

## Datos minimos reproducibles

El metodo recomendado es el management command:

```powershell
& "C:\Users\israe\miniconda3\envs\sicam\python.exe" manage.py seed_demo_data
```

Este comando crea, si no existen:

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

Para usar una imagen local propia de prueba:

```powershell
& "C:\Users\israe\miniconda3\envs\sicam\python.exe" manage.py seed_demo_data --image "C:\ruta\local\imagen_demo.png"
```

La imagen se copia a `apps/web/Backend/media/` mediante `ImageField`. La carpeta `media/` esta ignorada por Git.

## Carga manual desde frontend

Tambien existe un flujo funcional en la UI:

1. Abrir `Registro`.
2. Crear un paciente.
3. Crear un caso y dejar marcada la opcion de crear analisis automaticamente.
4. Ir a `Agregar Imagenes`.
5. Seleccionar paciente, caso y analisis.
6. Subir una o mas imagenes.
7. Volver a `Segmentacion`.
8. Buscar el paciente en el sidebar.
9. Seleccionar el caso.
10. Confirmar que la galeria muestra imagenes.

Este flujo usa endpoints Django REST:

```text
POST /api/pacientes/
POST /api/casos/
POST /api/analisis/
POST /api/muestras/
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

Directorio:

```powershell
cd "C:\Users\israe\OneDrive - Universidad de Guadalajara\Documents\SICAM\sicam-refactor\apps\segmentation-saliva"
```

Comando esperado:

```powershell
& "C:\Users\israe\miniconda3\envs\sicam\python.exe" -m uvicorn app.main:app --reload --port 8001
```

Puerto esperado:

```text
http://127.0.0.1:8001
```

Comprobaciones:

```text
http://127.0.0.1:8001/docs
http://127.0.0.1:8001/openapi.json
```

Endpoint consumido por Django:

```text
POST /segmentar
```

El cliente Django envia multipart con campo:

```text
file
```

### Modelo externo requerido

El microservicio de saliva carga:

```text
apps/segmentation-saliva/segmentacion_core/membranas_500_125
```

Este artefacto es externo y esta ignorado por Git. No debe agregarse al repositorio sin decision explicita.

Si falta este modelo, el microservicio puede fallar al arrancar o al ejecutar segmentacion real.

## Frontend Vue/Vite

Directorio:

```powershell
cd "C:\Users\israe\OneDrive - Universidad de Guadalajara\Documents\SICAM\sicam-refactor\apps\web\Frontend"
```

Instalar dependencias si hace falta:

```powershell
npm install
```

Arrancar Vite:

```powershell
npm run dev
```

Puerto esperado:

```text
http://127.0.0.1:5173
```

Verificar que `.env` o `.env.local` tenga:

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## Orden recomendado de arranque

Orden recomendado:

1. Django backend en `127.0.0.1:8000`.
2. Microservicio de saliva en `127.0.0.1:8001`.
3. Frontend Vite en `127.0.0.1:5173`.

El orden no es obligatorio para inspeccionar UI, pero si se quiere ejecutar segmentacion desde frontend, Django debe estar disponible y el microservicio de saliva debe responder.

## Verificacion en API y frontend

Despues de ejecutar `seed_demo_data`, validar:

```text
GET http://127.0.0.1:8000/api/pacientes/
GET http://127.0.0.1:8000/api/casos/
GET http://127.0.0.1:8000/api/analisis/
GET http://127.0.0.1:8000/api/muestras/
```

En frontend:

1. Abrir `Segmentacion`.
2. Buscar `Demo SICAM` o `SICAM-DEMO-001`.
3. Seleccionar el caso demo.
4. Confirmar que la galeria muestra una imagen.

## Ejecucion de segmentacion

Desde frontend:

1. Seleccionar la muestra en la galeria.
2. Presionar `Ejecutar segmentacion`.
3. Django llama:

```text
POST /api/muestras/{id}/segmentar/
```

4. Django orquesta el microservicio de saliva:

```text
POST http://localhost:8001/segmentar
```

5. Si la respuesta es valida, Django crea un `ResultadoSegmentacion`.

## Consulta de resultados historicos

Endpoint:

```text
GET /api/muestras/{id}/resultados-segmentacion/
```

El frontend lo consume al seleccionar muestra y despues de una segmentacion exitosa.

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

## Solucion de problemas frecuentes

### La galeria muestra cero imagenes

Verificar:

```powershell
& "C:\Users\israe\miniconda3\envs\sicam\python.exe" manage.py seed_demo_data
```

Y confirmar:

```text
GET /api/analisis/
```

Debe existir al menos un `AnalisisPred` con `muestras_saliva`.

### La imagen no carga en frontend

Verificar:

- Django corre con `DEBUG=True`;
- `MEDIA_URL=/media/`;
- el archivo existe en `apps/web/Backend/media/`;
- el navegador puede abrir la URL de `imagen` que devuelve `/api/muestras/`.

### `Ejecutar segmentacion` falla con servicio no disponible

Verificar:

- `SALIVA_SEGMENTATION_SERVICE_URL=http://localhost:8001`;
- FastAPI de saliva esta corriendo;
- `http://127.0.0.1:8001/docs` abre.

### El microservicio de saliva no arranca

Verificar si existe:

```text
apps/segmentation-saliva/segmentacion_core/membranas_500_125
```

Ese modelo no se versiona ni se descarga automaticamente.

### El overlay no aparece

Verificar:

- existe `ResultadoSegmentacion`;
- el resultado incluye `resultado_normalizado`;
- `resultado_normalizado.objects` contiene objetos con `geometry.type="polygon"`;
- cada geometria tiene al menos tres puntos validos.

## Detener servicios

En cada terminal donde haya un servidor activo:

```text
Ctrl+C
```

Servicios habituales:

- Django `runserver`;
- FastAPI `uvicorn`;
- Vite `npm run dev`.

## Validaciones recomendadas

Backend:

```powershell
& "C:\Users\israe\miniconda3\envs\sicam\python.exe" manage.py check
& "C:\Users\israe\miniconda3\envs\sicam\python.exe" manage.py makemigrations --check
& "C:\Users\israe\miniconda3\envs\sicam\python.exe" -m pytest
& "C:\Users\israe\miniconda3\envs\sicam\python.exe" manage.py test
```

Frontend, solo si se modifica:

```powershell
npm run build
```

## Notas de seguridad

- No usar datos clinicos reales para demos.
- No commitear `.env`.
- No commitear `db.sqlite3`.
- No commitear `media/`.
- No commitear modelos, pesos ni `membranas_500_125`.
- No modificar `cellpose/` sin autorizacion explicita.
