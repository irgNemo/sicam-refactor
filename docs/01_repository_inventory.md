# 01 - SICAM Repository Inventory

## Scope

This inventory was created from the three code packages received for SICAM:

```text
micronucleos-web.zip
segmentacion_sangre.zip
Segmentacion_web.zip
```

The codebase is currently organized as three independent projects rather than one fully integrated monorepo.

## Top-Level Projects

```text
sicam_code/
├── micronucleos-web/
│   ├── Backend/              # Django + DRF backend
│   └── Frontend/             # Vue 3 + Vite frontend
├── Segmentacion_web/         # FastAPI microservice for saliva segmentation
└── segmentacion_sangre/      # FastAPI microservice for blood segmentation
```

## Project 1: micronucleos-web

### Purpose

Main SICAM web application.

### Observed Structure

```text
micronucleos-web/
├── Backend/
│   ├── api/
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── views.py
│   │   └── migrations/
│   ├── config/
│   │   ├── settings.py
│   │   ├── urls.py
│   │   ├── asgi.py
│   │   └── wsgi.py
│   ├── manage.py
│   └── db.sqlite3
└── Frontend/
    ├── src/
    │   ├── App.vue
    │   ├── main.js
    │   ├── components/
    │   │   ├── MainContent.vue
    │   │   ├── SideBar.vue
    │   │   └── TopBar.vue
    │   └── views/
    │       └── RegistroView.vue
    ├── package.json
    └── vite.config.js
```

### Backend Technology

- Django
- Django REST Framework
- django-cors-headers
- PostgreSQL configured in `settings.py`
- Local `db.sqlite3` file also present

### Frontend Technology

- Vue 3
- Vite
- Axios

### Current Integration Status

The frontend calls the Django backend directly using hardcoded URLs:

```text
http://127.0.0.1:8000
```

Observed modules:

- Patient registration
- Case registration
- Image upload
- Case search
- Basic segmentation view shell
- Placeholder modules for analysis and characterization

## Project 2: Segmentacion_web

### Purpose

FastAPI microservice for saliva image segmentation.

### Observed Structure

```text
Segmentacion_web/
├── app/
│   ├── main.py
│   ├── routers/
│   │   └── segmentacion.py
│   ├── services/
│   │   └── segmentador.py
│   └── utils/
│       └── poligonos.py
└── segmentacion_core/
    ├── seg_membranas.py
    ├── seg_nucleos.py
    ├── seg_micronucleos.py
    ├── membranas_500_125
    ├── cellpose/
    └── model/
```

### Technology

- FastAPI
- OpenCV
- NumPy
- Cellpose bundled under `segmentacion_core/cellpose`
- Custom trained Cellpose model: `membranas_500_125`

### Endpoint

```http
POST /segmentar
```

### Output Contract

```json
{
  "objetos": [
    {
      "id": 1,
      "tipo": "membrana",
      "puntos": [[10, 20], [11, 21]]
    }
  ]
}
```

## Project 3: segmentacion_sangre

### Purpose

FastAPI microservice for blood image segmentation and micronucleus detection.

### Observed Structure

```text
segmentacion_sangre/
├── main.py
├── requirements.txt
├── app/
│   ├── routers/
│   │   └── segmentacion.py
│   ├── services/
│   │   └── segmentador.py
│   └── utils/
│       └── poligonos.py
└── segmentacion_core/
    ├── sicam_master.py
    └── cellpose/
```

### Technology

- FastAPI
- OpenCV
- NumPy
- scikit-image
- scikit-learn DBSCAN
- Cellpose bundled under `segmentacion_core/cellpose`

### Endpoint

```http
POST /api/v1/segmentar
```

### Output Contract

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

## Initial Architectural Observation

The project is best understood as an early-stage distributed system composed of:

```text
Vue Frontend
    ↓
Django REST Backend
    ↓
FastAPI saliva microservice
FastAPI blood microservice
```

However, the current Django backend does not yet expose a clear orchestration layer that calls both segmentation microservices, stores their outputs, and feeds the frontend editor/reporting modules.

## Recommended Monorepo Shape

For refactor work, use this target structure as a reference:

```text
sicam/
├── apps/
│   ├── backend/
│   ├── frontend/
│   └── services/
│       ├── segmentation_saliva/
│       └── segmentation_blood/
├── packages/
│   └── sicam_segmentation_common/
├── docs/
├── docker-compose.yml
├── .env.example
└── README.md
```
