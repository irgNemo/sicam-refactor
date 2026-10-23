# Sprint 18T-A — Usuarios, instituciones, roles, autoría y permisos

Fecha: 2026-10-22. Estado: **READY_WITH_MEDIA_DEPLOYMENT_ACTION_PENDING**.
Revisión visual operativa pendiente. No se creó ninguna credencial real, no se
asignó institución ni autor a datos históricos. Sin commit ni push.

## Punto de partida y auditoría

- Rama `master`; HEAD inicial `0a8e3e32db0e641af4d0772a5c2393a1a6963a6d`.
- Working tree inicialmente limpio; `git diff --check` correcto.
- Django `check` correcto; migraciones API `0001`–`0010` aplicadas.
- Python del entorno `sicam`; Node `24.17.0`.
- Se mantiene `django.contrib.auth.models.User`; no se cambia `AUTH_USER_MODEL`.
- Antes, DRF utilizaba sus defaults Session/Basic authentication y AllowAny.
  Acquisition exigía autenticación; Registro, Segmentación y Characterization
  no tenían una política institucional. Vue guardaba Basic credentials sólo en
  memoria para Acquisition, sin login operativo común.
- Django servía `/media/` públicamente en DEBUG. Filtrar API no protegía esos
  archivos. Ahora ese montaje se elimina.
- Existe una cuenta activa de plataforma (`is_staff=True`, `is_superuser=True`).
  Se conservó sin cambios, sin leer ni publicar credenciales ni datos personales.
  Puede acceder al legacy no asignado después de iniciar sesión.

## Arquitectura de identidad y ownership

`Institution`: `id`, `code` único y estable, `name`, `active`, `notes`, timestamps.
`SicamUserProfile`: OneToOne a User, FK PROTECT a institución, rol comprobado por
constraint (`ADMIN`, `OPERATOR`, `REVIEWER`), `must_change_password`, timestamps.
No duplica username, correo, nombre ni contraseña. La activación es `User.is_active`.

Una cuenta operativa tiene una institución. El superuser es global; no necesita
profile. `is_staff` por sí solo no concede privilegios SICAM. El Django admin es
exclusivamente consola de plataforma: requiere superuser operativo, respetando
el cambio obligatorio de contraseña cuando exista un profile.

Ownership directo nullable: `Paciente.institution`, `AcquisitionProfile.institution`.
El caso y análisis lo derivan del paciente; muestra, resultado, revisión,
caracterización e importación lo derivan del análisis/paciente. Calibration deriva
del profile; CalibrationReference de Calibration; AcquisitionSeries del paciente.
La serie comprueba en el modelo que paciente/profile tengan la misma institución;
la calibración sigue teniendo que corresponder al profile. Profiles inactivos no
son admisibles para series nuevas y no aparecen en su selector.

**Institución operativa no es origen externo clínico.**
`external_id_namespace` conserva su significado y valor. Por ejemplo, una
institución LASAID puede custodiar una identidad externa de otro hospital.
`IDENTIFIED` y `PSEUDONYMIZED` mantienen sus campos y semántica anteriores.

## Permisos centralizados

`api/access.py` contiene `OperationalPermission`, `WRITE_ROLES`, `scoped`,
`ScopedViewMixin` y `ScopedSerializerMixin`. No depende de filtros del cliente.

| Recurso / acción | ADMIN | OPERATOR | REVIEWER | Superuser |
|---|---|---|---|---|
| Pacientes, casos, análisis, imágenes: consultar | Propia institución | Propia institución | Propia institución | Global, incluido legacy |
| Registrar / editar esos recursos | Sí | Sí | No | Sí, ownership explícito en altas |
| Crear / editar series | Sí | Sí | No | Sí |
| Profiles: consultar | Sí | Sí | Sí | Global |
| Profiles: crear / editar | Sí | No | No | Sí |
| Calibration / referencias: consultar | Sí | Sí | Sí | Global |
| Calibration / referencias: crear / administrar según reglas existentes | Sí | No | No | Sí |
| Ejecutar segmentación sobre muestra accesible | Sí | Sí | Sí | Sí |
| Crear / editar BORRADOR, reservar ID editorial | Sí | Sí | Sí | Sí |
| VALIDAR revisión | Sí | No | Sí | Sí |
| Characterization: ejecutar / consultar | Sí | Sí | Sí | Sí |
| Usuarios: listar / crear / editar / activar / desactivar | Sólo propios | No | No | Global |
| Instituciones: leer | Propia | Propia | Propia | Global |
| Instituciones: crear / editar / activar | No | No | No | Sí |
| Eliminar User o Institution por API | No | No | No | No: no existe destroy |
| DELETE institucional sobre recursos operativos | No, pendiente 18T-B | No | No | No se amplían endpoints heredados |

