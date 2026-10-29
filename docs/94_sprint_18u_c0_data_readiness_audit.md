# Sprint 18U-C0 — Auditoría de disponibilidad para datasets reales

Fecha local: 2026-10-29, America/Mexico_City.

SPRINT 18U-C0 = READY_WITH_AUDIT_ISSUES_PENDING

Auditoría completada de todas las muestras SALIVA de LASAID. No se ejecutó
remediación. Pendientes de evidencia/decisión: correspondencia durable del alias
externo PAIR_008, reutilización de un dataset legacy sin catálogo de clases y
selección explícita de versión/política científica para el siguiente conjunto.
Estas limitaciones no impiden conocer la elegibilidad actual de las 67 muestras.

## Alcance y estado inicial

Rama `master`; HEAD `ed31864593a4ffac80f8d31ea8ee9c9f7f86b236`.
Working tree inicialmente limpio. Institución explícita `LASAID`, PK 1.
No se agregan funcionalidades, comandos productivos, endpoints, migraciones ni UI.
Único cambio versionable de este sprint: este documento.
Se preserva [Dataset Builder 18U-B/B.1/B.2](93_sprint_18u_b_dataset_builder.md).

## Procedimiento y semántica exacta

El adaptador temporal `/tmp/sicam18uc0/readiness.py` llama directamente a
`api.services.datasets.builder.build_snapshot`; no replica sus reglas.
Usa membresías sólo en memoria y la etiqueta técnica `AUDIT_UNCLASSIFIED` para
satisfacer el contrato del preview. No asigna clases científicas: esa etiqueta
no se persiste ni se usa en el reporte por clases. Sólo se agrupan clases cuando
ya están explícitamente almacenadas en un dataset real.

Se seleccionan **las 22 variables soportadas** del catálogo actual para los cuatro
modos, sin inventar métricas. La elegibilidad física depende también de esa
selección: aquí se exige toda la selección soportada, no sólo área. La comparación
con un preview debe usar exactamente versión, unidades, features y filtros iguales.

Se reutilizan también `resolve_effective_segmentation`, `relations`, `metric`,
`source_info`, `columns` y validación del catálogo de clases a través del builder.
No se llama a generación/persistencia de datasets ni a motores científicos.
El preview calcula filas en memoria; los artefactos sólo contienen conteos,
razones e identificadores internos, no valores científicos por núcleo.

Orden real de evaluación por muestra:

1. RELATIONSHIP_MISMATCH.
2. ARCHIVED: paciente, caso, análisis o muestra archivados.
3. NO_EFFECTIVE_SEGMENTATION: último resultado SALIVA ausente/incompleto o
   payload efectivo falso/vacío según el resolver actual.
4. SEGMENTATION_NOT_VALIDATED si el filtro exige VALIDADA.
5. NO_CHARACTERIZATION o CHARACTERIZATION_VERSION_MISMATCH en ese resultado.
6. SOURCE_CHANGED si ninguna caracterización de versión exacta coincide con
   fuente/revisión y hash efectivo almacenado cuando existe.
7. SOURCE_UNVERIFIABLE para automático sin hash verificable; validación del
   payload → INVALID_CHARACTERIZATION.
8. En PHYSICAL: NO_PHYSICAL_VALUES, CALIBRATION_INCOMPATIBLE y validación de
   campos físicos por fila. Las filas incompletas pueden excluirse parcialmente.
9. Validación de asociaciones; NO_NUCLEI si no hay filas exportables.

Los códigos primarios son los originales. Para categorías de lectura se mapean
SEGMENTATION_NOT_VALIDATED → NOT_VALIDATED y
CHARACTERIZATION_VERSION_MISMATCH → VERSION_MISMATCH; otros códigos conservan
su detalle aunque la categoría sea OTHER. READY sólo significa elegibilidad.

