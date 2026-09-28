# Sprint 18D — Caracterización SALIVA 2.1

## Alcance y baseline

Validación realizada en WSL, entorno `sicam`, el 2026-09-28. Rama `master`,
HEAD inicial `47d567f57290b073246aceadbaea0a023e656df4`; working tree inicialmente
limpio. No staging, commit ni push.

SALIVA agrega `eccentricity`, `std_gray_intensity` y `metrics.texture` para
membranas, núcleos y micronúcleos. `algorithm_version`, `version` y
`schema_version` de nuevas caracterizaciones SALIVA son `2.1`.
BLOOD conserva exactamente counts-only `1.0`, incluido su JSON existente
(`version`, sin introducirle un campo `schema_version`).

Un objeto **membrana** representa la **región celular delimitada por la
membrana**, no el espesor físico de una línea ni una banda de borde. Todas sus
métricas raster se calculan sobre esa región completa. No se crean métricas de
edge. Las unidades existentes siguen siendo px y px²; no hay calibración física.

No se modifican microservicios, segmentación, thresholds, asociaciones,
requisitos, modelos, migraciones ni fórmulas 2.0. La presentación de las nuevas
métricas queda para 18E.

## Auditoría previa a implementación

Localizaciones (rutas relativas a `apps/web/Backend`):

| Responsabilidad | Implementación auditada |
| --- | --- |
| Snapshot persistido | `api/models.py`: `ResultadoCaracterizacion` |
| Resolución efectiva | `api/services/segmentation/effective.py` |
| Idempotencia, persistencia, vigencia | `api/services/characterization/service.py` |
| Versiones | `api/services/characterization/types.py`, `saliva.py` |
| Geometría y asociaciones | `geometry.py`, `saliva.py` |
| Fotometría original | `intensity.py` |
| API de lectura/escritura | `api/views.py`, `api/serializers.py` |
| Regresiones previas | `api/tests.py`, `api/test_saliva_strategies.py` |
| Renderer | Frontend: `CharacterizationResultPanel.vue`, `characterizationPresentation.js` |

El orden real es:

1. Bloquear el resultado padre dentro de una transacción y resolver el resultado
   efectivo: última revisión VALIDADA por número; si no existe, AUTOMATICO.
   BORRADOR no participa.
2. Buscar snapshot por padre + revisión efectiva + fuente + versión de algoritmo.
3. Copiar el payload efectivo; abrir la imagen original con Pillow `convert('L')`.
4. Medir **antes de asociar**: perímetro, autointersección, área, centroide
   geométrico, circularidad, fotometría; 2.1 añade momentos raster y GLCM aquí.
5. Asociar núcleos/MN a membranas usando el centroide geométrico. Un único
   contenedor asocia; ninguno deja huérfano; varios producen ambigüedad. El borde
   cuenta y mantiene `POINT_ON_BOUNDARY`.
6. Construir células, elegir núcleo del MN dentro de su célula, calcular
   distancias y ratios; después construir resumen, índices y calidad de asociación.
7. Crear y validar un nuevo `ResultadoCaracterizacion`, o devolver el snapshot
   existente sin recalcularlo si coincide la clave lógica.

En 2.0 la intensidad dibujaba un polígono Pillow con `outline=1, fill=1` en una
máscara del tamaño completo de la imagen y recorría todos sus píxeles. La media
era `sum(gray8) / N / 255`. La inclusión del borde raster se conserva.

Autointersección conserva sólo el perímetro si pudo calcularse: retorna antes de
área, centroide, circularidad y fotometría, y no permite asociación espacial.
Menos de tres puntos o coordenadas inválidas producen `INVALID_POINTS`; área
cero produce `DEGENERATE_POLYGON` (si la geometría no fue rechazada antes por
autointersección). Estas decisiones permanecen intactas.

## Máscara compartida y escala

`raster.py` construye una sola máscara local por objeto válido. Convierte los
vértices a enteros en coordenadas originales siguiendo el truncamiento de Pillow
antes de trasladar al bounding box; esto conserva también polígonos fraccionales.
La imagen gris se recorta una sola vez. La máscara y los bytes grises se reutilizan
para media, desviación estándar, excentricidad y textura.

Sólo se incluyen píxeles rasterizados del polígono, incluido su borde como en
2.0. Nunca se rellena el bounding box como objeto ni se usan ceros exteriores
como muestras. La fuente fotométrica es la imagen **original**, convertida a `L`,
no la imagen segmentada. Escala `I = gray8 / 255.0`.