REVIEWER puede generar una propuesta de segmentación y trabajar su borrador como
parte de la revisión; no puede registrar pacientes, muestras ni infraestructura.
No se añadió validación científica de calibración a la UI. 18S-A.2 sigue pendiente.
No se añadieron operaciones de lifecycle. Los endpoints destructivos heredados de
Registro siguen restringidos a plataforma hasta definir la política de 18T-B.

Consultas list/detail/actions/nested/compatibility usan scoping backend. Un ID de
otra institución devuelve 404 si la acción está permitida al rol; si el rol no
puede realizar la acción, 403 antes de consultar el objeto. Relaciones FK de
serializers usan querysets filtrados. Una FK ajena se rechaza con 400, sin nombres,
conteos ni datos del recurso ajeno. Modelos nuevos sin mapa de ownership fallan
cerrados. Usuarios sin profile, inactivos, con institución inactiva o contraseña
pendiente no pueden operar. Legacy sin institución sólo es visible al superuser.

Paciente/profile nuevos toman institución del actor institucional. Intentar enviar
otra se rechaza; un superuser debe seleccionar una institución activa. La API no
reasigna ownership de objetos existentes, ni siquiera para superuser. La operación
legacy usa un command explícito separado.

## Constraints e importación ImageJ

La antigua unicidad global de `Paciente.identificacion` y de
`(external_id_namespace, external_patient_id)` impedía que dos instituciones
registraran la misma autoridad externa. `0011` las sustituye por:

- unique `(institution, identificacion)`;
- unique `(institution, external_id_namespace, external_patient_id)` cuando hay namespace;
- constraints parciales equivalentes para legacy `institution IS NULL`.

No se modifica ningún identificador existente ni la función que deriva la
identificación pseudonimizada. Caso conserva unique paciente/case_number.
Nombres de profile, calibration y series no eran globalmente únicos: permanecen
como metadata; su ownership y selección se filtran por institución.

`run_import` exige una institución activa explícita. Cada command que crea datos
requiere `--institution <code>`: `import_imagej_dataset`, `seed_demo_data`,
`seed_optika_40x_calibration`. El audit command de sólo lectura no crea ownership.
No se ejecutaron seeds ni imports reales en este sprint.

Las nuevas claves de importación incorporan la PK institucional como namespace
operativo, sin sustituir el namespace clínico. Su identidad canónica es:
`['sicam.imagej.tenant.v1', institution_id, 'sicam.imagej.import.v1', dataset,
patient_namespace, external_id, case_number]`; los hashes de sample/logical/annotation
conservan el resto del contrato anterior. No se recalcula geometría de imports
históricos. Después de una asignación explícita, los registros legacy conservan
sus claves previas: se consultan dentro del tenant y se reconocen sin rekey ni
sobrescritura. Pruebas cubren reimport legacy, dos tenants con la misma identidad y
el mismo archivo, claves distintas y no-op por tenant.

## Autoría

`AuthoredModel` añade `created_by` / `updated_by` nullable, FK User SET_NULL en
Paciente, Caso, AnalisisPred, MuestraSaliva, MuestraSangre, RevisionSegmentacion,
AcquisitionProfile, Calibration, CalibrationReference, AcquisitionSeries y
ResultadoCaracterizacion. Referencias comparten el mismo soporte abstracto y la
creación automática registra el actor; también se puede consultar su calibración.

