# Sprint 18T-B.1 — Aceptación operativa del data lifecycle

> Repetición más reciente: **2026-10-26**, sobre HEAD `77ca825`. Véase
> «Repetición operativa del 26 de octubre de 2026» al final. Las secciones
> anteriores conservan la evidencia histórica de la primera aceptación.

Fecha: 2026-10-25, America/Mexico_City.
Estado: **READY_WITH_MANUAL_VISUAL_REVIEW_PENDING**.

## Alcance y precheck

- Rama `master`; HEAD `618bff9add6085a186bccd134173ea6547357006`
  (`Add safe data lifecycle management`). Working tree inicialmente limpio;
  `git diff --check` pasó. 18T-B estaba commiteado.
- Python del entorno `sicam`; Node `v24.17.0`.
- `manage.py check`: sin incidencias. API 0001–0012 aplicadas.
- No se aplicaron migraciones, ni se implementó 18T-C.
- No se hicieron staging, commit ni push.
- Se usaron datos nuevos `TEST_LIFECYCLE_`, sin datos clínicos. No se ejecutaron
  CURRENT, ALT, BLOOD ni Characterization sobre la BD real.

## Método y límites de la evidencia

Las operaciones reales se hicieron mediante el router, middleware, serializers,
permisos y endpoints normales de Django/DRF, usando `APIClient` en proceso,
`enforce_csrf_checks=True`, almacenamiento real y BD de desarrollo real.
No hubo inserts SQL ni escrituras ORM directas de los objetos del escenario.

Se inicializaron sesiones temporales locales para los usuarios existentes, usando
el SessionStore de Django y su comprobación de hash de sesión. No se utilizó
`force_authenticate`, ni se desactivaron CSRF o los permisos. No se solicitaron,
cambiaron ni expusieron contraseñas; tampoco se modificó `last_login`. Cada sesión
temporal se cerró por `/api/auth/logout/`. La sesión original quedó idéntica.
Esta inicialización local no constituye una nueva aceptación del formulario de
login ni una prueba HTTP desde un navegador; el login se aceptó en 18T-A.1.

La única dependencia científica nueva es **sintética**: POST normal
`/api/muestras/69/segmentar/`, con `api.views.segment_image` sustituido temporalmente
en el proceso de aceptación por una respuesta controlada. Todas las salidas HTTP
externas de `requests` se bloquearon en ese proceso. El microservicio no se ejecutó.
El normalizador y la persistencia sí fueron los productivos. `respuesta_json`
incluye `acceptance.synthetic=true`, `microservice_executed=false` y el marcador
`TEST_LIFECYCLE_18TB1`. El resultado 29 lleva strategy `CURRENT_CUSTOM_V1` porque
se ejercitó esa ruta de API; **no es evidencia de inferencia CURRENT real** y no
puede emplearse en evaluaciones científicas. Resultado, muestra y ejecución quedan
bajo el paciente sintético archivado.

Se registraron 105 peticiones del escenario, 26 comprobaciones explícitas y 36
comprobaciones adicionales de listados. Protección cross-institution, operador
no creador, Characterization y revisión VALIDADA se comprobaron con fixtures
sintéticos en BD/storage aislados. No se creó una segunda institución ni usuarios.
La revisión visual en navegador queda pendiente: las pruebas SSR/componentes no
la sustituyen.

## Baseline real y conteos finales

El baseline actual ya contenía **1 paciente archivado y 1 LifecycleEvent**.
No se asumió el cero descrito al finalizar 18T-B; ambas filas preexistentes se
preservaron. El evento inicial no forma parte de esta aceptación.

| Modelo | Antes | Después de limpieza |
|---|---:|---:|
| Institution | 1 | 1 |
| User | 4 | 4 |
| Paciente | 8 | 9 |
| Caso | 8 | 9 |
| AnalisisPred | 8 | 9 |
| MuestraSaliva | 65 | 66 |
| MuestraSangre | 2 | 2 |
| AcquisitionSeries | 2 | 3 |
| AcquisitionProfile | 1 | 2 |
| Calibration | 1 | 2 |
| CalibrationReference | 3 | 3 |
| ResultadoSegmentacion | 28 | 29 |
| SegmentationExecution | 27 | 28 |
| RevisionSegmentacion | 27 | 27 |
| ResultadoCaracterizacion | 24 | 24 |
| ImageJImportRecord | 23 | 23 |
| LifecycleEvent | 1 | 27 |
| Session | 1 | 1 |

Usuarios utilizados: institución LASAID, ID 1; ADMIN ID 2, OPERATOR ID 3,
REVIEWER ID 4, activos y sin cambio de contraseña pendiente. El cuarto usuario
preexistente no se utilizó. No se publican nombres, emails ni credenciales.

Archivados antes: Patient=1, demás modelos archivable=0. Después: Patient=2,
Sample SALIVA=1, Series=1, Profile=1; Case/Analysis=0 individualmente, pero sus
filas de prueba quedan ocultas por su paciente archivado.

## Backup e integridad

BD detectada mediante settings:
`/home/israel/repos/sicam-refactor/apps/web/Backend/db.sqlite3`.

MEDIA_ROOT:
`/home/israel/repos/sicam-refactor/apps/web/Backend/media`.

Backup nuevo:
`/tmp/sicam18tb1_backup_20261025T151033Z/database/db.sqlite3`.

SHA-256 de la copia consistente:
`f01039ecbfb35c243ec430d9d2567d06672e7bf007f4a371f8324979914eea05`.

Se usó `sqlite3.Connection.backup` desde conexión de origen read-only. Copia
legible, `PRAGMA integrity_check = ok`, `foreign_key_check = []`.
Se compararon filas de la copia y origen antes de empezar. Directorio de respaldo
0700 y BD 0600. Incluye `manifest.json`, `hashes.txt`, `RECOVERY.md`, conteos,
hashes por fila y manifest/hash de media. **No es una copia completa de media**;
el alcance solicitado aquí es su manifest verificable. Los archivos científicos
originales no se sometieron a ninguna operación de borrado.

