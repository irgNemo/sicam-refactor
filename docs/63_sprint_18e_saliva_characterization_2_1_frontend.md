# Sprint 18E — Frontend Characterization SALIVA 2.1

## Baseline y alcance

Rama `master`, HEAD inicial `05fb4dfbc97be53c9254e03848c838465df2c90a`
(`Add saliva characterization 2.1 metrics`). Precheck: working tree limpio.
Implementación limitada a frontend y este documento. Sin staging, commit ni push.

Se presentan excentricidad, desviación estándar de intensidad y textura GLCM
persistidas en SALIVA 2.1. No se calculan métricas, asociaciones, distancias ni
índices en JavaScript; no se infieren valores ausentes. No hay interpretación
clínica, clasificación normal/anormal, thresholds ni colores de riesgo.

Backend, modelos, migraciones, tres microservicios, dependencias y lockfiles
permanecen intactos. No se encontró un defecto de contrato que requiriera backend.

## Auditoría previa

Rutas relativas a `apps/web/Frontend`:

| Archivo | Responsabilidad existente y decisión |
| --- | --- |
| `src/components/characterization/CharacterizationResultPanel.vue` | Selecciona renderer; mantiene `selectedCellId`, selección bidireccional y reseteo al cambiar snapshot. Sin cambios. |
| `src/domain/characterizationPresentation.js` | Ya admitía 2.0/2.1; formatter numérico central con `—`, porcentaje genotóxico y valores ausentes. Se extiende sin alterar el formatter previo. |
| `src/components/characterization/SalivaMorphometricResult.vue` | Summary, índices, calidad de asociaciones, tabla de células, detalles, huérfanos/ambiguos y warnings. Se extiende aquí. |
| `src/components/characterization/CharacterizationEffectiveOverlay.vue` | Proyección read-only, visibilidad por tipo, clic/teclado de membranas y resaltado de objetos relacionados por IDs. Sin cambios. |
| `tests/segmentationStrategies.test.mjs` | Node + Vite/Vue SSR, host Vue mínimo para eventos; estrategias, legacy, edición, navegación de revisiones, pan/zoom/proyección. Se conserva y adapta la expectativa de 18D que aún ocultaba campos 2.1. |

El renderer legacy SALIVA v1 y BLOOD 1.0 está en el propio
`CharacterizationResultPanel.vue`, en las ramas de conteos/índices/warnings que
no usan el renderer morfométrico. El fallback de schema desconocido sigue igual.

Contrato auditado:

- `summary`: conteos, clases nucleares, índices, agregados geométricos y
  `association_quality`. Sólo se leen; no se reconstruyen a partir de `cells`.
- `cells[]`: `membrane_id`, `source_raw_id`, `display_label`, `metrics`, estado de
  asociación, clase nuclear, conteos y arrays `nuclei[]`/`micronuclei[]`.
- Núcleo: `id`, `source_raw_id`, `metrics`, `association_status`.
- MN: campos anteriores, `display_label`, `nucleus_id` y tres métricas relativas
  dentro de `metrics`.
- `unassociated` y `ambiguous`: arrays `nuclei`/`micronuclei`; ambiguos conservan
  `candidate_membrane_ids`. Se mantienen estas relaciones sin reasociar.
- `warnings[]`: `code`, `object_id`, `message` y contexto adicional.
- `methodology.texture`: parámetros globales de GLCM.

Antes de 18E, los detalles vivían dentro de la última columna de la tabla, con
un mínimo de 700 px adicionales. Para agregar grupos sin ampliar excesivamente
la tabla, ahora cada detalle ocupa una fila con `colspan=6`. Se conservan las seis
columnas del resumen, los IDs, los eventos de selección y el contenedor de scroll.

## Versiones y renderer

| Payload | Presentación |
| --- | --- |
| SALIVA 2.1 | Morfometría e intensidad extendidas, textura por objeto y metodología global |
| SALIVA 2.0 | Mismas métricas anteriores; no aparecen placeholders o warnings por campos 2.1 ausentes |
| SALIVA legacy v1 | Renderer legacy existente |
| BLOOD 1.0 | Conteos existentes; sin secciones 2.1 vacías |
| Schema desconocido | Fallback existente; no se supone compatibilidad científica |

Los históricos se leen tal como llegan. Se reutiliza la fixture 2.0 congelada en
18D para comprobar el renderer. No se cambia la política previa de vigencia ni
se agrega selección de históricos en este sprint.

