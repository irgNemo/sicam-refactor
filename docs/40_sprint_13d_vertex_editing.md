# Sprint 13D - Edicion de contornos mediante vertices

## Objetivo

Sprint 13D agrega edicion de contornos existentes moviendo vertices individuales de una mascara seleccionada.

Aplica a:

- `membrana`;
- `nucleo`;
- `micronucleo`;
- objetos automaticos;
- objetos manuales;
- historicos legacy con IDs editoriales unicos de `RevisionSegmentacion`.

Sprint 13D no agrega ni elimina vertices individuales.

## Herramienta VERTEX

El editor ahora tiene cuatro herramientas:

- `SELECT`: seleccionar/deseleccionar mascaras.
- `PAN`: mover el visor.
- `DRAW`: crear mascaras completas.
- `VERTEX`: editar el contorno de la mascara seleccionada.

Nombre visible:

```text
Editar contorno
```

`VERTEX` puede activarse sin objeto seleccionado, pero muestra un aviso:

```text
Seleccione una mascara para editar su contorno.
```

## Handles

Cuando `editorTool === "VERTEX"` y existe `selectedObject`, el frontend renderiza handles SVG sobre `geometry.points` del objeto seleccionado.

Los handles:

- aparecen solo para el objeto seleccionado;
- no modifican `geometry.points` al renderizarse;
- usan un circulo visible pequeno;
- usan un area de hit mayor y transparente;
- no alteran `segmentationLabelPalette`;
- se ocultan/interrumpen cuando `effectivePanMode === true`.

El objetivo es soportar contornos densos sin renderizar handles para todos los objetos simultaneamente.

## Identidad

Un vertice se identifica localmente por:

```text
objectId editorial + vertexIndex
```

No se crean IDs persistentes para vertices.

La edicion usa exclusivamente `resultado_editado.objects[].id`, nunca `provenance.base_object_id`.

## Coordenadas

La edicion reutiliza la conversion geometrica de Sprint 13C:

```text
event.clientX/clientY
-> SVG local mediante getScreenCTM().inverse()
-> coordenada natural de imagen mediante overlayContainment
-> geometry.points[vertexIndex]
```

No se guardan coordenadas CSS, viewport ni `clientX/clientY`.

La misma ruta funciona con:

- Zoom;
- Pan;
- Rotacion 90;
- Rotacion 180;
- Rotacion 270;
- combinaciones de rotacion, zoom y pan.

## Drag y Pointer Capture

El drag de vertice usa Pointer Events:

1. `pointerdown` sobre handle inicia `vertexDrag`.
2. Se guarda `objectId`, `vertexIndex`, `before`, `provenanceBefore` y `pointerId`.
3. Se llama `setPointerCapture(pointerId)` sobre el handle.
4. `pointermove` convierte la posicion a coordenada natural y actualiza solo ese punto en `workingObjects`.
5. `pointerup` registra una unica operacion `MOVE_VERTEX`.
6. `pointercancel` o `lostpointercapture` restauran el punto inicial si el gesto no finaliza normalmente.

No se registra una operacion por cada movimiento del puntero.

## Limites de imagen

Si el puntero sale fuera del area real de imagen bajo `object-fit: contain`, el editor conserva el ultimo punto valido y no introduce coordenadas fuera de imagen.

La validacion frontend evita depender del backend para este limite.

## Space y Pan

`Space` mantiene prioridad sobre la edicion de vertices:

- `VERTEX` sin `Space`: drag sobre handle mueve vertice.
- `VERTEX + Space`: el visor entra en pan temporal y no mueve vertices.

Cuando `effectivePanMode === true`, la capa de handles no captura eventos.

## Provenance

Al mover un vertice:

- si el objeto era automatico, conserva `origin = "automatic"` y `base_object_id`;
- si el objeto era manual, conserva `origin = "manual"` y `base_object_id = null`;
- se agrega `modified = true` en `provenance`.

No se convierte un objeto automatico en manual.

## Undo/Redo

Se agrego la operacion:

```text
MOVE_VERTEX
```

La operacion guarda:

- `objectId`;
- `vertexIndex`;
- `before`;
- `after`;
- `provenanceBefore`;
- `provenanceAfter`.

Undo restaura el punto y provenance previos.

Redo reaplica el punto y provenance posteriores.

