# Sprint 18B — Estrategias de segmentación SALIVA en backend

## Alcance y baseline

Inicio en `/home/israel/repos/sicam-refactor`, rama `master`, working tree
limpio, HEAD `065c0733dad61926e0cf78738f1758fa26124199`:
`Add alternative saliva segmentation service`. Commits anteriores:
`7a3036f`, `93badea`, `f5df193`, `7618954`.

La selección múltiple se limita a **SALIVA**:

- `CURRENT_CUSTOM_V1`: servicio SALIVA histórico, modelo `membranas_500_125`.
- `ALT_CPSAM_MORPHOLOGICAL_V1`: servicio ALT de Sprint 18A, Cellpose 4.0.8/cpsam.

**BLOOD no tiene estrategias formalizadas en este sprint.** Su provenance
es deliberadamente `NULL`; no es un error ni se transforma en UNKNOWN,
DEFAULT o una identidad inventada. ALT nunca se ejecuta contra BLOOD.
No hay selector frontend, comparación de calidad, cambios científicos ni
modificaciones de los tres microservicios.

## Auditoría previa del flujo existente

Auditoría completada antes de implementar:

| Responsabilidad | Ubicación / comportamiento existente |
|---|---|
| Muestra SALIVA | `api/models.py::MuestraSaliva`; FK análisis e imagen |
| Muestra BLOOD | `api/models.py::MuestraSangre`; modelo y almacenamiento separados |
| Resultado | `ResultadoSegmentacion`; FK `muestra` o `muestra_sangre`, constraint de coherencia con `tipo_muestra` |
| Iniciar SALIVA | `api/views.py::MuestraSalivaViewSet.segmentar`; `/api/muestras/{id}/segmentar/` |
| Iniciar BLOOD | `MuestraSangreViewSet.segmentar`; `/api/muestras-sangre/{id}/segmentar/` |
| Lectura de imagen | `_read_muestra_image` |
| Elección de cliente | `api/services/segmentation/factory.py`; SALIVA y BLOOD separados por `SampleType` |
| Transporte | `base_client.py`; requests POST multipart `file`, errores controlados |
| Endpoint SALIVA | `saliva_client.py`; `POST /segmentar` |
| Endpoint BLOOD | `blood_client.py`; `POST /api/v1/segmentar` |
| Configuración | `config/settings.py::SEGMENTATION_SERVICES`; claves SALIVA y SANGRE |
| Normalización | `normalizers.py::normalize_segmentation_result`; IDs secuenciales únicos y `source.raw_id` |
| Persistencia | `views.py::_create_segmentation_result` |
| Respuesta inmediata | `_build_segmentation_response` |
| Historial | Acciones `resultados_segmentacion`, `ResultadoSegmentacionSerializer`; orden descendente fecha/ID |
| Revisiones | `RevisionSegmentacion`, `services/segmentation/revisions.py`, acciones crear/editar/validar |
| Efectivo | `effective.py::resolve_effective_segmentation`; última VALIDADA > AUTOMATICO; BORRADOR ignorado |
| Caracterización | `services/characterization/service.py`; consume efectivo; SALIVA 2.0, BLOOD counts-only 1.0 |
| Tests previos | `api/tests.py` y `api/services/segmentation/tests.py`; HTTP mockeado y dos integraciones omitidas |

Separación real de tipos: SALIVA usa `SampleType.SALIVA='SALIVA'`; BLOOD
usa `SampleType.BLOOD='SANGRE'`, con alias de entrada `BLOOD` en la factory.
El normalizador ya soporta raw IDs repetidos: no fue necesario modificarlo.
SALIVA devuelve errores del upstream sin crear resultados; BLOOD conserva
su comportamiento de persistir resultados ERROR. Esa diferencia se mantiene.

Flujo final:

```text
request SALIVA -> action/serializer -> estrategia validada (default CURRENT)
-> factory -> resolve_saliva_segmentation_service -> SalivaSegmentationClient
-> POST /segmentar -> normalizador existente -> ResultadoSegmentacion + strategy

request BLOOD -> action (rechaza campo segmentation_strategy si está presente)
-> factory BLOOD existente -> POST /api/v1/segmentar
-> normalizador/persistencia existentes -> ResultadoSegmentacion + NULL
```

## Campo y migración

`api/segmentation_strategies.py::SalivaSegmentationStrategy` centraliza sólo
los dos identificadores SALIVA como `TextChoices`.

`ResultadoSegmentacion.segmentation_strategy` es CharField(max_length=40),
con esas choices, `null=True`, `blank=True`, **sin default global**. La acción
SALIVA valida y asigna una estrategia antes de llamar al servicio y persistir.
El modelo sigue admitiendo NULL para BLOOD y para escrituras ORM fuera de
ese flujo; no se añade un default que contamine BLOOD.

Migración `0007_saliva_segmentation_strategy`:

1. Añade la columna nullable.
2. `RunPython` usa el modelo histórico y el alias real de la conexión.
3. Actualiza sólo filas con `muestra` presente, `muestra_sangre` ausente y
   estrategia NULL a `CURRENT_CUSTOM_V1`.