No existen ramas CURRENT/ALT para presentar métricas. Una prueba compara el
HTML completo del mismo resultado 2.1 con ambas procedencias y obtiene igualdad.

## Organización por objeto

`SalivaObjectMetrics.vue` es un componente pequeño compartido por región celular,
núcleos, MN, huérfanos y ambiguos. Usa únicamente los grupos de presentación que
entrega `objectMetricGroups`; no mantiene estado científico.

1. **Morfometría**: área, perímetro, centroide, circularidad; excentricidad en 2.1.
2. **Intensidad**: media; desviación estándar en 2.1.
3. **Textura GLCM** en 2.1: contraste, homogeneidad, energía, correlación y entropía.
4. **Computabilidad** en una zona secundaria: ángulos válidos y pares válidos.
5. En MN se conservan distancia y fracciones respecto al núcleo asociado.

Las regiones celulares se titulan **Región celular**, y el conteo de membranas
se presenta como **Células**, sin cambiar el número recibido. La explicación
aclara que se mide la región delimitada, no el espesor de membrana. El overlay
conserva su contrato técnico `membrana` y su leyenda existente.

Se mantienen IDs normalizados como identidad editorial, raw ID como información
adicional, núcleo asociado, clase nuclear, ausencia de MN y conteos persistidos.
Los grupos no asociados/ambiguos conservan su detalle expandible existente y
ahora muestran todos los grupos de métricas disponibles, incluidos null.

## Labels, unidades y precisión

`METRIC_LABELS`, `formatMetric`, `formatCentroid` y `objectMetricGroups` viven en
`characterizationPresentation.js`. Se reutiliza `formatNumber`; no se distribuye
`toFixed` por templates ni se muta el payload.

| Campo | Label | Formato |
| --- | --- | --- |
| `area_px2` | Área | 2 decimales, px² |
| `perimeter_px` | Perímetro | 2 decimales, px |
| `centroid_px` | Centroide | (x, y), 2 decimales, px |
| `circularity` | Circularidad | 4 decimales, sin unidad |
| `eccentricity` | Excentricidad | 4 decimales, sin unidad |
| `mean_gray_intensity` | Intensidad media | 4 decimales, normalizada |
| `std_gray_intensity` | Desv. estándar de intensidad | 4 decimales, normalizada |
| `texture.contrast` | Contraste | 4 decimales |
| `texture.homogeneity` | Homogeneidad | 4 decimales |
| `texture.energy` | Energía | 4 decimales |
| `texture.correlation` | Correlación | 4 decimales |
| `texture.entropy` | Entropía | 4 decimales |
| `texture.valid_angles` | Ángulos válidos | Entero |
| `texture.valid_pairs` | Pares válidos | Entero |
| `distance_to_nucleus_px` | Distancia al núcleo | 2 decimales, px |
| `area_fraction_to_nucleus` | Fracción de área respecto al núcleo | 4 decimales |
| `intensity_fraction_to_nucleus` | Fracción de intensidad respecto al núcleo | 4 decimales |

Las intensidades no se convierten a porcentaje ni se multiplican por 255. La
textura no recibe unidades físicas. No hay conversión a µm.

`null`, ausentes y valores no finitos se representan mediante **—**. Los ceros
siguen siendo valores (`0.0000` o `0` para contadores). Valores pequeños pueden
redondearse a `0.0000` conforme a la precisión elegida, nunca se confunden con
un dato ausente. No se redondean fracciones de contadores a enteros inventados:
si el dato recibido no es entero, se muestra `—`.

Se explica una sola vez por resultado 2.1 que 0 de excentricidad corresponde a
forma aproximadamente circular y cerca de 1 a mayor elongación; no es un
clasificador. También se aclara la escala gris normalizada de 0 a 1.

## Metodología dinámica y warnings

El botón **Metodología de textura** muestra un bloque único por resultado 2.1.
`textureMethodologyRows(result.methodology.texture)` presenta método, niveles,
distancia, ángulos, simetría, normalización y agregación a partir del payload.
Los labels son humanos, los valores no están hardcodeados. Se traduce la clave
conocida `mean_over_valid_angles`; otras agregaciones mantienen un fallback legible.
Parámetros ausentes no se sustituyen por defaults científicos. Si falta el bloque
completo, se indica que no está disponible en ese resultado.

`warningLabel` reconoce, entre otros:

- `ECCENTRICITY_NOT_COMPUTABLE`: No fue posible calcular la excentricidad.
- `TEXTURE_INSUFFICIENT_PAIRS`: No hay suficientes pares de píxeles para calcular
  la textura.
- `TEXTURE_CORRELATION_UNDEFINED`: No fue posible calcular la correlación GLCM
  para este objeto.

Se conserva la agrupación, el mensaje del backend, `object_id` (incluido 0) y
contexto adicional. Warnings geométricos anteriores reciben labels humanos;
códigos futuros conservan un fallback escapado por Vue, sin ocultarlos ni
convertirlos en error fatal. Autointersección/métricas inválidas se muestran como
`—` y warning; no se corrigen polígonos ni se estiman valores.

## Summary, distancias y selección

No cambian `summary`, `association_quality`, genotoxicidad o citotoxicidad.
Se conserva incluso el formato porcentual previo del índice genotóxico; no se
agregan interpretaciones o nuevos indicadores.

MN conserva exclusivamente `distance_to_nucleus_px` y sus ratios. La UI muestra
la distancia persistida al núcleo asociado, o `—` cuando es null. No calcula
distancias al centro/borde celular, entre núcleos ni entre MN.

`CharacterizationResultPanel` sigue siendo dueño de `selectedCellId`:

- Clic/teclado sobre membrana del overlay → evento `select-cell` → célula
  seleccionada y scroll local hacia su fila.
- Clic en fila/botón de célula → selección y resaltado de membrana, núcleos y MN
  según IDs y relaciones recibidas. Clic repetido deselecciona.
- Abrir detalle/metodología no emite selección ni cambia IDs.
- Actualizar un valor 2.1 del mismo snapshot no pierde selección ni resaltado.

No se modifican overlay, proyección, colores por tipo, polígonos, rutas, edición,
protecciones de navegación, listeners de teclado ni manejo de snapshots del padre.
No se dibujan ejes de excentricidad, mapas de textura o colores por features.

## Accesibilidad y responsive

Nuevos desplegables: botones nativos `type=button`, `aria-expanded` y
`aria-controls` enlazados a IDs generados con `useId`. El contenido cerrado se
oculta con `v-show`. Los botones permiten activación nativa por teclado y tienen
foco visible. Se conservan los `details/summary` nativos existentes para grupos
especiales. Los encabezados de tabla ahora tienen `scope=col`.

Los detalles usan una fila completa y grid auto-fit con columnas desde 240 px,
que se apilan según espacio disponible. Metodología también usa grid adaptable;
labels y valores largos permiten wrap. La tabla de seis columnas conserva
scroll local (mínimo 620 px) en pantallas pequeñas, no una tabla de 12+ columnas.
No se añaden colores clínicos; se conservan los estilos anteriores de warnings,
estados de computabilidad y selección.

La estructura responsive y las relaciones accesibles se verificaron en código y
tests. **No se afirma inspección visual de escritorio/móvil**, pendiente por
falta de navegador/automatización visual disponible en esta sesión.

## Pruebas y validación

Nueva fixture `tests/fixtures/saliva21.mjs`: sintética, pequeña, sin imágenes ni
JSON clínicos. Incluye célula con núcleo/MN, célula binucleada sin MN, métricas 0 y
null, MN con distancia null, huérfanos, ambiguos y warnings conocidos/desconocidos.

`tests/characterization21.test.mjs`: 22 casos. Cubre formatters, labels, unidades,
precisión, null/no finitos/0/valores pequeños, GLCM 0/1/null con 4 ángulos y 123
pares, metodología con 32/1 y luego 16/2, flags falsos y parámetros ausentes,
warnings con fallback escapado, células/objetos especiales, versiones, independencia
CURRENT/ALT y no mutación de datos.

La prueba interactiva monta componentes Vue reales con un host mínimo:
selecciona el polígono, verifica `selectedCellId` y los tres objetos resaltados,
comprueba scroll local, selecciona otra fila, abre detalles y metodología,
actualiza reactivamente contraste y verifica que selección y highlight persisten.
Comprueba relaciones ARIA y headers. Es una prueba de eventos/estado, no de
layout en navegador.

La suite anterior de 21 casos se conserva: legacy, histórico 2.0, estrategias,
revisiones/efectivo, guards de validación, edición, pan, zoom y proyección.
La comparación 18D que exigía HTML idéntico entre 2.0/2.1 se adapta a comprobar
los campos comunes y los nuevos grupos sólo en 2.1.

