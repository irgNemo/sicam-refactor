# Sprint 16B - Integracion backend E2E de segmentacion de sangre

## Proposito

Implementar el flujo backend completo para segmentar una `MuestraSangre` existente, sin modificar frontend ni microservicios.

El flujo queda:

```text
MuestraSangre.imagen
-> Django REST
-> segment_image("SANGRE", image_bytes, filename=...)
-> apps/segmentation-blood
-> respuesta JSON cruda
-> normalizacion 1.1 con sample_type SANGRE
-> ResultadoSegmentacion(muestra_sangre=..., tipo_muestra="SANGRE")
-> historial / revisiones / effective comunes
```

## Endpoint Django

Ruta agregada:

```http
POST /api/muestras-sangre/{id}/segmentar/
```

Ruta de historial agregada:

```http
GET /api/muestras-sangre/{id}/resultados-segmentacion/
```

El endpoint recibe solo el ID de la muestra. Django lee `MuestraSangre.imagen` desde storage usando el `ImageField`; el frontend no debe reenviar el archivo.

## Configuracion del microservicio

No se hardcodearon URLs en views.

Se reutiliza:

```python
settings.SEGMENTATION_SERVICES["SANGRE"]
```

Valores por defecto actuales:

```text
BLOOD_SEGMENTATION_SERVICE_URL=http://localhost:8002
BLOOD_SERVICE_TIMEOUT=240
```

El timeout de BLOOD se amplio a `240` segundos despues de observar una inferencia
directa real de `116.174261` segundos en CPU. `SALIVA_SERVICE_TIMEOUT` se
mantiene en `30` segundos.

No se agregaron variables nuevas y no se modifico `.env`.

## Client / adapter usado

Se reutiliza:

```python
segment_image(SampleType.BLOOD, image_bytes, filename=muestra.imagen.name)
```

La factory resuelve:

```text
SANGRE -> BloodSegmentationClient
```

El cliente usa:

```http
POST /api/v1/segmentar
Content-Type: multipart/form-data
field: file
```

## Contrato multipart

El request al microservicio usa:

```python
files = {
    "file": (filename, image_bytes)
}
```

con `timeout` configurado desde settings.

## Persistencia de ResultadoSegmentacion

### Exito

Si la llamada al microservicio y la normalizacion son validas:

```text
tipo_muestra = SANGRE
muestra = None
muestra_sangre = <MuestraSangre>
estado = COMPLETADO
respuesta_json = respuesta cruda del microservicio
resultado_normalizado = contrato 1.1
```

Se conserva cada ejecucion como un nuevo `ResultadoSegmentacion`, igual que saliva.

### Error

Si falla la llamada o la validacion/normalizacion:

```text
tipo_muestra = SANGRE
muestra = None
muestra_sangre = <MuestraSangre>
estado = ERROR
error = mensaje controlado
resultado_normalizado = None
```

Cuando existe respuesta cruda pero falla la validacion, `respuesta_json` conserva esa respuesta para trazabilidad.

## Respuesta Django

En exito, la respuesta conserva el shape usado por saliva:

```json
{
  "objetos": [],
  "resultado_segmentacion": {
    "id": 1,
    "estado": "COMPLETADO",
    "tipo_muestra": "SANGRE",
    "creado_en": "..."
  },
  "resultado_normalizado": {}
}
```

En error, responde con:

```json
{
  "error": "...",
  "resultado_segmentacion": {
    "id": 1,
    "estado": "ERROR",
    "tipo_muestra": "SANGRE",
    "creado_en": "..."
  }
}
```

No se cambio el contrato de saliva.

## Raw response

La respuesta cruda de `segmentation-blood` se guarda sin modificar semantica:

```json
{
  "objetos": [
    {
      "id": 1,
      "tipo": "membrana",
      "puntos": [[1, 1], [10, 1], [10, 10]]
    },
    {
      "id": 1,
      "tipo": "micronucleo",
      "puntos": [[4, 4], [5, 4], [5, 5]]
    }
  ]
}
```

## Normalizacion 1.1

Se reutiliza el normalizador comun:

```python
normalize_segmentation_result(raw_result, sample_type=SampleType.BLOOD)
```

Despues se valida de forma estricta antes de persistir `COMPLETADO`:

- labels permitidos para sangre: `membrana`, `micronucleo`;
- `geometry.type = "polygon"`;
- `geometry.points` con al menos 3 puntos;
- coordenadas finitas.

No se agregan labels de saliva como `nucleo`.

## Duplicate raw IDs

El microservicio puede devolver raw IDs repetidos entre clases, por ejemplo:

```text
membrana id=1
micronucleo id=1
```

El normalizador conserva:

```text
source.raw_id = 1
```

pero genera IDs editoriales unicos:

```text
objects[].id = 1..N
```

Esto mantiene estable el editor experto.

## Summary blood

El resumen normalizado para sangre usa solo labels reales de sangre:

```json
{
  "counts_by_label": {
    "membrana": 1,
    "micronucleo": 1
  },
  "total_objects": 2
}
```

No se agrega `nucleo=0`.

## Pipeline cientifico BLOOD recuperado del legacy

Esta auditoria describe el pipeline ejecutable actual de:

```text
apps/segmentation-blood/segmentacion_core/sicam_master.py
```

No se modificaron algoritmos, thresholds ni labels.

### Entrada y decodificacion

El endpoint FastAPI recibe un `UploadFile` en:

```http
POST /api/v1/segmentar
```

El campo multipart es:

```text
file
```

`app/routers/segmentacion.py` lee los bytes y ejecuta:

```text
run_in_threadpool(segmentar_pipeline, contenido)
```

`app/services/segmentador.py` delega en:

```text
segmentacion_core.sicam_master.segmentar_desde_bytes(file_bytes)
```

`segmentar_desde_bytes()` hace:

```text
bytes -> np.frombuffer -> cv2.imdecode(..., cv2.IMREAD_COLOR) -> cv2.cvtColor(BGR, RGB)
```

Si `cv2.imdecode()` no puede decodificar la imagen, lanza:

```text
ValueError("No se pudo decodificar la imagen. Verifica el formato.")
```

### Preprocesamiento

`_preprocesar(img_rgb)` aplica:

```text
1. skimage.transform.resize(img_rgb, (224, 224, 3), anti_aliasing=True)
2. conversion a uint8 multiplicando por 255
3. cv2.cvtColor(..., cv2.COLOR_RGB2GRAY)
4. gamma = 0.8 con cv2.LUT
5. cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8, 8))
6. cv2.GaussianBlur(img_clahe, (3, 3), 0)
7. cv2.addWeighted(img_clahe, 1.5, gaussian, -0.5, 0)
```

La salida de preprocesamiento es una imagen en grises de `224x224`.

### Cellpose

`_segmentar_celulas(img_rgb)` obtiene el modelo con:

```python
models.CellposeModel(gpu=False)
```

El modelo se guarda globalmente en `_modelo` y se reutiliza.

La llamada real a Cellpose es:

```python
masks_224, _, _ = modelo.eval(img_prep, diameter=None, channels=[0, 0])
```

Parametros reales:

```text
gpu = False
diameter = None
channels = [0, 0]
```

La mascara `masks_224` se escala al tamano original si hace falta con:

```text
skimage.transform.resize(..., order=0, preserve_range=True, anti_aliasing=False)
```

Esto preserva IDs enteros por nearest-neighbor. La mascara resultante representa celulas y se retorna como:

```text
resultado["celulas"]
```

El endpoint convierte esa mascara a objetos con:

```python
obtener_poligonos_desde_mascara(resultado["celulas"], "membrana")
```

Por tanto, en el contrato HTTP actual, las celulas segmentadas por Cellpose se publican como:

```text
tipo = "membrana"
```

### Micronucleos

`_detectar_micronucleos(img_gris, masks)` recibe la imagen original en grises y la mascara de celulas.

Constantes reales del codigo:

```text
UMBRAL_ZSCORE_CELULA = 8
UMBRAL_ZSCORE_PIXEL = 3
MIN_PIXELES_CLUSTER = 5
MIN_PUNTOS_CLUSTER = 6
CIRCULARIDAD_MINIMA = 0.5
DBSCAN_EPS = 2.5
DBSCAN_MIN_SAMPLES = 4
```

Para cada ID de celula distinto de cero:

```text
pixeles = img_gris[masks == cell_id]
```

Se calcula z-score robusto de celula completa con:

```text
0.6745 * (max(pixeles) - mediana) / MAD
```

Si `MAD == 0`, se usa:

```text
mad = 1e-9
```

La celula se considera candidata si:

```text
zscore_robusto_celula > UMBRAL_ZSCORE_CELULA
```

Para cada celula candidata:

```text
coords = np.argwhere(masks == cell_id)
intensidades = img_gris[coords[:, 0], coords[:, 1]]
mediana = np.median(intensidades)
mad = np.median(np.abs(intensidades - mediana)) + 1e-9
z_pixs = 0.6745 * (intensidades - mediana) / mad
coords_b = coords[z_pixs > UMBRAL_ZSCORE_PIXEL]
```

Si `len(coords_b) < MIN_PIXELES_CLUSTER`, la celula candidata se omite.

### DBSCAN

DBSCAN se instancia en:

```text
apps/segmentation-blood/segmentacion_core/sicam_master.py
_detectar_micronucleos()
```

Parametros exactos:

```python
DBSCAN(eps=DBSCAN_EPS, min_samples=DBSCAN_MIN_SAMPLES, n_jobs=1)
```

Valores reales:

```text
eps = 2.5
min_samples = 4
n_jobs = 1
```

No se declara `metric`, por lo que se usa el default de `sklearn.cluster.DBSCAN`.

Los datos de entrada a DBSCAN son coordenadas de pixeles brillantes:

```text
coords_b
```

El ruido se identifica con:

```text
label == -1
```

y se descarta.

Un cluster se conserva si:

```text
len(cluster_coords) >= MIN_PUNTOS_CLUSTER
```

### Circularidad

Para cada cluster conservado se crea una mascara binaria temporal `cm` y se obtienen contornos con:

```python
cv2.findContours(cm, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
```

La formula real usada para circularidad es:

```text
4 * np.pi * area / perimetro ** 2
```

con:

```text
area = cv2.contourArea(contornos[0])
perimetro = cv2.arcLength(contornos[0], True)
```

Si `perimetro == 0`, el cluster se descarta.

Si la circularidad es menor que:

```text
CIRCULARIDAD_MINIMA = 0.5
```

el cluster se descarta.

Cada cluster valido incrementa `id_mic` y se escribe en:

```text
resultado["micronucleos"]
```

### Salida del microservicio

`app/routers/segmentacion.py` usa el mismo extractor de poligonos para ambas mascaras:

```python
objetos += obtener_poligonos_desde_mascara(resultado["celulas"], "membrana")
objetos += obtener_poligonos_desde_mascara(resultado["micronucleos"], "micronucleo")
```

`obtener_poligonos_desde_mascara()` usa:

```text
np.unique(mascara), excluyendo 0
cv2.findContours(..., cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
cv2.approxPolyDP(contorno, epsilon=1.5, True)
```

Solo agrega objetos si el contorno simplificado tiene al menos 3 puntos.

La salida HTTP final conserva:

```json
{
  "objetos": [
    {
      "id": 1,
      "tipo": "membrana",
      "puntos": [[10, 20], [12, 25], [15, 28]]
    },
    {
      "id": 1,
      "tipo": "micronucleo",
      "puntos": [[40, 50], [42, 51], [43, 53]]
    }
  ]
}
```

### Coincidencia con documentacion

La documentacion `docs/05_blood_microservice_inventory.md` coincide con el codigo en:

- endpoint `POST /api/v1/segmentar`;
- campo multipart `file`;
- uso de `run_in_threadpool`;
- labels de salida `membrana` y `micronucleo`;
- constantes de z-score, DBSCAN y circularidad;
- resize a `224x224`;
- `gamma = 0.8`;
- `CLAHE(clipLimit=4.0, tileGridSize=(8, 8))`;
- `diameter=None`;
- `channels=[0, 0]`;
- `n_jobs=1` en DBSCAN.

La documentacion simplifica el detalle de:

- formula exacta de z-score robusto;
- formula exacta de circularidad;
- uso de `cv2.approxPolyDP(..., epsilon=1.5, True)`;
- filtro `MIN_PIXELES_CLUSTER` antes de DBSCAN;
- filtro `MIN_PUNTOS_CLUSTER` despues de DBSCAN.

No se detecto una discrepancia cientifica entre esa documentacion y el codigo ejecutable revisado.

