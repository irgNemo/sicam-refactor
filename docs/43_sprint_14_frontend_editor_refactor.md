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
- `mainImage`;
- `segmentationSvg`.

Esto evita exponer nodos internos desde componentes hijos y preserva `screenPointToNaturalImagePoint`.

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

- Extraer `SegmentationOverlay.vue`.
- Evaluar `useSegmentationEditor.js`.
- Evaluar `useSegmentationRevision.js`.
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

## Checklist Manual Pendiente

1. `NAVIGATE`: seleccionar imagenes, verificar resultado efectivo, zoom, pan, rotacion y capas.
2. `SELECT`: seleccionar membrana, nucleo anidado y eliminar objeto.
3. `DRAW`: dibujar membrana, nucleo y micronucleo; insertar, mover y eliminar puntos.
4. `VERTEX`: validar LOD, nearest vertex, INSERT, MOVE y DELETE.
5. Undo/Redo: probar crear, insertar vertice, mover vertice, eliminar vertice y eliminar objeto.
6. Persistencia: guardar BORRADOR, recargar y continuar edicion.
7. Validacion: `BORRADOR -> VALIDADA`.
8. Efectivo: confirmar que `NAVIGATE` muestra la `VALIDADA`.
