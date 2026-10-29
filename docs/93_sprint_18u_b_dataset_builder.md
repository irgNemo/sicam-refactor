# Sprint 18U-B — Dataset Builder de características nucleares

## Alcance y punto de partida

Implementación SALIVA, tipo `SALIVA_NUCLEAR_FEATURES`, granularidad
`NUCLEUS_MN_RELATION`. Se exportan **resultados guardados**, sin ejecutar
segmentación, Characterization, importación ImageJ ni asignación de series.
No se calculan métricas faltantes ni se infieren clases clínicas.

Precheck: `master`, HEAD `cc29d5c2c9a86aa04d997d25115a508cee193030`, working tree
limpio y `git diff --check` correcto. 18U-A/A.1/A.2 ya estaban en ese commit.
Python 3.10.20, Django 5.2.18 y Node 24.17.0. Sin dependencias nuevas/actualizadas.

El Excel de referencia se audita contra las **columnas conceptuales suministradas
por el investigador** y el código/JSON persistido de Characterization; no se
recibió en este sprint una ruta concreta al libro de referencia para comparar
sus hojas o valores. No se declara equivalencia numérica con un libro externo.

## Arquitectura, almacenamiento y migración

- `dataset_models.py`: `MLDataset`, `MLDatasetPatient`, `MLDatasetSample`.
- `services/datasets/features.py`: catálogo explícito y orden de columnas.
- `services/datasets/builder.py`: selección de fuentes, filas, exclusiones,
  hashes y manifiesto. Sólo lectura de resultados científicos.
- `dataset_views.py`: permisos, borradores, preview, generación y descargas.
- `services/datasets/xlsx.py`: escritor OOXML de valores, usando `zipfile` y XML
  de la biblioteca estándar. No se añadió openpyxl; el importador ImageJ existente
  también usa biblioteca estándar para su contrato limitado de lectura XLSX.
- `DatasetsView.vue`: módulo Conjuntos de datos. Reutiliza `PatientLookup`,
  `CompactValue`, API autenticada y permisos existentes.

La aplicación no usa Vue Router: se integra como sección `datasets` en el
navegador de secciones existente de `App.vue`, con su persistencia de contexto.
TopBar incorpora Conjuntos de datos y permite envolver botones en pantallas
estrechas. Se agregan guards de salida/logout y beforeunload para trabajo sin
Guardar/busy; no se rediseña el shell.

`MLDataset` guarda institución, nombre/descripción, tipo, versión exacta,
unidades, configuración, autor/fechas, versión optimista del borrador, counts,
hash, matriz de filas congelada y manifiesto. Estados: `DRAFT` y `GENERATED`.
`MLDatasetPatient` enlaza paciente/clase/local_id; restricciones únicas por
(dataset,paciente) y (dataset,local_id). **La clase no se escribe en Paciente.**
`MLDatasetSample` enlaza muestra y caracterización exacta (nullable para
exclusiones), alias, inclusión/motivo y snapshot de provenance; único por
(dataset,muestra). FKs a fuentes/pacientes usan PROTECT.

Migración **0014_nuclear_dataset_snapshots**: crea sólo esas tres tablas y sus
restricciones/relaciones. Se aplicó después de verificar el backup; no modifica
columnas científicas existentes. No hay deriva de modelos pendiente.

## Contrato de selección y reproducibilidad

1. Usuario guarda explícitamente configuración y membresías; no autosave por tecla.
2. Un borrador puede estar incompleto; preview exige pacientes y clase no vacía
   para cada seleccionado. Generación además exige al menos una fila exportable.
3. Iniciales son búsqueda, no identidad. PatientLookup exige selección explícita,
   incluso con iniciales duplicadas. Relaciones usan PK/FK reales, scope institucional.
4. Clases son textos arbitrarios definidos por el investigador, máximo 100
   caracteres. No se infieren por nombre, iniciales, archivo o identificador.
   No se implementa asignación masiva opcional en esta primera versión.
5. Se elige exactamente **2.1 o 2.2**. No se admite 2.0 ni fallback de versión.
6. Para cada muestra SALIVA se examina su resultado de segmentación más reciente
   por PK. Debe estar COMPLETADO y tener resultado normalizado. Se resuelve su
   efectiva mediante el resolver existente: última VALIDADA, o base automática;
   una base MANUAL sin VALIDADA no califica. BORRADOR nunca es fuente efectiva.
7. Se elige la caracterización guardada más reciente de la versión exacta que
   coincida con fuente/revisión efectiva y, cuando está presente, con el hash
   de la segmentación efectiva. Empates: created_at y PK descendentes.
8. Automáticas antiguas sin hash verificable se excluyen `SOURCE_UNVERIFIABLE`;
   no se asume que una base mutable conserva el contenido medido. VALIDADA 2.1
   puede identificarse por revisión persistida; siempre se guarda además SHA-256
   del JSON completo de caracterización. No se compara con la calibración actual.
9. Preview calcula counts, balance, exclusiones, primeras diez filas y hash, sin
   persistir datasets generados ni nuevas métricas. Requiere confirmación explícita.
10. Generación es `transaction.atomic()`: actualización condicional de la versión
    DRAFT (también obtiene bloqueo de escritura SQLite), nueva lectura/verificación
    de membresías/fuentes/filtros y comparación con `preview_hash`. Cambio: 409
    `PREVIEW_CHANGED` o `DATASET_CHANGED`; se revierte íntegramente y se requiere
    nueva preview. Un fallo al guardar referencias revierte todo.
11. GENERATED rechaza modificación y regeneración por API, y `MLDataset.save()`
    rechaza guardar encima de un generado. No hay endpoint/UI de eliminación.
    Nuevas caracterizaciones posteriores no sustituyen las filas exportadas.
    Las restricciones son de aplicación/ORM; no se pretende proteger contra un
    administrador que edite directamente SQLite mediante SQL.

