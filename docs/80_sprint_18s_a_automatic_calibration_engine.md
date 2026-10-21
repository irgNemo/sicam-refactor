# Sprint 18S-A — Motor automático de calibración microscópica

Estado: **READY_FOR_SCIENTIFIC_REVIEW**. Estimación provisional; **no es una
calibración científicamente validada de SICAM**. La aceptación científica y sus
umbrales corresponden a 18S-A.1.

## Alcance y estado de partida

HEAD: `21008c36abdc425f471e7ef1e54bcb2d2aadf292`, rama `master`.
Estado inicial: sólo `?? data/`, que contenía los tres originales de calibración y
sus archivos `Zone.Identifier`. Se añadió `/data/calibration/` a `.gitignore`.
No se agregaron imágenes, overlays, resultados reales ni pesos al control de versiones.

Motor Python aislado en `apps/web/Backend/api/services/calibration/`. No importa
Django ni modelos, no abre la BD, no implementa endpoints y no modifica Registro,
Segmentación, Characterization 2.1, frontend ni unidades de resultados existentes.
No hay migraciones, instalaciones ni cambios de requirements.

Dependencias existentes utilizadas: NumPy 2.2.6, OpenCV
(`opencv-python-headless==5.0.0.93`, runtime `cv2` 5.0.0), Pillow 10.2.0.
No se necesitan SciPy, scikit-image ni matplotlib.

## Originales y contrato físico explícito

Ubicación local: `data/calibration/`. Todos son **JPEG RGB, tres canales,
4928 × 4928 px**, metadata JFIF 72 × 72 dpi. Estos dpi son informativos y **no
participan en ninguna fórmula**. No hay transformación EXIF ni resize en lectura.

Configuración declarada: microscopio OPTIKA B-1000FLHBO; cámara OPTIKA C-B25+;
adaptador M-114; objetivo 40×. No se infiere la dimensión física del nombre:
`manifest.example.json` declara `pattern_type`, `division_um` o
`known_diameter_um`, `objective_magnification`, `expected_dimensions_px` y
`acquisition`. Las rutas relativas se resuelven respecto al manifest.

| Archivo | Dimensión física suministrada | Bytes | SHA-256 |
|---|---:|---:|---|
| `Cal_DIV0.01mm_40x.jpg` | división de referencia 10 µm; familia por confirmar | 12700768 | `262835496b50f13d1dadcb934c2dda765b1f2055848b0b02d6ffffa446ac1d33` |
| `Cal_0.15mm_40x (1).jpg` | diámetro de disco 150 µm | 11964805 | `d9daee7d4bc1790c004110d2febda32c7874a837c7298a85c1c739a3fb96c58b` |
| `Cal_0.07mm_40x (1).jpg` | diámetro de disco 70 µm | 12175912 | `a3665c451b17ec42eb4713c5894ce66ca357305c39c67c6dd36e767f00ef3998` |

Los hashes posteriores coinciden con el inventario anterior al procesamiento.
La inspección de los dos patrones circulares muestra un disco oscuro principal
por archivo, compatible visualmente con el tipo declarado. Esto no sustituye la
certificación del diámetro físico del patrón.

## Arquitectura y reproducibilidad

- `common.py`: normalización de iluminación, geometría float64 y fórmulas comunes.
- `grid.py`: segmentos, rotación, centros de marcas, periodicidades y ajuste robusto.
- `circle.py`: un único detector/refinador para ambos tamaños de disco.
- `engine.py`: contrato explícito, hash de los mismos bytes decodificados,
  validación de dimensiones, resultados y consenso provisional.
- `diagnostics.py`: overlays en coordenadas originales; sólo su presentación final
  se reduce a un máximo de 1400 px.
- `cli.py`: runner sin configuración Django, JSON y reporte legible.
- `api/test_calibration.py`: fixtures sintéticas generadas en memoria/temporales.

Comando desde un entorno `sicam` ya instalado:

```bash
cd ~/repos/sicam-refactor/apps/web/Backend
conda activate sicam
python -m api.services.calibration.cli \
  --manifest api/services/calibration/manifest.example.json \
  --output /tmp/sicam18sa_calibration
```

