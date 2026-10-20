# Sprint 18R-D — Análisis y reglas de integridad de Registro

## Baseline y precheck

- Rama: `master`.
- HEAD: `49fed95273d1294384406ee894a4eed7715e7ab9` (`Redesign registration interface`).
- Working tree inicial limpio, con 18R-C commiteado.
- Entornos existentes: Python de `sicam` y Node **24.17.0**.
- Django check sin problemas; migraciones api **0001–0009 aplicadas**.
- SQLite: `integrity_check = ok`; `foreign_key_check = 0 infracciones`.
- Sin instalaciones, migraciones, staging, commit ni push.

## Crear análisis para un caso existente

Se reutiliza **POST `/api/analisis/`**, sin nuevos endpoints ni cambios en
views, URLs o modelos. El serializer existente ya comprueba que el paciente
sea el propietario del caso.

En Imágenes, «Crear análisis» aparece sólo si el caso seleccionado no tiene
análisis, terminó correctamente la consulta y el contexto paciente/caso es
coherente. No se ofrece mientras la lista carga o ha fallado.

Se toma el paciente del campo `paciente` del caso devuelto por la API,
verificando que coincida con la selección. El usuario no introduce IDs.

```json
{
  "id_paciente_fk": "<paciente del caso>",
  "id_caso_fk": "<caso seleccionado>",
  "estado": 0
}
```

Los placeholders anteriores representan IDs numéricos en la petición real.
El análisis se crea **Abierto**. No se modifica Caso ni se genera `case_number`.

Al confirmar el POST:

1. Se conserva la respuesta creada y su ID.
2. Se recarga GET `/api/casos/{id}/analisis/`.
3. El nuevo análisis queda seleccionado, conservando paciente/caso y pestaña.
4. Se habilita continuar con imágenes.

Si la recarga falla, se conserva el análisis confirmado y se avisa que falló
la actualización de la lista. Reintentar la carga ejecuta GET; no repite POST.
Si falla el POST, se conserva contexto/archivos y se muestra un error legible.

`isCreatingAnalysis` bloquea el segundo envío, navegación, cambios de contexto,
selección de archivos y limpieza durante la operación. Se muestra
«Creando análisis...». Al terminar se libera el bloqueo.

La creación invalida lecturas anteriores con `analysesGeneration`, comprueba
contexto/disposición antes de aplicar respuestas y no permite que un GET viejo
borre la selección nueva. Una creación exitosa sin otros cambios pendientes
no deja el formulario dirty.

**Decisión de alcance UI:** casos con uno o más análisis no muestran el nuevo
botón. La API/modelo siguen admitiendo múltiples análisis por caso, cubierto
por pruebas. No se impone unicidad ni se restringe esa capacidad backend.

## Regla de análisis cerrado

| Estado | Texto UI | Alta de nuevas imágenes |
| --- | --- | --- |
| 0 | Abierto | Permitida |
| 1 | En proceso | Permitida |
| 2 | Cerrado | Rechazada |

### Backend

`SampleUploadSerializer` contiene la validación compartida de `analisis`,
heredada por los serializers de MuestraSaliva y MuestraSangre.

En las altas, un análisis cerrado produce HTTP **400**:

```json
{
  "analisis": ["No se pueden agregar imágenes a un análisis cerrado."]
}
```

La validación precede a `serializer.save()`: no se crea muestra ni se almacena
su imagen. Se prueba directamente con multipart en `/api/muestras/` y
`/api/muestras-sangre/`, sin depender de la UI.

La regla se aplica a altas (`instance is None`). No altera la consulta de
análisis/muestras existentes ni define nuevas políticas de edición o
reasignación de muestras existentes.

### Frontend

Los análisis cerrados siguen visibles y seleccionables. Las opciones y el
resumen muestran el estado en texto; el destino cerrado muestra:

> Este análisis está cerrado y no admite nuevas imágenes.

Se deshabilitan tipo/selector de archivos y submit. Los handlers bloquean
selección y envío/reintento cuando el análisis seleccionado está cerrado.
Cambiar de análisis conserva el reset de 18R-B: vacía pendientes, libera URLs
y notifica el cambio de contexto.

No se cambia ningún estado automáticamente. `cambiar_estado`, reapertura y
transiciones no forman parte de este sprint.

## Fecha de nacimiento

Backend: `PacienteSerializer.validate_fecha_nacimiento()` rechaza fechas
posteriores a `timezone.localdate()`, con error por campo:

> La fecha de nacimiento no puede ser futura.

La comparación utiliza fechas, no conversiones del DateField a timestamps.
Aplica a CREATE, PUT y PATCH cuando se proporciona el campo, en ambas
modalidades IDENTIFIED y PSEUDONYMIZED. Las reglas de identidad permanecen
intactas. PATCH de otros campos sobre un paciente válido continúa permitido.