`all_exclusion_reasons` contiene todos los rechazos efectivamente devueltos por el
builder, incluidos parciales si los hubiera. El builder se detiene en el primer
bloqueo por muestra: no se inventan fallos posteriores. `context_gaps` informa
por separado ausencia de serie/calibración/versión y presencia de borrador;
**no son rechazos adicionales**. En esta BD no hubo filas excluidas parcialmente.

BORRADOR nunca efectivo. VALIDADA más reciente por número de revisión prevalece;
en ausencia de VALIDADA se usa base MANUAL/AUTOMATIC. AUTOMATICO no es VALIDADO.
PIXELS no consulta ni exige calibración/serie. PHYSICAL usa el snapshot físico
almacenado de Characterization, sin recalcular ni sustituirlo por calibración viva.

## Cobertura actual

Todos los identificadores Pxxx son aliases de auditoría, distintos de los aliases
locales de cada dataset. PK/sample/result/revision se incluyen sólo para auditoría
interna. No se publican nombres, iniciales, nacimiento, correo, teléfono,
identificadores hospitalarios/externos, basenames o rutas de imágenes.

| Métrica LASAID | Cantidad |
| --- | --- |
| Pacientes / con SALIVA / con SALIVA activa | 10 / 10 / 7 |
| SALIVA total / activa / excluida por archivo | 67 / 25 / 42 |
| SANGRE, OUT OF SCOPE | 2 |
| Efectiva VALIDADA / MANUAL / AUTOMATIC / NONE (activas) | 19 / 4 / 1 / 1 |
| Muestras activas con BORRADOR | 6 |
| Serie asignada / ausente (activas) | 7 / 18 |
| Calibración asociada / ausente (activas) | 7 / 18 |
| Asociadas PROVISIONAL / VALIDATED final / RETIRED | 7 / 0 / 0 |
| Sin Characterization: total / activas | 45 / 5 |

Las seis muestras con borrador son 42, 45, 56, 58, 62 y 63. Las dos primeras
conservan VALIDADA efectiva. No se equiparó tener borrador con estar validada.
Los 42 archivados no se suman a los 25 activos ni se proponen para restauración.
Hay tres calibraciones institucionales: 1 PROVISIONAL (ID 1), 2 RETIRED (IDs 3,5).
Ninguna VALIDATED. Las siete muestras asociadas usan la calibración 1.

### Characterization: registros frente a muestras

| Versión | Registros totales | Muestras totales | Registros en activas | Muestras activas |
| --- | --- | --- | --- | --- |
| 2.0 | 2 | 2 | 0 | 0 |
| 2.1 | 21 | 21 | 20 | 20 |
| 2.2 | 4 | 3 | 4 | 3 |

Las versiones se solapan por muestra; no sumar esas columnas como imágenes
únicas. Hay 22 muestras con alguna Characterization (20 activas). Muestra 41 tiene
dos registros 2.2; sólo se elige el más reciente compatible con su fuente efectiva.
Las tres muestras con 2.2 elegible son 41, 46 y 66; 66 usa base AUTOMATIC.

## Cuatro modos solicitados

Todos usan Characterization 2.2. Excluidas activas = 25 menos elegibles;
además se excluyen 42 archivadas en todos los modos.

| Modo | Unidades | Sólo VALIDADA | Pacientes elegibles | Muestras | Activas excluidas | Núcleos | Asociaciones MN | Filas | Físicas provisionales |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | PIXELS | True | 1 | 2 | 23 | 21 | 1 | 21 | N/A |
| B | PIXELS | False | 2 | 3 | 22 | 34 | 12 | 38 | N/A |
| C | PHYSICAL | True | 1 | 2 | 23 | 21 | 1 | 21 | 2 |
| D | PHYSICAL | False | 2 | 3 | 22 | 34 | 12 | 38 | 3 |