La media mantiene exactamente su aritmética anterior usando un histograma de
256 valores: suma entera de intensidades / cantidad / 255. No se modifica
`centroid_px`: sigue siendo el centroide geométrico del polígono.

## Excentricidad

En los N píxeles de la máscara, calcular media de coordenadas `(x̄,ȳ)` y momentos
poblacionales `mu20=mean((x-x̄)²)`, `mu02=mean((y-ȳ)²)`,
`mu11=mean((x-x̄)(y-ȳ))`. Las coordenadas locales equivalen a las originales para
estos momentos centrales y evitan acumular grandes traslaciones.

Para la matriz `[[mu20,mu11],[mu11,mu02]]`:

- `delta = hypot(mu20-mu02, 2*mu11)`;
- `lambda_max = (mu20+mu02+delta)/2`;
- `lambda_min = (mu20+mu02-delta)/2`;
- `eccentricity = sqrt(1-lambda_min/lambda_max)`.

Se protegen valores negativos por redondeo y el rango [0,1]. Si N<2,
`lambda_max <= 1e-12`, geometría inválida o coordenadas incompatibles con la imagen,
el valor es `null` con `ECCENTRICITY_NOT_COMPUTABLE`, una vez por objeto.
Un raster lineal con dispersión y polígono geométricamente válido puede tener
excentricidad 1; un polígono de área cero conserva la degradación geométrica 2.0.
El centro de masa raster no reemplaza el centroide geométrico.

## Desviación estándar

`std_gray_intensity = sqrt(sum((I-mean(I))²)/N)`, **poblacional, ddof=0**,
sobre exactamente los mismos píxeles normalizados que la media. El histograma
permite sumar por intensidad sin volver a extraer los píxeles.

Una región constante da cero. Sin píxeles o sin imagen, da `null`; no se impone
un clamp artificial a 0.5. Sólo se protege la raíz contra redondeo negativo.

## Textura GLCM

`raster_metrics.py` define `TEXTURE_GRAY_LEVELS=32`.
Cuantización `q=floor(gray8*32/256)`: 0→0, 7→0, 8→1, 255→31.
Distancia 1 px; offsets `(dx,dy)` en coordenadas de imagen:

| Ángulo | Offset |
| --- | --- |
| 0° | (1,0) |
| 45° | (1,-1) |
| 90° | (0,-1) |
| 135° | (-1,-1) |

Por orientación, sólo cuentan pares cuyos **dos** píxeles pertenecen a la máscara
y están dentro de la imagen. Cada par (i,j) incrementa C[i,j] y C[j,i], incluso
si i=j. Cada matriz 32×32 con pares se normaliza independientemente a suma 1.

Para P normalizada:

| Feature | Fórmula |
| --- | --- |
| contrast | Σ P(i,j)(i-j)² |
| homogeneity | Σ P(i,j)/(1+(i-j)²) |
| energy | sqrt(Σ P(i,j)²) |
| entropy | -Σ P(i,j)log₂P(i,j), sólo P>0 |
| correlation | Σ P(i,j)(i-μi)(j-μj)/(σiσj), marginales de P |

Si `σiσj <= 1e-12`, la correlación de ese ángulo es indefinida (`null`), nunca
se inventa cero. Cada feature se promedia **sin ponderar** por cantidad de pares
entre ángulos donde esa feature es computable. Un ángulo sin pares no participa;
un ángulo con correlación indefinida puede aportar las otras cuatro features.

Contrato por objeto:

```json
{"metrics":{"texture":{
  "contrast":null,"homogeneity":null,"energy":null,
  "correlation":null,"entropy":null,"valid_angles":0,"valid_pairs":0
}}}
```

`valid_angles` cuenta orientaciones con al menos un par.
`valid_pairs` suma pares originales en las cuatro orientaciones **antes** de la
duplicación simétrica. No existe un mínimo arbitrario adicional de píxeles.
Sin pares: features `null`, contadores 0, `TEXTURE_INSUFFICIENT_PAIRS`.
Con pares pero ninguna correlación computable: `TEXTURE_CORRELATION_UNDEFINED`;
las otras features siguen disponibles.

2.0 no tenía bloque metodológico. Se agrega una sola vez por resultado:

```json
{"methodology":{"texture":{
  "method":"GLCM","gray_levels":32,"distance_px":1,
  "angles_deg":[0,45,90,135],"symmetric":true,"normalized":true,
  "aggregation":"mean_over_valid_angles"
}}}
```