La comparación final verifica cada PK preexistente y el hash de todos sus campos
en todas las tablas: **0 filas anteriores eliminadas o alteradas**, incluidas
sesiones originales, usuarios, eventos anteriores y snapshots científicos.
Sólo se añadieron las filas sintéticas enumeradas. Integridad SQLite final OK,
sin infracciones FK. No se restauró el backup de una aceptación exitosa.

## Inventario de objetos de prueba

Todos pertenecen a LASAID ID 1, directamente o por su jerarquía. El nombre de
muestra es el basename del archivo; el nombre de resultado es un alias documental,
y su payload conserva el marcador sintético. Los prefijos distinguen estos datos
de los pacientes científicos. Los objetos borrados conservan autor en el evento.

| Modelo | ID | Label/nombre técnico | created_by | Estado final |
|---|---:|---|---|---|
| Paciente | 9 | `TEST_LIFECYCLE_EMPTY_PATIENT` | 2 | Eliminado mediante lifecycle |
| Paciente | 10 | `TEST_LIFECYCLE_DEPENDENT_PATIENT` | 2 | Eliminado mediante lifecycle |
| Caso | 9 | `TEST_LIFECYCLE_CASE_B` | 2 | Eliminado mediante lifecycle |
| AnalisisPred | 9 | `TEST_LIFECYCLE_ANALYSIS_B` | 2 | Eliminado mediante lifecycle |
| MuestraSaliva | 67 | `TEST_LIFECYCLE_empty_sample` | 3 | Eliminado mediante lifecycle |
| MuestraSaliva | 68 | `TEST_LIFECYCLE_admin_deleted_sample` | 3 | Eliminado mediante lifecycle |
| AcquisitionProfile | 2 | `TEST_LIFECYCLE_unused_profile` | 2 | Eliminado mediante lifecycle |
| Paciente | 11 | `TEST_LIFECYCLE_SCIENTIFIC_FIXTURE_PATIENT` | 2 | Archivado |
| Caso | 10 | `TEST_LIFECYCLE_CASE_D` | 2 | Conservado; oculto por paciente archivado |
| AnalisisPred | 10 | `TEST_LIFECYCLE_ANALYSIS_D` | 2 | Conservado; oculto por paciente archivado |
| AcquisitionProfile | 3 | `TEST_LIFECYCLE_used_profile` | 2 | Archivado |
| Calibration | 2 | `TEST_LIFECYCLE_unused_calibration` | 2 | Eliminado mediante lifecycle |
| AcquisitionSeries | 3 | `TEST_LIFECYCLE_empty_series` | 3 | Eliminado mediante lifecycle |
| Calibration | 3 | `TEST_LIFECYCLE_used_calibration` | 2 | RETIRED |
| AcquisitionSeries | 4 | `TEST_LIFECYCLE_used_series` | 3 | Archivado |
| MuestraSaliva | 69 | `TEST_LIFECYCLE_derived_sample` | 3 | Archivado |
| ResultadoSegmentacion | 29 | `TEST_LIFECYCLE_SYNTHETIC_RESULT` | Sin campo de autor | Conservado; oculto por paciente archivado |

Ejecución sintética: `ef2e8998-4fc1-4987-9e2a-a0c569c1f03c`, resultado 29, ALL,
COMPLETED. Este modelo y ResultadoSegmentacion no tienen campo `created_by`;
el actor de la petición fue OPERATOR 3, registrado en el journal temporal.
No se inventó autoría en sus modelos.

Propósitos: paciente 9 prueba A; paciente/caso/análisis 10/9/9 prueba B;
muestras 67/68 prueba C; paciente/caso/análisis 11/10/10 y muestra 69 prueba D;
series 3/4 pruebas E/F; profiles 2/3 pruebas G/H; calibraciones 2/3 pruebas I/J.
Se crearon 17 objetos principales y 1 SegmentationExecution; quedaron 8 objetos
principales y la ejecución como evidencia protegida. Ninguna revisión o
Characterization real nueva.

## Resultados operativos

