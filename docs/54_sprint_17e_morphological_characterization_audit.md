# Sprint 17E - Auditoria exhaustiva de caracterizacion morfologica legacy

## 1. Proposito

Este documento cierra la auditoria read-only de caracterizacion morfologica
legacy antes de continuar con la pestana `Analisis`.

La auditoria busca separar tres cosas:

- lo que existe como codigo ejecutable;
- lo que existe como UI, documento historico o placeholder;
- lo que requiere decision cientifica antes de implementarse en
  `sicam-refactor`.

No se modifico codigo fuente, modelos, endpoints, migraciones, frontend ni
microservicios.

## 2. Estado Git de inicio

Antes de crear este documento, `sicam-refactor` estaba limpio:

```text
git status --short
<sin salida>
```

Por esa razon se permite crear este reporte en:

```text
docs/54_sprint_17e_morphological_characterization_audit.md
```

## 3. Repositorios encontrados

Directorio base inspeccionado:

```text
C:\Users\israe\OneDrive - Universidad de Guadalajara\Documents\SICAM
```

| Repo | Path | Branch | Remote |
|---|---|---|---|
| `sicam-refactor` | `...\SICAM\sicam-refactor` | `master` | `https://github.com/irgNemo/sicam-refactor.git` |
| `micronucleos-web` | `...\SICAM\micronucleos-web` | `main` | `https://github.com/Ericsson2004/micronucleos-web.git` |
| `Segmentacion_web` | `...\SICAM\Segmentacion_web` | `main` | `https://github.com/RobbertRios/Segmentacion_web.git` |
| `segmentacion_sangre` | `...\SICAM\segmentacion_sangre` | `main` | `https://github.com/RobbertRios/segmentacion_sangre.git` |

Tambien existen carpetas locales `docs` e `imagenes`, pero no se identificaron
como repositorios Git en esta inspeccion.

## 4. Arquitectura real de `micronucleos-web`

`micronucleos-web` contiene:

- `Backend`: Django + Django REST Framework.
- `Frontend`: Vue.
- `Funciones_de_Segmentacion_en_models_py.ipynb`: notebook explicativo de
  Cellpose/segmentacion, no modulo runtime de caracterizacion web.

### Backend

Archivos relevantes:

- `micronucleos-web/Backend/api/models.py`
- `micronucleos-web/Backend/api/serializers.py`
- `micronucleos-web/Backend/api/views.py`
- `micronucleos-web/Backend/api/urls.py`
- `micronucleos-web/Backend/api/tests.py`

Modelos encontrados:

- `Paciente`
- `Caso`
- `AnalisisPred`
- `MuestraSaliva`
- `ResultadoAnalisis`

`ResultadoAnalisis` guarda solo conteos:

```text
nucleos
micronucleos
membranas
fecha_analisis
```

No contiene campos morfometricos como area, intensidad, redondez, distancia,
fracciones, circularidad media o tamano medio.

`views.py` registra viewsets para pacientes, casos, analisis y muestras. No se
encontro endpoint de caracterizacion morfologica ni endpoint de CSV/PDF.

`tests.py` contiene solo el esqueleto generado por Django:

```text
from django.test import TestCase

# Create your tests here.
```

### Frontend

Archivos relevantes:

- `micronucleos-web/Frontend/src/components/MainContent.vue`
- `micronucleos-web/Frontend/src/App.vue`
- `micronucleos-web/Frontend/src/components/TopBar.vue`

`MainContent.vue` contiene botones visibles:

```text
Exportar CSV
Generar PDF
```

No se encontro handler funcional asociado para generar CSV/PDF.

`App.vue` contiene una seccion `caracterizacion` como placeholder. No se
encontro la tabla "Resultados por Membrana" ni calculos morfologicos.

## 5. Coincidencia con la captura legacy

Se buscaron literalmente estas cadenas en repositorios locales:

- `Membranas analizadas`
- `Total micronucleos`
- `Frecuencia`
- `Frecuencia uN`
- `Circularidad media`
- `Tamano medio`
- `Distribucion de Estructuras`
- `Resultados por Membrana`
- `Area Nucleo`
- `Area MN`
- `Int. Nucleo`
- `Int. MN`
- `Redondez N.`
- `Redondez MN`
- `Distancia`
- `Fra. Area`
- `Fra. Int.`
- `Celulas con alerta`
- `Exportar CSV`
- `Generar PDF`
- variantes de `micronucleo`, `MN` y `uN`

Resultado:

| Cadena / familia | Resultado | Estado |
|---|---|---|
| `Exportar CSV` | Encontrado en `micronucleos-web/Frontend/src/components/MainContent.vue` y en el refactor heredado | UI LEGACY / PLACEHOLDER |
| `Generar PDF` | Encontrado en `micronucleos-web/Frontend/src/components/MainContent.vue` y en el refactor heredado | UI LEGACY / PLACEHOLDER |
| Tabla `Resultados por Membrana` | No encontrada | NO IMPLEMENTADO EN REPOS LOCALES |
| Columnas `Area Nucleo`, `Area MN`, `Int. Nucleo`, `Int. MN`, `Redondez`, `Distancia`, `Fra. Area`, `Fra. Int.` | No encontradas como strings ni headers | NO IMPLEMENTADO EN REPOS LOCALES |
| Resumen `Membranas analizadas`, `Frecuencia uN`, `Circularidad media`, `Tamano medio` | No encontrado | NO IMPLEMENTADO EN REPOS LOCALES |
| `Celulas con alerta (uN >= 2)` | No encontrado | NO IMPLEMENTADO EN REPOS LOCALES |

Conclusion: la captura no corresponde a una implementacion localizada en los
repositorios disponibles. Con la evidencia actual debe clasificarse como
mockup, prototipo externo o implementacion no presente localmente. No se debe
asumir que sus formulas existen en `micronucleos-web`.

## 6. Flujo legacy SALIVA encontrado

La implementacion cientifica mas completa encontrada esta en
`Segmentacion_web`, principalmente en:

- `segmentacion_core/controller/controllerroot.py`
- `segmentacion_core/model/folder.py`
- `segmentacion_core/model/mask.py`
- `segmentacion_core/model/nuclei.py`
- `segmentacion_core/model/micronuclei.py`
- `segmentacion_core/model/cytoplasm.py`
- `app/routers/segmentacion.py`
- `app/services/segmentador.py`
- `app/utils/poligonos.py`

Pipeline PySide legacy:

```text
imagenes RGB
-> CellposeModel(model_type=None, pretrained_model=membranas_500_125)
-> model.eval(images, diameter=125, channels=[[1, 0]])
-> Mask(masks[i], Mask.CYTOPLASM)
-> mask_cytoplasm.add_elements()
-> mask_cytoplasm.select_elements()
-> mask_nucleus.add_elements(cytoplasms=...)
-> mask_nucleus.select_elements(img=..., cytoplasms=...)
-> mask_micronucleus.add_elements(cytoplasms=...)
-> mask_micronucleus.select_elements(img=..., cytoplasms=...)
-> conteos por imagen
-> indices por carpeta
-> reporte .xlsx
```

Microservicio SALIVA:

```text
POST /segmentar
-> {"objetos": [{ "id": int, "tipo": "membrana|nucleo|micronucleo", "puntos": [...] }]}
```

## 7. Flujo legacy/current BLOOD encontrado

La implementacion de sangre esta en `segmentacion_sangre`:

- `main.py`
- `app/routers/segmentacion.py`
- `app/services/segmentador.py`
- `app/utils/poligonos.py`
- `segmentacion_core/sicam_master.py`

Endpoint real:

```text
POST /api/v1/segmentar
multipart file: UploadFile = File(...)
```

Salida real:

```json
{
  "objetos": [
    { "id": 1, "tipo": "membrana", "puntos": [[x, y]] },
    { "id": 1, "tipo": "micronucleo", "puntos": [[x, y]] }
  ]
}
```

`sicam_master.py` produce:

```text
"celulas": masks_celulas.astype(np.uint16)
"micronucleos": masks_micronucleos.astype(np.uint16)
```

El router mapea:

```text
resultado["celulas"]      -> "membrana"
resultado["micronucleos"] -> "micronucleo"
```

No se encontro caracterizacion morfologica posterior para BLOOD; las reglas de
z-score, DBSCAN e intensidad son parte del detector de micronucleos.

## 8. Tabla de metricas auditadas

| Metrica | Repo | Archivo / funcion | Estructura | Entrada | Salida | Formula exacta encontrada | Unidad | Consumidor | Estado | Test | Portabilidad |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Membranas analizadas | `Segmentacion_web` | `controllerroot.py::__write_resume`, `folder.py::calculate_indices` | citoplasmas/celulas validas | `mask_cytoplasm.elements` | conteo | `len(mask_cytoplasm.elements)` despues de filtros | conteo | UI PySide/XLSX | LEGACY | No | PORTABLE_WITH_ADAPTATION |
| Total micronucleos | `Segmentacion_web` | `mask.py::select_elements`, `controllerroot.py` | micronucleos validos | `Micronuclei.is_a_element()` | conteo | suma de `mask_micronucleus.total_micronucleus` | conteo | UI PySide/XLSX | LEGACY | No | PORTABLE_WITH_ADAPTATION |
| Frecuencia uN | `Segmentacion_web` | `folder.py::calculate_indices` | estudio/carpeta | micronucleos, citoplasmas | indice | `micronucleus / cytoplasm` | ratio, no porcentaje | UI PySide/XLSX | LEGACY | No | PORTABLE_WITH_DECISION |
| Frecuencia uN de captura | No encontrado | No encontrado | resumen UI | no disponible | no disponible | `17 / 78 * 100` es compatible con captura, pero no esta implementado | porcentaje no demostrado | No encontrado | PROTOTYPE/UNKNOWN | No | REQUIRES_DECISION |
| Indice de genotoxicidad actual | `sicam-refactor` | `api/services/characterization/saliva.py::characterize_saliva_result` | resultado efectivo | counts `micronucleo`, `membrana` | indice | `micronuclei / membranes if membranes else None` | ratio | API/Frontend | ACTIVE | Si | ACTIVE |
| Indice de citotoxicidad legacy | `Segmentacion_web` | `folder.py::calculate_indices` | estudio/carpeta | binucleadas, trinucleadas, citoplasmas | indice | `(binucleate + trinucleate) / cytoplasm` | ratio | UI PySide/XLSX | LEGACY | No | REQUIRES_ASSOCIATION |
| Area Nucleo | `Segmentacion_web` | `model/nuclei.py::is_a_element` | nucleo candidato | contorno OpenCV | variable auxiliar | `cv2.contourArea(contours[i])` | px^2 | filtro de segmentacion | CALLED INDIRECTLY | No | PORTABLE_WITH_ADAPTATION |
| Area MN | `Segmentacion_web` | `model/micronuclei.py::is_a_element` | micronucleo candidato | contorno OpenCV | variable auxiliar | `cv2.contourArea(contours[i])` | px^2 | filtro de segmentacion | CALLED INDIRECTLY | No | PORTABLE_WITH_ADAPTATION |
| Fra. Area | `Segmentacion_web` | `model/micronuclei.py::__area_is_valid` | micronucleo vs nucleo/citoplasma | area MN, area nucleo guardada en `cytoplasm.area` | booleano | `area_micronuclei / area_nuclei`; valido si `0.08 < proportion < .33` | ratio | filtro de deteccion | CALLED INDIRECTLY | No | REQUIRES_SCIENTIFIC_DECISION |
| Proporcion nucleo/citoplasma | `Segmentacion_web` | `model/nuclei.py::__area_is_valid` | nucleo candidato | area nucleo, area citoplasma | booleano | `area_nuclei / area_cyto`; valido si `0.01 < proportion < .1` | ratio | filtro de deteccion | CALLED INDIRECTLY | No | REQUIRES_SCIENTIFIC_DECISION |
| Intensidad Nucleo | No encontrado como metrica final | No encontrado | no disponible | no disponible | no disponible | No se encontro media de intensidad 0-1 o 0-255 para nucleo | no demostrada | No encontrado | NOT_FOUND | No | UNKNOWN |
| Intensidad MN | No encontrado como metrica final | No encontrado | no disponible | no disponible | no disponible | No se encontro media de intensidad 0-1 o 0-255 para micronucleo | no demostrada | No encontrado | NOT_FOUND | No | UNKNOWN |
| Fra. Int. | No encontrado | No encontrado | no disponible | no disponible | no disponible | No se encontro `IntMN / IntNucleo` | no demostrada | No encontrado | NOT_FOUND | No | REQUIRES_DECISION |
| Redondez Nucleo | `Segmentacion_web` | `model/nuclei.py::__is_ellipse` | nucleo candidato | contorno | booleano | XOR contra elipse ideal; valido si `img_result.sum() / pixels * 100 < 15` | porcentaje de diferencia, no redondez 0-1 | filtro de deteccion | CALLED INDIRECTLY | No | REQUIRES_DECISION |
| Redondez MN | `Segmentacion_web` | `model/micronuclei.py::__is_ellipse` | micronucleo candidato | contorno | booleano | XOR contra elipse ideal; valido si `img_result.sum() / pixels * 100 < 16` | porcentaje de diferencia, no redondez 0-1 | filtro de deteccion | CALLED INDIRECTLY | No | REQUIRES_DECISION |
| Circularidad BLOOD | `segmentacion_sangre` | `sicam_master.py::_detectar_micronucleos` | cluster candidato | contorno de cluster | booleano | `4 * np.pi * area / perimetro ** 2`; valido si `>= 0.5` | adimensional | filtro de deteccion | ACTIVE MICROSERVICE | No | REQUIRES_DECISION |
| Circularidad media | No encontrado como salida | No encontrado | resumen UI | no disponible | no disponible | No se encontro promedio de circularidad | no demostrada | No encontrado | NOT_FOUND | No | REQUIRES_DECISION |
| Tamano medio | No encontrado | No encontrado | resumen UI | no disponible | no disponible | No se encontro promedio de area/tamano | no demostrada | No encontrado | NOT_FOUND | No | REQUIRES_DECISION |
| Perimetro | `sicam-refactor` / `segmentacion_sangre` | `characterization/geometry.py::polygon_perimeter`, `sicam_master.py` | poligono / cluster | puntos o contorno | helper/intermedio | suma de distancias entre vertices; o `cv2.arcLength(contour, True)` en BLOOD | px | tests/helper o filtro | PARTIAL/INTERMEDIATE | Si en refactor helper | PORTABLE |
| Centroide | No encontrado | No encontrado | no disponible | no disponible | no disponible | No se encontro `cv2.moments`, centroide de mascara o promedio de puntos como metrica | no demostrada | No encontrado | NOT_FOUND | No | PORTABLE_WITH_DECISION |
| Distancia | No encontrado | No encontrado | no disponible | no disponible | no disponible | No se encontro distancia nucleo-MN | no demostrada | No encontrado | NOT_FOUND | No | REQUIRES_ASSOCIATION |
| Celulas con alerta `uN >= 2` | No encontrado | No encontrado | celula/membrana | no disponible | no disponible | No se encontro regla `micronucleos_en_celula >= 2` | conteo no demostrado | No encontrado | NOT_FOUND | No | REQUIRES_ASSOCIATION |

