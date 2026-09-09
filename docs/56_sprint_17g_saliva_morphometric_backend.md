# Sprint 17G - Backend de Caracterizacion SALIVA v2

## Fecha

2026-09-03 18:23:49 -06:00

## Referencia Git

- Rama: `master`
- Commit base observado: `410060d`

## Objetivo

Implementar en backend la caracterizacion morfometrica SALIVA v2 definida en:

```text
docs/55_sprint_17f_saliva_morphometric_contract.md
```

La fuente efectiva de caracterizacion sigue siendo:

```text
ResultadoSegmentacion -> resolve_effective_segmentation()
```

Prioridad de fuente:

1. ultima `RevisionSegmentacion` en estado `VALIDADA`;
2. resultado automatico cuando no existe revision validada;
3. `BORRADOR` nunca se usa para caracterizacion.

## Alcance implementado

Se agrego la capa computacional SALIVA v2 sin cambiar modelos, migraciones ni endpoints.

SALIVA ahora usa:

```text
algorithm_version = "2.0"
schema_version = "2.0"
```

BLOOD conserva el comportamiento existente de conteos:

```text
algorithm_version = "1.0"
```

## Archivos modificados

- `apps/web/Backend/api/services/characterization/__init__.py`
- `apps/web/Backend/api/services/characterization/geometry.py`
- `apps/web/Backend/api/services/characterization/intensity.py`
- `apps/web/Backend/api/services/characterization/saliva.py`
- `apps/web/Backend/api/services/characterization/service.py`
- `apps/web/Backend/api/services/characterization/types.py`
- `apps/web/Backend/api/tests.py`

No se crearon migraciones.

## Formulas y reglas implementadas

### Geometria

- Area de poligono con formula shoelace.
- Perimetro como suma de distancias euclidianas entre vertices consecutivos y cierre.
- Centroide de poligono usando area firmada.
- Circularidad:

```text
4 * pi * area / perimeter^2
```

Si la circularidad queda apenas arriba de 1 por tolerancia numerica, se normaliza a `1.0`.
Si excede la tolerancia, se reporta `INVALID_CIRCULARITY`.

### Validacion espacial

- Puntos no numericos, booleanos, infinitos o `NaN` invalidan geometria.
- Poligonos auto-intersectantes se marcan con `SELF_INTERSECTING_POLYGON`.
- Poligonos degenerados se marcan con `DEGENERATE_POLYGON`.
- `INSIDE` y `ON_BOUNDARY` cuentan como dentro.
- `ON_BOUNDARY` agrega warning `POINT_ON_BOUNDARY`.

### Asociacion celular

- `nucleo` y `micronucleo` se asocian por centroide a `membrana`.
- Si un objeto cae en una sola membrana, queda asociado.
- Si no cae en membrana, va a `unassociated`.
- Si cae en varias membranas, va a `ambiguous`.
- Los micronucleos asociados a una membrana se vinculan al nucleo mas cercano de la misma celula.

### Indices

- `genotoxicity_index = total_micronuclei / total_membranes`
- `cytotoxicity_index = (binucleated_cells + trinucleated_cells) / total_membranes`
- `genotoxicity_status` es `VALID` o `NOT_COMPUTABLE`; no depende de asociacion.
- `cytotoxicity_status` puede ser `VALID`, `PARTIAL` o `NOT_COMPUTABLE`.

### Intensidad

- Se intenta cargar la imagen original asociada a la muestra.
- La intensidad se calcula como media de gris normalizada en `[0, 1]`.
- Si no hay imagen o es ilegible, se reporta `IMAGE_UNAVAILABLE`.
- Si los puntos no caben en la imagen, se reporta `COORDINATE_SPACE_MISMATCH`.

## Contrato de salida SALIVA v2

La caracterizacion SALIVA devuelve:

```text
version
schema_version
sample_type
source
summary
cells
unassociated
ambiguous
warnings
```

El resultado automatico y las revisiones expertas no se modifican.

## Idempotencia

