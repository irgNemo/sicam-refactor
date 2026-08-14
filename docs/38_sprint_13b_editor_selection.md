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
- `suppressNextOverlayClick`: evita seleccionar una mascara cuando el gesto fue pan con `Space`.

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