Frontend:

- `max` del input utiliza año/mes/día locales del navegador, sin `toISOString()`.
- La regla se comprueba nuevamente antes de realizar POST.
- `change` e `invalid` muestran el mensaje inline incluso cuando la validación
  HTML impide el submit.
- Corregir la fecha elimina su error local.
- El mismo campo presenta errores DRF del servidor.
- Ayer y hoy son válidos; mañana es inválido.

## Regresiones preservadas

Se conservan doble submit, transacción Caso+Análisis, coherencia paciente/caso,
dirty state, beforeunload, generaciones de lecturas, limpieza de contexto,
object URL cleanup, estados por archivo y reintento exclusivo de PENDING/ERROR.

No hay autoavance ni wizard. El CSS de Registro es byte-exacto respecto a
18R-C. Se mantienen pestañas, layout, responsive, labels, errores inline y
previews; sólo se añaden los controles/estados necesarios.

No se modifican Segmentación, editor, effective, Characterization ni
microservicios.

## Validaciones ejecutadas

| Comando / comprobación | Resultado |
| --- | --- |
| `python manage.py test api.test_registration --noinput` | **10 tests OK**, incluyendo subcasos por estado/identidad/fecha/método |
| `python manage.py test api --noinput` | **235 tests OK** |
| `node tests/registration.test.mjs` | **34 passed** |
| `node tests/segmentationStrategies.test.mjs` | **59 passed** |
| `node tests/characterization21.test.mjs` | **22 passed** |
| `npm run build` con Node 24.17.0 | **PASS** |
| `python manage.py check` | Sin problemas |
| `python manage.py makemigrations --check --dry-run` | **No changes detected** |
| SQLite integrity / foreign keys inicial y final | **ok / 0 infracciones** |
| `git diff --check` | **PASS** |

Las pruebas backend añaden: múltiples análisis abiertos sin alterar el caso;
POST SALIVA/SANGRE para estados 0/1/2 sin cambios de estado ni archivos ante
rechazo; ayer/hoy/mañana en CREATE/PUT/PATCH para ambas identidades. Las pruebas
de fecha futura comprueban que un rechazo no muta registros.

Las diez pruebas frontend nuevas cubren creación, doble clic, contexto,
loading, selección, error/reintento, fallo de recarga posterior al POST,
GET obsoleto, desmontaje, contexto incoherente, estados, bloqueo de primer
upload/retry, liberación de URLs y fecha/error inline. Se conservan las 24
pruebas de Registro de 18R-C.

Toda escritura de prueba usa BD de test, archivos sintéticos en un
`TemporaryDirectory` y adaptadores HTTP simulados. No se efectuó aceptación
manual con altas reales ni se automatizó navegador.

## Integridad de datos reales

Rutas resueltas desde settings:

- BD: `/home/israel/repos/sicam-refactor/apps/web/Backend/db.sqlite3`.
- Media: `/home/israel/repos/sicam-refactor/apps/web/Backend/media`.

Se compararon SHA-256 antes/después de la BD y de los **88 archivos** de media:

- **DB_UNCHANGED = True**
- **MEDIA_UNCHANGED = True**

SQLite se abrió mediante URI `mode=ro`. Evidencia temporal:
`/tmp/sicam18rd_pre.json` y `/tmp/sicam18rd_final.json`.
Son manifiestos de verificación, no backups.

## Archivos modificados

- `apps/web/Backend/api/serializers.py`
- `apps/web/Backend/api/test_registration.py`
- `apps/web/Frontend/src/views/RegistroView.vue`
- `apps/web/Frontend/tests/registration.test.mjs`
- `docs/78_sprint_18r_d_registration_analysis_rules.md`

## Decisiones diferidas y límites

- PSEUDONYMIZED UI, `case_number`, gestión manual de estado, reapertura y
  transiciones siguen pendientes.
- **DURABLE_UPLOAD_IDEMPOTENCY = NOT_IMPLEMENTED**.
- No se introduce autoavance ni wizard obligatorio.
- El bloqueo de doble clic es local; una respuesta de POST perdida no asegura
  que el servidor no haya creado el registro. No hay idempotencia durable
  nueva para análisis ni uploads.
- La UI usa el estado consultado. Si otro cliente lo cambia, el servidor
  comprueba el estado al validar cada alta. No se implementa un protocolo de
  bloqueo concurrente entre cierre de análisis y persistencia de muestras.
- El servidor decide la fecha válida en su zona local. Un navegador con otro
  reloj/zona puede mostrar un límite distinto cerca de medianoche; el error
  backend sigue presentándose inline.
- Inspección visual humana de los nuevos controles pendiente.

**SPRINT 18R-D = PASS WITH DEFERRED PRODUCT DECISIONS**