A/C: muestras 41 y 46, paciente P002. B/D: se añade 66, paciente P008.
Aceptar base efectiva añade exactamente **1 paciente y 1 muestra**, de origen
AUTOMATIC; ninguna de las cuatro bases MANUAL se vuelve elegible por ese cambio.

Todos los resultados físicos elegibles son PHYSICAL_TECHNICALLY_AVAILABLE y
PHYSICAL_PROVISIONAL; PHYSICAL_FINAL = 0. PHYSICAL_ELIGIBLE_PROVISIONAL = true
para esas muestras, sin convertir PROVISIONAL en exclusión ni aceptación final.

Las filas se obtienen de asociaciones persistidas: núcleo con 0 MN → 1 fila,
con N MN → N filas. No se usa producto cartesiano. Núcleos sin asociación celular
se conservan conforme al builder; MN sin asociación nuclear no inventa una fila.

### Rechazos primarios exactos

| Código | A | B | C | D |
| --- | --- | --- | --- | --- |
| ARCHIVED | 42 | 42 | 42 | 42 |
| CHARACTERIZATION_VERSION_MISMATCH | 17 | 17 | 17 | 17 |
| SEGMENTATION_NOT_VALIDATED | 5 | 0 | 5 | 0 |
| NO_CHARACTERIZATION | 0 | 4 | 0 | 4 |
| NO_EFFECTIVE_SEGMENTATION | 1 | 1 | 1 | 1 |

### Alternativa ya disponible 2.1 / PIXELS

Sin crear ni recalcular nada, el mismo builder con versión 2.1 admite **5 pacientes,
19 muestras, 95 núcleos, 21 asociaciones MN y 102 filas**. Igual total tanto con
VALIDADA obligatoria como permitiendo bases efectivas. Esto demuestra con datos
reales que PIXELS no necesita calibración: 14 de esas muestras carecen de serie.
En modo 2.1 relajado, 66 queda SOURCE_UNVERIFIABLE; su 2.2 sí tiene fuente verificable.
Elegir 2.1 es una decisión explícita de protocolo, no mezclar versiones ni reemplazar
silenciosamente la 2.2 solicitada.

## Resumen por paciente

V/M/A/Ø = efectivas VALIDADA/MANUAL/AUTOMATIC/ninguna en muestras activas.
C21/C22 = número de registros almacenados en activas. Serie/cal = muestras activas
con asociación; todas las calibraciones de esta columna son provisionales.

| Alias | Total | Activas | Archivadas | V/M/A/Ø | Borrador | C21/C22 | Serie/cal | A | B | C | D | 2.1 validada |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P001 | 40 | 0 | 40 | 0/0/0/0 | 0 | 0/0 | 0/0 | 0 | 0 | 0 | 0 | 0 |
| P002 | 5 | 5 | 0 | 5/0/0/0 | 1 | 5/3 | 5/5 | 2 | 2 | 2 | 2 | 5 |
| P003 | 5 | 5 | 0 | 5/0/0/0 | 0 | 5/0 | 0/0 | 0 | 0 | 0 | 0 | 5 |
| P004 | 3 | 3 | 0 | 3/0/0/0 | 0 | 3/0 | 0/0 | 0 | 0 | 0 | 0 | 3 |
| P005 | 3 | 3 | 0 | 2/1/0/0 | 2 | 2/0 | 0/0 | 0 | 0 | 0 | 0 | 2 |
| P006 | 6 | 6 | 0 | 4/2/0/0 | 2 | 4/0 | 0/0 | 0 | 0 | 0 | 0 | 4 |
| P007 | 1 | 1 | 0 | 0/1/0/0 | 1 | 0/0 | 0/0 | 0 | 0 | 0 | 0 | 0 |
| P008 | 2 | 2 | 0 | 0/0/1/1 | 0 | 1/1 | 2/2 | 0 | 1 | 0 | 1 | 0 |
| P009 | 1 | 0 | 1 | 0/0/0/0 | 0 | 0/0 | 0/0 | 0 | 0 | 0 | 0 | 0 |
| P010 | 1 | 0 | 1 | 0/0/0/0 | 0 | 0/0 | 0/0 | 0 | 0 | 0 | 0 | 0 |

