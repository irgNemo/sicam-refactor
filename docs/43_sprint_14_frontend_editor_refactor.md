# Sprint 14 - Refactor incremental del frontend del editor de segmentacion

## Objetivo

Reducir responsabilidades de `MainContent.vue` sin cambiar funcionalidad, contratos API, geometria del overlay, layout ni comportamiento editorial.

Este sprint fue tratado como refactor incremental, no como rediseño.

## Problema original

`apps/web/Frontend/src/components/MainContent.vue` concentraba seleccion de muestra, historial, resultado efectivo, revisiones, modos de editor, viewport, overlay SVG, DRAW, VERTEX, Undo/Redo, persistencia y paneles de UI.

Linea base observada:

```text
MainContent.vue antes: 4822 lineas
MainContent.vue despues: 4472 lineas
```

## Arquitectura Antes

```text
MainContent
   ├── seleccion de muestra e historial
   ├── segmentacion y resultado efectivo
   ├── toolbar NAVIGATE/EDIT
   ├── viewport, zoom, pan, rotacion
   ├── SVG overlay
   ├── DRAW / VERTEX
   ├── Undo/Redo
   ├── persistencia de BORRADOR / VALIDADA
   ├── Resumen de Conteo
   └── Capas visibles
```

## Arquitectura Despues

```text
MainContent
   ├── data orchestration
   ├── revision orchestration
   ├── effective result
   ├── editor state
   ├── SVG overlay y pointer handlers
   ├── viewport state
   │
   ├── SegmentationEditorToolbar
   ├── SegmentationImageControls
   ├── SegmentationCountSummary
   ├── SegmentationResultPanel
   ├── OverlayLayersCard
   └── useSegmentationViewport
```

`MainContent.vue` sigue siendo el orquestador. No se elimino ni se reescribio.

## Componentes Extraidos

### `SegmentationEditorToolbar.vue`

Responsabilidad:

- render de controles `NAVIGATE` / `EDIT`;
- render de herramientas `SELECT`, `PAN`, `DRAW`, `VERTEX`;
- indicadores de revision activa y dirty state.

Contrato:

- props: `viewerMode`, `isEditMode`, `revisionLoading`, `activeRevision`, `isDraftDirty`, `editorTool`;
- emits: `change-viewer-mode`, `change-editor-tool`.

No llama API ni decide transiciones.

### `SegmentationImageControls.vue`

Responsabilidad:

- render de botones Zoom In, Zoom Out, Rotar y Ajustar.

Contrato:

- prop: `imageZoom`;
- emits: `zoom-in`, `zoom-out`, `rotate`, `reset`.

No modifica estado internamente.

### `SegmentationCountSummary.vue`

Responsabilidad:

- render de `Resumen de Conteo`;
- muestra membranas, nucleos, micronucleos y total.

Contrato:

- props: `summary`, `palette`.

No recalcula resumen ni consulta backend.

### `SegmentationResultPanel.vue`

Responsabilidad:

- render de boton `Ejecutar segmentacion`;
- errores/exito de segmentacion;
- indicador de resultado efectivo;
- revision pendiente;
- revision validada;
- historial compacto.

Contrato:

- props de solo lectura para loading, errores, metadata, historial y revision;
- emits: `run-segmentation`, `continue-edit`.

No llama API directamente.

### `OverlayLayersCard.vue`

Responsabilidad:

- render de `Capas visibles`;
- checkboxes por etiqueta;
- swatches y nombres visibles.

Contrato:

- prop: `labels`;
- emit: `change-visibility`.

La fuente de verdad sigue siendo `overlayLabelVisibility` en `MainContent.vue`.

## Composable Extraido

### `useSegmentationViewport.js`

Responsabilidad:

- constantes `ZOOM_MIN`, `ZOOM_MAX`, `ZOOM_STEP`;
- calculo de limites de pan;
- calculo de `object-fit: contain`;
- validacion liviana de puntos;
- transformacion natural image -> coordenadas SVG.

Funciones:

```text
calculateImagePanLimits
calculateOverlayContainment
getValidPolygonPoints
scalePointToOverlay
scalePolygonPointsToOverlay
```

