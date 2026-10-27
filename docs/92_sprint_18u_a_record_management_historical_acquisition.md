# Sprint 18U-A — Gestión de registros y asociación histórica a series

Fecha: 2026-10-26, America/Mexico_City.
Estado: **READY_FOR_VISUAL_ACCEPTANCE**.

## Precheck, baseline y backup

Rama `master`; HEAD `835c7d9ad87e252101252e1211b34525beebfa9f`
(`Upgrade backend to Django 5.2 LTS`). Working tree inicialmente limpio,
18T-D commiteado, `git diff --check` PASS. Python **3.10.20**, Django **5.2.18**,
Node **24.17.0**. No se instalaron ni actualizaron dependencias.

BD: `/home/israel/repos/sicam-refactor/apps/web/Backend/db.sqlite3`.
MEDIA_ROOT: `/home/israel/repos/sicam-refactor/apps/web/Backend/media`.

Backup previo consistente: `/tmp/sicam18ua_backup_20261026T222558Z/database/db.sqlite3`.
SHA-256: `6df5c618c3b661fa9365d4263256661237df88605ab6cf16d0a3687b0ee7e4f1`.

SQLite backup desde conexión read-only, copia legible, integrity_check `ok`,
foreign_key_check sin infracciones. `manifest.json` y `media_hashes.json` contienen
conteos, hashes de filas y hashes/tamaños de media. El manifiesto no es una copia
de los archivos; no se necesitó copiar imágenes. `/tmp` no sustituye una ubicación
durable de recuperación. No se restauró ni modificó el dataset real.

| Modelo | Antes | Después |
|---|---:|---:|
| `api_paciente` | 10 | 10 |
| `api_caso` | 10 | 10 |
| `api_analisispred` | 10 | 10 |
| `api_muestrasaliva` | 67 | 67 |
| `api_muestrasangre` | 2 | 2 |
| `api_acquisitionseries` | 4 | 4 |
| `api_acquisitionprofile` | 3 | 3 |
| `api_calibration` | 3 | 3 |
| `api_resultadosegmentacion` | 30 | 30 |
| `api_revisionsegmentacion` | 27 | 27 |
| `api_resultadocaracterizacion` | 25 | 25 |
| `api_lifecycleevent` | 53 | 53 |
| Archivos media | 95 | 95 |

| Tipo | Con serie antes/después | Sin serie antes/después |
|---|---:|---:|
| SALIVA | 4 / 4 | 63 / 63 |
| SANGRE | 0 / 0 | 2 / 2 |

Los conteos incluyen registros archivados y TEST preexistentes. No se ha asociado
ninguna imagen histórica real automáticamente ni durante la aceptación.

## UX y arquitectura

Antes: botón/card separado «Gestionar registros existentes» encima del formulario,
con selector genérico de recursos y listas lifecycle.

Ahora: `RegistroView.vue` contiene dos modos con el mismo lenguaje visual:

- **Nuevo registro** (default): conserva Paciente / Caso / Imágenes, altas
  IDENTIFIED/PSEUDONYMIZED, análisis, cargas y selector de series existentes.
- **Gestionar registros**: nuevo `RecordManagement.vue` con tabs Pacientes / Casos /
  Imágenes, cards blancas, bordes/radios/espaciado compatibles y tablas adaptadas
  con scroll horizontal en pantallas pequeñas.

El selector usa botones nativos, foco visible, estado `aria-pressed` y navegación
sin recarga. Cambiar modo usa `confirmLeave`: bloquea operaciones activas y pide
confirmación por trabajo pendiente. Los formularios nuevos se conservan mediante
`v-show`; cambiar modo no envía ni copia sus datos a gestión. La selección de
imágenes de gestión participa en el guard de salida y se descarta al desmontar.
La navegación y las protecciones de carga obsoleta/doble submit existentes siguen
cubiertas por los 40 tests de Registro.

Se reemplazó el uso del antiguo `LifecycleBrowser` en Registro. No se creó una
segunda implementación de lifecycle: las filas reutilizan `LifecycleActions`,
el inspector, confirmaciones, permisos y endpoints existentes. Su componente
legacy permanece en el repositorio, sin una segunda pantalla activa en Registro.

### Listas y filtros

Pacientes: identificador técnico `Paciente #ID`, tipo de identidad, número de
casos/imágenes, estado y acciones Ver casos / Ver imágenes / lifecycle.
Búsqueda por ID o iniciales; no se devuelven nombres, contactos, DOB ni expediente.
No se añade un formulario paralelo para editar datos personales.

Casos: `Caso #ID`, paciente técnico, conteos de análisis/imágenes, estado y
Ver imágenes / lifecycle. Búsqueda por ID, filtro de paciente e inclusión de
archivados conforme a la política ADMIN/SUPERUSER existente. Los títulos libres
no se exponen en estas listas para evitar PII innecesaria.

