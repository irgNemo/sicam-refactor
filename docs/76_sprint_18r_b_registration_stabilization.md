# Sprint 18R-B — Estabilización funcional de Registro

## Baseline y alcance

- Rama inicial: `master`.
- HEAD inicial: `6c7ab93f1db206ff2b7abbb8266c30272194900a`.
- Working tree inicialmente limpio.
- Se mantienen las tres pestañas actuales. No se implementa wizard ni rediseño.
- Se conserva Paciente → Caso → AnalisisPred → MuestraSaliva/MuestraSangre.
- No cambian modelos, migraciones, editor, segmentación, effective,
  Characterization ni microservicios.
- Sin staging, commit ni push.

## Precheck y datos reales

`manage.py check` no encontró problemas. `showmigrations api` mostró
0001–0009 aplicadas. SQLite pasó `integrity_check` y `foreign_key_check`.

La auditoría de datos existentes se realizó mediante una conexión SQLite
`mode=ro`, comparando `AnalisisPred.id_paciente_fk` contra el paciente de su caso:

**EXISTING_CROSS_RELATION_INCONSISTENCY_COUNT = 0**.

No se corrigieron ni crearon registros reales. Las únicas operaciones sobre
la BD de trabajo fueron comprobaciones de lectura.

BD: `apps/web/Backend/db.sqlite3`.
Media: `apps/web/Backend/media`.

No se creó un backup de restauración: no se ejecutó ninguna operación que
escribiera datos reales, condición que lo requería en este sprint. Las pruebas
backend utilizaron la BD de test creada/destruida por Django; las nuevas pruebas
de Registro no escriben media. Las pruebas frontend usan adaptadores HTTP
simulados y archivos sintéticos.

Se registraron SHA-256 de la BD y de los 88 archivos de media antes y después:

- `/tmp/sicam18rb_pre_integrity.json`: manifiesto inicial de hashes.
- `/tmp/sicam18rb_final_integrity.json`: comparación e integridad finales.
- BD byte-exacta respecto del inicio: **sí**.
- Inventario y contenido de media sin cambios: **sí**.

Estos manifiestos no son copias de seguridad. Cualquier futura aceptación con
escrituras reales requiere crear y verificar un backup nuevo antes de ejecutarla.

## Problemas de 18R-A y soluciones

| Problema | Solución |
| --- | --- |
| Doble submit Paciente/Caso | Flags de petición y guard en cada handler; fieldset y tabs deshabilitados durante la operación; recuperación en `finally` |
| Upload concurrente | Un lote secuencial, guard `isUploading`; contexto y selección bloqueados durante la subida |
| Hijos obsoletos al cambiar paciente/caso | IDs y listas dependientes se limpian antes de iniciar el GET, incluso si se vacía la selección |
| Respuestas fuera de orden | Contadores de generación separados; un cambio de paciente invalida también la carga de análisis |
| Fallos silenciosos al cargar opciones | Notificación visible, opciones vacías, loading restablecido y botones de reintento |
| Archivos que sobreviven al cambio de contexto | Cambio de paciente/caso/análisis/tipo vacía la selección, libera previews y notifica si había pendientes |
| Caso persistido aunque falle el análisis | Acción backend con `transaction.atomic()` |
| Análisis con paciente/caso distintos | Validación del serializer en POST, PUT y PATCH |
| Reintento de imágenes ya subidas | Estados individuales; sólo PENDING/ERROR entran en el siguiente lote |
| Object URLs retenidas | Revocación al quitar, reemplazar, limpiar, cambiar contexto y desmontar |
| Pérdida inadvertida de formularios | Confirmación en tabs/salida de Registro y aviso nativo `beforeunload` |

## Contrato de la operación transaccional

Nueva acción en `CasoViewSet`:

```http
POST /api/casos/crear-con-analisis/
Content-Type: application/json
```

Payload utilizado por Registro:

```json
{
  "paciente": 123,
  "titulo": "Caso de ejemplo",
  "descripcion": ""
}
```

Se valida/crea Caso mediante `CasoSerializer`. Dentro de la misma transacción
se valida/crea AnalisisPred con:

- `id_paciente_fk`: paciente del caso creado;
- `id_caso_fk`: ID del caso creado;
- `estado`: 0, Abierto.

Respuesta **201**, con los resultados completos de los serializers:

```json
{
  "caso": {"id_caso": 456, "...": "..."},
  "analisis": {"id_analisis": 789, "...": "..."}
}
```

Un error de validación devuelve **400** con errores DRF; si el análisis falla
después de guardar Caso dentro de la transacción, se revierte Caso. No existe
compensación desde frontend mediante borrado.

`POST /api/casos/` permanece disponible y se utiliza cuando
`crear_analisis=false`. `POST /api/analisis/` permanece disponible, ahora con la
validación cruzada. En actualizaciones parciales la validación combina los
valores enviados con los existentes para comprobar la pareja completa.

Registro no envía ni genera `case_number`.

## Estados y feedback frontend

- `isCreatingPatient`, `isCreatingCase`, `isUploading`: bloqueos de doble envío.
- Texto `Registrando...`, `Creando...`, `Subiendo...`; `aria-busy` en fieldsets.
- Lecturas de casos/análisis tienen sus propios estados de carga y error.
- Las respuestas antiguas no modifican listas, flags de carga ni mensajes.
- Los errores DRF 400 de campos conocidos se traducen a etiquetas legibles y
  texto limitado, usando interpolación Vue; no se renderiza HTML ni tracebacks.
  Errores no reconocidos/servidor usan el mensaje genérico.
