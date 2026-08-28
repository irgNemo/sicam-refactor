# Sprint 17A - Auditoria del legacy de caracterizacion y analisis SICAM

## 1. Proposito

Este documento reconstruye el significado real de "caracterizacion" en el
legacy SICAM a partir del codigo existente y de la documentacion historica.

No implementa caracterizacion nueva. No modifica backend, frontend,
microservicios, modelos, endpoints ni algoritmos.

Regla arquitectonica para sprints futuros:

```text
caracterizacion oficial
-> debe consumir resultado efectivo
-> latest VALIDADA si existe
-> AUTOMATICO si no existe VALIDADA
-> nunca BORRADOR
```

## 2. Definicion encontrada de caracterizacion legacy

En el legacy SALIVA, la caracterizacion no existe como modulo puro separado.
La evidencia muestra tres niveles mezclados:

- postprocesamiento de segmentacion para aceptar/rechazar citoplasmas,
  nucleos y micronucleos;
- agregacion de conteos por imagen y por carpeta;
- reporte Excel con indices de citotoxicidad y genotoxicidad.

La caracterizacion cientifica efectiva encontrada en codigo ejecutable legacy
es:

```text
por imagen:
- citoplasmas validos
- nucleos detectados
- celulas binucleadas
- celulas trinucleadas
- micronucleos detectados

por estudio/carpeta:
- suma de citoplasmas
- suma de nucleos
- suma de binucleadas
- suma de trinucleadas
- suma de micronucleos
- indice de citotoxicidad = (binucleadas + trinucleadas) / citoplasmas
- indice de genotoxicidad = micronucleos / citoplasmas
```

No se encontro un diagnostico clinico final del tipo positivo/negativo,
sano/enfermo, riesgo o score diagnostico. Tampoco se encontro un backend web
actual que calcule caracterizacion.

## 3. Clasificacion de funciones encontradas

| Archivo | Funcion / clase | Categoria | Observacion |
|---|---|---|---|
| `apps/segmentation-saliva/segmentacion_core/controller/controllerroot.py` | `ControllerRoot.segmentation()` | SEGMENTACION | Ejecuta Cellpose para membranas y despues selecciona nucleos/micronucleos. |
| `apps/segmentation-saliva/segmentacion_core/controller/controllerroot.py` | `ControllerRoot.__write_resume()` | AGREGACION/ESTADISTICA | Suma conteos e indices para tabla UI legacy. |
| `apps/segmentation-saliva/segmentacion_core/controller/controllerroot.py` | `ControllerRoot.__create_report()` | REPORTE/EXPORTACION | Genera `.xlsx` con conteos e indices. |
| `apps/segmentation-saliva/segmentacion_core/controller/controllerroot.py` | `ControllerRoot.__jaccard_index()` | UTILIDAD/GEOMETRIA | Calcula Jaccard manual vs automatico para auditoria de segmentacion. |
| `apps/segmentation-saliva/segmentacion_core/controller/controllerroot.py` | `ControllerRoot.__oscar_index()` | UTILIDAD/GEOMETRIA | TP/FN/FP por bounding boxes con margen. |
| `apps/segmentation-saliva/segmentacion_core/model/folder.py` | `Folder.calculate_indices()` | CARACTERIZACION / AGREGACION | Calcula indices finales de citotoxicidad/genotoxicidad. |
| `apps/segmentation-saliva/segmentacion_core/model/mask.py` | `Mask.add_elements()` | SEGMENTACION / UTILIDAD | Extrae objetos desde mascaras. |
| `apps/segmentation-saliva/segmentacion_core/model/mask.py` | `Mask.select_elements()` | SEGMENTACION / AGREGACION | Filtra objetos y acumula totales. |
| `apps/segmentation-saliva/segmentacion_core/model/cytoplasm.py` | `Cytoplasm.is_a_element()` | SEGMENTACION | Valida limites de celula/citoplasma. |
| `apps/segmentation-saliva/segmentacion_core/model/nuclei.py` | `Nuclei.is_a_element()` | SEGMENTACION / RELACION ESPACIAL | Busca nucleos dentro de cada citoplasma. |
| `apps/segmentation-saliva/segmentacion_core/model/micronuclei.py` | `Micronuclei.is_a_element()` | SEGMENTACION / RELACION ESPACIAL | Busca micronucleos dentro de cada citoplasma con color nuclear. |
| `apps/segmentation-blood/segmentacion_core/sicam_master.py` | `_preprocesar()` | SEGMENTACION | Resize 224x224, grayscale, gamma, CLAHE, sharpening. |
| `apps/segmentation-blood/segmentacion_core/sicam_master.py` | `_segmentar_celulas()` | SEGMENTACION | Cellpose y reescalado de mascara a tamano original. |
| `apps/segmentation-blood/segmentacion_core/sicam_master.py` | `_detectar_micronucleos()` | SEGMENTACION | Z-score, DBSCAN y circularidad para micronucleos. |
| `apps/web/Frontend/src/App.vue` | placeholder `caracterizacion` | PLACEHOLDER | No ejecuta calculos ni llamadas HTTP. |
| `apps/web/Frontend/src/components/MainContent.vue` | botones `Exportar CSV` / `Generar PDF` | PLACEHOLDER / UI LEGACY | No tienen handler funcional observado. |
| `apps/web/Backend/api/models.py` | `ResultadoAnalisis` | LEGACY ACTIVO EN MODELO | Conteos saliva antiguos; no participa en flujo nuevo de `ResultadoSegmentacion`. |
| `apps/web/Backend/api/models.py` | `AnalisisMascara` | LEGACY ACTIVO EN MODELO | Imagenes de mascaras ligadas a `ResultadoAnalisis`; no integrado a revisiones actuales. |