Imágenes: checkbox, basename/ID, SALIVA/SANGRE, paciente, caso/análisis, resolución
original/modo cuando legibles, serie, estado físico del backend, cantidad de
caracterizaciones guardadas, estado lifecycle y acciones existentes. «Guardadas»
no implica vigencia ni recalcula ninguna Characterization.

Filtros: búsqueda por archivo/ID, paciente, caso, tipo, cualquier serie / sin serie /
ID de serie específica e incluir archivados. **Estado físico (página)** filtra
explícitamente sólo los 20 registros cargados, usando los códigos ya devueltos
por backend; evita escanear/decodificar todas las imágenes para cada consulta.
No se presenta como un filtro científico global de dataset.

Selección individual, selección de página visible y limpieza; sólo registros
no archivados de la página, nunca selección implícita de toda la BD. Cambiar
consulta, página o tab limpia selección/preview. Peticiones GET obsoletas no
sustituyen resultados recientes; ejecución/preview bloquean cambios concurrentes.
Hay estados vacíos de pacientes, casos, imágenes, sin serie y sin series elegibles.

## Contratos backend

Nuevas rutas siguiendo convenciones `/api/`:

| Método / ruta | Contrato |
|---|---|
| GET `/api/record-management/patients/` | Lista privada paginada de pacientes |
| GET `/api/record-management/cases/` | Lista privada paginada de casos |
| GET `/api/record-management/images/` | Lista privada paginada SALIVA/SANGRE |
| GET `/api/record-management/series/?patient=<id>` | Opciones válidas para el paciente; contexto de profile/calibración |
| POST `/api/record-management/series/preview/` | Validación y compatibilidad por imagen, sin escrituras |
| POST `/api/record-management/series/assign/` | Confirmación y asociación transaccional |

Listas: `{count, page, page_size:20, results:[...]}`; página positiva, orden
estable por tipo/PK para imágenes. Parámetros `search`, `patient`, `case`, `type`,
`series` (`none` o ID), `include_archived=true`. Inputs inválidos se rechazan.
Las listas no exponen rutas de storage ni payloads científicos completos.

Preview:

```json
{
  "series_id": 7,
  "samples": [{"type": "SALIVA", "id": 123}]
}
```

De 1 a 50 imágenes, sin duplicados. SALIVA/SANGRE pueden mezclarse si pertenecen
al **mismo paciente**. Devuelve `series` con profile/calibración, `results` por
imagen (`id`, `type`, `already_assigned`, `compatibility`), `compatible_count` y
`preview_token` firmado.

Confirmación: el mismo payload más `confirm:true` y `preview_token`. El token
vence a los 600 segundos, está ligado al actor y al digest del contexto mostrado:
selección, archivos referenciados, compatibilidad y metadata de serie/profile/
calibración. Un token adulterado, expirado o un contexto cambiado exige preview
nuevo. No contiene los datos del contexto en claro, sólo digest/actor firmados.

La transacción engloba validación, locks operacionales de objetos/ancestros y
persistencia. Revalida existencia, estado, permisos, paciente/institución y serie.
Primero valida el lote completo; guarda mediante `sample.save` con las reglas de
modelo existentes y `updated_by`, no SQL update ni sustitución de modelo.
Un fallo de cualquier guard/save revierte todo el lote. No hay asignación parcial.

### Permisos y conflictos

- Sesión operativa requerida; CSRF/SessionAuthentication existentes permanecen.
- ADMIN y OPERATOR: misma política institucional de escritura de muestras que
  ya permite el endpoint PATCH normal; no se inventa restricción de creador ni
  se amplían privilegios. La restricción de creador para hard-delete es otra
  política y sigue intacta en lifecycle.
- REVIEWER: listas de consulta, sin selección/asignación. POST denegado por backend.
- SUPERUSER: política de plataforma existente, conservando coherencia
  paciente/institución/profile y requerimiento de institución activa.
- Cross-institution inaccesible: 404 por scope; paciente mixto o incompatible:
  conflicto 409, nunca división automática del lote.
- Imágenes o ancestros archivados: restauración previa requerida. History de
  listas sólo ADMIN/SUPERUSER con flag explícito; no habilita escritura archivada.
- Series elegibles: mismo paciente/institución, activas; profile activo/no archivado,
  calibración no retirada. No se elige automáticamente ni siquiera una única opción.
- Misma serie: no-op, incluyendo reintento de la misma petición confirmada mientras
  el token/contexto sigan válidos. No duplica filas ni cambia autores innecesariamente.
- Otra serie: **SERIES_ALREADY_ASSIGNED**, «Esta imagen ya pertenece a otra serie».
  No se ofrece reasignación ni desasignación en este sprint.