Una nueva operacion despues de Undo limpia `redoStack`, igual que en Sprint 13C.

## Dirty State

Mover un vertice marca `isDraftDirty = true`.

Undo/Redo actualizan el dirty state contra el ultimo snapshot guardado.

Guardar sigue siendo explicito mediante `Guardar borrador`.

## Persistencia

Sprint 13D reutiliza el flujo de Sprint 13C:

```text
PATCH /api/revisiones-segmentacion/{id}/
```

El payload sigue enviando `resultado_editado` con `workingObjects`.

Despues de guardar:

- `activeRevision` se actualiza con la respuesta;
- `workingObjects` se sincroniza;
- `isDraftDirty = false`;
- Undo/Redo se limpian;
- `EDIT` permanece activo.

## Legacy 1.0

Los objetos legacy ya llegan al BORRADOR con IDs editoriales unicos.

La edicion de vertices opera sobre ese ID editorial. Si dos objetos tienen `provenance.base_object_id = 255`, mover un vertice de uno no modifica el otro.

## Rendimiento de contornos densos

Sprint 13D no simplifica ni reduce `geometry.points`.

Primera estrategia:

- renderizar handles solo para el objeto seleccionado;
- mantener handles pequenos;
- usar area de hit transparente mayor que el circulo visible.

La evaluacion de rendimiento debe hacerse manualmente sobre una membrana con contorno denso. No se aplico Douglas-Peucker ni otra simplificacion.

## Reorganizacion de toolbar y limpieza de controles legacy

Despues de la primera implementacion de Sprint 13D se detecto que los controles:

```text
Navegar
Editar
Revision #N - BORRADOR
Seleccionar
Mover
Dibujar
Editar contorno
```

quedaban en una sola fila visual. En viewports de laptop esto amontonaba los botones, hacia que `Editar contorno` quedara parcialmente fuera del area accesible e invadia visualmente el panel de `Resumen de Conteo`.

El hotfix reorganizo la toolbar en dos niveles:

- Fila 1: modo del visor y estado de revision.
- Fila 2: herramientas de interaccion sobre la imagen.

Fila 1:

```text
Navegar | Editar | Revision #N - BORRADOR | Cambios sin guardar
```

Fila 2, visible solo en modo `EDIT`:

```text
Seleccionar | Mover | Dibujar | Editar contorno
```

La fila de herramientas pertenece al area del visor, usa `flex-wrap` y no se extiende como una unica barra horizontal hacia `Resumen de Conteo`.

Tambien se auditaron controles legacy visibles:

- Icono de lapiz: placeholder sin handler real; eliminado porque el flujo actual usa `Editar` y `Editar contorno`.
- Icono de brocha/limpiar: placeholder sin handler real; eliminado porque no representa una accion implementada.
- Icono de papelera superior: placeholder sin handler real; eliminado porque la accion real es `Eliminar mascara` en `Objeto seleccionado`.
- Icono de check verde: placeholder sin handler real; eliminado. La validacion experta queda reservada para un sprint futuro con un control explicito.
- `Marcar para revision manual`: placeholder sin handler real; eliminado para evitar un camino duplicado con el editor experto.
- `Marcar revision`: placeholder sin handler real dentro de `Capas visibles`; eliminado.
- `Exportar Datos`: placeholder sin handler real dentro de `Capas visibles`; eliminado.

Controles preservados:

- `Exportar CSV` y `Generar PDF` en el encabezado global, porque son funcionalidades de producto previstas.
- `Eliminar mascara` en `Objeto seleccionado`, por ser una accion contextual real.
- `Deshacer`, `Rehacer` y `Guardar borrador`, por pertenecer al panel contextual de revision.
- `Zoom`, `Zoom Out`, `Rotar` y `Ajustar`, por ser controles funcionales del visor.
- `Capas visibles`, como unico control canonico de visibilidad por etiqueta.

No se modifico la logica geometrica del editor:

- `screenPointToNaturalImagePoint`;
- `geometry.points`;
- handles;
- pointer capture;
- `effectivePanMode`;
- Zoom/Pan/Rotar/Ajustar;
- `DRAW`;
- `CREATE_OBJECT`;
- `DELETE_OBJECT`;
- `MOVE_VERTEX`;
- Undo/Redo;
- guardado de BORRADOR.

## Zoom extendido y edicion fina de mascara en construccion