## Degradaciones y advertencias

- Polígono inválido, auto-intersectado o de área cero: métricas nuevas `null`,
  textura vacía con contadores cero; se conserva el warning geométrico existente
  y se añade el de excentricidad. No se intenta fotometría ni GLCM.
- Imagen ausente: un `IMAGE_UNAVAILABLE` global; media/std/textura no disponibles.
  La excentricidad puede calcularse con la máscara geométrica sin intensidad.
- Coordenadas fuera de imagen: `COORDINATE_SPACE_MISMATCH`, métricas raster
  `null`; se conservan geometría y asociaciones existentes sin recortar
  silenciosamente el objeto para atribuirle medidas parciales.
- Máscara vacía: media/std/excentricidad `null`, textura sin pares y warnings
  correspondientes. Un solo píxel tiene media, std=0, excentricidad `null` y sin
  pares GLCM. No se sustituye ninguna indefinición por NaN o Infinity.
- Los warnings mantienen `{code, object_id, message}`. No se duplican avisos de
  falta de imagen o geometría para cada feature fotométrica.

## Distance metrics — current contract and open extensions

`micronucleus.metrics.distance_to_nucleus_px` es la distancia euclidiana entre
**centroides geométricos** del MN y su núcleo asociado, en px. Se elige el núcleo
más cercano entre los asociados a la misma membrana; empate: menor ID. No se
buscan núcleos en otras células. Sin núcleo asociado, distancia y ratios relativos
son `null`. Esto incluye MN huérfanos/ambiguos y células sin núcleo.

Se conservan `area_fraction_to_nucleus`, `intensity_fraction_to_nucleus`, los
índices genotóxico/citotóxico y `association_quality` sin cambios.

Extensiones abiertas, **no implementadas**, que requieren contrato científico:

- núcleo → centroide celular;
- MN → centroide celular;
- MN → borde celular;
- distancias entre núcleos de células multinucleadas;
- distancias entre micronúcleos.

No hay campo genérico `distance_between_objects` ni matrices all-to-all.

## Versionado, históricos, estrategias y frontend

El modelo tiene un CheckConstraint de coherencia fuente/revisión, sin unicidad
que obligue a sobrescribir 2.0. La idempotencia del servicio ya incorpora
`algorithm_version` y bloquea el padre. No se requieren cambios de modelo ni
migraciones: mismo padre/revisión puede conservar 2.0 y crear un snapshot 2.1.

No hay backfill ni actualizaciones de JSON históricos. Lectura y serializer
siguen entregando 2.0 intacto. Como antes, `vigente` se calcula según versión
actual y resultado efectivo: 2.0 pasa a no vigente sin escribir su fila. La API
POST devuelve 201 para snapshot nuevo y 200 para reutilización; GET lista ambos.
No se afirma inmutabilidad absoluta del modelo frente a escrituras externas:
se conserva la política existente del servicio y endpoints.

Caracterización recibe imagen + resultado efectivo. No se agregan ramas por
`segmentation_strategy`; mismo payload y misma imagen CURRENT/ALT producen el
mismo resultado científico. BLOOD conserva su servicio y contrato counts-only.

El frontend tenía comprobación exacta `schema_version === '2.0'`. El único cambio
productivo frontend permite `2.0` y `2.1` en `isSalivaMorphometricV2`, conservando
el renderer, rutas, selección y contratos previos. SALIVA v1 y BLOOD v1 continúan
con su renderer de conteos. No se muestran todavía las features nuevas ni se
calculan métricas en el cliente. No se agrega un explorador de históricos: se
conserva la selección/vigencia previa y se comprueba que el renderer puede leer
un snapshot 2.0 cuando se le proporciona.

## Pruebas y validaciones

`api/test_characterization_2_1.py` cubre círculo raster simétrico, rectángulo con
excentricidad analítica, traslación, geometrías inválidas, máscara vacía, un píxel,
máscara dispersa; std constante, dos niveles y ddof=0; GLCM constante,
checkerboard con valores analíticos, cuatro ángulos, promedio no ponderado,
correlación parcial/indefinida, cuantización y conteo antes de simetría.

El test obligatorio de contaminación usa un triángulo idéntico sobre dos fondos
0/255, incluidos píxeles exteriores **dentro** de su bounding box: media, std y
textura son idénticas. Otro test contrasta máscara recortada contra Pillow de
imagen completa para polígonos enteros, fraccionales y cóncavos.