Desde `apps/web/Frontend`:

```bash
node --test tests/*.test.mjs
node tests/characterization21.test.mjs
node tests/segmentationStrategies.test.mjs
npm run build
node_modules/.bin/eslint src/domain/characterizationPresentation.js \
  src/components/characterization/SalivaMorphometricResult.vue \
  src/components/characterization/SalivaObjectMetrics.vue \
  tests/characterization21.test.mjs tests/fixtures/saliva21.mjs \
  tests/segmentationStrategies.test.mjs
```

Resultados: dos archivos de suite PASS; 22 + 21 = **43 casos**. Build Vite PASS,
103 módulos. ESLint read-only sin errores ni warnings. No se ejecutó
`npm run lint` (contiene `--fix`) ni se actualizaron dependencias.

Desde `apps/web/Backend`, entorno `sicam`:

```bash
python -m pytest -q api/test_characterization_2_1.py api/tests.py \
  -k 'Characterization or RasterMetrics'
```

Resultado: **44 passed, 116 deselected in 1.73s**. Cubre caracterización 2.1,
históricos, API/idempotencia, revisiones y BLOOD sin cambiar backend.

## Smokes 2.1, 2.0 y BLOOD

Se crearon únicamente en `/tmp/sicam18e` una SQLite demo aislada y fixtures
sintéticas, sin tocar la base habitual. `sicam18e_settings.py` sobrescribe la
base y MEDIA_ROOT; `seed.py` carga snapshots de presentación. No ejecuta Cellpose,
no usa datos clínicos y no recalcula ciencia.

Se iniciaron Django `127.0.0.1:8000` y Vite `127.0.0.1:5173` para una página
temporal `/__sicam18e` que monta el panel real con respuestas de la API demo.
La página permite alternar SALIVA 2.1, SALIVA 2.0 y BLOOD 1.0. Es un harness de
presentación; proporcionar manualmente el histórico al panel no cambia la
política de selección/vigencia del producto.

| Smoke | API HTTP | Render SSR/estado | Revisión visual |
| --- | --- | --- | --- |
| SALIVA 2.1 | 200 | PASS: summary, grupos nuevos, metodología, warnings/null y selección | PENDING |
| SALIVA 2.0 | 200 | PASS: métricas previas, sin grupos 2.1 | PENDING |
| BLOOD 1.0 | 200 | PASS: conteos, sin GLCM/excentricidad/std | PENDING |

Vite devolvió 200 para la página, el harness y los dos componentes de métricas.
Las respuestas HTTP quedaron en `/tmp/sicam18e/http-{1,2,3}.json`.
Los procesos iniciados fueron detenidos; los puertos 8000/5173 quedaron libres.
No se dejó ningún microservicio activo ni se lanzó segmentación pesada.

Para completar inspección manual mientras existan los temporales, desde Backend:

```bash
PYTHONPATH=/tmp/sicam18e python manage.py runserver 127.0.0.1:8000 \
  --noreload --settings=sicam18e_settings
```

En otra terminal:

```bash
node /tmp/sicam18e/vite-smoke.mjs
```

Abrir `http://127.0.0.1:5173/__sicam18e`. Revisar a 1280 px y ancho móvil: abrir
detalles/metodología, comprobar lectura sin superposición, scroll contenido,
selección bidireccional y teclado; alternar 2.0/BLOOD. Detener ambos procesos al
terminar. La ausencia de navegador en esta sesión impide certificar estos puntos
visuales; HTTP/SSR no sustituyen esa inspección.

## Archivos y cierre

Modificados:

- `src/components/characterization/SalivaMorphometricResult.vue`;
- `src/domain/characterizationPresentation.js`;
- `tests/segmentationStrategies.test.mjs`.

Nuevos:

- `src/components/characterization/SalivaObjectMetrics.vue`;
- `tests/characterization21.test.mjs`;
- `tests/fixtures/saliva21.mjs`;
- este documento.

README, guía WSL y startup fueron revisados: sin contradicciones por instalación
ni arranque, por lo que no se modifican. Doc 62 y documentos históricos intactos.

`git diff -- apps/web/Backend` y diffs de los tres microservicios: vacíos.
`git diff --check`: PASS. Working tree limitado a estos siete archivos;
staging vacío. No se versionan artefactos del smoke. No commit ni push.

SPRINT 18E = PASS WITH VISUAL SMOKE PENDING
