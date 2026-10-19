# Sprint 18N — Characterization 2.1 sobre revisiones ImageJ validadas

**SPRINT 18N-B = PASS WITH SCIENTIFIC REVIEW PENDING**

Fecha: 2026-10-19 (America/Mexico_City).
Rama: `master`.
HEAD: `c9281f46d1533c82fca31c214f9fc570643a517c`.

## Alcance y preflight 18N-A

18N-A comprobó 19 muestras con effective VALIDADA, M/N/MN positivos,
imágenes disponibles y contrato estructural válido. No había caracterizaciones
previas para esas 19. Los tres registros existentes pertenecían a samples 2 y 40.
Las asociaciones espaciales y métricas no se habían recalculado en el preflight.

18N-B ejecutó únicamente las 19 muestras del manifiesto aprobado.
Se conservaron sin Characterization las muestras 56/58/62/63 y sin cambios
las caracterizaciones históricas 1/2/3. No se ejecutó ALT, CURRENT ni BLOOD.
No se modificó código, fórmulas, thresholds, parámetros, normalización ni
asociaciones manualmente.

## Precondiciones y respaldo

Working tree inicialmente limpio. Django check PASS. Migraciones api 0001–0009
aplicadas y sin pendientes. SQLite integrity_check ok y foreign_key_check vacío.
Antes: 3 ResultadoCaracterizacion y 88 archivos de media.

Respaldo nuevo:
`/tmp/sicam18nb_backup_20261019T165046Z/`
(sufijo UTC; 10:50:46 local).

Contiene `database/db.sqlite3`, `media/`, `manifest.txt`, `hashes.txt`
y `RECOVERY.md`.
BD real: `apps/web/Backend/db.sqlite3`.
MEDIA_ROOT: `apps/web/Backend/media`.

La copia de BD se realizó bajo bloqueo exclusivo SQLite, sin WAL, verificando
SHA-256 idéntico, legibilidad e integridad de la copia. La copia de media
preserva los 88 archivos, rutas, tamaños, mtimes y hashes. Se verificó de nuevo
el respaldo antes de ejecutar.

SHA-256 BD previa/backup:
`80532487239d4d8acf3d83cce78d5c03657b0872d8c0c8b69f8bb4e7127472d0`.

El plan de recuperación exige detener escritores y verificar estado antes de
restaurar. No se restauró la ejecución exitosa.

## Ejecución por endpoint y concurrencia

Se invocó exclusivamente el endpoint existente
`POST /api/resultados-segmentacion/{result_id}/caracterizar/` a través de
`ResultadoSegmentacionViewSet.as_view({'post': 'caracterizar'})` y
DRF APIRequestFactory, en proceso y sobre la BD real. No se inició un servidor
HTTP ni se invocaron directamente funciones científicas para persistir; no se
insertaron ResultadoCaracterizacion manualmente por ORM.

El lote se ejecutó secuencialmente dentro de una transacción global, tomando
primero el bloqueo de dominio para impedir escrituras SQLite concurrentes.
Se comparó la BD completa contra el backup y se releyeron las 19 fuentes bajo
ese bloqueo. No hubo cambios de fuente ni registros ya existentes inesperados.
Después de cada llamada se verificaron HTTP, persistencia, versión, fuente,
FK, payload y hash de fuente antes de continuar.

Se mantuvo Characterization 2.1: geometría/centroide geométrico, eccentricity
mediante momentos raster, gray mean/std, GLCM 32 niveles, distancia 1,
ángulos 0/45/90/135°, symmetric y normalized. Se conservan las métricas de
textura y asociación MN–núcleo existentes. **Sin calibración física.**

## Resultados creados

Todas las filas: versión 2.1, source VALIDADA, FK a la revisión indicada,
HTTP inicial 201. La segunda ronda devolvió HTTP 200 y exactamente el mismo ID.
Los conteos asociados N/MN indican asociación a membrana; el caso particular
MN–núcleo de sample 59 se detalla más abajo. M/N/MN son conteos de entrada.