## 4. Pipeline SALIVA legacy

El pipeline legacy SALIVA reconstruido desde `ControllerRoot.segmentation()` es:

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
-> reporte xlsx
```

El microservicio SALIVA actual conserva la misma idea, pero expone JSON de
poligonos:

```text
POST /segmentar
-> {"objetos": [{ "id": int, "tipo": "membrana|nucleo|micronucleo", "puntos": [...] }]}
```

## 5. Entidades cientificas SALIVA

### Membrana / celula / citoplasma

El codigo usa nombres mixtos:

- `membrana` en JSON actual;
- `cytoplasm` en clases legacy;
- `celula` en comentarios de extraccion.

La mascara de membranas/citoplasma es la base para asociar nucleos y
micronucleos. Cada citoplasma se extrae por ID de mascara y se guarda con:

- `mask`;
- `pos_x`;
- `pos_y`.

### Nucleo

`Nuclei` se construye por cada `Cytoplasm`, usando la mascara individual y
posicion del citoplasma. El metodo `Nuclei.is_a_element()` devuelve el numero
de nucleos aceptados para esa celula.

Si encuentra `2`, `Mask.select_elements()` incrementa `total_binucleate`.
Si encuentra `3`, incrementa `total_trinucleate`.

### Micronucleo

`Micronuclei` tambien se construye por cada `Cytoplasm`. Requiere que el
citoplasma tenga `color_nuclei`, calculado durante la busqueda de nucleos.
El metodo `Micronuclei.is_a_element()` devuelve cuantos micronucleos acepta.

## 6. Metricas morfologicas SALIVA encontradas

### Area

Hay uso real de area por contorno:

```text
area_cyto = cv2.contourArea(contours[0])
area_nuclei = cv2.contourArea(contours[i])
area_micronuclei = cv2.contourArea(contours[i])
```

Tambien se calcula area por conteo de pixeles en `Micronuclei.__has_nuclei_color()`:

```text
area_micronuclei = np.where(img_micronuclei_mask[:, :, 0] != 0, 1, 0).sum()
area_mask_color = np.where(img_mask_color != 0, 1, 0).sum()
```

No hay unidades fisicas. La unidad implicita es pixel o area OpenCV en el
espacio de imagen procesado.

### Proporcion nucleo/citoplasma

En `Nuclei.__area_is_valid()`:

```text
proportion = area_nuclei / area_cyto
valido si 0.01 < proportion < 0.1
```

### Proporcion micronucleo/nucleo

En `Micronuclei.__area_is_valid()`:

```text
proportion = area_micronuclei / area_nuclei
valido si 0.08 < proportion < 0.33
```

### Elipticidad aproximada

En `Nuclei.__is_ellipse()`:

```text
img_original = contorno rellenado
img_ideal = elipse ajustada con cv2.fitEllipse(contour)
img_result = img_ideal ^ img_original
valido si img_result.sum() / pixels * 100 < 15
```

En `Micronuclei.__is_ellipse()`:

```text
valido si img_result.sum() / pixels * 100 < 16
```

Esto no es circularidad formal; es una comparacion binaria contra una elipse
ideal ajustada.

### Color nuclear para micronucleos

En `Nuclei.__has_garbage()`, si la jerarquia tiene exactamente dos contornos,
se guarda rango de tono HSV en `cytoplasm.color_nuclei`:

```text
cytoplasm.color_nuclei = [min_hue, max_hue]
```

En `Micronuclei.__has_nuclei_color()`:

```text
range_lower = (color_nuclei[0] - 3, 0, 0)
range_upper = (color_nuclei[1] + 3, 255, 255)
area_mask_color * 100 / area_micronuclei > 60
```

### Metricas buscadas pero no implementadas como salida

No se encontro salida persistida o reportada para:

- perimetro SALIVA;
- circularidad SALIVA;
- diametro por objeto;
- radio;
- centroide;
- bounding box como metrica final;
- elongacion;
- relacion de aspecto;
- convexidad;
- solidez;
- excentricidad;
- intensidad media;
- area fraction o intensity fraction.

Algunas existen como calculos auxiliares o derivados temporales, pero no como
resultado de caracterizacion versionado.

## 7. Relaciones espaciales SALIVA

### Asociacion nucleo-celula

La asociacion se hace por iteracion paralela sobre citoplasmas:

```text
for nuclei, cyto in zip(elementos_nuclei, elementos_cytoplasm):
    n_nucleos = nuclei.is_a_element(img=imagen_rgb, cytoplasm=cyto)
