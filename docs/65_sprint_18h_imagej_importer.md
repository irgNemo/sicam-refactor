# Sprint 18H — Importador ImageJ de anotaciones manuales SALIVA

Cierre de validación: 2026-10-03. Rama master; HEAD inicial
`09c00859a4260dcf64c51d0c28cdeafe7f65ab5a`. Precheck limpio.
Cambios sin staging, commit ni push. No se implementó Sprint 18I.

## Resultado

Implementado `python manage.py import_imagej_dataset`: lectura XLSX, descubrimiento
exacto de parejas, conversión topológica, preflight de identidad e idempotencia,
persistencia ORM transaccional con storage gestionado y compensación, más
compatibilidad de base manual con effective/editor/UI.

No se importa clase clínica, diagnóstico, grupo ni tratamiento. No se llaman
CURRENT, ALT, FastAPI o Characterization desde el importador. Se reutiliza el
helper puro de detección de autointersecciones del módulo geometry, sin ejecutar
el pipeline de caracterización.

El [contrato para el alumno](64_imagej_dataset_import_format.md) documenta
estructura, Excel, cell region, máscaras opcionales, errores y CLI.

## Modelos y migración

`api/migrations/0008_imagej_manual_import.py`:

- Paciente: identity_mode IDENTIFIED/PSEUDONYMIZED; external_id_namespace,
  external_patient_id e initials. Nombre/apellido usan string vacío (no NULL)
  para pseudonimizados. IDENTIFIED conserva ambos obligatorios mediante clean,
  serializer y constraint. PSEUDONYMIZED exige iniciales e identidad externa y
  nombres vacíos. Fecha de nacimiento e identificación heredada siguen
  obligatorias; no se inventan datos.
- Unique parcial (external_id_namespace, external_patient_id) para identidad
  externa presente; constraint exige ambos campos o ninguno. Initials NO es PK
  ni único globalmente. Misma ID externa en otro namespace es válida.
- `identificacion` heredada de nuevos pacientes usa alias técnico `ext:` + UUID5
  de `(namespace, external_patient_id)`; no es nombre ficticio ni ID hospitalario
  reinterpretado como PK. La autoridad durable es el par de campos externos.
- Caso.case_number nullable, positivo cuando existe; unique condicionado
  (paciente,case_number). Históricos permanecen NULL. Nuevo caso: título Caso 1,
  número 1. Candidato histórico de título literal Caso 1 sólo se adopta si es
  único y no tiene otro número; ambigüedad devuelve CASE_AMBIGUOUS.
- ResultadoSegmentacion.base_origin AUTOMATIC/MANUAL, default AUTOMATIC para
  históricos. MANUAL exige SALIVA y estrategia NULL mediante constraint.
- ImageJImportRecord: UUID, dataset_key, patient_namespace, external_patient_id,
  patient_key normalizada, case_number, basename lógico, hashes, tres keys
  UNIQUE, versiones, FileField source_mask_file, FKs PROTECT a paciente/caso,
  OneToOne PROTECT a muestra/resultado, status READY, metadata y timestamps.
  No registro incompleto se confirma: se guarda en la misma transacción que
  muestra/resultado. Análisis se alcanza desde muestra. La máscara queda
  vinculada al resultado mediante ese registro, no al modelo legacy de máscaras.

Reglas de Paciente protegidas en modelo y serializer (también PATCH), además de
constraints. CasoSerializer devuelve errores de validación para números inválidos
o duplicados. Los timestamps registran fecha real de creación, no una fecha de
estudio inferida.

La migración se probó en BD de tests y en una **copia temporal** de SQLite.
Las columnas existentes de las diez tablas api se compararon con el original:
idénticas. No se ejecutó migrate sobre `apps/web/Backend/db.sqlite3`.
La aplicación local requiere aplicar esta migración antes de usar los modelos
nuevos contra esa BD; esa operación no se realizó durante este sprint.

## Descubrimiento, Excel y relaciones

Matching `strip().casefold()` exacto, ACL distinto de ACL2. XLSX estándar con
cuatro campos o adapter fijo ijc1 para columnas ID/Iniciales/Fecha de nacimiento
con encabezado fila 2. Lectura mediante zipfile/XML stdlib; sin openpyxl ni capa
arbitraria de mapeos. Se rechazan fórmulas en campos consumidos, IDs duplicados o
con precisión numérica dudosa, fechas inválidas/faltantes/futuras y múltiples
hojas. Otras columnas de datos no se consumen.