4. Deja resultados BLOOD en NULL. No inspecciona el JSON.

El `QuerySet.update` no altera `actualizado_en`. No se tocan respuesta,
normalización, revisiones, caracterizaciones, estados, errores ni fechas.
El reverse del backfill es noop: al revertir se elimina la columna nueva,
conservando todos los campos anteriores.

Validación local: backup SQLite en `/tmp/sicam18b-before-migration.sqlite3`,
seguido de `manage.py migrate`: OK. Había un resultado SALIVA y uno SANGRE;
quedaron respectivamente CURRENT y NULL. Fingerprints de todas las columnas
anteriores de las **10 tablas api**: idénticos antes/después. La prueba de
migración también cubre resultados ERROR, revisiones y caracterizaciones.

## Configuración y resolución

| Estrategia / tipo | Configuración | URL default | Timeout |
|---|---|---|---:|
| SALIVA CURRENT | `SALIVA_SEGMENTATION_SERVICE_URL`, `SALIVA_SERVICE_TIMEOUT` | `http://127.0.0.1:8001` | 30 s |
| SALIVA ALT | `SALIVA_ALT_SEGMENTATION_SERVICE_URL`, `SALIVA_ALT_SERVICE_TIMEOUT` | `http://127.0.0.1:8003` | 240 s |
| BLOOD | Configuración existente `BLOOD_*`, sin cambios | `http://localhost:8002` | 240 s |

CURRENT conserva sus variables y timeout. Su fallback local se expresa como
127.0.0.1 en lugar de localhost; los valores configurados previamente por
entorno siguen teniendo precedencia. No se modifica el `.env` local.

CURRENT continúa en `SEGMENTATION_SERVICES['SALIVA']`; ALT tiene un bloque
independiente `SALIVA_ALT_SEGMENTATION_SERVICE`. El resolver SALIVA devuelve
URL, timeout y estrategia efectiva. BLOOD no pasa por él. No hay URLs en
views ni clientes y no se duplicó el transporte HTTP. `.env.example`
documenta las nuevas variables.

## API y compatibilidad

La acción de segmentar admite JSON, multipart y form-urlencoded; la subida
normal de muestras conserva sus parsers existentes. No cambian las rutas.

```http
POST /api/muestras/{id}/segmentar/
Content-Type: application/json

{"segmentation_strategy":"ALT_CPSAM_MORPHOLOGICAL_V1"}
```

| Request | Resultado |
|---|---|
| SALIVA, campo omitido / request vacío | CURRENT; compatible con frontend actual |
| SALIVA, CURRENT explícito | CURRENT |
| SALIVA, ALT explícito | ALT |
| SALIVA, desconocido, vacío o null explícito | HTTP 400 antes de HTTP/persistencia |
| BLOOD, campo omitido | Flujo histórico, estrategia NULL |
| BLOOD, campo presente (incluido null) | HTTP 400: `segmentation_strategy is only supported for SALIVA samples` |

La respuesta de éxito agrega `segmentation_strategy` dentro de
`resultado_segmentacion`. Se conserva el raw `objetos` y
`resultado_normalizado` v1.1 sin introducir variantes CURRENT/ALT.
Dos núcleos con raw id=7 reciben dos IDs normalizados distintos, ambos
con `source.raw_id=7`.

Errores ALT mantienen el patrón SALIVA: timeout 504; conexión 503; HTTP
fallido, JSON inválido o contrato inválido 502; sin resultados exitosos falsos.
No se cambia el registro de ERROR de BLOOD ni su timeout.

## Lectura, efectivo, revisiones y caracterización

`ResultadoSegmentacionSerializer` expone la estrategia de sólo lectura en
historial; BLOOD emite null. No cambian filtros ni ordenamientos.

`/api/resultados-segmentacion/{id}/efectivo/` agrega la provenance del padre
tanto para AUTOMATICO como VALIDADA. El selector mantiene su comportamiento:
última VALIDADA > AUTOMATICO; un BORRADOR no es efectivo.

RevisionSegmentacion no tiene nuevo campo ni altera la estrategia del padre.
Characterization no cambia: no hay ramas por estrategia; SALIVA sigue en
algoritmo 2.0 y BLOOD en 1.0 counts-only. Las pruebas verifican resultados
científicos idénticos para ambas estrategias con la misma geometría/imagen,
y caracterización del efectivo VALIDADA para ambas.

## Pruebas y baseline

Nuevo `api/test_saliva_strategies.py`: 13 métodos, con subtests para CURRENT,
ALT, valores inválidos y BLOOD. Cubren todas las rutas de selección,
persistencia, serialización/historial, raw IDs repetidos, timeouts/conexión/
HTTP 500/JSON/contrato inválidos, efectivo, revisión validada, caracterización,
configuración independiente y migración con preservación de datos.
Los mocks de cuatro pruebas previas de factory SALIVA se reubicaron al
resolver que ahora lee settings; se mantienen sus expectativas.
No se requiere Cellpose ni microservicios para los tests Django.

Resultados con `sicam` (Python 3.10.20, Django 5.0.1):

