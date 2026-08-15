# Sprint 13B - Modo editor y seleccion de mascaras SVG

## Fecha

2026-08-14 14:23:16 -06:00

## Referencia Git

- Rama: `master`
- Commit: `a98afeb`

## Objetivo

Agregar en el frontend un modo editor minimo para consultar o crear un `RevisionSegmentacion` en estado `BORRADOR`, renderizar sus objetos editables sobre el overlay SVG y permitir seleccionar mascaras sin modificar geometria.

Este sprint no implementa guardado de cambios, validacion experta, creacion/eliminacion de mascaras, edicion de puntos, undo/redo ni cambios de backend.

## Archivos modificados

- `apps/web/Frontend/src/components/MainContent.vue`
- `apps/web/Frontend/src/services/segmentationRevisionService.js`

## Servicio frontend creado

Se agrego `src/services/segmentationRevisionService.js` con funciones para consumir los endpoints Django de revisiones:

- `getSegmentationRevisions(resultadoId)`
- `getOrCreateSegmentationDraft(resultadoId)`
- `getSegmentationRevision(revisionId)`

En Sprint 13B la UI usa `getOrCreateSegmentationDraft(resultadoId)` para solicitar el `BORRADOR` activo del resultado de segmentacion seleccionado.

## Estado agregado en frontend

`MainContent.vue` ahora mantiene estado minimo de editor:

- `viewerMode`: `NAVIGATE` o `EDIT`.
- `activeRevision`: borrador experto cargado desde Django.
- `activeRevisionId`: identificador del borrador.
- `revisionLoading`: estado de carga del borrador.
- `revisionError`: error al entrar en modo editor.
- `selectedObjectKey`: clave local defensiva para seleccionar objetos aunque `object.id` no sea unico.
- `isSpacePressed`: permite pan temporal en modo editor.
- `editorTool`: herramienta activa del editor, `SELECT` o `PAN`.

## Resultado activo

El resultado de segmentacion activo se determina desde:

1. `ultimoResultadoSegmentacion`, si existe historial persistido.
2. `segmentacionResultado`, si acaba de ejecutarse segmentacion y todavia no hay historial cargado.

El identificador usado para pedir el borrador se obtiene de:

- `resultadoSegmentacionActivo.id`, para resultados historicos.
- `resultadoSegmentacionActivo.resultado_segmentacion.id`, para respuestas inmediatas del endpoint `POST /api/muestras/{id}/segmentar/`.

## Fuente del overlay

La fuente de objetos del overlay depende del modo:

- `NAVIGATE`: usa `resultadoNormalizadoActivo.objects`.
- `EDIT`: usa `activeRevision.resultado_editado.objects`.

El resumen de conteo tambien cambia de fuente:

- En `EDIT`, prefiere `activeRevision.resumen`.
- Fuera de `EDIT`, usa `resultadoNormalizadoActivo.summary`.

## Carga y reutilizacion de BORRADOR

Al presionar `Editar`:

1. Se valida que exista un `ResultadoSegmentacion` activo.
2. Se llama `POST /api/resultados-segmentacion/{id}/revisiones/`.
3. Django devuelve el `BORRADOR` existente o crea uno nuevo.
4. El frontend guarda la respuesta en `activeRevision`.
5. El overlay cambia a los objetos de `resultado_editado`.

Si el `BORRADOR` ya esta cargado y pertenece al mismo resultado, se reutiliza en memoria y no se hace una nueva llamada.

Al cambiar de muestra o de resultado activo, el modo vuelve a `NAVIGATE`, se limpia la seleccion y se descarta la revision activa local.

## Seleccion SVG

En modo `EDIT`, cada `<polygon>` del overlay:

- Recibe eventos de seleccion.
- Usa una `selectionKey` local que combina indice, id y label.
- No depende unicamente de `object.id`, para mantener compatibilidad con historicos `version 1.0` donde puede haber IDs repetidos.
- Muestra el objeto seleccionado con estilo visual destacado.

El panel `Objeto seleccionado` muestra:

- Tipo.
- ID interno del objeto.
- Origen (`automatic` o `manual`).
- ID base cuando existe `provenance.base_object_id`.

## Pan, zoom y rotacion

El modo `NAVIGATE` mantiene el comportamiento existente:

- Zoom In.
- Zoom Out.
- Rotar.
- Ajustar.
- Pan cuando `imageZoom > 1`.

En modo `EDIT`:

- Click sobre un poligono selecciona mascara.
- El pan normal queda deshabilitado para evitar conflicto con seleccion.
- `Space` habilita pan temporal.
- Imagen y SVG siguen dentro del mismo `image-transform-layer`, por lo que zoom, rotacion y pan se aplican conjuntamente.

## Compatibilidad

El editor es compatible con:

- Resultados normalizados `version 1.1`.
- Historicos `version 1.0` con IDs potencialmente duplicados.