El hash es SHA-256 del JSON UTF-8 canónico (`sort_keys`, separadores compactos,
sin NaN): schema, configuración, membresías/clases, fuentes exactas y sus hashes,
filas, exclusiones y resumen. No incluye nombre/descripción ni fechas volátiles
para distinguir contenido científico de presentación. El dataset sí conserva
sus fechas/autor. Preview repetida con las mismas fuentes/configuración produce
el mismo hash.

Consultas agrupadas mediante select_related/prefetch_related: no una consulta
por muestra. Listado paginado a 20 sin cargar snapshots completos. Generación
síncrona: límite de 500 pacientes y 100000 filas; sin Celery, Redis ni trabajos
asíncronos. No se ha medido rendimiento de cohortes grandes reales.

## Granularidad y política de calidad

Cada núcleo con MN asociados produce una fila por **nucleus_id persistido**;
con cero MN produce una fila con MN/relaciones vacías. Ejemplo probado:
0 MN + 1 MN + 3 MN = **5 filas**, no producto cartesiano.

Se incluyen núcleos de `cells[].nuclei` y núcleos en `unassociated.nuclei` y
`ambiguous.nuclei`; estos últimos conservan una fila sin relación MN. No se
inventan asociaciones para MN sin nucleus_id. Se rechazan IDs nucleares/MN
duplicados dentro de las relaciones y enlaces a un núcleo ajeno a su célula.
Por tanto el dataset no cuenta todos los MN de una imagen: cuenta asociaciones
persistidas exportables. `Tiene_MN` significa **tiene asociación**, no ausencia
histológica de MN. Se debe revisar esta política de inclusión según el estudio.

Default: `validated_only=true`. La alternativa permite efectiva automática
verificable. Pacientes, casos, análisis y muestras archivados se excluyen; no hay
opción de incluirlos. Relaciones paciente/caso inconsistentes se excluyen.
Sólo se enumeran muestras SALIVA, sin mezclar o reinterpretar SANGRE.

## Mapeo del Excel de referencia

Rutas bajo `ResultadoCaracterizacion.resultado_json`. En la tabla:
**N** = `cells[].nuclei[].metrics` (o métricas de núcleos no asociados/ambiguos),
**M** = `cells[].micronuclei[].metrics`, asociado por `nucleus_id` persistido.
Las columnas referidas a identidad son metadatos del dataset, no métricas.

| Columna de referencia | Campo SICAM / nivel | Versiones | Unidad | Exportación | Estado/notas |
|---|---|---|---|---|---|
| ID_paciente | membresía → alias | 2.1/2.2 | identificador | ID_paciente | AVAILABLE; P001, no PK clínico |
| ID_foto | muestra → alias | 2.1/2.2 | identificador | ID_foto | AVAILABLE; P001_IMG001 |
| Nucleo | núcleo.id → alias | 2.1/2.2 | identificador | Nucleo | AVAILABLE; P001_IMG001_N001 |
| MN | micronúcleo.id + nucleus_id → alias | 2.1/2.2 | identificador | MN | AVAILABLE; vacío si no hay relación |
| Clase | MLDatasetPatient.class_label | todas | etiqueta | Clase | AVAILABLE; explícita, no diagnóstico inferido |
| Area_px | N.area_px2 | 2.1/2.2 | px² | Area_px2 | AVAILABLE; nombre de unidad corregido explícitamente |
| Perimetro_px | N.perimeter_px | 2.1/2.2 | px | Perimetro_px | AVAILABLE |
| Elipticidad | — | — | — | — | NOT_AVAILABLE_IN_SICAM; no sustituir por excentricidad |
| Excentricidad | N.eccentricity | 2.1/2.2 | adimensional | Excentricidad | AVAILABLE |
| Circularidad | N.circularity | 2.1/2.2 | adimensional | Circularidad | AVAILABLE |
| Solidez | — | — | — | — | NOT_AVAILABLE_IN_SICAM |
| Intensidad_media_gris | N.mean_gray_intensity | 2.1/2.2 | escala gris | Intensidad_media_gris | AVAILABLE |
| Desv_std_intensidad | N.std_gray_intensity | 2.1/2.2 | escala gris | Desv_std_intensidad | AVAILABLE |
| GLCM_Contraste | N.texture.contrast | 2.1/2.2 | textura píxel | GLCM_Contraste | AVAILABLE |
| GLCM_Homogeneidad | N.texture.homogeneity | 2.1/2.2 | textura píxel | GLCM_Homogeneidad | AVAILABLE |
| GLCM_Energia | N.texture.energy | 2.1/2.2 | textura píxel | GLCM_Energia | AVAILABLE |
| GLCM_Correlacion | N.texture.correlation | 2.1/2.2 | textura píxel | GLCM_Correlacion | AVAILABLE |
| Relacion_Proporcion_area_MN_sobre_nucleo | M.area_fraction_to_nucleus / relación | 2.1/2.2 | adimensional | Relacion_area_MN_nucleo | AVAILABLE; copiar valor guardado |
| Relacion_Proporcion_perimetro_MN_sobre_nucleo | — | — | — | — | NOT_AVAILABLE_IN_SICAM; no dividir perímetros en el exportador |
| Relacion_Distancia_borde_MN_nucleo_px | — | — | px | — | NOT_AVAILABLE_IN_SICAM; no es la distancia almacenada |

Variables adicionales admitidas, con semántica explícita:

| Exportación | Ruta/nivel | Versiones | Unidad |
|---|---|---|---|
| Area_um2 | N.area_um2 | 2.2 compatible | µm² |
| Perimetro_um | N.perimeter_um | 2.2 compatible | µm |
| Distancia_centroides_MN_nucleo_px | M.distance_to_nucleus_px / relación | 2.1/2.2 | px, centroide a centroide |
| Distancia_centroides_MN_nucleo_um | M.distance_to_nucleus_um / relación | 2.2 compatible | µm, centroide a centroide |
| MN_Area_px2 / MN_Area_um2 | M.area_px2 / M.area_um2 | 2.1/2.2; µm² sólo 2.2 | px² / µm² |
| MN_Perimetro_px / MN_Perimetro_um | M.perimeter_px / M.perimeter_um | 2.1/2.2; µm sólo 2.2 | px / µm |
| MN_Excentricidad / MN_Circularidad | M.eccentricity / M.circularity | 2.1/2.2 | adimensional |
| MN_Intensidad_media_gris / MN_Desv_std_intensidad | M.mean_gray_intensity / M.std_gray_intensity | 2.1/2.2 | escala gris |
| MN_GLCM_Contraste / MN_GLCM_Homogeneidad | M.texture.contrast / M.texture.homogeneity | 2.1/2.2 | textura píxel |
| MN_GLCM_Energia / MN_GLCM_Correlacion | M.texture.energy / M.texture.correlation | 2.1/2.2 | textura píxel |
| Tiene_MN | presencia de relación persistida | 2.1/2.2 | booleano, 0/1 en tabla |

No se añade cálculo de entropía, solidez, elipticidad, índices celulares ni
normalización al pipeline. La selección de variables es una selección de
columnas almacenadas, no selección estadística de features.

## Unidades y calibración

- PIXELS: valores de píxel y variables adimensionales/intensidad/textura guardadas.
- PHYSICAL: sustituye columnas dimensionales por sus equivalentes físicos guardados.
- BOTH: ambas representaciones; exige disponibilidad física igual que PHYSICAL.
- 2.1 sólo PIXELS; 2.2 admite los tres modos.
- Para PHYSICAL/BOTH el snapshot debe declarar physical_units_available y estado
  COMPATIBLE o COMPATIBLE_PROVISIONAL. Cada núcleo necesita area_um2 no nula;
  además deben existir valores de las columnas físicas seleccionadas, salvo
  campos MN de una fila sin MN. Relaciones con valores físicos faltantes se
  excluyen y cuentan separadamente; no se mezclan medidas físicas ausentes.
- En PIXELS, métricas científicas nulas permanecen nulas, sin imputación.
- PROVISIONAL se incluye con count, advertencia antes de confirmar y manifiesto.
  No equivale a metrología definitiva.
- Se conserva el snapshot físico original; cambiar la Calibration actual no
  convierte unidades ni invalida silenciosamente medidas ya guardadas.
- GLCM sigue en dominio píxel (metodología persistida en cada fuente):
  `GLCM_PHYSICAL_DISTANCE_NORMALIZATION = PENDING`.

## API, permisos y privacidad

API `/api/datasets/`: GET listado, POST crear; `/{uuid}/`: GET detalle y PUT
borrador completo con `version`. Acciones: `/options/`, `/{uuid}/preview/`,
`/{uuid}/generate/`, `/{uuid}/download/csv/`, `/xlsx/`, `/manifest/`.
Generate exige `{version, preview_hash, confirm: true}`. No DELETE/PATCH de
snapshots. No se crean datasets mediante GET.

ADMIN/OPERATOR crean/guardan/generan en su institución. REVIEWER consulta,
preview y descarga, sin modificación. SUPERUSER conserva alcance global y debe
seleccionar institución para crear. Se reutilizan OperationalPermission/scoped;
la institución y todas las membresías se validan de nuevo en servidor. Un cambio
posterior de institución del paciente no expone su identidad por una membresía
antigua ni permite generar con ella.

UI autorizada: identidad mínima del PatientLookup. Exportaciones: aliases
locales, no nombre, apellido, email, teléfono, DOB, identificadores externos ni
nombres de archivos. FK internos de pacientes/muestras se conservan sólo en el
snapshot interno; manifiesto público incluye IDs de caracterización/revisión y
fuentes/hashes necesarios para auditoría, sin PII clínica. Nombre y clases son
texto del investigador: éste debe evitar introducir PII en campos libres.

Aliases deterministas: pacientes por PK ascendente, imágenes por paciente/PK;
núcleos y MN por IDs persistidos ordenados como texto. Incluye aliases para
muestras excluidas, por lo que puede haber huecos en la tabla exportada. Son
estables dentro del snapshot, no identificadores globales entre datasets.

## Preview, exclusiones y manifiesto

Preview: pacientes/clases, imágenes elegibles/excluidas, filas, núcleos,
asociaciones MN, versión, unidades, política de validación, counts provisionales,
balance por clase (pacientes/imágenes/filas), elegibilidad por paciente, columnas
y motivos. No se persiste su matriz hasta Generate.

Códigos: ARCHIVED, NO_CHARACTERIZATION, CHARACTERIZATION_VERSION_MISMATCH,
SEGMENTATION_NOT_VALIDATED, NO_EFFECTIVE_SEGMENTATION, NO_PHYSICAL_VALUES,
CALIBRATION_INCOMPATIBLE, SOURCE_CHANGED, SOURCE_UNVERIFIABLE,
INVALID_CHARACTERIZATION, NO_NUCLEI, RELATIONSHIP_MISMATCH.
SANGRE no se enumera al fijar SALIVA; no se mezcla como exclusión de una cohorte
SALIVA. Las exclusiones de relaciones físicas parciales se distinguen de
imágenes excluidas completas (`excluded_rows` frente a `excluded_samples`).

Manifiesto: UUID/nombre/schema, autor/institución y fechas, tipo/grano, counts y
balance, versión/unidades/features/filtros, fuentes exactas y hashes del JSON,
hash de segmentación efectiva guardado y verificado, contexto físico permitido,
resumen de estados de calibración y count PROVISIONAL, exclusiones y hash de
contenido. Guarda `split_group=patient`, `split_applied=false` y la advertencia:
**Las particiones de entrenamiento/validación/prueba deben realizarse por
paciente, no por fila, núcleo ni imagen.** No se ejecutan particiones.

## CSV y Excel