No se crea LifecycleEvent por asociar series: no es una acción lifecycle. La autoría
se conserva con el mecanismo `updated_by` existente. Motivo no requerido.

## Compatibilidad y provenance física

Se reutiliza **physical_compatibility**. Su comportamiento numérico/decisiones no
cambia. Se añadieron parámetros opcionales de contexto (`series`, `patient_id`)
para la lista paginada, cuyos objetos se obtienen con `select_related`; los callers
anteriores y preview/commit mantienen la consulta fresca por defecto. Un test
compara ambos resultados y otro comprueba que el número de queries de la página
no crece por cada imagen. Conteos mediante annotations, IDs de página mediante
UNION y carga relacionada en hasta dos querysets. No fetch de todas las imágenes
ni duplicación de compatibilidad en JavaScript.

La asociación describe adquisición; **no equivale a calibración compatible**:

| Situación | Asociación / feedback |
|---|---|
| Resolución/modo compatibles, PROVISIONAL | Asociación permitida; COMPATIBLE_PROVISIONAL y advertencia provisional |
| Compatible, VALIDATED | Contrato COMPATIBLE existente, sin cambiar estado metrológico |
| Resolución distinta | Asociación permitida; RESOLUTION_MISMATCH; valores físicos no disponibles |
| Modo distinto | Asociación permitida; IMAGE_MODE_MISMATCH; valores físicos no disponibles |
| Sin calibración | Asociación permitida; NO_CALIBRATION; procesamiento en píxeles |
| Calibración RETIRED | Nueva asociación bloqueada conforme a política preexistente |
| Profile/paciente incoherentes | Bloqueados por admisión/modelos; no se inventa compatibilidad |

No resize, sustitución/escalado automático de calibración ni inferencia desde
filename/resolución. Las dimensiones y modo del listado salen de los bytes
originales; datos ilegibles se muestran como no disponibles.

La UI muestra serie/profile/calibración, número seleccionado y compatibles/no
compatibles antes de confirmar; una incompatibilidad lleva aviso visible. El éxito
indica disponibilidad física y calibración provisional cuando corresponda, sin
prometer metrología definitiva. SALIVA necesita además una segmentación completa;
SANGRE conserva su contrato de conteos. No se ejecuta Characterization ni se crea
un algoritmo/endpoint alternativo: se indica usar Caracterización en el menú actual.

Cualquier imagen con serie actual está protegida frente a reasignación, tenga o no
Characterization 2.2. Un resultado 2.2 histórico pixel-only de una imagen **sin**
serie puede conservarse mientras se hace la primera asociación: su snapshot no se
reescribe. Una futura caracterización explícita sigue las reglas existentes de
fingerprint/idempotencia; la asociación nunca actualiza el resultado previo.

## Pruebas y validaciones

| Validación | Resultado |
|---|---|
| Backend dirigido nuevo | **18 passed** |
| Frontend dirigido nuevo | **12 passed** |
| Regresión dirigida Registro | **40 passed** |
| Backend completo, una ejecución estable | **466 passed, 2 skipped**, 25.88 s |
| Frontend completo, una ejecución estable | **199 passed, 0 failed** |
| Segmentación/editor | 59, incluidos en frontend, sin repetición separada |
| `npm run build` | PASS, 1.10 s |
| `manage.py check` | PASS |
| `makemigrations --check --dry-run` | No changes detected |
| `pip check` | PASS |
| `git diff --check` | PASS |

Backend dirigido cubre: preview sin escrituras, asignación compatible, lote mixto
SALIVA/SANGRE del mismo paciente, pacientes distintos, tenant, REVIEWER, OPERATOR,
serie inválida, duplicados, confirmación, misma/otra serie, snapshots 2.2 con/sin
serie previa, resolución/modo, ausencia/retiro de calibración, archivado, preview
cambiado/adulterado, profile indisponible, reintento idéntico, rollback tras fallo
en segundo save, paginación/filtros/privacidad, opciones por paciente y N+1.

Frontend dirigido cubre modos/guard, preservación de datos nuevos, tabs, listas,
estados vacíos, contexto/badges, filtros y respuestas obsoletas, selección limitada,
mezcla de pacientes, REVIEWER, selección explícita de serie, advertencias,
confirmación, doble-submit y conflictos que invalidan preview.

Durante desarrollo se corrigieron fixtures nuevos sin `respuesta_json`, una
comparación de Decimal usando objeto sin refrescar y el test de navegación antiguo
que asumía un solo `<nav>`. Se añadió un mapeo seguro de códigos de conflicto para
mostrar el bloqueo de otra serie. No se relajaron assertions científicas ni permisos.
La suite completa pasó a la primera ejecución estable; no hubo refactor especulativo.
Los dos skipped siguen siendo las integraciones que requieren servicios científicos
reales; no se iniciaron. Persisten los 36 avisos CheckConstraint ya diferidos.