Sprint 13D-B amplio la precision del editor de dibujo antes de cerrar Sprint 13D.

### Zoom

El visor usa constantes frontend:

```text
ZOOM_MIN = 1
ZOOM_MAX = 5
ZOOM_STEP = 0.25
```

Equivalen a:

- minimo: 100%;
- maximo: 500%;
- paso: 25%.

`Zoom In` aplica:

```text
min(current + step, 5)
```

`Zoom Out` aplica:

```text
max(current - step, 1)
```

`Ajustar` conserva el comportamiento esperado:

```text
zoom = 1
rotation = 0
pan = 0
```

El algoritmo de pan no se reemplazo. Se reutiliza el clamp existente basado en el tamano renderizado, rotacion y zoom, ahora tambien hasta 500%.

### Puntos de mascara en construccion

Durante `DRAW`, `draftPolygonPoints` ahora tiene estado local de seleccion:

```text
selectedDraftPointIndex
```

Este estado aplica solo a la mascara temporal en construccion. No se mezcla con:

```text
selectedObjectKey
```

porque `selectedObjectKey` identifica mascaras ya creadas en `workingObjects`.

Cada punto temporal se representa con:

- un circulo visible;
- un area de hit transparente mayor;
- highlight discreto cuando esta seleccionado.

El tamano visible y el hit-area se compensan contra `imageZoom` para mantenerse usables entre 100% y 500%.

### Mover puntos temporales

Pointer down sobre un punto existente en `DRAW`:

1. selecciona `selectedDraftPointIndex`;
2. inicia `draftPointDrag`;
3. usa `setPointerCapture`;
4. actualiza solo `draftPolygonPoints[index]` en tiempo real;
5. guarda coordenadas naturales de imagen mediante `screenPointToNaturalImagePoint`.

Mover un punto temporal no modifica `workingObjects`, no genera `MOVE_VERTEX` y no entra al `undoStack`.

La razon es que la mascara aun no existe como objeto persistible. Solo al pulsar `Finalizar mascara` se crea `CREATE_OBJECT`.

### Eliminar punto temporal

Cuando existe `selectedDraftPointIndex`, el panel de dibujo muestra:

```text
Eliminar punto
```

Al pulsarlo:

- elimina exactamente ese punto de `draftPolygonPoints`;
- limpia `selectedDraftPointIndex`;
- actualiza el preview inmediatamente.

Tambien se soporta `Delete` o `Backspace` en `DRAW`, siempre que el foco no este dentro de `input`, `textarea`, `select` o contenido editable.

Eliminar puntos temporales puede dejar la mascara con 0, 1 o 2 puntos. `Finalizar mascara` sigue requiriendo 3 o mas puntos.

### Insertar punto en segmento

El preview visible se usa como fuente del hit-testing:

- segmentos `p0 -> p1`, `p1 -> p2`, etc.;
- segmento de cierre `ultimo -> primero` solo cuando el `polygon` ya es visible, es decir con 3 o mas puntos.

Click suficientemente cerca de un segmento visible:

```text
A -- B -- C
```

inserta un punto entre los extremos:

```text
A -- NEW -- B -- C
```

Para el segmento de cierre:

```text
C -- A
```

el punto se inserta al final del arreglo, preservando la topologia visual:

```text
A -- B -- C -- NEW -- A
```

El hit-testing usa tolerancia en pixeles de pantalla:

```text
SEGMENT_HIT_TOLERANCE_PX = 8
```

La distancia se calcula proyectando el punto del evento sobre el segmento en coordenadas de pantalla. El punto insertado se proyecta de regreso al SVG y luego a coordenadas naturales de imagen.

### Prioridad de eventos en DRAW

La prioridad queda:

1. `effectivePanMode`;
2. handle de punto existente;
3. segmento visible;
4. espacio libre.

`Space` conserva prioridad absoluta:

- `Space + drag` sobre handle: pan;
- `Space + drag` sobre segmento: pan;
- `Space + drag` sobre fondo: pan.

No se modifican `draftPolygonPoints` durante pan temporal.

### Prevencion de puntos accidentales

Los handles y segmentos usan `pointerdown` con `stopPropagation` y `pointer capture`.

Tambien cortan el `click` asociado, para evitar:

```text
mover punto + agregar punto extra
insertar punto + agregar punto extra
```