La visibilidad por etiqueta sigue dependiendo de `label`, no de `object.id`.

Tras el hotfix de compatibilidad legacy de Sprint 13A, los resultados normalizados historicos `version 1.0` con IDs duplicados pueden abrir un `BORRADOR` sin re-segmentar. El backend asigna IDs editoriales unicos en `resultado_editado.objects[].id` y conserva el ID automatico original en `provenance.base_object_id`.

## Validacion ejecutada

### Build frontend

Comando:

```powershell
npm.cmd run build
```

Resultado:

```text
PASS
```

Notas:

- El primer intento dentro del sandbox fallo por el problema conocido de Vite/esbuild al resolver `vite.config.js`.
- El build se repitio fuera del sandbox y finalizo correctamente.
- Vite transformo 72 modulos y genero `dist/`.
- PowerShell mostro una advertencia local de `Execution_Policies` al cargar el perfil, despues del build exitoso.

## Checklist manual pendiente

1. Levantar backend Django.
2. Levantar frontend Vue/Vite.
3. Seleccionar una muestra con `ResultadoSegmentacion` persistido.
4. Confirmar que el visor inicia en modo `Navegar`.
5. Confirmar que `Zoom`, `Zoom Out`, `Rotar` y `Ajustar` siguen funcionando.
6. Presionar `Editar`.
7. Confirmar que se carga o reutiliza un `BORRADOR`.
8. Confirmar que aparece `Revision #N - BORRADOR`.
9. Confirmar que el overlay se mantiene visible.
10. Hacer click en una mascara SVG y confirmar que se resalta.
11. Confirmar que el panel `Objeto seleccionado` muestra tipo, ID y procedencia.
12. Confirmar que las capas visibles siguen ocultando/mostrando etiquetas.
13. Confirmar que en modo editor no se hace pan accidental al seleccionar.
14. Mantener `Space` y arrastrar para confirmar pan temporal.
15. Cambiar de muestra y confirmar que vuelve a `Navegar` y limpia seleccion/revision activa.

## Hotfix - seleccion SVG, pan temporal y solapamiento

Despues de la validacion manual de Sprint 13B se corrigieron tres defectos de interaccion:

1. Una mascara seleccionada no podia deseleccionarse con un segundo click.
2. En modo `EDIT`, `Space + drag` podia no iniciar pan cuando el gesto empezaba sobre un poligono SVG.
3. El poligono seleccionado se renderizaba arriba como el mismo elemento interactivo, por lo que el highlight podia bloquear la seleccion inmediata de estructuras interiores o anidadas.

### Causas raiz

- La seleccion asignaba siempre `selectedObjectKey = selectionKey`; no existia toggle.
- El pan temporal dependia de que el `pointerdown` burbujeara desde el SVG/poligono hasta el wrapper.
- `overlayPolygons()` reordenaba el poligono seleccionado para dibujarlo encima, y ese mismo poligono seguia capturando eventos.
- No habia una separacion explicita entre click y drag.

### Cambios aplicados

- Se mantuvo una identidad defensiva unica con `overlayObjectKey(object, index)`.
- La misma identidad se usa para `:key`, seleccion, comparacion de seleccionado, highlight y panel `Objeto seleccionado`.
- La seleccion ahora es tipo toggle:
  - click A selecciona A.
  - click A otra vez limpia seleccion.
  - click B cambia seleccion a B.
- El SVG se separo en dos capas:
  - `segmentation-polygons`: poligonos interactivos en orden estable.
  - `selection-highlight`: highlight visual del seleccionado con `pointer-events="none"`.
- El highlight ya no bloquea clicks hacia estructuras interiores.
- `pointerdown` del wrapper se escucha en fase capture para dar prioridad a navegacion temporal con `Space`.
- El pan usa `setPointerCapture()` y libera captura al terminar.
- Se agrego umbral de drag de `5px`.
- Si el movimiento supera el umbral, no se genera seleccion accidental por el click posterior.
- `Space` en modo `EDIT` activa navegacion temporal y no selecciona poligonos.
- `keyup` y `window.blur` limpian `isSpacePressed` y finalizan pan activo.

### Limitacion residual

Si dos poligonos interactivos reales se solapan de forma exacta, el SVG seguira seleccionando el elemento que reciba el hit-test del navegador. Este hotfix evita que el highlight sea la causa del bloqueo, pero no implementa todavia un selector avanzado de objetos apilados.

### Checklist manual del hotfix