| Caso | Evidencia y resultado |
|---|---|
| A. Patient vacío 9 | Inspector sin dependencias, `scientific_dependencies=false`, recomienda HARD_DELETE. OPERATOR/REVIEWER reciben 403; ADMIN borra, evento 2 sobrevive. |
| Motivo/confirmación | Vacío y espacios: 400; confirm=false: 400; sin eventos. Sesiones reales sin header CSRF: 403 para los tres roles. |
| B. Patient con Case/Analysis | HARD_DELETE directo devuelve 409 `SCIENTIFIC_DEPENDENCIES_EXIST`, dependencias y recomendación ARCHIVE. OPERATOR/REVIEWER no archivan (403). |
| ARCHIVE/RESTORE Patient | Oculta jerarquía operativa, ADMIN puede leer con include_archived; restaura los mismos IDs y conserva exactamente hijos. Eventos 3–8. |
| Hijo archivado | Restaurar padre no restaura el Case archivado individualmente; restaurar hijo con padre archivado da 409. Luego se restauró explícitamente. |
| C. Sample propia 67 | created_by=3; inspector sin dependencias; creador OPERATOR elimina, REVIEWER recibe 403. Archivo eliminado y media protegida devuelve 404. |
| Sample 68 por ADMIN | Creada por OPERATOR; ADMIN elimina muestra/archivo mediante lifecycle. |
| D. Sample con resultado 69 | Dependencia sintética M=1/N=1; inspector científico=true; HARD_DELETE 409. ARCHIVE conserva archivo y resultado; RESTORE conserva hash completo del resultado. |
| Media archivada | ADMIN obtiene media histórica de prueba; anónimo 403. Cross-tenant 404 en fixtures; no se abre media pública. |
| E. Series vacía 3 | Creador OPERATOR elimina; evento 13. |
| F. Series usada 4 | HARD_DELETE 409; ARCHIVE la oculta y rechaza nuevo upload 400; muestra existente permanece; RESTORE vuelve al contexto válido. |
| G. Profile sin uso 2 | HARD_DELETE recomendado y ejecutado por ADMIN, evento 11. |
| H. Profile usado 3 | HARD_DELETE 409; modificación individual de objetivo, ancho, alto, cámara, adaptador y image_mode devuelve 400. Name/notes 200. |
| Profile archivado | No aparece en lista operativa; crear Series con él devuelve 400; muestra histórica continúa disponible. Restore comprobado antes de limpieza. |
| I. Calibration sin uso 2 | Sin referencias ni Series: HARD_DELETE permitido y ejecutado. Con CalibrationReference se conserva evidencia y sólo RETIRE: cubierto por fixtures de lifecycle. |
| J. Calibration usada 3 | HARD_DELETE 409; OPERATOR/REVIEWER RETIRE 403; ADMIN RETIRE 200, estado RETIRED y evento 20. |
| No UNRETIRE | Inspector sin acciones; RESTORE 409; PATCH PROVISIONAL/VALIDATED 400. Nuevas Series y uploads ligados a la calibración retirada devuelven 400. |
| Historial protegido | Characterization y revisión VALIDADA sin delete en tests aislados; no se intentó borrar Characterization 24 real. |
| Carrera preview→ejecución | Test existente: preview permite borrar, aparece Case, POST reevalúa y devuelve 409 conservando ambos. |
| Cross-institution | Fixtures ejercitan inspect/archive/restore/delete/retire con ADMIN, OPERATOR y REVIEWER: 404 sin mutaciones. |
| No creador | Fixtures: OPERATOR no puede borrar muestra ajena o de autor NULL. No se crea otra cuenta real. |

Se verificaron listas operativas y `include_archived=true` de Patient, Case,
Analysis, Sample, Series y Profile para los tres roles (36 comprobaciones).
Sólo ADMIN con el filtro ve los objetos sintéticos archivados al final.

## Media

93 archivos originales: rutas, tamaños y SHA-256 idénticos al final.

Muestra 67:
`muestras/saliva/2026/10/TEST_LIFECYCLE_empty_sample.png`.
SHA-256 previo:
`6b1992a6643f5c82b921a8d166aee839ab2adb7932a831b31373a9d9be67f0b3`.

Evento 9 conserva filename, ruta relativa, hash previo, actor, institución,
motivo, dependencias vacías y `media_cleanup.status=DELETED`.
Se comparó el manifest justo antes/después: desapareció únicamente ese archivo.
La muestra 68 tenía otro archivo con el mismo contenido sintético; evento 10
registra su eliminación. Ningún archivo original cambió o desapareció.

Al final quedan **94 archivos**: los 93 originales y
`muestras/saliva/2026/10/TEST_LIFECYCLE_derived_sample.png`, asociado a la muestra
69 archivada. No hay referencias nuevas, imágenes de calibración ni archivos
huérfanos introducidos por esta aceptación.

## Eventos reales

Baseline 1 → final 27: **26 eventos nuevos**, IDs 2–27. Todos de institución 1.
Actor 2=ADMIN, 3=OPERATOR. Timestamps de esta tabla en UTC.
El journal y `events.csv` guardan reason exacto y metadata/dependency counts.
La tabla abrevia los dos motivos largos; no contiene PII.

| Evento | Acción | Tipo / ID histórico | Actor | Timestamp UTC | Motivo |
|---:|---|---|---:|---|---|
| 2 | HARD_DELETE | paciente / 9 | 2 | 2026-10-25 15:12:45.722132Z | Datos de prueba 18T-B.1 |
| 3 | ARCHIVE | paciente / 10 | 2 | 2026-10-25 15:12:45.777537Z | Datos de prueba 18T-B.1 |
| 4 | RESTORE | paciente / 10 | 2 | 2026-10-25 15:12:45.812413Z | Datos de prueba 18T-B.1 |
| 5 | ARCHIVE | caso / 9 | 2 | 2026-10-25 15:12:45.834482Z | Datos de prueba 18T-B.1 |
| 6 | ARCHIVE | paciente / 10 | 2 | 2026-10-25 15:12:45.843588Z | Datos de prueba 18T-B.1 |
| 7 | RESTORE | paciente / 10 | 2 | 2026-10-25 15:12:45.856526Z | Datos de prueba 18T-B.1 |
| 8 | RESTORE | caso / 9 | 2 | 2026-10-25 15:12:45.868142Z | Datos de prueba 18T-B.1 |
| 9 | HARD_DELETE | muestrasaliva / 67 | 3 | 2026-10-25 15:12:46.474646Z | Muestra subida por error |
| 10 | HARD_DELETE | muestrasaliva / 68 | 2 | 2026-10-25 15:12:46.979340Z | Datos de prueba 18T-B.1 |
| 11 | HARD_DELETE | acquisitionprofile / 2 | 2 | 2026-10-25 15:12:47.018405Z | Datos de prueba 18T-B.1 |
| 12 | HARD_DELETE | calibration / 2 | 2 | 2026-10-25 15:12:47.093787Z | Datos de prueba 18T-B.1 |
| 13 | HARD_DELETE | acquisitionseries / 3 | 3 | 2026-10-25 15:12:47.118484Z | Datos de prueba 18T-B.1 |
| 14 | ARCHIVE | muestrasaliva / 69 | 2 | 2026-10-25 15:12:47.246637Z | Datos de prueba 18T-B.1 |
| 15 | RESTORE | muestrasaliva / 69 | 2 | 2026-10-25 15:12:47.275069Z | Datos de prueba 18T-B.1 |
| 16 | ARCHIVE | acquisitionseries / 4 | 2 | 2026-10-25 15:12:47.303466Z | Datos de prueba 18T-B.1 |
| 17 | RESTORE | acquisitionseries / 4 | 2 | 2026-10-25 15:12:47.335712Z | Datos de prueba 18T-B.1 |
| 18 | ARCHIVE | acquisitionprofile / 3 | 2 | 2026-10-25 15:12:47.433514Z | Datos de prueba 18T-B.1 |
| 19 | RESTORE | acquisitionprofile / 3 | 2 | 2026-10-25 15:12:47.466452Z | Datos de prueba 18T-B.1 |
| 20 | RETIRE | calibration / 3 | 2 | 2026-10-25 15:12:47.513777Z | Datos de prueba 18T-B.1 |
| 21 | HARD_DELETE | analisispred / 9 | 2 | 2026-10-25 15:12:47.579522Z | Datos de prueba 18T-B.1 |
| 22 | HARD_DELETE | caso / 9 | 2 | 2026-10-25 15:12:47.597476Z | Datos de prueba 18T-B.1 |
| 23 | HARD_DELETE | paciente / 10 | 2 | 2026-10-25 15:12:47.610222Z | Datos de prueba 18T-B.1 |
| 24 | ARCHIVE | muestrasaliva / 69 | 2 | 2026-10-25 15:12:47.627720Z | Evidencia sintética conservada |
| 25 | ARCHIVE | acquisitionseries / 4 | 2 | 2026-10-25 15:12:47.642437Z | Evidencia sintética conservada |
| 26 | ARCHIVE | acquisitionprofile / 3 | 2 | 2026-10-25 15:12:47.657211Z | Evidencia sintética conservada |
| 27 | ARCHIVE | paciente / 11 | 2 | 2026-10-25 15:12:47.672552Z | Evidencia sintética conservada |