## Integridad científica y real

Las pruebas usan BD y storage temporales. Comparación final de **todas las tablas**
por PK y hash de fila completa: idénticas. Mismas asociaciones, counts, usuarios,
revisiones, import records y LifecycleEvents **53 → 53**.

Media: **95 → 95**, mismos filenames/tamaños/SHA-256; ningún archivo real creado,
borrado o modificado. SQLite integrity_check `ok`, foreign_key_check sin infracciones.

Characterization **24**, sample **66**, versión **2.2**,
**COMPATIBLE_PROVISIONAL**: fila completa, resultados/features, snapshot,
hash efectivo y fingerprint idénticos. sx `0.055233934048`, sy `0.055010060892`.
`CAL-OPTIKA-40X-PROVISIONAL-001`: **PROVISIONAL**, escalas/profile/provenance y
referencias intactos. No cálculos científicos reales ni nuevo lifecycle real.

Evidencia local: `/tmp/sicam18ua/`, con before/after snapshots, baseline.log,
manifest de media, pruebas dirigidas, backend_full.log/xml, nueve logs frontend,
build.log e integrity_final.log. No se incluyen imágenes ni datos clínicos en Git.

## Archivos y alcance

### Nota de reanudación

Al reanudar el cierre, `/tmp/sicam18ua/` y el backup temporal anterior ya no
estaban disponibles. Los resultados de regresión y la comparación completa
before/after indicados arriba corresponden a la ejecución previa, cuyos resultados
quedaron registrados en la conversación; no se volvieron a ejecutar las suites.
No debe considerarse que ese backup temporal siga siendo recuperable.

Se comprobó nuevamente, sólo por lectura: SQLite `ok`, sin infracciones FK,
los mismos conteos y asociaciones de las tablas anteriores, 95 archivos media,
Characterization 24 con versión/sample/estado/fingerprint esperados y calibración
PROVISIONAL con las mismas escalas. No se pudo repetir la comparación de todos
los hashes de media/filas al faltar el manifiesto previo. Esta comprobación breve
no sustituye la comparación completa que sí pasó antes de la pausa ni certifica
eventuales cambios externos posteriores. No se escribió en BD o media al reanudar.

### Inventario de cambios

- `api/record_management.py`: API privada y asociación transaccional.
- `api/urls.py`: rutas.
- `api/services/acquisition/compatibility.py`: contexto opcional para lectura
  paginada; decisiones científicas intactas y default fresco preservado.
- `api/test_record_management.py`: fixtures/tests aislados.
- `Frontend/src/components/registration/RecordManagement.vue`: gestión integrada.
- `Frontend/src/views/RegistroView.vue`: modos y guard existente.
- `Frontend/tests/recordManagement.test.mjs`: pruebas nuevas.
- `Frontend/tests/registration.test.mjs`: localizar nav de creación por aria-label.
- `docs/92_sprint_18u_a_record_management_historical_acquisition.md`: informe.

Sin modelos, migraciones, requirements, frontend shell, algoritmos científicos o
Dataset Builder nuevos. Sin git add, commit ni push. Los archivos nuevos siguen
untracked hasta una futura autorización de versionado.

## Checklist visual del investigador

No se automatizó navegador ni se atribuye aceptación visual todavía. Acceso local
conocido `http://127.0.0.1:5173/`. Reiniciar Django/Vite si no recargaron los nuevos
archivos. No hacen falta CURRENT/ALT/BLOOD para revisar esta gestión.
Usar fixtures TEST para asociación experimental o acciones destructivas; no utilizar
la calibración real ni una imagen histórica sin confirmar su procedencia.

- [ ] A. Registro → Nuevo registro: Paciente/Caso/Imágenes mantienen apariencia y flujo.
- [ ] B. Registro → Gestionar registros: modos y cards integrados visualmente; probar teclado.
- [ ] C. Pacientes: búsqueda por ID, listas, conteos, Ver casos/Ver imágenes y lifecycle.
- [ ] D. Casos: filtro paciente, lista, acciones y contexto.
- [ ] E. Imágenes: filtros, estados, paginación y selección de página visible.
- [ ] F. Seleccionar imagen TEST histórica sin serie; selección mixta de pacientes bloqueada.
- [ ] G. Elegir explícitamente una serie TEST del paciente; no selección automática.
- [ ] H. Revisar preview, conteos y confirmación antes de asociar.
- [ ] I. Ver advertencia PROVISIONAL; no presentarla como metrología definitiva.
- [ ] J. Imagen TEST incompatible: asociación advertida, valores físicos no disponibles.
- [ ] K. Imagen ya asociada: otra serie bloqueada; misma serie no duplica.

Probar además vuelta al modo nuevo con trabajo pendiente, REVIEWER de consulta,
archivados ADMIN y ausencia de Characterization automática tras éxito.

