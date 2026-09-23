# Sprint 18A — Microservicio SALIVA alternativo Cellpose-SAM

## Alcance y aislamiento

Estrategia `ALT_CPSAM_MORPHOLOGICAL_V1`; `algorithm_version=1.0`;
`cellpose_version=4.0.8`; `cellpose_model=cpsam`; CPU; puerto 8003.

Se añade `apps/segmentation-saliva-alt/` sin integración Django/frontend,
selector, migraciones ni cambios en Characterization. SALIVA actual
(`CURRENT_CUSTOM_V1`, modelo `membranas_500_125`, puerto 8001), BLOOD (8002)
y los entornos `sicam`/`sicam-blood` permanecen intactos. No hay comparación
de calidad, optimización de umbrales ni selección automática de estrategia.

Precheck del 2026-09-23: `WORK_REPO=/home/israel/repos/sicam-refactor`,
rama `master`, HEAD `7a3036f` (`Add saliva morphometric characterization
frontend`), `git status --short` vacío. Los cinco commits iniciales fueron
`7a3036f`, `93badea`, `f5df193`, `7618954`, `4045393`.

## Fuente y trazabilidad

Procedencia declarada por el solicitante: **RobbertRios/sicam**.
`SOURCE_REPO=/home/israel/repos/sicam-main`, exclusivamente lectura.
La copia realmente encontrada está anidada en `sicam-main/sicam-main/`:

```text
/home/israel/repos/sicam-main/sicam-main/micro-saliva/
```

`SOURCE_PIPELINE_FOUND=YES` en esa ruta. En la ruta directa indicada
inicialmente no existe. No hay `.git` en la carpeta exterior ni en la copia
interior: status/branch/log de la fuente no están disponibles. Se trata de
una copia extraída, con archivos `:Zone.Identifier`; no puede atribuirse un
commit de origen verificable. Se inventariaron 274 entradas con tamaño,
modo, mtime y SHA-256 antes de escribir la implementación, en
`/tmp/sicam18a-source-before.json`; la comparación final cubre también
archivos ignorados y no versionados. No se importó ni ejecutó Python desde
la fuente, ni se copiaron cachés, modelos, resultados o el vendorizado.

Archivos auditados y ruta real del flujo:

1. `app/main.py`: lifespan precarga modelo.
2. `app/routers/segmentacion.py`: `POST /segmentar`, multipart **file**;
   llama en threadpool a `app/services/segmentador.py::segmentar_pipeline`.
3. `app/services/segmentador.py`: OpenCV imdecode BGR → RGB;
   llama `segmentacion_core/seg_pipeline_v2.py::segmentar_todo`.
4. `seg_pipeline_v2.py`: membranas Cellpose + morfología de núcleos/MN;
   devuelve tres máscaras uint16, fondo cero.
5. El router convierte cada máscara con
   `app/utils/poligonos.py::obtener_poligonos_desde_mascara`.
6. `requirements.txt` original, UTF-16: fija Cellpose 4.0.8 y NumPy 2.2.6;
   mezcla dependencias efectivas con otras innecesarias para este flujo.

Los supuestos `segmentacion_core/segmentacion.py` y
`segmentacion_core/poligonos.py` no existen en la fuente; sus equivalentes
son el router y `app/utils/poligonos.py`. En ALT se separa el ensamblado de
respuesta en `segmentacion_core/segmentacion.py` y se ubica el conversor en
`segmentacion_core/poligonos.py`. El único helper científico transitivo es
el propio pipeline; `seg_membranas.py`, `seg_nucleos.py`, `seg_micronucleos.py`,
controllers, GUI y Cellpose vendorizado no participan en este flujo.

Checksums SHA-256 de archivos fuente:

