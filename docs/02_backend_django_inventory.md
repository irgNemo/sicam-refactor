# 02 - Django Backend Inventory

## Project

```text
apps/web/Backend
```

This backend comes from the previous `micronucleos-web/Backend` project.

## Frameworks and Libraries

- Django
- Django REST Framework
- django-cors-headers
- django-environ
- Pillow
- requests

## Django Apps

Only one project-specific app is currently present:

```text
api
```

## Configuration Files

```text
apps/web/Backend/config/settings.py
apps/web/Backend/config/urls.py
apps/web/Backend/config/asgi.py
apps/web/Backend/config/wsgi.py
apps/web/Backend/.env.example
```

## Current Settings Status

Configuration has been externalized with `django-environ`.

Current configurable values include:

- `SECRET_KEY`
- `DEBUG`
- `ALLOWED_HOSTS`
- database settings
- `CORS_ALLOWED_ORIGINS`
- `LANGUAGE_CODE`
- `TIME_ZONE`
- `SEGMENTATION_SERVICES`

The local default database is SQLite:

```text
apps/web/Backend/db.sqlite3
```

That SQLite file is local/generated and should not be committed.

PostgreSQL can be configured through environment variables, but it is not the hardcoded default in the current settings.

## Technical Validation Status

The current inventory is based on source inspection. A minimal runtime validation pass is still pending.

Recommended validation:

```bash
cd apps/web/Backend
python manage.py check
python manage.py migrate --check
pytest api/services/segmentation/tests.py
```

The exact commands may need adjustment after dependencies and the local Python environment are installed.

## URL Configuration

Root routes:

```text
/admin/
/api/
/media/ when DEBUG=True
```

API routes are delegated to:

```text
api.urls
```

Registered API routes:

```text
/api/pacientes/
/api/casos/
/api/analisis/
/api/muestras/
```

Custom actions:

```http
GET  /api/pacientes/{id}/casos/
GET  /api/casos/{id}/analisis/
POST /api/analisis/{id}/cambiar_estado/
```

Important current absence:

```http
POST /api/muestras/{id}/segmentar/
```

`api.views.saludo` exists, but no health route is currently registered in `api/urls.py`.

## Models

### Paciente

```text
id_paciente: AutoField primary key
nombre: CharField(100)
apellido: CharField(100)
fecha_nacimiento: DateField
identificacion: CharField(50, unique=True)
email: EmailField nullable/blank
telefono: CharField(20) nullable/blank
fecha_registro: DateTime auto_now_add
```

Purpose: stores patient identity/contact information.

### Caso

```text
id_caso: AutoField primary key
paciente: ForeignKey(Paciente, related_name='casos')
titulo: CharField(200)
descripcion: TextField nullable/blank
fecha_creacion: DateTime auto_now_add
```

Purpose: groups clinical work for one patient.

### AnalisisPred

```text
id_analisis: AutoField primary key
id_paciente_fk: ForeignKey(Paciente, related_name='analisis')
id_caso_fk: ForeignKey(Caso, related_name='analisis')
fecha: DateField auto_now_add
estado: IntegerField choices
observaciones: TextField nullable/blank
```

Estado choices:

```text
0 = Abierto
1 = En Proceso
2 = Cerrado
```

Potential issue: `id_paciente_fk` duplicates the patient relation already implied through `id_caso_fk.paciente`. This may create integrity drift if both point to different patients.

### MuestraSaliva

```text
id_muestra: AutoField primary key
analisis: ForeignKey(AnalisisPred, related_name='muestras_saliva')
imagen: ImageField(upload_to='muestras/saliva/%Y/%m/')
fecha_subida: DateTime auto_now_add
```

Purpose: stores uploaded saliva sample images.

Limitation: blood sample images are not represented by the current backend model.

### ResultadoAnalisis

```text
id_resultado: AutoField primary key
muestra: ForeignKey(MuestraSaliva, related_name='resultados')
nucleos: IntegerField
micronucleos: IntegerField
membranas: IntegerField
fecha_analisis: DateTime auto_now_add
```

Purpose: stores aggregate segmentation counts.

Limitation: no JSON field currently stores object polygons or raw segmentation results.

### AnalisisMascara

```text
id_mascara_analisis: AutoField primary key
resultado: ForeignKey(ResultadoAnalisis, related_name='mascaras')
tipo_mascara: CharField(50)
imagen: ImageField(upload_to='mascaras/saliva/%Y/%m/')
algoritmo: CharField(100)
fecha_generacion: DateTime auto_now_add
```

Purpose: stores mask image files associated with a result.

Limitation: does not model edited polygons, validation status, or object-level segmentation.

## Serializers

The API uses basic ModelSerializers:

```text
PacienteSerializer
CasoSerializer
MuestraSalivaSerializer
ResultadoAnalisisSerializer
AnalisisSerializer
```

`AnalisisSerializer` nests `muestras_saliva` read-only.

Potential issue: `MuestraSalivaSerializer` does not include nested `resultados`; however, frontend summary logic expects `muestra.resultados` in some paths. This should be aligned later.

## ViewSets

### PacienteViewSet

CRUD for patients.

Custom action:

```http
GET /api/pacientes/{id}/casos/
```

### CasoViewSet

CRUD for cases.

Custom action:

```http
GET /api/casos/{id}/analisis/
```

### AnalisisViewSet

CRUD for analyses.

Custom action:

```http
POST /api/analisis/{id}/cambiar_estado/
```

Payload:

```json
{
  "estado": 1
}
```

Allowed values: `0`, `1`, `2`.

Potential issue: the implementation checks `nuevo_estado in [0, 1, 2]`; if frontend sends string values such as `"1"`, validation will fail.

### MuestraSalivaViewSet

CRUD for saliva samples.

Uses:

```text
MultiPartParser
FormParser
```

Purpose: image upload.

Missing action:

```http
POST /api/muestras/{id}/segmentar/
```

## Segmentation Client Layer

Django now includes HTTP clients for the FastAPI segmentation services:

```text
apps/web/Backend/api/services/segmentation/
├── base_client.py
├── saliva_client.py
├── blood_client.py
├── exceptions.py
├── factory.py
├── tests.py
└── USAGE.md
```

Public helpers:

```python
get_segmentation_client(sample_type)
segment_image(sample_type, image_file, filename='image.jpg')
```

Supported factory keys:

```text
SALIVA
SANGRE
```

This layer is infrastructure only at the moment. Existing API endpoints do not call it yet.

## Current Backend Gaps

The Django backend still lacks:

- Minimal validated backend test/check results in this refactored workspace.
- `POST /api/muestras/{id}/segmentar/`.
- Persistence of raw segmentation JSON.
- General `ImagenMuestra` model for saliva and blood.
- Validation/revision status for segmentations.
- Characterization model and endpoints.
- Report model and export endpoints.
- Async job/task tracking.
- Authentication endpoints for doctors.
- Role-based access control.
- A routed health endpoint.
- Deployment/runbook documentation for backend runtime configuration.

Already addressed:

- Environment-based configuration.
- Frontend-facing API base URL externalization.
- Django clients for segmentation microservices.

## Refactor Guidance

Do not rename or replace models in the current sanitation step.

Next safe backend integration should be narrow:

1. Add an action for `POST /api/muestras/{id}/segmentar/`.
2. Use `api.services.segmentation.segment_image(...)`.
3. Persist the returned `objetos` JSON in a new migration-backed model.
4. Keep existing endpoints unchanged.

Larger restructuring into domain apps should wait until the endpoint and persistence path are validated.
