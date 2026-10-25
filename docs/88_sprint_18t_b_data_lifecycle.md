# Sprint 18T-B — Data lifecycle

Fecha local: 2026-10-23 (America/Mexico_City).
Estado: **READY_FOR_DATA_LIFECYCLE_REVIEW**. Implementación, regresiones, migración
e integridad verificadas; la revisión visual/operativa humana queda pendiente.

## Baseline y alcance

- Rama `master`; HEAD inicial `1efa877479bcfb324806fd90f14b12d6ab8a9bae`.
- Working tree limpio al reintentar. Cierre documental 18T-A.1 en `ef530d9` y
  corrección de auth en `1efa877`, separados de este sprint.
- Python del entorno `sicam`; Node 24.17.0. Migraciones API previas 0001–0011.
- No se ejecutan acciones lifecycle sobre datos científicos reales. Las acciones
  destructivas y las llamadas científicas simuladas se prueban en test DB/storage.
- No bulk delete, purga, event sourcing, dashboard de auditoría ni 18T-C.

## Principio y arquitectura

La FK de Django no define por sí sola la política de borrado. El servicio
`api/services/lifecycle.py` inspecciona el grafo real antes de mostrar opciones y
lo vuelve a consultar dentro de una transacción antes de ejecutar. No se llama al
borrado en cascada si existe una dependencia; las referencias PROTECT tampoco se
eliminan para forzar un borrado.

Se conservan los managers normales. Los servicios científicos internos siguen
leyendo históricos; el filtrado operacional se realiza en el límite de API y en
las elecciones de relaciones de serializers. Las consultas de datos archivados
son explícitas, de lectura y ADMIN/superuser, siempre con scope institucional.

### Estados y metadatos

`ArchivableModel` añade a Paciente, Caso, AnalisisPred, MuestraSaliva,
MuestraSangre, AcquisitionSeries y AcquisitionProfile:

- archived_at nullable;
- archived_by nullable, FK User SET_NULL;
- archive_reason (texto).

Los campos son read-only en los serializers ordinarios. ARCHIVE requiere motivo
no vacío (máximo 2000 caracteres) y actor autenticado. RESTORE también requiere
motivo y crea un evento: limpia archived_at y conserva los metadatos del último
archivo; todos los episodios anteriores permanecen en LifecycleEvent. No se
reescriben los autores de creación ni se inventa autoría para legacy NULL.

Calibration reutiliza status=RETIRED, con reason y actor en el evento. No hay
UNRETIRE ni promoción administrativa a VALIDATED. Su snapshot histórico y escalas
no se reescriben. El PATCH ordinario ya no permite cambios de status; una validación
científica necesita un proceso explícito futuro.

### LifecycleEvent

Campos: institution (PROTECT, nullable sólo para legacy de plataforma), actor
(SET_NULL), action, target_type, target_id textual, target_display, reason,
metadata JSON y created_at. No hay FK al target: HARD_DELETE no elimina el evento.
Acciones implementadas: ARCHIVE, RESTORE, HARD_DELETE, RETIRE.

Snapshot mínimo: tipo/ID técnico, institución, actor, motivo, counts de dependencias,
created_by_id original y, para Patient, identity_mode. No se copia `Paciente.__str__`,
nombre completo, email o teléfono al evento. Los archivos incluyen ruta relativa,
basename y SHA-256 cuando existen. El motivo es introducido por el usuario; la UI
no añade datos clínicos al texto.

## Matriz de política

| Recurso | Sin uso/dependencias | Con uso/dependencias | Restauración | Rol |
|---|---|---|---|---|
| Patient | HARD_DELETE o ARCHIVE | ARCHIVE | Sí | ADMIN / superuser |
| Case | HARD_DELETE o ARCHIVE | ARCHIVE | Parent activo | ADMIN / superuser |
| Analysis | HARD_DELETE o ARCHIVE | ARCHIVE, independiente de estado 0/1/2 | Parents activos | ADMIN / superuser |
| Sample SALIVA/SANGRE | HARD_DELETE; ADMIN también ARCHIVE | ARCHIVE, nunca hard delete | Parents activos | ADMIN; OPERATOR creador sólo hard delete seguro |
| AcquisitionSeries | HARD_DELETE; ADMIN también ARCHIVE | ARCHIVE | Patient activo, Profile disponible y coherencia; no Calibration RETIRED | ADMIN; OPERATOR creador sólo hard delete vacío |
| AcquisitionProfile | HARD_DELETE o ARCHIVE | ARCHIVE | Sí; no reactiva active=False | ADMIN / superuser |
| Calibration | HARD_DELETE sólo PROVISIONAL sin series, referencias ni snapshots; también RETIRE | RETIRE | No UNRETIRE | ADMIN / superuser |
| CalibrationReference | No delete individual | Evidencia preservada | No aplica | Inmutable desde lifecycle |
| ResultadoSegmentacion | No delete | Historial preservado | No aplica | Sin acción destructiva |
| Revision BORRADOR/VALIDADA | No delete general | Historial preservado | No aplica | Sin acción destructiva |
| Characterization | No delete ni archivo individual | Snapshot preservado | No aplica | Sin acción destructiva |
| User | is_active existente; nunca hard delete | Autoría preservada | Reactivación existente | ADMIN institucional / superuser |
| Institution | active existente; nunca hard delete | Relaciones preservadas | Activación existente | Sólo superuser |

