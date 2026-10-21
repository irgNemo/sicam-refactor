# Sprint 18S-A.1 — Revisión científica provisional de calibración

**READY_FOR_SCIENTIFIC_DECISION**: evidencia disponible para decisión humana.
**PROVISIONAL_ONLY**: no se declara calibración definitiva ni PASS científico.

## Precheck y baseline

- Rama `master`; HEAD `2d90e0d086efd941446066d2c41ed95755e8cf89`:
  `Add automatic microscopy calibration engine`.
- Working tree inicial limpio; 18S-A ya commiteado.
- Historial anterior: `21008c3`, `2d7e406`, `49fed95`, `c783143`.
- Ejecución original de 18S-A reproducida **exactamente**, antes de editar código.
  Comparación de JSON excluyendo únicamente la ruta del diagnóstico.
- Baseline anterior conservado en `/tmp/sicam18sa_calibration/`.
  Reproducción independiente: `/tmp/sicam18sa1_calibration/baseline/`.
- Tres originales JPEG RGB de **4928 × 4928 px**, presentes e ignorados por Git.
  Los metadatos 72 dpi no intervienen en ningún cálculo.

| Fuente en `data/calibration/` | SHA-256 intacto |
|---|---|
| `Cal_DIV0.01mm_40x.jpg` | `262835496b50f13d1dadcb934c2dda765b1f2055848b0b02d6ffffa446ac1d33` |
| `Cal_0.15mm_40x (1).jpg` | `d9daee7d4bc1790c004110d2febda32c7874a837c7298a85c1c739a3fb96c58b` |
| `Cal_0.07mm_40x (1).jpg` | `a3665c451b17ec42eb4713c5894ce66ca357305c39c67c6dd36e767f00ef3998` |

Configuración declarada: OPTIKA B-1000FLHBO, C-B25+, M-114, objetivo 40×.
No se encontró certificado/tolerancia local del patrón:
**REFERENCE_PATTERN_TOLERANCE = UNKNOWN**.

## Cambios algorítmicos acotados

`review.py` y `review_cli.py` añaden experimentos reproducibles y reportes;
no importan Django ni acceden a modelos/BD. `common.normalized_gray` y
`circle.measure_circle` permiten variar explícitamente suavizado, cantidad de
perfiles y rechazo MAD. Sus defaults conservan exactamente los cálculos de 18S-A.
No se cambió el detector GRID original, el manifest ni sus reglas de consenso.

La interpretación del grid se calcula y se guarda **antes** del análisis de
sensibilidad de los círculos. Ninguna escala circular entra en la identificación.
No hay optimización hacia una escala esperada ni selección de parámetros por imagen.
No se modifican modelos, migraciones, Registro, UI, segmentadores ni Characterization.

## GRID: hipótesis y evidencia espacial

Hipótesis: paso menor = división declarada de 10 µm; paso mayor = cinco divisiones,
50 µm. La coincidencia de escalas con círculos no constituye evidencia para elegirla.

| Eje | Pitch menor baseline px | Pitch mayor baseline px | Cociente | Desviación absoluta de 5 | Desviación de 5 % |
|---|---:|---:|---:|---:|---:|
| X | 182.557727463054 | 914.466261000508 | 5.009189551757 | 0.009189551757 | 0.183791035149 |
| Y | 182.945854060990 | 915.250412004268 | 5.002848611694 | 0.002848611694 | 0.056972233888 |

Se separan marcas por longitud proyectada (familias cortas/largas), se ajusta cada
familia independientemente y se comprueba fase, índices y presencia de cuatro
marcas menores interiores entre dos mayores. Esto evita validar únicamente el
cociente de dos ajustes que reutilizan observaciones.

Los índices empiezan en cero en la primera marca observada; las ausencias conservan
sus huecos. No se generan puntos para medir: las subdivisiones inferidas sólo se
representan en gris en el diagnóstico.