CSV UTF-8, coma, punto decimal, filas/columnas estables y nulos como celda vacía.
Columnas base: ID_paciente, ID_foto, Nucleo, MN, Clase, Tiene_MN; después features
en orden del catálogo, independientemente del orden de clicks.

XLSX: hojas Datos, Pacientes, Exclusiones y Manifiesto. Datos contiene las mismas
filas/columnas/valores que CSV; numéricos como celdas numéricas, strings inline,
sin fórmulas. Primera fila inmovilizada, filtros y anchos de 24 caracteres.
Manifiesto se aplana por rutas para no poner arrays largos en una única celda.
Los textos que comienzan (tras espacios) con =,+,-,@ se prefijan con apóstrofo
en ambas tablas CSV/XLSX para evitar interpretación como fórmula. No se altera
el snapshot/clase almacenado ni los valores numéricos. Se rechazan caracteres de
texto incompatibles con XML al guardar el borrador.

## Backup, baseline y limitación de reanudación

Se creó y verificó un backup SQLite consistente, conteos y manifiesto de hashes
media en `/tmp/sicam18ub_backup_20261027/` **antes de migrar**. El historial de
herramientas registra integrity_check ok y FK sin infracciones. La migración
0014 se aplicó correctamente en esa ejecución.

Al reanudar el 28 de octubre, esos artefactos temporales y los logs previos ya no
estaban disponibles. **No se presenta el backup nuevo como premigración ni se
puede repetir la comparación de hashes contra el backup perdido.** Se creó un
backup nuevo, consistente y verificado, **POST_MIGRATION_0014**, en
`/tmp/sicam18ub_backup_20261028/`, con db.sqlite3, counts.json,
media_manifest.json y manifest.json (SHA-256). Una restauración desde ese backup
conserva el esquema 0014. No se ha restaurado ni sobrescrito la BD de trabajo.

Estado real al retomar: instituciones 1, usuarios Django 4, perfiles de usuario 3, pacientes 10,
casos 10, análisis 10, SALIVA 67, SANGRE 2, AcquisitionSeries 4,
AcquisitionProfile 3, Calibration 3, Characterization 27 (2.0: 2; 2.1: 21;
2.2: 4), LifecycleEvents 53; media 95 archivos. Nuevas tablas Dataset: **0/0/0**.
Estos counts concuerdan con lo disponible del precheck; no se ejecuta importación
ni generación real. Los hashes completos antes/después se verifican para el
tramo reanudado y se reportan con ese alcance, no para el backup perdido.

Characterization 24 conserva versión 2.2, muestra 66,
COMPATIBLE_PROVISIONAL y fingerprint
`c80144bf271ed7e977040a69a288a14c44efc4eb93f311a07b95d320c0526b1e`.
La calibración `CAL-OPTIKA-40X-PROVISIONAL-001` conserva PROVISIONAL y escalas
sx `0.055233934048`, sy `0.055010060892`.

## Validaciones

Pruebas aisladas, sin acceso de escritura a media/BD científicas:

- Backend dirigido: **15 passed**. Row grain 0/1/3 → 5; clases explícitas;
  PIXELS/PHYSICAL/BOTH, null físico parcial, PROVISIONAL, versión exacta,
  VALIDADA/AUTOMATICO/BORRADOR, fuente cambiada, transacción/rollback,
  concurrencia optimista, inmutabilidad, nueva caracterización posterior,
  permisos y aislamiento institucional, consistencia CSV/XLSX, privacidad,
  inyección de fórmulas, metadatos OPTIONS y ausencia de N+1.
- Frontend dirigido: **8 passed** en la ejecución anterior; se incluyen ahora
  dentro de la regresión completa. Listado, borrador, PatientLookup/PK e iniciales
  duplicadas, clases, versión/unidades/features, preview/exclusiones/PROVISIONAL,
  confirmación, snapshot inmutable, descargas visibles y REVIEWER.
- Backend completo una vez: **486 passed, 2 skipped**, 36 avisos previos de
  CheckConstraint.check. Frontend completo una vez: 218 pass y una expectativa
  histórica de TopBar desactualizada (4 secciones antes, 5 ahora). Se actualizó
  esa aserción para incluir Conjuntos de datos y se repitió sólo la suite afectada:
  **59 passed**; total final de cobertura de las suites: **219 passed**, sin fallos
  pendientes. No se repitió la regresión completa. Build una vez: **PASS**.
- Django check sin incidencias; `makemigrations --check --dry-run`: No changes
  detected. `pip check`: No broken requirements found; aviso de caché no
  escribible sin impacto ni instalaciones.
- En el tramo reanudado, hashes de todas las **33 tablas** y del archivo
  SQLite idénticos; nombres/hashes de **95 archivos** de media idénticos;
  Characterization 24 y Calibration 1 con hashes de fila completos idénticos;
  LifecycleEvents **53 → 53**, Dataset/Patient/Sample **0/0/0**. SQLite
  integrity_check = ok, foreign_key_check = []. El backup postmigración se
  verificó además comparando los hashes lógicos de todas sus tablas con la BD
  fuente (la API SQLite backup no promete igualdad byte a byte del archivo).

Logs y snapshots de la reanudación: `/tmp/sicam18ub/`. El contenido de /tmp es
temporal; trasladar los respaldos a almacenamiento durable según la política
operativa antes de depender de ellos como recuperación de largo plazo.

## Checklist visual A–R