```

No hay una busqueda global por distancia ni centroides. Cada nucleo se detecta
dentro del recorte de su citoplasma.

### Asociacion micronucleo-celula

La asociacion tambien es por citoplasma:

```text
for cyto in elementos_cytoplasm:
    if cyto.color_nuclei is None:
        continue
    micro = Micronuclei(mask=cyto.mask, pos_x=cyto.pos_x, pos_y=cyto.pos_y)
    n_micro = micro.is_a_element(img=imagen_rgb, cytoplasm=cyto)
```

### Asociacion micronucleo-nucleo

No hay asociacion explicita por ID de nucleo. La evidencia real es:

- el area de nucleo aceptado se guarda temporalmente en `cytoplasm.area`;
- el color nuclear se guarda en `cytoplasm.color_nuclei`;
- el micronucleo se acepta si su area relativa y color son compatibles.

### Jerarquia de contornos

`Nuclei.__hierarchy_is_valid()` y `Micronuclei.__hierarchy_is_valid()` usan
`cv2.findContours(..., cv2.RETR_TREE, ...)` y cuentan padres en `hierarchy`.
Aceptan cuando `count_parent % 2` es verdadero.

### Implicacion para editor experto

El editor actual modifica poligonos. Para reconstruir caracterizacion SALIVA
desde el resultado efectivo se necesitara reimplementar asociacion espacial
desde poligonos, no desde los objetos `Cytoplasm`, `Nuclei` y `Micronuclei` en
memoria legacy. La equivalencia exacta con recortes/masks legacy no esta
garantizada sin rasterizar poligonos o definir reglas geometricas nuevas.

## 8. Agregados SALIVA

Por imagen, `ControllerRoot.__draw_image_selected()` muestra:

```text
citoplasmas = len(mask_cytoplasm.elements)
nucleos = mask_nucleus.total_elements
micronucleos = mask_micronucleus.total_micronucleus
binucleadas = mask_nucleus.total_binucleate
trinucleadas = mask_nucleus.total_trinucleate
```

Por carpeta/estudio, `ControllerRoot.__write_resume()` y
`Folder.calculate_indices()` agregan:

```text
cytoplasm += len(img.mask_cytoplasm.elements)
nucleus += img.mask_nucleus.total_elements
binucleate += img.mask_nucleus.total_binucleate
trinucleate += img.mask_nucleus.total_trinucleate
micronucleus += img.mask_micronucleus.total_micronucleus
```

Indices:

```text
cytotoxicity_index = (binucleate + trinucleate) / cytoplasm
genotoxicity_index = micronucleus / cytoplasm
```

`ControllerRoot.__create_report()` aplica la misma formula y, si
`cytoplasms == 0`, escribe `Indeterminacion`.

## 9. Reportes legacy SALIVA

El reporte implementado usa `openpyxl.Workbook()` y guarda:

```text
<folder_name>.xlsx
```

Columnas por imagen:

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
B1 = Indice de citotoxicidad
B2 = Indice de genotoxicidad
```

