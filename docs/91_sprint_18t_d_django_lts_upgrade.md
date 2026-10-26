# Sprint 18T-D — Upgrade controlado a Django 5.2 LTS

Estado final (2026-10-26): **READY_FOR_DEPLOYMENT_BASELINE**.
Regresión integral cerrada en 18T-D.B; infraestructura productiva pendiente.

## 18T-D.A — CONTROLLED UPGRADE

Fecha: 2026-10-26, America/Mexico_City.
Estado histórico al concluir fase A: **READY_FOR_FULL_REGRESSION**.
La regresión completa y el cierre posterior se documentan en 18T-D.B, al final.

### Precheck y dependencias

Rama `master`, HEAD `bac40bdd33c44aebd01449d6ac1e060aa82196b1` (`Update data lifecycle
acceptance record`), working tree inicialmente limpio y `git diff --check` PASS.
18T-C y la repetición documentada de 18T-B.1 ya estaban commiteados. No se repitió
18T-B.1 ni se crearon objetos lifecycle en la BD real.

- Python **3.10.20 → 3.10.20**; pip 26.2.1.
- Django **5.0.1 → 5.2.18** en `/home/israel/miniconda3/envs/sicam`.
- `DEPENDENCY_SOURCE_OF_TRUTH = apps/web/Backend/requirements.txt`.
- `DJANGO_TARGET = 5.2.18`, anunciado antes de modificar dependencias.
- Selección: última versión estable 5.2.x publicada por la fuente configurada
  consultada (`pypi.org`); rama LTS compatible con Python 3.10, sin prereleases,
  Django 6.x ni cambio de Python.
- Cambio de pin único: `Django==5.2.18`. No hay lockfile/pyproject/Conda YAML ni
  Dockerfile alternativo del backend que controle su instalación. Los manifests
  de microservicios son independientes; las guías de instalación remiten al
  requirements del backend. Las menciones de 5.0.1 en auditorías anteriores son
  contexto histórico, no una segunda fuente de pins.
- Instalación exacta: `python -m pip install --no-cache-dir
  --disable-pip-version-check 'Django==5.2.18'`, desde el Python de `sicam`.
  La consulta/instalación requirió acceso de red fuera del sandbox; la primera
  consulta restringida falló por DNS, la posterior completó correctamente.
- `pip check` antes/después: **No broken requirements found**.
- Comparación completa de `pip freeze`: eliminado sólo `Django==5.0.1`, agregado
  sólo `Django==5.2.18`. **Paquetes adicionales actualizados: ninguno**.

| Dependencia auditada | Versión instalada, sin cambios | Restricción relevante |
|---|---|---|
| djangorestframework | 3.14.0 | Django >=3.0, sin límite superior declarado |
| django-cors-headers | 4.3.1 | Django >=3.2; asgiref >=3.6 |
| django-environ | 0.12.0 | Configuración de entorno conservada |
| Pillow | 10.2.0 | Sin restricción Django |
| psycopg2-binary | 2.9.9 | Driver declarado/instalado; BD actual SQLite |
| django-extensions | 3.2.3 | Sin cambio; no forma parte de INSTALLED_APPS actual |
| pytest / pytest-django / pytest-cov | 7.4.4 / 4.7.0 / 4.1.0 | Compatibilidad comprobada con los tests dirigidos |
| asgiref / sqlparse | 3.12.1 / 0.6.0 | Satisfacen >=3.8.1 / >=0.3.1 exigidos por Django nuevo |
| Gunicorn / WhiteNoise | No instalados | Decisión WSGI pendiente, no se añadieron |

SQLite efectivo: 3.53.4. No se probó un servidor PostgreSQL ni se cambió de motor.
Auth/session siguen siendo los módulos nativos Django y SessionAuthentication;
no JWT ni nuevas dependencias. Lectura ImageJ existente no depende de openpyxl
instalado; no se añadió un paquete Excel en este sprint.