Los CSV/JSON temporales contienen también IDs internos, totales de muestras sin
Characterization/serie/calibración, calibraciones provisionales/finales, versiones
y los cuatro resultados por muestra. El alias ordenado Pxxx no es pseudónimo
persistente y debe leerse junto con su PK interno de este snapshot.

## Resumen de todas las muestras activas

A=C y B=D en esta auditoría concreta; no es una equivalencia general de unidades.

| Sample interno | Paciente | Effective | Borradores | Versiones guardadas | Serie | A/C | B/D |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 41 | P002 | VALIDATED_REVISION | — | 2.2,2.1 | 1 | READY | READY |
| 42 | P002 | VALIDATED_REVISION | 28 | 2.1 | 1 | CHARACTERIZATION_VERSION_MISMATCH | CHARACTERIZATION_VERSION_MISMATCH |
| 43 | P003 | VALIDATED_REVISION | — | 2.1 | — | CHARACTERIZATION_VERSION_MISMATCH | CHARACTERIZATION_VERSION_MISMATCH |
| 44 | P004 | VALIDATED_REVISION | — | 2.1 | — | CHARACTERIZATION_VERSION_MISMATCH | CHARACTERIZATION_VERSION_MISMATCH |
| 45 | P005 | VALIDATED_REVISION | 27 | 2.1 | — | CHARACTERIZATION_VERSION_MISMATCH | CHARACTERIZATION_VERSION_MISMATCH |
| 46 | P002 | VALIDATED_REVISION | — | 2.2,2.1 | 1 | READY | READY |
| 47 | P002 | VALIDATED_REVISION | — | 2.1 | 1 | CHARACTERIZATION_VERSION_MISMATCH | CHARACTERIZATION_VERSION_MISMATCH |
| 48 | P002 | VALIDATED_REVISION | — | 2.1 | 1 | CHARACTERIZATION_VERSION_MISMATCH | CHARACTERIZATION_VERSION_MISMATCH |
| 49 | P003 | VALIDATED_REVISION | — | 2.1 | — | CHARACTERIZATION_VERSION_MISMATCH | CHARACTERIZATION_VERSION_MISMATCH |
| 50 | P003 | VALIDATED_REVISION | — | 2.1 | — | CHARACTERIZATION_VERSION_MISMATCH | CHARACTERIZATION_VERSION_MISMATCH |
| 51 | P003 | VALIDATED_REVISION | — | 2.1 | — | CHARACTERIZATION_VERSION_MISMATCH | CHARACTERIZATION_VERSION_MISMATCH |
| 52 | P003 | VALIDATED_REVISION | — | 2.1 | — | CHARACTERIZATION_VERSION_MISMATCH | CHARACTERIZATION_VERSION_MISMATCH |
| 53 | P004 | VALIDATED_REVISION | — | 2.1 | — | CHARACTERIZATION_VERSION_MISMATCH | CHARACTERIZATION_VERSION_MISMATCH |
| 54 | P004 | VALIDATED_REVISION | — | 2.1 | — | CHARACTERIZATION_VERSION_MISMATCH | CHARACTERIZATION_VERSION_MISMATCH |
| 55 | P005 | VALIDATED_REVISION | — | 2.1 | — | CHARACTERIZATION_VERSION_MISMATCH | CHARACTERIZATION_VERSION_MISMATCH |
| 56 | P005 | MANUAL_BASE | 20 | ninguna | — | SEGMENTATION_NOT_VALIDATED | NO_CHARACTERIZATION |
| 57 | P006 | VALIDATED_REVISION | — | 2.1 | — | CHARACTERIZATION_VERSION_MISMATCH | CHARACTERIZATION_VERSION_MISMATCH |
| 58 | P006 | MANUAL_BASE | 21 | ninguna | — | SEGMENTATION_NOT_VALIDATED | NO_CHARACTERIZATION |
| 59 | P006 | VALIDATED_REVISION | — | 2.1 | — | CHARACTERIZATION_VERSION_MISMATCH | CHARACTERIZATION_VERSION_MISMATCH |
| 60 | P006 | VALIDATED_REVISION | — | 2.1 | — | CHARACTERIZATION_VERSION_MISMATCH | CHARACTERIZATION_VERSION_MISMATCH |
| 61 | P006 | VALIDATED_REVISION | — | 2.1 | — | CHARACTERIZATION_VERSION_MISMATCH | CHARACTERIZATION_VERSION_MISMATCH |
| 62 | P006 | MANUAL_BASE | 25 | ninguna | — | SEGMENTATION_NOT_VALIDATED | NO_CHARACTERIZATION |
| 63 | P007 | MANUAL_BASE | 26 | ninguna | — | SEGMENTATION_NOT_VALIDATED | NO_CHARACTERIZATION |
| 64 | P008 | NONE | — | ninguna | 2 | NO_EFFECTIVE_SEGMENTATION | NO_EFFECTIVE_SEGMENTATION |
| 66 | P008 | AUTOMATIC_BASE | — | 2.2,2.1 | 2 | SEGMENTATION_NOT_VALIDATED | READY |