## 9. Formulas exactas confirmadas

### Legacy SALIVA

Conteos por imagen:

```text
citoplasmas = len(mask_cytoplasm.elements)
nucleos = mask_nucleus.total_elements
binucleadas = mask_nucleus.total_binucleate
trinucleadas = mask_nucleus.total_trinucleate
micronucleos = mask_micronucleus.total_micronucleus
```

Indices por carpeta:

```text
cytotoxicity_index = (binucleate + trinucleate) / cytoplasm
genotoxicity_index = micronucleus / cytoplasm
```

Si `cytoplasms == 0`, `ControllerRoot.__create_report()` escribe:

```text
Indeterminacion
```

Reglas de deteccion/filtro:

```text
area_nuclei / area_cyto
valido si 0.01 < proportion < .1

area_micronuclei / area_nuclei
valido si 0.08 < proportion < .33

nucleo: diferencia contra elipse ideal < 15
micronucleo: diferencia contra elipse ideal < 16

color nuclear:
area_mask_color * 100 / area_micronuclei > 60
```

Estas reglas son filtros de segmentacion/deteccion, no metricas descriptivas
versionadas ni criterios para eliminar objetos de una `RevisionSegmentacion`
validada por experto.

### BLOOD

Reglas internas del detector de micronucleos:

```text
UMBRAL_ZSCORE_CELULA = 8
UMBRAL_ZSCORE_PIXEL = 3
MIN_PIXELES_CLUSTER = 5
MIN_PUNTOS_CLUSTER = 6
CIRCULARIDAD_MINIMA = 0.5
DBSCAN_EPS = 2.5
DBSCAN_MIN_SAMPLES = 4

z_celula = 0.6745 * (max(pixeles) - mediana) / mad
z_pixel = 0.6745 * (intensidades - mediana) / mad
circularidad = 4 * np.pi * area / perimetro ** 2
```

Estas reglas clasifican candidatos durante segmentacion. No se persisten como
caracterizacion ni se exponen como tabla final.

### Refactor actual

`sicam-refactor` implementa:

```text
SALIVA:
counts por label
genotoxicity_index = micronuclei / membranes if membranes else None
cytotoxicity_index = None

BLOOD:
counts por label
indices = {}
```

El backend usa resultado efectivo:

```text
VALIDADA mas reciente > AUTOMATICO
BORRADOR nunca se usa para caracterizacion oficial
```

## 10. Unidades y calibracion

No se encontro una calibracion fisica pixel -> micrometro en codigo local.

Busquedas realizadas incluyeron:

```text
micron
micrometer
micrometre
um
um_per_pixel
microns_per_pixel
pixel_size
pixel_spacing
scale
calibration
calibracion
resolution
dpi
magnification
objective
40x
100x
```

Resultado:

- areas legacy calculadas con OpenCV estan en pixeles cuadrados (`px^2`);
- distancias no fueron encontradas como metrica;
- `sicam-refactor` no convierte a `um` ni `um^2`;
- la unidad `um^2` visible en la captura no esta soportada por el codigo
  auditado.

No se debe inventar una conversion fisica. Para reportar `um` o `um^2` se
requiere definir fuente de calibracion, magnificacion, tamano de pixel o metadata
de adquisicion.

## 11. Asociacion membrana -> nucleo -> micronucleo

### SALIVA

La asociacion legacy no usa IDs persistentes tipo `#27.1`. Usa listas y recortes:

```text
for nuclei, cyto in zip(elementos_nuclei, elementos_cytoplasm):
    n_nucleos = nuclei.is_a_element(img=imagen_rgb, cytoplasm=cyto)
```

Para micronucleos:

```text
for cyto in elementos_cytoplasm:
    if cyto.color_nuclei is None:
        continue
    micro = Micronuclei(mask=cyto.mask, pos_x=cyto.pos_x, pos_y=cyto.pos_y)
    n_micro = micro.is_a_element(img=imagen_rgb, cytoplasm=cyto)
```

La relacion micronucleo-nucleo no esta representada como FK, ID o mapeo directo.
El nucleo aceptado deja informacion auxiliar en el citoplasma:

```text
cytoplasm.area = area_nuclei
cytoplasm.color_nuclei = [min_hue, max_hue]
```

Luego el micronucleo se acepta si su area relativa y color son compatibles.

### BLOOD

Los micronucleos se detectan dentro de mascaras celulares candidatas, pero la
salida final solo expone objetos `membrana` y `micronucleo`. No hay `nucleo` en
el contrato BLOOD.

