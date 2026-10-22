# Sprint 18S-C — Interfaz operativa de adquisición y calibración

## Baseline y alcance

Baseline `f4306daadb13890fb2008284dc5be70bfee72455`, rama `master`, working tree
inicial limpio. 18S-B commiteado; Django check sin incidencias y api 0001–0010
aplicadas. Se inspeccionaron los cuatro modelos, las FK nullable de SALIVA/SANGRE,
serializers, endpoints, restricciones e implementación de compatibilidad de 18S-B.

Este sprint utiliza ese esquema sin modificar modelos ni generar migraciones.
No modifica el motor `api/services/calibration`, Characterization, segmentación,
ImageJ, geometrías ni resultados científicos históricos. Las medidas siguen en
píxeles; no hay conversiones a µm/µm² ni recalculo de caracterizaciones.

## IMPORTANT_PENDING_18S_A2

**La calibración es operativamente utilizable y científicamente PROVISIONAL.**
No se presenta como VALIDATED ni se añade un botón de validación científica.
Siguen pendientes:

- adquisiciones repetidas y repetibilidad;
- certificado/especificación y tolerancias del patrón;
- imágenes a 0° y 90°;
- estudio de anisotropía;
- incertidumbre metrológica;
- criterios científicos definitivos PASS/REVIEW/FAIL.

## Valores adoptados, sin recalcular el consenso aprobado

| Dato | sx µm/px | sy µm/px |
|---|---|---|
| CIRCLE_150 | 0.054382897123 | 0.054261143289 |
| CIRCLE_70 | 0.056084970972 | 0.055758978496 |
| Consenso operativo 18S-A.1 | **0.055233934048** | **0.055010060892** |

Es el consenso no ponderado C150+C70. El GRID completo mantiene
`AMBIGUOUS_GRID_PERIODICITY` y **no participa** en este consenso. No se usa la media
GRID+círculos ni la escala isotrópica como sustituto de sx/sy.
`0.0551219974698993` se conserva exclusivamente como dato auxiliar de provenance.

El seed guarda exactamente los decimales aprobados. El DecimalField de 18S-B puede
representarlos en la API con ceros finales hasta 15 posiciones decimales; no cambia
su valor. Método `AUTOMATIC_MULTI_REFERENCE`, versión
`calibration-provisional-v1/18S-A.1`.

Provenance conserva `seed_key=optika-40x-18s-a1-v1`,
`consensus_method=unweighted consensus of CIRCLE_150 and CIRCLE_70`,
`grid_status=AMBIGUOUS_GRID_PERIODICITY`, `scientific_status=PROVISIONAL_ONLY`,
`important_pending_18s_a2=true`, ambas escalas de cada círculo, el consenso y el
valor isotrópico auxiliar. Ninguna estimación previa del chat sustituye estos datos.

## Seed controlado y referencias

Desde Backend / entorno `sicam`:

```bash
python manage.py seed_optika_40x_calibration
# Opcional: verificar e incorporar los originales disponibles como evidencia.
python manage.py seed_optika_40x_calibration --include-evidence
```

`--source-dir` permite indicar una carpeta alternativa. Por defecto usa
`<repo>/data/calibration/`. Sin `--include-evidence`, registra sólo metadata/hash;
si un original no existe, la referencia puede quedar sin archivo. Si existe y su
hash no coincide, aborta **antes de cualquier escritura**.

Localiza un perfil físicamente equivalente, bloquea ambigüedades/conflictos y
reutiliza la misma calibración/provenance. La segunda ejecución devuelve
`ALREADY_PRESENT`; no renumera, no reescribe evidencia ni revierte RETIRED a
PROVISIONAL. Si un registro previo sólo tiene metadata y después se solicitan
archivos, se informa `EXISTING_METADATA_ONLY`: no se reemplaza silenciosamente
la evidencia inmutable de 18S-B.

Se usa `transaction.atomic()` y un lock local del comando bajo `/tmp`, identificado
por la BD, para serializar invocaciones concurrentes del seed en WSL. Esto no
implementa idempotencia durable general ni un coordinador distribuido. Archivos
nuevos de un intento fallido se compensan; no se eliminan archivos preexistentes.

Perfil creado en la BD de trabajo:

- ID **1**, `OPTIKA 40x`.
- Microscopio **OPTIKA B-1000FLHBO**.
- Cámara **OPTIKA C-B25+**, adaptador **M-114**, objetivo **40×**.
- Resolución **4928×4928**, modo **RGB**; binning no inventado.

Calibración creada: ID **1**, `CAL-OPTIKA-40X-PROVISIONAL-001`, **PROVISIONAL**.
Se crearon tres referencias y se copiaron los tres originales, sin modificarlos,
a rutas UUID gestionadas por `CalibrationReference.source_image`:

| Referencia | Dimensión conocida | Estado | SHA-256 origen = storage |
|---|---|---|---|
| GRID | 10 µm/división | AMBIGUOUS_GRID_PERIODICITY | `262835496b50f13d1dadcb934c2dda765b1f2055848b0b02d6ffffa446ac1d33` |
| C150 | 150 µm de diámetro | MEASURED | `d9daee7d4bc1790c004110d2febda32c7874a837c7298a85c1c739a3fb96c58b` |
| C70 | 70 µm de diámetro | MEASURED | `a3665c451b17ec42eb4713c5894ce66ca357305c39c67c6dd36e767f00ef3998` |

Todas las referencias son de 4928×4928. Las imágenes y los manifiestos de media no
se incluyen en Git. El seed real se ejecutó dos veces con `--include-evidence`:
primera `CREATED`, segunda `ALREADY_PRESENT`; conteos, filas, hashes BD y media
idénticos entre ambas ejecuciones.

## Navegación y acceso de operador

La navegación principal ofrece **Segmentación / Caracterización / Registro /
Adquisición**. La sección nueva tiene dos contextos: **Configuraciones** y
**Calibraciones**, con diseño adaptable al ancho y formularios etiquetados.
Se preservan guards de navegación del editor y Registro, y se añade guard del
trabajo pendiente en Adquisición.

Las APIs de 18S-B requieren autenticación. Como antes no había interfaz de acceso,
`OperatorAccess` permite autenticar un usuario Django existente mediante el
BasicAuthentication ya disponible, comprobado con
`GET /api/acquisition-operator/`. No crea cuentas, tokens ni sesiones nuevas en BD.
La contraseña se mantiene sólo en memoria del cliente Axios durante el acceso;
se limpia el input al terminar, se elimina al desconectar/recargar y nunca se guarda
en localStorage, sessionStorage ni archivos. Fuera de localhost el cliente exige
HTTPS. Axios usa nombres CSRF de Django para el caso de sesión existente en el mismo
origen. No se rebajan permisos a AllowAny ni se cambia la política global de Registro.

**La BD de trabajo tiene cero usuarios Django.** No se creó un usuario durante este
sprint: el alcance de escritura real sólo autoriza perfil/calibración/referencias.
Para revisar interactivamente adquisición, el investigador debe disponer de una
cuenta; por ejemplo, puede crearla mediante el comando normal:

```bash
cd ~/repos/sicam-refactor/apps/web/Backend
conda activate sicam
python manage.py createsuperuser
```

Ese comando **no se ejecutó**. Es un requisito operativo pendiente de la revisión
humana, independiente del seed. El Registro sin serie y el procesamiento en píxeles
continúan funcionando sin acceso de operador.

## Configuraciones y calibraciones en UI

Configuraciones permite listar, consultar, crear y editar metadata. Todos los campos
desconocidos permitidos por backend siguen siendo opcionales. El serializer añade
`physical_fields_locked` de sólo lectura, derivado de referencias existentes, sin
nuevo campo en BD: los perfiles sin uso pueden completarse; en perfiles ya usados
sólo se editan nombre/notas. La validación definitiva sigue en backend.

Calibraciones muestra nombre, perfil, sx, sy, estado textual, fecha y referencias.
El badge **Provisional** no depende sólo del color. La ayuda explica la validación
experimental pendiente. La lista se puede actualizar; no se ofrece una acción
trivial para promover a VALIDATED.

## Calibración automática general

Flujo UI:

1. Seleccionar perfil y nombre de calibración.
2. Adjuntar una o varias referencias.
3. Indicar explícitamente CIRCLE + diámetro conocido o GRADUATED_GRID + división
   conocida, en µm. No se extrae ese significado del nombre del archivo.
4. Pulsar **Medir referencias**; ver sx/sy, anisotropía, fuentes utilizadas/excluidas,
   estado por referencia y warnings.