No se encontro generacion PDF funcional en backend actual. El frontend muestra
botones `Exportar CSV` y `Generar PDF`, pero no se observo handler asociado en
`MainContent.vue`.

## 10. Pipeline BLOOD actual/legacy integrado

El pipeline BLOOD real vive en `apps/segmentation-blood/segmentacion_core/sicam_master.py`:

```text
bytes
-> cv2.imdecode
-> BGR a RGB
-> _segmentar_celulas()
   -> _preprocesar()
      -> resize 224x224
      -> RGB a grayscale
      -> gamma 0.8
      -> CLAHE clipLimit=4.0 tileGridSize=(8, 8)
      -> GaussianBlur(3, 3)
      -> addWeighted sharpening
   -> CellposeModel(gpu=False)
   -> model.eval(img_prep, diameter=None, channels=[0, 0])
   -> resize nearest neighbor al tamano original
-> RGB a grayscale original
-> _detectar_micronucleos()
   -> z-score robusto por celula
   -> pixeles brillantes por z-score
   -> DBSCAN
   -> filtro de circularidad
-> mascaras celulas y micronucleos
-> poligonos JSON
```

Endpoint FastAPI real:

```text
POST /api/v1/segmentar
multipart form-data: file
respuesta: {"objetos": [...]}
```

Labels reales:

- `membrana`, derivado de `resultado["celulas"]`;
- `micronucleo`, derivado de `resultado["micronucleos"]`.

No existe label `nucleo` en BLOOD.

## 11. Metricas BLOOD encontradas

Las metricas BLOOD encontradas son parte de segmentacion, no de una
caracterizacion posterior:

### Z-score robusto de celula

```text
mediana = np.median(pixeles)
mad = np.median(np.abs(pixeles - mediana))
z = 0.6745 * (np.max(pixeles) - mediana) / mad
valido si z > UMBRAL_ZSCORE_CELULA
UMBRAL_ZSCORE_CELULA = 8
```

### Z-score por pixel

```text
z_pixs = 0.6745 * (intensidades - mediana) / mad
coords_b = coords[z_pixs > UMBRAL_ZSCORE_PIXEL]
UMBRAL_ZSCORE_PIXEL = 3
```

### DBSCAN

```text
DBSCAN_EPS = 2.5
DBSCAN_MIN_SAMPLES = 4
MIN_PIXELES_CLUSTER = 5
MIN_PUNTOS_CLUSTER = 6
n_jobs = 1
```

### Circularidad de cluster

```text
area = cv2.contourArea(contornos[0])
perimetro = cv2.arcLength(contornos[0], True)
circularidad = 4 * np.pi * area / perimetro ** 2
valido si circularidad >= CIRCULARIDAD_MINIMA
CIRCULARIDAD_MINIMA = 0.5
```

### Metricas BLOOD no encontradas como caracterizacion posterior

No se encontro caracterizacion BLOOD separada despues de detectar membranas y
micronucleos. No se encontro salida para:

- tamano de celulas como metrica final;
- tamano de micronucleos como metrica final;
- relacion micronucleo/celula;
- densidad;
- porcentajes;
- diagnostico;
- score;
- reporte.

Los conteos actuales de BLOOD provienen del `summary.counts_by_label` generado
por el normalizador Django sobre el JSON de segmentacion.

## 12. Identidad de objetos

### Legacy SALIVA

La identidad legacy depende de:

- ID de mascara de Cellpose para citoplasmas/membranas;
- posicion en listas paralelas `cytoplasms`, `nuclei`, `micronuclei`;
- recortes `pos_x`, `pos_y`;
- no de un ID editorial persistente.

### BLOOD

La mascara de celulas usa IDs enteros de Cellpose. La mascara de micronucleos
asigna IDs incrementales `id_mic`. El extractor de poligonos usa el ID de la
mascara como `id` crudo.

### Modelo actual

En el contrato normalizado actual:

```text
objects[].id = ID editorial unico dentro del resultado
objects[].source.raw_id = ID crudo de mascara/procedencia
objects[].source.raw_type = tipo crudo
```

Recomendacion para caracterizacion nueva:

```text
usar objects[].id del resultado efectivo como identidad canonica
conservar source.raw_id solo como provenance
```

No se debe depender de `source.raw_id`, porque ya se observo que puede no ser
unico en resultados historicos o entre clases.

## 13. Espacio de coordenadas

