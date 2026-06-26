# SICAM Refactor

Repositorio de saneamiento y refactorizacion de SICAM (Sistema de Captura y Analisis de Micronucleos).

Este workspace nuevo se construyo a partir de tres repositorios fuente previos:

- `micronucleos-web`: aplicacion web Django + Vue.
- `Segmentacion_web`: microservicio FastAPI para segmentacion de saliva.
- `segmentacion_sangre`: microservicio FastAPI para segmentacion de sangre.

## Estructura Actual

El workspace funciona como monorepo de refactorizacion. Las tres aplicaciones fuente se conservaron como aplicaciones separadas bajo `apps/`:

- `apps/web/`
- `apps/segmentation-saliva/`
- `apps/segmentation-blood/`

```text
sicam-refactor/
├── apps/
│   ├── web/                       # Aplicacion web integrada: Backend Django + Frontend Vue
│   ├── segmentation-saliva/       # Microservicio de segmentacion de muestras salivales
│   └── segmentation-blood/        # Microservicio de segmentacion de muestras de sangre
├── docs/                          # Inventarios, brechas, prioridades y contexto maestro
├── scripts/                       # Scripts de utilidad
├── docker/                        # Archivos Docker pendientes de consolidacion
├── .gitignore
├── PHASE_0_SUMMARY.md
├── PHASE_2_SUMMARY.md
└── README.md
```

## Estado Real Actual

El repositorio ya paso por una iteracion de saneamiento tecnico inicial:

- Se limpiaron archivos generados/locales como `__pycache__/`, `*.pyc`, `.pytest_cache/`, `db.sqlite3`, `debug.log` y temporales detectados.
- `.gitignore` fue ajustado para Python, Django, Node/Vite, entornos locales, logs, bases SQLite y artefactos temporales.
- El backend Django usa configuracion basada en variables de entorno mediante `django-environ`.
- Existe `apps/web/Backend/.env.example`.
- El frontend Vue ya centraliza Axios en `apps/web/Frontend/src/services/apiClient.js`.
- El frontend usa `import.meta.env.VITE_API_BASE_URL`.
- Existe `apps/web/Frontend/.env.example`.
- El backend ya tiene clientes HTTP para microservicios de segmentacion en `apps/web/Backend/api/services/segmentation/`.

## Validacion Tecnica Pendiente

Aunque el saneamiento documental y de configuracion ya esta aplicado, todavia falta una validacion tecnica minima del estado actual:

- instalar dependencias y ejecutar checks del backend Django;
- instalar dependencias y ejecutar build/checks del frontend Vue;
- validar que ambos microservicios FastAPI levantan y responden a sus endpoints de segmentacion;
- documentar comandos de ejecucion y despliegue para cada servicio;
- definir pruebas smoke para el flujo integrado cuando exista el endpoint Django de segmentacion.

Los endpoints existentes de Django se mantienen:

```text
/api/pacientes/
/api/casos/
/api/analisis/
/api/muestras/
/api/pacientes/{id}/casos/
/api/casos/{id}/analisis/
/api/analisis/{id}/cambiar_estado/
```

## Aplicaciones

### `apps/web/`

Aplicacion web principal:

- `Backend/`: API Django REST para pacientes, casos, analisis y muestras.
- `Frontend/`: interfaz Vue 3 + Vite.

El backend contiene una capa de clientes de segmentacion, pero todavia no expone un endpoint Django que ejecute la segmentacion de una muestra.

### `apps/segmentation-saliva/`

Microservicio FastAPI heredado de `Segmentacion_web`.

Endpoint principal esperado:

```http
POST /segmentar
```

### `apps/segmentation-blood/`

Microservicio FastAPI heredado de `segmentacion_sangre`.

Endpoint principal esperado:

```http
POST /api/v1/segmentar
```

## Pendientes Principales

Todavia falta integrar funcionalmente los tres sistemas:

- Completar validacion tecnica minima de backend, frontend y microservicios.
- Crear `POST /api/muestras/{id}/segmentar/` en Django.
- Persistir el JSON de segmentacion retornado por los microservicios.
- Generalizar `MuestraSaliva` hacia un modelo tipo `ImagenMuestra` que soporte saliva y sangre.
- Integrar el flujo completo frontend -> Django -> microservicio -> persistencia.
- Agregar validacion de segmentaciones por especialista.
- Implementar caracterizacion cuantitativa.
- Implementar reportes/exportacion.
- Documentar pruebas y despliegue.

## Documentacion

La carpeta `docs/` contiene el inventario y contexto vigente del refactor:

- `docs/02_backend_django_inventory.md`
- `docs/03_frontend_vue_inventory.md`
- `docs/08_integration_gaps.md`
- `docs/09_refactor_priorities.md`
- `docs/10_codex_master_context.md`

## Estado

Refactorizacion en progreso.

Ultima actualizacion documental: 2026-06-25.