La geometria se movio de forma mecanica. No se cambio precision, redondeo ni modelo de coordenadas.

## Ownership del Estado

### Viewport

`MainContent.vue` conserva:

- `imageZoom`;
- `imageRotation`;
- `panX`;
- `panY`;
- estado de pan activo;
- refs DOM.

Las formulas puras viven en `useSegmentationViewport.js`.

### Editor

`MainContent.vue` conserva:

- `viewerMode`;
- `editorTool`;
- `vertexEditMode`;
- `workingObjects`;
- `draftPolygonPoints`;
- seleccion;
- Undo/Redo;
- dirty state;
- handlers de pointer.

No se extrajo el estado editorial en este sprint para evitar dependencias circulares con viewport, SVG y pointer capture.

### Revisiones

`MainContent.vue` conserva:

- `activeRevision`;
- `pendingDraftRevision`;
- `latestValidatedRevision`;
- `effectiveSegmentation`;
- save/validate orchestration.

No se cambiaron servicios HTTP ni endpoints.

## DOM Refs

Permanecen en `MainContent.vue`:

- `imageFrame`;
- `mainImage`.

Despues de Sprint 14B, el nodo SVG vive dentro de `SegmentationOverlay.vue`.
`MainContent.vue` conserva la orquestacion de coordenadas mediante
`getSegmentationSvgElement()`, que obtiene el nodo desde el componente hijo con
`getSvgElement()`.

## Pointer Capture y Listeners

Permanecen en `MainContent.vue`:

- pan;
- draft point drag;
- vertex drag;
- pointer capture;
- listeners globales de teclado, blur y beforeunload.

No se duplicaron listeners.

## Comportamientos Preservados

El refactor no cambia intencionalmente:

- resultado efectivo en `NAVIGATE`;
- `EDIT` con `BORRADOR`;
- zoom 100-800%;
- pan;
- Space + Pan;
- rotacion;
- ajustar;
- capas visibles;
- overlay SVG;
- DRAW;
- VERTEX;
- Undo/Redo;
- guardar BORRADOR;
- validar revision;
- refresh de Resumen del Caso.

## Validaciones

Comando ejecutado:

```powershell
npm.cmd run build
```

Resultado:

```text
PASS
```

Dentro del sandbox aparecio el bloqueo conocido de Vite/esbuild al resolver `vite.config.js`; el build real paso fuera del sandbox.

## Pendientes Fuera de Alcance

- Agregar tests frontend si se incorpora infraestructura futura.
- Resolver detalles visuales menores en un sprint separado.

## Hotfix de estilos scoped tras extraccion de componentes

Despues de extraer componentes en Sprint 14 se detecto una regresion visual: los controles extraidos aparecian con apariencia HTML nativa.

Causa:

```text
MainContent.vue usaba <style scoped>.
Al mover DOM interno a componentes hijos, las reglas scoped de MainContent ya no aplicaban a esos nodos.
```

Componentes afectados:

- `SegmentationEditorToolbar.vue`;
- `SegmentationImageControls.vue`;
- `SegmentationCountSummary.vue`;
- `SegmentationResultPanel.vue`;
- `OverlayLayersCard.vue`.

Estrategia aplicada:

- se movieron estilos especificos al `<style scoped>` del componente que renderiza cada bloque;
- `MainContent.vue` conserva solo estilos que todavia consume directamente o que pertenecen al layout padre;
- no se convirtio CSS scoped en global;
- no se uso `:deep()`;
- no se agregaron `!important`;
- no se cambiaron props, emits, handlers ni logica.

Reglas reubicadas por ownership:

- toolbar, botones de modo y badges -> `SegmentationEditorToolbar.vue`;
- controles de zoom/rotacion/ajuste -> `SegmentationImageControls.vue`;
- tabla de conteos -> `SegmentationCountSummary.vue`;
- panel de segmentacion, resultado efectivo, historial y tarjetas de revision -> `SegmentationResultPanel.vue`;
- card de capas visibles, tabla, checkboxes y labels -> `OverlayLayersCard.vue`.

Confirmacion funcional:

- el hotfix es CSS/presentacion;
- no modifica backend;
- no modifica API;
- no modifica resultado efectivo;
- no modifica DRAW, VERTEX, Undo/Redo, viewport ni geometria del overlay.

## Sprint 14B - Extraccion del overlay SVG

Sprint 14B extrajo el render SVG del overlay a:

```text
apps/web/Frontend/src/components/segmentation/SegmentationOverlay.vue
```

Objetivo:

- reducir responsabilidades visuales de `MainContent.vue`;
- mantener en `MainContent.vue` el estado editorial, pointer capture, Undo/Redo,
  revisiones y calculos de coordenadas;
- preservar el mismo sistema de transformacion compartido entre imagen y SVG.

Responsabilidades de `SegmentationOverlay.vue`:

- renderizar el `<svg>` absoluto sobre la imagen;
- renderizar poligonos visibles, highlights, poligono en construccion y handles
  de vertices;
- contener los estilos scoped del overlay SVG;
- emitir intenciones de interaccion al padre.

Responsabilidades que permanecen en `MainContent.vue`:

- construir `overlayPolygons` y `selectionHighlightPolygons`;
- calcular LOD, vertices visibles, segmentos cercanos y handles;
- manejar `DRAW`, `VERTEX`, seleccion, borrador, Undo/Redo y persistencia;
- mantener pointer capture y conversiones con `getScreenCTM()`;
- conservar `image-transform-layer` como wrapper comun de imagen y overlay.

Contrato principal del componente:

- props: estado de modo (`isEditMode`, `effectivePanMode`, `isDrawMode`,
  `isVertexMode`, `vertexEditMode`), medidas de imagen, colecciones ya
  calculadas, estilos de stroke/fill y radios de handles;
- emits: `overlay-click`, `polygon-pointerdown`, `polygon-click`,
  `draft-segment-pointerdown`, eventos de drag de puntos de borrador y eventos
  de drag de vertices.

Manejo del ref SVG:

- `SegmentationOverlay.vue` expone `getSvgElement()`;
- `MainContent.vue` usa `getSegmentationSvgElement()`;
- `svgArrayPointToScreenPoint()` y `screenPointToSvgPoint()` siguen viviendo en
  el padre y siguen usando el mismo nodo SVG para `getScreenCTM()`.

Fuente de verdad de geometria:

- no se duplicaron formulas de coordenadas;
- `useSegmentationViewport.js` conserva las funciones puras de viewport;
- `MainContent.vue` conserva las computadas editoriales que dependen del estado
  de revision, seleccion y pointer events.

Conteo de lineas observado:

```text
MainContent.vue antes de Sprint 14B: 4072 lineas
MainContent.vue despues de Sprint 14B: 3793 lineas
SegmentationOverlay.vue: 482 lineas
```

Validacion automatica ejecutada:

```powershell
npm.cmd run build
git diff --check
```

Resultado:

```text
PASS
```

Nota: dentro del sandbox se reprodujo el bloqueo conocido de Vite/esbuild al
resolver `vite.config.js`; el build paso fuera del sandbox.

Checklist manual especifico:

1. `NAVIGATE`: overlay visible y capas visibles funcionales.
2. Zoom, Zoom Out, Rotar, Ajustar y pan mantienen imagen y overlay alineados.
3. `EDIT/SELECT`: seleccion de objetos automatizados y manuales.
4. `DRAW`: crear mascara, insertar/mover/eliminar vertices de borrador.
5. `VERTEX`: handles visibles, INSERT/MOVE/DELETE sin cambio de comportamiento.
6. Guardar `BORRADOR`, recargar y validar revision.

## Sprint 14C - Extraccion del dominio editorial

Sprint 14C extrajo el estado y las operaciones editoriales en memoria a:

```text
apps/web/Frontend/src/composables/useSegmentationEditor.js
```

Objetivo:

- hacer que `workingObjects` tenga una unica fuente de verdad editorial;
- mover operaciones de dominio como crear/eliminar mascaras, modificar vertices,
  Undo/Redo y dirty state fuera de `MainContent.vue`;