### IDs `#27.1` / `#27.2`

No se encontro codigo que genere IDs de fila como:

```text
#27.1
#27.2
```

La hipotesis `#27 = membrana/celula 27`, `#27.1 = micronucleo 1 de celula 27`
es plausible por la captura, pero no esta confirmada por codigo local. Debe
tratarse como decision de diseno pendiente, no como contrato legacy recuperado.

## 12. CSV, PDF y XLSX

### CSV

No se encontro implementacion real de exportacion CSV con headers:

```text
ID
AreaNucleo
AreaMN
IntensidadNucleo
IntensidadMN
RedondezNucleo
RedondezMN
Distancia
FraccionArea
FraccionIntensidad
```

`Exportar CSV` existe como boton de UI en `MainContent.vue`, pero no se encontro
handler funcional.

### PDF

No se encontro generacion PDF funcional, template PDF ni dependencia dedicada
para reportes PDF en los repos auditados.

`Generar PDF` existe como boton de UI en `MainContent.vue`, pero no se encontro
handler funcional.

### XLSX

`Segmentacion_web/segmentacion_core/controller/controllerroot.py::__create_report`
usa `openpyxl.Workbook()` y guarda:

```text
<folder_name>.xlsx
```

Columnas:

```text
Grupo
Imagen
Citoplasmas
Nucleos
Binucleadas
Trinucleadas
Micronucleos
```

Celdas iniciales:

```text
B1 = indice de citotoxicidad
B2 = indice de genotoxicidad
```

Este reporte no contiene la tabla morfologica por membrana de la captura.

## 13. Codigo activo vs legacy

| Componente | Funcion / archivo | Clasificacion | Motivo |
|---|---|---|---|
| `sicam-refactor` backend | `api/services/characterization/service.py` | ACTIVE | Consumido por endpoint `POST /api/resultados-segmentacion/{id}/caracterizar/`. |
| `sicam-refactor` backend | `api/services/characterization/saliva.py` | ACTIVE | Calcula conteos e indice de genotoxicidad SALIVA. |
| `sicam-refactor` backend | `api/services/characterization/geometry.py` | PARTIAL | Tiene helpers de area/perimetro con tests, pero no se integran aun al servicio de caracterizacion. |
| `sicam-refactor` frontend | `src/views/CaracterizacionView.vue` | ACTIVE | Pestana actual de caracterizacion consume API y muestra conteos/indices. |
| `micronucleos-web` frontend | `src/App.vue` caracterizacion | PROTOTYPE/PLACEHOLDER | No ejecuta caracterizacion. |
| `micronucleos-web` frontend | botones CSV/PDF | UI LEGACY/PLACEHOLDER | Sin handlers encontrados. |
| `Segmentacion_web` PySide | `ControllerRoot.__write_resume` | LEGACY | UI desktop previa. |
| `Segmentacion_web` PySide | `ControllerRoot.__create_report` | LEGACY | Genera XLSX. |
| `Segmentacion_web` modelos | `Nuclei`, `Micronuclei`, `Mask`, `Folder` | LEGACY CALLED INDIRECTLY | Usados por pipeline legacy y microservicio saliva heredado. |
| `segmentacion_sangre` | `sicam_master.py` | ACTIVE MICROSERVICE | Segmentacion real BLOOD. |

## 14. Comparacion con `sicam-refactor`

| Metrica legacy / captura | Existe en refactor | Falta | Portable | Requiere adaptacion | Requiere decision cientifica |
|---|---:|---:|---:|---:|---:|
| Conteo `membrana` SALIVA | Si | No | Si | No | No |
| Conteo `nucleo` SALIVA | Si | No | Si | No | No |
| Conteo `micronucleo` SALIVA | Si | No | Si | No | No |
| Conteo `membrana` BLOOD | Si | No | Si | No | No |
| Conteo `micronucleo` BLOOD | Si | No | Si | No | No |
| `genotoxicity_index` SALIVA | Si | Parcial | Si | Si: denominator legacy `cytoplasm`, actual `membrana` | Si: ratio vs porcentaje |
| `cytotoxicity_index` SALIVA | No | Si | No directo | Si: requiere binucleada/trinucleada desde poligonos | Si |
| Area Nucleo | Helper parcial | Si | Si | Si | Si: unidad y objeto valido |
| Area MN | Helper parcial | Si | Si | Si | Si: unidad y objeto valido |
| Intensidad Nucleo | No | Si | No sin imagen | Si: requiere imagen original y mascara/poligono rasterizado | Si |
| Intensidad MN | No | Si | No sin imagen | Si | Si |
| Redondez Nucleo | No | Si | Si | Si | Si: formula exacta |
| Redondez MN | No | Si | Si | Si | Si |
| Distancia Nucleo-MN | No | Si | No directo | Si: requiere asociacion | Si |
| Fra. Area | No | Si | Si | Si | Si |
| Fra. Int. | No | Si | No sin intensidad | Si | Si |
| Frecuencia uN `%` | No | Si | Si | Si | Si: denominator y escala |
| Circularidad media | No | Si | Si | Si | Si: estructura promediada |
| Tamano medio `um^2` | No | Si | No sin calibracion | Si | Si |
| Celulas con alerta `uN >= 2` | No | Si | No directo | Si: asociacion por celula | Si |
| CSV/PDF | No | Si | Si | Si | Si: formato oficial |

## 15. Portabilidad sobre resultado efectivo

Clasificacion:

| Elemento | Fuente necesaria | Clasificacion | Comentario |
|---|---|---|---|
| Conteos por label | `effective.resultado.objects[].label` | PORTABLE | Ya implementado. |
| Area por poligono | `geometry.points` | PORTABLE | Se puede calcular en px^2 con shoelace; falta integrar. |
| Perimetro por poligono | `geometry.points` | PORTABLE | Helper existe; falta integrar. |
| Centroide | `geometry.points` | PORTABLE_WITH_DECISION | Falta decidir formula: centroide poligonal, promedio de vertices o mascara. |
| Redondez/circularidad | area + perimetro | PORTABLE_WITH_DECISION | Debe decidirse si usar `4*pi*area/perimeter^2` o formula legacy eliptica. |
| Intensidad | imagen original + poligono rasterizado | PORTABLE_WITH_ADAPTATION | Requiere leer imagen y definir canal/normalizacion. |
| Distancia nucleo-MN | centroide + asociacion | REQUIRES_ASSOCIATION | No hay regla confirmada en codigo web. |
| Fra. Area | areas nucleo/MN asociados | REQUIRES_ASSOCIATION | Requiere definir emparejamiento. |
| Fra. Int. | intensidades nucleo/MN asociados | REQUIRES_ASSOCIATION | Requiere intensidad y emparejamiento. |
| Frecuencia uN | conteos + denominador | REQUIRES_DECISION | Legacy usa ratio; captura sugiere porcentaje. |
| Tamano medio `um^2` | areas + calibracion | NOT_PORTABLE sin calibracion | No hay pixel->um. |
| Alerta `uN >= 2` | micronucleos por membrana/celula | REQUIRES_ASSOCIATION | La constante 2 no esta implementada localmente. |

