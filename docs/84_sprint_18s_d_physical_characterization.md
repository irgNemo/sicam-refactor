# Sprint 18S-D — Characterization 2.2 con unidades físicas

## Baseline y alcance

Verificación en WSL el 2026-10-21. Rama `master`, HEAD inicial
`fde13690405ada3affc55075f50c800d87e4f79f` (`Add acquisition and calibration workflow`).
18S-C commiteado; working tree inicialmente limpio. `manage.py check` sin
problemas y migraciones `api/0001–0010` aplicadas.

Las nuevas caracterizaciones SALIVA persistidas usan versión **2.2**. Se añade
una representación física a la salida pixelaria de 2.1, sin cambiar su cálculo.
BLOOD conserva counts-only 1.0. No se ejecutaron segmentadores, importaciones,
recalibraciones ni caracterizaciones sobre muestras de trabajo.

No cambian modelos, constraints, endpoints, requisitos, motores de calibración,
segmentación ni archivos científicos de 2.1 (`saliva.py`, `geometry.py`,
`intensity.py`, `raster.py`, `raster_metrics.py`). No hay migración ni backfill;
no se necesitó backup para cambios de esquema. Se verificó por hashes la
inmutabilidad de la BD y el storage reales.

## Auditoría del contrato existente

| Responsabilidad | Ruta relativa a `apps/web/Backend` |
| --- | --- |
| Persistencia | `api/models.py::ResultadoCaracterizacion`, JSON `resultado_json` |
| Fuente | FK `resultado_segmentacion`, FK opcional `revision_segmentacion`, `source_type` |
| Versionado | `algorithm_version`, `created_at`, `services/characterization/types.py` |
| Orquestación/idempotencia/vigencia | `api/services/characterization/service.py` |
| Algoritmo pixelario 2.1 | `api/services/characterization/saliva.py` y helpers geométricos/raster |
| Resolver efectivo | `api/services/segmentation/effective.py` |
| API | `api/views.py::ResultadoSegmentacionViewSet`, `api/serializers.py::ResultadoCaracterizacionSerializer` |
| Autoridad física | `api/services/acquisition/compatibility.py::physical_compatibility` |
| Nueva capa 2.2 | `api/services/characterization/physical.py` |

La API conserva `POST /api/resultados-segmentacion/{id}/caracterizar/` (201 nuevo,
200 idempotente) y `GET /api/resultados-segmentacion/{id}/caracterizaciones/`.
El serializer conserva `resultado_json`, fuente, versión y `vigente`. No existe
selector público de versión; el POST ahora persiste SALIVA 2.2. La función pura
`characterize_effective_segmentation` permanece como entrada pixelaria reproducible
2.1; la orquestación añade 2.2 después de invocarla.

La idempotencia anterior usaba padre + revisión + fuente + versión. 2.2 añade el
fingerprint del contenido efectivo y contexto físico dentro del JSON existente.
No se necesitan columnas adicionales.

### Effective y guard manual

Se conserva el resolver: última VALIDADA por número de revisión, o base
MANUAL/AUTOMATIC si no hay VALIDADA. BORRADOR nunca se usa como entrada.

**Se conserva también el guard de 18H:** una base MANUAL sin revisión VALIDADA
no se caracteriza; se pide revisar y validar antes. El modelo de caracterización
sólo permite fuentes AUTOMATICO sin revisión o VALIDADA con revisión. Este sprint
no elimina ese guard ni convierte una base manual en automática. La expresión
“sin serie sigue caracterizando en píxeles” se aplica a entradas ya admitidas por
el flujo vigente. Las nuevas pruebas cubren esta restricción explícitamente.

## Flujo 2.2 y reproducibilidad

1. Transacción y bloqueo del resultado padre, como antes.
2. Resolver effective y aplicar el guard manual existente.
3. Obtener compatibilidad del servicio de adquisición. Durante persistencia se
   bloquean perfil, calibración y serie en el orden de padres usado por adquisición;
   el estado de calibración no puede cambiar a mitad del cálculo mediante esos saves.