5. Sólo con escala técnicamente utilizable, pulsar **Crear calibración provisional**.

El GRID admite una declaración explícita de retícula uniforme conocida. No se marca
por defecto; corresponde a `grid_reference=uniform_lattice`, ya soportado por el
motor, y no elimina la ambigüedad de patrones jerárquicos no declarados.

Rutas autenticadas, multipart:

- `POST /api/calibrations/automatic-preview/`: mide y devuelve `review`, sin persistir.
- `POST /api/calibrations/automatic/`: vuelve a verificar/medir, compara el
  `source_token` de la revisión y persiste sólo si coincide y es utilizable.

Campos: `acquisition_profile`, `label`, `source_token` para creación, `references`
como lista JSON y un archivo `reference_0`, `reference_1`, etc. Cada entrada contiene
`pattern_type`, `known_dimension_um` y opcionalmente `grid_reference`. Límites:
8 referencias, 30 MiB por archivo y 128 MiB por lote. Se rechazan archivos faltantes,
extras, repetidos bajo el mismo campo y metadata física inválida.

La operación reutiliza **measure_image** y **consensus** existentes; no duplica ni
ajusta el algoritmo. Una sola referencia MEASURED puede producir PROVISIONAL con
warning `SINGLE_MEASURED_REFERENCE`. Para varias medibles se utiliza el consenso
mediano que ya entrega el motor; esta política general no reemplaza el seed C150+C70
explícitamente aprobado. Los estados por referencia, estadísticas de consenso,
versión, hashes y warnings quedan en provenance/diagnósticos.

Un GRID ambiguo queda excluido y visible; si hay otras fuentes medibles puede
continuarse. Si no hay escala, o los originales no corresponden a resolución/modo
del perfil, no se crea calibración. No se inventan umbrales científicos de aceptación.
El objetivo del perfil debe conocerse para llamar al motor; si falta, se informa.

Archivos de entrada temporales bajo `/tmp`, eliminados al terminar. Creación de
Calibration y referencias en una transacción; cleanup de los archivos nuevos si
falla cualquier referencia o el commit. El perfil se relee/bloquea y se contrasta
antes de persistir. El token detecta cambios entre medir/crear, **no** implementa
idempotencia durable: tras una respuesta de red incierta se debe consultar la lista
antes de reintentar. La UI bloquea doble envío mientras la operación está en curso.

No se persisten overlays diagnósticos en esta versión: se muestran diagnósticos
estructurados, estados, fuentes, escalas y anisotropía. No se genera una segunda
implementación visual del motor ni se versionan imágenes temporales.

## Series y Registro → Imágenes

`GET /api/acquisition-series/?patient=<id>` filtra en backend. El componente también
filtra por paciente y descarta respuestas obsoletas con un contador de generación.

- Sin series: explica la ausencia, permite **Crear serie** o continuar sin serie.
- Exactamente una: selección automática al cargar el contexto del paciente.
- Varias: selección explícita, sin asumir que todas las imágenes usan el mismo perfil.
- Crear serie pide etiqueta, configuración, calibración opcional y fecha opcional.
  No repite los campos de cámara/objetivo por imagen.
- Calibraciones de otro perfil y RETIRED no aparecen como nuevas opciones.
- Series históricas RETIRED se muestran, conservando el bloqueo físico del backend.
- Serie sin calibración: **Sin calibración física**, permite upload y trabajo en píxeles.
- PROVISIONAL se muestra con texto y aviso de futuras medidas provisionales.

Upload SALIVA/SANGRE envía `acquisition_series=<id>` únicamente si está seleccionada.
Sin selección conserva el payload anterior y la FK nullable. Cambiar paciente limpia
serie, caso, análisis y archivos; cambiar serie descarta pendientes, libera URLs de
preview e informa. La creación de serie participa en busy/dirty y al guardar limpia
su formulario/baseline. No se navega durante escrituras en curso.

El resumen de destino incluye paciente/caso/análisis, serie, configuración,
calibración/estado y SALIVA/SANGRE. La información óptica sigue siendo declarada por
el operador, no inferida de un JPEG.

## Compatibilidad pre/post upload

El navegador lee dimensiones cuando puede y da feedback temprano. 4928×4928 contra
el perfil 4928×4928 indica coincidencia de resolución pendiente de comprobación del
backend; 2464×2464 muestra incompatibilidad y permite continuar sin medidas físicas.
Si el navegador no puede decodificar un TIFF u otro formato, no se inventan dimensiones.
No hay resize, reescalado proporcional ni botón de corrección automática.