- `created_by` se establece al crear y es inmutable en API/model.save.
- `updated_by` registra el actor de escrituras reales; no cambia al consultar.
- Payloads del cliente no pueden elegir autor.
- Crear caso con análisis, cambiar estado, crear borrador, guardar/validar revisión,
  segmentación selectiva y creación de calibración propagan el actor.
- Reutilizar un borrador existente no atribuye una edición inexistente.
- Characterization registra el solicitante solamente cuando crea el recurso.
  La respuesta idempotente no modifica autor, timestamp ni JSON histórico.
- Respuestas con autoría ofrecen `{id, username, display_name}`, sin correo.
  Detalle de profile muestra autoría cuando existe.
- CLI sin usuario request mantiene autor NULL: no inventa personas.
- Todos los autores históricos siguen NULL. No hay backfill por timestamp,
  superuser ni Git. No se implementó un AuditLog ni autoría retroactiva de
  ejecuciones históricas; `created_by/updated_by` no equivalen a un historial de eventos.

## Login, password y administración

Se reutiliza SessionAuthentication de Django/DRF. El Basic aislado de Acquisition
se sustituye por la sesión operativa compartida; no se introdujo JWT.

| Endpoint | Contrato |
|---|---|
| GET `/api/auth/me/` | `{user, csrf_token}`; `user=null` sin acceso activo |
| POST `/api/auth/login/` | `username`, `password`; requiere CSRF incluso anónimo |
| POST `/api/auth/logout/` | invalida sesión, devuelve contexto anónimo; requiere CSRF |
| POST `/api/auth/password/` | `current_password`, `new_password`, `confirmation`; requiere sesión y CSRF |
| `/api/users/`, `/api/users/<id>/` | list/create/retrieve/update; sin destroy |
| `/api/institutions/`, `/api/institutions/<id>/` | list/create/retrieve/update según rol; sin destroy |

`user` contiene id, username, nombres, email, institution, role, is_superuser,
is_active y must_change_password. Se usan `set_password`, validators de Django y
`update_session_auth_hash`. No hay signup ni recuperación por correo. No se
imprimen ni almacenan contraseñas fuera del hash; formularios limpian secretos.
La contraseña temporal se envía sólo por POST y no se devuelve en respuestas.
No se admiten is_staff/is_superuser/groups/user_permissions/password en la API de
administración. Las cuentas de plataforma se administran fuera de esta API.

Una cuenta nueva debe cambiar contraseña antes de cualquier API operativa,
incluyendo imágenes. Puede obtener /me, cambiar contraseña o cerrar sesión.
Desactivar usuario/institución bloquea los requests siguientes. Cambio de rol o
activación se serializa por institución en transaction.atomic/select_for_update:
ADMIN no puede degradar/desactivar al último ADMIN activo. Superuser tiene la
excepción administrativa explícita. No hay hard-delete de usuario ni institución en UI/API ni en Django admin.

Vue usa un estado reactivo central y bootstrap /me único. `AuthGate` no monta el
workspace antes del login/cambio obligatorio. Administración tiene guard de
navegación y guard propio de componente, además de backend. El header muestra
usuario/institución/rol/logout. La sección permite crear/editar/activar usuarios;
institución fija para ADMIN y seleccionable para superuser. No hay botón Delete.

Registro oculta altas al REVIEWER y ofrece consulta; listas de pacientes/casos
siguen disponibles en la navegación normal. Acquisition muestra metadata de sólo
lectura a no administradores. OPERATOR no ve validación de revisión. Logout y
cambio de sección respetan guards existentes del editor, Registro y Acquisition;
Administración añade guard de formularios abiertos. El contexto paciente/caso en
sessionStorage se limpia al cambiar usuario/institución o cerrar sesión. No se
persisten credenciales ni tokens de autenticación en localStorage/sessionStorage.

## Media, CSRF, CORS y despliegue

Django ya no sirve `/media/` como static público. URLs serializadas de imágenes,
incluidas las muestras anidadas de análisis, apuntan al backend protegido:

- `/api/private-media/saliva/<id>/`;
- `/api/private-media/sangre/<id>/`;
- `/api/private-media/calibration/<id>/`;
- `/api/private-media/imagej-mask/<uuid>/`.