4. Construir snapshot/fingerprint y buscar un resultado existente equivalente.
5. Si no existe, ejecutar exactamente el algoritmo pixelario 2.1 sobre la imagen
   original, sin resize; extender una copia de su salida con datos físicos.
6. Validar y guardar un nuevo `ResultadoCaracterizacion`. No actualizar anteriores.

`select_for_update` tiene semántica efectiva en motores que lo soportan. En SQLite
se conserva la transacción/snapshot de lectura y su mecanismo de bloqueo; una
contención puede fallar con database-locked y requerir reintento. No se añade una
política de retries o índice nuevo en este sprint.

Los hashes usan SHA-256 de JSON UTF-8, `sort_keys=True`, separadores `(',', ':')`,
`ensure_ascii=False`, `allow_nan=False`. Se conserva el orden de listas.

```text
effective_segmentation_hash = SHA256(canonical(effective.resultado))
fingerprint = SHA256(canonical({
  characterization_version,
  effective_segmentation_hash,
  physical_context
}))
```

El contexto incluye disponibilidad, status/reason, serie, dimensiones de imagen,
estado de las medidas y snapshot completo de calibración cuando es compatible.
La búsqueda sigue incluyendo padre, revisión, fuente y versión: un mismo contenido
en dos revisiones no se confunde. Cambios en geometría/IDs/provenance/orden de la
base también invalidan el fingerprint. `vigente` compara contra datos frescos,
sin confiar en relaciones ORM cacheadas.

Misma entrada/contexto devuelve el mismo recurso. Un nuevo ID de calibración,
escalas, status o metadata del snapshot produce un nuevo resultado; no modifica el
anterior. Los snapshots son históricos aunque la calibración cambie de etiqueta o
estado. 2.0/2.1 se siguen leyendo sin modificar su JSON, aunque dejan de estar
vigentes respecto de la versión actual.

**Límite de adquisición conservado:** una serie ya calibrada no admite cambiar su
FK, y una muestra ya asociada no admite cambiar de serie. La sensibilidad del
fingerprint a CAL-001 → CAL-002 se prueba con fixtures de BD de tests; no se abre
un flujo de reasignación ni se altera esta restricción de 18S-B. Las nuevas muestras
pueden pertenecer a nuevas series/calibraciones. Una serie sin calibración sí puede
recibirla posteriormente, y se prueba ese flujo normal de forma persistida.

## Snapshot y estructura JSON

Se conservan `cells`, `summary`, `unassociated`, `ambiguous`, `warnings`, `source`
y `methodology` con todos los valores pixelarios originales. Se añaden:

- `version`, `schema_version`, `characterization_version`: `2.2`.
- `physical_units_available`, `physical_status`, `physical_unavailable_reason`.
- `physical_measurements_status`: `PROVISIONAL_CALIBRATION`,
  `VALIDATED_CALIBRATION` o null.
- `acquisition_series_id`, `image_dimensions_px: {width, height}` cuando legibles.
- `calibration`: null si no utilizable; si utilizable incluye `calibration_id`,
  `label`, `status`, `acquisition_profile_id`, `acquisition_series_id`,
  `scale_x_um_per_px`, `scale_y_um_per_px`, `source_width_px`, `source_height_px`,
  `compatibility_status`, `method`, `algorithm_version`, `provenance` copiada.
- `provenance`: hash efectivo, fingerprint, `pixel_algorithm_version=2.1`,
  `IMPORTANT_PENDING_18S_A2=true` y pendiente de normalización física GLCM.

Las escalas se guardan como cadenas decimales de Calibration sin perder precisión.
Los cálculos derivados usan float de Python, como la geometría existente, sin
redondeo de presentación antes de persistir. La equivalencia física de un valor
pixelario null es null; sin compatibilidad **no se añaden campos físicos** a métricas.
Un null no se interpreta como cero.