## Imagen seleccionada para smoke - antecedente superado

No se encontro una imagen confirmada BLOOD dentro del repositorio, `media`, fixtures, scripts, docs o carpetas locales inspeccionadas.

Inventario de imagenes locales revisadas:

```text
Total aproximado: 83
apps/web/Backend/media/muestras/saliva/2026/01: 41
apps/web/Backend/media/muestras/saliva/2026/07: 3
apps/web/Backend/media/muestras/saliva/2026/08: 39
```

Todas las imagenes encontradas estan bajo:

```text
apps/web/Backend/media/muestras/saliva
```

Ademas, la base local reporto:

```text
MuestraSangre.objects.count() = 0
```

Conclusion:

```text
No hay imagen seleccionada para smoke real de sangre.
El smoke E2E BLOOD sigue bloqueado hasta obtener una imagen externa/original confirmada como sangre.
```

Este bloqueo quedo superado posteriormente al proporcionar imagenes externas
confirmadas de sangre fuera del repositorio:

```text
C:\Users\israe\OneDrive - Universidad de Guadalajara\Documents\SICAM\imagenes\Sangre\sangre_01.jpeg
C:\Users\israe\OneDrive - Universidad de Guadalajara\Documents\SICAM\imagenes\Sangre\sangre_02.jpeg
```

Las imagenes fuente no se agregaron a Git.

## Hotfix de timeout BLOOD y smoke E2E real

Fecha:

```text
2026-08-26
```

### Cambio de timeout

Se actualizo unicamente la configuracion de BLOOD:

```text
BLOOD_SERVICE_TIMEOUT=240
```

Archivos afectados:

```text
apps/web/Backend/config/settings.py
apps/web/Backend/.env.example
apps/web/Backend/api/services/segmentation/tests.py
```

El timeout de saliva permanece sin cambios:

```text
SALIVA_SERVICE_TIMEOUT=30
```

### Validacion de configuracion

`settings.SEGMENTATION_SERVICES` reporto:

```text
SALIVA timeout = 30
SANGRE timeout = 240
```

Se agrego una prueba para proteger que los timeouts por componente no se mezclen.

### Imagen `sangre_01.jpeg`

Validacion previa de archivo:

```text
bytes = 66048
shape = (1280, 719, 3)
decode = PASS
```

Evidencia directa FastAPI previa:

```text
POST http://127.0.0.1:8002/api/v1/segmentar
HTTP 200
time_total = 116.174261 s
objetos = 351
labels = membrana:350, micronucleo:1
raw duplicate ids = 1:2
```

E2E por Django:

```text
POST http://127.0.0.1:8000/api/muestras-sangre/2/segmentar/
HTTP 200
time_total = 120.840785 s
ResultadoSegmentacion id = 13
```

Persistencia:

```text
tipo_muestra = SANGRE
estado = COMPLETADO
muestra_sangre_id = 2
respuesta_json objetos = 351
resultado_normalizado.version = 1.1
resultado_normalizado total = 351
counts_by_label = membrana:350, micronucleo:1
ids normalizados unicos = 351
```

Historial:

```text
GET /api/muestras-sangre/2/resultados-segmentacion/
HTTP 200
items = 1
resultado id = 13
```

Resultado efectivo:

```text
GET /api/resultados-segmentacion/13/efectivo/
HTTP 200
fuente = AUTOMATICO
version = 1.1
total_objects = 351
counts_by_label = membrana:350, micronucleo:1
```

### Imagen `sangre_02.jpeg`

Validacion previa de archivo:

```text
bytes = 36476
shape = (1280, 719, 3)
decode = PASS
```

Evidencia directa FastAPI:

```text
POST http://127.0.0.1:8002/api/v1/segmentar
HTTP 200
time_total = 123.069527 s
objetos = 282
labels = membrana:280, micronucleo:2
raw duplicate ids = 2:2, 3:2
labels invalidos = 0
```

E2E por Django:

```text
POST http://127.0.0.1:8000/api/muestras-sangre/3/segmentar/
HTTP 200
time_total = 120.761650 s
ResultadoSegmentacion id = 14
```

Persistencia:

```text
tipo_muestra = SANGRE
estado = COMPLETADO
muestra_sangre_id = 3
respuesta_json objetos = 282
resultado_normalizado.version = 1.1
resultado_normalizado total = 282
counts_by_label = membrana:280, micronucleo:2
ids normalizados unicos = 282
```