Principio para revisiones validadas:

```text
RevisionSegmentacion VALIDADA = estructura experta oficial.
No debe eliminarse un objeto validado porque falle un filtro automatico legacy.
Si se implementa caracterizacion morfologica, debe medir objetos efectivos.
Deteccion/filtrado y medicion descriptiva deben permanecer separados.
```

## 16. SALIVA vs BLOOD

| Metrica | SALIVA | BLOOD | Nota |
|---|---:|---:|---|
| Conteos por label | Si | Si | Labels distintos por tipo. |
| Genotoxicidad | Parcial | No definido | SALIVA implementa ratio `micronucleo/membrana`; BLOOD no tiene regla. |
| Citotoxicidad | Legacy PySide | No encontrado | SALIVA requiere binucleada/trinucleada. |
| Area por objeto | Posible | Posible | Desde poligonos, pero unidad px^2. |
| Intensidad | Requiere decision | Requiere decision | BLOOD usa intensidad para detectar, no para caracterizar. |
| Redondez/circularidad | Requiere decision | Requiere decision | BLOOD tiene circularidad interna solo para clusters MN. |
| Distancia nucleo-MN | Requiere decision | No aplica/unknown | BLOOD no expone nucleo. |
| Alerta `uN >= 2` | Requiere asociacion | Requiere asociacion | No implementada. |

No se deben portar reglas SALIVA a BLOOD por analogia.

## 17. Respuestas puntuales A-Q

### A. `micronucleos-web` contiene la implementacion?

No. Contiene modelos y UI basica heredada, pero no la implementacion historica
de metricas morfologicas de la captura.

### B. La captura corresponde a codigo real o mockup?

No corresponde a codigo real localizado. Con la evidencia disponible se
clasifica como mockup/prototipo externo o implementacion ausente localmente.

### C. Formulas exactas de la captura

| Formula solicitada | Estado |
|---|---|
| Area nucleo | Solo encontrada como auxiliar legacy: `cv2.contourArea(contours[i])`, px^2, filtro de deteccion. |
| Area MN | Solo encontrada como auxiliar legacy: `cv2.contourArea(contours[i])`, px^2, filtro de deteccion. |
| Intensidad nucleo | No encontrada como metrica final. |
| Intensidad MN | No encontrada como metrica final. |
| Redondez nucleo | No encontrada como `4*pi*area/perimeter^2`; legacy usa comparacion contra elipse ideal con tolerancia 15. |
| Redondez MN | No encontrada como metrica final; legacy usa comparacion contra elipse ideal con tolerancia 16. |
| Distancia | No encontrada. |
| Fraccion area | Encontrada como filtro: `area_micronuclei / area_nuclei`, valido si `0.08 < proportion < .33`; no salida de UI. |
| Fraccion intensidad | No encontrada. |
| Frecuencia uN | Legacy: `micronucleus / cytoplasm`; captura sugiere `micronucleos / membranas * 100`, pero no esta implementado. |
| Circularidad media | No encontrada. |
| Tamano medio | No encontrado. |
| Alerta `uN >= 2` | No encontrada. |

### D. Perimetro y centroide

- Perimetro: existe como helper actual `polygon_perimeter(points)` en
  `sicam-refactor`, y como intermedio de circularidad BLOOD con
  `cv2.arcLength(contours[0], True)`. No aparece como output de usuario.
- Centroide: no se encontro como output ni intermedio confirmado.

### E. Asociacion membrana/nucleo/MN

SALIVA legacy asocia por recorte y listas paralelas de citoplasmas. No hay mapa
persistente membrana->nucleo->MN. BLOOD no expone nucleo.

### F. IDs `#27.1` / `#27.2`

No se encontro generador de esos IDs. La semantica queda no demostrada.

### G. Unidad real de areas/distancias

Areas encontradas: `px^2`. Distancias: no encontradas. No hay evidencia de `um`.

### H. Calibracion `um`

No encontrada.

### I. CSV real

No encontrado. Solo boton placeholder.

### J. PDF real

No encontrado. Solo boton placeholder.

### K. Reglas area/ellipse/HSV

| Regla | Valor | Categoria |
|---|---|---|
| `area_nuclei / area_cyto` | `0.01 < proportion < .1` | deteccion/filtering |
| `area_micronuclei / area_nuclei` | `0.08 < proportion < .33` | deteccion/filtering |
| diferencia nucleo vs elipse ideal | `< 15` | deteccion/filtering |
| diferencia MN vs elipse ideal | `< 16` | deteccion/filtering |
| color HSV MN similar a nucleo | `area_mask_color * 100 / area_micronuclei > 60` | deteccion/filtering |

### L. Funciones/archivos/lineas clave

- `Segmentacion_web/segmentacion_core/model/nuclei.py`: area nucleo,
  proporcion area/citoplasma, tolerancia eliptica nucleo y HSV nuclear.
- `Segmentacion_web/segmentacion_core/model/micronuclei.py`: area MN,
  proporcion area MN/nucleo, tolerancia eliptica MN y filtro de color.
- `Segmentacion_web/segmentacion_core/model/mask.py`: conteos de nucleos,
  binucleadas, trinucleadas y micronucleos.
- `Segmentacion_web/segmentacion_core/model/folder.py`: indices de citotoxicidad
  y genotoxicidad.
- `Segmentacion_web/segmentacion_core/controller/controllerroot.py`: resumen UI
  PySide y reporte `.xlsx`.
- `segmentacion_sangre/segmentacion_core/sicam_master.py`: z-score, DBSCAN y
  circularidad interna para micronucleos de sangre.
- `sicam-refactor/apps/web/Backend/api/services/characterization/saliva.py`:
  conteos e indice de genotoxicidad actual.
- `sicam-refactor/apps/web/Backend/api/services/characterization/service.py`:
  resultado efectivo y persistencia de `ResultadoCaracterizacion`.
- `sicam-refactor/apps/web/Backend/api/services/characterization/geometry.py`:
  helpers de area y perimetro de poligonos.

### M. Active vs legacy