Motivo exacto evento 9: `Imagen de prueba subida por error`.
Motivo exacto eventos 24–27:
`Datos de prueba 18T-B.1 conservados como evidencia; no utilizar científicamente`.
Resto: `Datos de prueba 18T-B.1`.

Los eventos 2, 9, 10, 11, 12, 13, 21, 22 y 23 sobreviven a sus targets eliminados.
No se borró ningún evento, ni se usó SQL directo/purga para limpiar.

## Conservación científica y limpieza

La limpieza eliminó sólo objetos sin dependencias, mediante API lifecycle:
muestras vacías, Series vacía, Profile vacío, Calibration vacía y jerarquía B
(desde Analysis hasta Patient). El resultado sintético es historial protegido:
no se eliminó para forzar un borrado de sus padres.

Quedan archivados Patient 11, Sample 69, Series 4 y Profile 3; Case 10 y Analysis
10 quedan ocultos por el Patient. Calibration 3 queda RETIRED y con label TEST.
Resultado 29 y ejecución sintética permanecen trazables bajo esa jerarquía.
No se debe desarchivar ni reutilizar esta calibración como configuración científica.

Characterization 24 conserva exactamente toda su fila y JSON:
version 2.2, sample 66, `COMPATIBLE_PROVISIONAL`, snapshot de Calibration 1,
sx `0.055233934048000`, sy `0.055010060892000`.
`provenance.fingerprint`:
`c80144bf271ed7e977040a69a288a14c44efc4eb93f311a07b95d320c0526b1e`.

Calibration real `CAL-OPTIKA-40X-PROVISIONAL-001` permanece PROVISIONAL, con
escalas idénticas y **0 LifecycleEvents** aplicados a ella. No se recalculó nada.
Todos los pacientes, casos, análisis, muestras, segmentaciones, revisiones,
caracterizaciones y metadatos de adquisición que existían antes siguen idénticos.

## Bug mínimo y cobertura adicional

Única corrección productiva: la etiqueta RETIRE decía `Retirar`; el criterio de
aceptación exige `Retirar calibración`. Se cambió sólo ese texto en
`src/services/lifecycle.js`. No cambian payloads, permisos, estados o algoritmos.

Regresión frontend: comprueba el literal y render del modal, recomendación de
HARD_DELETE sin dependencias, RETIRE en calibración usada y ausencia de acciones
administrativas de UNRETIRE. También verifica rechazo de motivo sólo espacios.

Cobertura backend añadida: validar una revisión sintética por endpoint normal,
confirmar que aun VALIDADA no ofrece lifecycle delete, rechaza HARD_DELETE 409 y
conserva objetos/estado sin eventos. No hubo bug de backend ni cambios de modelo.

## Validaciones finales

| Validación | Resultado |
|---|---|
| Backend completo `python -m pytest -q -p no:cacheprovider` | **425 passed, 2 skipped** |
| Frontend registration | 40 passed |
| Frontend acquisition | 19 passed |
| Frontend segmentationStrategies | 59 passed |
| Frontend characterization21 | 22 passed |
| Frontend characterization22 | 15 passed |
| Frontend auth | 12 passed |
| Frontend lifecycle | 11 passed |
| Total frontend, ejecutando cada `tests/*.test.mjs` con Node | **178 passed** |
| `npm run build` | PASS, 125 módulos |
| `python manage.py check` | PASS |
| `python manage.py makemigrations --check --dry-run` | No changes detected |
| `showmigrations api` | 0001–0012 aplicadas; ninguna nueva |
| SQLite integrity / foreign keys | ok / ninguna infracción |
| Filas y media baseline | 0 cambios |
| `git diff --check` | PASS |

## Revisión visual pendiente