Política conservadora para calibraciones: incluso una referencia sin uso operacional
se considera evidencia; no se borran sus TIFF ni filas para eliminar su Calibration.
El OPERATOR no puede borrar un recurso ajeno o legacy created_by=NULL. REVIEWER
mantiene su función de validación científica, sin acciones destructivas generales.

No se permite hard-delete de un objeto ya archivado: primero se restaura si el
contexto lo permite y luego se inspecciona otra vez. Repetir ARCHIVE/RESTORE/RETIRE
ya aplicado devuelve conflicto claro sin duplicar eventos. Repetir hard-delete
devuelve 404.

## Ancestros, selectores e históricos

- Patient archivado oculta Cases, Analyses, Samples, Series y resultados derivados.
- Case y Analysis archivados ocultan sus descendientes operacionales.
- No se propaga archived_at mediante updates masivos a descendientes.
- Restaurar el padre no restaura hijos archivados individualmente.
- Restaurar un hijo con parent archivado devuelve PARENT_ARCHIVED y referencia
  técnica al superior en warnings.
- Series/Profile archivados no pueden utilizarse en nuevas relaciones/uploads.
  El archivo de metadata de adquisición no borra ni oculta los snapshots existentes
  de muestras independientes; esos históricos conservan su contexto científico.
- Los selectores de subida excluyen series archivadas, perfiles no disponibles y
  series con calibraciones retiradas. El backend revalida aunque el selector esté
  obsoleto.
- Listados, detalles normales y acciones científicas respetan archivo de muestra y
  ancestros. Los endpoints anidados de casos/análisis y resumen de segmentación
  también filtran; no sólo el listado principal.
- `include_archived=true` habilita lectura histórica sólo para ADMIN/superuser.
  No habilita escrituras sobre recursos archivados ni acceso cross-tenant.
- Media histórica conserva autenticación y scope institucional. Nunca se abre
  `/media/` públicamente.
- ImageJ puede reconocer una importación previa de forma idempotente, pero no
  reutiliza Patient/Case/Analysis archivados para crear una pareja nueva.

## Inmutabilidad de adquisición

Los campos científicos de Profile se bloquean desde su primer uso por Calibration,
Series o referencia en un snapshot JSON de Characterization:

microscope_manufacturer, microscope_model, camera_manufacturer, camera_model,
adapter_model, objective_magnification, image_width_px, image_height_px,
image_mode, binning_x y binning_y.

name y notes siguen editables sin reescribir los valores científicos. La UI muestra
el bloqueo existente y ofrece archivar para crear una configuración corregida.
No se añadió Clone Profile; mejora futura `PROFILE_VERSIONING_ENHANCEMENT`.
Calibration mantiene sus campos numéricos/provenance inmutables; RETIRE no equivale
a invalidar ni recalcular automáticamente resultados previos.

## API y permisos

Endpoint central, con autenticación de sesión/CSRF de 18T-A:

```text
GET  /api/lifecycle/<resource>/<id>/
POST /api/lifecycle/<resource>/<id>/
```

Resources: pacientes, casos, analisis, muestras, muestras-sangre,
acquisition-series, acquisition-profiles, calibrations. También se puede inspeccionar
historial protegido (resultados-segmentacion, revisiones-segmentacion,
characterizations, calibration-references), sin acciones destructivas. Inspección
de users/institutions reservada a ADMIN/superuser.

Preview:

