# Sprint 18M-B — Validación controlada de 19 revisiones

Fecha local: 2026-10-18 (America/Mexico_City). Los timestamps de ejecución
registrados abajo están en UTC y corresponden al 19 de octubre UTC.
HEAD: `534f4a55f46a1782836a0757b8a82debc6e6b683`, rama `master`.

## Decisión vigente del investigador

La actualización explícita de 18M-B sustituye el conjunto inicial de 18 revisiones:
autoriza **19**, incluida sample 41 / revisión 4. La revisión visual humana
completada es una declaración del investigador, no una inferencia del agente.

Para sample 41, el investigador confirma que no modificó manualmente objetos
durante la revisión reciente y acepta el contenido actual del borrador 4.
La diferencia histórica del MN respecto de la base manual ya estaba en VALIDADA 3;
no fue introducida por 18L. Antes de validar se comprobó por igualdad profunda
que N y MN de revisión 4 eran idénticos a los de revisión 3. No se restauró ni
modificó geometría o provenance. Revisión 4 ahora es VALIDADA y efectiva;
revisión 3 permanece íntegra en historial.

## Precheck

Git inicialmente sólo mostraba el documento esperado, sin seguimiento:
`docs/69_sprint_18l_alt_membrane_segmentation.md`. No se modificó ese documento:
conserva la auditoría y las recomendaciones anteriores a esta nueva decisión.

Django check: PASS. Migraciones api 0001–0009 aplicadas, sin pendientes.
SQLite integrity_check: ok; foreign_key_check sin infracciones.

Las 19 parejas se comprobaron contra la BD: pertenencia correcta, único borrador
activo, última revisión, contrato y resumen válidos, M>0 y N/MN presentes.
N/MN coinciden con las bases manuales para 42–61; para 41, la referencia autorizada
es VALIDADA 3. Los conteos de membranas coinciden con la auditoría 18M-A.
Antes de validar se guardaron hashes canónicos del snapshot completo y de las
listas ordenadas M/N/MN: JSON con claves ordenadas, separadores compactos,
UTF-8 y SHA-256.

## Respaldo nuevo verificado

Directorio: `/tmp/sicam18mb_backup_20261019T023549Z/`.

Contiene:

- `database/db.sqlite3`
- `media/`
- `manifest.txt`
- `hashes.txt`
- `RECOVERY.md`

BD real: `apps/web/Backend/db.sqlite3`.
MEDIA_ROOT: `apps/web/Backend/media`.
La BD se copió bajo bloqueo exclusivo SQLite, en modo journal distinto de WAL.
Se comprobaron hashes idénticos original/copia, legibilidad, integrity_check y
foreign_key_check. Media: 88 archivos, con paths, tamaños, mtimes y hashes iguales
al respaldo. No se reutilizó un backup anterior.

SHA-256 BD previa y backup:
`a6102fc96fce7c77af8e20d8a1979e193438b3f737e1309ed3525e9bea3127d7`.

El plan de recuperación requiere detener escritores antes de restaurar y
comprobar hashes e integridad. No se restauró el lote exitoso.

## Mecanismo y ejecución

Se invocó en proceso el endpoint real
`RevisionSegmentacionViewSet.validar` mediante DRF APIRequestFactory,
con POST y `expected_updated_at` de cada snapshot previo. No se asignó
`estado=VALIDADA` directamente por ORM ni se evitó la lógica del endpoint.

Las 19 llamadas fueron secuenciales, en el orden de la actualización autorizada,
dentro de una transacción global. Se tomó el bloqueo de dominio antes de
recomprobar el estado de toda la BD contra el respaldo; cada endpoint ejecutó
sus validaciones, guardas de concurrencia y timestamps normales. Después de cada
HTTP 200 se verificó snapshot, hashes, estado, validado_en y resolución effective,
antes de avanzar. Sólo se confirmó la transacción tras verificar todas las filas.

Una primera comprobación auxiliar detectó diferencias de representación de fechas
entre el lector SQLite del backup y Django (strings frente a date/datetime).
Se detuvo antes de cualquier llamada de validación; la transacción se revirtió y
el hash de BD siguió idéntico al respaldo. Se corrigió únicamente el script
temporal para usar la misma conversión de tipos en ambos lectores. No hubo
cambio de código productivo ni repetición de una validación exitosa.

## Resultados

Todas las filas siguientes pasaron de BORRADOR a VALIDADA, sin borrador activo
remanente para ese resultado. Effective apunta a la revisión indicada.
M/N/MN = membranas/núcleos/micronúcleos; contenido antes/después idéntico.