La caracterizacion oficial activa esta en `sicam-refactor`. El codigo PySide de
`Segmentacion_web` es legacy. El microservicio de sangre esta activo para
segmentacion, no para caracterizacion morfologica.

### N. Que falta en `sicam-refactor`

- morfometria por objeto;
- asociacion membrana->nucleo->micronucleo desde resultado efectivo;
- centroide/distancia;
- intensidad sobre imagen original;
- fracciones area/intensidad;
- frecuencia `uN` con escala definida;
- circularidad media;
- tamano medio;
- alerta `uN >= 2`;
- CSV/PDF reales;
- calibracion fisica pixel->um.

### O. Que puede portarse sin cambios cientificos

- conteos por label;
- lectura de resultado efectivo `VALIDADA > AUTOMATICO`;
- persistencia versionada de `ResultadoCaracterizacion`;
- area/perimetro en pixeles si se documenta como medicion geometrica, no como
  diagnostico.

### P. Que requiere decision cientifica

- denominador de frecuencia `uN`;
- ratio vs porcentaje;
- formula de redondez/circularidad;
- definicion de tamano medio;
- conversion a `um`/`um^2`;
- canal y normalizacion de intensidad;
- asociacion nucleo-MN;
- semantica de IDs `#27.1`;
- alerta `uN >= 2`;
- alcance SALIVA/BLOOD.

### Q. Git status

Despues de crear este documento, el cambio esperado es solo:

```text
?? docs/54_sprint_17e_morphological_characterization_audit.md
```

## 18. Decision recomendada para siguientes sprints

No implementar la captura literalmente todavia. Primero abrir una decision
cientifica de contrato morfologico con:

1. unidad oficial (`px`, `px^2`, `um`, `um^2`);
2. calibracion requerida o declaracion explicita de ausencia de calibracion;
3. estructura de asociacion membrana/nucleo/MN;
4. formula de redondez/circularidad;
5. definicion de frecuencia `uN`;
6. definicion de alerta `uN >= 2`;
7. si BLOOD comparte metricas o solo conteos;
8. formato final de CSV/PDF.

## 19. Conclusion

Sprint 17E audit = PASS CON LIMITACIONES.

La auditoria encontro caracterizacion SALIVA legacy basada en conteos,
binucleadas/trinucleadas, micronucleos, citotoxicidad y genotoxicidad en un
flujo PySide/XLSX. No encontro la interfaz morfologica de la captura como codigo
real en los repos locales. Tampoco encontro CSV/PDF reales, calibracion
micrometrica, tabla por membrana ni formulas persistidas para intensidad,
distancia, redondez, fracciones, circularidad media o tamano medio.

El refactor actual esta correctamente posicionado para implementar
caracterizacion sobre resultado efectivo, pero las metricas morfologicas de la
captura requieren decisiones cientificas antes de codificarse.

## 20. Adenda Sprint 17E.1 - reauditoria dirigida de `backend/creacion`

### 20.1 Proposito de la adenda

Esta adenda corrige la conclusion documental anterior para el caso especifico
del branch remoto `origin/backend/creacion` de `micronucleos-web`.

La auditoria original de Sprint 17E reviso el estado local de `main` y, con esa
evidencia, clasifico la captura de caracterizacion como mockup o codigo no
presente localmente. La reauditoria dirigida encontro que
`origin/backend/creacion` si contiene una implementacion ejecutable de
caracterizacion morfologica y una vista Vue que coincide con la captura.

No se hizo checkout, no se modifico codigo, no se portaron algoritmos y no se
hizo commit.

### 20.2 Referencia Git auditada

Repositorio:

```text
C:\Users\israe\OneDrive - Universidad de Guadalajara\Documents\SICAM\micronucleos-web
```

Branch remoto auditado:

```text
origin/backend/creacion
```

Hash remoto verificado:

```text
9d9d39a4f81957d7825dc011451634cf98c23d53
```

`git ls-remote --heads origin` reporto:

```text
refs/heads/backend/creacion 9d9d39a4f81957d7825dc011451634cf98c23d53
```

### 20.3 Evidencia backend encontrada

`origin/backend/creacion:Backend/api/urls.py` registra el endpoint real:

```text
GET /api/casos/<int:id_caso>/caracterizacion/
```

Funcion:

```text
caracterizacion_caso
```

Evidencia:

- `Backend/api/urls.py:59`: `path('casos/<int:id_caso>/caracterizacion/', caracterizacion_caso, name='caracterizacion-caso')`.
- `Backend/api/views.py:672`: `_distancia_euclidea`.
- `Backend/api/views.py:676`: `_calcular_metricas_objeto`.
- `Backend/api/views.py:723`: `_caracterizar_muestra`.
- `Backend/api/views.py:793`: `caracterizacion_caso`.

Tambien existe generacion de overlay PNG:

```text
GET /api/mascaras/<int:id_analisis>/overlay/?offset=<n>&filtrar_vacios=true
```

Funciones asociadas:

- `_dibujar_mascaras`
- `_filtrar_membranas_vacias`
- `obtener_mascara_png`

La caracterizacion legacy de este branch es exclusiva para SALIVA en la ruta
auditada: `caracterizacion_caso` omite muestras cuyo `tipo_muestra` sea
`sangre`.

### 20.4 Evidencia frontend encontrada

`origin/backend/creacion:Frontend/src/views/CaracterizacionView.vue` contiene
una pantalla real de caracterizacion que coincide con la captura legacy:

- KPI cards: `Membranas analizadas`, `Total micronucleos`, `Frecuencia uN`,
  `Circularidad media`, `Tamano medio`.
- visor de imagen con overlay de mascara.
- leyenda de `Membrana`, `Nucleo`, `Micronucleo`.
- tabla `Resultados por Membrana`.
- columnas `Area Nucleo`, `Area MN`, `Int. Nucleo`, `Int. MN`,
  `Redondez N.`, `Redondez MN`, `Distancia`, `Fra. Area`, `Fra. Int.`.
- `Exportar CSV`.
- `Generar PDF`.

Evidencia:

- `Frontend/src/views/CaracterizacionView.vue:748`: llamada a
  `axios.get('/api/casos/${props.caseId}/caracterizacion/')`.
- `Frontend/src/views/CaracterizacionView.vue:896-967`: construccion de KPI
  cards.
- `Frontend/src/views/CaracterizacionView.vue:969-1034`: barras de
  distribucion y alerta `uN >= 2`.
- `Frontend/src/views/CaracterizacionView.vue:1037-1088`: `exportarCSV`.
- `Frontend/src/views/CaracterizacionView.vue:1096-1134`: `generarPDF`.
- `Frontend/package.json`: dependencia `html2pdf.js`.