```json
{
  "resource_type": "muestrasaliva",
  "id": "1",
  "display": "muestrasaliva #1",
  "allowed_actions": ["ARCHIVE"],
  "recommended_action": "ARCHIVE",
  "dependencies": {"ResultadoSegmentacion": 1},
  "scientific_dependencies": true,
  "archived": false,
  "operationally_active": true,
  "media_files": [{"filename": "example.jpg"}],
  "warnings": []
}
```

POST:

```json
{"action":"ARCHIVE","reason":"Creado/subido por error","confirm":true}
```

Respuesta 200 con action, event_id y target_id. El DELETE genérico de viewsets
queda cerrado, incluso para plataforma; todas las eliminaciones usan este contrato
central equivalente. No se pide contraseña nuevamente.

Códigos: 400 input/motivo/confirmación inválidos; 403 rol insuficiente; 404 target
no visible/cross-tenant/inexistente; 409 dependencias/estado incompatibles.
Conflictos incluyen code, recommended_action, dependencies y warnings.
Códigos principales: SCIENTIFIC_DEPENDENCIES_EXIST, ACTION_NOT_AVAILABLE,
PARENT_ARCHIVED, PROFILE_UNAVAILABLE, CALIBRATION_RETIRED, INSTITUTION_MISMATCH,
RESOURCE_ARCHIVED y MEDIA_INSPECTION_FAILED. PendingSegmentationExecution aparece
como dependencia y RESOURCE_BUSY como warning: no cambiar lifecycle durante el cálculo.

Los controles de institución/usuario inactivos y último ADMIN permanecen. Desactivar
Institution ahora exige confirm_deactivation=true en la API de plataforma, con
advertencia explícita en UI; no se desactiva LASAID como prueba. Django admin también
advierte y no permite borrado de Institution/User ni del historial científico.

## Transacciones, concurrencia y storage

- Reconsulta de target/dependencias dentro de atomic y select_for_update sobre
  ancestros/target. Los escritores operacionales revalidan relaciones bajo locks.
- SQLite no implementa row locks: su serialización de escrituras y rollback
  impiden confirmar un borrado tras un conflicto. Un fallo de concurrencia de BD
  no implica éxito; el operador debe actualizar/reintentar. No se implementó retry
  automático ni un sistema distribuido de locks.
- Estado + evento se confirman juntos. Fallar la creación del evento revierte la
  operación. No se confía en el preview enviado por frontend.
- La segmentación mantiene llamadas HTTP fuera de transacciones largas, conserva
  sus registros de fallo y revalida disponibilidad al persistir. No cambia la
  matemática ni las reglas editoriales de reemplazo.
- Una ejecución pendiente, incluso ALL antes de tener FK a resultado, se detecta
  por su referencia durable sample_id; bloquea lifecycle hasta terminar.
- HARD_DELETE calcula hash antes de borrar la fila. Los bytes se borran después
  del commit, nunca al hacer rollback.
- Antes de borrar bytes se buscan referencias del mismo nombre en todos los
  FileField/ImageField del dominio. Ante posible archivo compartido se conserva:
  SHARED_FILE_RETAINED. No se borran otros archivos como compensación.
- Si storage.delete falla: evento con MEDIA_DELETE_FAILED y tipo de excepción;
  registro ya eliminado, archivo conservado para limpieza administrativa posterior.
- PENDING_DELETE permanece si el proceso se interrumpe antes del callback: evidencia
  para reconciliación futura. No hay worker automático de limpieza.
- Un archivo ausente antes de eliminar registra missing_before_delete y hash NULL.
- No hay soporte para escritores que omitan la capa de dominio mediante SQL/bulk
  updates arbitrarios. Los tests verifican la revalidación de dependencias agregadas
  entre preview y ejecución y la cancelación ante archivo concurrente.

## Frontend

- Registro: «Gestionar registros existentes», listado por Patient/Case/Analysis/
  Sample/Series, con «Más acciones» por recurso. Separado de los selects de alta.
- Adquisición: «Más acciones» en Profile y Calibration; sin botón administrativo
  para validar calibración. Perfiles archivados no se ofrecen para nueva calibración.
- ADMIN puede incluir archivados y restaurar según preview. REVIEWER no recibe
  controles destructivos; OPERATOR consulta sólo acciones que el backend autoriza.
- Modal muestra objeto, filename, dependencias, consecuencia, recomendación,
  motivo y confirmación específica. Incluye foco inicial, retorno de foco y trampa
  de Tab; Escape cierra cuando no hay operación en curso.
- Opciones de motivo y comentario; «Otro» exige comentario. El servidor exige
  reason aunque se omita la UI. No se interpreta HTML recibido como error.