| Archivo relativo a micro-saliva | SHA-256 |
|---|---|
| `segmentacion_core/seg_pipeline_v2.py` | `dca6d4f1dfaa671d21763f7847a6c85d1e3d413d1167c07a40aa68805bcf4407` |
| `app/routers/segmentacion.py` | `409feb6a9db6229958401eb8d3a4cdb880b91ddc56856c67e29f31e1e95960d8` |
| `app/utils/poligonos.py` | `261c5b80312dc55eebeeefbf67ff8bff3e2359b53d30d5017b864f2a167cabaf` |
| `app/main.py` | `9fa7dba7a6d042001ce9681e1a5ec7a1ce402e785a2ce186240db1d6bb2266d5` |
| `app/services/segmentador.py` | `db74539f51d17b285bba95ff1efccdcb01f009e48752312826124fdea5833fc2` |
| `requirements.txt` | `f510f7fdfd3e41f155c56c0616bb6096f571f921b73959c00003348535e1afff` |

## Cellpose y artefacto efectivo

La fuente menciona `pretrained_model="cyto3"`, pero la API oficial de 4.0.8
declara `MODEL_NAMES=["cpsam"]`. Su constructor admite
`CellposeModel(gpu=False, pretrained_model="cpsam")`; un nombre desconocido
se sustituye por cpsam. ALT evita esa ambigüedad: exige versión 4.0.8,
verifica cpsam en `MODEL_NAMES`, valida el artefacto y pasa su **ruta absoluta**
al constructor. Así tampoco puede sombrearlo un archivo `cpsam` en el cwd.
Mantiene `use_bfloat16=True`, el default de 4.0.8, y los argumentos `eval`
originales. El código instalado se inspecciona como evidencia de API.

El cache se resuelve mediante `models.MODEL_DIR` (variable
`CELLPOSE_LOCAL_MODELS_PATH` o `~/.cellpose/models`). El archivo existente:

```text
nombre: cpsam
tamaño: 1233587898 bytes
SHA-256: e1440429eb384f95afe32bcba6510f90d518eaedc917ede549bed6804004abe2
```

Es el mismo artefacto validado para BLOOD, reutilizado en lectura. ALT falla
si falta o no coincide; no permite descargas implícitas ni fallback. El
startup registra estrategia, versión Cellpose, modelo, algoritmo y ruta.

## Parámetros científicos preservados

| Etapa | Operaciones / parámetros |
|---|---|
| Preprocesado | resize RGB 512×512 con anti_aliasing; gray; inversión; percentiles 1/99; límite superior max(p99,p1+0.10); rescale_intensity; uint8 |
| Cellpose | diameter=80; flow_threshold=0.5; cellprob_threshold=-0.5; resample=False |
| Membranas | remove_small_objects min_size=200; resize nearest-neighbor al tamaño original; uint16 |
| Núcleo | Gaussian sigma=1.0; mínimo 100 píxeles celulares; Multi-Otsu classes=3; fallback Otsu×0.95 |
| Semillas | distancia máxima >=3; distancia >max×0.45; min_size=10; semilla mayor >=0.003×área celular; candidatos >=0.30×semilla mayor |
| Reconstrucción nuclear | radio int(0.55×distancia máxima); dilatación disk; intersección con máscara oscura; primera región de temp_props como en fuente |
| Filtros nucleares | rechazo si borde >30 píxeles y eccentricity>0.80; contraste >=0.06; área **>35**; eccentricity<0.92; solidity>0.70; convex hull; intersección final con célula |
| Validación celular | eliminar membrana si no tiene label nuclear detectado |
| MN | Gaussian sigma=1; Multi-Otsu classes=3 / Otsu×0.95; excluir núcleo; remove_small_objects min_size=800 |
| Área MN | inclusivo: max(800, área nuclear/16) <= área MN <= área nuclear/3 |
| Geometría MN | aspect ratio<2.5; eccentricity<0.90; solidity>0.70 |
| Fotometría MN | intensidad candidata<=intensidad nuclear+0.12; contraste célula/candidato>=0.05 |
| Borde MN | overlap<5 píxeles; convex hull final |

El código fuente exige área nuclear **estrictamente mayor que 35**, aunque
el enunciado abrevia "minimum area=35". Se conserva la desigualdad original.