Por tanto, para `origin/backend/creacion`, la captura no debe clasificarse como
mockup. Debe clasificarse como implementacion legacy real con limitaciones
cientificas y tecnicas.

### 20.5 Contrato de salida real de caracterizacion legacy

`caracterizacion_caso` devuelve:

```json
{
  "totales": {
    "nucleos": 0,
    "micronucleos": 0,
    "membranas": 0
  },
  "membranas": [],
  "imagenes": []
}
```

Cada fila de `membranas` puede contener:

```json
{
  "id_tabla": "27.1",
  "id_muestra": 1,
  "area_nucleo": 0,
  "area_mn": 0,
  "int_nucleo": 0,
  "int_mn": 0,
  "redondez_n": 0,
  "redondez_mn": 0,
  "distancia": 0,
  "fra_area": 0,
  "fra_int": 0
}
```

Cada elemento de `imagenes` puede contener:

```json
{
  "id": 1,
  "title": "Muestra 1",
  "src": "/media/...",
  "mask_src": "/api/mascaras/<id_analisis>/overlay/?offset=<n>&filtrar_vacios=true",
  "requiere_revision_manual": false
}
```

### 20.6 Formulas y reglas encontradas en `backend/creacion`

| Item | Campo / metrica | Archivo / lineas | Formula o regla real | Observacion |
|---|---|---|---|---|
| 1 | Area de nucleo | `Backend/api/views.py:693-700`, `762` | Rasteriza poligono sobre mascara PIL y usa `np.sum(mask_arr)` | Unidad efectiva: pixeles cuadrados. |
| 2 | Area de micronucleo | `Backend/api/views.py:693-700`, `763` | Misma formula de area sobre el poligono del MN | Unidad efectiva: pixeles cuadrados. |
| 3 | Intensidad nucleo | `Backend/api/views.py:709-712`, `764` | `np.mean(pixels) / 255.0` sobre imagen original en gris | Normalizada 0-1. |
| 4 | Intensidad MN | `Backend/api/views.py:709-712`, `765` | Misma formula sobre pixeles del poligono MN | Normalizada 0-1. |
| 5 | Perimetro | `Backend/api/views.py:683-687` | Suma de distancias entre puntos consecutivos con cierre por `np.roll` | Unidad efectiva: pixeles. |
| 6 | Redondez / circularidad de objeto | `Backend/api/views.py:702-707` | `(4 * np.pi * area) / (perimeter ** 2)`, truncada a maximo `1.0` | Se reporta como `roundness`. |
| 7 | Centroide | `Backend/api/views.py:681` | Promedio aritmetico de vertices `[mean(x), mean(y)]` | No usa centroide geometrico por momentos. |
| 8 | Distancia nucleo-MN | `Backend/api/views.py:672-673`, `768` | Distancia euclidiana entre centroides | Unidad efectiva: pixeles. |
| 9 | Fraccion de area | `Backend/api/views.py:769` | `area_mn / area_nucleo` si `area_nucleo > 0` | Ratio sin unidad. |
| 10 | Fraccion de intensidad | `Backend/api/views.py:770` | `int_mn / int_nucleo` si `int_nucleo > 0` | Ratio sin unidad. |
| 11 | Frecuencia uN | `Frontend/src/views/CaracterizacionView.vue:908-910` | `(totales.micronucleos / totales.membranas) * 100` | Porcentaje en UI. |
| 12 | Circularidad media | `Frontend/src/views/CaracterizacionView.vue:901-903` | Promedio de `row.redondez_n` sobre filas de tabla | Puede ponderar de mas membranas con varios MN. |
| 13 | Tamano medio | `Frontend/src/views/CaracterizacionView.vue:904-906` | Promedio de `row.area_nucleo` sobre filas de tabla | UI muestra `um3`, pero no hay calibracion fisica. |
| 14 | Alerta `uN >= 2` | `Frontend/src/views/CaracterizacionView.vue:981-990` | Cuenta membranas cuyo numero de filas con `area_mn > 0` es `>= 2` | Calculada por imagen activa. |
| 15 | Footer `con alertas` | `Frontend/src/views/CaracterizacionView.vue:884-894`, `576` | Cuenta membranas con al menos un MN | No usa el umbral `>= 2`. |

### 20.7 Asociacion membrana -> nucleo -> micronucleo

La asociacion no usa inclusion geometrica punto-en-poligono. Usa proximidad de
centroides:

1. Calcula metricas y centroides de membranas, nucleos y micronucleos.
2. Para cada nucleo, calcula distancia contra todos los centroides de membrana.
3. Asigna el nucleo a la membrana con menor distancia.
4. Para cada membrana, elige como nucleo principal el de mayor area.
5. Para cada micronucleo, calcula distancia contra todos los centroides de
   membrana.
6. Asigna el micronucleo a la membrana con menor distancia.

La regla esta en `Backend/api/views.py:739-754`.

Esta regla es portable tecnicamente, pero requiere decision cientifica antes de
adoptarse en `sicam-refactor`, porque puede asociar objetos cercanos aunque no
esten contenidos dentro de una membrana.

### 20.8 Semantica de `#27.1` y `#27.2`

`id_tabla` se construye en `Backend/api/views.py:760`.

Interpretacion real:

- `27` identifica la membrana visual global dentro del caso.
- `.1`, `.2`, etc. identifican el indice local del micronucleo asociado a esa
  membrana.
- Si la membrana tiene nucleo pero no tiene MN, `id_tabla` queda como `"27"`
  sin sufijo.

Por tanto, `#27.1` y `#27.2` significan dos micronucleos asociados a la
membrana visual 27, no dos membranas distintas.

### 20.9 Calibracion fisica

No se encontro calibracion pixel -> `um`, `um2` o `um3` en
`origin/backend/creacion`.

Las areas y distancias se calculan en pixeles. La UI muestra `Tamano medio` con
unidad `um3` en `Frontend/src/views/CaracterizacionView.vue:959`, pero esa
unidad no esta respaldada por una conversion fisica en el backend auditado.

### 20.10 CSV y PDF

CSV:

- Implementado en frontend.
- `Frontend/src/views/CaracterizacionView.vue:1037-1088`.
- Exporta `filteredSortedData` a un `Blob` CSV.
- No hay endpoint backend de CSV.

PDF:

- Implementado en frontend con `html2pdf.js`.
- `Frontend/src/views/CaracterizacionView.vue:1096-1134`.
- `Frontend/package.json` declara `html2pdf.js`.
- No hay endpoint backend de PDF.

### 20.11 Contraste contra `sicam-refactor`

`sicam-refactor` ya tiene caracterizacion activa, pero no contiene aun la
morfometria de `origin/backend/creacion`.

