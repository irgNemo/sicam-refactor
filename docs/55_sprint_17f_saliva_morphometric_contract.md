# Sprint 17F - Saliva Morphometric Characterization Contract v2

## 1. Alcance

Este documento define la especificacion cientifica, geometrica y de datos para
la futura `Caracterizacion SALIVA v2` de SICAM.

El objetivo es que un sprint posterior pueda implementar la caracterizacion sin
tomar decisiones cientificas implicitas.

Esta especificacion es solo de diseno. No modifica codigo, modelos, endpoints,
migraciones, frontend ni microservicios.

La futura implementacion debe operar sobre:

```text
ResultadoSegmentacion
-> effective
-> VALIDADA mas reciente si existe
-> AUTOMATICO si no existe VALIDADA
-> ResultadoCaracterizacion
```

`BORRADOR` nunca es fuente oficial para caracterizacion.

## 2. Fuentes

Fuentes usadas:

- `docs/54_sprint_17e_morphological_characterization_audit.md`
- `sicam-refactor` actual
- `micronucleos-web` branch `origin/backend/creacion`
- commit auditado `9d9d39a4f81957d7825dc011451634cf98c23d53`
- `Segmentacion_web` solo para reglas legacy confirmadas
- implementacion actual de `ResultadoCaracterizacion`

Archivos clave confirmados en `origin/backend/creacion`:

- `Backend/api/views.py`
- `Frontend/src/views/CaracterizacionView.vue`

Archivos clave actuales en `sicam-refactor`:

- `apps/web/Backend/api/services/characterization/service.py`
- `apps/web/Backend/api/services/characterization/saliva.py`
- `apps/web/Backend/api/services/characterization/types.py`
- `apps/web/Backend/api/services/characterization/geometry.py`
- `apps/web/Frontend/src/views/CaracterizacionView.vue`

No se introduce literatura externa ni reglas clinicas nuevas. Cuando una regla
no esta sustentada directamente por codigo legacy o por el refactor actual, se
marca como decision de diseno.

## 3. Vocabulario

`SEGMENTACION`:
detecta o propone objetos.

`REVISION EXPERTA`:
corrige objetos, geometria y labels.

`CARACTERIZACION`:
mide los objetos efectivos.

`effective`:
resultado oficial que resuelve `VALIDADA > AUTOMATICO`. Un `BORRADOR` no forma
parte del resultado efectivo.

`membrana`:
objeto normalizado que representa la celula en SALIVA.

`nucleo`:
objeto normalizado nuclear.

`micronucleo`:
objeto normalizado de micronucleo.

`cell`:
estructura derivada desde una `membrana` efectiva y sus asociaciones.

`source.raw_id`:
identificador de procedencia del microservicio. Puede repetirse y no debe usarse
como identidad editorial ni relacional.

`objects[].id`:
identidad oficial del objeto normalizado/effective. Todas las asociaciones de
v2 deben referenciar estos IDs.

## 4. Principios

### 4.1 Medicion != deteccion

La segmentacion detecta candidatos. La revision experta puede corregirlos. La
caracterizacion mide el resultado efectivo.

Por tanto, una estructura validada por experto no debe descartarse durante
caracterizacion porque incumpla filtros legacy de deteccion, por ejemplo:

- `area_nucleo / area_citoplasma`
- `area_mn / area_nucleo`
- tolerancia contra elipse ideal
- similitud HSV
- umbral de circularidad usado para aceptar candidatos

Esos thresholds pertenecen a deteccion, no a medicion descriptiva.

### 4.2 Trazabilidad

La caracterizacion v2 debe preservar el origen del calculo:

- fuente `AUTOMATICO` o `VALIDADA`;
- `resultado_segmentacion_id`;
- `revision_segmentacion_id` cuando aplique;
- `numero_revision` cuando aplique;
- `algorithm_version`;
- `schema_version`.

### 4.3 No mutabilidad del insumo

El calculo no debe modificar:

- `ResultadoSegmentacion.respuesta_json`;
- `ResultadoSegmentacion.resultado_normalizado`;
- snapshot de `RevisionSegmentacion`;
- objetos del `effective` recibido.

### 4.4 Degradacion parcial

Los problemas locales por objeto deben producir `warnings`, no fallar toda la
caracterizacion, siempre que el contrato minimo del resultado efectivo siga
siendo valido.

## 5. Alcance SALIVA v2

SALIVA v2 debe cubrir:

- metricas globales;
- metricas por celula/membrana;
- metricas por nucleo;
- metricas por micronucleo;
- asociaciones celula-nucleo-micronucleo;
- indices de genotoxicidad y citotoxicidad;
- warnings estructurados;
- contrato JSON estable.

BLOOD queda fuera de morfometria v2. Para BLOOD se mantiene el alcance
`counts-only` actual hasta un diseno posterior.

## 6. Unidades oficiales

Hasta disponer de calibracion fisica, las unidades oficiales son:

| Magnitud | Unidad |
|---|---|
| Area | `px2` |
| Perimetro | `px` |
| Centroide | `px` |
| Distancia | `px` |
| Circularidad | adimensional |
| Intensidad media gris | adimensional normalizada `0..1` |
| Fraccion de area | adimensional |
| Fraccion de intensidad | adimensional |
| Indices | adimensional |

No usar:

- `um`
- `um2`
- `um3`

No inventar conversion pixel -> micrometro.

Una futura calibracion puede agregarse como capa posterior, pero las medidas
base en pixeles deben conservarse para reproducibilidad.

## 6.1 Sistema de coordenadas SALIVA

Resultado de auditoria dirigida:

```text
ORIGINAL_IMAGE_COORDINATES
```

Evidencia del pipeline actual:

1. `apps/segmentation-saliva/app/routers/segmentacion.py` recibe un
   `UploadFile`, lee bytes y llama `segmentar_pipeline(contenido)`.
2. `apps/segmentation-saliva/app/services/segmentador.py::leer_imagen_bytes`
   usa `cv2.imdecode(np_arr, cv2.IMREAD_COLOR)` y luego
   `cv2.cvtColor(img, cv2.COLOR_BGR2RGB)`. No se encontro resize en esta ruta.