## Clasificación dimensional y fórmulas

`FEATURE_DIMENSIONS` y `PHYSICAL_FIELDS`, en `physical.py`, son el registro central
que se prueba contra los nombres reales de las métricas. Counts/clases/estados son
metadatos y no reciben conversión. No existen diámetros adicionales en 2.1.

| Clase | Campos reales | Conversión |
| --- | --- | --- |
| AREA | `metrics.area_px2`, `summary.mean_nucleus_area_px2` | `area_um2`, `mean_nucleus_area_um2`: valor × sx × sy |
| LENGTH | `perimeter_px` | `perimeter_um`: perímetro del mismo polígono transformado X×sx, Y×sy |
| LENGTH | `distance_to_nucleus_px` | `distance_to_nucleus_um`: distancia de los mismos centroides y misma asociación |
| COORDINATE | `centroid_px=[x,y]` | `centroid_um=[x×sx,y×sy]` |
| DIMENSIONLESS | circularidad, excentricidad, ratios MN/núcleo, circularidad media, índices, tasas de asociación | Sin conversión ni redefinición |
| INTENSITY | `mean_gray_intensity`, `std_gray_intensity` | Sin conversión, intensidades normalizadas 0–1 como 2.1 |
| TEXTURE_PIXEL_DOMAIN | contrast, homogeneity, energy, correlation, entropy, valid_angles, valid_pairs | Sin modificación |

Para una distancia: `sqrt((dx*sx)^2 + (dy*sy)^2)`.
Para un perímetro: sumar esa expresión sobre cada segmento, incluido último→primero,
del mismo contorno que 2.1; no se sustituye por perímetro_px × escala media.

Se cubren membranas (regiones celulares, no espesor de borde), núcleos y MN,
además de objetos huérfanos/ambiguos y área nuclear promedio. La distancia MN
conserva **nucleus_id seleccionado por 2.1 en píxeles**: no se elige otro núcleo si
cambia el más cercano en coordenadas físicas. Huérfanos/ambiguos sin núcleo siguen
con distancia null. Autointersecciones/degeneraciones conservan las decisiones de
computabilidad y advertencias de 2.1.

Centroides físicos: posición respecto al origen de la imagen, no coordenadas
absolutas del portaobjetos. Excentricidad (momentos raster) y circularidad siguen en
espacio pixelario; con anisotropía no equivalen necesariamente a recalcular esas
formas en espacio físico. No se introduce silenciosamente una nueva definición.

GLCM permanece 32 niveles, distancia 1 px, ángulos 0°/45°/90°/135°, simétrica,
normalizada y agregada como 2.1. Ni intensidad ni textura reciben unidades µm.
Un paso de 1 px no garantiza la misma distancia física entre calibraciones/ejes.

Para la calibración OPTIKA actual se usan, vía la relación real de cada muestra:
`sx=0.055233934048`, `sy=0.055010060892`. No se usa el valor isotrópico auxiliar
`0.0551219974698993` ni se fija OPTIKA como fallback para muestras sin relación.

## Compatibilidad

La única autoridad es `physical_compatibility`; no se duplican sus decisiones.
`can_use_physical_units` es el wrapper booleano de ese mismo servicio, por lo que
no hace falta volver a ejecutarlo y abrir la imagen dos veces para obtener el booleano.

| Estado | Resultado nuevo |
| --- | --- |
| COMPATIBLE_PROVISIONAL | Píxeles + físico, snapshot PROVISIONAL y aviso visible |
| COMPATIBLE | Píxeles + físico, snapshot VALIDATED |
| NO_ACQUISITION_SERIES / NO_CALIBRATION | Píxeles y explicación, sin valores físicos |
| RESOLUTION_MISMATCH / IMAGE_MODE_MISMATCH | Píxeles; no resize ni escalas aproximadas |
| CALIBRATION_RETIRED | Sin nuevos físicos; snapshots anteriores intactos |
| PROFILE_MISMATCH / PATIENT_MISMATCH / INVALID_CALIBRATION | Píxeles y motivo del servicio |
| INVALID_IMAGE | Sin físicos; permanece la política 2.1: geometría disponible y advertencias de imagen/intensidad no disponible |