- No cambia el payload del paciente; no se añade normalización de mayúsculas,
  reglas de fecha ni nuevas modalidades de identidad.
- La notificación cancela su temporizador anterior y no se vuelve a programar
  después del desmontaje.

Tras éxito se conservan localmente:

- `newlyCreatedPatientId`;
- `newlyCreatedCaseId`;
- `newlyCreatedAnalysisId`, o null si se creó sólo Caso.

Se recarga la lista de pacientes y se limpian los formularios exitosos. No se
cambia automáticamente de pestaña.

## Upload y previews

Cada archivo tiene `PENDING`, `UPLOADING`, `SUCCESS` o `ERROR`, con nombre y
estado visibles. El upload mantiene un snapshot del análisis/tipo y ejecuta
una petición por vez. Un fallo individual no oculta los éxitos anteriores ni
impide intentar los otros archivos del lote.

Los archivos SUCCESS permanecen visibles como resultado, pero no son pendientes
ni vuelven a enviarse al reintentar. Se conservan los IDs de muestra devueltos.
Los ERROR pueden reintentarse. Cambiar contexto sólo descarta la selección
local; nunca borra muestras persistidas.

Una imagen que falla al renderizar muestra **Vista previa no disponible** sin
bloquear el upload. No se añadió renderer TIFF ni validación científica.

**DURABLE_UPLOAD_IDEMPOTENCY = NOT_IMPLEMENTED**.

La protección de reintento se limita a éxitos confirmados en esta instancia de
UI. No cubre pérdida de respuesta después de persistencia, recarga, nueva
selección del mismo archivo, otra pestaña o cliente concurrente. No hay hashes,
constraints ni claves idempotentes nuevos. Una respuesta de red ambigua no permite
asegurar que el servidor no guardó el archivo.

## Navegación y dirty state

Hay trabajo sin guardar si existen campos manuales llenos, cambios en Caso,
archivos PENDING/ERROR o una operación de escritura activa.

- Formulario limpio: navegación libre.
- Cambio de pestaña con trabajo pendiente: confirmación; cancelar conserva
  pestaña/datos; confirmar cambia de pestaña conservando los formularios.
- Salir de Registro: `App.vue` consulta `confirmLeave()` mediante ref del
  componente. Es el único cambio de navegación global y no modifica el guard
  de segmentación.
- Durante una escritura se bloquea navegar/limpiar desde la UI.
- Recargar/cerrar: `beforeunload` solicita la advertencia nativa. El navegador
  decide su presentación y puede exigir interacción previa.
- Desmontar: libera previews, quita listener y temporizador e invalida lecturas.

No se implementó persistencia de formularios en sessionStorage.

## Pruebas y validación

Entornos: Python de `sicam`, Node **24.17.0**. Sin instalaciones.

| Comando | Resultado |
| --- | --- |
| `python manage.py test api.test_registration api.test_imagej --noinput` | 31 tests, OK |
| `python manage.py test api --noinput` | 231 tests, OK, incluye las anteriores |
| `node tests/registration.test.mjs` | 18 passed |
| `node tests/segmentationStrategies.test.mjs` | 59 passed |
| `node tests/characterization21.test.mjs` | 22 passed |
| `npm run build` | PASS |
| `python manage.py check` | Sin problemas |
| `python manage.py makemigrations --check --dry-run` | No changes detected |
| SQLite integrity / foreign keys | ok / 0 infracciones |
| Relación paciente–caso en BD real, al terminar | 0 inconsistencias |
| `git diff --check` | PASS |

Los seis tests backend nuevos comprueban éxito atómico, caso inválido, rollback
por análisis rechazado, endpoints existentes, FK cruzada en alta y actualizaciones
parciales/completas. El fallo de análisis se inyecta en su validación, verificando
que Caso ya existe dentro de la transacción y desaparece después del rollback.

Los tests frontend cubren éxito/error, doble envío, IDs devueltos, limpieza
inmediata, respuestas obsoletas, carga fallida/reintento, uploads SALIVA/SANGRE
secuenciales y parciales, reintento selectivo, liberación de URLs y dirty navigation.
La regresión 18Q permanece verde.

No se realizó aceptación visual en navegador ni alta real.

## Decisiones diferidas

- Rediseño visual: **18R-C**.
- Wizard obligatorio: **NO**.
- UI de pacientes pseudonimizados: futuro **18R-D**; se conserva IDENTIFIED.
- Exposición/numeración de `case_number`: pendiente.
- Controles de estado del análisis: pendientes; `cambiar_estado` no se usa aquí.
- **CLOSED_ANALYSIS_UPLOAD_POLICY = PENDING_DECISION**; se conserva la posibilidad
  de seleccionar análisis Cerrado y se muestra su estado.
- **FUTURE_BIRTH_DATE_VALIDATION = PENDING_PRODUCT_DECISION**.
- **DURABLE_UPLOAD_IDEMPOTENCY = NOT_IMPLEMENTED**.
- **CASE_WITHOUT_ANALYSIS_UI_DEBT**: crear Caso sin análisis se mantiene; añadir
  después un análisis desde Registro requiere una decisión posterior.

## Archivos

- `apps/web/Backend/api/serializers.py`
- `apps/web/Backend/api/views.py`
- `apps/web/Backend/api/test_registration.py`
- `apps/web/Frontend/src/views/RegistroView.vue`
- `apps/web/Frontend/src/App.vue`
- `apps/web/Frontend/src/services/registrationErrors.js`
- `apps/web/Frontend/tests/registration.test.mjs`
- `docs/76_sprint_18r_b_registration_stabilization.md`

**SPRINT 18R-B = PASS WITH DEFERRED PRODUCT DECISIONS**