| Evidencia | X | Y |
|---|---:|---:|
| Marcas cortas (n_minor) | 7 | 5 |
| Marcas largas (n_major) | 5 | 6 |
| Índices de las largas | 4,9,14,19,24 | 0,5,10,15,20,25 |
| Separación entre largas, en índices menores | 5 | 5 |
| Grupos de cinco intervalos completamente observados | **0** | **1** |
| RMS de posición de mayores respecto a retícula menor, px | 3.382293846987 | 1.769626358913 |
| Desfase de ajuste de cortas en primera larga, px | −4.773059754174 | −0.639948810176 |
| Pitch de ajuste sólo de cortas, px | 182.487818383281 | 182.817750293855 |
| Pitch de ajuste sólo de largas, px | 914.466261000508 | 915.250412004268 |

**X:** las cortas observadas están a izquierda/derecha del conjunto central. No
aparecen cuatro cortas entre dos largas centrales. Hay concordancia de fase y paso
5:1, pero la estructura interior se extrapola. La primera y última marca son
sensibles al recorte del campo.

**Y:** entre 166.958585944331 y 1079.401704849376 px aparecen realmente cuatro
marcas interiores: 351.605677068250, 531.923804602370, 715.012090207919 y
900.034251025683 px. Es un grupo observado de cinco intervalos. Los siguientes
intervalos mayores no muestran esas cuatro subdivisiones.

### Decisión conservadora, pendiente de revisión del investigador

Este estudio exige al menos un grupo completo observado **por eje**, además de
familias independientes y correspondencia de fase. Es una política conservadora
de suficiencia de evidencia, no una prueba de que la interpretación X sea falsa ni
una condición metrológica universal. El investigador puede revisar si la evidencia
externa del patrón permite aceptar X sin observar sus subdivisiones interiores.

Resultado conjunto: **AMBIGUOUS_GRID_PERIODICITY**; el GRID completo no entra como
tercer método de consenso. No se transfiere automáticamente a X la interpretación
obtenida en Y. Falta especificación del portaobjetos que identifique ambas familias
o una adquisición donde se vea un intervalo X mayor con sus cuatro marcas internas.

Los controles geométricos de reconocimiento son tolerancias técnicas explícitas:
separación de amplitudes >1.6, correspondencia espacial dentro de 0.12 pitch y
cociente dentro de 0.12 unidades de 5. No son umbrales de aceptación científica de
sx/sy; no producen PASS científico. Las marcas rechazadas por correspondencia
espacial son cero en esta imagen, pero las marcas sensibles al borde permanecen
identificadas en el análisis de rotación y variación espacial.

## Escalas menor/mayor y autoconsistencia

| Eje | 10 µm / pitch menor | 50 µm / pitch mayor | Diferencia absoluta µm/px | Diferencia simétrica % |
|---|---:|---:|---:|---:|
| X | No asignada | No asignada | N/A | N/A |
| Y, interpretación parcial provisional | 0.054660981804 | 0.054629857954 | 0.000031123850 | 0.056956009332 |

La comprobación menor/mayor es interna: comparte imagen y parte de las marcas;
no equivale a otro patrón independiente. No se publican escalas X bajo una
asignación física todavía no admitida por la política anterior.

## Rotación y observaciones comunes

Se conserva la rotación original: **−0.297855446683°**. El warp es rígido, a escala
unidad. Su factor coseno es aproximadamente 0.999986487527; no se redimensiona.

La comparación ingenua de todos los centros arroja:

| Eje/familia | Pitch antes px | Pitch después px | RMS antes px | RMS después px |
|---|---:|---:|---:|---:|
| X menor | 182.828312828332 | 182.557727463054 | 1.025468476827 | 5.327773449206 |
| X mayor | 914.326034804191 | 914.466261000508 | 0.932882480482 | 0.865177887967 |
| Y menor | 183.023207992356 | 182.945854060990 | 1.390074131589 | 1.700779351931 |
| Y mayor | 915.191193375265 | 915.250412004268 | 1.474308017445 | 1.437449900640 |

No se oculta el aumento de RMS menor. La rotación/canvas expone marcas que antes
quedaban excluidas por tocar el borde: X 15.600260244/4924.602376513 px y Y
4920.855861447 px. Por tanto, cambió el conjunto observado.

