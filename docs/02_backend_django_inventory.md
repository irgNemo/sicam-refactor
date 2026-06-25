# 02 - Django Backend Inventory

## Project

```text
micronucleos-web/Backend
```

## Frameworks and Libraries

- Django
- Django REST Framework
- django-cors-headers
- PostgreSQL configured in settings

## Django Apps

Only one project-specific app was detected:

```text
api
```

## Configuration Files

```text
Backend/config/settings.py
Backend/config/urls.py
Backend/config/asgi.py
Backend/config/wsgi.py
```

## Current Settings Observations

### Security-sensitive values hardcoded

`settings.py` contains:

- `SECRET_KEY` hardcoded
- `DEBUG = True`
- PostgreSQL credentials hardcoded
- `CORS_ALLOW_ALL_ORIGINS = True`
- `ALLOWED_HOSTS = []`

### Database configuration

Configured engine:

```python
'django.db.backends.postgresql'
```

Configured database:

```text
NAME: pruebas_web
USER: postgres
PASSWORD: 123456789
HOST: localhost
PORT: 5432
```

A local `db.sqlite3` file is also present, which suggests development inconsistency or previous use of SQLite.

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

Purpose: analysis workflow instance associated to patient and case.

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

Limitation: no JSON field for object polygons or raw segmentation result.

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

Potential issue: `MuestraSalivaSerializer` does not appear to include nested `resultados`; however, frontend code expects `muestra.resultados` in some summary calculations. That means the current frontend may not receive the data it expects unless the serializer has been changed elsewhere or the UI path is not fully functional.

## ViewSets

### PacienteViewSet

CRUD for patients.

Custom action:

```http
GET /api/pacientes/{id}/casos/
```

Returns all cases for a patient.

### CasoViewSet

CRUD for cases.

Custom action:

```http
GET /api/casos/{id}/analisis/
```

Returns all analyses for a case.

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

Potential issue: the implementation checks `nuevo_estado in [0, 1, 2]`; if frontend sends string values (`"1"`) this validation will fail.

### MuestraSalivaViewSet

CRUD for saliva samples.

Uses:

```text
MultiPartParser
FormParser
```

Purpose: image upload.

## API Router

```text
/api/pacientes/
/api/casos/
/api/analisis/
/api/muestras/
```

## Current Backend Gaps

The Django backend currently lacks:

- Authentication endpoints for doctors
- Role-based access control
- General `SampleImage` model for saliva and blood
- Endpoint to trigger segmentation
- HTTP client for FastAPI microservices
- Persistence of segmentation polygons
- Validation/revision status for segmentations
- Characterization model
- Report model and export endpoints
- Async job/task tracking
- Error handling strategy for external microservices
- Environment-based configuration

## Refactor Recommendation

Split the current `api` app into domain-focused apps:

```text
backend/
├── accounts/
├── patients/
├── cases/
├── samples/
├── segmentation/
├── characterization/
├── reports/
└── integrations/
    └── segmentation_clients/
```

Or, if keeping a single app initially, introduce internal modules:

```text
api/
├── models/
├── serializers/
├── views/
├── services/
├── selectors/
├── clients/
└── tests/
```
