# Sprint 13C - Crear/eliminar mascaras y persistir BORRADOR

## Objetivo

Sprint 13C habilita la primera edicion real del snapshot experto de segmentacion:

- crear mascaras manuales completas;
- eliminar mascaras automaticas o manuales;
- actualizar conteos locales;
- deshacer y rehacer operaciones completas;
- guardar el `BORRADOR` mediante `PATCH`;
- recargar y recuperar los cambios desde Django.

Sprint 13C no permite editar vertices de mascaras existentes. Esa edicion queda para Sprint 13D.

## Estado local

El frontend separa el estado persistido del servidor y el estado local de trabajo:

- `activeRevision`: ultimo `RevisionSegmentacion` conocido por el servidor.
- `workingObjects`: copia editable local de `activeRevision.resultado_editado.objects`.

Durante `EDIT`, el overlay y el resumen de conteo usan `workingObjects`.

`activeRevision.resultado_editado.objects` no se muta en cada interaccion local.

## Identidad editorial

Los objetos de `RevisionSegmentacion` ya tienen IDs editoriales unicos.

La edicion usa `resultado_editado.objects[].id` como identidad persistida del snapshot. No usa:

- `source.raw_id`;
- `provenance.base_object_id`;
- IDs duplicados del automatico legacy.

En frontend, la clave de seleccion en modo `EDIT` se deriva del ID editorial.

## Dirty State

`isDraftDirty` indica si `workingObjects` difiere del ultimo estado guardado.

Se marca como dirty despues de:

- crear mascara;
- eliminar mascara;
- `Undo`;
- `Redo`;

Despues de `PATCH` exitoso:

- `activeRevision` se reemplaza con la respuesta del servidor;
- `workingObjects` se recarga desde la respuesta;
- `isDraftDirty = false`;
- `undoStack` y `redoStack` se limpian.

Si existe una mascara en construccion (`draftPolygonPoints.length > 0`), tambien se considera trabajo pendiente para prevenir perdida silenciosa.

## Herramientas

En modo `EDIT` existen tres herramientas:

- `SELECT`: selecciona/deselecciona mascaras y permite eliminar la seleccion.
- `PAN`: mueve imagen y SVG usando el motor de pan existente.
- `DRAW`: agrega vertices para construir una mascara nueva.

`effectivePanMode` sigue siendo la fuente unica para pan:

- `NAVIGATE`;
- `EDIT + PAN`;
- `EDIT + Space`.

En `DRAW`, mantener `Space` activa pan temporal y no agrega vertices.

## Tipo de mascara

`drawingLabel` define el tipo de mascara manual a crear:

- `membrana`;
- `nucleo`;
- `micronucleo`.

Los colores provienen de `segmentationLabelPalette`. No se agrego una segunda paleta.

Si la capa del tipo seleccionado esta oculta, al activar `DRAW` o cambiar `drawingLabel` se vuelve visible.

## Coordenadas

Los puntos persistidos se guardan en coordenadas naturales de la imagen.

El flujo de conversion es:

```text
event.clientX/clientY
-> SVG local mediante SVGSVGElement.getScreenCTM().inverse()
-> coordenada natural usando overlayContainment offsetX/offsetY/scaleX/scaleY
```

Esto reutiliza la misma geometria del overlay:

```text
natural image point -> scalePoint() -> SVG overlay point
```

No se guardan coordenadas CSS, de viewport ni `clientX/clientY`.

## Zoom, pan y rotacion

La conversion usa la CTM real del SVG, por lo que incorpora la transformacion aplicada al wrapper comun:

- zoom;
- pan;
- rotacion;

El objetivo es que una mascara dibujada con zoom/pan/rotacion siga ubicada sobre la misma region anatomica al usar `Ajustar`.

## Letterbox

El visor usa `object-fit: contain`, por lo que puede existir espacio visible que no pertenece a la imagen.

Sprint 13C valida que el punto convertido caiga dentro de la caja visible real de la imagen. Si el click cae fuera del area de imagen, no se agrega vertice y se muestra feedback discreto.

## Crear mascara

En `DRAW`:

1. Click valido sobre la imagen agrega un vertice a `draftPolygonPoints`.
2. La UI muestra puntos y lineas temporales.
3. `Finalizar mascara` se habilita con 3 o mas puntos.
4. Al finalizar se crea un objeto nuevo en `workingObjects`.
5. El objeto queda seleccionado.
6. Se registra una operacion `CREATE_OBJECT` en `undoStack`.

La geometria creada usa:

```json
{
  "type": "polygon",
  "points": []
}
```

## Provenance manual

Los objetos manuales usan el contrato de Sprint 13A:

```json
{
  "origin": "manual",
  "base_object_id": null
}
```

No se agregaron campos nuevos como `modified`.

## IDs manuales

Los IDs manuales son enteros positivos y unicos dentro de `workingObjects`.

La estrategia es monotona:

- toma el maximo ID editorial actual;
- asigna el siguiente entero disponible;
- no renumera objetos existentes;
- no reutiliza IDs eliminados durante la misma sesion.

## Eliminar mascara

En `SELECT`, con un objeto seleccionado, `Eliminar mascara`:

- elimina exactamente ese objeto de `workingObjects`;
- limpia la seleccion;
- actualiza conteos locales;
- marca dirty;
- registra `DELETE_OBJECT` en `undoStack`.

Eliminar una mascara automatica solo la elimina del snapshot revisado. `ResultadoSegmentacion.resultado_normalizado` permanece intacto.

## Undo/Redo

Sprint 13C implementa historial de operaciones completas:

- `CREATE_OBJECT`;
- `DELETE_OBJECT`.