Las dimensiones esperadas por defecto son 4928 × 4928; otros tamaños deben
especificarse explícitamente (como en tests). Un mismatch produce
`SOURCE_DIMENSION_MISMATCH`, sin medición, resize ni consenso. Archivo ausente:
`REAL_CALIBRATION_FILES_MISSING`; bytes no decodificables: `INVALID_SOURCE_IMAGE`.
Dimensiones físicas ausentes, no positivas o no finitas se rechazan antes de medir.

El runner rechaza rutas fuente duplicadas y un directorio de salida que contenga
los originales. No realiza operaciones aleatorias; los tests con ruido fijan seed.
Dos ejecuciones completas sobre los originales produjeron resultados numéricos
idénticos, incluyendo métricas/contornos; sólo difieren las rutas de diagnóstico.

## Método GRID

1. Grayscale de los píxeles originales. Plano de iluminación robusto mediante
   percentiles altos por tiles, normalización fotométrica y suavizado sigma 1 px.
   Los tiles estiman iluminación; no son una imagen reducida de medición.
2. Otsu para estructuras oscuras. LSD a `scale=1.0`, evitando su reducción interna
   por defecto. Segmentos con longitud mínima `max(10, 0.02*min(width,height))`.
3. Mediana ponderada de orientaciones cercanas a horizontal/vertical, dentro de
   ±15°. Rotación rígida a escala unidad, canvas ampliado para no recortar. No hay
   resize; la matriz afín queda registrada para regresar a coordenadas originales.
4. Proyecciones por eje; eliminación del pedestal de líneas ortogonales, centros
   ponderados de cada banda y posibles familias por amplitud de marca.
5. Modos de separaciones vecinas como periodicidades candidatas. Búsqueda
   determinista de fase, índices enteros conservando huecos y ajuste
   `p_i = a + b*i`. Se registran centros usados/rechazados, índices faltantes,
   pitch, RMS residual, R² y soporte de separaciones adyacentes.
6. **La periodicidad geométrica no identifica por sí sola los 10 µm.** Sólo un
   patrón declarado explícitamente `grid_reference="uniform_lattice"` permite
   elegir un pitch mediante soporte adyacente dominante. Empates permanecen
   ambiguos. Esta declaración se usa en sintéticos y **no** en el patrón real.