- [ ] A. Abrir Conjuntos de datos.
- [ ] B. Crear un borrador TEST.
- [ ] C. Buscar y elegir pacientes TEST por iniciales.
- [ ] D. Asignar dos clases explícitas diferentes.
- [ ] E. Comprobar counts y balance por clase.
- [ ] F. Elegir versión exacta de Characterization.
- [ ] G. Seleccionar PIXELS.
- [ ] H. Elegir variables soportadas.
- [ ] I. Guardar y obtener vista previa.
- [ ] J. Inspeccionar las exclusiones.
- [ ] K. Probar PHYSICAL/BOTH en 2.2 y su cambio de elegibilidad.
- [ ] L. Ver advertencia de calibración PROVISIONAL.
- [ ] M. Generar con datos TEST y confirmación explícita.
- [ ] N. Comprobar inmutabilidad y nueva definición para otro experimento.
- [ ] O. Descargar CSV.
- [ ] P. Descargar Excel y abrirlo en Excel/LibreOffice.
- [ ] Q. Comparar filas, columnas, nulos y valores científicos.
- [ ] R. Comprobar ausencia de PII y advertencia de split por paciente.

No se automatizó una creación real para esta aceptación. La apertura visual del
XLSX y del módulo en navegador queda pendiente del investigador.

## Pendientes

Se conservan IMPORTANT_PENDING_18S_A2,
ACQUISITION_SERIES_REASSIGNMENT_POLICY, RETIRED_RECALCULATION_POLICY,
DURABLE_UPLOAD_IDEMPOTENCY, GLCM_PHYSICAL_DISTANCE_NORMALIZATION,
MANUAL_VISUAL_REVIEW_18S_D, PRODUCTION_MEDIA_ACCESS_CONTROL,
DJANGO_CHECKCONSTRAINT_CONDITION_MIGRATION y ORIGINAL_FILENAME_DISPLAY.

Se añaden `ML_DATASET_LIFECYCLE_POLICY = PENDING` y
`DATASET_BLOOD_FEATURE_EXPORT = FUTURE`. No se implementaron splits, k-fold,
balanceo, SMOTE, normalización/selección estadística de variables, entrenamiento,
ZIP/imágenes/máscaras ni clonación/versionado de datasets. 18U-C requiere
instrucción posterior. Antes del primer dataset real, completar A–R con TEST y
revisar clases, política de núcleos sin asociación y fuentes/exclusiones.

## Estado Git y cierre

`git diff --check` PASS. Diff de archivos ya seguidos: 6 archivos, 20 inserciones,
6 eliminaciones, además de los archivos nuevos de modelos/servicio/API,
migración, UI, tests y este documento. Estado completo y stat en
`/tmp/sicam18ub/git_status_final.txt` y `git_diff_stat.txt`. No commit ni push.

Implementación y pruebas listas para revisión visual. Se mantiene pendiente la
aceptación de la limitación de evidencia del baseline inicial: el backup y los
hashes premigración temporales no están disponibles para una nueva comparación.
No se interpreta esa ausencia como modificación de datos científicos, pero
no se declara una comparación de hashes que no se pudo repetir.

SPRINT 18U-B = READY_WITH_DATASET_ISSUES_PENDING

## 18U-B.1 — CLASS INTEGRITY AND ACCEPTANCE REFINEMENT

Refinamiento del 28/10/2026 sobre 18U-B sin commit. Rama `master`, HEAD
`cc29d5c2c9a86aa04d997d25115a508cee193030`. El árbol inicial ya contenía seis
archivos modificados de integración y ocho entradas nuevas (incluido el
directorio de servicios); se preservan juntos. No hay commit ni push.

### Clases y compatibilidad histórica

La inspección encontró clases lógicamente duplicadas `Clase 2` / `clase 2`.
Ahora el usuario crea **Clases del conjunto** una vez y selecciona una opción
por paciente. Se conservan nombres arbitrarios sin validación médica.
`MLDataset.config.classes` guarda el catálogo; `MLDatasetPatient.class_label`
conserva la asignación. No hay entidad nueva ni migración B.1.

La autoridad backend usa `label.strip().casefold()` como clave de comparación;
el display conserva la primera etiqueta aceptada, con extremos recortados.
Rechaza vacías, sólo espacios y duplicadas con «Ya existe una clase equivalente
con ese nombre.». Las asignaciones equivalentes se resuelven al display del
catálogo; las ajenas se rechazan. La UI rechaza duplicados mediante trim y
comparación en minúsculas, y el backend aplica adicionalmente casefold Unicode.
Un borrador puede guardar pacientes sin asignar, pero preview/generación exige
exactamente una clase válida para cada paciente. No había asignación masiva
en 18U-B; continúa fuera del alcance opcional de este refinamiento.

Los borradores anteriores sin catálogo se presentan con un catálogo derivado
para revisión y guardado explícito. No se actualizan en segundo plano.
**Los GENERATED existentes no se normalizan ni se reescriben**, incluyendo
sus clases, filas, hash, configuración y manifiesto. Las respuestas de consulta
pueden derivar contadores faltantes del resumen congelado de pacientes, sin
persistirlos. La lista extrae sólo ese pequeño resumen mediante JSONField;
no carga la matriz científica completa. Los manifiestos históricos descargados
siguen siendo exactamente los originales.

### Conteos, advertencia y exportación

Nuevos resúmenes/manifiestos incluyen:

- `selected_patient_count`: miembros explícitos del conjunto.
- `included_patient_count`: miembros con al menos una fila exportada.
- `zero_row_patient_count`: seleccionados con cero filas tras filtros/exclusiones.
- Por clase: `selected_patients`, `included_patients`, `row_count`.

Se retienen los campos antiguos como alias compatibles. El hash continúa usando
el mismo algoritmo sobre el snapshot; los nuevos metadatos forman parte de los
snapshots futuros. No se cambia extracción, grano, fingerprints de fuentes ni
semántica `NUCLEUS_MN_RELATION`.

La UI distingue los tres conteos y la distribución por clase. Una advertencia
visible indica cuántos seleccionados no aportan datos elegibles y que permanecen
para auditoría. La confirmación explícita de fuentes, clases, exclusiones y
advertencias sigue siendo obligatoria antes de generar; cero filas totales sigue
impidiendo la generación. No se elimina silenciosamente ningún miembro.