Implementacion activa actual:

- `apps/web/Backend/api/services/characterization/service.py`
- `apps/web/Backend/api/services/characterization/saliva.py`
- `apps/web/Backend/api/services/characterization/types.py`
- `apps/web/Frontend/src/views/CaracterizacionView.vue`

Alcance actual en `sicam-refactor`:

- usa `ResultadoSegmentacion` efectivo (`VALIDADA > AUTOMATICO`);
- persiste `ResultadoCaracterizacion`;
- reutiliza caracterizacion vigente;
- soporta SALIVA con conteos y `genotoxicity_index = micronucleo / membrana`;
- soporta BLOOD solo con conteos y bloqueos documentados;
- documenta como bloqueada la regla espacial legacy
  membrana-nucleo-micronucleo.

Faltantes frente a `origin/backend/creacion`:

- area por nucleo;
- area por micronucleo;
- intensidad por nucleo;
- intensidad por micronucleo;
- redondez/circularidad por objeto;
- distancia nucleo-MN;
- fraccion de area;
- fraccion de intensidad;
- asociacion membrana -> nucleo -> micronucleo;
- identificadores visuales `#27.1`;
- alerta `uN >= 2`;
- CSV;
- PDF;
- overlay PNG backend para caracterizacion.

### 20.12 Cambios a las conclusiones de Sprint 17E

Cambia:

- La afirmacion "no se encontro endpoint de caracterizacion morfologica" queda
  corregida para `origin/backend/creacion`: si existe
  `GET /api/casos/<int:id_caso>/caracterizacion/`.
- La afirmacion "la tabla Resultados por Membrana no fue encontrada" queda
  corregida para `origin/backend/creacion`: si existe en
  `Frontend/src/views/CaracterizacionView.vue`.
- La afirmacion "CSV/PDF son placeholder" queda corregida para
  `origin/backend/creacion`: CSV y PDF si tienen handlers frontend.
- La captura no debe clasificarse como mockup para `origin/backend/creacion`;
  debe clasificarse como implementacion legacy real.

Permanece:

- En el `main` local de `micronucleos-web` auditado originalmente, esas piezas
  no estaban presentes.
- `Segmentacion_web` sigue siendo una fuente legacy PySide/XLSX separada.
- No hay calibracion fisica demostrada.
- No hay pruebas automatizadas encontradas para estas formulas en
  `micronucleos-web`.
- BLOOD no tiene caracterizacion morfologica equivalente.
- `sicam-refactor` todavia no debe portar estas formulas sin decision
  cientifica.

### 20.13 Portabilidad y decisiones requeridas

Portable con adaptacion tecnica:

- calculo de area/perimetro en pixeles desde poligonos;
- intensidad media sobre imagen original en escala de grises;
- distancia euclidiana entre centroides;
- CSV frontend;
- PDF frontend;
- tabla por membrana.

Requiere decision cientifica:

- adoptar proximidad de centroides como asociacion oficial;
- definir si `Frecuencia uN` debe ser ratio o porcentaje;
- validar circularidad/redondez y su truncamiento a `1.0`;
- corregir o justificar unidades `um`, `um2` o `um3`;
- definir alerta `uN >= 2`;
- definir si `Circularidad media` y `Tamano medio` deben promediar filas,
  membranas unicas u objetos unicos;
- decidir si se incorpora overlay PNG backend o se reutiliza el overlay SVG
  actual de `sicam-refactor`.

### 20.14 Respuestas explicitas solicitadas en Sprint 17E.1

1. Branch existe: si, como `origin/backend/creacion`.
2. Hash: `9d9d39a4f81957d7825dc011451634cf98c23d53`.
3. `views.py` contiene caracterizacion: si.
4. `CaracterizacionView.vue` coincide con la captura: si, contiene KPI,
   visor, tabla, CSV y PDF.
5. Real vs mockup: real en `origin/backend/creacion`; no era real en el
   `main` local auditado originalmente.
6. Area nucleo: pixel count sobre poligono rasterizado.
7. Area MN: pixel count sobre poligono rasterizado.
8. Intensidad nucleo: media de gris dentro de mascara / 255.
9. Intensidad MN: media de gris dentro de mascara / 255.
10. Fraccion area: `area_mn / area_nucleo`.
11. Fraccion intensidad: `int_mn / int_nucleo`.
12. Redondez: `(4 * pi * area) / perimeter^2`, truncada a `1.0`.
13. Centroide: promedio de vertices.
14. Distancia: euclidiana entre centroides nucleo-MN.
15. Frecuencia uN: `(micronucleos / membranas) * 100` en la UI legacy.
16. Circularidad media: promedio de `redondez_n` por fila de tabla.
17. Tamano medio: promedio de `area_nucleo` por fila de tabla.
18. Alertas: por imagen, membranas con `>= 2` MN; footer global cuenta
   membranas con al menos un MN.
19. Calibracion: no encontrada.
20. Asociacion membrana->nucleo->MN: proximidad de centroides.
21. Semantica `#27.1/#27.2`: membrana 27, micronucleos 1 y 2.
22. Alerta MN>=2: implementada en `distributionBars`; no usada igual en el
   footer global.
23. CSV: implementado en frontend, sin endpoint backend.
24. PDF: implementado en frontend con `html2pdf.js`, sin endpoint backend.
25. Conclusiones que cambian: endpoint, UI, formulas, CSV/PDF y captura real
   para `backend/creacion`.
26. Conclusiones que permanecen: ausencia en `main` local original, falta de
   calibracion, falta de tests y necesidad de decision cientifica.
27. Falta en refactor: morfometria, asociacion espacial, CSV/PDF y reglas de
   alerta.
28. Portable: geometria en pixeles, intensidad, CSV/PDF y tabla, con
   adaptacion al contrato efectivo.
29. Requiere decision cientifica: unidades, asociacion, promedios, frecuencia,
   alerta y alcance SALIVA/BLOOD.
30. `docs/54` actualizado: si, mediante esta adenda.
31. `git status`: debe mostrar solo este documento modificado despues de la
   actualizacion documental.

### 20.15 Conclusion corregida

Sprint 17E.1 audit = PASS WITH LIMITATIONS.

La reauditoria dirigida confirma que `origin/backend/creacion` contiene una
implementacion legacy real de caracterizacion morfologica SALIVA. La captura
corresponde a esa implementacion o a una variante muy cercana de ella.

La implementacion es valiosa como referencia tecnica, pero no debe portarse
literalmente sin cerrar decisiones cientificas sobre unidades, calibracion,
asociacion espacial, definicion de promedios, frecuencia `uN`, alertas y alcance
SALIVA/BLOOD.