## Frontend

`characterizationPresentation.js` reconoce schema 2.2 sin cambiar el fallback de
SALIVA v1/v2.0/v2.1 ni BLOOD v1. `metricPresentation` sólo formatea valores persistidos.
`SalivaObjectMetrics` muestra µm/µm² primero y px/px² debajo, conservando los nulls.
Se incluyen el centroide, la distancia MN–núcleo y el área nuclear promedio.

`SalivaMorphometricResult` añade contexto compacto: etiqueta de calibración,
Provisional/Validada, aviso provisional y detalle desplegable con sx/sy (6 decimales),
resolución y significado del origen de coordenadas. Las métricas físicas se muestran
con 3 decimales; no se cambia el dato guardado. Sin físicos, sólo aparecen píxeles y
un motivo humano. No aparecen campos µm vacíos o falsos ceros. El detalle GLCM indica
que no está normalizada en espacio físico.

Se mantiene el botón existente Generar/Recalcular. Ninguna carga de página recalcula
registros históricos. No se añadieron exportaciones, bulk recalculation ni cambios
a selección/overlay/editor, Registro o adquisición.

## Auditoría read-only de BD de trabajo

Se usó ORM y conexión SQLite `PRAGMA query_only=ON`. Sin nombres de pacientes,
contenido clínico ni imágenes en este documento. Artefactos locales en
`/tmp/sicam18sd/`: `audit.py`, `pre.json`, `post.json`, logs de validación.

| Observación actual | Cantidad |
| --- | ---: |
| Muestras totales | 69 |
| Con AcquisitionSeries | 4 |
| Sin AcquisitionSeries / NO_ACQUISITION_SERIES | 65 |
| COMPATIBLE | 0 |
| COMPATIBLE_PROVISIONAL | 2 |
| IMAGE_MODE_MISMATCH | 2 |
| Otros motivos incompatibles | 0 |
| Caracterizaciones 2.0 | 2 |
| Caracterizaciones 2.1 | 21 |
| Caracterizaciones 2.2 reales | 0 |
| Total caracterizaciones históricas | 23 |
| Archivos de media | 95 |

Los totales difieren del contexto histórico de 18S-C (22 caracterizaciones y 65
muestras); son el estado **ya existente al iniciar** este sprint, no una modificación
introducida aquí. No se infieren nuevas asociaciones por resolución.

Se comparan SHA-256 del archivo de BD, hashes canónicos de las 26 tablas completas,
hash por cada caracterización y SHA-256 de cada archivo de media antes/después.
BD inicial: `c50400eee7a0fc8aa1127b74511a27d4ac13bed363d7386f7ee2b83073711941`.
El resultado de la comparación final se registra en el cierre de este documento.

## Validación automática

Todos los fixtures con escritura usan BD de tests y media temporal. No hay pruebas
reales automáticas sobre pacientes de trabajo.

- Backend completo: **345 tests PASS**, incluidos 22 nuevos de 2.2, 29 de motor de
  calibración, adquisición 18S-B/C, Registro, ImageJ, normalización, revisiones,
  effective, Characterization 2.1 y BLOOD.
- Nuevos casos: áreas anisotrópicas, perímetro oblicuo contra fórmula independiente,
  vector MN diagonal, asociación invariante aun si anisotropía cambia el más cercano,
  centroides, cobertura del registro de features, equivalencia profunda de todos los
  campos anteriores, intensidad/std/excentricidad/GLCM idénticas, nulls/degenerados/
  ambiguos, canonicalización/fingerprint/orden.
