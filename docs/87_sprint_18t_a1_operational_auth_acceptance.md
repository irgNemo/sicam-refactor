# Sprint 18T-A.1 — Bootstrap operacional y aceptación de auth

Actualizado: 2026-10-23, America/Mexico_City.

**Estado: READY_FOR_DATA_LIFECYCLE.** Bootstrap, ownership, integridad,
regresiones y aceptación humana de auth completados. El investigador confirmó
login, cambio obligatorio, encabezado, creación/prueba de OPERATOR y REVIEWER,
y logout. La comprobación ORM final confirma los tres roles activos en LASAID,
todos con must_change_password=False. No se implementó 18T-B.

## Precheck y continuidad

- Rama `master`; HEAD `464aebad9ffc10e28f00e43a5d6d99afee85dbe6`,
  `Add institutional users roles and permissions`.
- Inicio de 18T-A.1: working tree limpio, 18T-A commiteado.
- Al reanudar: únicamente este documento untracked, creado por la primera fase.
  No había cambios de código ni modificaciones ajenas.
- El investigador confirmó la creación interactiva correcta del ADMIN. No se
  volvió a crear Institution ni ADMIN. No se solicitó, leyó ni cambió su contraseña.
- Django check PASS, migraciones API 0001–0011 aplicadas;
  `makemigrations --check --dry-run`: No changes detected.

## Commands auditados y bootstrap

Código, help y docs/86 revisados. Desde `apps/web/Backend`, entorno `sicam`:

```bash
python manage.py bootstrap_institution --code LASAID --name LASAID
python manage.py create_sicam_admin
python manage.py assign_legacy_institution --institution LASAID --dry-run
python manage.py assign_legacy_institution --institution LASAID --confirm-all-unassigned
```

La primera fase ejecutó bootstrap dos veces: `CREATED: institution_id=1` y
`ALREADY_EXISTS: institution_id=1`. LASAID está activa, sin duplicados.
El investigador ejecutó `create_sicam_admin` en su terminal.

El procedimiento pide código institucional, username, correo y contraseña temporal
con confirmación oculta. Asigna ADMIN y must_change_password=True automáticamente.
**No solicita nombre/apellido:** se podrán completar desde Administración → Usuarios
tras el cambio obligatorio. No se inventaron argumentos ni datos personales.

ADMIN existente: user ID 2, LASAID ID 1, activo, no superuser;
`must_change_password=false` tras el cambio realizado por el investigador.
Hay además una cuenta de
plataforma histórica intacta. Codex no modificó credenciales; los usuarios y sus
cambios de contraseña fueron gestionados por el investigador mediante el flujo normal.

## Backup e integridad antes de ownership

BD: `/home/israel/repos/sicam-refactor/apps/web/Backend/db.sqlite3`.
MEDIA_ROOT: `/home/israel/repos/sicam-refactor/apps/web/Backend/media`.

Backup de la primera fase:
`/tmp/sicam18ta1_backup_20261023T012415Z/database/db.sqlite3`.
SHA-256: `8348e5c504a347eac447a8b31ab22ced7caecd582ba268d8232611219d46d54d`.

**Backup renovado después de la creación humana del ADMIN y antes de asignar:**
`/tmp/sicam18ta1_backup_20261023T192833Z/database/db.sqlite3`.
SHA-256: `e76d4da5ead28b2acd731fd5e48d7610658772094f87cef86b69347e156324c9`.

Copia consistente mediante SQLite backup API, reabierta y verificada:
`integrity_check=ok`, `foreign_key_check=[]`, conteos/hashes por tabla idénticos.
Incluye `before.json`, `hashes.txt`, `RECOVERY.md`, manifest de los 93 archivos
media con tamaño y SHA-256; permisos de directorio 0700/archivos 0600.
Es backup de BD y manifest de media; no una copia adicional de imágenes.

Restauración sólo con escritores detenidos, comprobando si existen cambios
posteriores del investigador. No se restauró ninguna copia.

## Inventario, dry-run y asignación autorizada