Se resuelve el objeto autorizado antes de abrir el FileField. No se acepta una
ruta de filesystem del cliente. FileResponse usa `Cache-Control: private, no-store`,
`Vary: Cookie`, `X-Content-Type-Options: nosniff`. Sin sesión: 403; objeto ajeno: 404.
Mismas reglas para TIFF ImageJ. No se copió ni alteró ningún archivo real.

Axios usa cookies (`withCredentials`) y X-CSRFToken. /me establece cookie y token;
login rota el token y el cliente conserva el nuevo. No se desactiva CSRF.
CORS usa allowlist existente y credentials; no `CORS_ALLOW_ALL_ORIGINS`.
CSRF_TRUSTED_ORIGINS usa esa misma lista explícita. Fuera de DEBUG las cookies son
Secure; la cookie de sesión es HttpOnly. Para este WSL el API configurado es
`http://127.0.0.1:8000`; abrir Vue en `http://127.0.0.1:5173` para mantener el mismo
hostname de cookies. No mezclar localhost con 127.0.0.1.

**PRODUCTION_MEDIA_ACCESS_CONTROL = DEPLOYMENT_ACTION_REQUIRED.**
No se inspeccionó ni modificó un proxy de producción. Un alias Nginx o bucket
público anterior puede saltarse Django: eliminarlo es requisito de despliegue.
Contrato mínimo, adaptado al upstream real por quien administra el servidor:

```nginx
# Ningún alias público al MEDIA_ROOT.
location ^~ /media/ { return 404; }
location /api/ {
    proxy_pass http://sicam_backend;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
    # Conservar Cookie y X-CSRFToken; no cachear /api/private-media/.
}
```

El almacenamiento debe permanecer privado también por otros aliases/orígenes.
Servir frontend y API bajo el mismo sitio HTTPS; configurar origins permitidos y
terminación TLS de acuerdo con el proxy confiable. No se habilitó cookies para
sites arbitrarios. Antes de publicación comprobar: URL antigua anónima bloqueada,
media protegida anónima bloqueada, sesión A accede A y no B. Los tests demuestran
el comportamiento Django, no certifican la configuración externa.

## Migración, backup e invariantes reales

Backup nuevo consistente mediante API backup de SQLite:
`/tmp/sicam18ta_backup_20261022T172002Z/database/db.sqlite3`.

SHA-256: `ddd02d14ea6ed48be11bced6e11035e3742ba696f68cea4dd762e23eb1ce2bed`.
Directorio con permisos 0700; archivos privados. `before.json` contiene schema,
conteos, hashes de filas históricas y manifest SHA-256 de los 93 media;
`hashes.txt`, `RECOVERY.md`, `after.json` completan la evidencia local. No se copió
media porque esta migración no escribe storage; el backup solicitado incluye su
manifest/hash verificable. No versionar el backup.

BD resuelta: `/home/israel/repos/sicam-refactor/apps/web/Backend/db.sqlite3`.
MEDIA_ROOT: `/home/israel/repos/sicam-refactor/apps/web/Backend/media`.
Se comprobó que la BD aún coincidiera con el snapshot antes de migrar.
`0011_operational_identity` aplicada; no data migration de ownership/autoría.
Django añadió automáticamente dos content types y ocho permisos estándar: son
metadata esperada de los dos modelos nuevos, no cambios científicos. La
comparación conserva todas las filas anteriores también en esas tablas.

| Recurso | Antes | Después |
|---|---:|---:|
| Pacientes / casos / análisis | 8 / 8 / 8 | 8 / 8 / 8 |
| Muestras SALIVA / SANGRE | 65 / 2 | 65 / 2 |
| Resultados segmentación | 28 | 28 |
| Revisiones | 27 | 27 |
| Characterizations | 24 | 24 |
| Imports ImageJ / ejecuciones | 23 / 27 | 23 / 27 |
| Profiles / calibraciones / referencias / series | 1 / 1 / 3 / 2 | 1 / 1 / 3 / 2 |
| Usuarios | 1 | 1 |
| Instituciones / SicamUserProfile nuevos | No existían tablas | 0 / 0 |
| Media | 93 | 93, mismos SHA-256 |