- Un 409 actualiza preview, muestra conflicto y exige confirmar de nuevo. No cambia
  silenciosamente de eliminar a archivar ni reenvía otra acción.
- Acciones deshabilitadas cuando hay trabajo sin guardar/operaciones en curso.
  Se refrescan listados/contexto tras cambios para no reutilizar selecciones obsoletas.

## Backup, migración e integridad

El backup anterior de `/tmp` no estaba disponible después de la reanudación del
entorno; se creó uno nuevo antes de cualquier migración real:

`/tmp/sicam18tb_backup_20261024T040823Z/database/db.sqlite3`

Fecha UTC del nombre; corresponde a 2026-10-23 en America/Mexico_City.
SHA-256: `7cf2704b23de4174c7a556038839527c6ce34f1e0bacbdaeb4592985049f425b`.

Incluye before.json con columnas/conteos/hashes por tabla y manifest SHA-256 de
93 media, hashes.txt y RECOVERY.md. SQLite backup API, integrity_check ok y
foreign_key_check vacío; copia legible. No es una copia adicional de media.
Detener escritores antes de restaurar; no sobrescribir cambios posteriores humanos.

Migración `0012_data_lifecycle`: 21 campos de archivo (7 modelos × 3) y
LifecycleEvent. Sin data migration destructiva. Los legacy quedan activos con
archived_at/archived_by NULL y archive_reason vacío.

Aplicación real: `python manage.py migrate --noinput`, únicamente
`api.0012_data_lifecycle... OK`. Backup revalidado contra todas las tablas antes de
migrar. Post: API 0001–0012 aplicadas; Django check PASS;
`makemigrations --check --dry-run`: No changes detected.

Se compararon todas las columnas existentes de cada tabla contra el backup
(excluyendo sólo django_migrations/contenttypes/auth_permission, modificadas por
Django al instalar el esquema). Resultado: mismas filas y valores históricos,
incluidos usuarios/sesiones; metadata de archivo nueva en NULL/vacío y
LifecycleEvent=0. Ninguna acción lifecycle real ejecutada.

Baseline posterior: 1 Institution, 4 Users, 3 perfiles operativos, 8 Patients,
8 Cases, 8 Analyses, 65 Samples SALIVA y 2 SANGRE, 1 AcquisitionProfile,
2 Series, 1 Calibration, 3 referencias, 28 segmentaciones, 27 revisiones,
24 Characterizations, 23 import records, 27 ejecuciones. Conteos históricos
sin cambios. Media 93/93 con hashes idénticos. SQLite integrity_check=ok,
foreign_key_check vacío.

Characterization 24, muestra 66: versión 2.2, COMPATIBLE_PROVISIONAL;
CAL-OPTIKA-40X-PROVISIONAL-001 conserva sx=0.055233934048 y sy=0.055010060892.
Toda la fila/JSON permanece idéntica; fingerprint:
`c80144bf271ed7e977040a69a288a14c44efc4eb93f311a07b95d320c0526b1e`.
No cambios de effective segmentation, GLCM, unidades físicas ni algoritmos.

Lectura adicional del inspector sobre datos reales (sin POST/mutación): Patient 1,
Profile 1 y Sample 66 permiten sólo ARCHIVE; Calibration 1 permite sólo RETIRE.
No se usaron credenciales ni sesiones del investigador para esta lectura de dominio.

Evidencias temporales: `/tmp/sicam18tb/integrity_final.json`,
`read_only_preview.json`, `model_graph.json`, logs de tests/build y scripts de
backup/verificación. No se añaden estos artefactos ni archivos científicos a Git.

## Pruebas y límites

La suite cubre matriz de roles, creator vs no creator, legacy NULL, cross-tenant,
inspección y conflictos, dependencias nuevas tras preview, rollback de eventos y
storage, archivo/restauración padre/hijo, historial sin mutaciones, eliminación de
archivos no compartidos, conservación de compartidos, fallo de storage, JSON-only
references, falta de permisos, Profile usado inmutable, Calibration retirada,
protección de borrador/VALIDADA/Characterization y Django admin.

Frontend cubre preview, acciones dictadas por backend, motivos, confirmación,
consecuencias, 409 y reconfirmación, roles, archivados y selectores de series.

Resultados finales de la versión implementada:

- Backend completo: **424 passed, 2 skipped**, 43.63 s; incluye 27 nuevas pruebas
  lifecycle. Las omisiones existentes corresponden a pruebas condicionales;
  no se convirtieron fallos de lifecycle en skips.