Al emparejar **las mismas diez marcas por eje**, mediante la transformación rígida
y proximidad geométrica, el resultado es:

| Eje | Pitch antes px | Pitch después px | RMS antes px | RMS después px | Cambio pitch % |
|---|---:|---:|---:|---:|---:|
| X | 182.828312828332 | 182.839866573945 | 1.025468476827 | 0.923537522467 | 0.006319251312 |
| Y | 183.023207992356 | 183.018973515624 | 1.390074131589 | 1.386544116836 | 0.002313655063 |

La rotación conserva/mejora el residual sobre observaciones comparables; el mayor
cambio inicial se relaciona con marcas del borde. No se reemplazan retrospectivamente
los pitches baseline ni se afirma invariancia exacta del detector rasterizado.

## Variación espacial y posible distorsión

Los gaps de cinco índices se dividen entre cinco para expresar pitch unitario,
pero cuentan como **una estimación**, no cinco observaciones independientes.
El JSON separa intervalos menores observados e intervalos mayores normalizados.

| Conjunto | Media pitch X/Y px | SD muestral X/Y px | Rango relativo X/Y % |
|---|---|---|---|
| Todas las marcas detectadas | 180.289431237 / 182.462945517 | 5.740605924 / 1.965978406 | 10.276866093 / 3.099098821 |
| Marcas comunes antes/después | 182.668688553 / 182.751119332 | 0.414977692 / 1.847689995 | 0.583995842 / 3.094211961 |
| Sólo intervalos mayores / 5 | 182.863648292 / 183.079238771 | 0.289517120 / 0.464168124 | 0.383229517 / 0.524805430 |

Subconjuntos disjuntos de marcas comunes (primeras/centrales/últimas):

| Eje | Primero px | Central px | Último px |
|---|---:|---:|---:|
| X | 182.393427881 | 183.011667834 | 182.652927599 |
| Y | 182.447864032 | 182.934587824 | 182.687107967 |

Pendiente lineal de pitch local frente a posición, sobre marcas comunes:
X = `9.254854789e-5 px/px`, Y = `3.022464694e-5 px/px`.
Cambio ajustado sobre el intervalo observado: X **+0.222298990%**, Y **+0.066571895%**;
R² = **0.155668162 / 0.000540404**. Incluyendo bordes, las tendencias son
+1.590783550% / −0.770508624%; la dirección Y incluso cambia.

Hay variación espacial medible, pero no una tendencia óptica estable demostrada.
**OPTICAL_DISTORTION_SIGNAL = NOT_ESTABLISHED**. No se interpreta cualquier
pendiente numérica no nula como distorsión: extracción, geometría de marca y recorte
son factores confundidos. No hay corrección de lente ni atribución causal.

## Círculos y sensibilidad algorítmica

Mismo conjunto de ocho condiciones para ambos archivos: baseline; sigma de blur
0.7, 1.5 y 2 px (default 1); 720 y 2880 perfiles (default 1440); rechazo 3 y 6 MAD
(default 4.5). Un factor a la vez; sin tuning individual, sin cambio de dimensión
física. Todos los experimentos devolvieron MEASURED.

| Métrica | GRID | C150 | C70 |
|---|---|---:|---:|
| Puntos/marcas baseline | 12 X / 11 Y | 1440 bordes | 1440 bordes |
| Inliers | Según candidata | 1431 | 1440 |
| Fracción inliers | N/A | 0.99375 | 1.0 |
| RMS elíptico px | N/A | 3.249741555 | 3.228209343 |
| RMS circular px | N/A | 3.557028728 | 3.776012719 |
| Eje mayor/menor | N/A | 1.002960047 | 1.008878149 |
| Ángulo elipse ° | N/A | 69.658029124 | 65.631816547 |
| RMS elíptico / diámetro circular, aproximadamente | N/A | 0.11769% | 0.25790% |