No se guarda un snapshot completo en cada paso.

Semantica:

- Undo de create elimina el objeto.
- Redo de create restaura el objeto.
- Undo de delete restaura el objeto.
- Redo de delete vuelve a eliminarlo.
- Una nueva operacion normal limpia `redoStack`.

Los vertices individuales durante dibujo no entran al historial Undo/Redo. `Cancelar` descarta `draftPolygonPoints`.

## Conteos locales

Durante `EDIT`, el resumen de conteo se calcula desde `workingObjects`:

- crear mascara incrementa conteo y total;
- eliminar decrementa conteo y total;
- Undo/Redo actualiza inmediatamente;
- ocultar una capa no modifica conteos.

En `NAVIGATE`, el resumen mantiene el comportamiento previo basado en el resultado normalizado activo.

## PATCH

El servicio frontend usa:

```text
PATCH /api/revisiones-segmentacion/{id}/
```

Payload:

```json
{
  "resultado_editado": {
    "...": "...",
    "objects": []
  }
}
```

No se envian campos protegidos como `estado`, `numero_revision`, `resultado_segmentacion` o `validado_en`.

El snapshot se construye copiando `activeRevision.resultado_editado` y reemplazando solo `objects`.

## Errores de guardado

Si el backend rechaza el `PATCH`:

- `workingObjects` no se reemplaza;
- `isDraftDirty` permanece `true`;
- se mantiene `EDIT`;
- se muestra error;
- el usuario puede reintentar.

## Proteccion contra perdida de cambios

Si hay cambios locales sin guardar o un poligono en construccion, el frontend confirma antes de:

- salir de `EDIT`;
- cambiar de muestra;
- cerrar/recargar la pestana mediante `beforeunload`.

No hay autosave en Sprint 13C.

## Historicos legacy 1.0

El hotfix de Sprint 13A convierte IDs automaticos duplicados en IDs editoriales unicos al crear el BORRADOR.

Sprint 13C opera sobre esos IDs editoriales. Dos objetos con el mismo `provenance.base_object_id = 255` pueden seleccionarse, eliminarse, deshacerse y guardarse de forma independiente.

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

### Create

1. Entrar en `EDIT`.
2. Elegir `Dibujar`.
3. Crear `Membrana`, `Nucleo` y `Micronucleo` con 3 o mas puntos.
4. Confirmar color, `Origen = Manual`, conteos y dirty state.

### Coordenadas

Crear mascaras en:

- 100%, sin pan;
- Zoom 2x;
- Zoom 2x + Pan;
- Rotar 90;
- Rotar 180;
- Rotar 270;
- Rotar + Zoom + Pan.

Prueba critica:

```text
Rotar 90
-> Zoom
-> Pan
-> dibujar un Nucleo
-> Guardar borrador
-> Ajustar
-> comprobar ubicacion anatomica
```

### Delete

- Eliminar mascara automatica y confirmar conteo -1.
- Eliminar mascara manual y confirmar conteo -1.
- Confirmar que el automatico original sigue intacto.

### Undo/Redo

- Crear A, Undo, Redo.
- Eliminar B, Undo, Redo.
- Undo y luego crear C debe limpiar Redo.

### Persistencia

1. Crear mascara manual A.
2. Eliminar automatica B.
3. Guardar borrador.
4. Recargar.
5. Entrar en `EDIT`.
6. Confirmar A existe, B sigue eliminada y conteos son correctos.

### Legacy 1.0

Usar un BORRADOR derivado de resultado legacy con varios `provenance.base_object_id = 255`.

Verificar:

- seleccionar objetos distintos;
- eliminar uno;
- Undo;
- guardar;
- recargar;
- confirmar que se manipulo solo el objeto identificado por su ID editorial.

## BORRADOR pendiente en modo navegacion

`NAVIGATE` sigue mostrando el resultado automatico actual. Esto es deliberado:

```text
ResultadoSegmentacion automatico = resultado oficial mientras no exista revision VALIDADA
RevisionSegmentacion BORRADOR = trabajo experto guardado, aun no validado
```

Guardar un `BORRADOR` no convierte las correcciones en resultado oficial.

Para evitar confusion, cuando el resultado activo tiene una `RevisionSegmentacion` en estado `BORRADOR`, el frontend muestra un indicador compacto:

```text
Revision pendiente
Revision #N - Cambios guardados, aun no validados.
Continuar edicion
```

El indicador no cambia la fuente del overlay:

- En `NAVIGATE`, el overlay sigue usando el resultado automatico.
- En `EDIT`, el overlay usa `workingObjects` del `BORRADOR`.

La existencia del `BORRADOR` se detecta solo para el `ResultadoSegmentacion` activo. Si el borrador ya esta cargado en memoria, se reutiliza. Si no, el frontend consulta:

```text
GET /api/resultados-segmentacion/{id}/revisiones/
```

y localiza la revision con:

```text
estado == "BORRADOR"
```

No se consultan revisiones de todas las imagenes de la galeria.

`Continuar edicion` reutiliza el flujo existente de `EDIT`, basado en:

```text
POST /api/resultados-segmentacion/{id}/revisiones/
```

Ese endpoint es idempotente: devuelve el `BORRADOR` existente si ya hay uno.

Al cambiar de muestra o de resultado historico, el indicador se recalcula para el nuevo `ResultadoSegmentacion` activo y no conserva accidentalmente el borrador de la muestra anterior.

## Limitaciones

- No se editan vertices existentes.
- No se arrastra un poligono completo.
- No se cambia label de objetos existentes.
- No se implementa `Validar revision` en frontend.
- No hay autosave.
- Undo/Redo vive solo hasta el ultimo guardado exitoso.