`Pacientes` XLSX contiene `ID_paciente`, `Clase`, `Muestras_incluidas`, `Filas`,
`Estado_inclusion`: `INCLUIDO` o `SIN_DATOS_ELEGIBLES`. Los pacientes de cero filas
permanecen allí, y no aparecen en `Datos`. Ninguna identidad clínica se exporta.
Las cuatro hojas tienen anchos por cabecera/contenido típico (hasta 200 filas
para estimación), mínimo 12 y máximo 48; hashes quedan acotados. Cabeceras en
negrita, primera fila congelada, autofiltro y celdas numéricas conservadas.
`Datos` conserva columnas, valores, orden y nulos idénticos entre CSV y XLSX.

### Presentación

Enums internos/API/manifiesto continúan `PIXELS` / `PHYSICAL` / `BOTH`;
formulario, lista, detalle y preview muestran **Píxeles / Físicas / Ambas**.
Fechas de lista y detalle usan la convención existente
`toLocaleString('es-MX', {dateStyle:'short', timeStyle:'short'})`, zona local del
navegador; API y manifiesto conservan ISO.

Las variables seleccionadas se muestran con etiquetas humanas, entidad
núcleo/micronúcleo y unidades px²/µm² o px/µm cuando corresponden; intensidad,
GLCM y métricas adimensionales no reciben unidades físicas inventadas.
Los códigos y nombres de columnas de exportación permanecen estables.
Elipticidad, Solidez, proporción de perímetros y distancia entre bordes siguen
explícitamente no disponibles. Distancia entre centroides no se presenta como
si fuera distancia entre bordes.

### Archivos de B.1

- `api/services/datasets/classes.py` (nuevo).
- `api/dataset_views.py`, `api/services/datasets/builder.py`,
  `api/services/datasets/xlsx.py`, `api/test_datasets.py`.
- `Frontend/src/views/DatasetsView.vue`, `Frontend/tests/datasets.test.mjs`.
- Este documento.

Las rutas backend anteriores son relativas a `apps/web/Backend`; las frontend
a `apps/web`. El resto del árbol inicial 18U-B se conserva.

### Evidencia de aceptación B.1

Pruebas dirigidas: **18 backend PASS**, **10 frontend PASS**. Cubren catálogo,
trim/casefold, duplicados, asignación ajena, pacientes sin filas, manifiesto,
lectura histórica, inmutabilidad, paridad CSV/XLSX, ausencia de PII, anchos,
negritas, autofiltro/congelación, selector, advertencia, unidades, fechas y
etiquetas humanas.

Frontend completo ejecutado una vez sobre los diez archivos de tests, cada uno
en proceso separado con `node --test --test-isolation=none tests/<archivo>.test.mjs`:
**221 passed, 0 failed, 0 skipped**. Esta forma conserva aislamiento entre archivos
y expone el conteo individual; el runner Node/Vite con aislamiento por defecto
en este entorno sólo reportaba el contenedor del archivo.
`npm run build` ejecutado una vez: **PASS**.
`manage.py check`: sin incidencias. `makemigrations --check --dry-run`: sin cambios.
`pip check`: sin dependencias rotas (aviso de caché no escribible, sin impacto).
No se requiere aplicar ninguna migración B.1 ni modificar dependencias.

Base real inspeccionada sólo en lectura. El conjunto existente se llama
`prueba` (no se infiere ni se añade una marca TEST): **3 seleccionados,
2 incluidos, 1 sin datos elegibles**. Su distribución histórica permanece:

| Clase histórica | Seleccionados | Incluidos | Filas |
|---|---:|---:|---:|
| Clase 1 | 1 | 1 | 21 |
| Clase 2 | 1 | 0 | 0 |
| clase 2 | 1 | 1 | 17 |

Comparación antes/después por SHA-256 de todas las filas de cada tabla y de los
nombres/contenidos de media: sin cambios. SQLite `integrity_check = ok`,
`foreign_key_check = []`. **95 archivos media** intactos; LifecycleEvents
**53 → 53**; Characterization total **27 → 27**, incluida Characterization **24**
(2.2). Dataset/Patient/Sample **1/3/12 → 1/3/12**, incluido snapshot/manifiesto/hash
originales. Calibración `CAL-OPTIKA-40X-PROVISIONAL-001` intacta:
`PROVISIONAL`, sx `0.055233934048`, sy `0.055010060892`.

No se ejecutó segmentación ni Characterization sobre datos reales; no se tocó
AcquisitionSeries ni las fuentes científicas. Las pruebas usan base de tests y
fixtures sintéticas. No se implementa 18U-C.

Backend completo ejecutado una vez, después de estabilizar los cambios:
**489 passed, 2 skipped**, 36 avisos previos de deprecación Django, cero fallos.
Logs locales de verificación: `/tmp/sicam_b1_targeted_backend.log`,
`/tmp/sicam_b1_full_backend.log`, `/tmp/sicam_b1_full_frontend.log`,
`/tmp/sicam_b1_build.log`; evidencia de comparación de integridad en
`/tmp/sicam_b1_before.json` y script de lectura `/tmp/sicam_b1_integrity.py`.

`git diff --check`: PASS. `git diff --stat` conserva las seis modificaciones
rastreadas de 18U-B: **20 inserciones, 6 eliminaciones**; por diseño Git no
incluye los archivos todavía no rastreados de Dataset Builder en ese resumen.
`git status --short` conserva las mismas entradas iniciales más el archivo
`classes.py` dentro del directorio de servicios nuevo. No se añadió nada al
índice, ni se hizo commit/push.

Sin pendientes de implementación o pruebas. Recomendación: aceptación manual
final creando un **nuevo** borrador, definiendo clases, comprobando rechazo de
variantes de mayúsculas/espacios, seleccionando un paciente sin datos y
confirmando la advertencia; después revisar CSV/XLSX/manifiesto. Mantener
`prueba` intacto como evidencia histórica. Esta generación real manual no se
ejecuta automáticamente en este sprint.