La fixture sintética versionada `api/test_data/characterization_saliva_2_0.json`
fue generada con `saliva.py` del HEAD inicial, no contiene datos clínicos ni es un
artefacto del smoke. La regresión crea una fila 2.0, solicita 2.1 dos veces,
comprueba 201→200, IDs distintos para 2.0/2.1, JSON histórico idéntico, versión,
serializer y listado. Frontend usa esa misma fixture para comparar renderizado.

Las expectativas de versión actual en tests previos se actualizan a 2.1; las
pruebas que simulaban una versión futura usan `future-test-version`. Ninguna
aserción científica previa se elimina. Regresiones de AUTO, VALIDADA, BORRADOR,
stale, idempotencia, asociaciones, índices, media y BLOOD siguen pasando.

Desde `apps/web/Backend`, con `/home/israel/miniconda3/envs/sicam/bin/python`:

| Comando | Resultado |
| --- | --- |
| `python manage.py check` | System check identified no issues (0 silenced). |
| `python manage.py makemigrations --check` | No changes detected |
| `python -m pytest -q` | 198 passed, 2 skipped in 3.55s |
| `python manage.py test` | 173 tests, OK, 2.344s; base de test destruida |

Las dos omisiones pytest ya existían: requieren servicios reales activos.
Durante desarrollo se corrigió una fixture Pillow que usaba listas donde esa
versión requiere tuplas, y dos expectativas antiguas de versión en tests de
estrategias. Las ejecuciones finales anteriores están en verde.

Desde `apps/web/Frontend`:

- `node tests/segmentationStrategies.test.mjs`: 21 passed, 0 failed.
- `node --test tests/segmentationStrategies.test.mjs`: archivo completo PASS
  (ese modo de aislamiento resume un archivo, no los 21 casos internos).
- `npm run build`: PASS, Vite 7.3.0, 101 módulos, 1.94s.

## Smokes y rendimiento

Artefactos exclusivamente en `/tmp/sicam18d/`; script reproducible de esta sesión
`/tmp/sicam18d_smoke.py`. Se llama al servicio Django
`characterize_effective_segmentation`, sin persistir ni ejecutar segmentación.

| Caso | Dimensiones | Objetos | Duración | Métricas nuevas calculables |
| --- | --- | --- | --- | --- |
| Sintético, patrón `(3*x+5*y)%256` | 256×256 | 1 membrana + 1 núcleo + 1 MN | 0.118065 s | 3/3 |
| Real, imagen de prueba autorizada | 4928×4928 RGB | 3 membranas + 3 núcleos + 1 MN | 6.875906 s | 7/7 |

La segmentación ALT persistida reutilizada corresponde byte a byte a la imagen
autorizada (SHA-256 `03719a2eef66f1b6497bac0d577a733aa0b0d4688f4fa21e5baf73488f177d7e`).
No se incluyen nombres clínicos ni rutas de medios personales en esta documentación.
No se volvió a ejecutar Cellpose ni se compararon imágenes diferentes.

En ambos casos: schema 2.1, todos los objetos contienen los tres campos nuevos,
serialización `allow_nan=False` correcta, sin warnings. Todos los campos 2.0
comunes coinciden exactamente contra la implementación previa (se excluyen sólo
campos aditivos, versiones y warnings nuevos). Esa comparación del smoke usa
la media recortada; la equivalencia con la media de máscara completa se comprueba
independientemente en los tests numéricos.

Archivos temporales: `synthetic.png`, `synthetic-result.json`, `real-result.json`,
`summary.json`. Hashes de la base SQLite local y de la imagen original iguales
antes/después. Ningún resultado del smoke se persiste. No se arrancan servicios.

El costo por objeto depende del bounding box y cuatro recorridos de pares, con
matrices constantes 32×32. Sólo se convierte la imagen completa a gris una vez;
no se crea una máscara completa ni se recorre toda la imagen para cada objeto.
Los tiempos son observaciones de esta instalación, no un SLA ni una evaluación
de calidad científica, precisión, sensibilidad o superioridad de estrategia.

## Cierre

`git diff --check`: PASS. Diffs de los tres microservicios vacíos.
No cambios en modelos, migraciones, requirements ni lockfiles. Working tree
contiene únicamente código/pruebas de caracterización, el ajuste mínimo frontend
y este documento; sin staging. Sin imágenes, pesos, JSON reales ni artefactos
temporales añadidos a Git. Los documentos históricos no se reescriben.

SYNTHETIC_SMOKE = PASS

REAL_GEOMETRY_SMOKE = PASS

SPRINT 18D = PASS