3. `SegmentadorMembranas.segmentar(imagen_rgb)` llama
   `CellposeModel.eval(imagen_rgb, diameter=125, channels=[1, 0], ...)` y
   devuelve la mascara filtrada. No se encontro reescalado de salida.
4. `segmentar_nucleos(imagen_rgb, masks_cytoplasm)` reconstruye la mascara
   final con `imagen_rgb.shape[:2]`.
5. `segmentar_micronucleos(imagen_rgb, masks_cytoplasm, cytoplasm_data)`
   reconstruye la mascara final con `imagen_rgb.shape[:2]`.
6. `obtener_poligonos_desde_mascara(mascara, tipo_objeto)` obtiene contornos
   directamente sobre `mascara.shape` y devuelve `puntos.tolist()`.
7. `api/services/segmentation/normalizers.py` copia `raw_object["puntos"]` a
   `geometry.points` sin transformacion geometrica.
8. El frontend proyecta `geometry.points` usando `naturalWidth`,
   `naturalHeight` y la caja visible con `object-fit: contain`.

Conclusion:

- las coordenadas de `geometry.points` de SALIVA estan en pixeles de la imagen
  original decodificada por OpenCV;
- no se encontro transformacion intermedia que requiera reescalado antes de
  medir o rasterizar sobre la imagen original;
- las metricas geometricas e intensidad pueden operar directamente sobre
  `geometry.points` y el archivo original, siempre que la imagen cargada para
  intensidad tenga las mismas dimensiones que la imagen segmentada.

Riesgo residual:

- si en el futuro se introduce resize en `segmentation-saliva` o en el cliente
  Django, el contrato debera cambiar a
  `SEGMENTATION_COORDINATES_WITH_TRANSFORM` y documentar explicitamente la
  transformacion.

## 7. Geometria

### 7.1 Puntos validos

Un punto valido es:

```json
[x, y]
```

con:

- dos coordenadas;
- numeros finitos;
- no booleanos;
- coordenadas en pixeles de la imagen original.

Un poligono medible requiere al menos 3 puntos validos.

### 7.1.1 Poligono simple

Para medicion morfometrica fiable, el poligono debe ser simple:

- sus segmentos no deben cruzarse entre si;
- se permite el cierre del ultimo punto al primero;
- segmentos adyacentes comparten vertice y no cuentan como autointerseccion;
- segmentos no adyacentes no deben intersectarse;
- casos colineales deben tratarse de forma determinista.

Un poligono auto-intersectado no debe corregirse automaticamente.

Politica para `SELF_INTERSECTING_POLYGON`:

- no eliminar el objeto;
- conservar `id`, `label` y `source`;
- `area_px2 = null`;
- `centroid_px = null`;
- `circularity = null`;
- asociacion espacial = no calculable;
- agregar warning `SELF_INTERSECTING_POLYGON`.

`perimeter_px` puede reportarse como longitud del path cerrado si los puntos son
validos, porque esa longitud esta matematicamente definida aun cuando el objeto
no sea morfometricamente valido. Debe documentarse que ese perimetro no valida
la morfometria del objeto.

Deteccion conceptual:

```text
comparar cada segmento contra segmentos no adyacentes
excluir pares que comparten vertice por adyacencia
incluir segmento de cierre
tratar intersecciones colineales con regla determinista
```

### 7.2 Area

Definicion oficial:

```text
A = 1/2 * abs(sum(x_i * y_{i+1} - x_{i+1} * y_i))
```

con cierre del poligono:

```text
punto n -> punto 0
```

Unidad:

```text
px2
```

Decision cerrada:

- usar area geometrica vectorial por formula de shoelace;
- no usar rasterizacion PIL como valor oficial de area.

Razon:

area, perimetro y centroide deben proceder de la misma representacion vectorial
para mantener consistencia geometrica.

Casos limite:

- menos de 3 puntos validos: metrica no calculable;
- area `0`: poligono degenerado;
- poligono degenerado: `area_px2 = 0`, metricas derivadas dependientes pueden
  ser `null`.

### 7.3 Perimetro

Definicion oficial:

```text
P = sum(sqrt((x_{i+1} - x_i)^2 + (y_{i+1} - y_i)^2))
```

incluyendo el segmento:

```text
ultimo punto -> primer punto
```

Unidad:

```text
px
```

El helper existente `polygon_perimeter(points)` puede servir como base tecnica
en Sprint 17G, pero este documento no modifica codigo.

### 7.4 Centroide geometrico

No usar el promedio aritmetico de vertices del legacy como definicion oficial.

Para un poligono no degenerado, usar centroide geometrico basado en area
orientada:

```text
A_signed = 1/2 * sum(x_i * y_{i+1} - x_{i+1} * y_i)

Cx = 1 / (6 * A_signed) *
     sum((x_i + x_{i+1}) * (x_i * y_{i+1} - x_{i+1} * y_i))

Cy = 1 / (6 * A_signed) *
     sum((y_i + y_{i+1}) * (x_i * y_{i+1} - x_{i+1} * y_i))
```

Salida:

```json
[x, y]
```

Unidad:

```text
px
```

Si `A_signed == 0`, usar:

```json
null
```

No usar fallback silencioso al promedio de vertices.

### 7.5 Circularidad

Definicion oficial:

```text
C = 4 * pi * A / P^2
```

Aplicable a:

- `nucleo`;
- `micronucleo`;
- `membrana` si se decide exponer su metrica.

Rango teorico:

```text
0 < C <= 1
```

para poligonos simples ideales.

Si `P == 0`:

```json
null
```

No usar la regla legacy de diferencia contra elipse ideal como metrica
descriptiva. Esa regla fue un filtro de deteccion.

No aplicar clamp general a `1.0` para ocultar inconsistencias geometricas.

Tolerancia numerica oficial:

```text
CIRCULARITY_EPSILON = 1e-9
```

Justificacion:

- los calculos se haran con `float` de doble precision;
- `1e-9` cubre ruido numerico pequeno alrededor de `1.0`;
- valores por encima de ese margen sugieren problema geometrico, de puntos,
  autointerseccion o inconsistencia de calculo.

