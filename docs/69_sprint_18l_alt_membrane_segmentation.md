# Sprint 18L — Segmentación ALT de membranas y auditoría post-revisión humana

Fecha de auditoría: 2026-10-16. Rama `master`.
HEAD: `534f4a55f46a1782836a0757b8a82debc6e6b683`.

## Cierre y límites

Se documenta el cierre de ejecución de 18L-A y 18L-B y la revisión visual humana
completada **según declaración explícita del investigador en la solicitud 18M-A**.
No se infiere revisión visual, autoría ni aprobación científica desde timestamps.
El cierre no equivale a validar revisiones: las decisiones de validación permanecen
pendientes. Las muestras 56, 58, 62 y 63 siguen sin membranas persistidas.

18L-A: muestras 46, 49, 54 y 57.
18L-B: muestras 47, 48, 50, 51, 52, 53, 55, 56, 58, 59, 60, 61, 62 y 63.
La muestra 51 se completó separadamente reutilizando su BORRADOR 13.
Las ejecuciones relacionadas usan `ALT_CPSAM_MORPHOLOGICAL_V1`, target
`MEMBRANES`; sus salidas se guardaron en borradores, preservando las bases ImageJ.
Las muestras 41–45 también se incluyen en esta auditoría del dataset completo;
42–45 corresponden al piloto 18J, no a ejecuciones nuevas de 18L.

Esta auditoría consultó Django ORM con SQLite en modo `mode=ro` y
`PRAGMA query_only=ON`. No ejecutó segmentación, Characterization, importación,
validación ni creación/edición de revisiones. La única escritura de repositorio
autorizada es este documento. No se hicieron staging, commit ni push.

## Precheck e integridad

- Working tree inicialmente limpio; HEAD registrado arriba.
- Últimos commits: `534f4a5`, `0b7bded`, `1a11f71`, `09c0085`, `05fb4df`.
- Django `check`: 0 incidencias.
- `showmigrations api`: 0001–0009 aplicadas, incluidas
  `0008_imagej_manual_import` y `0009_selective_saliva_segmentation`.
- Sin migraciones pendientes.
- SQLite `integrity_check = ok`; `foreign_key_check = []`.
- BD: `apps/web/Backend/db.sqlite3`, 4345856 bytes.
  SHA-256 antes/después:
  `a6102fc96fce7c77af8e20d8a1979e193438b3f737e1309ed3525e9bea3127d7`.
- MEDIA_ROOT: `apps/web/Backend/media`: 88 archivos,
  703174139 bytes.
  Mismos paths, tamaños, mtimes y SHA-256 antes/después.
- Se validó el contrato de los snapshots actuales y la coherencia de sus resúmenes,
  sin ejecutar cálculos de Characterization.

| Modelo | Filas |
| --- | --- |
| Paciente | 7 |
| Caso | 7 |
| AnalisisPred | 7 |
| MuestraSaliva | 63 |
| ResultadoSegmentacion | 27 |
| RevisionSegmentacion | 26 |
| ResultadoCaracterizacion | 3 |
| ImageJImportRecord | 23 |
| SegmentationExecution | 25 |


## Inventario actual

M/N/MN = membranas/núcleos/micronúcleos, contados desde objetos persistidos.
Todas las bases son SALIVA, origen `MANUAL`, estrategia `NULL`.
Todas las últimas revisiones son `BORRADOR` y existe exactamente un borrador
activo por muestra. Sólo 41 tiene también una revisión VALIDADA (id 3).