- mantener en `MainContent.vue` la orquestacion de API, revision efectiva,
  seleccion de muestra, DOM refs, pointer capture y conversion de coordenadas.

Arquitectura despues de Sprint 14C:

```text
MainContent
   |
   |-- revisions / effective / data
   |-- useSegmentationViewport
   |-- useSegmentationEditor
   |      |-- workingObjects
   |      |-- DRAW
   |      |-- VERTEX
   |      |-- Undo/Redo
   |
   |-- SegmentationOverlay
   |-- Toolbar
   `-- Panels
```

Ownership de `useSegmentationEditor.js`:

- `workingObjects`;
- `selectedObjectKey`;
- `selectedObject`;
- `selectedVertexIndex`;
- `selectedDraftPointIndex`;
- `draftPolygonPoints`;
- `draftPointDrag`;
- `vertexDrag`;
- `editorTool`;
- `vertexEditMode`;
- `drawingLabel`;
- `undoStack`;
- `redoStack`;
- `isDraftDirty`;
- `draftBaselineSignature`;
- `manualObjectIdCursor`;
- `workingSummary`.

Operaciones movidas:

- `loadRevisionSnapshot()` / `loadWorkingRevision()`;
- `resetEditor()`;
- `buildEditableSnapshot()`;
- asignacion monotona de IDs editoriales manuales;
- mutaciones de `provenance.modified`;
- `CREATE_OBJECT`;
- `DELETE_OBJECT`;
- `MOVE_VERTEX`;
- `INSERT_VERTEX`;
- `DELETE_VERTEX`;
- `undoRevisionEdit()`;
- `redoRevisionEdit()`;
- operaciones de borrador DRAW: append, insert, move, delete, finish y cancel.

Responsabilidades que permanecen en `MainContent.vue`:

- `RevisionSegmentacion` API;
- guardar `BORRADOR` por HTTP;
- validar revision por HTTP;
- resultado efectivo;
- historial y seleccion de muestra;
- refs DOM `imageFrame`, `mainImage` y SVG via `SegmentationOverlay`;
- `getScreenCTM()`, `DOMPoint` y conversiones screen/SVG/natural;
- `setPointerCapture()` y `releasePointerCapture()`;
- listeners globales de teclado, blur y beforeunload;
- `Space + Pan` y pan del visor;
- deteccion de segmentos cercanos en pantalla.

Flujo de coordenadas:

```text
PointerEvent
   -> MainContent screenPointToNaturalImagePoint()
   -> useSegmentationEditor opera con punto natural
   -> workingObjects
   -> MainContent computa overlay visual
   -> SegmentationOverlay renderiza SVG