## Pendientes y siguiente paso

- HISTORICAL_ACQUISITION_ASSOCIATION = **IMPLEMENTED_FOR_MANUAL_ASSIGNMENT**.
  No significa que las imágenes históricas reales hayan sido asociadas.
- ACQUISITION_SERIES_REASSIGNMENT_POLICY = **PENDING_DECISION**.
- IMPORTANT_PENDING_18S_A2, RETIRED_RECALCULATION_POLICY,
  DURABLE_UPLOAD_IDEMPOTENCY, GLCM_PHYSICAL_DISTANCE_NORMALIZATION,
  MANUAL_VISUAL_REVIEW_18S_D, PRODUCTION_MEDIA_ACCESS_CONTROL,
  DJANGO_CHECKCONSTRAINT_CONDITION_MIGRATION y demás pendientes anteriores se
  conservan (infraestructura/WSGI/SQLite, retención, media huérfana, rate limiting,
  recuperación de contraseñas y membresía multiinstitución incluidos).

Después de la aceptación visual, próximo bloque propuesto: **18U-B — Dataset
Builder**. No se implementaron clases, exportación ML/CSV/XLSX, splits, selección
de features ni manifest de datasets en 18U-A.

SPRINT 18U-A = READY_FOR_VISUAL_ACCEPTANCE

## 18U-A.1 — IDENTIDAD Y BÚSQUEDA CONTEXTUAL

### Punto de partida y alcance

Refinamiento sobre los cambios **sin commit de 18U-A**, rama `master`, HEAD
`835c7d9ad87e252101252e1211b34525beebfa9f`. Se preservan los cambios previos en
compatibilidad (contexto precargado para listados), rutas, Registro, gestión,
pruebas y este documento. A.1 no modifica algoritmos, modelos, dependencias ni la
semántica de asignación de series. No se implementa 18U-B.

Antes, Gestión buscaba pacientes por iniciales o PK, mostraba `Paciente #PK` y
solicitaba filtros numéricos Paciente/Caso. Segmentación (`SideBar.vue`) cargaba
`/api/pacientes/`, usando `PacienteSerializer`, y filtraba localmente por
`patientDisplayName` (iniciales para pseudonimizados, nombre para identificados),
identificación e ID externo; sólo mostraba cinco candidatos. Ese endpoint ya
utiliza `ScopedViewMixin` y la política de archivados. El serializador general
contiene datos que no hacen falta para un lookup; no se amplía su exposición.

**Iniciales son atributos de búsqueda, nunca identidad única.** La selección
siempre conserva el PK real y las operaciones continúan validando FK reales.

### Arquitectura compartida y privacidad

- `api/patient_lookup.py`: filtro compartido `search_patients`, proyección mínima
  `patient_identity` y paginación fija de 20 resultados, ordenados por PK.
- `GET /api/pacientes/lookup/?q=...&page=1`: acción del ViewSet existente; reutiliza
  `get_queryset()` para permisos, institución y ciclo de vida. No crea relaciones.
- Campos buscables mediante coincidencia parcial e insensible a mayúsculas:
  `initials`, `identificacion`, `external_id_namespace`, `external_patient_id`.
  Espacios externos recortados y consulta limitada a 150 caracteres.
- Respuesta: `id`, `initials`, `identificacion`, `identity_mode`,
  `external_id_namespace`, `external_patient_id`, dentro de
  `{count, next, previous, results}`. No incluye nombre, apellido, email, teléfono
  ni fecha de nacimiento. No se derivan iniciales ficticias de otros campos.
- ADMIN/OPERATOR/REVIEWER ven su institución; SUPERUSER conserva alcance global.
  Archivados siguen excluidos por defecto; sólo ADMIN/plataforma puede incluirlos
  según la política existente. Acceso anónimo rechazado.
- Gestión de pacientes usa exactamente el mismo filtro y proyección mínima.
  Casos e imágenes incluyen `patient_identity` sin consultas extra por fila.
- `PatientLookup.vue` es reutilizable: entrada de búsqueda, carga, error,
  resultados vacíos, candidatos, paginación, selección explícita y limpieza.
  No autoselecciona aunque sólo haya una coincidencia. Distingue iniciales
  duplicadas mediante identificación técnica y namespace/ID externo.
- `patientPresentation.js` centraliza las etiquetas operativas y traducciones
  `Pseudonimizado` / `Identificado`. Nombre principal: iniciales, o identificación
  técnica cuando no hay iniciales; PK reservado para estado/API.
- Segmentación reutiliza el mismo componente y endpoint. Conserva la emisión de
  `select-patient` con PK, las protecciones de navegación, selección de casos,
  resúmenes y carga existente del contexto. La búsqueda compartida se limita a
  los cuatro atributos anteriores: no busca nombres/apellidos. La ficha de
  paciente ya existente mantiene su presentación y permisos previos.