| Sample | patient_key técnico | Resultado | Base M/N/MN | Última revisión | Revisión M/N/MN | Effective | BORRADOR activo | Tiene VALIDADA |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 41 | ACL | 5 | 0/5/1 | 4 | 5/5/1 | VALIDADA | sí | sí |
| 42 | ACL | 6 | 0/3/1 | 5 | 4/3/1 | MANUAL | sí | no |
| 43 | AMBC | 7 | 0/5/1 | 6 | 4/5/1 | MANUAL | sí | no |
| 44 | ARR | 8 | 0/5/1 | 7 | 2/5/1 | MANUAL | sí | no |
| 45 | COA | 9 | 0/4/1 | 8 | 4/4/1 | MANUAL | sí | no |
| 46 | ACL | 10 | 0/16/1 | 9 | 13/16/1 | MANUAL | sí | no |
| 47 | ACL | 11 | 0/5/1 | 14 | 2/5/1 | MANUAL | sí | no |
| 48 | ACL | 12 | 0/11/1 | 15 | 1/11/1 | MANUAL | sí | no |
| 49 | AMBC | 13 | 0/1/1 | 10 | 2/1/1 | MANUAL | sí | no |
| 50 | AMBC | 14 | 0/8/2 | 16 | 9/8/2 | MANUAL | sí | no |
| 51 | AMBC | 15 | 0/8/3 | 13 | 7/8/3 | MANUAL | sí | no |
| 52 | AMBC | 16 | 0/2/4 | 17 | 1/2/4 | MANUAL | sí | no |
| 53 | ARR | 17 | 0/6/1 | 18 | 6/6/1 | MANUAL | sí | no |
| 54 | ARR | 18 | 0/1/3 | 11 | 1/1/3 | MANUAL | sí | no |
| 55 | COA | 19 | 0/10/1 | 19 | 9/10/1 | MANUAL | sí | no |
| 56 | COA | 20 | 0/6/1 | 20 | 0/6/1 | MANUAL | sí | no |
| 57 | ECM | 21 | 0/1/2 | 12 | 1/1/2 | MANUAL | sí | no |
| 58 | ECM | 22 | 0/10/1 | 21 | 0/10/1 | MANUAL | sí | no |
| 59 | ECM | 23 | 0/2/1 | 22 | 3/2/1 | MANUAL | sí | no |
| 60 | ECM | 24 | 0/1/1 | 23 | 3/1/1 | MANUAL | sí | no |
| 61 | ECM | 25 | 0/1/3 | 24 | 1/1/3 | MANUAL | sí | no |
| 62 | ECM | 26 | 0/1/1 | 25 | 0/1/1 | MANUAL | sí | no |
| 63 | EHC | 27 | 0/2/1 | 26 | 0/2/1 | MANUAL | sí | no |


### Timestamps persistidos de la última revisión

ISO-8601, zona America/Mexico_City (UTC−06:00). Estos timestamps no acreditan
por sí mismos revisión visual ni autoría. Ninguna de estas últimas revisiones
tiene `validado_en`.

| Sample | Revisión | created_at | updated_at |
| --- | --- | --- | --- |
| 41 | 4 | 2026-10-04T18:19:19.891165-06:00 | 2026-10-04T18:19:19.891184-06:00 |
| 42 | 5 | 2026-10-04T19:36:26.182401-06:00 | 2026-10-04T19:36:26.182421-06:00 |
| 43 | 6 | 2026-10-04T19:37:38.805256-06:00 | 2026-10-04T20:28:38.904255-06:00 |
| 44 | 7 | 2026-10-04T19:38:54.457222-06:00 | 2026-10-04T20:32:58.809348-06:00 |
| 45 | 8 | 2026-10-04T19:40:02.864120-06:00 | 2026-10-04T19:40:02.864139-06:00 |
| 46 | 9 | 2026-10-05T13:01:08.893006-06:00 | 2026-10-05T13:01:08.893043-06:00 |
| 47 | 14 | 2026-10-14T21:45:24.684133-06:00 | 2026-10-14T21:45:24.684168-06:00 |
| 48 | 15 | 2026-10-14T21:47:52.594267-06:00 | 2026-10-14T21:47:52.594444-06:00 |
| 49 | 10 | 2026-10-05T13:03:56.193884-06:00 | 2026-10-05T13:03:56.193913-06:00 |
| 50 | 16 | 2026-10-14T21:50:24.458442-06:00 | 2026-10-14T21:50:24.458497-06:00 |
| 51 | 13 | 2026-10-05T17:50:58.875191-06:00 | 2026-10-14T22:40:12.127063-06:00 |
| 52 | 17 | 2026-10-14T21:52:46.103778-06:00 | 2026-10-14T21:52:46.103808-06:00 |
| 53 | 18 | 2026-10-14T21:56:03.608849-06:00 | 2026-10-14T21:56:03.608882-06:00 |
| 54 | 11 | 2026-10-05T13:06:52.266237-06:00 | 2026-10-05T13:06:52.266272-06:00 |
| 55 | 19 | 2026-10-14T21:58:15.866889-06:00 | 2026-10-14T21:58:15.866920-06:00 |
| 56 | 20 | 2026-10-14T21:59:28.589448-06:00 | 2026-10-14T21:59:28.589463-06:00 |
| 57 | 12 | 2026-10-05T13:09:29.900724-06:00 | 2026-10-05T13:09:29.900752-06:00 |
| 58 | 21 | 2026-10-14T22:00:40.428629-06:00 | 2026-10-14T22:00:40.428652-06:00 |
| 59 | 22 | 2026-10-14T22:01:56.893556-06:00 | 2026-10-14T22:01:56.893588-06:00 |
| 60 | 23 | 2026-10-14T22:03:23.713621-06:00 | 2026-10-14T22:03:23.713640-06:00 |
| 61 | 24 | 2026-10-14T22:04:38.657039-06:00 | 2026-10-14T22:04:38.657056-06:00 |
| 62 | 25 | 2026-10-14T22:05:50.914351-06:00 | 2026-10-14T22:05:50.914369-06:00 |
| 63 | 26 | 2026-10-14T22:07:03.441537-06:00 | 2026-10-14T22:07:03.441555-06:00 |