- Frontend: **177 PASS** (Registro 40, Acquisition 19, Segmentación/editor 59,
  Characterization 2.1 22, Characterization 2.2 15, Auth 12, Lifecycle 10).
- `npm run build`: PASS, 125 módulos.
- Django check, migraciones/check, integridad y `git diff --check`: PASS.

Se actualizó un test previo de Acquisition por el cambio contractual explícito:
un PATCH administrativo no puede promover Calibration a VALIDATED. Sí conserva
la edición de notas; la inmutabilidad numérica continúa comprobada. Las regresiones
selectivas verifican que la llamada al microservicio sigue fuera de una transacción
y que sus fallos/cancelaciones permanecen durables.

La revisión visual real de los nuevos menús/modales queda para el investigador.
READY_FOR_DATA_LIFECYCLE_REVIEW no autoriza eliminar ni archivar datos reales
mediante scripts. Se recomienda probar primero un registro vacío deliberadamente
creado para la revisión humana, inspeccionar el impacto y comprobar el evento;
las operaciones científicas destructivas ya están cubiertas en test DB.

## Pendientes conservados

IMPORTANT_PENDING_18S_A2; HISTORICAL_ACQUISITION_ASSOCIATION;
RETIRED_RECALCULATION_POLICY; DURABLE_UPLOAD_IDEMPOTENCY;
GLCM_PHYSICAL_DISTANCE_NORMALIZATION; MANUAL_VISUAL_REVIEW_18S_D;
PRODUCTION_MEDIA_ACCESS_CONTROL (DEPLOYMENT_ACTION_REQUIRED);
MULTI_INSTITUTION_USER_MEMBERSHIP; PASSWORD_RESET_EMAIL.

Añadidos: PROFILE_VERSIONING_ENHANCEMENT (clone/versionado futuro),
ARCHIVED_DATA_RETENTION_POLICY (sin purga), ORPHAN_MEDIA_CLEANUP (reconciliar
PENDING_DELETE/MEDIA_DELETE_FAILED). No se resolvió recalculación científica con
RETIRED ni se añadió dashboard de auditoría.

## Grafo auditado

FK y políticas tomadas de `_meta`, incluidas relaciones fuera de la lista inicial.
SET_NULL de autores/archivador no autoriza eliminar usuarios desde producto.
Los campos de archivo no ocultan objetos mediante managers globales.