Antes: Paciente IDs 1–8 y AcquisitionProfile ID 1 sin institución. Son los únicos
objetos de dominio con ownership directo pendiente. SicamUserProfile ya tenía
LASAID. Institution única LASAID, perfil OPTIKA 40x, calibración y series del entorno
auditado; sin otro tenant ni relaciones cruzadas. La asignación explícita de todos
los legacy de este entorno a LASAID estaba autorizada por el encargo.

Dry-run ejecutado:

```json
{"institution_id":1,"patient_ids":[1,2,3,4,5,6,7,8],"profile_ids":[1],"dry_run":true}
```

Comparación antes/después del dry-run: todas las tablas y media idénticas.
Después se ejecutó exactamente:

```bash
python manage.py assign_legacy_institution --institution LASAID --confirm-all-unassigned
```

Resultado: 8 pacientes y 1 perfil asignados. Verificación fila por fila contra el
backup: **sólo nueve valores institution_id cambiaron de NULL a 1**. Todos los
otros campos de esas filas y todas las demás tablas permanecieron idénticos.

Se conservaron identificacion, identity_mode, external_patient_id,
external_id_namespace, timestamps y autores. Institution LASAID no sustituye el
namespace externo. No se copiaron imágenes ni se ejecutaron pipelines reales.

## Baseline posterior

| Recurso | Total | Estado |
|---|---:|---|
| Institution | 1 | LASAID activa |
| User | 4 | 1 plataforma histórica + ADMIN/OPERATOR/REVIEWER LASAID |
| SicamUserProfile | 3 | ADMIN 1 / OPERATOR 1 / REVIEWER 1 |
| Paciente | 8 | LASAID; ninguno institution NULL |
| AcquisitionProfile | 1 | OPTIKA 40x, LASAID; ninguno NULL |
| Caso / AnalisisPred | 8 / 8 | LASAID derivada de pacientes |
| MuestraSaliva / MuestraSangre | 65 / 2 | LASAID derivada |
| AcquisitionSeries | 2 | Paciente, profile y calibration coherentes |
| Calibration / CalibrationReference | 1 / 3 | LASAID derivada del perfil |
| ResultadoSegmentacion | 28 | Sin cambios |
| RevisionSegmentacion | 27 | Sin cambios |
| ResultadoCaracterizacion | 24 | Sin cambios |
| ImageJImportRecord / SegmentationExecution | 23 / 27 | Sin cambios |
| Media | 93 | Mismos tamaños y SHA-256 |

Cero ownership directo pendiente en datos activos. Todos los `created_by` y
`updated_by` históricos siguen NULL, sin backfill ficticio. No se asignó la cuenta
de plataforma a una institución ni se le fabricó un perfil operacional.

## Characterization 24 preservada

Misma fila completa y mismo JSON científico antes/después:

- ID 24, muestra 66, versión 2.2.
- sx `0.055233934048`, sy `0.055010060892`.
- physical_status `COMPATIBLE_PROVISIONAL`.
- Calibration 1, `CAL-OPTIKA-40X-PROVISIONAL-001`; profile 1, series 2.
- fingerprint `c80144bf271ed7e977040a69a288a14c44efc4eb93f311a07b95d320c0526b1e`.
- SHA-256 JSON canónico (`sort_keys=True`, `separators=(',', ':')`):
  `357f3cb3848b6fb5f35d9d60f8740ec32526e26a984e4d5b1469763d6491e909`.

No se ejecutó Characterization sobre datos reales. El hash canónico no debe
confundirse con un hash del texto SQLite usando otra serialización.

## Aceptación ejecutada y alcance de la evidencia

**BD de trabajo, lectura:** `/api/auth/me/` anónimo devuelve 200, user NULL y CSRF;
`/api/pacientes/` anónimo devuelve 403 y `/media/` devuelve 404. Consultas mediante
Django APIClient, sin sesión artificial del ADMIN ni cambios persistentes.

**BD de tests y storage temporal:** suites existentes y dos pruebas adicionales
bajo `/tmp/sicam18ta1/operational_acceptance.py`. Credenciales exclusivamente
sintéticas; ningún password del investigador usado o modificado.