## Preservación estructural y correcciones observadas

Se compararon las listas N/MN de **todas** las revisiones de las 23 muestras con
sus bases manuales mediante igualdad profunda, conservando orden. La comparación
incluye IDs, geometría, source (incluido raw_id), provenance, metadata y cualquier
otro campo del objeto; no sólo conteos.

- N: igualdad exacta en las 23 muestras, incluidas ambas revisiones de 41.
- MN: igualdad exacta en 22 muestras. Excepción: muestra 41, revisiones 3 y 4.
- Muestra 41: `HUMAN_OBJECT_CHANGE_DETECTED`. El único MN conserva ID, source y
  metadata; cambian geometría y provenance respecto de la base.
  Provenance persistida: `origin=manual`, `base_object_id=null`,
  `modified=true`. El MN de VALIDADA 3 es exactamente igual al de BORRADOR 4.
  Por tanto, el cambio ya existía en la validada anterior; no se atribuye a 18L
  ni a una persona concreta. No se clasifica automáticamente como corrupción.
- En las últimas revisiones, las membranas presentes conservan provenance
  automática ALT y coinciden geométricamente con los objetos de sus ejecuciones
  asociadas. No se observan membranas de origen manual, membranas automáticas
  faltantes ni cambios geométricos frente a esas ejecuciones.
- La ausencia de cambios persistidos no contradice la declaración de revisión
  visual: revisar no exige editar. No se presume guardado de ediciones que no
  aparecen en la BD.

### Muestra 41: VALIDADA y BORRADOR coexistentes

Resultado 5. VALIDADA 3, número 1, M/N/MN = 1/5/1.
Creada `2026-10-03T21:49:17.723047-06:00`,
actualizada `2026-10-03T21:54:43.788695-06:00`,
validada `2026-10-03T21:54:43.788561-06:00`.
BORRADOR 4, número 2, M/N/MN = 5/5/1.
La VALIDADA 3 sigue efectiva; el borrador no la sustituye.
Se recomienda revisar la diferencia del MN contra la base antes de validar
el borrador. Esta recomendación no invalida la revisión 3.

### Muestras con salida inicial M=0

| Sample | Revisión | M actual | Membranas manuales | Estado | Validada | Evidencia de guardado posterior a ejecución |
| --- | --- | --- | --- | --- | --- | --- |
| 56 | 20 | 0 | 0 | BORRADOR | no | no observada |
| 58 | 21 | 0 | 0 | BORRADOR | no | no observada |
| 62 | 25 | 0 | 0 | BORRADOR | no | no observada |
| 63 | 26 | 0 | 0 | BORRADOR | no | no observada |


Los borradores sí están persistidos, con N/MN intactos. No hay evidencia de
membranas añadidas ni de un guardado posterior a su ejecución automática.
Se mantienen como `DRAFT_WITH_ZERO_MEMBRANES`; recomendación `KEEP_DRAFT`.

### Muestra 51 y limitación del respaldo

Sample 51, resultado 15, revisión 13, número 1: M/N/MN = 7/8/3.
Existe una sola revisión para ese resultado: no se creó un borrador duplicado.
N/MN conservados exactamente. Effective = MANUAL, sin VALIDADA.
Ejecución persistida `e218fcb6-7235-4392-b3f3-337b1a502ac5`,
ALT + MEMBRANES, COMPLETED, destino revisión 13.
Creación del borrador: `2026-10-05T17:50:58.875191-06:00`;
actualización: `2026-10-14T22:40:12.127063-06:00`;
finalización de ejecución: `2026-10-14T22:40:12.128015-06:00`.