1. Click A: A queda seleccionada.
2. Click A de nuevo: ninguna mascara queda seleccionada.
3. Click A y luego click B: solo B queda seleccionada.
4. Seleccionar Membrana exterior y luego Nucleo interior: Nucleo se selecciona inmediatamente.
5. Zoom 2x, `EDIT`, `Space + drag` desde espacio vacio: imagen y SVG se desplazan juntos.
6. Zoom 2x, `EDIT`, `Space + drag` desde una mascara: pan funciona y no cambia seleccion.
7. Soltar mouse y Space: cursor vuelve al estado normal y el siguiente click selecciona.
8. `Space + drag` sobre un poligono: no selecciona como efecto colateral.
9. Zoom 2x sin Space: click sobre poligono selecciona correctamente.
10. Rotar 90, 180 y 270: seleccion sigue operando sobre el SVG.
11. Ocultar la capa del objeto seleccionado: seleccion y highlight se limpian.
12. Cambiar de muestra durante `EDIT`: vuelve a `NAVIGATE`, limpia seleccion y termina pan.
13. Historico `version 1.0` con IDs duplicados: dos objetos con mismo `id` pueden seleccionarse individualmente por la key defensiva.

## Hotfix - pan definitivo en EDIT

La validacion manual posterior confirmo que la seleccion, el toggle, las estructuras anidadas y el highlight funcionaban, pero `Space + drag` seguia sin desplazar la imagen en modo `EDIT`.

### Causa exacta

El visor tenia reglas separadas para cursor, inicio de pan, eventos SVG y seleccion:

- El cursor podia indicar pan temporal por `isSpacePressed`.
- Los poligonos seguian siendo interactivos en modo `EDIT`.
- No habia una fuente unica para decidir si el visor estaba realmente en modo pan.
- El pan en `EDIT` dependia de la ruta de eventos desde SVG/poligonos hacia el wrapper.

Por eso la UI podia mostrar `Pan temporal` sin garantizar que el visor completo estuviera en la misma modalidad de eventos.

### Fuente unica de pan

Se agrego `effectivePanMode`, que es `true` cuando:

- `viewerMode === "NAVIGATE"`.
- `viewerMode === "EDIT" && editorTool === "PAN"`.
- `viewerMode === "EDIT" && isSpacePressed`.

Esta misma condicion gobierna:

- inicio del pan;
- cursor;
- prioridad de interaccion;
- `pointer-events` de la capa SVG interactiva.

### Herramientas de editor

En modo `EDIT` se agregaron dos herramientas minimas:

- `SELECT`: permite seleccionar/deseleccionar mascaras.
- `PAN`: convierte todo el visor en superficie de movimiento.

Al entrar en `EDIT`, al salir de `EDIT` o al cambiar de muestra, `editorTool` vuelve a `SELECT`.

### Space como atajo temporal

En `EDIT + SELECT`, mantener `Space` activa temporalmente `effectivePanMode`.

Soltar `Space` vuelve a `SELECT` sin cambiar la herramienta activa.

Si `editorTool === "PAN"`, `Space` no es necesario para mover el visor.

### Pointer events y pointer capture

Cuando `effectivePanMode === true`, la capa `segmentation-polygons` usa `pointer-events: none`, por lo que el `pointerdown` llega al wrapper del visor aunque empiece encima de una mascara.

El wrapper estable `image-transform-layer` concentra:

- `pointerdown.capture`;
- `pointermove`;
- `pointerup`;
- `pointercancel`;
- `lostpointercapture`;
- `setPointerCapture()`;
- `releasePointerCapture()`.

El algoritmo de pan no se duplico: `EDIT` reutiliza el mismo calculo de delta, clamp y `panX`/`panY` que `NAVIGATE`.

### Checklist manual del pan definitivo

1. `EDIT`, Zoom 2x, `SELECT`, mantener `Space`, drag desde fondo: pan.
2. `EDIT`, Zoom 2x, `SELECT`, mantener `Space`, drag desde mascara: pan sin seleccion accidental.
3. `EDIT`, Zoom 2x, activar `Mover`, drag desde fondo: pan.
4. `Mover`, drag desde mascara: pan sin seleccion accidental.
5. `Mover -> Seleccionar`, click mascara: seleccion inmediata.
6. `SELECT`, `Space + pan`, soltar `Space`, click mascara: seleccion inmediata.
7. Zoom + Rotar + Mover: imagen y SVG permanecen alineados.
8. `NAVIGATE`: pan sigue funcionando como antes.

## Limitaciones

- No se modifica geometria.
- No se persisten ediciones.
- No se valida una revision desde el frontend.
- No se crean ni eliminan objetos.
- No se agregan herramientas de edicion manual.
- No se agrega canvas.
- No se modifica backend.
- No se modifica el contrato API.

## Siguiente paso recomendado

Sprint 13C deberia implementar edicion minima controlada del `BORRADOR`, probablemente empezando por operaciones atomicas y auditables como mover puntos o marcar visibilidad/estado de objetos, siempre usando `PATCH /api/revisiones-segmentacion/{id}/` y sin tocar `ResultadoSegmentacion.respuesta_json` ni `resultado_normalizado`.