| Área | Evidencia automatizada |
|---|---|
| Login/me/logout | Sesiones reales de fixtures vía login con CSRF; logout invalida acceso |
| Cambio obligatorio | Acceso operativo denegado antes del cambio; habilitado después; validadores y CSRF activos |
| Usuarios operativos | ADMIN sintético crea OPERATOR y REVIEWER mediante `/api/users/`, con cambio obligatorio |
| OPERATOR | Crea paciente, caso, análisis, imagen y serie; guarda BORRADOR; Characterization sintética permitida |
| Restricciones OPERATOR | No usuarios, instituciones, validación ni infraestructura ADMIN-only |
| REVIEWER | Consulta, valida revisión preservando objetos, Characterization sintética; no alta de paciente/usuarios |
| ADMIN | Administración de usuarios y permisos de infraestructura; sin elevar superuser, reasignar institución o borrar usuarios |
| Autoría nueva | created_by=OPERATOR; actualización por ADMIN fija updated_by sin cambiar created_by |
| Aislamiento | List/detail/update/FK/actions/compatibility/Characterization/revisions y media entre tenants sintéticos |
| Media | Saliva, sangre, CalibrationReference y TIFF ImageJ: propio 200, otro tenant 404, anónimo 403 |
| Media pública | Rutas físicas `/media/...` devuelven 404 incluso con sesión; respuesta privada usa private,no-store |
| Inactivos | Usuario e institución inactivos no operan/login; reactivar usuario sintético permite login otra vez |
| Último ADMIN | Tests impiden desactivar/degradar último ADMIN institucional; cuenta real nunca puesta en riesgo |
| CSRF | Login/POST/PATCH con token válido; solicitudes sin token rechazadas; no se desactivó CSRF |

Los tests de matriz existentes emplean también force_authenticate para aislar
permisos; las pruebas de sesiones y los dos flujos adicionales usan login normal
con `APIClient(enforce_csrf_checks=True)`.

El investigador creó las cuentas operativas desde su sesión ADMIN y confirmó
que funcionan. No se sustituyó esa aceptación por impersonación ni cambio de
flags mediante scripts. La consulta final confirma:

| user_id | Institución | Rol | Activo | must_change_password |
|---|---|---|---|---|
| 2 | LASAID | ADMIN | Sí | False |
| 3 | LASAID | OPERATOR | Sí | False |
| 4 | LASAID | REVIEWER | Sí | False |

Datos sintéticos: DB de test aislada y TemporaryDirectory destruidos al terminar.
En la BD de trabajo permanecen las dos cuentas operativas de prueba creadas por
el investigador (IDs 3 y 4), activas; no se borraron ni desactivaron sin una decisión
sobre su uso posterior. No hay pacientes, imágenes, revisiones ni instituciones
ficticias nuevos en la BD de trabajo. No se usó DELETE SQL improvisado. La API
actual no ofrece borrado físico de usuarios; su desactivación puede gestionarse
por ADMIN cuando el investigador decida retirar esas cuentas.

## Regresión de esta continuación

- Backend completo: **397 passed, 2 skipped**, 16.03 s.
- Dos pruebas operacionales adicionales: **2 PASS**, DB de test destruida.
- Frontend: **165 PASS**: Registro 40, Acquisition 18, Segmentación/editor 59,
  Characterization 2.1 22, Characterization 2.2 15, Auth/admin/guards 11.
- `npm run build`: PASS, 120 módulos.
- Django check: PASS; makemigrations check: sin cambios; 0001–0011 aplicadas.
- Integridad final: SQLite ok, sin FK huérfanas, 93 media idénticos.

Comandos de regresión (Python del entorno sicam, Node 24.17.0):

```bash
# Backend
python -m pytest -q -p no:cacheprovider
python manage.py check
python manage.py showmigrations api
python manage.py makemigrations --check --dry-run
# Frontend, cada archivo ejecutado directamente
node tests/registration.test.mjs
node tests/acquisition.test.mjs
node tests/segmentationStrategies.test.mjs
node tests/characterization21.test.mjs
node tests/characterization22.test.mjs
node tests/auth.test.mjs
npm run build
```