En la continuidad previa de 18L-B51 se informó de respaldo temporal verificado
antes de ejecutar, pero los artefactos originales bajo /tmp dejaron de estar
disponibles al retomar. No se puede aportar ahora un respaldo preejecución
recuperable ni reconstruir una comparación completa byte a byte de toda aquella
BD. La comprobación actual de provenance, ejecución, unicidad y preservación N/MN
no sustituye ese respaldo histórico. No se repitió la segmentación para recrear
evidencia. La integridad read-only de esta auditoría sí se comprueba con hashes
actuales antes/después.

## Clasificación y decisión de validación

`READY_TO_VALIDATE` es una recomendación técnica basada en el snapshot actual
y la declaración de revisión humana; no ejecuta validación ni certifica calidad
científica. La declaración de 18M-A cubre 18L; para 42–45, la aceptación humana
previa está documentada en [18J](67_sprint_18j_end_to_end_pilot.md).

| Sample | patient_key | Revisión | M/N/MN | N exacto | MN exacto | Estado | Clasificación | Recomendación |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 41 | ACL | 4 | 5/5/1 | sí | no | BORRADOR | DRAFT_REQUIRES_INVESTIGATOR_REVIEW | REQUIRES_REVIEW |
| 42 | ACL | 5 | 4/3/1 | sí | sí | BORRADOR | REVIEWED_DRAFT_READY_TO_VALIDATE | READY_TO_VALIDATE |
| 43 | AMBC | 6 | 4/5/1 | sí | sí | BORRADOR | REVIEWED_DRAFT_READY_TO_VALIDATE | READY_TO_VALIDATE |
| 44 | ARR | 7 | 2/5/1 | sí | sí | BORRADOR | REVIEWED_DRAFT_READY_TO_VALIDATE | READY_TO_VALIDATE |
| 45 | COA | 8 | 4/4/1 | sí | sí | BORRADOR | REVIEWED_DRAFT_READY_TO_VALIDATE | READY_TO_VALIDATE |
| 46 | ACL | 9 | 13/16/1 | sí | sí | BORRADOR | REVIEWED_DRAFT_READY_TO_VALIDATE | READY_TO_VALIDATE |
| 47 | ACL | 14 | 2/5/1 | sí | sí | BORRADOR | REVIEWED_DRAFT_READY_TO_VALIDATE | READY_TO_VALIDATE |
| 48 | ACL | 15 | 1/11/1 | sí | sí | BORRADOR | REVIEWED_DRAFT_READY_TO_VALIDATE | READY_TO_VALIDATE |
| 49 | AMBC | 10 | 2/1/1 | sí | sí | BORRADOR | REVIEWED_DRAFT_READY_TO_VALIDATE | READY_TO_VALIDATE |
| 50 | AMBC | 16 | 9/8/2 | sí | sí | BORRADOR | REVIEWED_DRAFT_READY_TO_VALIDATE | READY_TO_VALIDATE |
| 51 | AMBC | 13 | 7/8/3 | sí | sí | BORRADOR | REVIEWED_DRAFT_READY_TO_VALIDATE | READY_TO_VALIDATE |
| 52 | AMBC | 17 | 1/2/4 | sí | sí | BORRADOR | REVIEWED_DRAFT_READY_TO_VALIDATE | READY_TO_VALIDATE |
| 53 | ARR | 18 | 6/6/1 | sí | sí | BORRADOR | REVIEWED_DRAFT_READY_TO_VALIDATE | READY_TO_VALIDATE |
| 54 | ARR | 11 | 1/1/3 | sí | sí | BORRADOR | REVIEWED_DRAFT_READY_TO_VALIDATE | READY_TO_VALIDATE |
| 55 | COA | 19 | 9/10/1 | sí | sí | BORRADOR | REVIEWED_DRAFT_READY_TO_VALIDATE | READY_TO_VALIDATE |
| 56 | COA | 20 | 0/6/1 | sí | sí | BORRADOR | DRAFT_WITH_ZERO_MEMBRANES | KEEP_DRAFT |
| 57 | ECM | 12 | 1/1/2 | sí | sí | BORRADOR | REVIEWED_DRAFT_READY_TO_VALIDATE | READY_TO_VALIDATE |
| 58 | ECM | 21 | 0/10/1 | sí | sí | BORRADOR | DRAFT_WITH_ZERO_MEMBRANES | KEEP_DRAFT |
| 59 | ECM | 22 | 3/2/1 | sí | sí | BORRADOR | REVIEWED_DRAFT_READY_TO_VALIDATE | READY_TO_VALIDATE |
| 60 | ECM | 23 | 3/1/1 | sí | sí | BORRADOR | REVIEWED_DRAFT_READY_TO_VALIDATE | READY_TO_VALIDATE |
| 61 | ECM | 24 | 1/1/3 | sí | sí | BORRADOR | REVIEWED_DRAFT_READY_TO_VALIDATE | READY_TO_VALIDATE |
| 62 | ECM | 25 | 0/1/1 | sí | sí | BORRADOR | DRAFT_WITH_ZERO_MEMBRANES | KEEP_DRAFT |
| 63 | EHC | 26 | 0/2/1 | sí | sí | BORRADOR | DRAFT_WITH_ZERO_MEMBRANES | KEEP_DRAFT |