| Sample | Resultado | Revisión | M/N/MN | validado_en (UTC) |
| --- | --- | --- | --- | --- |
| 41 | 5 | 4 | 5/5/1 | 2026-10-19T02:36:25.653923+00:00 |
| 42 | 6 | 5 | 4/3/1 | 2026-10-19T02:36:25.668448+00:00 |
| 43 | 7 | 6 | 4/5/1 | 2026-10-19T02:36:25.691767+00:00 |
| 44 | 8 | 7 | 2/5/1 | 2026-10-19T02:36:25.705248+00:00 |
| 45 | 9 | 8 | 4/4/1 | 2026-10-19T02:36:25.717362+00:00 |
| 46 | 10 | 9 | 13/16/1 | 2026-10-19T02:36:25.759224+00:00 |
| 47 | 11 | 14 | 2/5/1 | 2026-10-19T02:36:25.800940+00:00 |
| 48 | 12 | 15 | 1/11/1 | 2026-10-19T02:36:25.836682+00:00 |
| 49 | 13 | 10 | 2/1/1 | 2026-10-19T02:36:25.851255+00:00 |
| 50 | 14 | 16 | 9/8/2 | 2026-10-19T02:36:25.863191+00:00 |
| 51 | 15 | 13 | 7/8/3 | 2026-10-19T02:36:25.893727+00:00 |
| 52 | 16 | 17 | 1/2/4 | 2026-10-19T02:36:25.905037+00:00 |
| 53 | 17 | 18 | 6/6/1 | 2026-10-19T02:36:25.918564+00:00 |
| 54 | 18 | 11 | 1/1/3 | 2026-10-19T02:36:25.930781+00:00 |
| 55 | 19 | 19 | 9/10/1 | 2026-10-19T02:36:25.957059+00:00 |
| 57 | 21 | 12 | 1/1/2 | 2026-10-19T02:36:25.968955+00:00 |
| 59 | 23 | 22 | 3/2/1 | 2026-10-19T02:36:25.977056+00:00 |
| 60 | 24 | 23 | 3/1/1 | 2026-10-19T02:36:25.985456+00:00 |
| 61 | 25 | 24 | 1/1/3 | 2026-10-19T02:36:25.993037+00:00 |

Para 42–61 incluidas, effective pasó de MANUAL a VALIDADA.
Para 41 pasó de VALIDADA 3 a VALIDADA 4.
Sample 51 conservó la revisión 13; no se creó otra revisión.

## Invariantes comprobados

- Igualdad profunda de cada snapshot completo y hashes M/N/MN antes/después.
- IDs, geometrías, provenance, source, raw_id, metadata y orden intactos.
- Sólo cambiaron `estado`, `validado_en` y `actualizado_en` de las 19 revisiones.
  El endpoint recalculó resumen, pero su valor permaneció igual.
- Comparación completa de filas de todas las tablas contra el backup:
  ninguna otra fila cambió. Esto incluye bases, revisión 3, revisiones excluidas,
  SegmentationExecution, historial y datos ajenos al lote.
- Bases manuales intactas: MANUAL, estrategia NULL; no se copiaron objetos hacia ellas.
- Ninguna creación o eliminación de revisiones, muestras, pacientes o ejecuciones.
- Media intacta: mismos 88 archivos, tamaños, mtimes y hashes.

| Modelo | Antes | Después |
| --- | --- | --- |
| Paciente | 7 | 7 |
| Caso | 7 | 7 |
| AnalisisPred | 7 | 7 |
| MuestraSaliva | 63 | 63 |
| ResultadoSegmentacion | 27 | 27 |
| RevisionSegmentacion | 26 | 26 |
| ResultadoCaracterizacion | 3 | 3 |
| ImageJImportRecord | 23 | 23 |
| SegmentationExecution | 25 | 25 |

## Pendientes de anotación manual

| Sample | Revisión | Estado | M actual | Effective | Clasificación |
| --- | --- | --- | --- | --- | --- |
| 56 | 20 | BORRADOR | 0 | MANUAL | PENDING_MANUAL_MEMBRANE_ANNOTATION |
| 58 | 21 | BORRADOR | 0 | MANUAL | PENDING_MANUAL_MEMBRANE_ANNOTATION |
| 62 | 25 | BORRADOR | 0 | MANUAL | PENDING_MANUAL_MEMBRANE_ANNOTATION |
| 63 | 26 | BORRADOR | 0 | MANUAL | PENDING_MANUAL_MEMBRANE_ANNOTATION |

Se conservaron intactas para etiquetado/corrección manual posterior.
**M=0 no se acepta todavía como estado científico final** en esas cuatro muestras.
No se reejecutó segmentación, agregaron membranas ni borraron borradores.

## Characterization y exclusiones

**19 CHARACTERIZATION_READY**: 41–55, 57, 59, 60 y 61, cada una por su revisión
recién VALIDADA y efectiva. Es readiness técnica, no una evaluación científica
automatizada ni autorización para caracterizar.

**4 PENDING_MANUAL_MEMBRANE_ANNOTATION**, no listas: 56, 58, 62 y 63.

No se ejecutó Characterization, ALT, CURRENT ni BLOOD.
Characterization permanece diferida y necesita una decisión posterior.
`CURRENT_REAL_ACCEPTANCE = DEFERRED`.
`PAIR_008 = PENDING_MANUAL_TOPOLOGY_REVIEW`; no se tocó.

## Verificación final y artefactos

SQLite integrity_check: ok. foreign_key_check: sin infracciones.
Django check final: PASS.
Tests backend: **250 passed, 2 skipped**, ejecutados antes de validar, con
`python -B -m pytest -q -p no:cacheprovider` en el entorno sicam.
Los tests reales de microservicios permanecieron omitidos. No hubo cambios de
código ni necesidad de pruebas frontend.

SHA-256 BD tras validación:
`80532487239d4d8acf3d83cce78d5c03657b0872d8c0c8b69f8bb4e7127472d0`.

Artefactos locales bajo `/tmp/sicam18mb/`:

- `prevalidation.json`, `checks.txt`, `backup_verification.json`
- `validation_results.csv`
- `invariants.json`: hashes por revisión y clase, conteos y comparación de tablas
- `integrity.json`
- `characterization_readiness.json`

Git final: únicamente docs/69 y este docs/70 sin seguimiento; sin cambios de código.
`git diff --check` y verificación de whitespace de documentos nuevos: PASS.
Sin staging, commit ni push.

SPRINT 18M-B = PASS