La invocación inicial `node --test tests/*.test.mjs` sólo reportó seis archivos,
sin enumerar sus casos. No se usó esa salida como evidencia suficiente: se ejecutó
cada archivo directamente y se comprobó el total de 165 casos. No se modificó el
runner ni código para esta aceptación.

Evidencia local en `/tmp/sicam18ta1/`: logs backend/frontend/build/operational,
`post_assignment.json`, scripts de auditoría y pruebas. Los archivos de backup
contienen información privada y no deben versionarse ni compartirse.

## Aceptación humana confirmada

El investigador respondió «Sí funcionan» al checklist de encabezado LASAID/ADMIN,
creación de OPERATOR/REVIEWER mediante Administración, logout y acciones visibles
al entrar con cada rol. No se accedió a cookies ni sesiones del navegador desde
Codex. Esta evidencia es confirmación humana, no automatización visual.

- [x] Login real en `http://127.0.0.1:5173/`.
- [x] Cambio obligatorio completado en ADMIN y ambas cuentas de prueba (ORM).
- [x] Encabezado institucional y roles: confirmado por el investigador.
- [x] Creación de cuentas OPERATOR/REVIEWER y acciones visibles: confirmada.
- [x] Logout: confirmado por el investigador; invalidación de sesión además cubierta por tests.
- [x] IDs de cuentas reales de prueba registrados: 3 y 4.

La respuesta ante credenciales inválidas, el contrato `/api/auth/me/` y el acceso
privado a los distintos tipos de media cuentan con pruebas automatizadas. No se
atribuye a la respuesta humana una inspección explícita de cada endpoint o imagen.

Arranque conocido (no requiere CURRENT, ALT ni BLOOD para login/Registro):

```bash
cd ~/repos/sicam-refactor/apps/web/Backend
conda activate sicam
python manage.py runserver 127.0.0.1:8000

# Otra terminal
cd ~/repos/sicam-refactor/apps/web/Frontend
nvm use 24.17.0
npm run dev -- --host 127.0.0.1 --port 5173
```

Usar `http://127.0.0.1:5173` coherentemente con el hostname del backend.
No se arrancaron servidores adicionales en esta continuación.

## Pendientes y cierre

`PRODUCTION_MEDIA_ACCESS_CONTROL = DEPLOYMENT_ACTION_REQUIRED`: no se modificó
Nginx; producción no puede declararse segura si expone MEDIA_ROOT directamente.
Esto no bloquea el entorno local.

Se conservan:

- IMPORTANT_PENDING_18S_A2
- HISTORICAL_ACQUISITION_ASSOCIATION
- RETIRED_RECALCULATION_POLICY
- DURABLE_UPLOAD_IDEMPOTENCY
- GLCM_PHYSICAL_DISTANCE_NORMALIZATION
- MANUAL_VISUAL_REVIEW_18S_D
- MULTI_INSTITUTION_USER_MEMBERSHIP
- PASSWORD_RESET_EMAIL

La próxima prioridad sigue siendo `DATA_LIFECYCLE_DELETE_ARCHIVE_RESTORE`, tras
esta aceptación de auth. No se implementó 18T-B.

Git al completar ownership: únicamente docs/87 untracked; `git diff --check` PASS.
Ownership ya está asignado; **no repetir bootstrap ni
crear otro ADMIN al continuar**.

## Incidencia de login reportada y corrección acotada

El investigador intentó login desde `http://localhost:5173/` y recibió una página
HTML 403 de Django: `CSRF cookie not set.`. La API local está configurada como
`http://127.0.0.1:8000`. Estos hosts distintos no comparten el mismo sitio para las
cookies; `withCredentials` y el token en un header no sustituyen la cookie exigida
por Django. Se indicó usar **http://127.0.0.1:5173/** para mantener el mismo host.
La comprobación humana estaba pendiente en ese momento; posteriormente el
investigador confirmó que funcionó al usar 127.0.0.1. No se atribuyó el fallo
a una contraseña incorrecta.