Se conserva la politica previa de `ResultadoCaracterizacion`:

- no hay `PATCH` ni `PUT`;
- si existe una caracterizacion vigente para la misma fuente efectiva y version de algoritmo, se reutiliza;
- si cambia la revision validada efectiva, se crea un nuevo snapshot;
- si cambia la version de algoritmo, se crea un nuevo snapshot;
- `respuesta_json` y `resultado_normalizado` de `ResultadoSegmentacion` permanecen intactos.

## Pruebas agregadas o actualizadas

Se actualizaron las pruebas de caracterizacion para cubrir:

- area, area firmada, perimetro y centroide;
- circularidad con tolerancia numerica;
- poligonos auto-intersectantes;
- punto dentro, fuera y sobre borde;
- poligono concavo;
- uso de fuente efectiva automatica;
- ignorar `BORRADOR`;
- uso de la ultima revision `VALIDADA`;
- preservacion de `respuesta_json` y `resultado_normalizado`;
- asociacion de nucleos y micronucleos a membranas;
- objetos no asociados;
- objetos ambiguos;
- warnings `POINT_ON_BOUNDARY`, `SELF_INTERSECTING_POLYGON` y `COORDINATE_SPACE_MISMATCH`;
- intensidad media desde imagen original;
- medias morfometricas sin duplicar nucleos;
- cambio de version de algoritmo;
- no regresion de BLOOD counts-only;
- endpoint de caracterizacion;
- rechazo de resultado efectivo invalido.

## Comandos ejecutados

### Suite localizada

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -m pytest api/tests.py::CharacterizationCoreTests -q
```

Resultado:

```text
31 passed
```

### Django check

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' manage.py check
```

Resultado:

```text
System check identified no issues (0 silenced).
```

### Migraciones

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' manage.py makemigrations --check
```

Resultado:

```text
No changes detected
```

### Pytest completo

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -m pytest -q
```

Resultado:

```text
172 passed, 2 skipped in 4.03s
```