No se automatizó un navegador ni se atribuye aprobación visual al investigador.
Los objetos vacíos de aceptación ya se limpiaron; no se debe usar un paciente o
imagen científica para reproducir acciones destructivas. Para repetir visualmente
A/D se crearán nuevos objetos TEST desechables por UI; para C/E/F puede inspeccionarse
la evidencia archivada, sin desarchivar toda la jerarquía por accidente. G ya se
retiró: repetir RETIRE requiere otra calibración TEST, nunca la calibración real.
Este checklist describe una futura revisión manual, no acciones adicionales
realizadas en esta aceptación:

- [ ] A. Patient vacío: Más acciones → Eliminar.
- [ ] B. Patient con datos: Más acciones → Archivar.
- [ ] C. Ver archivados: Restaurar.
- [ ] D. Sample vacía: Eliminar imagen.
- [ ] E. Sample con datos: Archivar imagen.
- [ ] F. Profile usado: no editar parámetros científicos.
- [ ] G. Calibration utilizada: Retirar.

En cada modal comprobar objeto, dependencias, acción recomendada, consecuencias,
motivo y confirmación. Etiquetas: Eliminar permanentemente / Archivar / Restaurar /
Retirar calibración. REVIEWER no muestra botones; OPERATOR sólo puede borrar sus
Samples/Series sin dependencias. El modal usa las acciones permitidas por backend.

Acceso local conocido: `http://127.0.0.1:5173/`.

```bash
cd ~/repos/sicam-refactor/apps/web/Backend
conda activate sicam
python manage.py runserver 127.0.0.1:8000
```

```bash
cd ~/repos/sicam-refactor/apps/web/Frontend
nvm use 24.17.0
npm run dev -- --host 127.0.0.1 --port 5173
```

No hace falta iniciar microservicios para revisar lifecycle. No se arrancaron ni
se dejaron procesos adicionales por esta aceptación.

## Evidencia temporal, Git y siguientes pasos

`/tmp/sicam18tb1/`: baseline.json, acceptance.py/log/json, readback.py/log/json,
integrity_final.json, events.csv, logs backend/frontend/build y scripts de
snapshot/documentación. `acceptance.json` contiene IDs, peticiones y los eventos
completos; sólo los objetos sintéticos se incluyen en respuestas guardadas.
Los artefactos de /tmp son temporales y no se versionan; esta documentación
conserva los resultados esenciales.

Archivos modificados:

- `apps/web/Frontend/src/services/lifecycle.js`: etiqueta RETIRE.
- `apps/web/Frontend/tests/lifecycle.test.mjs`: cobertura contextual/rechazo.
- `apps/web/Backend/api/test_lifecycle.py`: protección de VALIDADA.
- `docs/89_sprint_18t_b1_data_lifecycle_operational_acceptance.md`: este informe nuevo.

Sin cambios de lógica backend, modelos, migraciones, requirements o cálculos.
HEAD permanece `618bff9add6085a186bccd134173ea6547357006`. Sin staging/commit/push.

Se conservan los pendientes:

- IMPORTANT_PENDING_18S_A2
- HISTORICAL_ACQUISITION_ASSOCIATION
- RETIRED_RECALCULATION_POLICY
- DURABLE_UPLOAD_IDEMPOTENCY
- GLCM_PHYSICAL_DISTANCE_NORMALIZATION
- MANUAL_VISUAL_REVIEW_18S_D
- PRODUCTION_MEDIA_ACCESS_CONTROL = DEPLOYMENT_ACTION_REQUIRED
- MULTI_INSTITUTION_USER_MEMBERSHIP
- PASSWORD_RESET_EMAIL
- ARCHIVED_DATA_RETENTION_POLICY
- ORPHAN_MEDIA_CLEANUP
- PROFILE_VERSIONING_ENHANCEMENT (pendiente previo de 18T-B, tampoco resuelto)

Recomendación: completar revisión visual y luego 18T-C, para auditoría
administrativa, consulta de LifecycleEvent, gestión de archivados, hardening de
despliegue/media/Nginx y refinamiento operativo. No se implementa 18T-C aquí.

SPRINT 18T-B.1 = READY_WITH_MANUAL_VISUAL_REVIEW_PENDING


## Repetición operativa del 26 de octubre de 2026

Estado: **READY_WITH_MANUAL_VISUAL_REVIEW_PENDING**.

### Precheck y alcance de esta repetición

- Rama `master`, HEAD `77ca825d9b89cd8f8f561502602104de84c8a2a1`.
  Working tree limpio al iniciar; 18T-B y la aceptación anterior commiteados.
- Django check PASS; migraciones API 0001–0013 ya aplicadas, incluida
  `0013_lifecycle_audit_indexes`. No se aplicó ni creó ninguna migración.
- 18T-C ya forma parte del baseline actual. No se reimplementó ni se amplió.
- Sólo se actualiza este documento. No hubo bug nuevo, corrección productiva,
  staging, commit ni push.
- Se preservaron también todos los objetos TEST anteriores; se creó un conjunto
  independiente con prefijo `TEST_LIFECYCLE_R2_20261026T170113`.

La BD inicial contenía **25 Characterizations**, 27 LifecycleEvents y 94 archivos
media. La primera aceptación documentada arriba tenía 24 Characterizations y
93 archivos iniciales. Estos valores actuales se midieron **antes** de escribir:
no se atribuye su diferencia a esta repetición, ni se corrige ningún dato previo.

### Backup y método

BD: `/home/israel/repos/sicam-refactor/apps/web/Backend/db.sqlite3`.
MEDIA_ROOT: `/home/israel/repos/sicam-refactor/apps/web/Backend/media`.

Backup consistente nuevo, creado y verificado antes de las operaciones:
`/tmp/sicam18tb1_backup_20261026T165923Z/database/db.sqlite3`.
SHA-256: `5f37d49eea374a67c47132e03c27c19c24171f4ca69d1664f5601ddf0c33e5cd`.
SQLite backup desde conexión read-only; `integrity_check=ok`, foreign keys sin
infracciones. Directorio con `manifest.json`, `hashes.txt`, `RECOVERY.md` y copia
legible de BD. El manifiesto registra conteos, hashes de filas y de los 94 archivos;
**no constituye una copia completa de media**.