Historial:

```text
GET /api/muestras-sangre/3/resultados-segmentacion/
HTTP 200
items = 1
resultado id = 14
```

Resultado efectivo:

```text
GET /api/resultados-segmentacion/14/efectivo/
HTTP 200
fuente = AUTOMATICO
version = 1.1
total_objects = 282
counts_by_label = membrana:280, micronucleo:2
```

### Limpieza posterior

Se eliminaron los datos temporales creados para el smoke:

```text
ResultadoSegmentacion eliminados = 13, 14
MuestraSangre eliminadas = 2, 3
media eliminada =
  media/muestras/sangre/2026/08/smoke16b_timeout_sangre_01.jpeg
  media/muestras/sangre/2026/08/smoke16b_timeout_sangre_02.jpeg
```

No se eliminaron:

```text
imagenes fuente externas
C:\Users\israe\.cellpose\models\cpsam
C:\Users\israe\.cellpose\models\tmp_lt6aj_u
```

### Deuda tecnica

Evaluar ejecucion asincrona de segmentacion BLOOD debido al tiempo de inferencia
CPU observado. Los tiempos reales medidos quedaron cerca de `120` segundos por
imagen, por lo que una ejecucion sincrona HTTP es funcional con timeout ampliado,
pero no es ideal para una experiencia de usuario robusta.

## Errores controlados

Se manejan:

- timeout -> HTTP 504;
- conexion rechazada -> HTTP 503;
- HTTP/servicio invalido -> HTTP 502;
- JSON invalido -> HTTP 502 desde el cliente;
- label inesperado -> HTTP 502;
- geometria invalida -> HTTP 502;
- error inesperado -> HTTP 500.

No se expone traceback.

## Historial

`GET /api/muestras-sangre/{id}/resultados-segmentacion/` devuelve los `ResultadoSegmentacion` asociados a la muestra de sangre ordenados por fecha descendente, equivalente al endpoint de saliva.

## Revisiones

No se agregaron endpoints especificos de sangre.

Se reutilizan:

```http
GET/POST /api/resultados-segmentacion/{id}/revisiones/
PATCH /api/revisiones-segmentacion/{id}/
POST /api/revisiones-segmentacion/{id}/validar/
```

La validacion de labels usa `resultado_segmentacion.tipo_muestra`.

## Effective

No se creo resolvedor separado.

Se reutiliza:

```http
GET /api/resultados-segmentacion/{id}/efectivo/
```

Funciona con `ResultadoSegmentacion` de sangre automatico y con revision `VALIDADA`.

## Resumen del caso

No se modifico `GET /api/casos/{id}/resumen-segmentacion/`.

Ese resumen sigue orientado a `MuestraSaliva` porque la semantica multimodal de caso todavia no esta definida. Se deja para Sprint 16C/17.

## Tests

Se agrego cobertura para:

- endpoint blood success;
- request hacia `segment_image(SANGRE, ...)`;
- persistencia `ResultadoSegmentacion` con `muestra_sangre`;
- raw JSON exacto;
- normalizacion 1.1;
- raw IDs duplicados y IDs editoriales unicos;
- timeout con resultado `ERROR`;
- label invalido `nucleo`;
- geometria invalida;
- historial blood;
- effective automatico blood;
- effective validado blood;
- crear, guardar y validar revision blood;
- cliente `BloodSegmentationClient` con URL, multipart field `file`, timeout, conexion, HTTP error y JSON invalido;
- factory `SANGRE -> BloodSegmentationClient`;
- tipo invalido sin fallback a saliva.

## No modificado

- No se modifico frontend.
- No se modificaron microservicios.
- No se modificaron algoritmos, Cellpose, thresholds ni postprocessing.
- No se crearon migraciones nuevas en Sprint 16B.

## Pendiente para Sprint 16C

- UI para subir/seleccionar `MuestraSangre`;
- galeria o filtro por tipo de muestra;
- accion frontend para ejecutar segmentacion blood;
- visualizacion de historial blood;
- integracion de resumen multimodal de caso si se define la semantica;
- definir si BLOOD debe ejecutarse de forma asincrona por cola/job antes de uso operativo.