Layout official, legacy-flat o legacy-repeated explícito. Fuente JPG/JPEG/PNG;
TIFF sólo máscara. Basename literal, no fuzzy. Symlinks y anidación incompatible
se rechazan. Formato, orientación y dimensiones se verifican sin transformación.

REUSE de paciente por namespace/ID antes de CREATE; verificar initials y DOB,
sin usarlos como clave principal. Discrepancia: PATIENT_DATA_CONFLICT, nunca
actualización silenciosa. Excel sin carpeta no crea pacientes. Si todo el
paciente tiene parejas inválidas, tampoco se crea un paciente vacío.

Reutilizar Caso 1 por número; análisis único coherente abierto/en proceso, o
crear uno abierto si falta. Múltiples análisis, incoherencia de paciente/caso o
análisis cerrado bloquean NUEVAS muestras como ANALYSIS_AMBIGUOUS. Reimportación
idéntica sigue siendo no-op aunque posteriormente se haya cerrado el análisis.

## Conversión y topología

Constantes en `api/services/imagej/contracts.py`:
`CONVERTER_VERSION='1.0'`, `CONTRACT_VERSION='imagej-gray-v1'`.

0=fondo, 85=micronúcleo, 170=cell region rellena, 255=núcleo. Clases opcionales,
incluso {0}. TIFF gris L uint8 de una página. Componentes conectados 8 por clase;
orden de clases membrana/nucleo/micronucleo y componentes por bounding box (y,x)
para IDs reproducibles en el convertidor. Normalizador SICAM existente asigna
IDs editoriales globales; `source.raw_id` de componente puede repetirse entre
clases.

`RETR_TREE` + `CHAIN_APPROX_NONE`; sin simplificación, lista abierta de coordenadas
enteras originales, al menos tres vértices distintos y área no nula. Detectar
múltiples exteriores, conectividad sólo diagonal, puntos repetidos/cruces,
contorno degenerado y bounds. Rasterizar con Pillow y exigir diferencia de
**cero píxeles**.

En 170, el interior adicional al componente sólo puede contener valores 85/255.
Esto reconstruye la región celular que subyace a las etiquetas nucleares en un
canal. Fondo 0 u otra región 170 dentro del exterior se rechazan; no rellenar
huecos reales ni modificar source TIFF. No se asignan relaciones celulares por
proximidad ni se calculan métricas científicas.

Ante topología no representable: rechazar pareja completa y reportar el primer
motivo. No hardcodear aliases del dataset, no separar regiones ni perder un
objeto individual silenciosamente. Contorno válido en el borde es admisible.

## Base manual, BORRADOR, effective y UI

Persistir COMPLETADO significa base disponible, NO validación. Raw conserva
`objetos` y una referencia/versiones de importación; normalizado conserva v1.1,
source y summary de tres clases incluyendo ceros. Cada objeto tiene
`provenance={origin:'manual',base_object_id:null}`. Strategy=NULL,
base_origin=MANUAL. El original TIFF se guarda aparte byte-exactamente.

No crear RevisionSegmentacion al importar. Editar usa el endpoint normal y
crea el primer BORRADOR con geometría, IDs, source y origen manual. El builder
preserva metadata de objetos; históricos automáticos conservan automatic y
base_object_id. VALIDADA sigue inmutable, BORRADOR nunca efectivo.

Effective: última VALIDADA si existe; de lo contrario base MANUAL o AUTOMATICO
según base_origin. No inferir manual de strategy=NULL por sí solo.

Vue muestra “Anotación manual” en el resultado y effective. Pacientes
pseudonimizados se muestran y buscan por initials/display_name/identificación;
el formulario normal sigue creando pacientes identificados con nombre/apellido
required. No se añadió UI de importación ni selector target. Overlay/editor,
rutas, controles de navegación y flujo BLOOD se conservan.

Guard mínimo: intentar caracterizar una base MANUAL no validada devuelve HTTP
400 con instrucción de revisar/validar, antes de ejecutar Characterization;
su modelo sólo admite fuentes AUTOMATICO/VALIDADA. Importar no crea ninguna
caracterización. Después de validar se conserva el flujo existente, incluido su
comportamiento ante cero membranas: un guard general de completitud queda como
follow-up, no se rediseña en 18H.

## Keys e idempotencia exactas