`intensidad_citoplasma` era la media de **toda** la región celular,
incluidos los núcleos. Se renombra `intensidad_region_celular` sin cambiar
la operación ni los umbrales. Comparación AST de ambas funciones
morfológicas, normalizando ese nombre: idénticas. `segmentar_todo` también
coincide al excluir docstring y logs de depuración.

## Comportamientos y limitaciones conocidas

- **Anucleadas:** ALT elimina toda membrana sin núcleo detectado.
  CURRENT_CUSTOM_V1 conserva la máscara de membranas independiente de que
  encuentre núcleos. No se homogeneizan ambos pipelines.
- **Binucleadas/multinucleadas:** todos los núcleos de una membrana usan
  `region.label`. OpenCV `RETR_EXTERNAL` extrae un contorno por componente
  separado; se producen dos objetos `nucleo` si hay dos componentes,
  ambos con el mismo `id` crudo. Igual posibilidad para MN. El campo externo
  sigue llamándose `id`, no `raw_id`; la normalización posterior de SICAM
  queda intacta y este servicio no genera nuevos IDs globales.
- **KNOWN SCIENTIFIC LIMITATION:** el área e intensidad del "núcleo
  principal" para MN incluyen conjuntamente todos los píxeles nucleares
  que comparten label. Afecta límites 1/16 y 1/3; no se corrige en 18A.
- **KNOWN SCIENTIFIC LIMITATION:** imágenes rectangulares se deforman
  temporalmente a 512×512. Las máscaras regresan al alto×ancho original
  por nearest-neighbor antes de analizar núcleos/MN. Los umbrales en píxeles
  no son invariantes a resolución; la validación científica queda pendiente.
- El mínimo absoluto 800 puede volver imposible el intervalo de MN en
  células con área nuclear menor de 2400. Se conserva.
- Convex hull, orden de contornos, simplificación epsilon=1.5 y descarte
  de polígonos degenerados se mantienen. No hay validación de calidad
  clínica, comparación de estrategias ni calibración física.

## Contrato y adaptaciones operativas

`POST /segmentar` recibe multipart `file` (coincide con SALIVA existente).
`GET /docs` y `GET /openapi.json` se sirven en `127.0.0.1:8003`.

```json
{"objetos": [{"id": 7, "tipo": "membrana", "puntos": [[10, 10], [20, 10], [20, 20]]}]}
```

Tipos exactos: `membrana`, `nucleo`, `micronucleo`; coordenadas `[x,y]` en
resolución original; se conservan labels crudos y orden por tipo.
No se agregan metadatos al resultado ni se toca ResultadoSegmentacion.

Adaptaciones respecto al original: imports mínimos; Cellpose PyPI externo
fijado en lugar del nombre engañoso; loader verificado durante lifespan;
prints de depuración pasan a logging; un solo procesamiento simultáneo
por proceso en lugar de tres, para acotar memoria CPU; errores de imagen
inválida 400 y fallo interno 500 sin traceback en respuesta. No se arrastra
`KMP_DUPLICATE_LIB_OK=TRUE` del original; el entorno aislado se valida por
imports/startup reales. Estos cambios no ajustan el algoritmo científico.

## Entorno y dependencias

Conda independiente `sicam-saliva-alt`, **Python 3.10.20**.
Los imports propios requieren FastAPI, Uvicorn, python-multipart, NumPy,
SciPy, scikit-image, OpenCV headless y Cellpose. Torch CPU/torchvision y
segment-anything son necesarios para Cellpose-SAM; sus demás dependencias
transitivas se fijan con las versiones resueltas. No se necesitan torchaudio,
requests, GUI, notebooks ni el Cellpose vendorizado para este flujo.
Pytest/httpx son sólo para tests. `constraints.txt` fija las 49 dependencias
del cierre runtime + tests para Linux x86_64/Python 3.10.20; los constraints
de tests no provocan su instalación con el requirements de runtime.
Versiones directas: Torch 2.12.1+cpu, torchvision 0.27.1+cpu, FastAPI 0.141.1,
Uvicorn 0.52.4, python-multipart 0.0.32, NumPy 2.2.6, SciPy 1.15.3,
scikit-image 0.25.2 y OpenCV headless 5.0.0.93. Las versiones API/IO sin
restricción científica se tomaron de los wheels del baseline WSL; se conserva
el pin científico explícito Cellpose 4.0.8 del original.
Véanse requirements y README del servicio para instalación y comandos
reproducibles; no se modifican otros entornos.