Comportamiento:

| Valor calculado | Resultado |
|---|---|
| `0 <= C <= 1` | usar `C` |
| `1 < C <= 1 + CIRCULARITY_EPSILON` | normalizar a `1.0` |
| `C > 1 + CIRCULARITY_EPSILON` | `circularity = null` y warning `INVALID_CIRCULARITY` |

No usar `INVALID_CIRCULARITY` para filtrar o eliminar objetos.

Nombre oficial:

```text
circularity
```

Nombre UI:

```text
Circularidad
```

Evitar `Redondez` en el contrato para reducir ambiguedad.

## 8. Intensidad media

Concepto conservado desde `origin/backend/creacion`:

```text
imagen original
-> grayscale
-> rasterizar poligono
-> seleccionar pixeles interiores
-> mean
-> dividir entre 255
```

Nombre oficial:

```text
mean_gray_intensity
```

Rango:

```text
0..1
```

La intensidad:

- no representa un canal biologico especifico;
- no es diagnostico;
- es media de luminancia/gris derivada de la imagen original.

Referencia legacy:

```python
Image.open(muestra.ruta_imagen.path).convert('L')
```

Decision de diseno para v2:

usar conversion equivalente a `PIL.Image.convert("L")`:

```text
L = 0.299 * R + 0.587 * G + 0.114 * B
```

con el redondeo/casteo propio de la libreria usada para generar la imagen en
escala de grises.

Si la imagen original falta o no puede leerse:

- no fallar toda la caracterizacion;
- `mean_gray_intensity = null`;
- fracciones de intensidad dependientes = `null`;
- agregar warning `IMAGE_UNAVAILABLE`.

Como SALIVA quedo auditado como `ORIGINAL_IMAGE_COORDINATES`, la rasterizacion
de intensidad puede usar `geometry.points` directamente sobre la imagen
original. Sprint 17G debe incluir una prueba con imagen real o fixture local
que confirme:

- dimensiones de imagen original;
- dimensiones de mascara/poligono;
- alineacion de la mascara rasterizada con los puntos originales.

Si esa prueba detecta discrepancia de dimensiones, `mean_gray_intensity` debe
quedar bloqueada y reportar `COORDINATE_SPACE_MISMATCH` hasta especificar la
transformacion exacta.

## 9. Asociacion celular

### 9.1 Principio

La asociacion legacy de `origin/backend/creacion` usa proximidad de centroides
a la membrana mas cercana. Esa regla no debe adoptarse como regla primaria
oficial porque puede asociar objetos cercanos aunque no esten dentro de la
celula.

La asociacion v2 debe usar geometria explicita.

La celula se representa por el objeto con:

```json
{ "label": "membrana" }
```

### 9.2 Point-in-polygon

La regla primaria de pertenencia es:

```text
centroide geometrico del objeto dentro del poligono de membrana
```

Para puntos exactamente en borde:

- considerarlos dentro;
- registrar warning opcional `POINT_ON_BOUNDARY` si se necesita trazabilidad.

Esta es una decision de diseno cerrada para evitar asociaciones arbitrarias por
proximidad global.

### 9.3 Asociacion nucleo -> membrana

Para cada `nucleo`:

1. Calcular centroide geometrico del nucleo.
2. Buscar membranas cuyo poligono contiene ese centroide.
3. Resolver:
   - 0 membranas: `membrane_id = null`, `association_status = UNASSOCIATED`.
   - 1 membrana: asociar a esa `membrane_id`.
   - 2+ membranas: marcar como ambigua.

Decision v2 para 2+ membranas:

- no elegir silenciosamente una asociacion arbitraria;
- si no se implementa interseccion robusta nucleo/membrana, marcar
  `association_status = AMBIGUOUS`;
- incluir warning `AMBIGUOUS_MEMBRANE_ASSOCIATION`;
- no agregar el objeto a ninguna `cell`;
- reportarlo en `ambiguous.nuclei`;
- no duplicarlo en `unassociated.nuclei`;
- no participar en clasificacion nuclear de una celula hasta que exista
  desempate cientificamente aceptado.

Decision abierta:

- si se implementara area de interseccion como desempate en una version
  posterior.

### 9.4 Asociacion micronucleo -> membrana

Misma regla primaria que para nucleo:

1. Calcular centroide geometrico del MN.
2. Buscar membranas cuyo poligono contiene ese centroide.
3. Resolver:
   - 0 membranas: `membrane_id = null`, `association_status = UNASSOCIATED`.
   - 1 membrana: asociar.
   - 2+ membranas: `association_status = AMBIGUOUS`.

Un MN `AMBIGUOUS`:

- sigue contando en `total_micronuclei`;
- no se agrega a ninguna `cell`;
- se reporta en `ambiguous.micronuclei`;
- no se duplica en `unassociated.micronuclei`;
- produce warning `AMBIGUOUS_MEMBRANE_ASSOCIATION`.

### 9.5 Asociacion micronucleo -> nucleo

Despues de resolver `membrane_id` del MN:

1. Buscar solo nucleos asociados a la misma membrana.
2. Resolver:
   - 0 nucleos: `nucleus_id = null`.
   - 1 nucleo: asociacion directa.
   - 2+ nucleos: elegir nucleo con distancia euclidiana minima entre
     centroides.

No usar nucleo de mayor area como regla general. Esa decision corrige el
comportamiento legacy para celulas binucleadas/trinucleadas.

Si no hay `nucleus_id`:

- `distance_to_nucleus_px = null`;
- `area_fraction_to_nucleus = null`;
- `intensity_fraction_to_nucleus = null`.

### 9.6 Boundary rule

Un punto en borde se considera dentro.

La implementacion debe distinguir tres estados con tolerancia numerica:

```text
INSIDE
ON_BOUNDARY
OUTSIDE
```

Regla:

- `INSIDE`: asociar normalmente;
- `ON_BOUNDARY`: asociar como dentro y agregar warning opcional
  `POINT_ON_BOUNDARY`;