```

Sincronizacion revision -> editor:

- al entrar a `EDIT`, `MainContent.vue` solicita o reutiliza el `BORRADOR`;
- despues llama `loadWorkingRevision(response.data)`;
- el composable deep-clonea `resultado_editado.objects`, reinicia seleccion,
  limpia DRAW/VERTEX/Undo/Redo y deja `isDraftDirty=false`.

Sincronizacion save exitoso -> editor:

- `MainContent.vue` ejecuta `updateSegmentationDraft()`;
- al recibir respuesta del backend actualiza `activeRevision`;
- despues llama `loadWorkingRevision(response.data)`;
- el composable sincroniza el snapshot confirmado y deja `isDraftDirty=false`.

Interaccion con `SegmentationOverlay.vue`:

- el overlay sigue siendo presentacional;
- emite eventos de puntero;
- `MainContent.vue` traduce eventos y coordenadas;
- `useSegmentationEditor.js` aplica la mutacion editorial.

Garantias preservadas:

- no se modifico backend;
- no se modificaron endpoints;
- no se modifico `segmentationRevisionService.js`;
- no se modificaron microservicios;
- no se cambiaron contratos de `resultado_editado`;
- no se cambiaron IDs, `raw_id`, `raw_type` ni `provenance` salvo las mismas
  mutaciones editoriales ya existentes.

Conteo de lineas observado:

```text
MainContent.vue antes de Sprint 14C: 3793 lineas
MainContent.vue despues de Sprint 14C: 3280 lineas
useSegmentationEditor.js: 690 lineas
```

Validacion automatica ejecutada:

```powershell
npm.cmd run build
git diff --check
rg -n "console\.(log|debug|table)" apps/web/Frontend/src/components/MainContent.vue apps/web/Frontend/src/components/segmentation apps/web/Frontend/src/composables apps/web/Frontend/src/services -g "*.vue" -g "*.js"
```

Resultado:

```text
PASS
```

Nota: dentro del sandbox se reprodujo el bloqueo conocido de Vite/esbuild al
resolver `vite.config.js`; el build paso fuera del sandbox.
`git diff --check` no reporto errores de whitespace, solo el aviso conocido de
LF/CRLF en este documento. La busqueda de logs temporales no encontro
coincidencias.

Checklist manual especifico:

1. `SELECT`: seleccionar membrana, nucleo y micronucleo; eliminar, Undo y Redo.
2. `DRAW`: append, insertar punto en segmento, mover punto, eliminar punto,
   finalizar y cancelar.
3. `VERTEX`: MOVE, INSERT, DELETE, minimo de 3 puntos y Undo/Redo.
4. Secuencia mixta: `CREATE_OBJECT`, `INSERT_VERTEX`, `MOVE_VERTEX`,
   `DELETE_VERTEX`, `DELETE_OBJECT`, luego Undo x5 y Redo x5.
5. Dirty/save: modificar, guardar `BORRADOR`, recargar y continuar edicion.
6. Validar: guardar, validar, volver a `NAVIGATE` y confirmar resultado efectivo.
7. Cambio de imagen: A -> B -> A sin arrastrar estado editorial entre muestras.
8. Space/Pan en DRAW y VERTEX sin romper prioridad de eventos.

## Sprint 14D - Extraccion del dominio de revisiones

Sprint 14D extrajo el ciclo frontend de `RevisionSegmentacion`, persistencia de
`BORRADOR` y resultado efectivo a:

```text
apps/web/Frontend/src/composables/useSegmentationRevision.js
```

Objetivo:

- mover el estado y networking de revisiones fuera de `MainContent.vue`;
- preservar a `MainContent.vue` como orquestador entre muestra, historial,
  editor, viewport, overlay y comunicacion con `App`/`SideBar`;
- mantener separadas las responsabilidades de revision y editor.

Arquitectura despues de Sprint 14D:

```text
MainContent
   |
   |-- sample/history orchestration
   |-- DOM / pointer coordination
   |
   |-- useSegmentationViewport
   |
   |-- useSegmentationEditor
   |      |-- workingObjects
   |      |-- DRAW / VERTEX
   |      `-- Undo/Redo
   |
   |-- useSegmentationRevision
   |      |-- BORRADOR
   |      |-- VALIDADA
   |      |-- save / validate
   |      `-- effective result
   |
   `-- SegmentationOverlay
```

Ownership de `useSegmentationRevision.js`:

- `activeRevision`;
- `activeRevisionId`;
- `pendingDraftRevision`;
- `latestValidatedRevision`;
- `effectiveSegmentation`;
- `effectiveSegmentationLoading`;
- `effectiveSegmentationError`;
- `pendingDraftLoading`;
- `pendingDraftError`;
- `isSavingDraft`;
- `saveDraftError`;
- `saveDraftMessage`;
- `isValidatingRevision`;
- `validateRevisionError`;
- `validateRevisionMessage`;
- `revisionLoading`;
- `revisionError`.

Operaciones movidas:

- `loadRevisionState()` / `loadPendingDraftRevision()`;
- `loadEffectiveSegmentation()`;
- `getOrCreateDraft()`;
- `saveActiveDraft()`;
- `validateActiveRevision()`;
- `resetRevisionState()`;
- `clearEffectiveSegmentation()`;
- deteccion de `latestValidatedRevision`;
- proteccion contra respuestas stale por `resultadoId` y token de effective.

Interaccion revision -> editor:

- `useSegmentationRevision.js` no importa `useSegmentationEditor.js`;
- `MainContent.vue` coordina ambos dominios;
- al entrar a `EDIT`, `getOrCreateDraft(resultadoId)` devuelve el `BORRADOR` y
  `MainContent.vue` llama `loadWorkingRevision(draft)`;
