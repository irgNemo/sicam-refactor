# Sprint 18R-E — Alta de pacientes pseudonimizados en Registro

## Baseline y alcance

- Rama: `master`.
- HEAD inicial: `2d7e406b290943e22743045e8a53de1ffe05ee90`.
- Working tree inicial limpio; 18R-D commiteado.
- Django check correcto, migraciones api 0001–0009 aplicadas y
  `makemigrations --check --dry-run`: **No changes detected**.
- Sin modificaciones de modelos, migraciones, endpoints ni datos reales.
- Sin staging, commit ni push. No se instalaron dependencias.

## Auditoría de identidad

`Paciente` ya admite IDENTIFIED/PSEUDONYMIZED y contiene los campos de autoridad
externa. Se conservan sus constraints: identificación única, unicidad del par
externo cuando el namespace está presente, autoridad completa y consistencia de
modalidad. La autoridad durable sigue siendo:

```text
(external_id_namespace, external_patient_id)
```

No hay catálogo de instituciones en el flujo actual. El origen se introduce como
texto libre. Se conserva el trim de los campos CharField del serializer y no se
transforman mayúsculas/minúsculas ni ceros iniciales. El importador conserva sus
restricciones propias de CLI para el namespace; no se amplían ni alteran aquí.

## Dos formularios y payloads

| Modalidad | Campos visibles | Payload |
| --- | --- | --- |
| IDENTIFIED, predeterminada | Identificación, fecha de nacimiento, nombre, apellido, email y teléfono | Los mismos seis campos de 18R-D; se mantiene compatible con clientes que omiten `identity_mode` |
| PSEUDONYMIZED | ID hospitalario, fecha de nacimiento, iniciales y origen/institución | `identity_mode=PSEUDONYMIZED`, `external_patient_id`, `fecha_nacimiento`, `initials`, `external_id_namespace` |

IDENTIFIED conserva los cuatro campos obligatorios y contacto opcional.
PSEUDONYMIZED exige sus cuatro campos y no muestra ni envía nombre, apellido,
email, teléfono o identificación técnica. El payload se construye mediante una
lista explícita de campos por modalidad, evitando filtrar valores ocultos.

El backend persiste nombre/apellido vacíos para la nueva alta pseudonimizada;
email/teléfono quedan con sus valores predeterminados del modelo, sin datos
inventados. La API rechaza nombre/apellido no vacíos en esa modalidad.

## Identificación técnica compartida con ImageJ

La fórmula estaba embebida en `services/imagej/importer.py`. Se extrajo, sin
cambiar el algoritmo, a:

```text
api/services/patient_identity.py::pseudonymized_identification
```

La implementación única es:

```python
'ext:' + uuid.uuid5(uuid.NAMESPACE_URL, repr((namespace, external_id))).hex
```

El serializer y el importador llaman al mismo helper. No se usan UUID aleatorios
ni timestamps para la identidad. La fórmula no normaliza entradas por su cuenta.

Fixture de regresión: `('test', '007')` produce exactamente
`ext:e8c598b817db5cd4a9c49cc752763a9e`. Otro namespace con el mismo ID produce
otro identificador. El test de integración comprueba la identidad del helper,
la generación en el preflight del importador y en la API, y una importación
sintética que reutiliza el paciente creado desde Registro. El reimport no duplica
pacientes ni registros ImageJ y el resultado sigue siendo MANUAL.

## Serializer y unicidad

`identificacion` puede omitirse al parsear el payload, pero sigue requerida por
validación condicional en CREATE/PUT de IDENTIFIED. PATCH conserva el valor
existente y rechaza dejar vacíos nombre, apellido o identificación.

En PSEUDONYMIZED la identificación enviada por un cliente se ignora: no puede
sobrescribir la derivación interna. Se genera después de validar la autoridad,
antes de persistir. Un conflicto con una identificación existente se devuelve
como error de validación, sin escribir.

Los duplicados del par externo producen HTTP 400 asociado a
`external_patient_id`:

> Ya existe un paciente con este ID en el origen seleccionado.

Se conservan constraints de BD como última protección. No se añade un mecanismo
nuevo de idempotencia o resolución de carreras entre clientes.

Los campos obligatorios/autoridad incompleta reciben errores por campo. Los
payloads malformados conservan la respuesta de validación DRF. La regla de fecha
futura de 18R-D sigue aplicando en CREATE/PUT/PATCH para ambas identidades.

## UPDATE/PATCH y datos históricos

La API existente permitía editar modalidad y autoridad. Este sprint no introduce
inmutabilidad. Si una petición válida cambia namespace/ID o convierte a
PSEUDONYMIZED, recalcula la identificación mediante el helper común. Conserva las
validaciones de identidad, unicidad, campos prohibidos y fecha.

Si la autoridad/modalidad no cambia, no recalcula identificaciones históricas,
incluso si un paciente antiguo tiene un identificador no canónico. No hay
normalización retrospectiva, migración de datos ni modificación masiva.

**PSEUDONYMIZED_AUTHORITY_MUTABILITY = PENDING_DECISION**.

La UI de este sprint sólo da de alta pacientes. Una política futura de edición
de autoridad debe considerar los registros históricos ImageJ que conservan su
autoridad de importación; no se reescriben esos registros aquí.

## Interacción, dirty state y presentación

- Selector nativo de radios Identificado/Pseudonimizado con legend, labels,
  estado checked, foco visible y wrap usando los estilos de 18R-C.