Ambos endpoints de creación de muestras ahora añaden `physical_compatibility` al
response 201, calculado por el servicio de dominio existente sobre el archivo guardado.
Así también el upload anónimo sin serie recibe `NO_ACQUISITION_SERIES`. La interfaz
reutiliza este resultado; dispone de GET como fallback para respuestas antiguas.

Cada archivo muestra por separado **Subida/Error** y estado físico. Si falla la
consulta de compatibilidad después de una subida confirmada, muestra `CHECK_FAILED`,
conserva SUCCESS y no reenvía la imagen. No se convierte una imagen persistida en
un falso fallo de upload que provoque duplicados. Las invariantes físicas de 18S-B
siguen siendo la autoridad y su servicio no cambia.

## Auditoría histórica, sin backfill

```bash
python manage.py audit_historical_acquisition
```

Comando read-only: dimensiones por paciente, tipos, series existentes y coincidencia
exclusivamente de resolución. Usa aliases y `PRAGMA query_only` en SQLite durante
la lectura. No guarda previews, no ejecuta segmentación/caracterización ni vincula series.
Reporte de esta ejecución: `/tmp/sicam18sc/historical_audit.json`.

| Alias | SALIVA | SANGRE | Resoluciones (cantidad) | Coinciden 4928×4928 | Series |
|---|---:|---:|---|---:|---:|
| PATIENT_001 | 40 | 2 | 1×1 (1); 2456×1842 (38); 4928×4928 (1); 719×1280 (2) | 1 | 0 |
| PATIENT_002 | 5 | 0 | 4928×4928 (5) | 5 | 0 |
| PATIENT_003 | 5 | 0 | 2464×2464 (5) | 0 | 0 |
| PATIENT_004 | 3 | 0 | 4928×4928 (3) | 3 | 0 |
| PATIENT_005 | 3 | 0 | 2464×2464 (3) | 0 | 0 |
| PATIENT_006 | 6 | 0 | 4928×4928 (6) | 6 | 0 |
| PATIENT_007 | 1 | 0 | 4928×4928 (1) | 1 | 0 |

65 muestras, 16 coincidencias de resolución, ningún archivo ausente/ilegible al
leer dimensiones. **Esto no prueba la configuración óptica ni habilita unidades
físicas.** Todas las FK históricas siguen null; no se crearon series reales.

## Respaldo e integridad real

Antes del seed:

- BD resuelta desde settings: `apps/web/Backend/db.sqlite3`.
- MEDIA_ROOT: `apps/web/Backend/media`.
- Backup SQLite: `/tmp/sicam18sc_backup_20261021T184835Z/database/db.sqlite3`.
- SHA-256 backup:
  `934937e3c427cbd4f4ae11ec26dbbec181c259e3bdd7b667f6a7faa82e9ec64e`.
- SHA-256 BD previo:
  `9819e22943ff78852aae0b3c37d159c5545882f9f61ce0c1219ebdbbf3f4eede`.
- Se verificó equivalencia completa de filas del backup generado con API SQLite,
  legibilidad, integrity_check y foreign_key_check; no se exige igualdad física
  byte a byte de los headers internos de la copia SQLite.
- Directorio privado con `manifest.json`, `media_manifest.json`, `hashes.txt`,
  `RECOVERY.md`. Media se respalda mediante manifiesto/hashes, no una copia completa.

Guard inmediatamente anterior confirmó BD, media y originales iguales al snapshot.
Después del seed y de su repetición:

| Dato | Antes | Después |
|---|---:|---:|
| AcquisitionProfile | 0 | 1 |
| Calibration | 0 | 1 |
| CalibrationReference | 0 | 3 |
| AcquisitionSeries | 0 | 0 |
| Pacientes / casos / análisis | 7 / 7 / 7 | 7 / 7 / 7 |
| Muestras SALIVA / SANGRE | 63 / 2 | 63 / 2 |
| Resultados segmentación / revisiones | 27 / 27 | 27 / 27 |
| Caracterizaciones | 22 | 22 |
| ImageJImportRecord / SegmentationExecution | 23 / 25 | 23 / 25 |
| Archivos media | 88 | 91 |