- `OUTSIDE`: no asociar con esa membrana.

La tolerancia de borde debe ser pequena y documentada en codigo durante Sprint
17G. El contrato no fija aun una constante porque depende de la implementacion
del algoritmo point-in-polygon.

## 10. Metricas por objeto

### 10.1 Metricas comunes

Para cada objeto medible:

```json
{
  "area_px2": 0.0,
  "perimeter_px": 0.0,
  "centroid_px": [0.0, 0.0],
  "circularity": 0.0,
  "mean_gray_intensity": 0.0
}
```

Si una metrica no es calculable:

```json
null
```

### 10.2 Membrana

Metricas requeridas:

- `area_px2`;
- `perimeter_px`;
- `centroid_px`;
- `circularity`;
- `mean_gray_intensity` solo si se decide exponer intensidad de membrana.

Decision:

- calcular internamente metricas geometricas de membrana;
- exponerlas dentro de `cell.metrics`;
- `mean_gray_intensity` de membrana queda `DEFERRED` si no se necesita en UI.

### 10.3 Nucleo

Metricas requeridas:

- `area_px2`;
- `perimeter_px`;
- `centroid_px`;
- `circularity`;
- `mean_gray_intensity`.

### 10.4 Micronucleo

Metricas requeridas:

- `area_px2`;
- `perimeter_px`;
- `centroid_px`;
- `circularity`;
- `mean_gray_intensity`;
- `distance_to_nucleus_px`;
- `area_fraction_to_nucleus`;
- `intensity_fraction_to_nucleus`.

## 11. Metricas por celula

Cada celula corresponde a una membrana efectiva.

### 11.1 Clasificacion nuclear

Clasificacion por numero de nucleos asociados a la membrana:

| Nucleos asociados | `nuclear_class` |
|---|---|
| 0 | `ANUCLEATED` |
| 1 | `MONONUCLEATED` |
| 2 | `BINUCLEATED` |
| 3 | `TRINUCLEATED` |
| >3 | `MULTINUCLEATED` |

No eliminar celulas sin nucleo ni celulas multinucleadas. Deben conservarse
descriptivamente.

### 11.2 Micronucleos por celula

Para cada celula:

```text
micronuclei_count = numero de MN asociados a esa membrana
```

Descriptor global:

```text
cells_with_2plus_micronuclei
```

Definicion:

```text
numero de membranas con micronuclei_count >= 2
```

Nombre UI recomendado:

```text
Celulas con >=2 micronucleos
```

No usar `alerta` como nombre cientifico ni como significado diagnostico.

## 12. Indices

### 12.1 Genotoxicidad

Mantener valor canonico actual:

```text
genotoxicity_index = total_micronuclei / total_membranes
```

si:

```text
total_membranes > 0
```

Si no:

```json
null
```

Es un ratio adimensional.

La UI puede derivar:

```text
micronucleus_frequency_percent = genotoxicity_index * 100
```

pero no debe persistirse obligatoriamente como metrica cientifica distinta.

Ejemplo:

```text
0.218
21.8 %
```

son dos representaciones del mismo cociente.

Estado computacional:

```text
genotoxicity_status
```

Valores:

| Valor | Condicion |
|---|---|
| `VALID` | `total_membranes > 0` |
| `NOT_COMPUTABLE` | `total_membranes == 0` |

No usar `PARTIAL` por objetos no asociados, porque genotoxicidad v2 usa conteos
globales efectivos y no depende de asociacion nucleo/MN/celula.

### 12.2 Citotoxicidad

Recuperar formula legacy como indice v2:

```text
cytotoxicity_index =
  (binucleated_cells + trinucleated_cells) / total_membranes
```

si:

```text
total_membranes > 0
```

Si no:

```json
null
```

Esta metrica solo esta disponible si la asociacion membrana -> nucleos se puede
resolver segun contrato v2.

No usar el algoritmo legacy de recortes como fuente actual.

Estado computacional:

```text
cytotoxicity_status
```

Valores:

| Valor | Condicion |
|---|---|
| `VALID` | `total_membranes > 0`, no hay nucleos `UNASSOCIATED` y no hay nucleos `AMBIGUOUS`. |
| `PARTIAL` | `total_membranes > 0` y existen nucleos `UNASSOCIATED` o `AMBIGUOUS`; se calcula con asociaciones resolubles. |
| `NOT_COMPUTABLE` | `total_membranes == 0` o la asociacion nuclear global impide un calculo significativo. |

Este estado expresa calidad computacional del calculo, no validez clinica.

## 13. Agregados

### 13.1 Conteos basicos

Los conteos basicos proceden del `effective` y no deben cambiar por fallas de
asociacion:

```text
total_membranes = count(label == "membrana")
total_nuclei = count(label == "nucleo")
total_micronuclei = count(label == "micronucleo")
```

Incluir objetos no asociados en los conteos globales.

### 13.2 Membranas analizadas

Definicion:

```text
total_membranes = numero de objetos effective con label == "membrana"
```

No limitar a membranas con nucleo.

Si se necesita otra metrica:

```text
cells_with_nucleus
```

debe reportarse como campo independiente.

### 13.3 Promedios de nucleos unicos

Corregir bug legacy: no promediar por filas de tabla MN.

Definir:

```text
mean_nucleus_area_px2 =
  promedio de area_px2 sobre nucleos unicos medibles

mean_nucleus_circularity =
  promedio de circularity sobre nucleos unicos con valor no-null
```

Cada nucleo pesa exactamente una vez, sin importar cuantos MN tenga asociados.

### 13.4 Agregados opcionales

Recomendados como `DEFERRED` para no crecer el alcance de v2 inicial:

```text
mean_micronucleus_area_px2
mean_micronucleus_circularity
```

No inventar otros agregados sin decision posterior.

### 13.5 Objetos no asociados

Reportar:

```text
unassociated_nuclei
unassociated_micronuclei
ambiguous_nuclei
ambiguous_micronuclei
```

Reglas:

- nucleo sin membrana: cuenta globalmente como nucleo, pero no participa en
  clasificacion nuclear de una celula;