Además se corrigió un bug de representación en `AuthGate.vue`: `Object.values`
aplicado a una respuesta HTML la convertía en caracteres separados por espacios.
`authErrorMessage` en `services/auth.js` conserva mensajes JSON estructurados y
devuelve mensajes legibles para HTML/errores de red, sin mostrar el documento del
servidor. Se añadió regresión en `tests/auth.test.mjs`.

Auth/admin/guards: **12 PASS** tras este ajuste (11 previos + 1 nuevo).
No se modificaron backend, CSRF, cookies, credenciales, BD ni ownership para
solucionar el login. No se rebajó SameSite ni se desactivaron controles de seguridad.
Git incluye esos tres archivos frontend y docs/87; sin staging, commit ni push.

El investigador reportó posteriormente el mensaje legible, pero aún sin login
exitoso. Se comprobó el servidor Django **en ejecución**, por HTTP a
`127.0.0.1:8000`, con Origin `http://127.0.0.1:5173`: `/api/auth/me/` respondió
200, Set-Cookie csrftoken (Secure=False, path=/), token presente, CORS para ese
origen y Allow-Credentials=true. Un POST a login con cuerpo vacío, esa cookie y
el token respondió **400 JSON por campos obligatorios**, no 403 CSRF. No se enviaron
credenciales ni se creó una sesión autenticada. Los valores de cookie/token no
se imprimieron ni guardaron en el reporte.

Esta comprobación verificó el servidor y el flujo HTTP con cookie jar. El
investigador confirmó después que el intento fallido seguía usando localhost.
Al cambiar a 127.0.0.1 confirmó login exitoso.

## Continuación después del login humano exitoso

El investigador autorizó continuar. La consulta ORM confirmó ADMIN ID 2, LASAID,
activo, must_change_password=False. Codex no leyó ni modificó contraseñas, cookies
o sesiones autenticadas. No se volvió a crear institución ni ADMIN.

Auditoría posterior en `/tmp/sicam18ta1/post_human_login.json`: todas las tablas
históricas se compararon contra el backup anterior al ownership, admitiendo sólo
las nueve asignaciones institution_id autorizadas. Se excluyeron de la comparación
exacta auth_user, django_session y SicamUserProfile, porque la autenticación humana
cambia legítimamente esas tablas; no se inspeccionó su contenido de credenciales
ni sesiones. Roles y flags operativos se consultaron explícitamente por ORM.

Resultado: datos científicos y autores históricos preservados; Characterization
24 idéntica; media 93/93 con mismos hashes; integrity_check=ok y cero infracciones
FK; Django check y git diff --check PASS. No se repitieron suites sin cambios de
código: siguen vigentes 397 backend + 2 tests operacionales, 165 frontend previos
más la nueva regresión de error de auth (166 en total), y build PASS.

Se pidió completar desde la sesión humana de ADMIN la creación de dos cuentas
claramente identificadas como prueba (OPERATOR y REVIEWER), comprobar encabezado,
acciones visibles y logout, sin compartir credenciales ni crear pacientes o
imágenes reales para esta revisión. El investigador confirmó que estos pasos
funcionan. La consulta final encontró ADMIN 2, OPERATOR 3 y REVIEWER 4 activos,
con cambio obligatorio completado. No se forzó ninguna sesión para sustituirlo.

La auditoría posterior a esa confirmación volvió a pasar: tablas históricas
intactas salvo ownership autorizado, Characterization 24 preservada, 93 media
idénticos, SQLite íntegro y sin infracciones FK. Django check y git diff --check
PASS. Se actualizó `/tmp/sicam18ta1/post_human_login.json` con el estado final.

El pendiente de despliegue Nginx y los pendientes científicos listados permanecen;
este cierre habilita la siguiente fase de desarrollo, no declara producción segura.
Git final: AuthGate.vue, services/auth.js y tests/auth.test.mjs modificados por la
corrección acotada de presentación de errores; docs/87 nuevo. Sin stage, commit,
push ni implementación de 18T-B.

SPRINT 18T-A.1 = READY_FOR_DATA_LIFECYCLE