| Sensibilidad entre ocho ajustes | C150 X | C150 Y | C70 X | C70 Y |
|---|---:|---:|---:|---:|
| Diámetro mínimo px | 2758.020314726 | 2764.168463688 | 1247.479128324 | 1255.261210234 |
| Diámetro máximo px | 2758.543533716 | 2764.499013363 | 1248.233941128 | 1255.600395687 |
| SD diámetro px | 0.168234900 | 0.109967936 | 0.262008104 | 0.095140614 |
| sx/sy mínimo µm/px | 0.054376520858 | 0.054259379104 | 0.056079231379 | 0.055750221361 |
| sx/sy máximo µm/px | 0.054386836529 | 0.054265867645 | 0.056113163267 | 0.055765285687 |
| SD escala µm/px | 0.000003316873 | 0.000002158623 | 0.000011778516 | 0.000004225466 |
| Rango relativo escala % | 0.018969008 | 0.011957807 | 0.060494452 | 0.027017091 |

Estas SD describen **algorithmic sensitivity**, no réplicas experimentales ni
incertidumbre metrológica completa. El rango depende de las perturbaciones
ensayadas; no excluye otros sesgos de borde, patrón, iluminación o adquisición.

La diferencia entre círculos persiste para todas las combinaciones ensayadas:
X **3.064099017–3.143537648%**, Y **2.698430254–2.737398173%**.
Por tanto, estas perturbaciones concretas no explican la discrepancia baseline.
Igualar C70 a la escala de C150 exigiría, sólo como cálculo contrafactual,
**+39.063180451 px en Dx y +34.654395341 px en Dy**. No se corrige ningún diámetro
ni se asume que C150 sea la verdad física.

### Sensibilidad a un error de diámetro absoluto

Se modifica algebraicamente el **diámetro total**, no cada borde radial:
`scale(delta) = D_um / (diameter_px + delta)`.
La tabla muestra cambio relativo de escala para `−delta / +delta`:

| delta px | C150 X % | C150 Y % | C70 X % | C70 Y % |
|---|---|---|---|---|
| 0.5 | +0.018130919 / −0.018124347 | +0.018090320 / −0.018083777 | +0.040076749 / −0.040044651 | +0.039843711 / −0.039811986 |
| 1 | +0.036268414 / −0.036242125 | +0.036187186 / −0.036161015 | +0.080185633 / −0.080057244 | +0.079719184 / −0.079592284 |
| 2 | +0.072563145 / −0.072457990 | +0.072400572 / −0.072295886 | +0.160499964 / −0.159986408 | +0.159565573 / −0.159057970 |
| 3 | +0.108884223 / −0.108647623 | +0.108640185 / −0.108404643 | +0.240943303 / −0.239787797 | +0.239539471 / −0.238397360 |

El patrón menor es más sensible al mismo error en píxeles. Incluso ±3 px de
**diámetro** no alcanza el desacuerdo entre patrones. Si ambos bordes se desplazaran
radialmente ±3 px, la perturbación total del diámetro sería ±6 px: otro experimento.

## Escalas, anisotropía y consenso

| Método | sx µm/px | sy µm/px | Anisotropía % | Estado |
|---|---:|---:|---:|---|
| GRID completo | N/A | N/A | No asignada físicamente | AMBIGUOUS_GRID_PERIODICITY |
| GRID eje Y únicamente | N/A | 0.054660981804 | N/A | Jerarquía Y observada; provisional parcial |
| CIRCLE_150 | 0.054382897123 | 0.054261143289 | 0.224133481 | MEASURED |
| CIRCLE_70 | 0.056084970972 | 0.055758978496 | 0.582941640 | MEASURED |

`anisotropy = 100*abs(sx-sy)/mean(sx,sy)`. Ambos círculos mantienen `sx > sy`
en las perturbaciones. Anisotropía C150: **0.203701731–0.230118089%**;
C70: **0.569400113–0.621884883%**. Hay una diferencia aparente de ejes estable frente
a estos ajustes, pero no prueba de anisotropía instrumental: puede incluir patrón
y óptica. Los ángulos elípticos se parecen, pero son sensibles en formas casi
circulares; no permiten atribución causal con dos adquisiciones.