- MN sin membrana: cuenta globalmente como MN, pero queda con
  `membrane_id = null`, `nucleus_id = null` y derivadas dependientes `null`;
- objetos ambiguos: contar y advertir.

Los objetos `UNASSOCIATED` y `AMBIGUOUS` deben separarse. No duplicar el mismo
objeto en ambas estructuras:

```text
unassociated.nuclei
unassociated.micronuclei
ambiguous.nuclei
ambiguous.micronuclei
```

### 13.6 Calidad de asociacion

Agregar al `summary`:

```json
{
  "association_quality": {
    "nuclei_associated": 0,
    "nuclei_total": 0,
    "nuclei_association_rate": null,

    "micronuclei_associated_to_membrane": 0,
    "micronuclei_associated_to_nucleus": 0,
    "micronuclei_total": 0,

    "micronuclei_membrane_association_rate": null,
    "micronuclei_nucleus_association_rate": null
  }
}
```

Ratios:

```text
associated / total
```

si `total > 0`.

Si `total == 0`, el ratio debe ser:

```json
null
```

No usar `0` ni `1` porque ambos pueden interpretarse como resultado medido.

## 14. JSON v2 propuesto

### 14.1 Estructura general

```json
{
  "schema_version": "2.0",
  "sample_type": "SALIVA",
  "source": {
    "type": "VALIDADA",
    "resultado_segmentacion_id": 1,
    "revision_segmentacion_id": 2,
    "numero_revision": 1
  },
  "summary": {},
  "cells": [],
  "unassociated": {},
  "ambiguous": {},
  "warnings": []
}
```

### 14.2 `summary`

```json
{
  "total_membranes": 0,
  "total_nuclei": 0,
  "total_micronuclei": 0,

  "anucleated_cells": 0,
  "mononucleated_cells": 0,
  "binucleated_cells": 0,
  "trinucleated_cells": 0,
  "multinucleated_cells": 0,

  "cells_with_nucleus": 0,
  "cells_with_2plus_micronuclei": 0,

  "genotoxicity_index": null,
  "genotoxicity_status": "NOT_COMPUTABLE",
  "cytotoxicity_index": null,
  "cytotoxicity_status": "NOT_COMPUTABLE",

  "mean_nucleus_area_px2": null,
  "mean_nucleus_circularity": null,

  "unassociated_nuclei": 0,
  "unassociated_micronuclei": 0,
  "ambiguous_nuclei": 0,
  "ambiguous_micronuclei": 0,

  "association_quality": {
    "nuclei_associated": 0,
    "nuclei_total": 0,
    "nuclei_association_rate": null,

    "micronuclei_associated_to_membrane": 0,
    "micronuclei_associated_to_nucleus": 0,
    "micronuclei_total": 0,

    "micronuclei_membrane_association_rate": null,
    "micronuclei_nucleus_association_rate": null
  }
}
```

`micronucleus_frequency_percent` debe ser UI-derived:

```text
summary.genotoxicity_index * 100
```

No persistirlo como metrica cientifica separada en v2 inicial.

### 14.3 `cell`

```json
{
  "membrane_id": 27,
  "source_raw_id": 255,
  "display_label": "Celula 27",
  "metrics": {
    "area_px2": 0.0,
    "perimeter_px": 0.0,
    "centroid_px": [0.0, 0.0],
    "circularity": 0.0,
    "mean_gray_intensity": null
  },
  "association_status": "ASSOCIATED",
  "nuclear_class": "MONONUCLEATED",
  "nuclei_count": 1,
  "micronuclei_count": 0,
  "nuclei": [],
  "micronuclei": []
}
```

`display_label` es presentacional y puede regenerarse.

### 14.4 `nucleus`

```json
{
  "id": 31,
  "source_raw_id": 255,
  "metrics": {
    "area_px2": 0.0,
    "perimeter_px": 0.0,
    "centroid_px": [0.0, 0.0],
    "circularity": 0.0,
    "mean_gray_intensity": 0.0
  },
  "association_status": "ASSOCIATED"
}
```

### 14.5 `micronucleus`

```json
{
  "id": 44,
  "source_raw_id": 255,
  "nucleus_id": 31,
  "display_label": "27.1",
  "metrics": {
    "area_px2": 0.0,
    "perimeter_px": 0.0,
    "centroid_px": [0.0, 0.0],
    "circularity": 0.0,
    "mean_gray_intensity": 0.0,
    "distance_to_nucleus_px": 0.0,
    "area_fraction_to_nucleus": 0.0,
    "intensity_fraction_to_nucleus": 0.0
  },
  "association_status": "ASSOCIATED"
}
```

`27.1` no es identidad primaria. Es etiqueta visual derivada:

```text
Celula 27, MN 1
```

### 14.6 `unassociated`

```json
{
  "nuclei": [
    {
      "id": 10,
      "source_raw_id": 255,
      "metrics": {}
    }
  ],
  "micronuclei": [
    {
      "id": 11,
      "source_raw_id": 255,
      "nucleus_id": null,
      "metrics": {
        "distance_to_nucleus_px": null,
        "area_fraction_to_nucleus": null,
        "intensity_fraction_to_nucleus": null
      }
    }
  ]
}
```

### 14.7 `ambiguous`

```json
{
  "nuclei": [
    {
      "id": 12,
      "source_raw_id": 255,
      "candidate_membrane_ids": [1, 2],
      "metrics": {}
    }
  ],
  "micronuclei": [
    {
      "id": 13,
      "source_raw_id": 255,
      "candidate_membrane_ids": [1, 2],
      "nucleus_id": null,
      "metrics": {
        "distance_to_nucleus_px": null,
        "area_fraction_to_nucleus": null,
        "intensity_fraction_to_nucleus": null
      }
    }
  ]
}
```

Un objeto ambiguo no debe aparecer simultaneamente en `unassociated`.

## 15. Warnings y errores

### 15.1 Warnings

Seccion opcional:

```json
{
  "warnings": [
    {
      "code": "IMAGE_UNAVAILABLE",
      "object_id": null,
      "message": "La imagen original no estuvo disponible para calcular intensidad."
    }
  ]
}
```

