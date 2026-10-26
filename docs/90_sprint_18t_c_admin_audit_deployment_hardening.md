# Sprint 18T-C — Auditoría administrativa y deployment/security hardening

Inicio: 2026-10-25. Cierre técnico: 2026-10-26 (America/Mexico_City).
Estado: **READY_WITH_INFRASTRUCTURE_ACTIONS_PENDING**.

## Baseline y alcance

- Rama `master`; HEAD `6c7255e634f049afe50c99e8d0e393b01a00d280`
  (`Validate data lifecycle operations`). 18T-B y 18T-B.1 commiteados;
  working tree limpio al empezar; `git diff --check` inicial PASS.
- Backend `sicam`, Django **5.0.1**; frontend Node **24.17.0**.
- Migraciones iniciales API 0001–0012 aplicadas. Check Django inicial PASS.
- Se conserva la aceptación 18T-B.1: no se crean, borran, archivan, restauran,
  retiran ni validan objetos reales o TEST en este sprint. La única escritura de
  esquema real es 0013, con índices. No se ejecutan algoritmos científicos.
- No se implementan purga, bulk delete, UNRETIRE, export CSV/PDF, reset por correo,
  multi-institution membership, 18S-A.2 ni 18T-D. No commit ni push.

| Recurso | Total antes/después | Archivado individual | Visible operacionalmente |
|---|---:|---:|---:|
| Paciente | 9 | 2 | 7 |
| Caso | 9 | 0 | 7 |
| AnalisisPred | 9 | 0 | 7 |
| MuestraSaliva | 66 | 1 | 25 |
| MuestraSangre | 2 | 0 | 0 |
| AcquisitionSeries | 3 | 1 | 2 |
| AcquisitionProfile | 2 | 1 | 1 |

La visibilidad considera ancestros archivados: no significa que se hayan eliminado
las filas ocultas. Los valores son el estado recibido de 18T-B.1 y de la revisión
previa del investigador, no mutaciones de 18T-C.

Otros conteos conservados: 1 Institution, 4 User (SUPERUSER/ADMIN/OPERATOR/REVIEWER,
uno de cada tipo y activos), 3 SicamUserProfile, 2 Calibration (1 PROVISIONAL,
1 RETIRED), 3 CalibrationReference, 29 ResultadoSegmentacion, 28
SegmentationExecution, 27 RevisionSegmentacion, 24 ResultadoCaracterizacion,
23 ImageJImportRecord, **27 LifecycleEvent**, 1 sesión preexistente y **94 archivos**.

Separación de prueba/ciencia: quedan Patient 11, Case/Analysis 10, Sample 69,
Profile 3, Series 4, Calibration 3, resultado sintético 29 y su ejecución, según
[18T-B.1](89_sprint_18t_b1_data_lifecycle_operational_acceptance.md). Sus prefijos
TEST y el payload de aceptación permiten reconocerlos; el resultado 29 no prueba
una inferencia CURRENT real. Media: 93 archivos originales + 1 archivo sintético.
Ninguno se modifica aquí.

## Backups y continuidad de evidencia

DB real: `apps/web/Backend/db.sqlite3`.
MEDIA_ROOT real: `apps/web/Backend/media` (ambos bajo el repositorio local).

Antes de aplicar 0013 se creó y verificó:
`/tmp/sicam18tc_backup_20261025T152911Z/database/db.sqlite3`.
SHA-256: `fc9966147da6e6b184fa257ceb4709a4cd9b7e0675265326f6d5afb8f64a6b03`.
Se verificó SQLite, manifest/hash de media, conteos y hashes por PK; después de
migrar se confirmó que sólo se añadió la fila de django_migrations correspondiente.

Al reanudar el 26 de octubre, `/tmp` ya no conservaba ese respaldo ni los logs.
**Ese backup anterior no se presenta como disponible para restauración.** Se
regeneró evidencia y un respaldo consistente nuevo, ya con 0013 aplicada:

`/tmp/sicam18tc_backup_20261026T151203Z/database/db.sqlite3`

SHA-256: `572082a0ec569f3670a19ddc56293a632c09fa1b3a00ecda5bf64b67847ce876`.

Ambos usaron SQLite backup API desde conexión read-only, integrity_check=ok y
foreign_key_check sin infracciones. El respaldo disponible tiene `manifest.json`,
`hashes.txt`, `RECOVERY.md`, conteos y hashes de filas/media, directorio 0700 y BD
0600. Es **BD + manifest de media**, no una copia completa de los archivos.
No se hizo una restauración automática. El procedimiento durable está en
[deployment_production.md](deployment_production.md#backup-y-recuperación).

## Auditoría: modelo, API y permisos

Se reutiliza LifecycleEvent: actor, institución, action, target_type/target_id,
reason, metadata y created_at. No se inventa otra auditoría persistente ni una FK
al recurso eliminado. No se reescriben eventos históricos para marcarlos TEST.

Endpoints nuevos, exclusivamente ADMIN/SUPERUSER:

| Endpoint GET | Contrato |
|---|---|
| `/api/admin-audit/events/` | Lista paginada de eventos |
| `/api/admin-audit/events/<id>/` | Detalle de evento, incluso target eliminado |
| `/api/admin-audit/options/` | Acciones/tipos realmente presentes y usuarios del scope |
| `/api/admin-audit/archived/` | Archivados por tipo; incluye sección RETIRED |
| `/api/admin-audit/health/` | Diagnóstico de lectura; `check_files=true` explícito |

ADMIN sólo ve su institución; institución ajena explícita devuelve 404. OPERATOR,
REVIEWER y anónimo no acceden. SUPERUSER puede consultar globalmente o filtrar por
institution donde está soportado. Los registros sin institución no se atribuyen
silenciosamente a un ADMIN institucional. ReadOnlyModelViewSet impide POST/PATCH/
DELETE de eventos, también para SUPERUSER. Django admin no permite añadir, editar
ni borrar LifecycleEvent.

Paginación: 25 por defecto, page/page_size, máximo 100. Orden descendente por
created_at e ID. Filtros: `date_from`, `date_to`, `actor`, `action`, `target_type`,
`institution`. Fechas YYYY-MM-DD, límites inclusivos por día en TIME_ZONE; se
implementa inicio inclusivo y fin exclusivo del día siguiente. Filtros inválidos
producen 400. Opciones vacías no inventan acciones. Tipos y acciones se consultan
con DISTINCT sin el orden implícito del modelo para evitar duplicaciones.

La descripción es tipo/ID técnico; no usa `Paciente.__str__` ni nombre clínico.
Detalle: actor username, **rol actual** (no se inventa rol histórico), institución,
acción/fecha, motivo, dependencias y filename/hash/status del cleanup. Metadata se
proyecta mediante una lista explícita: no se devuelven JSON arbitrario, paths
absolutos, contraseñas o tokens. El motivo histórico es texto introducido por un
usuario; no se transforma la fila original ni se garantiza que un texto libre
antiguo carezca de PII. Su consulta queda restringida a administración.

Se indica «Recurso eliminado» para HARD_DELETE/targets ausentes. Badge TEST sólo
cuando existe evidencia explícita en el target actual o un filename de metadata
con prefijo TEST_LIFECYCLE_. **No** se asigna TEST por rango de IDs 2–27, por rol o
por una heurística clínica. Algunos eventos sobre targets ya eliminados no tienen
evidencia suficiente para badge; permanecen consultables con su motivo original.

## Archivados y restauración

Administración → Archivados ofrece Patient, Case, Analysis, Sample SALIVA/SANGRE,
Series y Profile. Lista archivo **individual**; no confunde ocultación por un
padre archivado con archived_at propio. Filtros: tipo, fechas, archivador,
institución y texto técnico/ID; no búsqueda de PII clínica.

La tabla reutiliza LifecycleActions: primero inspector, después motivo,
confirmación y POST al servicio existente. No hay segunda implementación de
RESTORE. PARENT_ARCHIVED, PROFILE_UNAVAILABLE, CALIBRATION_RETIRED y conflictos
siguen siendo resueltos por lifecycle. Restaurar padre no restaura hijos archivados
individualmente. Sin acciones automáticas sobre los TEST existentes.

Calibration RETIRED se lista separadamente; no se ofrece VALIDATED/UNRETIRE.
Fecha y autor se obtienen del evento RETIRE más reciente, **no** de updated_at/by,
que podrían cambiar por una nota posterior. Si una retirada legacy carece de
evento, estos datos son desconocidos, no inventados. El test modifica metadata de
una calibración fixture y comprueba que el retiro sigue apuntando al evento.
`RETIRED_RECALCULATION_POLICY = PENDING_DECISION` se mantiene.

## Usuarios e instituciones

La tabla de usuarios añade último login, fecha de creación y cambio de contraseña
pendiente; conserva nombre, username, correo, institución, rol y activo/inactivo.
No añade eliminación de cuentas. La protección existente del último ADMIN se
conserva y se explica en la UI; la consola SUPERUSER conserva su excepción previa.

Institution añade un resumen administrativo: admins/usuarios activos, pacientes,
pacientes archivados, profiles, calibrations y series. No se incluyen métricas
científicas. Los resúmenes se omiten para lectores operacionales sin rol ADMIN y
en el bootstrap de sesión sin contexto administrativo.

Las cuentas de prueba de aceptación OPERATOR 3 y REVIEWER 4 deben revisarse antes
de producción; ninguna cuenta actual tiene prefijo TEST inequívoco. No se etiquetan
por inferencia ni se desactivan. No se solicitan o modifican contraseñas.

## Diagnóstico operacional

Sólo lectura, sin autoreparación y sin endpoint público sensible:

| Check | Resultado real al cierre |
|---|---|
| DATABASE_CONNECTIVITY | OK |
| MIGRATIONS | OK, ninguna pendiente |
| MEDIA_ROOT_ACCESSIBLE | OK |
| LEGACY_INSTITUTION_OWNERSHIP | OK global, 0; PLATFORM_ONLY para ADMIN institucional |
| USER_PROFILES | OK, 0 incompletos detectados |
| AUTHORSHIP_CONSISTENCY | OK, 0 inconsistencias |
| LIFECYCLE_CONSISTENCY | OK, 0 incidencias |
| ORPHAN_REFERENCES | OK, 0 referencias rotas detectadas |
| CALIBRATION_PROFILE_CONSISTENCY | OK |
| SERIES_PATIENT_INSTITUTION_CONSISTENCY | OK |
| MEDIA_REFERENCES | OK tras acción manual, 0 archivos faltantes |
| ORPHAN_MEDIA_CLEANUP | PENDING_ADMIN_ACTION; no se escaneó el disco por huérfanos |
| PRODUCTION_MEDIA_ACCESS_CONTROL | DEPLOYMENT_ACTION_REQUIRED |

Los recursos sin Institution sólo se enumeran en plataforma: un ADMIN de A no
puede recibir IDs de B o de ownership no asignable. Se inspeccionan campos/FKs
conocidos, no se certifica todo posible JSON científico. NULL created_by legacy
es válido; sí se reporta autor de otra institución, incluidas revisiones y
caracterizaciones. Se detectan referencias FK rotas y cleanup PENDING/FAILED de
LifecycleEvent, sin corregirlas.

«Verificar archivos» usa storage.exists; no rehashea media ni recorre directorios
en requests ordinarios. La detección de archivos físicos sin referencia quedó
fuera de la implementación opcional. Issues devueltos se limitan a 100, con conteo
total; el diagnóstico puede recorrer las filas del scope y no es un monitor para
invocarlo en cada request. No incluye nombres de pacientes ni rutas privadas.
El estado agregado WARNING conserva explícitamente las acciones de infraestructura.

## Settings y transporte

`config/security.py` define una política comprobable por environment.
Development sigue cargando `.env` y respeta las variables legacy, con precedencia
de DJANGO_*. Production no carga el `.env` local y exige configuración explícita.

| Control | Producción |
|---|---|
| SECRET_KEY | Obligatoria en environment; rechaza ausente/corta/insecure fallback |
| DEBUG | False obligatorio; True detiene arranque |
| ALLOWED_HOSTS | Lista explícita, sin wildcard |
| CSRF/CORS | Orígenes HTTPS explícitos; CORS vacío recomendado con mismo origen |
| CORS_ALLOW_ALL_ORIGINS | Prohibido |
| Cookies | Secure; sesión HttpOnly; SameSite=Lax; CSRF legible por Axios |
| HTTPS | SSL redirect obligatorio |
| Proxy | Header confiable sólo con DJANGO_TRUST_PROXY explícito |
| HSTS | 60 segundos iniciales; subdominios/preload requieren decisión |
| Headers | DENY, nosniff, referrer same-origin |
| Sesión | 8 horas por defecto configurable; no refresh en cada request |
| Password validators | Cuatro validators Django conservados |

Login/session fixation/logout/inactivos/password gate se mantienen bajo tests de
auth. No se implementa rate limiting externo. Errores API 5xx productivos se
presentan de forma genérica conservando HTTP status; no se publican URLs internas
ni tracebacks. Desarrollo conserva sus mensajes habituales.

No se cambió el `.env` real. `git check-ignore` confirma ambos `.env` ignorados y
`git ls-files` confirma que no están versionados. Plantillas seguras:
`.env.example` para desarrollo y `.env.production.example` para producción.

## Media, static, logging y despliegue

Sample SALIVA/SANGRE, CalibrationReference e ImageJ TIFF siguen pasando por
PrivateMediaView con sesión/tenancy. Esto también protege históricos archivados.
Se añade entrega X-Accel opcional: `DJANGO_PRIVATE_MEDIA_DELIVERY=nginx` valida
archivo/ruta local dentro de MEDIA_ROOT y emite `/_sicam_private_media/...`.
El modo default `django` mantiene FileResponse autorizado. Nginx requiere location
internal y no puede servir `/media/` públicamente. No se tocó infraestructura real.

STATIC_ROOT es configurable y distinto de MEDIA_ROOT. Se probó collectstatic en
`/tmp/sicam18tc/staticfiles`: **161 archivos**, sin publicar media ni añadir assets
al repo. Vite build produce dist; no es servidor productivo.

Logs JSON operacionales usan una lista fija de metadatos: user_id, institution_id,
route pattern, status y recurso técnico. No copian body, cookies, secretos, motivos
ni geometrías. En producción también se filtran logs Django y excepciones. Los
403/409 relevantes se registran como diagnóstico, sin crear LifecycleEvents.
Los endpoints administrativos/auth y media usan private/no-store. No se añadió
APM, exportador, dashboard analítico o segundo event store.

[deployment_production.md](deployment_production.md) contiene environment, instalación
controlada, migraciones, static, frontend, WSGI pendiente, snippet Nginx con
placeholders, HTTPS/proxy, bootstrap, backup/restauración y aceptación del despliegue.
No inventa dominios/certificados/servidores reales. Gunicorn no está instalado ni
declarado; no se añadió automáticamente. SQLite continúa sin migración de motor.

## Seguridad de producción: límites reales

Se ejecutó `manage.py check --deploy` con environment productivo simulado, secret
aleatorio efímero y `app.example.invalid` exclusivamente como hostname de prueba.
Resultado: **2 warnings, 0 silenciados**:

| Check | Clasificación | Decisión |
|---|---|---|
| security.W005 | DEPLOYMENT_ACTION_REQUIRED | No forzar INCLUDE_SUBDOMAINS sin validar todos los subdominios |
| security.W021 | DEPLOYMENT_ACTION_REQUIRED | No activar PRELOAD sólo para silenciar el aviso |
| DEBUG/secret/cookies/redirect/headers | RESOLVED en simulación | Policy/tests activos |
| Secret/hosts/TLS/proxy reales | ENVIRONMENT_REQUIRED | No existe despliegue real configurado aquí |
| Nginx/media/storage/permisos | DEPLOYMENT_ACTION_REQUIRED | Prueba real de infraestructura pendiente |

**Django 5.0.1 permanece instalado y fuera de soporte.** Es un requisito de
seguridad pendiente previo a producción, no un warning que check --deploy detecte.
No se hizo un upgrade amplio de dependencias dentro de este sprint. La documentación
oficial lo identifica como rama no soportada:
[Django 5.0 checklist](https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/).
Una salida limpia de checks no certifica seguridad productiva ni dependencias.

## Migración e integridad científica

0013_lifecycle_audit_indexes: cuatro índices para (institution, created_at, id),
(action, created_at), (target_type, created_at) y (created_at, id). Actor e Institution
ya disponían de índices por FK. No hay campos científicos nuevos ni RunPython.
Se aplicó después del backup verificado. API 0001–0013 aplicadas al cierre;
makemigrations --check --dry-run indica **No changes detected**.

La verificación previa a la pausa comparó todas las filas anteriores: sin cambios;
única adición django_migrations ID 31. Al reanudar se renovó snapshot y se verificó
nuevamente igualdad exacta de tablas y media durante el cierre. Las consultas de
aceptación reales fueron GET mediante APIClient con usuario local ya conocido,
sin crear sesiones, cuentas o eventos. No equivalen a una aceptación visual.

Characterization 24 permanece version 2.2, sample 66, COMPATIBLE_PROVISIONAL.
Fingerprint:
`c80144bf271ed7e977040a69a288a14c44efc4eb93f311a07b95d320c0526b1e`.

Calibration `CAL-OPTIKA-40X-PROVISIONAL-001` sigue PROVISIONAL, sx
`0.055233934048000`, sy `0.055010060892000`, con snapshot intacto.
Hashes canónicos de filas completas, verificados contra los valores previos:

- Characterization 24:
  `a3ccc0b3015d9ae60e27fa7654520866c3d5c6dd45a1d49a5096a313ce28055f`.
- Calibration 1:
  `dc8b5071889b58ed3b48dd5b37f4455519c840397d8600081dcf7fb3d5ecfec9`.

Canonicalización: JSON sort_keys=True, separators=(',', ':'), default=str y SHA-256.
Los 94 archivos conservan tamaño/hash. Sin nuevas Characterizations, segmentaciones,
revisiones, imports, cuentas, sesiones ni LifecycleEvents. SQLite integrity=ok y
foreign_key_check vacío.

## Validaciones y revisión pendiente

| Validación | Resultado final |
|---|---|
| Backend completo | **447 passed, 2 skipped** |
| Frontend registration | 40 passed |
| Frontend acquisition | 19 passed |
| Frontend segmentationStrategies | 59 passed |
| Frontend characterization21/22 | 22 / 15 passed |
| Frontend auth/lifecycle | 12 / 11 passed |
| Frontend adminAudit | 9 passed |
| Frontend total | **187 passed** |
| npm run build | PASS, 128 módulos |
| Django check | PASS |
| makemigrations --check --dry-run | No changes detected |
| check --deploy simulado | 2 warnings HSTS clasificados, sin silenciar |
| collectstatic temporal | PASS, 161 archivos |
| SQLite/integridad/media | PASS |
| git diff --check | PASS |

Cobertura nueva: roles/scoping/paginación/filtros/fechas/detail/target eliminado;
metadata privada y evidencia TEST; archivados y restore/conflictos; usuarios y
resumen; health sano, NULL ownership, perfil incompleto, media faltante, FK rota,
autoría derivada y adquisición inconsistente; FileResponse/X-Accel para los cuatro
tipos de media, anónimo/otro tenant/archivado/path fuera de root; settings de
producción, privacidad de logs y errores. Frontend prueba navegación/roles,
filtros, detalle, paginación, respuestas obsoletas, diagnósticos y reuso lifecycle.

Sin navegador automatizado: quedan para revisión humana las nuevas pestañas,
legibilidad de filtros/detalles, estado de usuarios y diagnóstico. No se declara
aceptación visual humana. Para probar restore, usar únicamente fixtures/objetos
TEST autorizados; no restaurar automáticamente la evidencia real archivada.

Evidencia regenerada: `/tmp/sicam18tc/` contiene baseline.json, real_readback.json,
integrity_final.json, logs backend/frontend/build/deploy/collectstatic y scripts
locales de snapshot/consulta. Estos archivos son temporales; el reporte conserva
resultados y límites cuando /tmp deje de existir.

## Archivos y estado Git

Cambios backend: nuevos admin_audit, operational_health, operational_logging,
config/security y tests; rutas, serializers de administración/media, registro
read-only de eventos en Django admin, settings e índices/migración 0013.
Frontend: AdminAuditPanel, servicio adminAudit, ampliación de AdministrationView
y pruebas. Configuración: plantillas de entorno y ignore de staticfiles.
Documentación: este archivo y deployment_production.md.

No cambios en cálculos de Characterization, segmentadores, thresholds, requirements,
merge científico, geometrías, provenance persistida, pacientes o datos TEST.
Working tree contiene sólo estos cambios de 18T-C sin staging; HEAD no cambió.
No commit, push, despliegue real ni 18T-D.

## Pendientes y clasificación

Científicos conservados:
IMPORTANT_PENDING_18S_A2; HISTORICAL_ACQUISITION_ASSOCIATION;
RETIRED_RECALCULATION_POLICY; DURABLE_UPLOAD_IDEMPOTENCY;
GLCM_PHYSICAL_DISTANCE_NORMALIZATION; MANUAL_VISUAL_REVIEW_18S_D.

Operativos abiertos:

- PRODUCTION_MEDIA_ACCESS_CONTROL = DEPLOYMENT_ACTION_REQUIRED
- DJANGO_SUPPORTED_RELEASE_UPGRADE = REQUIRED_BEFORE_PRODUCTION
- MULTI_INSTITUTION_USER_MEMBERSHIP
- PASSWORD_RESET_EMAIL
- ARCHIVED_DATA_RETENTION_POLICY = PENDING_DECISION
- ORPHAN_MEDIA_CLEANUP = PENDING_ADMIN_ACTION
- LOGIN_RATE_LIMITING = DEPLOYMENT/FUTURE_HARDENING
- SQLITE_PRODUCTION_SCALABILITY = FUTURE_DEPLOYMENT_DECISION
- WSGI_PRODUCTION_SERVER = DEPLOYMENT_DECISION
- PROFILE_VERSIONING_ENHANCEMENT (previo, sin resolución incidental)

Clasificación separada:

- **APPLICATION_READY:** implementación y regresiones listas para revisión; visual
  humana pendiente. No significa que el runtime instalado esté listo para exponerlo.
- **DEPLOYMENT_READY:** documentación/plantilla listas; despliegue efectivo aún no
  realizado ni aprobado.
- **PRODUCTION_SECURITY_READY:** **NO**. Requiere actualización de Django y revisión
  de dependencias, HTTPS/Nginx/storage/permisos, WSGI y aceptación de infraestructura.

Recomendación: revisar la UI administrativa y aprobar el siguiente bloque de
actualización de dependencias/deployment en staging. No abrir 18T-D ni otros
flujos científicos como parte de este cierre.

SPRINT 18T-C = READY_WITH_INFRASTRUCTURE_ACTIONS_PENDING
