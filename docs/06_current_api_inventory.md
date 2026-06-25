# 06 - Current API Inventory

## Django Backend API

Base URL currently used by frontend:

```text
http://127.0.0.1:8000
```

API prefix:

```text
/api/
```

## Resource: Pacientes

### List patients

```http
GET /api/pacientes/
```

### Create patient

```http
POST /api/pacientes/
```

Example payload:

```json
{
  "nombre": "Juan",
  "apellido": "Pérez",
  "fecha_nacimiento": "1980-01-01",
  "identificacion": "ABC123",
  "email": "juan@example.com",
  "telefono": "3330000000"
}
```

### Retrieve patient

```http
GET /api/pacientes/{id}/
```

### Update patient

```http
PUT /api/pacientes/{id}/
PATCH /api/pacientes/{id}/
```

### Delete patient

```http
DELETE /api/pacientes/{id}/
```

### Patient cases

```http
GET /api/pacientes/{id}/casos/
```

## Resource: Casos

### List cases

```http
GET /api/casos/
```

### Create case

```http
POST /api/casos/
```

Example payload:

```json
{
  "paciente": 1,
  "titulo": "Análisis de rutina",
  "descripcion": "Notas del caso"
}
```

### Retrieve case

```http
GET /api/casos/{id}/
```

### Update case

```http
PUT /api/casos/{id}/
PATCH /api/casos/{id}/
```

### Delete case

```http
DELETE /api/casos/{id}/
```

### Case analyses

```http
GET /api/casos/{id}/analisis/
```

## Resource: Analisis

### List analyses

```http
GET /api/analisis/
```

### Create analysis

```http
POST /api/analisis/
```

Example payload:

```json
{
  "id_paciente_fk": 1,
  "id_caso_fk": 1,
  "estado": 0,
  "observaciones": "Opcional"
}
```

### Retrieve analysis

```http
GET /api/analisis/{id}/
```

### Update analysis

```http
PUT /api/analisis/{id}/
PATCH /api/analisis/{id}/
```

### Delete analysis

```http
DELETE /api/analisis/{id}/
```

### Change status

```http
POST /api/analisis/{id}/cambiar_estado/
```

Payload:

```json
{
  "estado": 1
}
```

Allowed values:

```text
0 = Abierto
1 = En Proceso
2 = Cerrado
```

## Resource: Muestras

### List samples

```http
GET /api/muestras/
```

### Upload saliva sample

```http
POST /api/muestras/
Content-Type: multipart/form-data
```

Fields:

```text
imagen: file
analisis: analysis ID
```

### Retrieve sample

```http
GET /api/muestras/{id}/
```

### Delete sample

```http
DELETE /api/muestras/{id}/
```

## Saliva Segmentation Microservice API

Base URL not yet integrated in Django.

### Segment saliva image

```http
POST /segmentar
Content-Type: multipart/form-data
```

Field:

```text
file: image file
```

Response:

```json
{
  "objetos": [
    {
      "id": 1,
      "tipo": "membrana",
      "puntos": [[10, 20], [11, 21]]
    },
    {
      "id": 1,
      "tipo": "nucleo",
      "puntos": [[15, 25], [16, 26]]
    },
    {
      "id": 1,
      "tipo": "micronucleo",
      "puntos": [[30, 40], [31, 41]]
    }
  ]
}
```

## Blood Segmentation Microservice API

Base URL not yet integrated in Django.

### Segment blood image

```http
POST /api/v1/segmentar
Content-Type: multipart/form-data
```

Field:

```text
file: image file
```

Response:

```json
{
  "objetos": [
    {
      "id": 1,
      "tipo": "membrana",
      "puntos": [[10, 20], [11, 21]]
    },
    {
      "id": 1,
      "tipo": "micronucleo",
      "puntos": [[30, 40], [31, 41]]
    }
  ]
}
```

## API Gaps to Add

### Backend orchestration endpoints

```http
POST /api/samples/{id}/segment/
GET  /api/samples/{id}/segmentation/
PATCH /api/segmentations/{id}/
POST /api/segmentations/{id}/validate/
POST /api/segmentations/{id}/characterize/
GET  /api/characterizations/{id}/
POST /api/cases/{id}/reports/
GET  /api/reports/{id}/download/
```

### Health endpoints

```http
GET /api/health/
GET /api/v1/health         # saliva microservice
GET /api/v1/health         # blood microservice
```

### Authentication endpoints

```http
POST /api/auth/login/
POST /api/auth/logout/
GET  /api/auth/me/
```