Codigos recomendados:

| Codigo | Uso |
|---|---|
| `IMAGE_UNAVAILABLE` | Imagen original ausente o ilegible. |
| `COORDINATE_SPACE_MISMATCH` | Los puntos no coinciden con dimensiones de la imagen original. |
| `INVALID_POINTS` | Objeto con puntos estructuralmente invalidos. |
| `DEGENERATE_POLYGON` | Poligono con area 0. |
| `SELF_INTERSECTING_POLYGON` | Poligono no simple con cruce de segmentos no adyacentes. |
| `INVALID_CIRCULARITY` | Circularidad mayor que `1 + CIRCULARITY_EPSILON`. |
| `UNASSOCIATED_NUCLEUS` | Nucleo fuera de toda membrana. |
| `UNASSOCIATED_MICRONUCLEUS` | MN fuera de toda membrana. |
| `AMBIGUOUS_MEMBRANE_ASSOCIATION` | Centroide cae en mas de una membrana. |
| `POINT_ON_BOUNDARY` | Centroide cae exactamente en borde. |
| `INTENSITY_UNAVAILABLE` | No se pudo calcular intensidad de un objeto. |

Warnings por objeto no son errores fatales.

### 15.2 Errores fatales

Situaciones que deben impedir caracterizar:

- `effective` no es objeto JSON;
- `effective.resultado` no existe o no es objeto JSON;
- `resultado.objects` existe pero no es lista;
- `sample_type` no soportado;
- `sample_type == BLOOD` para morfometria v2;
- contrato minimo de objeto no permite identificar `id` y `label`;
- error no recuperable de persistencia.

## 16. Precision numerica

Principio:

- backend calcula y almacena precision completa razonable de `float`;
- frontend formatea;
- no redondear antes de calculos derivados.

Formato UI sugerido:

| Campo | Formato UI |
|---|---|
| Area | 1-2 decimales |
| Perimetro | 2 decimales |
| Circularidad | 4 decimales |
| Intensidad | 4 decimales |
| Distancia | 2 decimales |
| Fraccion de area | 4 decimales |
| Fraccion de intensidad | 4 decimales |
| Indices | 4 decimales |

## 17. CSV futuro

No implementar en Sprint 17F.

El CSV debe exportar `ResultadoCaracterizacion` persistido, no recalcular en el
frontend.

Columnas recomendadas:

```text
cell_id
cell_display_label
nuclear_class
nuclei_count
micronuclei_count
nucleus_id
micronucleus_id
nucleus_area_px2
mn_area_px2
nucleus_circularity
mn_circularity
nucleus_mean_gray_intensity
mn_mean_gray_intensity
distance_px
area_fraction
intensity_fraction
source_type
resultado_segmentacion_id
revision_segmentacion_id
algorithm_version
```

Representacion de celula sin MN:

- una fila por celula;
- `micronucleus_id = null`;
- metricas MN en `null`;
- conservar `nuclear_class` y `nuclei_count`.

## 18. PDF futuro

No implementar en Sprint 17F.

El PDF debe ser presentacion de `ResultadoCaracterizacion` persistido, no
recalculo cientifico en frontend.

Debe incluir:

- resumen;
- fuente efectiva;
- fecha de caracterizacion;
- version de algoritmo;
- tabla por celula/MN;
- advertencias;
- imagen/overlay read-only si esta disponible.

Esto corrige la arquitectura legacy, donde parte del reporte se arma en
frontend desde estado de pantalla.

## 19. Overlay

No crear endpoint PNG adicional por ahora.

El refactor ya tiene overlay SVG/editable basado en:

```text
imagen original + effective objects
```

Caracterizacion puede reutilizar esa infraestructura en modo read-only.

Decision de diseno:

- no duplicar overlay con una ruta PNG backend en v2 inicial;
- usar objetos efectivos normalizados y `ResultadoCaracterizacion` persistido
  como fuente de datos.

## 20. Frontend futuro

No implementar en Sprint 17F.

Estructura recomendada:

```text
Resumen
-> Distribucion celular
-> Imagen/overlay read-only
-> Tabla por celulas/estructuras
-> Exportaciones
```

No copiar literalmente el layout legacy si genera duplicacion o recalculo en
frontend.

El frontend debe:

- consumir caracterizacion persistida;
- derivar porcentajes visuales desde indices;
- formatear unidades;
- mostrar warnings;
- no recalcular metricas cientificas.

## 21. SALIVA vs BLOOD

Para `algorithm_version` / `schema_version` 2.0:

SALIVA:

- morfometria completa segun este contrato.

BLOOD:

- mantener caracterizacion `counts-only` de v1;
- no intentar aplicar nucleo, citotoxicidad ni morfometria SALIVA;
- reportar capability `NOT_DEFINED` o equivalente hasta diseno especifico.

## 22. Versionado

La caracterizacion actual usa:

```text
CHARACTERIZATION_ALGORITHM_VERSION = "1.0"
```

SALIVA v2 cambia la semantica y la estructura JSON. Se recomienda:

```text
schema_version = "2.0"
algorithm_version = "2.0"
```

Razon del bump major:

- agrega morfometria por objeto;
- agrega asociaciones;
- cambia de conteos simples a contrato estructurado por celula;
- define unidades oficiales;
- cambia reglas de promedios;
- agrega warnings;
- recupera citotoxicidad bajo reglas nuevas.

No modificar la constante en Sprint 17F.

## 23. Ejemplos matematicos

### 23.1 Cuadrado simple

Poligono:

```json
[[0, 0], [10, 0], [10, 10], [0, 10]]
```

Area:

```text
100 px2
```

Perimetro:

```text
40 px
```

Centroide:

```json
[5, 5]
```

Circularidad:

```text
4 * pi * 100 / 40^2 = pi / 4 = 0.785398...
```

### 23.2 Asociacion con dos membranas

Membrana A:

```json
id=1, points=[[0,0], [100,0], [100,100], [0,100]]
```

Membrana B:

```json
id=2, points=[[200,0], [300,0], [300,100], [200,100]]
```

Nucleo:

```json
id=3, centroid=[50,50]
```

Resultado:

```text
nucleo 3 -> membrana 1
```

MN:

```json
id=4, centroid=[250,50]
```

Resultado:

```text
micronucleo 4 -> membrana 2
```

Si membrana 2 no tiene nucleos asociados:

```text
micronucleo 4 -> nucleus_id = null
distance_to_nucleus_px = null
area_fraction_to_nucleus = null
intensity_fraction_to_nucleus = null
```

### 23.3 Celula binucleada y citotoxicidad

Tres membranas:

- celula 1: 1 nucleo;
- celula 2: 2 nucleos;
- celula 3: 3 nucleos.

Resumen:

```text
total_membranes = 3
mononucleated_cells = 1
binucleated_cells = 1
trinucleated_cells = 1
```

Citotoxicidad:

```text
(binucleated_cells + trinucleated_cells) / total_membranes
= (1 + 1) / 3
= 0.666666...
```

## 24. Casos limite

| Caso | Comportamiento v2 |
|---|---|
| 0 membranas | conteos globales validos; indices con denominador membranas = `null`. |
| 0 nucleos | nucleos globales 0; celulas `ANUCLEATED`; citotoxicidad 0 si hay membranas. |
| 0 MN | micronucleos globales 0; genotoxicidad 0 si hay membranas. |
| Poligono con <3 puntos | objeto no medible; warning `INVALID_POINTS`. |
| Poligono degenerado | area 0, centroide `null`, circularity `null`, warning `DEGENERATE_POLYGON`. |
| Poligono auto-intersectado | conservar objeto; `area_px2`, `centroid_px`, `circularity` y asociacion en `null`; warning `SELF_INTERSECTING_POLYGON`. |
| Circularidad `1 < C <= 1 + 1e-9` | normalizar a `1.0`. |
| Circularidad `C > 1 + 1e-9` | `circularity = null`; warning `INVALID_CIRCULARITY`. |
| Intensidad nucleo = 0 | `intensity_fraction_to_nucleus = null`. |
| Objeto fuera de toda membrana | cuenta global; se reporta en `unassociated`. |
| Objeto dentro de membranas superpuestas | cuenta global; se reporta en `ambiguous`, no en `unassociated`. |
| Membranas superpuestas | asociacion ambigua si el centroide cae en mas de una. |
| Nucleo en borde | considerar dentro; warning opcional `POINT_ON_BOUNDARY`. |
| MN en borde | considerar dentro; warning opcional `POINT_ON_BOUNDARY`. |
| Celula con multiples nucleos | clasificar segun conteo. |
| Celula con multiples MN | `micronuclei_count` y display labels por MN. |
| Imagen original ausente | intensidad `null`; warning `IMAGE_UNAVAILABLE`; no falla total. |
| Dimensiones imagen/puntos no coinciden | intensidad bloqueada; warning `COORDINATE_SPACE_MISMATCH`. |
| Revision VALIDADA con objetos manuales | medir geometria validada; no aplicar filtros de deteccion. |
| Resultado BLOOD | mantener counts-only; no aplicar SALIVA v2. |

## 25. Decisiones abiertas

| Decision | Propuesta | Evidencia | Riesgo | Estado |
|---|---|---|---|---|
| Area oficial | Shoelace vectorial | `geometry.py` ya tiene `polygon_area`; legacy usaba raster PIL para intensidad/area | Diferencia numerica contra area raster legacy | CLOSED |
| Perimetro oficial | Suma euclidiana cerrada | `geometry.py` ya tiene `polygon_perimeter`; legacy usa formula equivalente | Bajo | CLOSED |
| Centroide oficial | Centroide geometrico por area orientada | Legacy usaba promedio de vertices; contrato v2 busca consistencia geometrica | Puede cambiar asociaciones frente al legacy | CLOSED |
| Circularidad | `4*pi*A/P^2` | Legacy `backend/creacion` y BLOOD la usan como concepto; v2 la formaliza | Poligonos complejos pueden producir valores atipicos | CLOSED |
| Tolerancia circularidad | `CIRCULARITY_EPSILON = 1e-9`; solo normalizar `1 < C <= 1 + epsilon` | Error float de doble precision | Valores mayores quedan como warning | CLOSED |
| Clamp circularidad | No clamp general | Legacy clamp a 1.0 ocultaba inconsistencias | UI puede mostrar `null` por problemas geometricos | CLOSED |
| Intensidad gris | PIL `convert("L")`, media / 255 | Confirmado en `backend/creacion` | No equivale a canal biologico | CLOSED |
| Coordenadas SALIVA | `ORIGINAL_IMAGE_COORDINATES` | `cv2.imdecode`, mascaras con `imagen_rgb.shape[:2]`, normalizador sin transformacion | Futuro resize romperia intensidad si no se documenta | CLOSED |
| Autointerseccion | Warning y metricas geometricas principales `null` | Shoelace no es fiable para poligonos no simples | Requiere detector de segmentos | CLOSED |
| Asociacion primaria | Point-in-polygon de centroide sobre membrana | Corrige proximidad legacy | Requiere implementar helper robusto | CLOSED |
| Desempate por membranas superpuestas | Marcar ambiguo en v2 inicial | No hay evidencia suficiente para interseccion robusta | Menos asociaciones automaticas | OPEN |
| MN -> nucleo | Nucleo mas cercano dentro de misma membrana | Corrige nucleo principal por mayor area | Puede requerir validacion experta | CLOSED |
| Genotoxicidad | `total_micronuclei / total_membranes` | Refactor actual ya lo usa como ratio | UI debe diferenciar ratio vs porcentaje | CLOSED |
| `genotoxicity_status` | `VALID` o `NOT_COMPUTABLE` | No depende de asociacion | Bajo | CLOSED |
| Citotoxicidad | `(binucleated + trinucleated) / total_membranes` | Formula legacy confirmada | Depende de asociacion robusta | CLOSED |
| `cytotoxicity_status` | `VALID`, `PARTIAL`, `NOT_COMPUTABLE` | Necesario por nucleos no asociados/ambiguos | Puede requerir explicacion UI | CLOSED |
| Calidad de asociacion | `association_quality` con ratios o `null` si total 0 | Necesario para trazabilidad computacional | Bajo | CLOSED |
| Promedios | Nucleos unicos, no filas MN | Corrige bug legacy documentado | Requiere estructura por objeto | CLOSED |
| Termino alerta | Usar `cells_with_2plus_micronuclei`, no `alerta` | Evita significado diagnostico implicito | UI legacy usaba alerta | CLOSED |
| BLOOD en v2 | Mantener counts-only | No hay caracterizacion BLOOD equivalente | Usuarios pueden esperar simetria | CLOSED |
| CSV/PDF | Exportar caracterizacion persistida | Corrige arquitectura legacy frontend-heavy | Requiere sprint separado | DEFERRED |
| Overlay | Reusar SVG read-only | Refactor ya tiene overlay SVG | No replica PNG legacy | CLOSED |
| Calibracion fisica | No disponible | Auditoria no encontro pixel->um | Unidades clinicas no disponibles | OPEN |