SPRINT 18U-B.1 = READY_FOR_FINAL_DATASET_ACCEPTANCE

## 18U-B.2 — EFFECTIVE CLASS VALIDATION AND EXCLUSION SEMANTICS

Refinamiento del 28/10/2026 sobre `master`, HEAD inicial
`e10fb7dd1ba4f78cf780964853f5c8b68d2c249f`. El árbol inicial estaba **limpio**:
B/B.1 y la corrección de autenticación ya estaban en los commits anteriores.
Se preservan esas implementaciones; no se toca ningún archivo de autenticación.
Sin commit ni push durante B.2.

### Clases definidas y efectivas

La aceptación manual encontró `Prueba 3` con dos clases definidas, pero sólo
una representada: Clase A, 3 seleccionados / 2 incluidos / 38 filas; Clase B,
3 seleccionados / 0 incluidos / 0 filas. El aviso individual por pacientes sin
filas no impedía generar un conjunto con una sola clase efectiva.

**Clase efectiva**: al menos un paciente incluido **y** una fila exportada,
tras todos los filtros. Se inicializa el balance con **todo** el catálogo del
borrador, incluso clases todavía sin pacientes asignados. Preview/snapshot y
manifiestos futuros incluyen `defined_class_count`, `effective_class_count`,
`empty_class_count`, además de los conteos por clase y paciente de B.1.

La generación supervisada actual exige al menos **dos clases definidas y dos
efectivas**. Una sola clase definida se bloquea aunque tenga filas. Dos definidas
con sólo una efectiva también se bloquean. Tres definidas con dos efectivas y
una vacía pueden generar: la clase vacía permanece visible y documentada.
No se eliminan clases ni pacientes silenciosamente.

Una clase vacía es una advertencia fuerte en una tabla de preview con clase,
pacientes seleccionados, pacientes incluidos, filas y estado `OK` / `SIN DATOS
ELEGIBLES`. Se muestran los tres nuevos contadores. Si faltan clases efectivas,
se desactiva Generar y se explica por qué. El backend es la autoridad: dentro de
la transacción de generación reconstruye las fuentes/conteos, compara el hash
de preview y valida las clases antes de persistir. Una preview obsoleta conserva
el conflicto 409; un estado actual inválido devuelve 400 con mensaje claro y
filas por clase. Cualquier fallo revierte versión, muestras y snapshot.

Un **paciente** sin filas sigue siendo advertencia y permanece en la membresía,
snapshot y hoja Pacientes. No bloquea si quedan al menos dos clases efectivas.
`ML_ONE_CLASS_DATASET_SUPPORT = FUTURE`; no se añade modo one-class ni se inicia
18U-C. Se conservan los pendientes previos, incluida normalización de distancia
física GLCM, splits, entrenamiento y exportaciones futuras fuera de este sprint.

### Auditoría de las tres exclusiones de segmentación (sólo lectura)

Los mismos tres alias aparecen en `prueba2` y `Prueba 3`, ambos con
`validated_only=false`. Se trazaron desde `snapshot.sources.sample_id` al
resultado SALIVA más reciente y al resolver efectivo actual, sin ejecutar
Characterization ni modificar fuentes:

| Alias local | Muestra | Resultado | Base | Estado resultado | Revisión | Efectiva | Caracterizaciones |
|---|---:|---:|---|---|---|---|---:|
| P004_IMG003 | 56 | 20 | MANUAL presente | COMPLETADO | 20, nº 1, BORRADOR | MANUAL (base) | 0 |
| P005_IMG002 | 58 | 22 | MANUAL presente | COMPLETADO | 21, nº 1, BORRADOR | MANUAL (base) | 0 |
| P005_IMG006 | 62 | 26 | MANUAL presente | COMPLETADO | 25, nº 1, BORRADOR | MANUAL (base) | 0 |

No tienen revisión VALIDADA ni base automática. El BORRADOR no es efectivo;
lo es la base MANUAL. La condición anterior era:
`fuente == MANUAL OR (validated_only AND fuente != VALIDADA)`.
Por ello se aplicaba `SEGMENTATION_NOT_VALIDATED` a MANUAL incondicionalmente,
aunque la política del dataset no exigiera VALIDADA. Era una condición incorrecta
del filtro y una explicación engañosa, **sin filas recuperables en estos tres
casos**, porque tampoco existen caracterizaciones guardadas.

B.2 elimina esa exclusión incondicional. Con `validated_only=false` la base
MANUAL pasa el filtro de segmentación y se evalúa la caracterización guardada;
en los tres casos auditados la causa correcta para nuevas previews es
`NO_CHARACTERIZATION`. No se inventan métricas ni se incorpora el BORRADOR.
Characterization continúa exigiendo validar una anotación MANUAL antes de
caracterizarla; su servicio y restricciones de fuentes no se modifican.

### Semántica del filtro y códigos

- `validated_only=true`: exige que la fuente efectiva provenga de una revisión
  VALIDADA; una base AUTOMATICO o MANUAL efectiva produce
  `SEGMENTATION_NOT_VALIDATED`.
- `validated_only=false`: admite la fuente efectiva existente sin exigir esa
  revisión; se siguen exigiendo caracterización persistida de versión/fuente
  exactas, provenance y el resto de criterios científicos.
- El resolver compartido conserva su contrato: última VALIDADA, o base
  MANUAL/AUTOMATICO; BORRADOR nunca se convierte en efectiva.
- Se comprueba el resultado **efectivo**, no la presencia de una base que una
  VALIDADA ya sustituyó. Una VALIDADA con snapshot válido puede usarse aunque
  la base no esté presente; sólo BORRADOR sin base da
  `NO_EFFECTIVE_SEGMENTATION`.

No se introduce un código nuevo. Definiciones de los códigos vigentes:

| Código | Condición |
|---|---|
| ARCHIVED | Paciente, caso, análisis o muestra archivados. |
| RELATIONSHIP_MISMATCH | La relación paciente/caso de la muestra es inconsistente. |
| NO_EFFECTIVE_SEGMENTATION | No hay resultado COMPLETADO o el resolver no proporciona contenido efectivo. Incluye ausencia de resultado y BORRADOR sin base/VALIDADA. |
| SEGMENTATION_NOT_VALIDATED | Sólo con `validated_only=true`: existe efectiva pero su fuente no es VALIDADA. Mensaje: «La política del conjunto exige una segmentación validada.». |
| NO_CHARACTERIZATION | No hay caracterización persistida para ese resultado. |
| CHARACTERIZATION_VERSION_MISMATCH | Hay caracterizaciones, pero ninguna de la versión solicitada. |
| SOURCE_CHANGED | Hay versión exacta, pero no coincide fuente/revisión/hash efectivo con la caracterización. |
| SOURCE_UNVERIFIABLE | Caracterización AUTOMATICO antigua sin hash efectivo persistido verificable. |
| NO_PHYSICAL_VALUES | Faltan valores físicos requeridos; puede excluir una muestra completa o relaciones concretas. |
| CALIBRATION_INCOMPATIBLE | Estado del snapshot físico fuera de COMPATIBLE / COMPATIBLE_PROVISIONAL. |
| INVALID_CHARACTERIZATION | Versión/tipo JSON, estructura, relaciones o valores numéricos inválidos. |
| NO_NUCLEI | La caracterización no aporta núcleos/relaciones exportables. |

`NO_EFFECTIVE_SEGMENTATION` muestra «No existe una segmentación efectiva
completa.». `NO_CHARACTERIZATION` mantiene «Sin caracterización guardada.».
Estos mensajes se aplican a nuevas previews/snapshots. Los códigos y textos
históricos permanecen exactamente como se generaron.

### Preservación y pruebas

Todos los GENERATED anteriores, incluido `Prueba 3` con una sola clase efectiva,
siguen siendo legibles y descargables. No se valida retrospectivamente su
aptitud ni se reescriben manifiestos, snapshots, filas, hashes o exclusiones.
No cambia extracción de variables, cálculos, unidades, calibración, GLCM,
asociaciones MN, IDs locales ni orden/valores/nulos de CSV/XLSX. El algoritmo de
hash y los fingerprints permanecen intactos; los nuevos contadores de validación
forman parte del snapshot de futuras generaciones.

Archivos B.2: `Backend/api/dataset_views.py`,
`Backend/api/services/datasets/builder.py`, `Backend/api/test_datasets.py`,
`Frontend/src/views/DatasetsView.vue`, `Frontend/tests/datasets.test.mjs`
(rutas relativas a `apps/web`) y este documento. Sin migración ni dependencias.

Pruebas dirigidas: **25 backend passed**, **13 frontend passed**. Incluyen los
casos de clases A–D solicitados; catálogo no asignado; un paciente sin filas con
dos clases efectivas; rechazo/rollback y preview concurrente; históricos con una
clase efectiva; VALIDADA, base AUTOMATICO con/sin política estricta, BORRADOR que
no sustituye a la base, MANUAL sin caracterización, ausencia de resultado,
BORRADOR sin base y VALIDADA sin base. La prueba existente CSV/XLSX verifica
paridad científica y privacidad; no se modifica el escritor de exportaciones.

### Resultado final B.2

- Backend completo una vez: **498 passed, 2 skipped**, cero fallos; 36 avisos
  previos de deprecación Django.
- Frontend completo una vez: **229 passed**, cero fallos, sobre los 11 archivos
  de tests, cada uno aislado con `node --test --test-isolation=none`.
- `npm run build` una vez: PASS.
- `manage.py check`: sin incidencias. `makemigrations --check --dry-run`: sin
  cambios. `pip check`: sin dependencias rotas (aviso de caché no escribible).
- Evaluación adicional de fuentes de `Prueba 3` **sólo en memoria**, sin guardar:
  2 clases definidas / 1 efectiva / 1 vacía; las tres muestras auditadas producen
  `NO_CHARACTERIZATION`; columnas y filas científicas idénticas a las históricas.
  Esto no sustituye el snapshot generado ni sus motivos de exclusión originales.
- SHA-256 antes/después de todas las filas de cada tabla real: sin cambios.
  SQLite `integrity_check = ok`, `foreign_key_check = []`. LifecycleEvents
  **53 → 53**, Dataset/Patient/Sample **3/15/60 → 3/15/60**, Characterization
  **27 → 27**, incluida la 24; calibraciones intactas. Los **95 archivos media**
  conservan nombres y hashes. Sin nueva generación real ni procesos científicos.
- `git diff --check`: PASS; seis archivos modificados B.2, ninguno sin rastrear.
  Sin staging, commit ni push. Código y configuración de autenticación intactos.

Logs locales: `/tmp/sicam_b2_targeted_backend.log`,
`/tmp/sicam_b2_targeted_frontend.log`, `/tmp/sicam_b2_full_backend.log`,
`/tmp/sicam_b2_full_frontend.log`, `/tmp/sicam_b2_build.log`. La comparación de
integridad usa el baseline de este sprint en `/tmp/sicam_b1_before.json` y el
script de lectura `/tmp/sicam_b1_integrity.py`.

Sin pendientes de implementación B.2. Para aceptación manual final crear un
**nuevo borrador**: comprobar bloqueo con una clase definida o una efectiva;
luego usar al menos dos efectivas, verificar la advertencia individual y/o una
tercera clase vacía, generar y comparar CSV/XLSX/manifiesto. No reutilizar ni
alterar los tres históricos para hacer esta validación. Se mantienen los
pendientes futuros documentados; `ML_ONE_CLASS_DATASET_SUPPORT = FUTURE`.

SPRINT 18U-B.2 = READY_FOR_FINAL_DATASET_ACCEPTANCE