Se repitió la aceptación por APIClient en proceso, con API normal, BD/storage
reales, sesiones Django temporales y CSRF habilitado. Usuarios existentes de
LASAID (institución 1): ADMIN 2, OPERATOR 3, REVIEWER 4. No se crearon cuentas,
no se pidieron ni modificaron contraseñas y las sesiones temporales terminaron
por logout. La sesión preexistente quedó intacta. Esta evidencia no sustituye
una prueba visual del navegador ni prueba nuevamente el formulario de login.

Resultado: **140 peticiones registradas y 65 comprobaciones explícitas PASS**,
incluidas 36 comprobaciones de listados operativos/históricos por rol y 3 rechazos
CSRF. Las operaciones inválidas no crearon objetos ni eventos inesperados.

La dependencia de sample 72 es sintética: POST normal de segmentación con
`api.views.segment_image` sustituido sólo en el proceso de aceptación, bloqueando
salidas HTTP de `requests`. Se ejercitaron normalizador y persistencia reales,
sin ejecutar CURRENT/ALT/BLOOD. Resultado 30 conserva `acceptance.synthetic=true`,
`microservice_executed=false` y el marcador del intento. Su strategy
`CURRENT_CUSTOM_V1` **no acredita una inferencia CURRENT real**. Ejecución
`0a177e24-932b-4b84-bbce-62fbba41f07e`, M=1/N=1/MN=0 sintéticos.
No se ejecutó Characterization ni se creó una revisión.

### Objetos y escenarios reales

Todos los objetos pertenecen a institución 1. La etiqueta de cada fila es el
prefijo del intento seguido del sufijo indicado. Actor = usuario creador por API.

| Sufijo / propósito | Recurso | ID | Actor | Estado final |
|---|---|---:|---:|---|
| `empty_patient` | pacientes | 12 | 2 | Eliminado mediante API |
| `patient_B` | pacientes | 13 | 2 | Eliminado mediante API |
| `case_B` | casos | 11 | 2 | Eliminado mediante API |
| `analysis_B` | analisis | 11 | 2 | Eliminado mediante API |
| `empty_sample` | muestras | 70 | 3 | Eliminado mediante API |
| `admin_deleted_sample` | muestras | 71 | 3 | Eliminado mediante API |
| `unused_profile` | acquisition-profiles | 4 | 2 | Eliminado mediante API |
| `patient_D` | pacientes | 14 | 2 | Archivado |
| `case_D` | casos | 12 | 2 | Conservado bajo paciente archivado |
| `analysis_D` | analisis | 12 | 2 | Conservado bajo paciente archivado |
| `used_profile` | acquisition-profiles | 5 | 2 | Archivado |
| `unused_calibration` | calibrations | 4 | 2 | Eliminado mediante API |
| `empty_series` | acquisition-series | 5 | 3 | Eliminado mediante API |
| `used_calibration` | calibrations | 5 | 2 | RETIRED |
| `used_series` | acquisition-series | 6 | 3 | Archivado |
| `derived_sample` | muestras | 72 | 3 | Archivado |

Resultado 30 y su ejecución no disponen de campo `created_by`; el actor de la
petición fue OPERATOR 3 y su institución se resuelve por la muestra.

| Escenario | Evidencia de esta repetición | Resultado |
|---|---|---|
| A: paciente vacío | Patient 12 sin dependencias, inspector recomienda HARD_DELETE; delete ADMIN y evento 28 persistido | PASS |
| B: paciente dependiente | Patient 13, Case 11, Analysis 11: delete 409; archive oculta jerarquía; restore conserva hijos; archivo propio de Case sobrevive restauración del padre | PASS |
| C: muestra vacía | Sample 70 propia de OPERATOR, eliminación real del archivo; sample 71 eliminada por ADMIN | PASS |
| D: muestra dependiente | Sample 72: inspector científico, delete 409, archivo y resultado intactos al archivar/restaurar | PASS |
| E/F: series | Series 5 vacía eliminada por creador; Series 6 usada no eliminable, archive/restore y rechazo de nuevo upload | PASS |
| G/H: profiles | Profile 4 vacío eliminado; Profile 5 usado no eliminable, archive/restore; nuevas Series bloqueadas al estar archivado | PASS |
| Inmutabilidad profile | Rechazo 400 de objective, width, height, camera, adapter, image mode; nombre/notes administrativos permitidos | PASS |
| I: calibración vacía | Calibration 4 sin referencias ni uso: HARD_DELETE permitido | PASS |
| J: calibración usada | Calibration 5: delete 409, RETIRE ADMIN, no RESTORE/UNRETIRE; PATCH PROVISIONAL/VALIDATED rechazado; nuevos enlaces/uploads rechazados | PASS |
| Motivo/confirmación | Vacío, espacios y confirmación ausente rechazados antes de mutar | PASS |
| Roles | ADMIN opera; OPERATOR sólo borra sus objetos vacíos; REVIEWER rechazado; archivo/retire no permitido a OPERATOR | PASS |
| Histórico/media | ADMIN accede a media archivada, anónimo rechazado; listados históricos sólo ADMIN; media conservada | PASS |
| Conflicto | 409 con `SCIENTIFIC_DEPENDENCIES_EXIST`, `recommended_action`, `dependencies` | PASS |

La matriz cross-institution, acceso a media desde otra institución, operador no
creador, protección de Characterization y VALIDADA, y dependencia creada entre
preview/delete se verificaron en tests aislados existentes (`api/test_lifecycle.py`).
No se creó otra institución en la BD de trabajo. Los tests de componentes verifican
terminología, motivo, confirmación, roles, acciones permitidas, ausencia de UNRETIRE,
modal de dependencias y mensajes de conflicto. No se atribuye observación visual.