## Validación

Los tests sintéticos cubren dimensiones 512×512, 1024×1024 y 320×768,
uint16/labels, eliminación de objetos <200, parámetros eval, anucleadas,
dos núcleos con ID repetido, fallback Otsu, área MN absoluta/relativa y
combinada, polígonos degenerados/coordenadas, RGB, contrato multipart/JSON,
docs/OpenAPI y loader que rechaza versión/hash/tamaño incompatibles.

Validación ejecutada el 2026-09-23:

| Comprobación | Resultado |
|---|---|
| Python del entorno ALT | 3.10.20 |
| Cellpose instalado | 4.0.8, `site-packages/cellpose/models.py`, `MODEL_NAMES=['cpsam']` |
| Backend Torch | 2.12.1+cpu; CUDA no disponible |
| API instalada | Constructor admite `gpu=False`, `pretrained_model='cpsam'`, `use_bfloat16=True`; eval admite los cuatro parámetros originales |
| Tests con modelo simulado | **24 passed**, 2 avisos de deprecación, 2.91 s |
| `pip check` ALT | No broken requirements found |
| `pip check` sicam / sicam-blood | Ambos PASS; sólo lectura |
| Resolución final de requirements con constraints (`--dry-run`) | PASS, todos satisfechos |
| Startup real | PASS; carga el cpsam existente y registra estrategia/versión/modelo/algoritmo/ruta |
| `GET /docs` | HTTP 200 |
| `GET /openapi.json` | HTTP 200 |
| `POST /segmentar`, cpsam real + imagen sintética 384×640 | **HTTP 200 en 139.93 s**, respuesta exacta `{"objetos":[]}` |
| Apagado del servicio temporal | Shutdown completo; proceso finalizado |

Incidencias de ejecución: el portal de threads de TestClient quedó bloqueado
dentro del sandbox de la herramienta; la misma suite fuera del sandbox pasó
sin modificar el código para sortearlo. Starlette emite deprecaciones por
el uso de httpx y el alias BlockingPortal de AnyIO; no son fallos de tests.
La red interrumpió descargas: se reutilizaron wheels del caché en `/tmp` y
se completaron las dependencias faltantes. No se instalaron extras GUI.
Durante inferencia, Cellpose avisó que resizing está deprecated en v4.0.1+
y Torch avisó sobre comprobaciones de invariantes de tensores sparse
desactivadas por defecto. Se conservaron los defaults y parámetros originales;
la inferencia terminó sin error. No se silencian estos avisos.

La imagen de smoke se generó geométricamente en `/tmp/sicam18a-synthetic.png`
(384×640, tres elipses con centros oscuros). No deriva de fotografías ni
datos clínicos. Los assets `muestra-saliva.jpg`/`muestra-sangre.jpeg` de la
fuente no se usaron porque no se acreditó su procedencia no clínica. En ese
momento quedó pendiente un smoke con micrografía real de prueba autorizada;
se cierra en la sección "Real image smoke", sin evaluación científica de calidad.
La respuesta vacía verifica transporte, carga e inferencia completa; **no**
valida detecciones positivas ni coordenadas de polígonos reales. Estas últimas
se verifican en tests sintéticos con máscaras simuladas.

Artefactos de validación locales, no versionados:
`/tmp/sicam18a-docs.html`, `/tmp/sicam18a-openapi.json`,
`/tmp/sicam18a-synthetic.png`, `/tmp/sicam18a-smoke.json`,
`/tmp/sicam18a-dependency-check.txt` y el inventario inicial de la fuente.