| Sample | Resultado | Revisión | Caracterización | M/N/MN | Células | N/MN asociados | No asociados | Ambiguos | Warnings | Duración inicial (s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 41 | 5 | 4 | 4 | 5/5/1 | 5 | 5/0 | 1 | 0 | 3 | 11.106 |
| 42 | 6 | 5 | 5 | 4/3/1 | 4 | 3/1 | 0 | 0 | 0 | 9.03 |
| 43 | 7 | 6 | 6 | 4/5/1 | 4 | 3/0 | 3 | 0 | 3 | 3.023 |
| 44 | 8 | 7 | 7 | 2/5/1 | 2 | 2/1 | 3 | 0 | 3 | 5.744 |
| 45 | 9 | 8 | 8 | 4/4/1 | 4 | 4/1 | 0 | 0 | 0 | 2.633 |
| 46 | 10 | 9 | 9 | 13/16/1 | 13 | 15/1 | 1 | 0 | 1 | 26.131 |
| 47 | 11 | 14 | 10 | 2/5/1 | 2 | 2/0 | 4 | 0 | 4 | 6.171 |
| 48 | 12 | 15 | 11 | 1/11/1 | 1 | 0/0 | 12 | 0 | 12 | 4.566 |
| 49 | 13 | 10 | 12 | 2/1/1 | 2 | 1/1 | 0 | 0 | 0 | 0.862 |
| 50 | 14 | 16 | 13 | 9/8/2 | 9 | 8/2 | 0 | 0 | 0 | 6.125 |
| 51 | 15 | 13 | 14 | 7/8/3 | 7 | 8/3 | 0 | 0 | 0 | 4.742 |
| 52 | 16 | 17 | 15 | 1/2/4 | 1 | 1/0 | 5 | 0 | 5 | 1.279 |
| 53 | 17 | 18 | 16 | 6/6/1 | 6 | 6/1 | 0 | 0 | 0 | 13.895 |
| 54 | 18 | 11 | 17 | 1/1/3 | 1 | 1/3 | 0 | 0 | 0 | 3.874 |
| 55 | 19 | 19 | 18 | 9/10/1 | 9 | 9/1 | 1 | 0 | 1 | 5.995 |
| 57 | 21 | 12 | 19 | 1/1/2 | 1 | 1/2 | 0 | 0 | 0 | 2.104 |
| 59 | 23 | 22 | 20 | 3/2/1 | 3 | 2/1 | 0 | 0 | 0 | 3.9 |
| 60 | 24 | 23 | 21 | 3/1/1 | 3 | 1/1 | 0 | 0 | 0 | 5.724 |
| 61 | 25 | 24 | 22 | 1/1/3 | 1 | 1/3 | 0 | 0 | 0 | 1.777 |


Se verificaron `summary`, `cells`, `unassociated`, `ambiguous`, `warnings`,
source y metodología persistidos en cada payload.
Los 19 resultados son vigentes según el resolver actual.

Totales del lote: 78 membranas/células, 95 núcleos y 30 MN de entrada.
73 núcleos asociados a membrana; 22 MN asociados a membrana, de los cuales
21 tienen núcleo asociado. Hay 30 objetos en unassociated (22 N y 8 MN),
0 ambiguos y 32 warnings emitidos. No se corrigió ningún objeto.

### Sample 41

La caracterización 4 usa resultado 5, **VALIDADA 4**, version 2.1.
No usa revisión 3. La revisión 3 permanece intacta como historial.
La fuente contiene el MN histórico id 6: el algoritmo emite
SELF_INTERSECTING_POLYGON, ECCENTRICITY_NOT_COMPUTABLE y
UNASSOCIATED_MICRONUCLEUS. Esto se registra para revisión científica;
no se restaura desde la base ni se modifica geometría/provenance.

## Warnings y asociaciones para revisión científica

`CHARACTERIZATION_SCIENTIFIC_REVIEW_REQUIRED`.

| Sample | Clasificación de warnings | Objetos/observaciones |
| --- | --- | --- |
| 41 | GEOMETRY_WARNING; UNASSOCIATED_OBJECTS | MN 6: autointersección, excentricidad no computable, no asociado |
| 43 | UNASSOCIATED_OBJECTS | N 3,4; MN 6 |
| 44 | UNASSOCIATED_OBJECTS | N 1,2,5 |
| 46 | UNASSOCIATED_OBJECTS | N 14 |
| 47 | UNASSOCIATED_OBJECTS | N 3,4,5; MN 6 |
| 48 | UNASSOCIATED_OBJECTS | N 1–11; MN 12 (todos los N/MN de esta muestra) |
| 52 | UNASSOCIATED_OBJECTS | N 2; MN 3,4,5,6 |
| 55 | UNASSOCIATED_OBJECTS | N 1 |
| 59 | NO_WARNINGS emitidos | MN 3 asociado a membrana 5, sin núcleo en esa célula |


Excepto MN 6 de sample 41 (geometría inválida para asociación), los objetos
listados en unassociated tienen el mensaje persistido «El objeto no pertenece
a ninguna membrana». Son resultados del mecanismo actual, no reasignaciones
realizadas durante la auditoría.

**Sample 59:** la caracterización 20 contiene MN 3 en membrana 5, que no tiene
núcleos asociados. `nucleus_id`, `distance_to_nucleus_px`,
`area_fraction_to_nucleus` e `intensity_fraction_to_nucleus` son NULL.
El algoritmo admite ese estado y no emite warning específico; no se inventó
un warning en su payload. Se marca para revisión en los artefactos de auditoría.
Ausencia de warnings no garantiza todas las métricas MN–núcleo disponibles.

No hubo AMBIGUOUS_ASSOCIATION, TEXTURE_WARNING ni OTHER_WARNING.
Sin warnings emitidos: 42, 45, 49, 50, 51, 53, 54, 57, 59, 60 y 61.
La revisión científica recomendada incluye 41, 43, 44, 46, 47, 48, 52, 55 y 59.
Los warnings no se interpretan automáticamente como fallos funcionales.
No se detectó un bug funcional que requiriera modificar la implementación.

## Idempotencia y duplicados

Después de completar las 19 primeras ejecuciones, se repitió secuencialmente
el mismo endpoint para las 19 muestras. Todas devolvieron HTTP 200 con los mismos
IDs 4–22, sin cambios en ninguna fila respecto del final de la primera ronda.
El servicio reutiliza el snapshot por resultado/revisión/source/version;
los tests existentes verifican además que esa rama no recalcula.

Conteos ResultadoCaracterizacion: **3 -> 22 -> 22**.
Auditoría de combinación resultado/revisión/source/version: **0 duplicados
lógicos**. No se borró ni fusionó ningún registro.

## Invariantes y registros históricos

Los hashes canónicos SHA-256 de los 19 snapshots efectivos antes/después son
idénticos. Se incluyen IDs, geometrías, source, provenance, metadata y orden.
Se compararon todas las filas de todas las tablas con el respaldo: sólo se
añadieron las 19 caracterizaciones y avanzó su secuencia SQLite.

ResultadoSegmentacion, RevisionSegmentacion y SegmentationExecution permanecen
íntegros; no hay nuevas revisiones, validaciones ni cambios de effective.
MEDIA_ROOT conserva sus 88 archivos con idénticos hashes/tamaños/mtimes.

| Modelo | Antes | Después |
| --- | --- | --- |
| Paciente | 7 | 7 |
| Caso | 7 | 7 |
| AnalisisPred | 7 | 7 |
| MuestraSaliva | 63 | 63 |
| ResultadoSegmentacion | 27 | 27 |
| RevisionSegmentacion | 26 | 26 |
| ResultadoCaracterizacion | 3 | 22 |
| ImageJImportRecord | 23 | 23 |
| SegmentationExecution | 25 | 25 |


Caracterizaciones 1/2/3 comparadas por todos sus valores persistidos: intactas.

- ID 1: sample 2, versión 2.0, KEEP_AS_HISTORICAL.
- ID 2: sample 40, versión 2.0, KEEP_AS_HISTORICAL.
- ID 3: sample 40, versión 2.1, KEEP_AS_CURRENT.

## Exclusiones conservadas

56/revisión 20, 58/revisión 21, 62/revisión 25 y 63/revisión 26:
BORRADOR, effective MANUAL, M=0, sin ResultadoCaracterizacion.
`PENDING_MANUAL_MEMBRANE_ANNOTATION`, `CHARACTERIZATION_READY=NO`.
No se validaron, segmentaron ni añadieron membranas.

`CURRENT_REAL_ACCEPTANCE = DEFERRED`.
`PAIR_008 = PENDING_MANUAL_TOPOLOGY_REVIEW`.

## Verificación final y evidencias

SQLite integrity_check: ok. foreign_key_check: vacío. Django check final: PASS.
Migraciones api 0001–0009 aplicadas; no se aplicaron migraciones.
Regresión backend completa antes de ejecutar: **250 passed, 2 skipped**
(7.30 segundos); incluye Characterization, effective e idempotencia.
Comando: `python -B -m pytest -q -p no:cacheprovider`, entorno sicam.
No se repitió frontend ni se cambió código.

SHA-256 BD final:
`823e185769154137cd342826745c2a5a98e733e457e5b904ed7303c85aac1dd8`.

Artefactos en `/tmp/sicam18nb/`:

- `characterization_results.csv`: entrada, salida, HTTP e idempotencia por muestra.
- `characterization_payload_summary.json`: source, summary, metodología y hashes.
- `associations.json`: IDs/tipos, contexto de no asociados y MN sin núcleo.
- `warnings.json`: warnings originales completos por muestra, sin alterarlos.
- `idempotency.json`: IDs de ambas rondas.
- `integrity.json`: comparación de tablas, conteos, hashes de fuentes e integridad.
- `prestate.json`, `backup_verification.json`, `checks_pre.txt`,
  `committed_results.json` (committed se refiere a persistencia de BD, no Git).

Único archivo nuevo del repositorio: este documento.
`git diff --check` y revisión de whitespace del documento: PASS.
Sin staging, commit ni push.

Siguiente paso recomendado: revisión científica humana de las nueve muestras
señaladas, especialmente sample 41 por geometría histórica, sample 48 por ausencia
total de asociación N/MN y sample 59 por MN sin núcleo. Cualquier corrección debe
seguir el flujo editorial y una autorización posterior; no se ejecutó en 18N-B.

SPRINT 18N-B = PASS WITH SCIENTIFIC REVIEW PENDING