## 26. Criterios de aceptacion para Sprint 17G

El backend debera demostrar:

- tests unitarios de `polygon_area`;
- tests unitarios de `polygon_perimeter`;
- tests unitarios de centroide geometrico;
- tests unitarios de circularidad;
- tests de `CIRCULARITY_EPSILON = 1e-9`;
- tests de `INVALID_CIRCULARITY`;
- tests de deteccion de autointerseccion;
- tests con poligono simple;
- tests con bow-tie/self-crossing;
- tests con segmentos colineales;
- tests del segmento de cierre;
- tests de point-in-polygon incluyendo borde;
- tests de `INSIDE`, `ON_BOUNDARY` y `OUTSIDE`;
- tests de asociacion nucleo -> membrana;
- tests de asociacion MN -> membrana;
- tests de asociacion MN -> nucleo dentro de la misma membrana;
- tests de objetos no asociados;
- tests de objetos ambiguos;
- tests de poligonos degenerados;
- tests de intensidad desde imagen original;
- tests de sistema de coordenadas SALIVA con imagen real o fixture local;
- tests de alineacion de mascara de intensidad contra `geometry.points`;
- tests de degradacion parcial cuando falta imagen;
- tests de `COORDINATE_SPACE_MISMATCH`;
- tests de `effective` automatico;
- tests de `effective` validado;
- test que confirme que `BORRADOR` no se usa;
- test de `genotoxicity_index` ratio;
- test de `genotoxicity_status = VALID`;
- test de `genotoxicity_status = NOT_COMPUTABLE`;
- test de `cytotoxicity_index`;
- test de `cytotoxicity_status = VALID`;
- test de `cytotoxicity_status = PARTIAL`;
- test de `cytotoxicity_status = NOT_COMPUTABLE`;
- tests de `association_quality` y ratios `null` cuando total es 0;
- test de promedios por nucleos unicos;
- test de `cells_with_2plus_micronuclei`;
- test de JSON `schema_version = "2.0"`;
- test de no mutar snapshot ni resultado normalizado;
- test de idempotencia de `ResultadoCaracterizacion`;
- test de stale cuando cambia revision validada;
- test de no regresion para BLOOD counts-only.

El frontend no debe recalcular metricas cientificas en Sprint 17G.

## 27. Checklist de no implementacion

En Sprint 17F:

- no se modifico codigo;
- no se modificaron modelos;
- no se crearon migraciones;
- no se modifico frontend;
- no se implementaron endpoints;
- no se modificaron microservicios;
- no se modifico `docs/30_developer_startup_and_test_data.md`;
- no se hizo commit.

## 28. Conclusion

Sprint 17F = PASS WITH OPEN DECISIONS.

Quedan cerradas las decisiones necesarias para una primera implementacion
SALIVA v2:

- area geometrica por shoelace;
- perimetro euclidiano cerrado;
- centroide geometrico;
- circularidad `4*pi*A/P^2`;
- intensidad gris normalizada `0..1`;
- point-in-polygon como asociacion primaria;
- MN -> nucleo por nucleo mas cercano dentro de la misma membrana;
- genotoxicidad como ratio;
- citotoxicidad legacy recuperada bajo asociacion v2;
- unidades `px` y `px2`;
- no usar `um` sin calibracion;
- promedios por objetos unicos;
- no usar `alerta` como termino cientifico;
- BLOOD fuera de morfometria v2;
- version `2.0`.

Permanecen abiertas:

- calibracion fisica pixel -> micrometro;
- desempate robusto por interseccion cuando un objeto cae en membranas
  superpuestas;
- alcance y formato final de CSV/PDF;
- validacion cientifica externa de las reglas antes de uso diagnostico.

## 29. Adenda Sprint 17F.1 - hardening final

Sprint 17F.1 endurece el contrato sin cambiar `schema_version = "2.0"` porque
el contrato aun no ha sido implementado ni publicado como API estable.

Puntos cerrados:

- coordenadas SALIVA auditadas como `ORIGINAL_IMAGE_COORDINATES`;
- `mean_gray_intensity` puede rasterizar con `geometry.points` directamente
  mientras las dimensiones de imagen original coincidan;
- poligonos auto-intersectados producen `SELF_INTERSECTING_POLYGON` y no son
  morfometricamente validos;
- circularidad usa `CIRCULARITY_EPSILON = 1e-9`;
- citotoxicidad reporta `cytotoxicity_status`;
- genotoxicidad reporta `genotoxicity_status`;
- `summary.association_quality` expone tasas de asociacion;
- `unassociated` y `ambiguous` quedan separados;
- `ON_BOUNDARY` cuenta como dentro para asociacion.

Conclusion Sprint 17F.1:

```text
PASS WITH OPEN DECISIONS
```

Bloqueos no fatales para Sprint 17G:

- calibracion fisica sigue abierta;
- desempate por interseccion en membranas superpuestas sigue abierto;
- la prueba de coordenadas con imagen real debe confirmar que no existe
  `COORDINATE_SPACE_MISMATCH` antes de habilitar intensidad como metrica
  plenamente confiable.