## Real image smoke

Ejecutado el **2026-09-23** con la micrografía de prueba proporcionada y
expresamente autorizada para ALT. Identificador no sensible:
`prueba_saliva.jpg.jpeg`. La ruta inicialmente indicada no existía; se
localizó el archivo en la carpeta `nueva_saliva` de la copia fuente. Se leyó
sin modificarlo ni copiarlo al repositorio de trabajo. No se incluyen imagen,
EXIF, JSON, overlay ni datos clínicos en Git.

| Verificación | Resultado |
|---|---|
| Imagen | JPEG, RGB, 3 canales, 4928×4928 píxeles, 15399736 bytes |
| Entorno | Python 3.10.20; Cellpose 4.0.8 por metadata instalada; `MODEL_NAMES=['cpsam']`; pip check PASS |
| Modelo | cpsam, 1233587898 bytes; SHA-256 idéntico al esperado |
| Startup y endpoints | Startup completo; `/docs` y `/openapi.json` HTTP 200 |
| Petición | `POST /segmentar`, multipart `file`, imagen original sin resize externo |
| Respuesta | **HTTP 200**, **178.048302 s**, **3971 bytes** |
| Detecciones | **TOTAL=7; MEMBRANAS=3; NUCLEOS=3; MICRONUCLEOS=1** |
| Contrato | `objetos` lista; cada objeto tiene `id`, `tipo`, `puntos`; tipos permitidos; puntos `[x,y]` numéricos finitos |
| Coordenadas | **OUT_OF_BOUNDS_POINTS=0**; todos cumplen 0<=x<4928 y 0<=y<4928 |
| Polígonos | **DEGENERATE_POLYGONS=0**; listas vacías=0; área cero=0; entre **9 y 106 puntos** por objeto |
| Sanity check núcleos | **NUCLEI_OUTSIDE_MEMBRANES=0** |
| Sanity check MN | **MICRONUCLEI_OUTSIDE_MEMBRANES=0** |
| Shutdown | uvicorn terminó; puerto 8003 libre |

IDs por tipo en esta imagen:

| Tipo | IDs totales | IDs únicos | IDs repetidos |
|---|---:|---:|---|
| membrana | 3 | 3 | Ninguno |
| nucleo | 3 | 3 | Ninguno |
| micronucleo | 1 | 1 | Ninguno |

La ausencia de repetidos en esta muestra no cambia la semántica general:
ALT puede conservar varios componentes con el mismo raw ID por membrana.
Para el sanity check se usó el centroide geométrico aproximado del polígono
(moments de OpenCV) y pertenencia a cualquier membrana, incluyendo borde.
No se recalcularon asociaciones científicas persistentes ni se corrigió la salida.

**Comparación con el original: PASS.** Se ejecutaron sin modificaciones
`seg_pipeline_v2.py` y el conversor original `app/utils/poligonos.py`, leídos
y compilados en memoria desde la copia fuente, con el mismo entorno e imagen.
El proceso corrió desde `/tmp`, con `PYTHONDONTWRITEBYTECODE=1`, sin instalar
dependencias ni generar artefactos en la fuente. Se ejecutó también el loader
original: su nombre `cyto3` resuelve al mismo cache cpsam en Cellpose 4.0.8;
se comprobó la ruta efectiva y el checksum. ALT conserva su carga explícita
verificada, sin adoptar ese fallback.

Conteos originales: 3 membranas, 3 núcleos, 1 MN. Las tres máscaras originales
miden 4928×4928. Coinciden exactamente con ALT los conteos, los IDs por tipo,
los puntos de todos los polígonos y su orden: igualdad del contenido JSON
deserializado, sin requerir igualdad del formato de serialización.
Evidencia temporal: `/tmp/sicam18a-real-original-comparison.json` y
`/tmp/sicam18a-real-original-result.json`. No se compara calidad científica.