- al guardar, `saveActiveDraft(snapshot)` devuelve la revision guardada y
  `MainContent.vue` vuelve a sincronizar el editor con `loadWorkingRevision()`;
- al validar, `validateActiveRevision(resultadoId)` devuelve la revision
  `VALIDADA`, refresca effective y revisiones, y `MainContent.vue` vuelve a
  `NAVIGATE`.

Resultado efectivo:

- sigue viniendo del backend;
- `BORRADOR` nunca se trata como resultado efectivo;
- despues de validar, el composable refresca immediately el effective result
  para que `NAVIGATE` muestre la revision validada sin `F5`.

Responsabilidades que permanecen en `MainContent.vue`:

- seleccion de muestra;
- historial de resultados de segmentacion;
- `activeResultadoSegmentacionId`;
- cambios de `viewerMode`;
- confirmacion con `window.confirm`;
- condiciones mixtas como `canValidateRevision`, porque dependen de revision
  y editor;
- llamada a `editor.loadWorkingRevision()`;
- emision de `segmentation-completed` para refrescar Resumen del Caso;
- DOM refs, pointer capture, viewport y overlay.

Manejo de errores/loading:

- se conservan estados separados para carga de revisiones, carga de effective,
  guardado y validacion;
- save error conserva `EDIT`, `workingObjects`, dirty state y Undo/Redo;
- validate con `409` refresca el estado de revision del resultado activo.

Conteo de lineas observado:

```text
MainContent.vue antes de Sprint 14D: 3280 lineas
MainContent.vue despues de Sprint 14D: 3083 lineas
useSegmentationRevision.js: 323 lineas
```

Validacion automatica ejecutada:

```powershell
npm.cmd run build
git diff --check
rg -n "console\.(log|debug|table)" apps/web/Frontend/src/components/MainContent.vue apps/web/Frontend/src/components/segmentation apps/web/Frontend/src/composables apps/web/Frontend/src/services -g "*.vue" -g "*.js"
```

Resultado:

```text
PASS
```

Nota: dentro del sandbox se reprodujo el bloqueo conocido de Vite/esbuild al
resolver `vite.config.js`; el build paso fuera del sandbox.

Checklist manual especifico:

1. Imagen A con `VALIDADA`: `NAVIGATE` muestra `VALIDADA`.
2. Imagen B sin validada: `NAVIGATE` muestra `AUTOMATICO`.
3. Entrar a `EDIT` sin `BORRADOR`: crea `BORRADOR`.
4. Entrar a `EDIT` con `BORRADOR`: reutiliza el mismo.
5. Guardar: un solo PATCH, dirty=false y geometria intacta.
6. Validar: `BORRADOR -> VALIDADA -> effective -> NAVIGATE` sin `F5`.
7. `#1 VALIDADA`, editar, crear `#2 BORRADOR`: `NAVIGATE` sigue en `#1`.
8. Guardar/validar `#2`: `NAVIGATE` muestra `#2`.
9. `F5` con `BORRADOR` guardado: se detecta revision pendiente.
10. Alternar A/B/C sin contaminar `activeRevision`, `pendingDraft`,
    `latestValidated` ni `effective`.

## Checklist Manual Pendiente

1. `NAVIGATE`: seleccionar imagenes, verificar resultado efectivo, zoom, pan, rotacion y capas.
2. `SELECT`: seleccionar membrana, nucleo anidado y eliminar objeto.
3. `DRAW`: dibujar membrana, nucleo y micronucleo; insertar, mover y eliminar puntos.
4. `VERTEX`: validar LOD, nearest vertex, INSERT, MOVE y DELETE.
5. Undo/Redo: probar crear, insertar vertice, mover vertice, eliminar vertice y eliminar objeto.
6. Persistencia: guardar BORRADOR, recargar y continuar edicion.
7. Validacion: `BORRADOR -> VALIDADA`.
8. Efectivo: confirmar que `NAVIGATE` muestra la `VALIDADA`.