Click en espacio libre conserva el comportamiento anterior: agrega un punto al final.

### Rotacion y limites

La edicion fina reutiliza:

- `screenPointToSvgPoint`;
- `svgPointToNaturalImagePoint`;
- `overlayContainment`;
- `screenPointToNaturalImagePoint`.

Por eso funciona con:

- 0 grados;
- 90 grados;
- 180 grados;
- 270 grados;
- Zoom;
- Pan;
- combinaciones de Zoom, Pan y Rotacion.

Los puntos siguen rechazandose si caen fuera del area real de imagen bajo `object-fit: contain`, incluyendo letterboxing.

### DRAW vs VERTEX

`DRAW`:

- edita puntos temporales de `draftPolygonPoints`;
- permite seleccionar, mover, eliminar e insertar puntos antes de finalizar;
- no usa Undo/Redo global para esos cambios temporales.

`VERTEX`:

- edita vertices de mascaras ya creadas en `workingObjects`;
- genera operaciones `MOVE_VERTEX`;
- participa en Undo/Redo;
- persiste mediante `Guardar borrador`.

Sprint 13D-B no agrega insertar/eliminar vertices en mascaras finalizadas.

## Sprint 13D-C - Precision visual, UI contextual y contornos densos

Sprint 13D-C mejora la precision visual del editor experto sin modificar backend, API, `RevisionSegmentacion`, normalizador ni microservicios.

### Zoom 100-800%

El visor usa:

```text
ZOOM_MIN = 1
ZOOM_MAX = 8
ZOOM_STEP = 0.25
```

Equivale a:

- minimo: 100%;
- maximo: 800%;
- paso: 25%.

`Ajustar` conserva su semantica:

```text
zoom = 1
rotation = 0
panX = 0
panY = 0
```

El pan reutiliza el mismo clamp de Sprint 13D-B, basado en tamano renderizado, zoom y rotacion. No se agrego un segundo motor de navegacion.

### Tamano visual vs hit-area

Los handles de `DRAW` y `VERTEX` separan:

- circulo visible;
- hit-area transparente.

Constantes frontend:

```text
HANDLE_VISIBLE_RADIUS_PX = 3
HANDLE_SELECTED_RADIUS_PX = 4.25
HANDLE_HIT_RADIUS_PX = 8
```

El radio SVG se compensa contra `imageZoom`, por lo que el tamano en pantalla permanece aproximadamente estable entre 100% y 800%.

En `DRAW` se siguen mostrando todos los puntos de `draftPolygonPoints`; no se aplica LOD a mascaras en construccion.

### UI contextual

El panel contextual ahora depende de:

```text
viewerMode + editorTool + estado local
```

Matriz:

| Modo | Herramienta | Controles visibles |
| --- | --- | --- |
| `NAVIGATE` | N/A | navegacion, zoom, rotacion, capas, conteos e indicador de revision pendiente |
| `EDIT` | `SELECT` | objeto seleccionado, `Eliminar mascara` si hay seleccion, `Deshacer`, `Rehacer`, `Guardar borrador` |
| `EDIT` | `PAN` | mensaje compacto de navegacion; sin acciones grandes de edicion |
| `EDIT` | `DRAW` | tipo de estructura, puntos temporales, `Finalizar mascara`, `Cancelar`, `Eliminar punto` si aplica |
| `EDIT` | `VERTEX` | objeto seleccionado, vertice seleccionado si aplica, `Eliminar mascara`, `Deshacer`, `Rehacer`, `Guardar borrador` |

Durante `DRAW`, `Guardar borrador` no se muestra porque `draftPolygonPoints` aun no pertenece a `workingObjects`. Para persistir, primero se debe finalizar la mascara y crear `CREATE_OBJECT`.

### Level of Detail visual para VERTEX

El Level of Detail afecta unicamente la representacion de handles. No simplifica ni modifica la geometria de la mascara.

El poligono SVG se sigue dibujando con todos los puntos de:

```text
geometry.points
```

Si una mascara tiene 900 puntos, conserva 900 puntos en:

- `workingObjects`;
- `resultado_editado`;
- payload `PATCH`;
- `RevisionSegmentacion`.

El LOD solo decide que handles se renderizan.

### Algoritmo LOD

Se usa un algoritmo determinista en screen space:

```text
MIN_VERTEX_HANDLE_SPACING_PX = 12
```

Para cada vertice:

1. se convierte el punto natural a SVG con `scalePoint`;
2. se convierte a coordenadas de pantalla con `svgArrayPointToScreenPoint`;
3. se asigna a una celda de grid de 12 px;
4. se revisa la celda y vecindad inmediata;
5. si no hay otro handle demasiado cercano, se renderiza.

Esto es O(n) con grid espacial y depende de la transformacion visual actual. Al aumentar zoom, aparecen mas handles disponibles.

### Vertice seleccionado y vecinos

Se agrego estado frontend:

```text
selectedVertexIndex
```

Es independiente de:

```text
selectedObjectKey
```

Cuando hay `selectedVertexIndex`, ese vertice siempre se renderiza aunque el LOD general lo hubiera ocultado.

Tambien se fuerzan vecinos locales:

```text
VERTEX_NEIGHBOR_RADIUS = 3
```

Para un indice `100`, se muestran siempre:

```text
97, 98, 99, 100, 101, 102, 103
```

con wrap cuando el poligono lo requiere.

### Nearest vertex desde contorno

En `VERTEX`, click sobre/cerca del contorno de una mascara permite seleccionar el vertice real mas cercano, aunque su handle estuviera oculto por LOD.

Tolerancia:

```text
NEAREST_VERTEX_HIT_PX = 12
```

Flujo:

1. click sobre poligono;
2. se evalua `geometry.points` completo del objeto;
3. cada punto se proyecta a screen space;
4. se elige el vertice mas cercano si esta dentro de 12 px;
5. `selectedVertexIndex` queda activo;
6. se muestran el handle seleccionado y vecinos locales.

No se insertan vertices ni se altera geometria.

### Space/Pan

`Space` mantiene prioridad absoluta:

- `Space + drag` sobre handle: pan;
- `Space + drag` sobre contorno sin handle: pan;
- `Space + drag` sobre fondo: pan.

No se seleccionan ni mueven vertices durante pan temporal.

### MOVE_VERTEX

Mover un handle visible por LOD usa la misma operacion existente:

```text
MOVE_VERTEX
```

La identidad sigue siendo:

```text
objectId editorial + vertexIndex original
```

No se usa `provenance.base_object_id` para ubicar objetos editables.

### Limitaciones

Sprint 13D-C no implementa:

- agregar vertices a mascaras ya finalizadas;
- eliminar vertices de mascaras ya finalizadas;
- simplificacion persistida;
- suavizado;
- mover poligono completo;
- validacion topologica;
- validar revision;
- resultado efectivo.

## Hotfix Sprint 13D-C2 - Precision de contornos y dibujo independiente del orden

Durante pruebas reales a 800% se detecto que los strokes y handles del overlay ocupaban demasiado espacio visual. La causa fue que imagen y SVG se transforman juntos dentro de `image-transform-layer` mediante `scale(...)`; por lo tanto, un `stroke-width` fijo de SVG tambien se multiplicaba por el zoom.

El hotfix separa:

- geometria cientifica: `geometry.points`;
- representacion visual: strokes, opacidad y circulos visibles;
- area de interaccion: hit-areas transparentes.

No se modifican `geometry.points`, IDs, provenance, backend, persistencia ni microservicios.

### Stroke constante en pantalla

Los strokes principales ahora se compensan contra `imageZoom`.

Valores objetivo:

```text
OVERLAY_STROKE_PX = 1.5
SELECTED_OVERLAY_STROKE_PX = 2
DRAFT_STROKE_PX = 1.25
```

El valor SVG aplicado es:

```text
strokeWidth = targetPx / imageZoom
```

Asi, a 800% el contorno no se convierte en un bloque grueso. `vector-effect: non-scaling-stroke` se conserva como apoyo, pero la compensacion explicita cubre el escalado por CSS del wrapper.

### Handles finales

`DRAW`:

```text
DRAW_HANDLE_VISIBLE_RADIUS_PX = 2
DRAW_HANDLE_SELECTED_RADIUS_PX = 3
DRAW_HANDLE_HIT_RADIUS_PX = 8
DRAW_HANDLE_STROKE_PX = 1
DRAW_SELECTED_HANDLE_STROKE_PX = 1.25
```

`VERTEX`:

```text
VERTEX_HANDLE_VISIBLE_RADIUS_PX = 2.25
VERTEX_HANDLE_SELECTED_RADIUS_PX = 3.25
VERTEX_HANDLE_HIT_RADIUS_PX = 8
VERTEX_HANDLE_STROKE_PX = 1.1
VERTEX_SELECTED_HANDLE_STROKE_PX = 1.25
```

Los circulos visibles son pequenos. Las hit-areas transparentes se mantienen comodas.

### Fill-opacity por contexto

Se mantiene `segmentationLabelPalette` sin cambios, pero el alpha del fill se ajusta en render:

```text
NAVIGATE = 0.16
EDIT SELECT = 0.14
EDIT VERTEX = 0.09
EDIT DRAW = 0.06
DRAFT preview = 0.06
```

Durante `DRAW`, las mascaras existentes quedan como referencia visual ligera.

### Pointer-events por herramienta

Reglas finales:

- `SELECT`: los poligonos existentes siguen siendo interactivos.
- `PAN` o `Space`: los poligonos, handles y capas editoriales no bloquean el pan.
- `DRAW`: las mascaras existentes no interceptan la interaccion durante DRAW.
- `VERTEX`: solo el poligono seleccionado participa en nearest-vertex; los demas quedan como referencia visual.

Esto corrige el caso donde una membrana ya creada bloqueaba el dibujo de un nucleo o micronucleo dentro de ella.

### DRAW independiente del orden

El orden de creacion de membrana, nucleo y micronucleo no condiciona la posibilidad de dibujar estructuras anidadas.

Son validos:

```text
membrana -> nucleo -> micronucleo
micronucleo -> nucleo -> membrana
cualquier otro orden
```

En `DRAW`, las mascaras existentes no participan en hit-testing. La prioridad sigue siendo:

1. `effectivePanMode` / `Space`;
2. handle de `draftPolygonPoint`;
3. segmento del draft actual;
4. area libre de imagen;
5. mascaras existentes solo como referencia visual.

Click dentro de una membrana existente agrega puntos del nuevo nucleo/micronucleo si el punto cae dentro del area real de imagen.

### Z-order semantico

El render visual ordena los poligonos por etiqueta:

```text
1. membrana
2. nucleo
3. micronucleo
4. highlight/seleccion
5. DRAW preview
6. handles
```

Esto es solo orden SVG. No cambia:

- orden de `workingObjects`;
- IDs editoriales;
- provenance;
- payload `PATCH`;
- orden persistido en `resultado_editado`.

La identidad sigue usando `selectionKey` e ID editorial, no el indice visual renderizado.

### Regresiones a validar

- `membrana -> nucleo -> micronucleo` a 800%.
- orden inverso `micronucleo -> nucleo -> membrana`.
- `SELECT` despues de dibujar estructuras anidadas.
- `VERTEX` en cada estructura anidada.
- `PAN` y `Space + drag` sobre mascaras existentes, draft handles, segmentos y fondo.
- grosor visual a 100%, 200%, 400% y 800%.

## Hotfix Sprint 13D-C3 - Insercion/eliminacion de vertices en contornos finalizados

Sprint 13D-C3 audita el hit-area y extiende `VERTEX` para agregar y eliminar vertices en mascaras ya finalizadas.

No modifica:

- backend;
- API;
- modelos;
- migraciones;
- `RevisionSegmentacion`;
- `resultado_normalizado`;
- `respuesta_json`;
- microservicios.

Los cambios siguen afectando solo `workingObjects` y se persisten mediante el `PATCH` existente de BORRADOR al pulsar `Guardar borrador`.

### Auditoria de hit-area

El SVG esta dentro de `image-transform-layer`, que aplica:

```text
transform: scale(imageZoom)
```

Por eso los radios SVG deben compensarse con:

```text
effectiveSvgRadius = TARGET_SCREEN_RADIUS_PX / imageZoom
```

Formulas finales:

```text
DRAW visible = DRAW_HANDLE_VISIBLE_RADIUS_PX / imageZoom
DRAW selected = DRAW_HANDLE_SELECTED_RADIUS_PX / imageZoom
DRAW hit-area = DRAW_HANDLE_HIT_RADIUS_PX / imageZoom
VERTEX visible = VERTEX_HANDLE_VISIBLE_RADIUS_PX / imageZoom
VERTEX selected = VERTEX_HANDLE_SELECTED_RADIUS_PX / imageZoom
VERTEX hit-area = VERTEX_HANDLE_HIT_RADIUS_PX / imageZoom
```