Se compararon todas las columnas históricas mediante hash canónico, no sólo counts.
Los 88 archivos anteriores y los tres originales de `data/calibration` conservan sus
hashes. Las tres copias nuevas coinciden con los hashes aprobados. SQLite integrity
`ok`, foreign keys sin infracciones. La segunda ejecución no cambia siquiera el
hash de la BD: `513cc2b46a08cd73d4d4015e1c5848d9aa0f7152de70c9782bdbfaafc4d4c2af`.

Evidencia local: `/tmp/sicam18sc/pre.json`, `post.json`, `media_pre.json`,
`media_post.json`, `seed.log`, `integrity.py`, `historical_audit.json`.
No se versiona contenido clínico ni imágenes.

## Pruebas y revisión visual

- Backend completo, ejecutado **desde apps/web/Backend**: **323 tests OK**.
  Incluye 17 nuevos de 18S-C, 33 de adquisición 18S-B y 29 del motor 18S-A/A.1.
  Registro, ImageJ, Segmentación/revisiones/effective y Characterization intactos.
- Nuevos backend: seed inicial/repetido, valores exactos, hash erróneo, conflicto de
  estado; círculo, retícula, varias referencias, ambigüedad visible, ausencia de
  escala; fallo de motor y rollback/cleanup tras fallo de una segunda referencia;
  token obsoleto, imagen inválida, resolución incompatible, filtros/permisos,
  upload anónimo, mismatch no destructivo, fallo de consulta posterior, auditoría
  read-only y metadata de editabilidad del perfil.
- Frontend adquisición: **18 PASS**. Navegación/guards, formularios/listas, acceso
  en memoria, provisional, referencias, medición/creación, series cero/una/varias,
  stale requests, filtro de paciente, calibración opcional/retirada, payloads de
  ambos tipos, compatibilidad y limpieza de pendientes.
- Frontend Registro: **40 PASS**; Segmentación/editor: **59 PASS**;
  Characterization: **22 PASS**. Las expectativas de navegación se ajustaron a
  cuatro secciones reales y los tests de upload verifican también la consulta
  adicional de compatibilidad cuando falta en el response.
- Build con Node **24.17.0**: PASS. Django check: sin incidencias.
  `makemigrations --check --dry-run`: **No changes detected**.
- `git diff --check`: PASS. Sin commit, push ni staging.

Logs `/tmp/sicam18sc-{backend,acquisition-ui,registration,segmentation,characterization,build}.log`.
No hay navegador automatizable disponible ni ejecutables Chromium/Firefox instalados
en este entorno. Se comprobó renderizado SSR y comportamiento mediante tests; la
inspección visual/interacción real **queda para el investigador**, sin fingir que
fue ejecutada. No se modificó una muestra real para simular la validación visual.

Arranque para revisión:

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

No hacen falta CURRENT/ALT/BLOOD para revisar estos formularios. Revisar acceso de
operador, perfiles, calibración sembrada/provisional, referencias, formulario de
medición, series por paciente y los mensajes de resolución. Crear series/upload de
imágenes durante la revisión sí escribe datos y corresponde a una acción consciente
del investigador; el sprint no lo hizo automáticamente.

## Pendientes y contrato 18S-D

- **IMPORTANT_PENDING_18S_A2**: validación experimental pendiente.
- **HISTORICAL_ACQUISITION_ASSOCIATION = PENDING_MANUAL_CONFIRMATION**.
- **RETIRED_RECALCULATION_POLICY = PENDING_DECISION**: bloqueo físico conservador vigente.
- **DURABLE_UPLOAD_IDEMPOTENCY = PENDING**: no se resuelve accidentalmente aquí.
- Revisión visual/operativa humana y cuenta de operador local pendiente.
- Medición automática síncrona: su duración depende del tamaño/número de patrones;
  no se introduce cola de trabajos, distribución ni idempotencia general de creación.

18S-D podrá consultar `can_use_physical_units(sample)` y `physical_compatibility`
para obtener sx/sy, calibration_id y calibration_status con trazabilidad. Debe
preservar PROVISIONAL, definir persistencia de unidades/calibración usada y no
convertir una coincidencia de resolución histórica en confirmación de adquisición.
No comenzar conversiones antes de revisar este flujo operativo.

**SPRINT 18S-C = READY_FOR_VISUAL_AND_OPERATIONAL_REVIEW**