### SALIVA

SALIVA trabaja en pixeles de la imagen recibida por el pipeline. Las mascaras
y contornos se recortan con `pos_x` y `pos_y`, y luego se reinsertan en el
espacio de la imagen.

No se encontro una calibracion micrometrica ni conversion a unidades fisicas.

### BLOOD

BLOOD segmenta celulas en imagen preprocesada 224x224 y luego reescala la
mascara al tamano original con nearest neighbor. La deteccion de micronucleos
se ejecuta sobre `img_gris` derivada del RGB original y usa la mascara reescalada
al tamano original.

Riesgo:

- Cellpose decide objetos en 224x224;
- micronucleos se filtran en coordenadas originales;
- las metricas de circularidad y DBSCAN operan sobre pixeles originales despues
  del reescalado de la mascara celular.

Cualquier metrica de area/perimetro futura debe declarar si usa pixeles de la
imagen original o una mascara reescalada.

## 14. Diagnostico

No se encontro una regla implementada que produzca:

- positivo/negativo;
- sano/enfermo;
- riesgo;
- diagnostico clinico;
- clasificacion;
- score final.

Las reglas con thresholds encontradas pertenecen a segmentacion/postprocesamiento:

- SALIVA: proporciones de area, tolerancia eliptica, porcentaje de color.
- BLOOD: z-score, DBSCAN y circularidad.

No deben documentarse como diagnostico hasta que exista una decision cientifica
explicita.

## 15. ResultadoAnalisis y AnalisisMascara

`ResultadoAnalisis` en Django contiene:

```text
id_resultado
muestra -> MuestraSaliva
nucleos
micronucleos
membranas
fecha_analisis
```

`AnalisisMascara` contiene:

```text
id_mascara_analisis
resultado -> ResultadoAnalisis
tipo_mascara
imagen
algoritmo
fecha_generacion
```

Uso real observado:

- existen modelos y serializer de `ResultadoAnalisis`;
- no hay `ViewSet` registrado para `ResultadoAnalisis`;
- no hay endpoint actual de caracterizacion sobre `ResultadoAnalisis`;
- el flujo nuevo de segmentacion usa `ResultadoSegmentacion`;
- frontend actual usa historial/efectivo de `ResultadoSegmentacion`.

Clasificacion:

```text
ResultadoAnalisis = mezcla legacy de conteos de segmentacion/caracterizacion
AnalisisMascara = almacenamiento legacy de mascaras exportadas
```

No conviene reutilizarlos directamente para caracterizacion nueva sin un sprint
de diseno, porque estan centrados en SALIVA y no tienen trazabilidad a revision
VALIDADA/AUTOMATICO.

## 16. Documentacion vs codigo

| Tema | Clasificacion | Evidencia |
|---|---|---|
| `ResultadoAnalisis` como conteos saliva | CODIGO Y DOC COINCIDEN | Modelo Django y docs historicas lo describen como conteos. |
| Caracterizacion con area/perimetro/circularidad/centroid | DOC DESCRIBE ALGO NO IMPLEMENTADO | Docs mencionan metricas futuras; no hay salida persistida. |
| BLOOD con z-score/DBSCAN/circularidad | CODIGO Y DOC COINCIDEN | `sicam_master.py` y `docs/46...` coinciden. |
| BLOOD caracterizacion posterior | CODIGO NO IMPLEMENTA | Solo hay segmentacion y normalizacion de conteos. |
| Frontend Caracterizacion | PLACEHOLDER | `TopBar.vue` navega a placeholder en `App.vue`. |
| CSV/PDF frontend | UI LEGACY/HUERFANA | Botones visibles sin handler funcional observado. |
| Reporte Excel SALIVA PySide | CODIGO HACE ALGO NO INTEGRADO | `ControllerRoot.__create_report()` existe fuera del web flow. |
| Resultado efectivo para reportes/caracterizacion | DOC ACTUAL LO EXIGE | `effective.py` implementa `VALIDADA > AUTOMATICO`; caracterizacion aun no existe. |

## 17. Integracion propuesta con resultado efectivo

Flujo conceptual recomendado:

```text
ResultadoSegmentacion
-> resolve_effective_segmentation(resultado_segmentacion)
-> validar fuente:
   - VALIDADA
   - AUTOMATICO
   - nunca BORRADOR
-> caracterizador puro por sample_type
-> ResultadoCaracterizacion futuro
```

