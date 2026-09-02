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