## Muestras históricamente pendientes

Se verificó en ORM la correspondencia actual con ImageJImportRecord de
`ijc1-case1`, Caso 1, contrato imagej-gray-v1, converter 1.0. Para las cuatro
coinciden referencias de paciente, caso y resultado; UUID del registro en JSON.
No se asumió la identidad únicamente por el número de muestra.

| Sample | Alias | Caso | Resultado | Borrador | M/N/MN base y borrador |
| --- | --- | --- | --- | --- | --- |
| 56 | P005 | 5 | 20 | 20 | 0/6/1 |
| 58 | P006 | 6 | 22 | 21 | 0/10/1 |
| 62 | P006 | 6 | 26 | 25 | 0/1/1 |
| 63 | P007 | 7 | 27 | 26 | 0/2/1 |

Siguen MANUAL_BASE efectivas, sin Characterization ni serie/calibración. A/C:
SEGMENTATION_NOT_VALIDATED; B/D: NO_CHARACTERIZATION. Clasificación operativa:
PENDING_MANUAL_MEMBRANE_ANNOTATION. No se validó ni editó nada.

42: VALIDADA 5 efectiva, BORRADOR 28. 45: VALIDADA 8 efectiva, BORRADOR 27.
Ambas siguen elegibles para 2.1; tener borrador no invalida su VALIDADA anterior.
64: sin resultado efectivo ni Characterization, con serie 2/calibración 1.
66: base AUTOMATIC, 2.2 elegible sólo en B/D; no tiene borrador.

PAIR_008 / REAL_HOLE: docs/65, 68 y 71 documentan que no se importó.
Actualmente hay 23 ImageJImportRecord READY de ijc1-case1, coherentes con ese
cierre. El modelo sólo registra importaciones exitosas; no tiene registro durable
del rechazo ni del alias ordinal PAIR_008. No es posible demostrar desde esta BD
la correspondencia exacta alias↔archivo externo ni asignarle sample_id. No se
inventó un ID ni se reejecutó importación/conversión. Pendiente recuperar el
manifiesto original o una identificación externa explícita para esa trazabilidad.

## Clases explícitas y datasets existentes

Existen 3 GENERATED y 0 DRAFT. No se editó ni regeneró ninguno. Las clases de
esta sección provienen sólo de membresías/snapshots almacenados. Los aliases
D01–D03 identifican datasets, no clases clínicas.