Overlay temporal: **`/tmp/sicam18a-real-overlay.png`**, misma resolución que
la imagen original, con membranas verdes, núcleos naranjas y MN magenta,
sin etiquetas de texto. Generación/apertura verificadas; disponible para
inspección humana. Resumen: `/tmp/sicam18a-real-overlay-summary.txt`.
Respuesta íntegra: `/tmp/sicam18a-real-result.json`. Validación detallada,
incluido número de puntos por objeto: `/tmp/sicam18a-real-validation.json`.
Tiempos/status: `/tmp/sicam18a-real-http.json`. Todos son artefactos en `/tmp`.

Cellpose no expone `__version__` en este paquete: se verificó 4.0.8 mediante
`importlib.metadata.version('cellpose')`. Durante inferencia se repitieron
los avisos de resizing deprecated y tensores sparse ya documentados; no hubo
error HTTP ni modificación de defaults. No se cambiaron código, thresholds,
requirements, modelos ni integraciones. En esta tarea sólo se actualizó este
documento; se conservaron los cambios anteriores de Sprint 18A sin staging.
El inventario de la fuente en este smoke contiene **277 entradas**, incluida
la imagen agregada por el usuario antes de esta tarea: contenido, tamaño,
modo y mtime idénticos al finalizar. La imagen original y cpsam siguen
intactos. El inventario de archivos del repositorio de trabajo confirma que
sólo cambió este documento respecto al precheck del smoke. `git diff --check`
pasa; no aparecen artefactos temporales en Git. Ambos procesos de validación
terminaron; el puerto 8003 quedó libre. No se hizo staging, commit ni push.

```text
REAL IMAGE POSITIVE DETECTION = PASS
REAL IMAGE SMOKE = PASS WITH VISUAL REVIEW PENDING
SPRINT 18A = PASS
```

El cierre acredita detecciones positivas, contrato y geometría estructural
válidos, y overlay disponible. La inspección humana permanece pendiente;
no se emite juicio de calidad, sensibilidad, especificidad, precisión ni
comparación científica entre estrategias.

## Archivos y cierre técnico

Creaciones bajo `apps/segmentation-saliva-alt/`:

```text
README.md
requirements.txt
requirements-test.txt
constraints.txt
app/__init__.py
app/main.py
app/services/__init__.py
app/services/segmentador.py
segmentacion_core/__init__.py
segmentacion_core/seg_pipeline_v2.py
segmentacion_core/segmentacion.py
segmentacion_core/poligonos.py
tests/test_pipeline.py
tests/test_service.py
```

Además se crea este documento y se añade únicamente una sección ALT a
`docs/developer_environment_setup_wsl.md`. No se actualiza el handoff histórico
ni documentación anterior ajena al entorno ALT.

Estado esperado al entregar (sin staging):

```text
 M docs/developer_environment_setup_wsl.md
?? apps/segmentation-saliva-alt/
?? docs/58_sprint_18a_alt_saliva_segmentation_service.md
```

`git diff --check` y verificación equivalente de los 15 archivos nuevos:
PASS. Diffs de `apps/segmentation-saliva`, `apps/segmentation-blood` y
`apps/web`: vacíos. Staging: vacío. Sin commit ni push.

Fuente, comprobación inicial de implementación: `git -C /home/israel/repos/sicam-main status --short` vuelve a indicar
`fatal: not a git repository`, como al inicio. La verificación efectiva es
el inventario: las 274 entradas conservan contenido, tamaño, modo y mtime;
ningún archivo añadido, eliminado o modificado. El cache cpsam conserva su
tamaño y SHA-256. **sicam-main no fue modificado.**

```text
SPRINT 18A = PASS
```

Servicio independiente implementado y smoke con micrografía real de prueba
aprobado según los criterios técnicos solicitados. Overlay disponible para
revisión visual humana. Este cierre no autoriza la integración con Django
o frontend ni constituye una validación de calidad científica.