### Gestión contextual

- Pacientes: `Buscar paciente`, placeholder
  `Iniciales, ID técnico o identificador...`; iniciales/ID técnico en filas y enums
  traducidos. No se muestran PK como identidad principal.
- Casos e imágenes: `PatientLookup` reemplaza el input numérico de paciente.
  Contexto de filas: iniciales e identificación técnica, sin PII adicional.
- Imágenes: selector de casos deshabilitado sin paciente; consulta paginada a
  `/api/record-management/cases/?patient=<PK>&page=...`. `Más casos` permite
  acceder a las páginas siguientes sin truncar silenciosamente las opciones.
- Cambio/limpieza de paciente limpia caso, opciones y selección de imágenes,
  invalida respuestas anteriores y refresca resultados. Los filtros usan el PK
  seleccionado, no el texto. Una respuesta tardía no restaura opciones del
  paciente anterior. Hay reintento explícito si falla la carga de casos.
- Combinaciones incoherentes de paciente/caso en API devuelven un conjunto vacío
  por la intersección de ambas FK y el scope institucional; no filtran por
  iniciales ni exponen registros del caso incompatible.
- Se mantienen paginación, filtros de serie/estado físico, archivados, preview,
  confirmación, protección de reasignación y transacción de 18U-A.
- Jerarquía visual mínima: selector de modo agrupado sobre fondo suave;
  pestañas de contenido separadas. Sin rediseño general del formulario de alta.

### Nombre de imagen

`MuestraSaliva`/`MuestraSangre` almacenan el nombre del archivo en storage mediante
`imagen`; no existe un campo general de nombre original completo. ImageJ conserva
`logical_basename` (stem, sin extensión), no un nombre original completo común a
las imágenes subidas. No se reconstruye ni se presenta ese stem como si fuera el
filename original. Sigue visible el basename del archivo almacenado.

`ORIGINAL_FILENAME_DISPLAY = PENDING`. No se añade modelo ni migración para ello.

### Verificación automatizada

Todas las escrituras de pruebas usan BD y media temporales, sin pacientes reales.

- Dirigidas backend: gestión, lookup, registro y acceso: **66 passed**.
- Dirigidas frontend: Gestión/lookup **19 passed**; Segmentación **59 passed**.
- Cobertura nueva: dos pacientes EJT con IDs técnicos distintos, búsqueda parcial
  y sin distinguir mayúsculas, ID técnico/externo/namespace, resultados vacíos,
  aislamiento entre instituciones, tres roles, SUPERUSER, anónimo, archivados,
  límite/paginación, filtros por FK, combinación paciente/caso inválida,
  selección explícita, estados de carga/error, respuestas tardías, limpieza y
  paginación de casos, traducción de enums e integración de Segmentación.
- Regresión backend completa: **471 passed, 2 skipped**, una sola ejecución completa.
- Regresión frontend completa, ejecutada una vez: **206 passed, 0 failed**.
- `npm run build`, ejecutado una vez: **PASS**.
- `manage.py check`: sin incidencias.
- `manage.py makemigrations --check --dry-run`: `No changes detected`.
- `python -m pip check`: `No broken requirements found`. Aviso de caché pip no
  escribible, sin instalación ni modificación de dependencias.
- Los avisos existentes de `CheckConstraint.check` siguen pendientes; no se
  cambia su sintaxis ni las migraciones en este refinamiento.

Artefactos de esta ejecución: `/tmp/sicam18ua1/`, incluyendo logs dirigidos,
regresión, XML de backend, build y snapshots de integridad. Son temporales y no
forman parte del repositorio.

### Integridad real

Snapshots SQLite de sólo lectura y hashes SHA-256 antes/después:

- Las **30 tablas** mantienen exactamente conteos y hashes de todas sus filas,
  incluidas asociaciones, datos científicos, auth e historial.
- Hash del archivo SQLite idéntico antes/después. `integrity_check = ok`,
  `foreign_key_check = []`.
- **95 archivos de media**, mismos nombres relativos y hashes.
- Characterization **24**: hash de fila completo idéntico.
- Calibración **1**, `CAL-OPTIKA-40X-PROVISIONAL-001`: hash de fila completo
  idéntico; `PROVISIONAL`, sx `0.055233934048`, sy `0.055010060892`.
- LifecycleEvent: **53 → 53**, contenido idéntico.

La comparación completa está en `/tmp/sicam18ua1/comparison.json`; no contiene
nombres de pacientes ni payloads clínicos.

No se ejecutan segmentadores ni Characterization; no se asignan series reales,
no se editan pacientes/casos/imágenes, no se crean LifecycleEvents reales.

### Checklist visual A–L

Realizar en la UI con una sesión autorizada. Las acciones de escritura de prueba
se reservan a registros TEST; esta implementación no las ejecuta sobre datos reales.