CalibrationReference cuenta como evidencia según política: no se fuerza su borrado;
la calibración vacía de este escenario no tenía referencias.

### Conteos e integridad final

| Tabla | Antes | Después |
|---|---:|---:|
| `api_institution` | 1 | 1 |
| `auth_user` | 4 | 4 |
| `api_sicamuserprofile` | 3 | 3 |
| `api_paciente` | 9 | 10 |
| `api_caso` | 9 | 10 |
| `api_analisispred` | 9 | 10 |
| `api_muestrasaliva` | 66 | 67 |
| `api_muestrasangre` | 2 | 2 |
| `api_acquisitionseries` | 3 | 4 |
| `api_acquisitionprofile` | 2 | 3 |
| `api_calibration` | 2 | 3 |
| `api_calibrationreference` | 3 | 3 |
| `api_resultadosegmentacion` | 29 | 30 |
| `api_segmentationexecution` | 28 | 29 |
| `api_revisionsegmentacion` | 27 | 27 |
| `api_resultadocaracterizacion` | 25 | 25 |
| `api_imagejimportrecord` | 23 | 23 |
| `api_lifecycleevent` | 27 | 53 |
| `django_session` | 1 | 1 |

- **0 filas preexistentes modificadas/eliminadas**, comparadas por PK y hash de
  fila completa en todas las tablas. Sólo se agregaron las filas TEST/eventos
  identificados en el journal. Usuarios, institución y sesiones previas idénticos.
- **94/94 archivos preexistentes idénticos** por tamaño/SHA-256; final 95 archivos.
  Se eliminaron las imágenes TEST de samples 70 y 71; sus eventos conservan hash
  y estado `DELETED`. Sólo permanece la imagen sintética archivada de sample 72:
  `muestras/saliva/2026/10/TEST_LIFECYCLE_R2_20261026T170113_derived_sample.png`.
- PNG sintéticos de 32×32 RGB, SHA-256 de la imagen eliminada y de la conservada:
  `6b1992a6643f5c82b921a8d166aee839ab2adb7932a831b31373a9d9be67f0b3`.
  Son fixtures idénticos en archivos diferentes; no hay media huérfana nueva.
- Characterization 24/sample 66 intacta en toda su fila/JSON: versión 2.2,
  `COMPATIBLE_PROVISIONAL`, snapshot y fingerprint
  `c80144bf271ed7e977040a69a288a14c44efc4eb93f311a07b95d320c0526b1e`.
- Calibration 1 real intacta, PROVISIONAL, sx=`0.055233934048000`,
  sy=`0.055010060892000`, **0 LifecycleEvents** aplicados a ella.
- Resultado sintético 30 también conserva su hash completo tras archive/restore,
  retiro de calibración y limpieza; no cambió el contenido científico previo.
- SQLite `integrity_check=ok`, `foreign_key_check=[]`.

Limpieza mediante lifecycle API exclusivamente, sin purga ni SQL destructivo.
Permanecen Patient 14, Sample 72, Series 6 y Profile 5 archivados; Case 12 y
Analysis 12 ocultos por el paciente. Calibration 5 RETIRED, resultado 30 y ejecución
se conservan por trazabilidad. Todos con marcador TEST. No se borraron eventos.
Archivados finales: pacientes=3, SALIVA=2, series=2, profiles=2; casos/análisis=0
individualmente. Incluyen la evidencia previa, preservada íntegramente.

### Eventos de esta repetición

27 iniciales → 53 finales, **26 nuevos (28–53)**. Todos institución 1.
Actor 2=ADMIN, 3=OPERATOR. Se conserva motivo completo en la tabla y en `events.csv`.