### Django test

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' manage.py test
```

Resultado:

```text
Ran 147 tests in 1.959s
OK
```

## Smoke real SALIVA v2

Se ejecuto un smoke operacional sobre la base local usando resultados ya existentes. No se llamo al microservicio SALIVA, no se ejecuto una nueva segmentacion y no se crearon datos demo adicionales.

El primer intento con `APIClient` sin host explicito devolvio HTTP 400 porque el cliente usa `testserver` y el proyecto valida `ALLOWED_HOSTS`. El smoke se repitio con `HTTP_HOST=127.0.0.1`, sin cambios de codigo.

### Caso SALIVA AUTOMATICO

- `MuestraSaliva.id_muestra`: `4`
- Imagen tecnica: `muestras/saliva/2026/08/02_CgVvP6u.jpg`
- `ResultadoSegmentacion.id`: `19`
- Fuente efectiva: `AUTOMATICO`
- `ResultadoCaracterizacion.id`: `17`
- `algorithm_version`: `2.0`
- `schema_version`: `2.0`
- Primer POST exitoso: HTTP `201`
- Repeticiones de idempotencia: HTTP `200`, HTTP `200`
- Duplicados v2 creados: `0`

Resumen:

```text
total_membranes: 30
total_nuclei: 20
total_micronuclei: 9
anucleated_cells: 10
mononucleated_cells: 20
binucleated_cells: 0
trinucleated_cells: 0
multinucleated_cells: 0
cells_with_nucleus: 20
cells_with_2plus_micronuclei: 2
genotoxicity_index: 0.3
genotoxicity_status: VALID
cytotoxicity_index: 0.0
cytotoxicity_status: VALID
mean_nucleus_area_px2: 303.95
mean_nucleus_circularity: 0.8339761342295929
unassociated_nuclei: 0
unassociated_micronuclei: 1
ambiguous_nuclei: 0
ambiguous_micronuclei: 0
```

Calidad de asociacion:

```text
nuclei_associated / nuclei_total: 20 / 20
nuclei_association_rate: 1.0
micronuclei_associated_to_membrane / micronuclei_total: 8 / 9
micronuclei_membrane_association_rate: 0.8888888888888888
micronuclei_associated_to_nucleus / micronuclei_total: 8 / 9
micronuclei_nucleus_association_rate: 0.8888888888888888
```

Warnings:

```text
SELF_INTERSECTING_POLYGON: 1
UNASSOCIATED_MICRONUCLEUS: 1
```

Intensidad:

```text
available: 58
null: 1
out_of_range: 0
min: 0.348096
max: 0.826054
```

Validaciones matematicas:

```text
total_membranes == count label membrana: true
total_nuclei == count label nucleo: true
total_micronuclei == count label micronucleo: true
cell class sum == total_membranes: true
cytotoxicity formula: 0.0
genotoxicity formula: 0.3
genotoxicity percent audit: 30.0
```

Cells inspeccionadas:

| Motivo | membrane_id | nuclear_class | nuclei_count | micronuclei_count | nucleo | micronucleo |
| --- | ---: | --- | ---: | ---: | --- | --- |
| mononucleated | 2 | MONONUCLEATED | 1 | 0 | id 50, area 346.0, circularity 0.6153106332880505, intensity 0.48708660575947 | n/a |
| with_micronucleus | 3 | MONONUCLEATED | 1 | 1 | id 49, area 296.0, circularity 0.9163971194770059, intensity 0.4701702624623517 | id 59, nucleus_id 49, area 38.5, distance 64.34583535732244 |
| with_2plus_micronuclei | 22 | MONONUCLEATED | 1 | 2 | id 36, area 256.5, circularity 0.9303435144439415, intensity 0.5767657600674678 | id 54, nucleus_id 36, area 18.5, distance 27.367054501613353 |
| anucleated | 1 | ANUCLEATED | 0 | 0 | n/a | n/a |

No mutacion:

```text
ResultadoSegmentacion.respuesta_json unchanged: true
ResultadoSegmentacion.resultado_normalizado unchanged: true
RevisionSegmentacion snapshot unchanged: true
```

Historial:

```text
2.0 AUTOMATICO id 17 vigente true
1.0 AUTOMATICO id 13 vigente false
```

### Caso SALIVA VALIDADA

- `MuestraSaliva.id_muestra`: `4`
- Imagen tecnica: `muestras/saliva/2026/08/02_CgVvP6u.jpg`
- `ResultadoSegmentacion.id`: `10`
- Fuente efectiva: `VALIDADA`
- `RevisionSegmentacion.id`: `19`
- `numero_revision`: `6`
- `ResultadoCaracterizacion.id`: `18`
- `algorithm_version`: `2.0`
- `schema_version`: `2.0`
- POST de creacion: HTTP `201`
- POST de idempotencia: HTTP `200`
- Duplicados v2 creados: `0`

Resumen:

```text
total_membranes: 27
total_nuclei: 19
total_micronuclei: 9
anucleated_cells: 8
mononucleated_cells: 19
binucleated_cells: 0
trinucleated_cells: 0
multinucleated_cells: 0
cells_with_nucleus: 19
cells_with_2plus_micronuclei: 2
genotoxicity_index: 0.3333333333333333
genotoxicity_status: VALID
cytotoxicity_index: 0.0
cytotoxicity_status: VALID
mean_nucleus_area_px2: 290.7736710526362
mean_nucleus_circularity: 0.837136071697902
unassociated_nuclei: 0
unassociated_micronuclei: 1
ambiguous_nuclei: 0
ambiguous_micronuclei: 0
```

Calidad de asociacion:

```text
nuclei_associated / nuclei_total: 19 / 19
nuclei_association_rate: 1.0
micronuclei_associated_to_membrane / micronuclei_total: 8 / 9
micronuclei_membrane_association_rate: 0.8888888888888888
micronuclei_associated_to_nucleus / micronuclei_total: 8 / 9
micronuclei_nucleus_association_rate: 0.8888888888888888
```

Warnings:

```text
SELF_INTERSECTING_POLYGON: 2
UNASSOCIATED_MICRONUCLEUS: 1
```

Intensidad:

```text
available: 53
null: 2
out_of_range: 0
min: 0.348096
max: 0.826054
```

Validaciones matematicas:

```text
total_membranes == count label membrana: true
total_nuclei == count label nucleo: true
total_micronuclei == count label micronucleo: true
cell class sum == total_membranes: true
cytotoxicity formula: 0.0
genotoxicity formula: 0.3333333333333333
genotoxicity percent audit: 33.33333333333333
```

Cells inspeccionadas:

| Motivo | membrane_id | nuclear_class | nuclei_count | micronuclei_count | nucleo | micronucleo |
| --- | ---: | --- | ---: | ---: | --- | --- |
| mononucleated | 3 | MONONUCLEATED | 1 | 1 | id 49, area 296.0, circularity 0.9163971194770059, intensity 0.4701702624623517 | id 59, nucleus_id 49, area 38.5, distance 64.34583535732244 |
| with_micronucleus | 17 | MONONUCLEATED | 1 | 1 | id 40, area 299.0, circularity 0.6316233234566705, intensity 0.38846886717069273 | id 58, nucleus_id 40, area 25.0, distance 99.98462749030654 |
| with_2plus_micronuclei | 22 | MONONUCLEATED | 1 | 2 | id 36, area 256.5, circularity 0.9303435144439415, intensity 0.5767657600674678 | id 54, nucleus_id 36, area 18.5, distance 27.367054501613353 |
| anucleated | 5 | ANUCLEATED | 0 | 0 | n/a | n/a |

No mutacion:

```text
ResultadoSegmentacion.respuesta_json unchanged: true
ResultadoSegmentacion.resultado_normalizado unchanged: true
RevisionSegmentacion snapshot unchanged: true
```

Historial:

```text
2.0 VALIDADA id 18 revision 19 vigente true
1.0 VALIDADA id 12 revision 19 vigente false
1.0 VALIDADA id 11 revision 12 vigente false
1.0 VALIDADA id 3 revision 11 vigente false
```

### BLOOD quick regression

Se uso un resultado BLOOD existente sin ejecutar segmentacion BLOOD.

- `ResultadoSegmentacion.id`: `21`
- `MuestraSangre.id_muestra`: `5`
- HTTP status: `200`
- `ResultadoCaracterizacion.id`: `15`
- `algorithm_version`: `1.0`
- `source_type`: `AUTOMATICO`

Salida confirmada como counts-only:

```text
counts: {'membrana': 350, 'micronucleo': 1}
indices: {}
contains_saliva_morphometry: false
```

### Clasificacion del smoke

Resultado:

```text
PASS WITH WARNINGS
```

Los warnings observados se clasifican como `DATA QUALITY` o `EXPECTED WARNING` del contrato v2. No se observo `COORDINATE_SPACE_MISMATCH`, no hubo intensidad fuera de rango y no se detectaron anomalias matematicas de area, perimetro o circularidad.

## Limitaciones

- No se implemento caracterizacion morfometrica BLOOD.
- No se modifico frontend.
- El smoke real se ejecuto sobre datos locales existentes; no se ejecuto una nueva segmentacion.
- La intensidad actual usa una implementacion simple por mascara raster; puede optimizarse despues si el volumen de imagenes lo requiere.
- No se hizo backfill de caracterizaciones historicas.

## Pendientes recomendados

- Revisión visual/frontend del nuevo contrato de caracterizacion.
- Definir si BLOOD requiere contrato morfometrico propio o permanece counts-only.
- Documentar ejemplos de salida reales una vez exista smoke validado con datos demo.

## Conclusion

PASS WITH WARNINGS.

El backend queda validado para Caracterizacion SALIVA v2 sin migraciones y sin cambios de endpoints. Los warnings del smoke real corresponden a calidad de geometria/asociacion en datos existentes y no bloquearon el flujo.