Valores objetivo:

```text
DRAW_HANDLE_VISIBLE_RADIUS_PX = 2
DRAW_HANDLE_SELECTED_RADIUS_PX = 3
DRAW_HANDLE_HIT_RADIUS_PX = 8
VERTEX_HANDLE_VISIBLE_RADIUS_PX = 2.25
VERTEX_HANDLE_SELECTED_RADIUS_PX = 3.25
VERTEX_HANDLE_HIT_RADIUS_PX = 8
```

Con esta formula, a 100%, 200%, 400% y 800% el hit-area se mantiene aproximadamente en 8 px de pantalla.

### Submodo de Editar contorno

Dentro de:

```text
editorTool === "VERTEX"
```

se agrega:

```text
vertexEditMode
```

Valores:

- `MOVE`;
- `INSERT`.

Default:

```text
MOVE
```

UI:

```text
Mover puntos | Agregar punto
```

No es una herramienta nueva en la toolbar superior. Es un submodo contextual de `Editar contorno`.

### VERTEX + MOVE

`MOVE` conserva el comportamiento previo:

- LOD de handles;
- `selectedVertexIndex`;
- nearest-vertex;
- vecinos locales;
- drag de handle;
- `MOVE_VERTEX`;
- Undo/Redo;
- `Space` / pan temporal.

### VERTEX + INSERT

En `INSERT`, click sobre un segmento del objeto seleccionado inserta un vertice entre sus endpoints.

Algoritmo:

1. se construyen segmentos del objeto seleccionado usando todos sus `geometry.points`;
2. se proyectan endpoints a SVG/screen space;
3. se mide distancia del click al segmento en pixeles de pantalla;
4. si esta dentro de:

```text
VERTEX_SEGMENT_HIT_TOLERANCE_PX = 8
```

5. se proyecta el punto sobre el segmento;
6. se convierte el punto proyectado a coordenadas naturales;
7. se inserta en `geometry.points`.

Para un segmento:

```text
A, B, C
```

click sobre `A-B` produce:

```text
A, NEW, B, C
```

En segmento de cierre `ultimo -> primero`, el punto se agrega al final del arreglo:

```text
p0 ... pn NEW
```

Esto conserva la representacion cerrada del poligono, porque el ultimo punto vuelve a conectar con `p0`.

Despues de insertar:

- `selectedVertexIndex` apunta al nuevo vertice;
- se muestran handle seleccionado y vecinos;
- el modo permanece en `INSERT`.

### DELETE_VERTEX

Cuando existe `selectedVertexIndex`, el panel `Editar contorno` muestra:

```text
Eliminar punto
```

No se confunde con:

```text
Eliminar mascara
```

El boton se deshabilita si el objeto tiene 3 puntos o menos.

Regla:

```text
geometry.points.length >= 3
```

nunca se rompe. No se crea un poligono de 2 puntos.

Tambien se permite `Delete` o `Backspace` en `VERTEX`, siempre que el foco no este dentro de `input`, `textarea`, `select` o contenido editable.

### Operaciones Undo/Redo

Se agregan operaciones:

```text
INSERT_VERTEX
DELETE_VERTEX
```

Cada una guarda:

- `objectId` editorial;
- `vertexIndex`;
- `point`;
- `beforePoints`;
- `afterPoints`;
- `provenanceBefore`;
- `provenanceAfter`;
- `selectedVertexIndexBefore`;
- `selectedVertexIndexAfter`.

Se usan snapshots minimos de `geometry.points` del objeto porque los indices cambian despues de insertar/eliminar. No se busca por coordenadas.

Undo/Redo:

- `INSERT_VERTEX` undo restaura `beforePoints`; redo restaura `afterPoints`.
- `DELETE_VERTEX` undo restaura `beforePoints`; redo restaura `afterPoints`.
- `MOVE_VERTEX` sigue funcionando igual.

Una nueva operacion despues de Undo limpia `redoStack`, igual que el resto del editor.

### Provenance

Al insertar o eliminar vertices:

- `origin` se conserva;
- `base_object_id` se conserva;
- `raw_id` y `raw_type`, si existen, se conservan;
- se agrega o mantiene `modified = true`.