- Si hay datos exclusivos de la modalidad saliente, `window.confirm` pide
  confirmación antes de limpiar. Cancelar restaura incluso el estado nativo del
  radio; aceptar limpia los campos exclusivos y conserva la fecha común.
- Una fecha sola no exige confirmación, porque se conserva.
- Cambiar modalidad y escribir los nuevos campos cuenta como dirty.
- Limpiar y alta exitosa conservan modalidad y restablecen su baseline dirty.
- Éxito conserva `newlyCreatedPatientId`, refresca pacientes y limpia campos.
  No cambia de pestaña.
- Loading, bloqueo de doble submit, protección de navegación/beforeunload y
  errores inline se mantienen. Los nuevos errores usan labels de usuario.
- Grid de dos columnas, una columna en viewport estrecho; sin rediseño general.

`patientRegistrationLabel()` se añade al helper de presentación y se utiliza
en Nuevo Caso, selector de Imágenes y resumen de destino:

```text
IDENTIFIED:     Nombre Apellido · Identificación
PSEUDONYMIZED:  Iniciales · Namespace / ID hospitalario
```

No muestra el ID técnico pseudonimizado, ni siquiera como fallback. Ante datos
incompletos utiliza las partes disponibles o «Paciente pseudonimizado». Esto es
sólo texto de presentación, nunca un nombre persistido. Los IDs de las opciones
y relaciones enviados al backend no cambian. `patientDisplayName` y
`patientInitials` conservan su comportamiento para las otras pantallas. La API
sigue devolviendo el campo técnico existente; no se rompe el contrato de lectura.

## Pruebas y validaciones

Python del entorno `sicam`, Node **24.17.0**. Escrituras exclusivamente en BD de
test, media temporal y mocks; sin aceptación con pacientes reales.

| Validación | Resultado |
| --- | --- |
| `python manage.py test api.test_registration api.test_imagej --noinput` | **44 tests OK**: 18 Registro y 26 ImageJ |
| `python manage.py test api --noinput` | **244 tests OK** |
| `node tests/registration.test.mjs` | **40 passed** |
| `node tests/segmentationStrategies.test.mjs` | **59 passed** |
| `node tests/characterization21.test.mjs` | **22 passed** |
| `npm run build` | **PASS** |
| `python manage.py check` | Sin problemas |
| `python manage.py makemigrations --check --dry-run` | **No changes detected** |
| SQLite integrity / foreign keys | **ok / 0 infracciones**, antes y después |
| `git diff --check` | **PASS** |

Cobertura añadida: obligatoriedad IDENTIFIED, alta pseudonimizada sin ID técnico,
fórmula histórica fija, duplicados/otros namespaces, trim/case/ceros, campos
ausentes/vacíos/prohibidos, fecha futura, PUT/PATCH coherentes, preservación de
ID histórico, colisión técnica, reutilización/idempotencia ImageJ y origen MANUAL.

Frontend añade seis pruebas de modalidad, confirmación/cancelación, preservación
de fecha, limpieza/baseline, payload mínimo, doble submit, error por campo y
presentación. Se conservan las 34 pruebas anteriores, incluyendo las reglas de
análisis cerrado y creación de análisis de 18R-D.

No se ejecutó inspección visual en navegador. Queda pendiente revisión humana
del selector, confirmación, formularios y etiquetas en escritorio/viewport
estrecho; las pruebas SSR no sustituyen esa inspección.

## Auditoría read-only de datos reales

BD resuelta: `apps/web/Backend/db.sqlite3`; media: `apps/web/Backend/media`.
SQLite se abrió con URI `mode=ro`. Los manifiestos temporales son
`/tmp/sicam18re_pre.json` y `/tmp/sicam18re_final.json`.

- Antes/después: **7 pacientes**, **1 IDENTIFIED**, **6 PSEUDONYMIZED**.
- Hash de todos los valores de Paciente: idéntico.
- SHA-256 de BD completa: idéntico.
- Inventario/hashes de los **88 archivos de media**: idénticos.
- No se crearon pacientes reales ni se modificaron dataset/Excel.

## Archivos

- `apps/web/Backend/api/serializers.py`
- `apps/web/Backend/api/services/patient_identity.py` (nuevo)
- `apps/web/Backend/api/services/imagej/importer.py` (sólo reutiliza el helper)
- `apps/web/Backend/api/test_registration.py`
- `apps/web/Backend/api/test_imagej.py`
- `apps/web/Frontend/src/views/RegistroView.vue`
- `apps/web/Frontend/src/domain/patientPresentation.js`
- `apps/web/Frontend/src/services/registrationErrors.js`
- `apps/web/Frontend/tests/registration.test.mjs`
- `docs/79_sprint_18r_e_pseudonymized_registration.md` (nuevo)

## Decisiones diferidas

`case_number`, gestión manual de estados, reapertura/transiciones, idempotencia
durable de uploads y wizard/autoavance continúan fuera de alcance. No se cambia
Segmentación, editor, effective, Characterization ni microservicios.

Se mantienen los límites ya documentados para pérdida de respuesta POST,
concurrencia y diferencias de reloj/zona horaria. No se declara una garantía de
idempotencia durable nueva. La mutabilidad futura de autoridad y la revisión
visual siguen pendientes.

**SPRINT 18R-E = PASS WITH DEFERRED PRODUCT DECISIONS**