D01 `655dbdc2-27c1-4bdf-a604-9f958bb31502`: legacy 2.2/PHYSICAL/allow-effective.
Carece de `config.classes`; sus membresías tienen `Clase 1`, `Clase 2`, `clase 2`.
El preview actual rechaza las asignaciones sin catálogo. Las últimas dos además
son equivalentes bajo la política actual case-insensitive. **No se fusionan**.
Sólo se informa la evidencia congelada:

| Clase guardada | Seleccionados | Elegibles | Muestras | Núcleos | MN asociados | Filas |
| --- | --- | --- | --- | --- | --- | --- |
| Clase 1 | 1 | 1 | 2 | 21 | 1 | 21 |
| Clase 2 | 1 | 0 | 0 | 0 | 0 | 0 |
| clase 2 | 1 | 1 | 1 | 13 | 11 | 17 |

D02 `d4104b89-8eee-4298-a251-484d9b3d99f0`: 2.2/PHYSICAL/allow-effective. Preview actual:

| Clase explícita | Seleccionados | Elegibles | Muestras | Núcleos | MN asociados | Filas |
| --- | --- | --- | --- | --- | --- | --- |
| Clase A | 2 | 1 | 2 | 21 | 1 | 21 |
| Clase B | 4 | 1 | 1 | 13 | 11 | 17 |

D03 `7916057c-0d67-41f2-a003-dfa4b5151a97`: 2.2/BOTH/allow-effective. Preview actual:

| Clase explícita | Seleccionados | Elegibles | Muestras | Núcleos | MN asociados | Filas |
| --- | --- | --- | --- | --- | --- | --- |
| Clase A | 3 | 2 | 3 | 34 | 12 | 38 |
| Clase B | 3 | 0 | 0 | 0 | 0 | 0 |

D02 tiene dos clases con filas, pero sólo un paciente elegible por clase.
D03 tiene sólo una clase efectiva: no cumpliría hoy la condición de al menos dos
clases efectivas para una nueva generación. Se conserva su snapshot histórico.
Los snapshots D02/D03 dicen SEGMENTATION_NOT_VALIDATED para tres exclusiones,
mientras el preview actual, con validated_only=false, dice NO_CHARACTERIZATION.
Es consistente con la corrección de motivos de B.2; las filas elegibles siguen
siendo 38. No se reescriben motivos históricos. Los hashes de las tablas de
datasets/membresías/fuentes permanecen idénticos.

## Remediación priorizada por impacto

Ninguna acción de esta tabla se ejecutó. Ganancias futuras son potenciales y
condicionadas a revisión y a resultados almacenados válidos, no simulaciones de
nuevas mediciones. No se puede garantizar salida científica sin procesarla.

| Prioridad / decisión | Pacientes afectados | Muestras | Ganancia o límite verificable |
| --- | --- | --- | --- |
| 0. Definir si el protocolo admite 2.1 PIXELS | 5 | 19 | Ya elegibles; +17 muestras y +4 pacientes frente a A, sin cambiar BD |
| 1. Si se exige 2.2: completar versión sobre VALIDADA vigente | 5 | 17 | Potencial +17 muestras / +4 pacientes en A; todas pasan hoy 2.1 |
| 2. Completar/revisar membranas, validar y luego caracterizar 56/58/62/63 | 3 | 4 | Potencial +4 en A/B; validar solo aporta 0 sin Characterization; P007 sería un paciente nuevo |
| 3. Decidir revisión de 66 o admitir AUTOMATIC explícitamente | 1 | 1 | B ya añade 1 muestra y 1 paciente; validar exigiría Characterization nueva con fuente VALIDADA |
| 4. Revisar muestra 64 sin segmentación | 1 | 1 | Potencial +1 tras flujo científico completo; no determinable hoy |
| Física: asociar series/calibraciones correctas donde falten | 5 | 18 | Asociar solo aporta 0: no crea valores físicos almacenados |
| Física: caracterizar en 2.2 las validadas ya asociadas 42/47/48 | 1 | 3 | Potencial +3 en C; finalización científica de calibración sigue pendiente |
| Calibración final: cerrar 18S-A2 | 2 | 3 | 0 muestras técnicas nuevas inmediatas; afecta 3 elegibles físicas, 7 asociadas en total |