No se convierte `automatic` en `manual`.

### LOD tras insertar/eliminar

Despues de `INSERT_VERTEX` o `DELETE_VERTEX`, el LOD se recalcula desde `geometry.points` actual.

El LOD sigue siendo solo visual:

```text
No simplifica ni modifica la geometria de la mascara.
```

`selectedVertexIndex` se mantiene valido:

- tras insertar, apunta al nuevo vertice;
- tras eliminar, apunta a un vecino valido.

### Persistencia

El flujo no cambia:

```text
Editar contorno
-> INSERT_VERTEX / DELETE_VERTEX / MOVE_VERTEX
-> workingObjects
-> Guardar borrador
-> PATCH /api/revisiones-segmentacion/{id}/
```

El resultado automatico permanece inmutable.

### Pruebas manuales de C3

1. Confirmar matematicamente que DRAW y VERTEX hit-area usan `target / imageZoom`.
2. Insertar vertice en mascara finalizada: `N -> N+1`.
3. Undo de insert: `N`.
4. Redo de insert: `N+1`.
5. Eliminar vertice: `N -> N-1`.
6. Undo de delete: `N`.
7. Redo de delete: `N-1`.
8. Confirmar que con 3 puntos `Eliminar punto` esta deshabilitado.
9. Probar secuencia mixta: Insertar, Mover, Insertar, Eliminar, Undo completo, Redo completo.
10. Probar a 800% con 90, 180 y 270 grados.
11. Confirmar que objetos legacy con `base_object_id = 255` siguen independientes porque se usa ID editorial.

## Limitaciones topologicas

Sprint 13D no valida topologia avanzada.

Puede permitir:

- segmentos cruzados;
- auto-intersecciones;
- areas casi cero.

El backend valida estructura JSON, labels, IDs y puntos finitos, pero no geometria clinica/topologica avanzada.

## Validacion automatica

Comando:

```powershell
npm.cmd run build
```

Resultado:

```text
PASS
```

Nota: dentro del sandbox fallo por el problema conocido de Vite/esbuild al resolver `vite.config.js`; se valido fuera del sandbox.

## Checklist manual pendiente

### Basico

1. Seleccionar nucleo automatico.
2. Activar `Editar contorno`.
3. Mover un vertice.
4. Confirmar que solo ese vertice cambia.
5. Confirmar `origin = automatic`, `base_object_id` intacto y `modified = true`.
6. Confirmar dirty state.
7. Confirmar conteos sin cambios.

### Manual

1. Crear mascara manual.
2. Seleccionarla.
3. Activar `Editar contorno`.
4. Mover un vertice.
5. Confirmar `origin = manual` y geometria actualizada.

### Geometria critica

Mover vertices en:

- sin Zoom;
- Zoom 2x;
- Zoom + Pan;
- Rotar 90;
- Rotar 180;
- Rotar 270;
- Rotar + Zoom + Pan.

Prueba critica:

```text
Rotar 90
-> Zoom 2x
-> Pan
-> mover vertice
-> Guardar
-> Ajustar
-> confirmar posicion esperada
```

### Space + Pan

En `VERTEX`, con Zoom 2x:

- Space + drag desde fondo: pan.
- Space + drag desde polygon: pan.
- Space + drag desde handle: pan.
- Soltar Space y drag sobre handle: mueve vertice.

### Undo/Redo

1. Mover vertice A -> B.
2. Undo: vuelve a A.
3. Redo: vuelve a B.
4. Undo y luego nueva operacion: redo queda vacio.
5. Confirmar provenance restaurado.

### Persistencia

1. Mover al menos dos vertices.
2. Guardar borrador.
3. Recargar.
4. Continuar edicion.
5. Confirmar posiciones, handles y provenance.
6. Confirmar automatico original intacto en `NAVIGATE`.

### Legacy 1.0

1. Seleccionar dos objetos distintos con `provenance.base_object_id = 255`.
2. Mover un vertice del primero.
3. Confirmar que el segundo no cambia.
4. Guardar y recargar.
5. Confirmar separacion por ID editorial.

### Rendimiento

Probar una membrana densa y registrar:

- numero aproximado de puntos;
- fluidez al entrar en `VERTEX`;
- fluidez durante drag;
- lag perceptible de SVG, si existe.