Comparación por todas las columnas preexistentes: **idénticas**, incluyendo IDs,
geometrías, metadata, timestamps y respuestas históricas. Autores nuevos todos
NULL; pacientes/perfiles sin institución. SQLite integrity_check `ok`,
foreign_key_check sin infracciones. La caracterización 24 mantiene su JSON exacto
(SHA-256 del texto persistido
`7c85d622f6ac3ccf07c925fa07f1c25ce6deb1725cba934c443e6f17de050751`), lo que incluye
sx/sy, medidas físicas, snapshot y fingerprint sin recomputarlos. El motor de
calibración y las matemáticas 2.2 no cambiaron. El único cambio en su servicio de
persistencia es registrar actor en un recurso nuevo. No se ejecutó ningún modelo
ni Characterization sobre datos reales durante este sprint.

## Bootstrap y asignación manual posterior

Desde `apps/web/Backend`, entorno `sicam`:

```bash
python manage.py migrate
python manage.py bootstrap_institution --code LASAID --name LASAID
python manage.py create_sicam_admin
python manage.py assign_legacy_institution --institution LASAID --dry-run
```

El command de admin solicita usuario, correo, institución y contraseña con getpass,
sin argumento CLI de contraseña; no concede is_staff/is_superuser. Como alternativa
se conserva `python manage.py createsuperuser` para administración de plataforma.
El superuser existente puede crear institución y usuarios desde la nueva UI.

`bootstrap_institution` reutiliza el código sin sobrescribir metadata existente.
`assign_legacy_institution` lista IDs de pacientes/perfiles sin institución,
verifica colisiones y coherencia de series, no cambia identificadores, namespace,
media ni autores, y es idempotente. Opera sobre **todos** los pacientes/perfiles
no asignados; requiere revisar ese alcance, no deduce que una imagen pertenezca a
LASAID por su nombre. Después de aprobación explícita del investigador:

```bash
python manage.py assign_legacy_institution --institution LASAID --confirm-all-unassigned
```

**No se ejecutaron el bootstrap real, la creación real de admin ni la asignación
real o dry-run de ownership en este sprint.** Hasta dicha decisión, sólo el
superuser puede consultar los datos legacy. No hay una institución inventada en
la BD para desbloquear artificialmente a un operador.

Commands de carga posteriores deben especificar la institución revisada:

```bash
python manage.py import_imagej_dataset --institution LASAID --source <ruta> --patients-file <xlsx> --dataset-key <clave> --patient-namespace <origen> --dry-run
python manage.py seed_demo_data --institution LASAID
python manage.py seed_optika_40x_calibration --institution LASAID
```

No ejecutar un seed sobre legacy sin resolver antes ownership: no reemplaza
silenciosamente el perfil OPTIKA existente. Mantener los datos reales y backups
fuera del control de versiones.

## Validación y revisión visual

- Backend completo: **372 tests PASS** (345 previos + 27 nuevas pruebas).
- Incluye calibración (29), Characterization, normalización, revisiones/effective,
  Registro, Acquisition e ImageJ. Fixtures previos ahora usan identidad de
  plataforma explícita en DB de tests; los tests de seguridad usan APIClient
  original con roles/tenants separados. No se deshabilitan permisos para hacer
  pasar las regresiones.
- Auth/seguridad: 24 tests con subcasos matrix/list/detail/actions/FK, sesiones y
  CSRF reales, inactive/no-profile, password validators, último ADMIN, autoría,
  aislamiento de media, constraints y commands. Tres pruebas nuevas ImageJ para
  institución requerida, claves por tenant y reimport de claves legacy.
- Vue: Registro **40**, Acquisition **18**, Segmentación/editor **59**,
  Characterization 2.1 **22**, Characterization 2.2 **15**, Auth/admin/guards **11**.
- `npm run build`: PASS. No dependencias añadidas ni requirements modificados.
- Django `check`: PASS; `makemigrations --check --dry-run`: No changes detected.
- `git diff --check`: PASS. Sin stage, commit ni push.
- `pip check` del entorno sicam: No broken requirements found. La caché de pip
  quedó deshabilitada por permisos del sandbox; no se instaló ni cambió nada.