Las 17 validadas sin 2.2 incluyen 3 con serie/calibración y 14 sin serie.
Por ello completar 2.2 es la primera intervención potencial de mayor impacto en
PIXELS; no hace falta asociar calibración para ese fin. No se suman ganancias de
filas solapadas. Para PHYSICAL, 14 de esas 17 requieren resolver adquisición y
almacenar caracterización física compatible; no se puede asignar la misma escala
sólo por pertenecer al dataset.

Revisar 42/45 permite decidir si se conserva la VALIDADA efectiva actual o se
completa la edición pendiente antes de una nueva caracterización. No se propone
validar automáticamente sus borradores. Los 42 archivados permanecen excluidos.

## Advertencias científicas y FEATURE_GAP

`CAL-OPTIKA-40X-PROVISIONAL-001` sigue PROVISIONAL, verificado en BD como ID 1.
`IMPORTANT_PENDING_18S_A2` permanece abierto: capturas independientes,
referencias de cuadrícula/círculos, reposicionamiento, rotación, repetibilidad,
anisotropía, incertidumbre y tolerancias/umbrales de aceptación final.
No recomendar resultados en µm/µm² como definitivos hasta cerrar ese proceso.
Los snapshots físicos existentes son provisionales: cambiar un estado futuro
no reescribe ni convierte por sí solo esos snapshots en evidencia final.
PIXELS puede prepararse independientemente si el protocolo y clases son adecuados.

`GLCM_PHYSICAL_DISTANCE_NORMALIZATION = PENDING`: d=1 px no está normalizado
físicamente. No se modificó GLCM.

FEATURE_GAP, no exclusiones de muestra: elipticidad, solidez, ratio perímetro
MN/núcleo y distancia borde-a-borde MN–núcleo no están almacenados. No se añaden
ni aproximan. La distancia disponible es entre centroides.
Se mantienen los demás pendientes de docs/93; no se inicia 18U-C, splits,
entrenamiento, recalibración ni ampliación del builder.

## Seguridad, pruebas y reproducibilidad

BD resuelta desde settings:
`/home/israel/repos/sicam-refactor/apps/web/Backend/db.sqlite3`.
MEDIA_ROOT: `/home/israel/repos/sicam-refactor/apps/web/Backend/media`.
ORM con URI SQLite `mode=ro` y `PRAGMA query_only=ON`; lectura del reporte en una
transacción consistente. Comparación antes/después del archivo SQLite, hashes
lógicos de 32 tablas visibles para Django y conteos. Sin cambios. Media: 95 archivos,
inventario de rutas/tamaños/mtime idéntico; no se recalcularon hashes de imágenes.
SQLite integrity_check=ok y foreign_key_check=[] antes/después.

SHA-256 BD: `bd512dce249f792fa1e1a0c4c586aff19f387add42e92a569d2cc5d28c3d1b98`.

| Tabla | Antes | Después |
| --- | --- | --- |
| api_paciente | 10 | 10 |
| api_caso | 10 | 10 |
| api_analisispred | 10 | 10 |
| api_muestrasaliva | 67 | 67 |
| api_muestrasangre | 2 | 2 |
| api_resultadosegmentacion | 30 | 30 |
| api_revisionsegmentacion | 28 | 28 |
| api_resultadocaracterizacion | 27 | 27 |
| api_calibration | 3 | 3 |
| api_acquisitionseries | 4 | 4 |
| api_mldataset | 3 | 3 |
| api_mldatasetpatient | 15 | 15 |
| api_mldatasetsample | 60 | 60 |
| api_lifecycleevent | 53 | 53 |
| api_imagejimportrecord | 23 | 23 |
| api_segmentationexecution | 29 | 29 |