Las primitivas y el parámetro de escala de LSD se describen en la
[documentación oficial de OpenCV](https://docs.opencv.org/4.x/dd/d1a/group__imgproc__feature.html).
No se usa la escala de ningún círculo para decidir una familia GRID.

Para un grid alineado: `sx = division_um / pitch_x_px`,
`sy = division_um / pitch_y_px`. Para un grid ligeramente rotado, el motor utiliza
un modelo diagonal sin shear para expresar escalas en ejes del sensor:

```text
[c² s²] [1/sx²] = [(pitch_x/division_um)²]
[s² c²] [1/sy²]   [(pitch_y/division_um)²]
```

`c=cos(angle)`, `s=sin(angle)`. No es un modelo afín general: una deformación
anisótropa fuerte combinada con rotación puede dejar familias no ortogonales y
sesgar proyecciones. El warning `GRID_DIAGONAL_SCALE_MODEL_NO_SHEAR` explicita esa
limitación. No se corrige distorsión óptica.

### Resultado real GRID

Estado: **AMBIGUOUS_GRID_PERIODICITY**. Ninguna familia seleccionada;
`sx = sy = null`; excluido del consenso y de comparaciones físicas.
Rotación: **−0.297855446683°**. Centros detectados: **12 X, 11 Y**.
Los centros y los índices completos permanecen en JSON. Las candidatas pueden
compartir marcas; no son conjuntos independientes de observaciones.

| Eje | Pitch candidato px | Marcas usadas | Rechazadas respecto a esa candidata | RMS px | R² | Soporte adyacente |
|---|---:|---:|---:|---:|---:|---:|
| X | 182.557727463054 | 12 | 0 | 5.327773449206 | 0.999992124000 | 7 |
| X | 914.466261000508 | 5 | 7 | 0.865177887967 | 0.999999552446 | 4 |
| Y | 182.945854060990 | 11 | 0 | 1.700779351931 | 0.999999010625 | 6 |
| Y | 915.250412004268 | 6 | 5 | 1.437449900640 | 0.999999154296 | 4 |

Las marcas exteriores próximas al borde pueden sesgar centros de proyección;
estas candidatas son diagnósticas, no una calibración aceptada. Tampoco un R² alto
certifica la asignación física. Hace falta identificar la familia mediante la
especificación del portaobjetos u otra evidencia independiente.

## Método CIRCLE

Mismo código y parámetros para 70 y 150 µm:

1. Normalización del fondo, Otsu y contornos externos originales sin aproximación.
2. Candidatos de disco relleno: área mínima `max(50, 0.0005*W*H)`, al menos seis
   puntos, solidez ≥0.8, circularidad ≥0.45, fracción oscura interior ≥0.85.
   No hay posición central obligatoria. Si el segundo candidato tiene al menos
   la mitad del área del primero: `AMBIGUOUS_REFERENCE_OBJECT`.
3. Contorno a ≤4 px del borde: `CLIPPED_REFERENCE_OBJECT`, sin extrapolación.
4. Ajuste elíptico inicial en float64. Refinamiento sobre 1440 perfiles radiales,
   muestreo 0.25 px del raster original normalizado, máximo de gradiente y
   interpolación parabólica. Ventana de búsqueda `max(6 px, 0.02*radio mayor)`.
5. Ajuste elíptico algebraico restringido, coordenadas centradas/escaladas,
   cinco iteraciones de rechazo robusto MAD (4.5 MAD, piso 0.75 px).
   Al menos 30 bordes válidos y cobertura de los 36 sectores angulares.
6. Ajuste circular independiente sobre los mismos inliers. Se informa RMS radial
   circular y RMS elíptico aproximado mediante residuo implícito/gradiente.
   Este último no es una distancia ortogonal exacta a la elipse.

OpenCV proporciona la extracción de contornos usada aquí; los ajustes float64
se implementan en NumPy. Referencia de primitivas:
[OpenCV, análisis de formas](https://docs.opencv.org/4.x/d3/dc0/group__imgproc__shape.html).

Los controles anteriores son criterios técnicos de detección/estabilidad, **no
umbrales de aceptación científica de calibración**. No contienen rangos esperados
de µm/px ni se ajustaron contra estimaciones previas. Se probaron primero con
fixtures sintéticas y luego se aplicaron sin tuning de escala a los originales.

`diameter_x_px` / `diameter_y_px` son las extensiones de la elipse ajustada en ejes
X/Y del raster; no el bounding box binario ni los ejes mayor/menor. La escala usa:

```text
sx = D_um / diameter_x_px
sy = D_um / diameter_y_px
mean_scale = (sx + sy)/2
anisotropy_percent = 100*abs(sx-sy)/mean_scale
```

`equivalent_circle_diameter_px` corresponde al ajuste circular independiente;
`area_equivalent_diameter_px` es el diámetro de igual área de la elipse.
`axis_ratio = major/minor`; `circularity_deviation = 1 - 4*pi*area/perimeter²`
es diagnóstico del contorno binario grueso, sensible a rasterización/ruido.
El ángulo informado para círculos es el del eje mayor elíptico, no una rotación
independiente de la cámara; es inestable para círculos casi perfectos.

### Resultados reales de los círculos

| Métrica | CIRCLE_150 | CIRCLE_70 |
|---|---:|---:|
| Centro X px | 2539.932952404383 | 2708.258983885843 |
| Centro Y px | 2326.686565698055 | 1949.351641270880 |
| Diámetro X px | 2758.220101074683 | 1248.106200050754 |
| Diámetro Y px | 2764.409131637470 | 1255.403199423137 |
| Diámetro circular ajustado px | 2761.333292180061 | 1251.735649388431 |
| Eje mayor elipse px | 2765.394103868909 | 1257.279836944804 |
| Eje menor elipse px | 2757.232566059696 | 1246.215748311274 |
| Ángulo elipse ° | 69.658029124271 | 65.631816546871 |
| Major/minor | 1.002960046936 | 1.008878148626 |
| RMS elíptico aproximado px | 3.249741554797 | 3.228209343113 |
| RMS circular px | 3.557028727602 | 3.776012718941 |
| Bordes válidos / inliers | 1440 / 1431 | 1440 / 1440 |
| Fracción inliers | 0.99375 | 1.0 |
| Desviación circularidad binaria | 0.104216242635 | 0.104547987235 |

## Escalas y comparación física

| Fuente | sx µm/px | sy µm/px | Media µm/px | Anisotropía % | Métrica ajuste | Estado |
|---|---:|---:|---:|---:|---|---|
| GRID | — | — | — | — | Candidatas arriba; ninguna asignada | AMBIGUOUS_GRID_PERIODICITY |
| CIRCLE_150 | 0.054382897123 | 0.054261143289 | 0.054322020206 | 0.224133480703 | RMS elipse 3.249741554797 px | MEASURED |
| CIRCLE_70 | 0.056084970972 | 0.055758978496 | 0.055921974734 | 0.582941639757 | RMS elipse 3.228209343113 px | MEASURED |

Diferencia porcentual simétrica: `100*abs(a-b)/((a+b)/2)`.

| Comparación | Diferencia X % | Diferencia Y % |
|---|---:|---:|
| GRID vs CIRCLE_150 | N/A: familia física no identificada | N/A |
| GRID vs CIRCLE_70 | N/A: familia física no identificada | N/A |
| CIRCLE_150 vs CIRCLE_70 | 3.081572729246 | 2.722838664037 |

No se oculta ni se clasifica científicamente esta discrepancia. `MEASURED`
significa medición técnica disponible, no exactitud física demostrada.

## Consenso provisional, sin ponderaciones

Sólo dos métodos medidos, ambos circulares y con el mismo algoritmo. No son
réplicas independientes para estimar toda la incertidumbre del sistema.
Desviación estándar **muestral (ddof=1)**, MAD sin factor de escala.
Con menos de dos métodos no se publica escala combinada. Configuraciones,
resoluciones u objetivos distintos bloquean el consenso (`INCOMPATIBLE_ACQUISITION`).

| Estadístico | X µm/px (salvo %) | Y µm/px (salvo %) |
|---|---:|---:|
| Media | 0.055233934048 | 0.055010060892 |
| Mediana | 0.055233934048 | 0.055010060892 |
| Desviación estándar muestral | 0.001203547961 | 0.001059129432 |
| CV % | 2.179000973569 | 1.925337683417 |
| MAD | 0.000851036924 | 0.000748917604 |
| Mínimo | 0.054382897123 | 0.054261143289 |
| Máximo | 0.056084970972 | 0.055758978496 |
| Diferencia porcentual máxima | 3.081572729246 | 2.722838664037 |

`provisional_median_scale_x = 0.05523393404769274`

`provisional_median_scale_y = 0.05501006089210586`

Estado **PROVISIONAL_ONLY**. No hay ponderación por patrón, corrección óptica ni
PASS/FAIL científico por CV, anisotropía, residuos o R². Los decimales facilitan
reproducción numérica y no representan cifras de exactitud física certificada.

## Diagnósticos y artefactos

En `/tmp/sicam18sa_calibration/`:

- `source_inventory.json`: lectura previa de originales, tamaños, hashes y metadata.
- `results.json`: resultados completos, coordenadas, métricas, warnings, consenso.
- `report.txt`: resumen legible, familias/candidatas y métricas de ambos ajustes.
- `01-diagnostic.png`: GRID; segmentos cian, centros X rojos/Y amarillos.
  Ninguna familia usada físicamente. Rechazos por candidata registrados en JSON;
  en un grid medido, los rechazos seleccionados se muestran en magenta.
- `02-diagnostic.png`, `03-diagnostic.png`: contorno radial cian, elipse roja,
  círculo amarillo, centro rojo, puntos rechazados magenta.
- Logs de ejecución y pruebas; snapshots de integridad antes/después y
  `verification.json` con reproducibilidad y hashes.

La visualización reducida sigue los bordes de los discos; no se usó para medir.
Los JSON conservan coordenadas originales. Ningún diagnóstico está versionado.
Segunda ejecución reproducible en `/tmp/sicam18sa_calibration_repeat/`.

## Validación técnica

`api.test_calibration`: **19 tests**, con múltiples escenarios parametrizados.

| Cobertura | Evidencia |
|---|---|
| GRID alineado, ruido, blur, gradiente, marcas faltantes, outlier y combinación | Recuperación de sx/sy con tolerancia relativa 1%; múltiples marcas, residuo <1 px; outliers rechazados |
| GRID rotación 4° | Error angular <0.3°; pitches dentro de 1%; escalas dentro de 1% en fixture |
| GRID familias desconocidas / periodicidades empatadas | AMBIGUOUS_GRID_PERIODICITY |
| Círculo limpio, ruido, blur, gradiente, desplazado, combinación | Escalas dentro de 1%; residuo <1 px; fracción inliers >0.8 |
| Elipse de radios 110/80 px y elipse rotada 20° | sx/sy distintos, anisotropía recuperada; extensiones X/Y dentro de 1 px |
| Recorte, cercanía al borde, dos discos comparables, imagen uniforme | Fallos técnicos explícitos; sin escala física |
| Dimensiones y no-resize | Mismatch detiene medición; mocks prohíben resize; hashes y dimensiones intactos |
| DPI 72 vs 300 | Misma matriz de píxeles → escalas exactamente iguales |
| Determinismo | Igualdad completa de resultados sintéticos y de las dos ejecuciones reales |
| Contrato/consenso/runner | Valores físicos inválidos, ausentes/corruptos, exclusión, SD muestral, incompatibilidad de adquisición, outputs y protección de fuentes |

Tolerancias sintéticas son pruebas de ingeniería sobre referencias generadas,
no umbrales científicos para estas tres imágenes reales.

Regresión: `python manage.py test api --noinput`: **263 tests OK** (244 existentes
+19 del motor), incluyendo Registro, ImageJ, revisiones, segmentación y
Characterization. BD de tests separada; no ejecución de segmentadores ni
Characterization sobre muestras de trabajo.

`python manage.py check`: sin problemas.

`python manage.py makemigrations --check --dry-run`: **No changes detected**.

La BD de trabajo conserva su hash y los 88 archivos de MEDIA_ROOT conservan sus
hashes. La consulta de integridad read-only confirma `integrity_check=ok` y cero
infracciones de FK. No se ejecutó ninguna migración ni escritura de datos de trabajo.
`git diff --check`: limpio. Sin commit, staging ni push.

## Limitaciones y decisiones para 18S-A.1 / 18S-B

1. Confirmar independientemente qué marcas del portaobjetos representan 10 µm.
   No basta elegir la escala que se parezca a los círculos. El grid real no tiene
   todavía una vía automática de identificación física certificada.
2. Verificar diámetros certificados, tolerancias del patrón, enfoque y repetibilidad
   de adquisición. La apariencia del disco no certifica 70/150 µm.
3. Investigar la diferencia entre círculos (3.081573% X, 2.722839% Y) mediante
   referencias/repeticiones independientes antes de decidir si es aceptable.
4. La anisotropía aparente mezcla sensor, óptica, patrón, segmentación y distorsión;
   el warning `APPARENT_ANISOTROPY_INCLUDES_PATTERN_AND_OPTICS` evita atribuirla
   automáticamente a los píxeles. No hay corrección óptica ni inferencia causal.
5. Los controles técnicos fijos de detección no garantizan generalización a otros
   patrones, baja señal, anillos, grandes rotaciones, shear o fuerte distorsión.
   Blur/JPEG/interpolación y normalización pueden sesgar los bordes. No se estima
   todavía incertidumbre metrológica ni límites de confianza.
6. Definir científicamente criterios de CV, anisotropía, residuos, reproducibilidad
   y política de combinación; no añadir pesos arbitrarios.
7. Para 18S-B, diseñar perfil de adquisición/calibración antes de integrarlo con
   BD/UI. Conversión automática a µm/µm² sólo si coinciden al menos cámara y su
   configuración, objetivo, resolución y condiciones relevantes de adquisición
   (incluyendo binning, crop/resize y adaptador). No basta que dos imágenes tengan
   4928 × 4928. Si no coincide, continuar en px sin conversión física automática.
8. No aplicar estas escalas provisionales a resultados actuales. No se modificó
   Characterization 2.1 ni se añadieron columnas/unidades físicas.

SPRINT 18S-A = READY_FOR_SCIENTIFIC_REVIEW