Entrada conceptual al caracterizador:

```text
{
  "resultado_segmentacion_id": 123,
  "fuente": "AUTOMATICO|VALIDADA",
  "revision": null | {
    "id_revision_segmentacion": 10,
    "numero_revision": 2,
    "estado": "VALIDADA",
    "validado_en": "..."
  },
  "resultado": {
    "version": "...",
    "sample_type": "SALIVA|SANGRE",
    "objects": [...]
  },
  "resumen": {...}
}
```

## 18. Trazabilidad propuesta

Sin crear modelo todavia, una caracterizacion futura deberia guardar al menos:

```text
resultado_segmentacion_id
revision_segmentacion_id nullable
source = AUTOMATICO | VALIDADA
sample_type = SALIVA | SANGRE
characterizer_version
input_snapshot_hash
created_at
metrics_json
summary_json
```

`revision_segmentacion_id = null` debe significar que se caracterizo el
resultado automatico. Si hay `VALIDADA`, debe guardarse el ID de revision
validada usada.

## 19. Obsolescencia y recaracterizacion

Si un especialista modifica geometria y valida una nueva revision, la
caracterizacion anterior debe considerarse potencialmente obsoleta.

Mecanismos futuros recomendados:

- comparar `revision_segmentacion_id` usado contra la ultima `VALIDADA`;
- comparar `source` y `input_snapshot_hash`;
- exponer estado `vigente` calculado o persistido;
- forzar recalculo manual o job asincrono cuando cambie el resultado efectivo.

No se recomienda usar signals todavia sin una decision de operacion, porque
BLOOD puede ser lento y caracterizacion podria crecer.

## 20. Pure functions candidatas

Partes aptas para convertir en funciones puras:

- conteo por label desde `objects`;
- indices SALIVA desde conteos asociados:
  - citotoxicidad;
  - genotoxicidad;
- calculo geometrico por poligono:
  - area;
  - perimetro;
  - bounding box;
  - centroide;
  - circularidad;
- asociacion espacial por poligonos:
  - nucleo dentro de membrana;
  - micronucleo dentro de membrana;
  - micronucleo cercano/contenido respecto a nucleo, si se define regla;
- resumen por muestra/caso.

Partes que no deben depender de Django ORM:

- formulas geometricas;
- validacion de snapshots;
- agregaciones numericas.

El ORM deberia limitarse a recuperar resultado efectivo y persistir el JSON de
salida.

## 21. Contrato conceptual propuesto

Basado en evidencia legacy y contrato actual, una salida futura podria ser:

```json
{
  "version": "0.1",
  "sample_type": "SALIVA",
  "source": {
    "resultado_segmentacion_id": 123,
    "revision_segmentacion_id": null,
    "fuente": "AUTOMATICO",
    "input_snapshot_hash": "..."
  },
  "objects": [
    {
      "id": 1,
      "label": "membrana",
      "metrics": {
        "area_px": 1200.0,
        "perimeter_px": 160.0,
        "centroid_px": [50.0, 80.0],
        "bounding_box_px": [10.0, 20.0, 90.0, 140.0]
      },
      "relations": {
        "nucleos": [2],
        "micronucleos": [3]
      }
    }
  ],
  "summary": {
    "counts_by_label": {
      "membrana": 1,
      "nucleo": 1,
      "micronucleo": 1
    },
    "saliva": {
      "citotoxicity_index": 0.0,
      "genotoxicity_index": 1.0
    }
  }
}
```

Este contrato es conceptual, no definitivo. Debe ajustarse cuando se definan
formalmente reglas espaciales sobre poligonos editados.

Para BLOOD, no debe forzarse simetria:

```json
{
  "version": "0.1",
  "sample_type": "SANGRE",
  "source": {...},
  "objects": [...],
  "summary": {
    "counts_by_label": {
      "membrana": 350,
      "micronucleo": 1
    }
  }
}
```

No hay evidencia suficiente para indices BLOOD adicionales.

## 22. Diferencias SALIVA / BLOOD