Fuentes oficiales consultadas:
[Django 5.2 y Python](https://docs.djangoproject.com/en/5.2/releases/5.2/),
[cambios de 5.1](https://docs.djangoproject.com/en/5.2/releases/5.1/),
[parche 5.2.18](https://docs.djangoproject.com/en/5.2/releases/5.2.18/).
El índice consultado se conserva en `/tmp/sicam18tda/django_index.txt`.

### Riesgos de compatibilidad, cambios y warnings

`COMPATIBILITY_RISKS_FOUND` antes de editar: DRF 3.14 y demás integraciones con
Django sin soporte 5.2 deducible sólo de sus límites de versiones; declaraciones
`CheckConstraint(check=...)` deprecadas; rutas, sesiones/CSRF, FileField/storage,
serialización, restricciones y permisos requerían comprobación dirigida.
La búsqueda no encontró uso aplicativo de `DEFAULT_FILE_STORAGE`,
`STATICFILES_STORAGE`, `get_storage_class`, `timezone.utc`, `is_dst`, `ugettext`,
`force_text`, `USE_L10N` o `index_together` que exigiera adaptación.
No se añadió LoginRequiredMiddleware ni se alteró el orden del middleware.

**Correcciones productivas necesarias: ninguna** en las verificaciones de fase A.
No se cambiaron modelos, restricciones, migraciones, cálculos científicos, API ni
políticas de seguridad. Se añadió únicamente una prueba en `api/test_access.py`:
sesión auténtica mediante login, CSRF requerido para PATCH/lifecycle, POST válido,
archivo/restauración válidos y rechazo de acceso a otra institución. Esta prueba
usa Django TestCase y BD aislada, no sesiones/usuarios reales.

| Hallazgo | Clasificación | Decisión |
|---|---|---|
| 36 `RemovedInDjango60Warning` por `CheckConstraint.check` | SAFE_TO_DEFER | 18 declaraciones actuales y 18 en migraciones históricas; todavía admitidas en Django 5.2. Planificar `condition=` antes de 6.x; no reescribir historia ni suprimir warnings en esta fase |
| Deprecaciones atribuibles a terceros en tests dirigidos | THIRD_PARTY: ninguna observada | Mantener pins; esto no certifica todas las combinaciones fuera del alcance |
| APIs eliminadas sin uso en aplicación | NOT_APPLICABLE | Sin refactor preventivo |
| Advertencia de caché pip no escribible en sandbox | SAFE_TO_DEFER, operativa | Instalar con `--no-cache-dir`; no cambiar permisos de HOME |
| Errores/deprecaciones que obligaran corrección | FIXED: ninguno | No se detectó fallo de compatibilidad que exigiera parche |

No se suprimieron warnings globalmente. Los 36 avisos no son violaciones de
constraints ni cambios de geometría; quedan explícitos para mantenimiento futuro.

### Backup y baseline real

BD resuelta por settings:
`/home/israel/repos/sicam-refactor/apps/web/Backend/db.sqlite3`.
MEDIA_ROOT: `/home/israel/repos/sicam-refactor/apps/web/Backend/media`.

Backup previo: `/tmp/sicam18tda_backup_20261026T191449Z/database/db.sqlite3`.
SHA-256: `6df5c618c3b661fa9365d4263256661237df88605ab6cf16d0a3687b0ee7e4f1`.

Copia consistente SQLite desde conexión read-only, legible, con integrity_check
`ok` y foreign_key_check sin infracciones. El directorio incluye `manifest.json`,
`media_hashes.json`, `pip_before.txt`, versiones Python/Django y conteos/hashes de
filas. El manifiesto de media no es una copia de sus archivos; no se copiaron ni
modificaron imágenes. Restauración sólo coordinada, deteniendo escrituras y
verificando integridad; no se restauró nada durante este sprint.

| Modelo / estado | Antes | Después |
|---|---:|---:|
| `api_institution` | 1 | 1 |
| `auth_user` | 4 | 4 |
| `api_paciente` | 10 | 10 |
| `api_caso` | 10 | 10 |
| `api_analisispred` | 10 | 10 |
| `api_muestrasaliva` | 67 | 67 |
| `api_muestrasangre` | 2 | 2 |
| `api_acquisitionseries` | 4 | 4 |
| `api_acquisitionprofile` | 3 | 3 |
| `api_calibration` | 3 | 3 |
| `api_calibrationreference` | 3 | 3 |
| `api_resultadosegmentacion` | 30 | 30 |
| `api_revisionsegmentacion` | 27 | 27 |
| `api_resultadocaracterizacion` | 25 | 25 |
| `api_lifecycleevent` | 53 | 53 |
| `django_session` | 1 | 1 |
| Characterization 2.0 / 2.1 / 2.2 | 2 / 21 / 2 | 2 / 21 / 2 |
| Media files | 95 | 95 |

La comparación de todas las tablas por PK/hash de fila completa resulta idéntica,
incluidos usuarios, sesiones, eventos y las muestras TEST preexistentes. El
manifiesto final conserva exactamente las rutas, tamaños y SHA-256 de 95 archivos.
No hubo imports reales, nuevas calibraciones, segmentaciones ni Characterization
sobre la BD de trabajo. **LifecycleEvents: 53 → 53**.

### Invariantes científicos reales, comprobados read-only

Characterization 24: versión **2.2**, sample **66**, estado físico
**COMPATIBLE_PROVISIONAL**. Toda su fila/JSON, características, snapshot de
calibración, sx/sy, fingerprint y hash efectivo permanecen idénticos.
Fingerprint persistido:
`c80144bf271ed7e977040a69a288a14c44efc4eb93f311a07b95d320c0526b1e`.

Hash canónico de fila Characterization 24: `a3ccc0b3015d9ae60e27fa7654520866c3d5c6dd45a1d49a5096a313ce28055f`.

Hash del effective resuelto: `3f76cddd320f5c7d4d473f390fac963312121595f62e0987424f8b042daa184f`.

Los hashes de esta auditoría usan SHA-256 de JSON ordenado, separadores compactos
y conversión determinista de datetime/Decimal a texto; no se confunden con el
fingerprint persistido de Characterization.

Calibration `CAL-OPTIKA-40X-PROVISIONAL-001`: **PROVISIONAL**, sx
`0.055233934048000`, sy `0.055010060892000`; profile, provenance y todos sus campos
intactos. El snapshot completo está en la evidencia local, sin divulgar datos
clínicos. No hubo recálculo ni eventos aplicados a ella.

### Migraciones y configuración de seguridad

- `python manage.py check`: PASS, sin incidencias.
- `showmigrations`: todas aplicadas, API 0001–0013 incluidas.
- `makemigrations --check --dry-run`: **No changes detected**.
- `migrate --plan`: **No planned migration operations**.
- Migraciones aplicadas: **ninguna**, ni internas de Django ni propias.

Producción ensayada con secret aleatorio temporal no registrado, host
`app.example.invalid`, origen HTTPS y DEBUG=False. Se conservaron defaults:
SESSION/CSRF secure=True, SameSite=Lax, SSL redirect=True, DENY, nosniff,
Referrer-Policy=same-origin. Proxy confiable explícito produce
`('HTTP_X_FORWARDED_PROTO','https')`; sin opt-in permanece None, cubierto en tests.
HSTS=60, includeSubDomains/preload=False. Configuración de desarrollo y variables
legacy se probaron sin editar `.env` real. Secrets inválidos, DEBUG productivo,
hosts wildcard y orígenes inseguros se rechazan mediante tests de configuración.

`check --deploy` devuelve exclusivamente:

| Código | Clasificación vs. 18T-C | Motivo |
|---|---|---|
| security.W005 | EXISTING_EXPECTED | includeSubDomains requiere decisión de despliegue |
| security.W021 | EXISTING_EXPECTED | preload requiere decisión de despliegue |
| Nuevos warnings de seguridad | NEW_WARNING: ninguno | Sin política relajada |
| Warnings desaparecidos | RESOLVED: ninguno | Mismo baseline de avisos |

No se instaló/configuró Nginx. Contrato X-Accel comprobado con settings de test,
media privada Django comprobada en ambos modos con fixtures aislados.

### Pruebas dirigidas: 206 passed

Comando ejecutado: `python -m pytest -q -p no:cacheprovider -W default
--junitxml=/tmp/sicam18tda/targeted.xml` seguido de la selección explícita guardada
en `targeted_nodes.txt`. **No es la suite backend completa**.

| Grupo | Passed | Evidencia cubierta |
|---|---:|---|
| AccessTests + SessionTests | 25 | ADMIN/OPERATOR/REVIEWER/SUPERUSER, institución, FK spoofing, login/logout/me/password, inactivos, último ADMIN, autores, CSRF POST/PATCH/lifecycle |
| ProductionPolicyTests | 5 | Configuración dev/prod, secretos, cookies, proxy, logging sin exposición |
| LifecycleTests | 28 | Inspector, delete/archive/restore/retire, eventos, roles, cross-tenant, recheck/rollback, historial protegido |
| AdministrativeAuditTests | 17 | Eventos read-only, filtros/paginación/target eliminado, archivados, diagnóstico, permisos, admin, X-Accel, media de todos los tipos |
| RegistrationTests + PseudonymizedRegistrationTests | 18 | IDENTIFIED/PSEUDONYMIZED, DOB, atomicidad caso/análisis, relaciones y muestras |
| AcquisitionTests + selección AcquisitionOperationsTests | 35 | Profile, Calibration/Reference/Series, estado, resolución, compatibilidad, carga y pertenencia |
| Calibration engine + review | 29 | Geometría, determinismo, escalas, ambigüedad, consenso e invariantes numéricos; fixtures sintéticos |
| Characterization 2.1 | 12 | Intensidad, GLCM, std, eccentricity, equivalencia y regresión |
| Characterization 2.2 | 22 | Área/perímetro/centroides/distancia MN, unidades físicas, snapshot, fingerprint, idempotencia, estados, pixel-only |
| Selección RevisionSegmentacionTests | 7 | Base efectiva, BORRADOR no efectivo, VALIDADA, inmutabilidad y preservación |
| Selección ImageJImportTests | 8 | Institución obligatoria, identidad pseudonimizada, matching, idempotencia, máscaras, REAL_HOLE, guard manual |

El nuevo test de sesión comprueba tanto ausencia como token inválido antes de
admitir PATCH/lifecycle con token válido. Las suites restantes cubren media
anónima denegada, otra institución denegada, autorizada admitida, histórico y
`/media/` no público. No se usaron cuentas reales ni force_authenticate para el
nuevo test de sesión.

Smokes adicionales: imports/registro admin PASS; FileSystemStorage save/open/delete
sólo en `/tmp` PASS; FileField/media/reference mediante tests aislados PASS.
`collectstatic --noinput` con STATIC_ROOT temporal: **162 archivos** en
`/tmp/sicam18tda/static`, sin archivos generados versionados.

### Cambios, evidencia y siguiente fase

Archivos de esta fase:

- `apps/web/Backend/requirements.txt`: pin Django exacto.
- `apps/web/Backend/api/test_access.py`: cobertura de sesión/CSRF y tenant.
- `docs/91_sprint_18t_d_django_lts_upgrade.md`: este informe.
- `docs/deployment_production.md`: versión, instalación y gate de regresión.

Evidencia local: `/tmp/sicam18tda/` (before/after JSON, pip freezes, índice,
instalación, auditoría de dependencias, snapshot/backup, selección de tests,
JUnit y warnings, checks/migrations, collectstatic, seguridad/storage e integridad).
`/tmp` es temporal; la documentación conserva los resultados esenciales.

`git diff --check`: PASS. No cambios de modelos/migraciones, frontend ni algoritmos.
Sin commit ni push. No se ejecutó frontend, build ni regresión completa. No se
reiniciaron servicios existentes; reiniciarlos al adoptar el nuevo entorno, pues
pueden mantener Django anterior en memoria.

Próximo paso recomendado: **18T-D.B**, regresión completa backend/frontend/build y
aceptación operativa correspondiente, sin repetir lifecycle real por defecto.
No se certifica producción ni compatibilidad universal de DRF/terceros por pasar
la selección. No se resuelven incidentalmente IMPORTANT_PENDING_18S_A2, normalización
GLCM física, asociación histórica, política RETIRED, idempotencia durable de upload,
revisión visual, infraestructura/media, rate limiting o demás pendientes previos.
Deprecaciones CheckConstraint siguen planificadas antes de Django 6; no bloquean
la regresión con el target 5.2 LTS fijado.

SPRINT 18T-D.A = READY_FOR_FULL_REGRESSION


## 18T-D.B — FULL REGRESSION

Fecha: 2026-10-26, America/Mexico_City.
Resultado: **READY_FOR_DEPLOYMENT_BASELINE**.

### Precheck y alcance

Rama `master`; HEAD `bac40bdd33c44aebd01449d6ac1e060aa82196b1`.
Estado inicial esperado y confirmado:

```text
 M apps/web/Backend/api/test_access.py
 M apps/web/Backend/requirements.txt
 M docs/deployment_production.md
?? docs/91_sprint_18t_d_django_lts_upgrade.md
```

Diff inspeccionado: únicamente el pin de Django, la prueba de sesión/CSRF,
la guía de despliegue y este informe, todos de fase A. Sin cambios ajenos;
`git diff --check` PASS. Se preservó todo el trabajo anterior sin staging.
La comparación read-only inicial coincidió con el baseline previo al upgrade.

No se reinstalaron paquetes ni se repitió la selección de 206 tests como comando
separado. Cada suite completa se ejecutó **una sola vez**. Los tests dirigidos
que forman parte de la suite completa naturalmente quedan cubiertos por ella.
No hubo fallos que requirieran diagnóstico, correcciones o repeticiones.

### Regresión integral

| Validación | Resultado |
|---|---|
| Backend completo | **448 passed, 0 failed, 2 skipped**, 24.74 s |
| Frontend completo | **187 passed, 0 failed**, ocho archivos de tests |
| Segmentación/editor | **59 passed**, incluidos en frontend; no se repitieron |
| `npm run build` | PASS, 128 módulos, 1.08 s |
| `manage.py check` | Sin incidencias |
| `makemigrations --check --dry-run` | No changes detected |
| `pip check` inicial/final | No broken requirements found |
| `check --deploy` | Sólo security.W005 y security.W021 preexistentes |

Backend desde `apps/web/Backend`, Python de `sicam`:

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider -W default \
  --junitxml=/tmp/sicam18tdb/backend.xml
```

El incremento de 447 a 448 aprobados respecto al baseline se debe a la prueba
session/CSRF añadida en fase A. No se añadieron tests en fase B. Los dos skipped
son `test_real_segmentation_saliva` y `test_real_segmentation_blood`, que
requieren servicios reales ejecutándose. No se iniciaron esos servicios; no son
fallos ocultados ni skips añadidos por esta fase.

Frontend desde `apps/web/Frontend`, Node **24.17.0**. `package.json` no tiene un
script `test`; se utilizó el procedimiento establecido, ejecutando una vez cada
`tests/*.test.mjs` con Node y deteniéndose ante cualquier exit code no cero:

```bash
for testfile in tests/*.test.mjs; do
  name=$(basename "$testfile" .test.mjs)
  node "$testfile" > "/tmp/sicam18tdb/frontend_${name}.log" 2>&1 || exit $?
done
npm run build
```

| Suite frontend | Passed |
|---|---:|
| acquisition | 19 |
| adminAudit | 9 |
| auth | 12 |
| characterization21 | 22 |
| characterization22 | 15 |
| lifecycle | 11 |
| registration | 40 |
| segmentationStrategies (incluye editor y navegación) | 59 |
| Total | **187** |

Editor incluye modos/contexto, dibujo, IDs, undo/redo, guardado, navegación y
BORRADOR/effective. No existe una suite de editor adicional excluida del comando.
No npm update, audit fix, cambio de lockfile ni actualización frontend.
`collectstatic` no se repitió: ya pasó en fase A y nada relacionado cambió.

### Deploy y deprecaciones

Se reutilizó el método de fase A: DJANGO_ENV=production, secret aleatorio temporal
no expuesto, DEBUG=False, host `app.example.invalid`, CSRF HTTPS, CORS vacío y
proxy confiable explícito. No se configuró infraestructura real.

- `security.W005`: **EXISTING_EXPECTED**, includeSubDomains pendiente de verificar
  todos los subdominios. No se habilitó prematuramente.
- `security.W021`: **EXISTING_EXPECTED**, preload requiere decisión explícita.
- **NEW_WARNING = 0**; no warnings nuevos de seguridad sin explicación.
- Se mantienen exactamente **36** avisos `CheckConstraint.check` (18 modelos,
  18 migraciones históricas), todos con recomendación `.condition`.
  Clasificación: **DEFERRED_DJANGO_5_2_DEPRECATION**.
- Pendiente **DJANGO_CHECKCONSTRAINT_CONDITION_MIGRATION**: adaptar `check=` a
  `condition=` y comprobar estado/migraciones antes de un futuro upgrade mayor.
  No se refactorizaron modelos ni se suprimieron avisos globalmente.

No se generaron ni aplicaron migraciones; el plan de fase A ya era vacío.
No hubo cambios de configuración o código productivo en fase B.

### Integridad real final

Se reutilizó `/tmp/sicam18tda/before.json`, capturado antes del upgrade, y su
script de snapshot **en modo de comparación read-only**. La comprobación final
incluye todas las filas de todas las tablas por PK/hash, no sólo los conteos.
No se recalcularon resultados científicos.

| Invariante | Resultado |
|---|---|
| SQLite integrity_check | `ok` |
| SQLite foreign_key_check | Sin infracciones |
| Todas las filas/PK y conteos vs. fase A | Idénticos |
| LifecycleEvents reales | **53 → 53** |
| Media | **95 → 95**, mismas rutas, tamaños y SHA-256 |
| Characterization 24 | Fila y JSON completos idénticos |
| Calibración real y referencias | Todas las filas idénticas |
| Sesiones, usuarios, datos TEST anteriores | Idénticos |

Characterization 24 mantiene sample **66**, versión **2.2**,
**COMPATIBLE_PROVISIONAL**, sx **0.055233934048**, sy **0.055010060892**,
snapshot, hash de segmentación efectiva, fingerprint y features idénticos a los
registrados en fase A. No se ejecutó Characterization sobre esta muestra.

`CAL-OPTIKA-40X-PROVISIONAL-001` mantiene **PROVISIONAL**, profile, escalas,
provenance y referencias íntegros. Al permanecer todas las filas LifecycleEvent
idénticas, no se añadió ningún evento a ella ni a ningún objeto real.

No se ejecutaron CURRENT/ALT reales, imports ImageJ reales, creación de revisiones
reales ni 18T-B.1. Las pruebas trabajan con datos aislados; el build no alteró media.
Los conteos detallados permanecen exactamente como en la tabla de fase A.

### Dependencias finales y archivos

| Dependencia | Antes de 18T-D | Final |
|---|---|---|
| Python | 3.10.20 | **3.10.20** |
| Django | 5.0.1 | **5.2.18** |
| djangorestframework | 3.14.0 | **3.14.0** |
| Pillow | 10.2.0 | **10.2.0** |

Comparación completa de pip freeze: **únicamente cambió Django**. Requirements
mantiene `Django==5.2.18`. No nuevas instalaciones ni fixes en fase B.

En esta fase se actualizó **sólo docs/91**. `requirements.txt`, `test_access.py`
y `docs/deployment_production.md` conservan hash idéntico al inicio de fase B.
La guía de despliegue queda como se aprobó en fase A: sus indicaciones sobre
completar la regresión se satisfacen con este informe; no se modificó al no haber
corrección técnica necesaria.

Estado Git final esperado: los mismos cuatro archivos de 18T-D listados al inicio,
ningún cambio ajeno. `git diff --check` PASS. `git diff --stat` de archivos tracked:
3 archivos, 70 inserciones, 14 eliminaciones; docs/91 continúa untracked y por ello
no figura en ese stat hasta que se añada, acción no realizada aquí.
Sin git add, commit ni push.

Evidencia: `/tmp/sicam18tdb/` contiene backend.log/xml, los ocho logs frontend,
build.log, check.log, makemigrations.log, pip_check.log, deploy.log,
pip_final.txt, versions.json, pre_integrity.log, integrity_final.log y hashes de
archivos de fase A. Snapshots de comparación `phase_b_pre.json` y
`phase_b_final.json` permanecen en `/tmp/sicam18tda/`. Artefactos temporales,
no una política de backup durable. Backup previo documentado en fase A.

### Pendientes preservados y conclusión

- IMPORTANT_PENDING_18S_A2
- HISTORICAL_ACQUISITION_ASSOCIATION
- RETIRED_RECALCULATION_POLICY
- DURABLE_UPLOAD_IDEMPOTENCY
- GLCM_PHYSICAL_DISTANCE_NORMALIZATION
- MANUAL_VISUAL_REVIEW_18S_D
- PRODUCTION_MEDIA_ACCESS_CONTROL
- MULTI_INSTITUTION_USER_MEMBERSHIP
- PASSWORD_RESET_EMAIL
- ARCHIVED_DATA_RETENTION_POLICY
- ORPHAN_MEDIA_CLEANUP
- LOGIN_RATE_LIMITING
- SQLITE_PRODUCTION_SCALABILITY
- WSGI_PRODUCTION_SERVER
- DJANGO_CHECKCONSTRAINT_CONDITION_MIGRATION

Los demás pendientes previos tampoco se resuelven incidentalmente.

```text
APPLICATION_FRAMEWORK_BASELINE = READY
DJANGO_LTS_BASELINE = READY
REAL_PRODUCTION_INFRASTRUCTURE = PENDING
```

Próximo paso: revisar el diff de 18T-D y preparar una aceptación de despliegue
separada con Nginx, HTTPS, servidor WSGI, media protegida en infraestructura,
backups durables/restauración y validación de staging. No se considera listo un
servidor productivo por pasar estas pruebas. Reiniciar Django al adoptar el entorno
actualizado para no mantener módulos antiguos en procesos ya iniciados.

SPRINT 18T-D = READY_FOR_DEPLOYMENT_BASELINE