`H(A)=SHA256(json.dumps(A, ensure_ascii=False, separators=(',', ':'),
allow_nan=False).encode('utf-8')).hexdigest()`; sin BOM/newline; lowercase.
Namespace técnico literal `sicam.imagej.import.v1`. Dataset y namespace de
paciente se validan como identificadores ASCII lowercase; no se infieren.
ID externo texto; case_number entero 1. Basename literal conserva puntuación.

```text
I = ['sicam.imagej.import.v1', dataset_key, patient_namespace,
     external_patient_id, 1]
sample_key     = H(['sample', *I, image_sha256])
annotation_key = H(['annotation', sample_key, mask_sha256, '1.0', 'imagej-gray-v1'])
logical_key    = H(['logical', *I, exact_basename])
```

Initials/patient_key NO forman la identidad durable. Se registran para detectar
rebindings de carpeta a otro ID externo. SHA-256 streaming de los bytes originales,
comprobado también tras copia; no hash de imagen recodificada.

- Idéntica: ALREADY_IMPORTED, sin cambiar resultado, BORRADOR/VALIDADA, timestamps
  humanos, registros ni archivos. Verificar integridad de enlaces y storage.
- Mismo logical con imagen distinta: IMAGE_CHANGED_CONFLICT.
- Misma muestra con máscara distinta: MASK_CHANGED_CONFLICT.
- Versiones distintas: CONVERTER_VERSION_CONFLICT; nunca sobreescribir.
- Imagen idéntica bajo otro basename: SAME_IMAGE_NEW_NAME, revisión explícita.
- Duplicado de imagen en otra identidad/dataset o en el lote: DUPLICATE_IMAGE_CONFLICT.
- Archivo guardado faltante/corrupto o referencias inconsistentes:
  IMPORT_INTEGRITY_CONFLICT; no reparar automáticamente.

## Transacción y storage

Validar/converter/hashes antes de persistir y comprobar de nuevo estabilidad
antes de escribir. `transaction.atomic()` por pareja, incluyendo paciente/caso/
análisis nuevos, muestra, resultado y registro. Constraints de identidad/caso/
keys impiden duplicados; locks de paciente/caso donde la BD los soporta. SQLite
puede producir DB_ERROR por contención: rollback y nueva ejecución de preflight,
no retries parciales ni suponer que select_for_update bloquea en SQLite.

Imagen usa el ImageField/upload_to/storage existente de MuestraSaliva, nombre
UUID opaco. TIFF usa FileField `imagej/source_masks/%Y/%m/<uuid>.tif`.
Se respeta nombre retornado por storage, verificando hash de destino. No se
almacena ruta externa como dependencia funcional ni se escribe dentro del dataset.

Rollback de DB NO revierte storage: compensación elimina sólo archivos nuevos
propios. También se rastrea nombre UUID antes de guardar para limpiar escritura
parcial de FileSystemStorage. No borrar archivos existentes ante una colisión.
Error de compensación: STORAGE_CLEANUP_REQUIRED.

Límite operativo: terminación abrupta del proceso/SIGKILL entre copia y commit
no ejecuta finally/except y puede dejar archivos huérfanos. No hay reconciliador
de crashes en este sprint. Inspeccionar storage frente a referencias antes de
reintentar tras una caída; no ejecutar limpieza masiva automática. La compensación
está verificada para excepciones normales y escritura parcial en storage local.

El status durable actual es READY solamente: una transacción fallida no conserva
registro parcial de importación. Los errores viven en el reporte de la corrida.
No se implementó sistema de jobs, SegmentationExecution ni checkpoint de 18I.

## CLI y dry-run

Flags requeridos: --source, --patients-file, --dataset-key, --patient-namespace.
Opcionales: --case-number 1, --dry-run, --patient (repetible), --limit, --strict,
--layout official|legacy-flat|legacy-repeated, --patients-format standard|ijc1.
Sin --force, --overwrite ni clase.

Dry-run recorre Excel, identidad, casos/análisis, pairing, dimensiones, valores,
componentes, geometría/topología, hashes, integridad/idempotencia y acciones
esperadas. Sólo consultas ORM/storage; no crear pacientes/casos/resultados/
registros/archivos. Reporte stdout JSON con aliases y conteos de parejas aptas
(o ya importadas); no incluir objetos de parejas rechazadas en esos conteos.

## Validación sintética y regresiones