- 12 tests dirigidos temporales PASS: VALIDADA, MANUAL, AUTOMATIC, BORRADOR
  posterior no efectivo, sin resultado, versión exacta 2.1/2.2, PIXELS sin
  calibración, PHYSICAL provisional, archivo heredado, aislamiento institucional,
  privacidad, ausencia de escrituras SQL y snapshot GENERATED intacto.
- Tests con BD sintética aislada y MEDIA_ROOT temporal. Se comprobó que las
  consultas del adaptador son SELECT; no se accedió a motores científicos.
- 36 avisos existentes de deprecación CheckConstraint.check; sin fallos pendientes.
- Django check PASS; makemigrations --check --dry-run: No changes detected.
- Migraciones api 0001–0014 aplicadas. Ninguna migración creada/aplicada.
- pip check PASS; aviso de caché sin permisos, sin instalación ni actualización.
- No regresión backend completa: no cambió código productivo; se respeta la
  condición del prompt. No frontend/build porque no hubo cambios frontend.

Los errores iniciales del arnés temporal (columna CSV opcional y configuración
pytest fuera del repo) se corrigieron y revalidaron. No afectaron datos reales.
No se creó management command: el servicio existente ofrece un camino limpio
sin refactor productivo. El código reproducible queda sólo en /tmp.

Ejecución desde backend, usando Python del entorno sicam:

```bash
PYTHONDONTWRITEBYTECODE=1 /home/israel/miniconda3/envs/sicam/bin/python -B /tmp/sicam18uc0/run_audit.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/tmp/sicam18uc0:$PWD /home/israel/miniconda3/envs/sicam/bin/python -B -m pytest -c pytest.ini /tmp/sicam18uc0/test_readiness.py -q -p no:cacheprovider
PYTHONDONTWRITEBYTECODE=1 /home/israel/miniconda3/envs/sicam/bin/python -B /tmp/sicam18uc0/run_audit.py checks
PYTHONDONTWRITEBYTECODE=1 /home/israel/miniconda3/envs/sicam/bin/python -B /tmp/sicam18uc0/run_audit.py verify
```

Artefactos temporales, no versionados:

- `audit.json`: cobertura completa por muestra/paciente/modo y clases.
- `patient_readiness.csv`, `sample_readiness.csv`, `summary.json`.
- `before.json`, `after.json`, `integrity.json`, `final_integrity.json`.
- `readiness.py`, `run_audit.py`, `test_readiness.py` y script de metadatos técnicos.
- `tests.log`, `checks.log`, `pip_check.log`, `extra.json`.

/tmp no es almacenamiento durable; las conclusiones agregadas se conservan aquí.
No se exportaron pacientes con datos identificables, imágenes, geometrías ni
métricas científicas por objeto. No hubo escrituras de BD/media, cambios de estados,
series/calibraciones, generación de datasets ni alteración de snapshots.

## Cierre y siguiente paso

`git diff --check`: PASS. `git diff --stat`: vacío para archivos seguidos;
este documento nuevo es untracked y por eso no aparece en ese stat. Estado final
esperado: únicamente `?? docs/94_sprint_18u_c0_data_readiness_audit.md`.
Sin staging, commit ni push.

Recomendación: decidir primero protocolo 2.1/PIXELS ya disponible frente a 2.2;
si se mantiene 2.2, autorizar por separado completar la caracterización de las
17 muestras validadas faltantes. Revisar clases explícitas y fuentes efectivas
antes de generar otro conjunto. Resolver PAIR_008 con evidencia externa y tratar
los datasets legacy mediante una nueva definición si corresponde, conservando
los originales. No se realizó ninguna de esas acciones.

SPRINT 18U-C0 = READY_WITH_AUDIT_ISSUES_PENDING