| Validación | Resultado |
|---|---|
| `python manage.py migrate` | 0007 aplicada correctamente |
| `python manage.py check` | 0 issues |
| `python manage.py makemigrations --check` | No changes detected |
| `python -m pytest -q` | **185 passed, 2 skipped**, 3.65 s |
| `python manage.py test` | **160 tests, OK**, 2.48 s |
| Migración / preservación de datos | PASS en test y base local, incluidas revisiones/caracterizaciones |
| Compatibilidad CURRENT | Integración equivalente con transporte HTTP simulado: request omitido y CURRENT explícito → :8001/segmentar, timeout 30, resultado CURRENT persistido |
| Regresión BLOOD | Sin strategy → cliente BLOOD/NULL; ambas strategies rechazadas antes del transporte; historial/efectivo/counts-only PASS |

Las dos omisiones pytest son las integraciones reales preexistentes, no tests
nuevos omitidos. No se requiere cpsam en la suite normal. CURRENT se valida
por integración equivalente con HTTP simulado; **no se afirma un smoke nuevo
con su modelo real**. Esta modalidad está contemplada en el alcance de 18B.

## Smoke real Django → ALT, exclusivamente SALIVA

Se iniciaron temporalmente Django en `127.0.0.1:8000` y ALT en
`127.0.0.1:8003`. Django usó SQLite `/tmp/sicam18b-smoke.sqlite3` y
MEDIA_ROOT `/tmp/sicam18b-media`, con settings temporales fuera del repo.
La base habitual sólo recibió la migración/backfill autorizado; no recibió
los registros de este smoke.

Imagen: micrografía SALIVA de prueba autorizada en 18A, identificada como
`prueba_saliva.jpg.jpeg`, JPEG RGB 4928×4928. Se leyó de la copia fuente sin
modificarla. La copia para storage Django permanece en `/tmp`; no se versionan
imagen, respuesta ni información sensible.

```http
POST http://127.0.0.1:8000/api/muestras/1/segmentar/
Content-Type: application/json

{"segmentation_strategy":"ALT_CPSAM_MORPHOLOGICAL_V1"}
```

| Resultado | Evidencia |
|---|---|
| Startup/API | ALT OpenAPI y Django API HTTP 200 |
| Segmentación vía Django | **HTTP 200, 173.360001 s**, respuesta 8798 bytes |
| Objetos | **3 membranas, 3 núcleos, 1 micronúcleo** |
| Persistencia | Resultado 1, muestra SALIVA 1, COMPLETADO, FK sangre NULL, strategy ALT |
| Normalización | IDs únicos; `source.raw_id` coincide con cada ID de origen |
| JSON persistido | Respuesta raw y normalizada coinciden con la respuesta HTTP |
| Historial real HTTP | Strategy ALT |
| Efectivo real HTTP | AUTOMATICO, strategy ALT del padre |

IDs citados pertenecen exclusivamente a la SQLite temporal, no a datos de la
base habitual. La selección explícita llegó por el endpoint Django real,
no por una llamada directa al servicio. El timeout ALT de 240 s permitió la
inferencia. Se mantuvieron los avisos de runtime de Cellpose/Torch registrados
en 18A, sin alterar sus defaults ni parámetros.

Artefactos temporales: `/tmp/sicam18b-django-alt-result.json`,
`/tmp/sicam18b-django-alt-http.json`, `/tmp/sicam18b-smoke-verification.json`,
`/tmp/sicam18b-real-history.json`, `/tmp/sicam18b-real-effective.json` y logs
Django/ALT. Ambos servicios se apagaron al finalizar. **ALT nunca fue probado
con una imagen BLOOD**; las pruebas negativas BLOOD sólo verifican el rechazo
400 y ausencia de llamadas a microservicios.

## Archivos y cierre

Cambios funcionales exclusivamente en `apps/web/Backend`:

- `api/segmentation_strategies.py`: choices SALIVA.
- `api/models.py`, `api/migrations/0007_saliva_segmentation_strategy.py`: campo y backfill.
- `config/settings.py`, `.env.example`: URL/timeout ALT y fallback local CURRENT.
- `api/services/segmentation/strategies.py`, `factory.py`: resolución SALIVA.
- `api/views.py`, `api/serializers.py`: validación, persistencia, respuesta/historial.
- `api/services/segmentation/effective.py`: metadata aditiva del padre.
- `api/test_saliva_strategies.py`, `api/services/segmentation/tests.py`: pruebas y adaptación de mocks.

Documentación: este documento y una sección mínima de configuración Django
SALIVA en `docs/developer_environment_setup_wsl.md`.

No cambian `normalizers.py`, algoritmos de Characterization, código de
revisiones ni los microservicios. Los diffs de `apps/segmentation-saliva`,
`apps/segmentation-saliva-alt`, `apps/segmentation-blood` y
`apps/web/Frontend` están vacíos. No hay selector frontend ni estrategias BLOOD.
`git diff --check`: PASS; staging vacío. Cambios sin commit ni push.

```text
SPRINT 18B = PASS
```