La antigua prueba de upload anónimo se actualizó para exigir rechazo: es un cambio
intencional del contrato de acceso, no una regresión científica. La prueba de
Basic aislado se sustituyó por sesión compartida. SSR y tests de render verifican
la UI; no hay Chromium/Chrome disponible en este entorno. Revisión humana:

- [ ] Login con cuenta existente y logout efectivo.
- [ ] Crear institución y ADMIN mediante procedimiento revisado.
- [ ] Crear OPERATOR/REVIEWER ficticios autorizados para aceptación operativa.
- [ ] Cambio obligatorio de contraseña antes del workspace.
- [ ] ADMIN gestiona sólo su institución; no asigna superuser ni elimina usuarios.
- [ ] OPERATOR registra datos/series y guarda borrador; no valida.
- [ ] REVIEWER consulta Registro, edita y valida; no registra infraestructura.
- [ ] Header identifica usuario/tenant; guards conservan trabajo pendiente.
- [ ] Imágenes privadas cargan desde 127.0.0.1:5173 con sesión válida.
- [ ] Decidir asignación legacy antes de exponerlo a cuentas institucionales.

No se automatizaron acciones persistentes de aceptación visual ni se crearon
cuentas reales para simular esta revisión.

## Pendientes y contrato 18T-B

Se conservan:
`IMPORTANT_PENDING_18S_A2`, `HISTORICAL_ACQUISITION_ASSOCIATION`,
`RETIRED_RECALCULATION_POLICY`, `DURABLE_UPLOAD_IDEMPOTENCY`,
`GLCM_PHYSICAL_DISTANCE_NORMALIZATION`, `MANUAL_VISUAL_REVIEW_18S_D`.

Nuevos: `MULTI_INSTITUTION_USER_MEMBERSHIP = FUTURE_EXTENSION`,
`PASSWORD_RESET_EMAIL = FUTURE_DEPLOYMENT_FEATURE`,
`PRODUCTION_MEDIA_ACCESS_CONTROL = DEPLOYMENT_ACTION_REQUIRED` y revisión humana
operativa 18T-A. Una futura Membership podrá sustituir la afiliación OneToOne;
no se implementa ahora.

18T-B puede utilizar request.user, role/profile, institución del recurso,
created_by/updated_by, la política central y el scoping para evaluar dependencias,
archive/restore/retire, hard-delete seguro y motivos/deleted_by. Debe definir la
semántica antes de habilitar DELETE institucional, bloquear mutación de recursos
validados y contemplar compensación de storage. No asumir que autor implica
ownership ni que updated_by constituye un AuditLog. 18T-A no implementa lifecycle,
no elimina cuentas ni recursos y no cambia las reglas científicas.

## Archivos y alcance de cambios

Backend: nuevos `access_models.py`, `access.py`, `auth_views.py`, migración 0011,
commands de bootstrap/legacy/admin, tests de seguridad; integración en modelos,
serializers, views, settings/urls/admin, commands/importador y propagación de actor
en servicios. El motor de segmentación, fórmulas de Characterization y motor de
calibración permanecen intactos. Tests de regresión adaptan fixtures autenticados.

Frontend: `AuthGate.vue`, estado `services/auth.js`, `AdministrationView.vue`,
`InstitutionSelect.vue`; integración en App/TopBar/Registro/Acquisition, visibilidad
de Validar en MainContent, cliente CSRF, reemplazo del login Basic local y tests.
No cambian dibujo, selección, undo/redo, IDs ni lógica de effective.

Único documento nuevo del sprint: este archivo `docs/86`. Estado final:
41 archivos tracked modificados y 16 archivos nuevos untracked, ninguno staged.
`git diff --stat`: 41 files changed, 321 insertions(+), 196 deletions(-); Git no
incluye los 16 archivos nuevos en ese stat hasta que se agreguen. HEAD permanece
`0a8e3e32db0e641af4d0772a5c2393a1a6963a6d`. No se hizo commit ni push.

**SPRINT 18T-A = READY_WITH_MEDIA_DEPLOYMENT_ACTION_PENDING**