| Modelo.campo | Destino | on_delete | Nullable | Reverse |
|---|---|---|---|---|
| LifecycleEvent.institution | Institution | PROTECT | Sí | lifecycleevent_set |
| LifecycleEvent.actor | User | SET_NULL | Sí | + |
| SicamUserProfile.user | User | CASCADE | No | sicam_profile |
| SicamUserProfile.institution | Institution | PROTECT | No | sicamuserprofile_set |
| AcquisitionProfile.archived_by | User | SET_NULL | Sí | + |
| AcquisitionProfile.created_by | User | SET_NULL | Sí | + |
| AcquisitionProfile.updated_by | User | SET_NULL | Sí | + |
| AcquisitionProfile.institution | Institution | PROTECT | Sí | acquisitionprofile_set |
| Calibration.created_by | User | SET_NULL | Sí | + |
| Calibration.updated_by | User | SET_NULL | Sí | + |
| Calibration.acquisition_profile | AcquisitionProfile | PROTECT | No | calibrations |
| CalibrationReference.created_by | User | SET_NULL | Sí | + |
| CalibrationReference.updated_by | User | SET_NULL | Sí | + |
| CalibrationReference.calibration | Calibration | PROTECT | No | references |
| AcquisitionSeries.archived_by | User | SET_NULL | Sí | + |
| AcquisitionSeries.created_by | User | SET_NULL | Sí | + |
| AcquisitionSeries.updated_by | User | SET_NULL | Sí | + |
| AcquisitionSeries.patient | Paciente | PROTECT | No | acquisition_series |
| AcquisitionSeries.acquisition_profile | AcquisitionProfile | PROTECT | No | series |
| AcquisitionSeries.calibration | Calibration | PROTECT | Sí | series |
| Paciente.archived_by | User | SET_NULL | Sí | + |
| Paciente.created_by | User | SET_NULL | Sí | + |
| Paciente.updated_by | User | SET_NULL | Sí | + |
| Paciente.institution | Institution | PROTECT | Sí | paciente_set |
| Caso.archived_by | User | SET_NULL | Sí | + |
| Caso.created_by | User | SET_NULL | Sí | + |
| Caso.updated_by | User | SET_NULL | Sí | + |
| Caso.paciente | Paciente | CASCADE | No | casos |
| AnalisisPred.archived_by | User | SET_NULL | Sí | + |
| AnalisisPred.created_by | User | SET_NULL | Sí | + |
| AnalisisPred.updated_by | User | SET_NULL | Sí | + |
| AnalisisPred.id_paciente_fk | Paciente | CASCADE | No | analisis |
| AnalisisPred.id_caso_fk | Caso | CASCADE | No | analisis |
| MuestraSaliva.archived_by | User | SET_NULL | Sí | + |
| MuestraSaliva.created_by | User | SET_NULL | Sí | + |
| MuestraSaliva.updated_by | User | SET_NULL | Sí | + |
| MuestraSaliva.acquisition_series | AcquisitionSeries | PROTECT | Sí | muestrasaliva_samples |
| MuestraSaliva.analisis | AnalisisPred | CASCADE | No | muestras_saliva |
| MuestraSangre.archived_by | User | SET_NULL | Sí | + |
| MuestraSangre.created_by | User | SET_NULL | Sí | + |
| MuestraSangre.updated_by | User | SET_NULL | Sí | + |
| MuestraSangre.acquisition_series | AcquisitionSeries | PROTECT | Sí | muestrasangre_samples |
| MuestraSangre.analisis | AnalisisPred | CASCADE | No | muestras_sangre |
| ResultadoAnalisis.muestra | MuestraSaliva | CASCADE | No | resultados |
| ResultadoSegmentacion.muestra | MuestraSaliva | CASCADE | Sí | resultados_segmentacion |
| ResultadoSegmentacion.muestra_sangre | MuestraSangre | CASCADE | Sí | resultados_segmentacion |
| RevisionSegmentacion.created_by | User | SET_NULL | Sí | + |
| RevisionSegmentacion.updated_by | User | SET_NULL | Sí | + |
| RevisionSegmentacion.resultado_segmentacion | ResultadoSegmentacion | CASCADE | No | revisiones |
| SegmentationExecution.resultado_segmentacion | ResultadoSegmentacion | PROTECT | Sí | executions |
| SegmentationExecution.revision | RevisionSegmentacion | PROTECT | Sí | executions |
| ResultadoCaracterizacion.created_by | User | SET_NULL | Sí | + |
| ResultadoCaracterizacion.updated_by | User | SET_NULL | Sí | + |
| ResultadoCaracterizacion.resultado_segmentacion | ResultadoSegmentacion | CASCADE | No | caracterizaciones |
| ResultadoCaracterizacion.revision_segmentacion | RevisionSegmentacion | PROTECT | Sí | caracterizaciones |
| AnalisisMascara.resultado | ResultadoAnalisis | CASCADE | No | mascaras |
| ImageJImportRecord.paciente | Paciente | PROTECT | No | imagejimportrecord_set |
| ImageJImportRecord.caso | Caso | PROTECT | No | imagejimportrecord_set |
| ImageJImportRecord.muestra | MuestraSaliva | PROTECT | No | imagejimportrecord |
| ImageJImportRecord.resultado | ResultadoSegmentacion | PROTECT | No | imagejimportrecord |

Archivos asociados:

| Modelo.campo | Storage/upload_to |
|---|---|
| CalibrationReference.source_image | evidence_path → calibration/references/<calibration_id>/<UUID><suffix> |
| MuestraSaliva.imagen | muestras/saliva/%Y/%m/ |
| MuestraSangre.imagen | muestras/sangre/%Y/%m/ |
| AnalisisMascara.imagen | mascaras/saliva/%Y/%m/ |
| ImageJImportRecord.source_mask_file | imagej/source_masks/%Y/%m/ |

Además de FK se inspeccionan referencias JSON de Characterization a Calibration/Profile
y SegmentationExecution ALL pendiente por request_metadata.sample_id.

Sin stage, commit ni push. `git status` contiene únicamente implementación,
migración, tests y docs/88 de este sprint; DB/media/artefactos de prueba no aparecen.
`git diff --stat` muestra los cambios tracked; los archivos nuevos aparecen como
untracked y no se incluyen en ese stat hasta staging, que no se realizó.

SPRINT 18T-B = READY_FOR_DATA_LIFECYCLE_REVIEW