- [ ] A. Registro → Gestionar registros → Pacientes: buscar iniciales reales.
- [ ] B. Comprobar identidad significativa en cada coincidencia.
- [ ] C. Si hay iniciales duplicadas, distinguir candidatos por sus identificadores
  y seleccionar uno explícitamente.
- [ ] D. Casos: seleccionar paciente mediante PatientLookup.
- [ ] E. Verificar que aparecen sólo sus casos.
- [ ] F. Imágenes: seleccionar paciente.
- [ ] G. Comprobar que el selector Caso sólo ofrece casos de ese paciente.
- [ ] H. Cambiar paciente y comprobar limpieza del caso y opciones anteriores.
- [ ] I. Verificar iniciales/ID técnico como contexto de las imágenes.
- [ ] J. Comprobar `Pseudonimizado`, sin enum `PSEUDONYMIZED` visible.
- [ ] K. Segmentación: buscar iniciales, seleccionar y abrir un caso normalmente.
- [ ] L. Verificar Nuevo registro y asignación a series de 18U-A con registros TEST,
  conservando preview/confirmación y advertencia de calibración provisional.

### Pendientes y cierre

Se conservan todos los pendientes anteriores, incluidos:
`ACQUISITION_SERIES_REASSIGNMENT_POLICY = PENDING_DECISION`,
`IMPORTANT_PENDING_18S_A2`, `RETIRED_RECALCULATION_POLICY`,
`DURABLE_UPLOAD_IDEMPOTENCY`, `GLCM_PHYSICAL_DISTANCE_NORMALIZATION`,
`MANUAL_VISUAL_REVIEW_18S_D`, `PRODUCTION_MEDIA_ACCESS_CONTROL` y
`DJANGO_CHECKCONSTRAINT_CONDITION_MIGRATION`.

Cerrar 18U-A después de la aceptación visual A–L; después se podrá autorizar
18U-B utilizando el lookup compartido. No se hizo staging, commit ni push.

Git final: `git diff --check` sin errores; los siete archivos nuevos también
pasan la comprobación de whitespace. Estado completo en
`/tmp/sicam18ua1/git_status_final.txt` y stat en
`/tmp/sicam18ua1/git_diff_stat.txt`. Los cambios de 18U-A siguen presentes;
A.1 añade el helper de lookup, su acción de lectura, componente compartido,
identidad/contexto en Gestión y pruebas. No hay modelos, migraciones ni cambios
científicos nuevos. `git diff --stat` de archivos ya seguidos: 7 archivos,
52 inserciones, 61 eliminaciones; los archivos nuevos de Gestión/lookup, pruebas
y este documento siguen sin seguimiento (no se hizo staging).

SPRINT 18U-A.1 = READY_FOR_VISUAL_ACCEPTANCE

## 18U-A.2 — VISUAL POLISH

Pulido exclusivamente frontend sobre 18U-A/A.1 sin commit. Rama `master`, HEAD
`835c7d9ad87e252101252e1211b34525beebfa9f`. Se preservó el working tree previo.
Sin cambios adicionales de backend, APIs, modelos, dependencias, migraciones,
lifecycle, asignación de series, calibración ni Characterization.

### Presentación

- `compactPresentation.js` contiene helpers de presentación: identificadores
  largos muestran `…` y seis caracteres finales; si candidatos distintos tienen
  el mismo sufijo, éste se amplía hasta distinguirlos. Los identificadores cortos
  permanecen completos. No se modifican valores de API ni estado/FK.
- `CompactValue.vue` conserva el valor completo en `title` y `aria-label`.
  En tablas/fichas permite foco por teclado y revela el valor completo al enfocar.
  Dentro de botones de candidatos no añade focos anidados: el botón proporciona
  nombre accesible con identidad completa y `title`. La selección sigue siendo
  explícita, incluso con una única coincidencia.
- Pacientes y contexto de Casos/Imágenes muestran iniciales e ID compacto.
  Sin iniciales se mantiene el identificador técnico, sin inventarlas. En filas
  de pacientes no se repite el ID si ya es la etiqueta principal.
- Singular/plural aplicado a caso/casos, imagen/imágenes, análisis,
  caracterización/caracterizaciones, selección, coincidencias y conteos de
  registros/compatibilidad. Sólo cambia texto, no cálculos.
- Casos mantiene `Caso #PK` y elimina la línea redundante `ID PK`.
  No se implementa una nueva política de `case_number`.
- Archivos largos conservan comienzo y final, por ejemplo
  `020b5358…a68801.jpg`; el nombre completo sigue accesible. Storage intacto.
  `ORIGINAL_FILENAME_DISPLAY = PENDING` permanece vigente.
- Información de imagen: resolución y modo, perfil y serie disponibles,
  número de caracterizaciones. Badges científicos conservan su significado.