Como proxy puramente geométrico, suponiendo divisiones nominalmente iguales X/Y,
los pitches GRID darían anisotropía **0.212379094% (menores)** o
**0.085712834% (mayores)**. No son sx/sy físicos identificados ni fuerzan isotropía.
La diferencia entre ambos proxies y entre círculos impide establecer un único
factor de anisotropía sin nueva evidencia.

| Comparación | ΔX % | ΔY % |
|---|---:|---:|
| GRID completo–C150 | N/A | N/A |
| GRID completo–C70 | N/A | N/A |
| Eje Y GRID observado–C150 | N/A | 0.734173182 |
| Eje Y GRID observado–C70 | N/A | 1.988764873 |
| C150–C70 | 3.081572729 | 2.722838664 |

Las comparaciones Y parciales no añaden un tercer método completo al consenso.
Diferencia simétrica: `100*abs(a-b)/mean(a,b)`.

Consenso vigente: **dos círculos, sin ponderación; PROVISIONAL_ONLY**.

| Estadístico | X µm/px salvo % | Y µm/px salvo % |
|---|---:|---:|
| Media | 0.055233934048 | 0.055010060892 |
| Mediana | 0.055233934048 | 0.055010060892 |
| SD muestral (ddof=1) | 0.001203547961 | 0.001059129432 |
| CV % | 2.179000974 | 1.925337683 |
| MAD sin factor | 0.000851036924 | 0.000748917604 |
| Mínimo | 0.054382897123 | 0.054261143289 |
| Máximo | 0.056084970972 | 0.055758978496 |
| Rango relativo a media % | 3.081572729 | 2.722838664 |

Escala isotrópica auxiliar = promedio de las medias X/Y:
**0.0551219974698993 µm/px — AUXILIARY / PROVISIONAL**.
No sustituye sx/sy, no escoge media sobre mediana y no se aplica a muestras.
No se ofrece un consenso de tres métodos mientras GRID completo siga ambiguo.

## Diseño de criterios PASS / REVIEW / FAIL

Separar siempre dos dimensiones: posibilidad técnica de medir y aceptación
científica. Un método excluido no implica que todo el experimento carezca de valor.

| Criterio/métrica | Qué mide / utilidad | Política futura |
|---|---|---|
| Fuente inválida, mismatch de resolución | Identidad y geometría de la entrada | FAIL técnico del método; sin escala |
| Objeto recortado o candidatos ambiguos | Referencia incompleta/no identificable | FAIL técnico; no extrapolar |
| GRID sin asignación física | Ambigüedad de unidades de la familia | Excluir método; solicitar evidencia |
| Puntos insuficientes o resultado no determinista | Estabilidad/reproducibilidad técnica | FAIL técnico; investigar |
| Anisotropía | Diferencia aparente X/Y | REVIEW; contrastar patrón, óptica y repetibilidad |
| CV entre patrones y diferencia pareada | Dispersión y desacuerdo de métodos | REVIEW; contrastar con tolerancias justificadas |
| Residuo relativo | Adecuación geométrica del ajuste, normalizada por tamaño | Evaluar junto con sesgo y cobertura; no equivale a exactitud |
| Número/distribución de marcas | Soporte espacial, identificación y sensibilidad a extremos | Exigir cobertura demostrada, no sólo cantidad |
| Fracción de inliers / cobertura angular | Borde utilizado y exclusiones | REVIEW de diagnósticos si es insuficiente/no homogénea |
| Sensibilidad algorítmica | Dependencia del resultado respecto a opciones razonables | Registrar por componente; no confundir con incertidumbre total |

**PASS científico** requerirá tolerancias validadas, patrones trazables y evidencia
de consistencia/repetibilidad. **REVIEW científico** corresponde a mediciones
obtenibles pero con trazabilidad, incertidumbre o discrepancias por resolver.
**FAIL técnico** corresponde a imposibilidad de identificar/medir de forma válida.

Este caso requiere **revisión científica pendiente**, no PASS ni FAIL por el valor
del CV observado. No se proponen números finales de umbral a partir de sólo tres
imágenes y dos escalas completas. Los umbrales técnicos de extracción no se
convierten en reglas de aceptación de calibración.

