# Sprint 18Q-A — Distribución visual de segmentación

Estado: **READY_FOR_VISUAL_REVIEW**.
HEAD inicial: `bb0e80724ca6e38bda07c96caa1bf54d673e7039`, rama `master`.
Working tree inicialmente limpio.

## Problema y decisión

La tarjeta Capas visibles estaba fuera de la cuadrícula que contiene el visor
y la columna de acciones. Por ello aparecía después de toda la tarjeta principal,
dejando espacio bajo los controles cuando la columna derecha era más alta.
Además, la tabla vertical de capas imponía un min-height de 170px.

Se reutiliza OverlayLayersCard dentro de image-container, inmediatamente después
de SegmentationImageControls. La secuencia central es visor, controles y capas,
con el gap existente de 10px. La tarjeta usa opciones horizontales con flex-wrap;
se elimina su altura mínima y la tabla. El visor conserva sus alturas y breakpoints.
Se mantienen bordes, radios, sombra, tipografía y paleta existentes.

## Archivos y comportamiento

- `apps/web/Frontend/src/components/MainContent.vue`: traslado del componente,
  sin cambios de script ni estilos del visor o sidebars.
- `apps/web/Frontend/src/components/segmentation/OverlayLayersCard.vue`:
  template compacto y CSS; script, props y emits intactos.
- `apps/web/Frontend/tests/segmentationStrategies.test.mjs`: dos tests nuevos
  de interacción de capas y ubicación única después de los controles.

Los checkboxes reales conservan checked y change-visibility. Cada uno está
envuelto en un label pulsable y tiene foco visible. Se preservan nombres y
colores recibidos mediante label.stroke, sin introducir conteos nuevos.
La lista sigue siendo dinámica, preservando también las capas propias de BLOOD
y el mensaje Sin objetos dibujables cuando no existen capas.

No se modificaron SVG, coordenadas, zoom, rotación, selección, estado Vue,
watchers, API, edición, validación, segmentación selectiva ni Characterization.
No se consolidaron Resultado mostrado y Revisión validada. Sin cambios en
backend, microservicios, dependencias ni package-lock; sin escrituras en BD/media.

## Validación

Node 24.17.0, toolchain instalada; sin npm install.

- `node tests/segmentationStrategies.test.mjs`: **41 passed**, incluidos los
  39 existentes y dos nuevos. Cobertura de presentación AUTOMATICO/VALIDADA,
  BORRADOR, entrada EDIT del flujo selectivo, selección, edición de vértices,
  undo/redo, zoom/pan, contratos y activación/desactivación de las tres capas.
- `node tests/characterization21.test.mjs`: **22 passed**.
- `npm run build`: **PASS**, 105 módulos transformados.
- Diff revisado: cambios productivos limitados a template/CSS.
- `git diff --check`: PASS.

El test nuevo de capas inicialmente quedó cancelado por cargar el módulo Vite
durante la ejecución del test; se movió su carga al setup de módulos existente.
La suite final pasa sin debilitar ni eliminar pruebas anteriores.

## Revisión visual pendiente

No se realizó inspección en navegador: no se encontraron Chromium/Chrome ni
Playwright instalados. Los tests usan el renderer Vue existente; no certifican
medidas de layout en navegador. Flex-wrap y límites de ancho permiten ajuste
de filas sin imponer anchura fija, pendiente de comprobación visual real.

Revisar en escritorio grande y laptop: proximidad de capas a controles, visor
sin reducción, sidebars intactas, labels/foco legibles, ausencia de overflow y
modo lectura/BORRADOR/VALIDADA al entrar a Editar. Comprobar toggles y selección
sin guardar cambios durante la inspección. No se rediseñaron herramientas del editor.

Únicos cambios: los tres archivos frontend indicados y este documento.
Sin commit ni push; pendiente revisión visual del investigador.

SPRINT 18Q-A = READY_FOR_VISUAL_REVIEW