- Persistencia/API: fixture RGB 4928×4928 + PROVISIONAL con sx≠sy reales del contrato;
  segunda llamada 200/mismo ID; VALIDATED; retiro conserva snapshot; sin serie;
  serie sin calibración y asignación posterior; cambio de calibración con fixture
  aislado; mismatch exacto perfil 4928×4928/imagen 2464×2464 sin resize; imagen
  ilegible; modos incompatibles; denegaciones del servicio; 2.1 histórico inmutable;
  VALIDADA sobre BORRADOR; guard MANUAL; cambio de base invalida vigencia.
- Frontend Characterization: **22 regresiones + 15 nuevas PASS** (render SSR real,
  helper de presentación, doble representación, provisional/validada, nueve razones,
  ausencia de cálculo Vue, preservación de adimensionales/intensidad/GLCM e históricos).
- Frontend Segmentación/editor: **59 PASS**; Registro: **40 PASS**;
  adquisición: **18 PASS**.
- `npm run build`: **PASS**, Node 24.17.0, 113 módulos.
- Django `check`: **PASS**; `makemigrations --check --dry-run`: **No changes detected**.
- Los tests antiguos de API se ajustan únicamente en sus expectativas de nueva versión
  2.2. Las pruebas numéricas originales `test_characterization_2_1.py` no se modifican.

Comandos reproducibles, desde cada carpeta correspondiente:

```bash
# apps/web/Backend, entorno sicam
python manage.py test --noinput
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py showmigrations api

# apps/web/Frontend, Node 24.17.0
node tests/characterization21.test.mjs
node tests/characterization22.test.mjs
node tests/segmentationStrategies.test.mjs
node tests/registration.test.mjs
node tests/acquisition.test.mjs
npm run build
```

No se usa `node --test` como resumen de estas suites Vite: la ejecución directa
permite conservar el reporte completo de subtests del runner existente.

## Pendientes y revisión manual

- `IMPORTANT_PENDING_18S_A2`: calibración operativa **PROVISIONAL**, pendientes
  repetibilidad, rotación 0°/90°, especificación/tolerancia del patrón, anisotropía,
  incertidumbre metrológica y criterios científicos finales.
- `HISTORICAL_ACQUISITION_ASSOCIATION = PENDING_MANUAL_CONFIRMATION`.
- `RETIRED_RECALCULATION_POLICY = PENDING_DECISION`: no nuevos físicos con RETIRED;
  snapshots históricos preservados. No se decide política científica adicional.
- `DURABLE_UPLOAD_IDEMPOTENCY`: pendiente heredado de adquisición; no se resuelve aquí.
- `GLCM_PHYSICAL_DISTANCE_NORMALIZATION = PENDING_SCIENTIFIC_DECISION`.

Revisión visual recomendada, separada de esta ejecución y con datos sintéticos o
una futura autorización explícita para escribir: comprobar medidas físicas como
principal, px secundarios, aviso provisional, detalle sx/sy, centroides relativos,
razones de indisponibilidad y mantenimiento de resultados históricos. No se ha
realizado aceptación manual en navegador ni caracterización real nueva.

No staging, commit ni push.

## Cierre verificado

- Comparación `pre.json == post.json`: **PASS**, incluido SHA-256 byte-exacto de BD,
  hashes de las 26 tablas, de las 23 caracterizaciones y de los 95 archivos de media.
- `PRAGMA integrity_check`: `ok`; `PRAGMA foreign_key_check`: sin infracciones.
- HEAD sigue `fde13690405ada3affc55075f50c800d87e4f79f`; staging vacío.
- `git diff --check`: **PASS**. Diff tracked: 7 archivos, 130 inserciones,
  26 eliminaciones. Además hay 4 archivos nuevos sin seguimiento: capa física,
  tests backend 2.2, tests frontend 2.2 y este documento. Ningún otro cambio.
- No se aplicaron migraciones ni se realizaron escrituras en la BD/media de trabajo.

SPRINT 18S-D = READY_FOR_PHYSICAL_CHARACTERIZATION_REVIEW