Candidatas `READY_TO_VALIDATE` (18): 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 57, 59, 60, 61.
`KEEP_DRAFT` (4): 56, 58, 62, 63.
`REQUIRES_REVIEW` (1): 41.
No se recomienda `ALREADY_VALIDATED` para la última revisión de ninguna muestra:
todas son borradores, aunque 41 tenga otra revisión ya validada.

## Characterization readiness

Criterio técnico: revisión VALIDADA efectiva con snapshot válido, membranas,
imagen disponible y sin inconsistencias detectadas. No implica ejecutar
Characterization ni aceptar científicamente el contenido.
El BORRADOR nunca se considera effective.

| Sample | Effective | Revisión VALIDADA efectiva | CHARACTERIZATION_READY |
| --- | --- | --- | --- |
| 41 | VALIDADA | 3 | YES |
| 42 | MANUAL | — | NO |
| 43 | MANUAL | — | NO |
| 44 | MANUAL | — | NO |
| 45 | MANUAL | — | NO |
| 46 | MANUAL | — | NO |
| 47 | MANUAL | — | NO |
| 48 | MANUAL | — | NO |
| 49 | MANUAL | — | NO |
| 50 | MANUAL | — | NO |
| 51 | MANUAL | — | NO |
| 52 | MANUAL | — | NO |
| 53 | MANUAL | — | NO |
| 54 | MANUAL | — | NO |
| 55 | MANUAL | — | NO |
| 56 | MANUAL | — | NO |
| 57 | MANUAL | — | NO |
| 58 | MANUAL | — | NO |
| 59 | MANUAL | — | NO |
| 60 | MANUAL | — | NO |
| 61 | MANUAL | — | NO |
| 62 | MANUAL | — | NO |
| 63 | MANUAL | — | NO |


Sólo 41 tiene readiness técnica, por su revisión 3 (1/5/1), no por su borrador 4
(5/5/1). Las otras 22 requieren una validación posterior apropiada; 56/58/62/63
además siguen sin membranas. No se creó ningún ResultadoCaracterizacion.

## Siguiente decisión y exclusiones

El investigador debe decidir sobre las 18 candidatas, revisar la diferencia MN
de 41 y resolver el estado sin membranas de 56/58/62/63. No se valida nada en 18M-A.
Antes de una futura validación hay que releer estado y timestamp; el endpoint
existente exige `expected_updated_at` para revisiones con ejecuciones completadas
y rechaza versiones obsoletas. Los timestamps de este documento no deben usarse
ciegamente si el usuario continúa editando.

- `CURRENT_REAL_ACCEPTANCE = DEFERRED`.
- `PAIR_008 = PENDING_MANUAL_TOPOLOGY_REVIEW`, exclusión previa por REAL_HOLE.
  No se importó ni corrigió en esta fase.
- Sin modificaciones de código, BD ni media; no se iniciaron microservicios.
- Único archivo nuevo previsto en Git: este documento.
- `git diff --check` y comprobación de whitespace del documento nuevo sin incidencias.

SPRINT 18M-A = READY_FOR_VALIDATION_DECISION