- `api/test_imagej.py`: 25 tests nuevos con fixtures exclusivamente sintéticas en
  directorios temporales: identidad/serializer/constraints, Caso 1/null/reuso/
  ambigüedad, XLSX/matching/fechas/IDs, todas combinaciones de máscara, oclusión
  170 con núcleo/MN, holes/diagonal/múltiples exteriores/cruces/degenerados/borde,
  formatos/pairing, dry-run sin escrituras, importación ORM, hashes/copias,
  reimportación con BORRADOR/VALIDADA/análisis cerrado, conflictos/versiones,
  rollback/archivo preexistente/escritura parcial/cambio de source, strict/layout,
  Editar→guardar→validar y guard de Characterization manual.
- Backend completo: **223 passed, 2 skipped**. Omisiones: smokes que requieren
  servicios reales, expresamente fuera de alcance. Incluye normalización,
  estrategias, revisiones/effective, Characterization 2.1 y BLOOD existentes.
- Frontend estrategias/editor: **23 passed**, incluyendo presentación manual y
  paciente pseudonimizado, selección/edición N/MN con cero M, eliminar, undo/redo,
  agregar M y construir payload sin mutar fuente.
- Frontend Characterization 2.1: **22 passed**. Build Vite: PASS.
- Django check: 0 issues. makemigrations --check: No changes detected.
- pip check: No broken requirements found. Requirements agrega numpy 2.2.6 y
  opencv-python-headless 5.0.0.93, versiones disponibles usadas por el convertidor.
  No se instalaron dependencias durante esta tarea.

## Dry-run real, sin importación

Dataset local externo leído desde WSL; Excel BD_IJC1. Layout legacy-flat y adapter
ijc1, namespace ijc1, dataset ijc1-case1. Se usó una copia de SQLite migrada bajo
`/tmp/sicam18h_validation/audit.sqlite3`, no la BD de trabajo. Ese snapshot refleja
los datos locales previos; no equivale a haber migrado o importado la BD real.

Primero un paciente: 5 parejas aptas, 40 N, 5 MN, 0 M; exit 0.
Luego lote completo: duración observada 80.42 s; exit **2 esperado por una pareja
rechazada**, no error operativo.

| Agregado | Resultado |
| --- | ---: |
| Pacientes descubiertos / matched | 6 / 6 |
| Pacientes a crear / reutilizar | 6 / 0 |
| Casos a crear / reutilizar | 6 / 0 |
| Entradas de pairing | 24 |
| Parejas aptas | 23 |
| Ya importadas | 0 |
| Conflictos de identidad/contenido | 0 |
| Rechazos topológicos | 1 |
| Errores de valores / dimensiones | 0 / 0 |
| Objetos en parejas aptas: M / N / MN | 0 / 114 / 34 |

Alias PATIENT_002 / PAIR_008: UNSUPPORTED_POLYGON_TOPOLOGY, REAL_HOLE.
El identificador es de orden del reporte, no un nombre personal ni una regla
hardcodeada. Se requiere revisión manual de esa pareja; no se cambió GT.
Los conteos de las 24 máscaras de 18F (119 N/35 MN) incluyen la pareja rechazada;
los 114/34 de este dry-run son sólo las 23 parejas aptas.

La BD temporal quedó byte-idéntica tras el dry-run completo, ledger vacío.
Dataset, BD real y MEDIA_ROOT se comprueban por SHA-256/tamaño/mtime contra
snapshot inicial: **49/49 archivos del dataset, 42/42 archivos de MEDIA_ROOT y
db.sqlite3 sin cambios**. `git diff --check` pasó. Los reportes de validación
permanecen sólo en /tmp.

## Archivos y límites

Backend: models.py, serializers.py, servicios revisions/effective y guard pequeño
de characterization/service.py; requirements; nuevo paquete services/imagej,
management command, migración 0008 y test_imagej.py.
Frontend: MainContent, SideBar, RegistroView, SegmentationResultPanel,
segmentationStrategies, helper patientPresentation y tests de estrategias.
Documentación: esta guía y 64_imagej_dataset_import_format.md.

No se tocaron microservicios, modelos de segmentación, thresholds, rutas API,
algoritmos científicos ni datos originales. No implementación de targets/merge/
SegmentationExecution. No import real, no commit, no push.

Pendiente operativo, no ejecución autorizada: aplicar migración a BD destino
cuando se autorice preparar el piloto; aprobar posteriormente importación real
limitada. La pareja rechazada no debe entrar sin resolver su representación.

**SPRINT 18H = PASS**: infraestructura y validaciones solicitadas completadas;
una pareja real se rechaza correctamente bajo la política aprobada. PASS no
significa importación real realizada ni validación científica del dataset.