| ID | Acción | Tipo / ID | Actor | Timestamp UTC | Motivo |
|---:|---|---|---:|---|---|
| 28 | HARD_DELETE | paciente / 12 | 2 | 2026-10-26 17:01:13.482232+00:00 | Datos de prueba 18T-B.1 (repetición controlada) |
| 29 | ARCHIVE | paciente / 13 | 2 | 2026-10-26 17:01:13.625713+00:00 | Datos de prueba 18T-B.1 (repetición controlada) |
| 30 | RESTORE | paciente / 13 | 2 | 2026-10-26 17:01:13.707872+00:00 | Datos de prueba 18T-B.1 (repetición controlada) |
| 31 | ARCHIVE | caso / 11 | 2 | 2026-10-26 17:01:13.774141+00:00 | Datos de prueba 18T-B.1 (repetición controlada) |
| 32 | ARCHIVE | paciente / 13 | 2 | 2026-10-26 17:01:13.807326+00:00 | Datos de prueba 18T-B.1 (repetición controlada) |
| 33 | RESTORE | paciente / 13 | 2 | 2026-10-26 17:01:13.841607+00:00 | Datos de prueba 18T-B.1 (repetición controlada) |
| 34 | RESTORE | caso / 11 | 2 | 2026-10-26 17:01:13.868812+00:00 | Datos de prueba 18T-B.1 (repetición controlada) |
| 35 | HARD_DELETE | muestrasaliva / 70 | 3 | 2026-10-26 17:01:15.560734+00:00 | Imagen de prueba subida por error |
| 36 | HARD_DELETE | muestrasaliva / 71 | 2 | 2026-10-26 17:01:16.534199+00:00 | Datos de prueba 18T-B.1 (repetición controlada) |
| 37 | HARD_DELETE | acquisitionprofile / 4 | 2 | 2026-10-26 17:01:16.648800+00:00 | Datos de prueba 18T-B.1 (repetición controlada) |
| 38 | HARD_DELETE | calibration / 4 | 2 | 2026-10-26 17:01:16.832749+00:00 | Datos de prueba 18T-B.1 (repetición controlada) |
| 39 | HARD_DELETE | acquisitionseries / 5 | 3 | 2026-10-26 17:01:16.887770+00:00 | Datos de prueba 18T-B.1 (repetición controlada) |
| 40 | ARCHIVE | muestrasaliva / 72 | 2 | 2026-10-26 17:01:17.178318+00:00 | Datos de prueba 18T-B.1 (repetición controlada) |
| 41 | RESTORE | muestrasaliva / 72 | 2 | 2026-10-26 17:01:17.246178+00:00 | Datos de prueba 18T-B.1 (repetición controlada) |
| 42 | ARCHIVE | acquisitionseries / 6 | 2 | 2026-10-26 17:01:17.315346+00:00 | Datos de prueba 18T-B.1 (repetición controlada) |
| 43 | RESTORE | acquisitionseries / 6 | 2 | 2026-10-26 17:01:17.383529+00:00 | Datos de prueba 18T-B.1 (repetición controlada) |
| 44 | ARCHIVE | acquisitionprofile / 5 | 2 | 2026-10-26 17:01:17.570152+00:00 | Datos de prueba 18T-B.1 (repetición controlada) |
| 45 | RESTORE | acquisitionprofile / 5 | 2 | 2026-10-26 17:01:17.646002+00:00 | Datos de prueba 18T-B.1 (repetición controlada) |
| 46 | RETIRE | calibration / 5 | 2 | 2026-10-26 17:01:17.742322+00:00 | Datos de prueba 18T-B.1 (repetición controlada) |
| 47 | HARD_DELETE | analisispred / 11 | 2 | 2026-10-26 17:01:17.871112+00:00 | Datos de prueba 18T-B.1 (repetición controlada) |
| 48 | HARD_DELETE | caso / 11 | 2 | 2026-10-26 17:01:17.899671+00:00 | Datos de prueba 18T-B.1 (repetición controlada) |
| 49 | HARD_DELETE | paciente / 13 | 2 | 2026-10-26 17:01:17.924245+00:00 | Datos de prueba 18T-B.1 (repetición controlada) |
| 50 | ARCHIVE | muestrasaliva / 72 | 2 | 2026-10-26 17:01:17.957511+00:00 | Datos de prueba 18T-B.1; evidencia sintética conservada, no usar científicamente |
| 51 | ARCHIVE | acquisitionseries / 6 | 2 | 2026-10-26 17:01:17.984104+00:00 | Datos de prueba 18T-B.1; evidencia sintética conservada, no usar científicamente |
| 52 | ARCHIVE | acquisitionprofile / 5 | 2 | 2026-10-26 17:01:18.016380+00:00 | Datos de prueba 18T-B.1; evidencia sintética conservada, no usar científicamente |
| 53 | ARCHIVE | paciente / 14 | 2 | 2026-10-26 17:01:18.046670+00:00 | Datos de prueba 18T-B.1; evidencia sintética conservada, no usar científicamente |

Eventos 28, 35–39 y 47–49 permanecen aunque sus targets fueron eliminados.

### Validaciones de esta repetición

| Validación | Resultado |
|---|---|
| Backend completo, pytest sin cacheprovider | **447 passed, 2 skipped** |
| Frontend: registration/acquisition/segmentationStrategies | 40 / 19 / 59 passed |
| Frontend: characterization21/characterization22 | 22 / 15 passed |
| Frontend: auth/lifecycle/adminAudit | 12 / 11 / 9 passed |
| Frontend total | **187 passed**, 0 failed |
| `npm run build` | PASS, 128 módulos |
| `manage.py check` | PASS |
| `makemigrations --check --dry-run` | No changes detected |
| `showmigrations api` | 0001–0013 aplicadas, sin intervención |
| SQLite, hashes baseline y readback de filas nuevas | PASS |
| `git diff --check` | PASS |

No se inició ningún servicio adicional. Sólo queda modificado este documento;
sin código, modelos, requirements o migraciones nuevas. HEAD permanece `77ca825`.

### Revisión visual pendiente y siguientes pasos

No se automatizó navegador ni se considera aceptada la UX por estas pruebas.
Usar sólo datos TEST desechables, nunca los científicos. Los objetos vacíos ya
fueron eliminados; para repetir acciones destructivas se necesitan fixtures TEST
nuevos. No reactivar la calibración retirada ni reutilizarla científicamente.

- [ ] A. Patient vacío: Más acciones → Eliminar.
- [ ] B. Patient con datos: Más acciones → Archivar.
- [ ] C. Ver archivados: Restaurar.
- [ ] D. Sample vacía: Eliminar imagen.
- [ ] E. Sample con datos: Archivar imagen.
- [ ] F. Profile usado: no editar parámetros científicos.
- [ ] G. Calibration utilizada: Retirar.

Acceso conocido: `http://127.0.0.1:5173/`; comandos de arranque en el checklist
histórico anterior. No hacen falta microservicios. Comprobar objeto/dependencias,
consecuencias, recomendación, motivo y confirmación en los modales.

Evidencia de esta repetición: `/tmp/sicam18tb1_rerun/`, con `baseline.json`,
`acceptance.json/log/py`, `events.csv`, `readback.json/py`, `integrity_final.json`,
logs de backend/frontend/build y scripts de snapshot/documentación. Los archivos
`/tmp` son temporales; las tablas anteriores conservan lo esencial versionable.

Se mantiene la lista de pendientes documentada arriba; ninguno se resuelve
incidentalmente. La implementación de 18T-C ya está presente en el baseline;
corresponde completar esta revisión visual y continuar su aceptación/despliegue
según decisión del investigador. No se implementó nuevo trabajo de 18T-C.
Sin commit ni push.

SPRINT 18T-B.1 = READY_WITH_MANUAL_VISUAL_REVIEW_PENDING