Residuos, sensibilidad de parámetros y dispersión entre patrones son cantidades
distintas de la incertidumbre de medida. La incertidumbre del propio patrón es
un componente relevante de la trazabilidad; aquí es desconocida. Referencia:
[JCGM/VIM, measurement standard](https://jcgm.bipm.org/vim/en/5.1.html) y
[guías JCGM/GUM del BIPM](https://www.bipm.org/en/committees/jc/jcgm/publications).
No se inventa tolerancia del portaobjetos ni intervalo de confianza.

## Validaciones, outputs y reproducción

- **29 tests de calibración OK**: 19 previos +10 nuevos.
- Nuevos: jerarquía 5:1 y autoconsistencia; extracción desde patrones sintéticos
  por eje; cociente 5 con fase incorrecta; periodicidad no jerárquica;
  extrapolación sin grupo observado; ausencia de familias por longitud;
  jitter/determinismo; sensibilidad circular idéntica para ambos tamaños;
  perturbación de diámetro total y estadísticos muestrales.
- Regresión completa backend: **273 tests OK**. BD de test separada.
- `manage.py check`: sin problemas.
- `manage.py makemigrations --check --dry-run`: **No changes detected**.
- Dos ejecuciones del estudio: resultados numéricos idénticos.
- Hashes de originales, BD de trabajo y 88 archivos de MEDIA_ROOT intactos.
- Sin instalaciones, cambios de requirements, migraciones ni datos de trabajo.
- Sin staging, commit ni push.

```bash
cd ~/repos/sicam-refactor/apps/web/Backend
conda activate sicam
python -m api.services.calibration.review_cli \
  --manifest api/services/calibration/manifest.example.json \
  --baseline /tmp/sicam18sa_calibration/results.json \
  --output /tmp/sicam18sa1_calibration
```

El runner compara primero todos los resultados numéricos con el baseline; cualquier
cambio produce `BASELINE_CALIBRATION_REGRESSION` antes del estudio. Si el baseline
original ya no está disponible, puede reproducirse con el CLI de 18S-A en otro
directorio y contrastarse con docs/80; no se debe inventar un baseline nuevo para
ocultar una discrepancia.

En `/tmp/sicam18sa1_calibration/`:

- `results.json`, `report.md`: datos completos y tablas de experimentos.
- `grid-evidence.json`: decisión geométrica congelada antes de círculos.
- `grid-hierarchy.png`: índices, cortas/largas, grupos observados/inferidos.
- `grid-indexed-overlay.png`: marcas e índices sobre el original, sólo render reducido.
- `grid-local-pitch.png`: pitch local; intervalos observados separados de gaps normalizados.
- `circle-1-diagnostic.png`, `circle-2-diagnostic.png`: bordes, elipse y círculo.
- `baseline/`, `repeat/`, logs de tests y `verification.json`.

## Recomendación para la siguiente decisión

1. Revisar los diagnósticos y la política conservadora aplicada a X. Obtener
   especificación del portaobjetos o una imagen X con un grupo completo de cinco
   subdivisiones. La geometría actual es compatible con 5:1, pero no se acepta
   automáticamente como identificación física completa.
2. Obtener certificado/tolerancia y repetir adquisiciones con enfoque/control de
   iluminación y posiciones del campo. No atribuir la discrepancia C70 a un factor
   experimental sin medirlo; las perturbaciones probadas no la explican.
3. Diseñar presupuesto de incertidumbre y límites de aceptación a partir de esa
   evidencia; mantener las estimaciones presentes como provisionales.
4. Para 18S-B, comprobar al menos cámara/configuración, adaptador, objetivo,
   resolución y ausencia de transformaciones incompatibles. Un mismatch permite
   seguir en px, pero **no conversión automática a µm/µm²**.
5. No integrar todavía perfiles, series, BD, UI ni unidades físicas en Characterization.

SPRINT 18S-A.1 = READY_FOR_SCIENTIFIC_DECISION