- Tabla con `table-layout: fixed`, contenido largo con salto de línea,
  selección de 52 px y columna Acciones de 140 px. Con el contenedor de Registro
  de hasta 960 px, los textos largos no determinan el ancho de las columnas ni
  desplazan Acciones. El mínimo de 760 px permite scroll sólo cuando el espacio
  disponible es menor (pantallas pequeñas); no se ocultan columnas importantes.
  `Más acciones` conserva texto completo. La comprobación de overflow y lectura
  en navegador real permanece en el checklist visual, no fue medida con un
  navegador automatizado durante esta ejecución.
- Placeholder compartido: `Iniciales o identificador`.
- Segmentación sólo monta PatientLookup sin paciente seleccionado. Tras selección
  conserva una ficha: identidad, ID compacto, tipo traducido, edad ya existente
  y una sola acción `Cambiar paciente`. El evento de cambio existente sigue
  gestionando los guards y contexto; al limpiar se monta un buscador vacío.
- La jerarquía de navegación de A.1 permanece sin cambios.

Archivos de A.2: `SideBar.vue`, `registration/PatientLookup.vue`,
`registration/RecordManagement.vue`, nuevo `registration/CompactValue.vue`,
nuevo `domain/compactPresentation.js`, `tests/recordManagement.test.mjs` y este
mismo `docs/92`. El resto de los cambios pendientes sigue perteneciendo a A/A.1.

### Pruebas e integridad

- Dirigidas: **24 Gestión/lookup**, **59 Segmentación**, sin fallos.
- Nuevos casos cubren abreviación, conservación accesible del valor completo,
  sufijos coincidentes con iniciales duplicadas, singular/plural, ID de caso sin
  duplicación, filename, presencia de Estado/Acciones y perfil/serie, una sola
  acción de cambio y regreso al buscador vacío.
- Regresión completa una vez por suite: **backend 471 passed, 2 skipped**;
  **frontend 211 passed, 0 failed**. Build una vez: **PASS**.
- Django check: sin incidencias; `makemigrations --check --dry-run`: sin cambios;
  `pip check`: sin incompatibilidades. Persisten 36 avisos de deprecación ya
  conocidos y el aviso de caché pip no escribible; no afectan el resultado.
- Snapshots de sólo lectura: hash del archivo SQLite idéntico, conteos y hashes
  de las 30 tablas idénticos, asociaciones intactas; `integrity_check = ok`,
  `foreign_key_check = []`. LifecycleEvent **53 → 53**. Media **95 archivos**,
  mismos nombres/hashes. Characterization **24** y Calibration **1**: hashes
  completos idénticos. `CAL-OPTIKA-40X-PROVISIONAL-001` sigue **PROVISIONAL**, sx
  `0.055233934048`, sy `0.055010060892`. No se asignaron series reales.

Artefactos temporales: `/tmp/sicam18ua2/` (logs, snapshots y comparación de hashes).
No hay información clínica identificable en este informe. No se ejecutan motores
científicos ni asignaciones reales. No se hizo staging, commit ni push.

### Checklist final visual

- [ ] A. Pacientes: iniciales legibles, ID compacto con valor completo accesible,
  singular/plural correcto y Acciones visible.
- [ ] B. Casos: `Caso #PK` sin ID duplicado, contexto compacto y filtros legibles.
- [ ] C. Imágenes: filename compacto y completo accesible con hover/teclado;
  sin scroll horizontal en escritorio normal; Estado y Acciones visibles;
  resolución/modo, perfil/serie y caracterizaciones legibles.
- [ ] D. Segmentación: buscar, seleccionar, comprobar cierre del buscador y una
  sola acción `Cambiar paciente`; usarla y verificar búsqueda limpia.
- [ ] E. PatientLookup: pacientes con iniciales iguales siguen distinguiéndose
  por su ID; elegir explícitamente y comprobar paciente/caso correctos.

Tras aprobar A–E, realizar una prueba manual de asignación con imágenes y serie
TEST del mismo paciente, preview y confirmación explícita; comprobar advertencia
PROVISIONAL y que no se recalcula Characterization. Una asignación de datos reales
requiere seleccionar la adquisición correcta y confirmarla expresamente. No se
realizó esa operación en A.2. Permanecen todos los pendientes de A/A.1 y no se
inicia Dataset Builder.

Git: `git diff --check` sin errores. Diff acumulado de archivos ya seguidos:
7 archivos, 57 inserciones, 64 eliminaciones; no incluye los 9 archivos nuevos
sin seguimiento de A/A.1/A.2. Estado detallado en
`/tmp/sicam18ua2/git_status_final.txt`. No se hizo staging.

SPRINT 18U-A.2 = READY_FOR_FINAL_VISUAL_ACCEPTANCE