| Dimension | SALIVA | BLOOD |
|---|---|---|
| Objetos | `membrana`, `nucleo`, `micronucleo` | `membrana`, `micronucleo` |
| Metricas por objeto legacy | Areas auxiliares, elipticidad aproximada, color nuclear; no se persisten por objeto | Z-score, DBSCAN, circularidad auxiliares de segmentacion; no se persisten por objeto |
| Relaciones | Nucleo/micronucleo dentro de citoplasma por recortes y listas paralelas | Micronucleos detectados dentro de mascaras celulares candidatas |
| Agregados | Citoplasmas, nucleos, binucleadas, trinucleadas, micronucleos | Conteos por label actuales; no hay agregados cientificos legacy separados |
| Diagnostico | No encontrado | No encontrado |
| Reporte legacy | Excel `.xlsx` PySide con indices | No encontrado |
| Legacy implementado | Si, en PySide/modelos de saliva | Segmentacion actual, no caracterizacion posterior |
| Legacy documentado | Parcial; docs mencionan metricas futuras no implementadas | Docs 16B documenta segmentacion |
| Gaps | Rehacer asociaciones desde poligonos editados; definir unidades | Definir si hay caracterizacion cientifica posterior o solo conteos |

## 23. Codigo a reutilizar o reescribir

### Reutilizar casi directo

- `resolve_effective_segmentation()` como fuente canonica de snapshot oficial.
- Configuracion de labels por `sample_type` en `types.py`.

### Adaptar

- `Folder.calculate_indices()` como formula de indices SALIVA, pero no su
  dependencia de `Folder/Image/Mask`.
- `ControllerRoot.__create_report()` como referencia de columnas legacy, no
  como implementacion web.

### Reescribir como funcion pura

- Conteos SALIVA/BLOOD desde `objects`.
- Indices de citotoxicidad/genotoxicidad.
- Area/perimetro/centroide/bounding box desde poligonos.
- Asociacion nucleo/membrana y micronucleo/membrana sobre geometria efectiva.

### No reutilizar directamente

- UI PySide `ControllerRoot`.
- Pickle `.caz` de estudio.
- Exportaciones temporales a Desktop/cellanalizer.
- `ResultadoAnalisis` como modelo final de caracterizacion multimuestra.
- Cualquier flujo que consuma `resultado_normalizado` directamente ignorando
  `RevisionSegmentacion`.

## 24. Tests futuros recomendados

- geometria simple conocida: cuadrado, triangulo, poligono concavo;
- area esperada en pixeles;
- perimetro esperado;
- centroide esperado;
- bounding box esperado;
- circularidad esperada si se decide incluirla;
- nucleo dentro de membrana;
- nucleo fuera de membrana;
- micronucleo dentro de membrana;
- micronucleo asociado a nucleo, si se define regla;
- snapshot `AUTOMATICO`;
- snapshot `VALIDADA` modificada;
- `BORRADOR` no se usa;
- nueva `VALIDADA` vuelve obsoleta caracterizacion previa;
- BLOOD sin micronucleos;
- BLOOD con multiples micronucleos;
- IDs raw duplicados;
- IDs editoriales unicos;
- resultados historicos version `1.0`;
- resultados actuales version `1.1`.

## 25. Preguntas cientificas pendientes

1. Si `membrana` en SALIVA debe interpretarse formalmente como citoplasma,
   celula completa o contorno celular.
2. Si los indices legacy son suficientes:
   - `citotoxicity_index = (binucleate + trinucleate) / cytoplasm`;
   - `genotoxicity_index = micronucleus / cytoplasm`.
3. Como definir binucleada/trinucleada desde poligonos editados: conteo de
   nucleos dentro de membrana, inclusion por centroide, interseccion de area o
   rasterizacion.
4. Como asociar micronucleo a nucleo/celula tras edicion experta.
5. Si deben existir umbrales clinicos/diagnosticos y cuales son.
6. Si BLOOD necesita caracterizacion posterior o solo conteos validados.
7. Si hay calibracion fisica pixel-micrometro disponible.
8. Si se debe caracterizar cada muestra, cada resultado, cada revision o cada
   caso completo.
9. Cual debe ser la version inicial formal del algoritmo de caracterizacion.
10. Que formato de reporte operativo/cientifico se requiere: JSON, CSV, XLSX,
    PDF o combinacion.

## 26. Conclusion

Sprint 17A AUDIT = PASS CON PREGUNTAS.

La auditoria encontro caracterizacion SALIVA legacy basada en conteos,
binucleadas/trinucleadas, micronucleos e indices de citotoxicidad/genotoxicidad.
No encontro diagnostico clinico implementado. No encontro caracterizacion BLOOD
separada de la segmentacion. La proxima iteracion deberia disenar una capa de
caracterizacion pura que consuma exclusivamente resultado efectivo.
