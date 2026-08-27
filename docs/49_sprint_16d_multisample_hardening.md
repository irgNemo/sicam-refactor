# Sprint 16D - Hardening E2E SALIVA/BLOOD

## Fecha

```text
2026-08-27 16:25:22 -06:00
```

## Proposito

Hacer hardening E2E del flujo multimuestra `SALIVA`/`SANGRE` despues de la validacion manual de Sprint 16C, sin agregar funcionalidades grandes, sin redisenar la interfaz, sin tocar algoritmos cientificos y sin implementar jobs asincronos.

## Auditoria inicial

Se revisaron:

- `App.vue`
- `MainContent.vue`
- `SideBar.vue`
- `RegistroView.vue`
- `segmentationService.js`
- `segmentationTypes.js`
- composables de editor, revision y viewport
- componentes `segmentation/*`
- modelos y endpoints backend de `MuestraSaliva`, `MuestraSangre`, `ResultadoSegmentacion` y `RevisionSegmentacion`

El archivo untracked extrano de la raiz del repositorio no se abrio, no se modifico, no se borro y no se stageo.

## Bugs encontrados y corregidos

### Cambio de muestra durante segmentacion

Hallazgo:

```text
Los tabs SALIVA/SANGRE ya quedaban bloqueados durante segmentacion, pero la galeria permitia seleccionar otra muestra mientras segmentacionLoading=true.
```

Riesgo:

```text
Una respuesta tardia de segmentacion, especialmente BLOOD, podia mezclarse con otra muestra seleccionada.
```

Correccion:

- `selectImagen()` ignora cambios de muestra mientras `segmentacionLoading=true`.
- Los thumbnails no activos se muestran deshabilitados visualmente durante segmentacion.
- `ejecutarSegmentacion()` captura `sampleType` y `muestraId` antes del request.
- La respuesta y el error se aplican solo si `isCurrentSample(muestraId, sampleType)` sigue siendo verdadero.

### Texto ambiguo en lista de casos

Hallazgo:

```text
SideBar.vue mostraba un contador como "imagenes", pero ese valor proviene solo de muestras_saliva.
```

Correccion:

```text
El texto se aclaro como contador de saliva para evitar sugerir que ya es un agregado multimodal.
```

## Matriz de estados

### SALIVA

- Sin muestra: galeria vacia muestra estado neutral.
- Muestra sin segmentacion: panel muestra ausencia de historial/resultados.
- Muestra con `COMPLETADO`: historial, effective automatico, resumen y overlay usan el resultado activo.
- Muestra con `ERROR`: backend conserva resultado `ERROR`; frontend muestra error controlado y permite reintentar.
- `COMPLETADO + BORRADOR`: el BORRADOR aparece como revision pendiente y no reemplaza effective.
- `COMPLETADO + VALIDADA`: effective usa `VALIDADA`; automatico permanece historico.

### SANGRE

- Sin muestra: galeria muestra `No hay muestras de sangre cargadas.`
- Muestra sin segmentacion: panel muestra ausencia de historial/resultados.
- Muestra con `COMPLETADO`: historial, effective automatico, resumen y overlay usan `SANGRE`.
- Muestra con `ERROR`: backend conserva resultado `ERROR`; frontend muestra error controlado y permite reintentar.
- `COMPLETADO + BORRADOR`: el BORRADOR aparece como revision pendiente y no reemplaza effective.
- `COMPLETADO + VALIDADA`: effective usa `VALIDADA`; automatico permanece historico.

## Cambio SALIVA/BLOOD

Al cambiar de tipo se limpia:

- muestra seleccionada;
- resultado activo;
- historial;
- effective;
- revision activa;
- BORRADOR pendiente en UI;
- objetos de trabajo;
- seleccion editorial;
- undo/redo;
- mediciones de imagen;
- zoom, pan y rotacion;
- visibilidad de capas.

`drawingLabel` se restablece usando `defaultDrawingLabel` de la configuracion activa.

## Cambio de muestra del mismo tipo

`selectImagen()` limpia estado de resultado, historial, effective, revision, seleccion, editor, overlay y viewport antes de cargar la nueva muestra.

Durante una segmentacion activa, el cambio de muestra queda bloqueado para evitar race conditions con requests sincronos largos.

## BORRADOR pendiente

El estado de revision se obtiene desde backend con `loadRevisionState(resultadoId)`.

Comportamiento esperado:

- BORRADOR guardado reaparece al volver al resultado correspondiente.
- BORRADOR no se convierte en effective.
- BORRADOR de una muestra no aparece en otra.

`useSegmentationRevision.js` mantiene proteccion contra respuestas stale mediante `activeResultadoId` y `effectiveSegmentationRequestToken`.

## Cambios sin guardar

El flujo conserva `confirmDiscardDraftChanges()` antes de cambiar muestra/tipo cuando hay trabajo local pendiente.

Comportamiento:

- cancelar mantiene la edicion;
- aceptar descarta solo cambios locales;
- no guarda implicitamente.

## VALIDADA como effective

Backend conserva la semantica comun:

```text
sin VALIDADA -> AUTOMATICO
con VALIDADA -> VALIDADA
BORRADOR -> ignorado por effective
```

La segmentacion automatica y `resultado_normalizado` permanecen historicos e inmutables frente a revisiones.

## Multiples segmentaciones

La politica vigente no cambia:

```text
Cada ejecucion exitosa crea un nuevo ResultadoSegmentacion.
```

El historial se ordena por:

```text
creado_en desc
id_resultado_segmentacion desc
```

La UI toma `historialSegmentacion[0]` como ultima segmentacion.

## Error state y timeout

El backend maneja errores controlados:

- timeout -> `504`;
- conexion -> `503`;
- HTTP/servicio invalido -> `502`;
- JSON invalido -> `502`;
- label o geometria invalida -> `502`;
- inesperado -> `500`.

Frontend muestra el mensaje `error.response?.data?.error` cuando existe, sin exponer traceback.

`BLOOD_SERVICE_TIMEOUT` permanece en:

```text
240
```

`SALIVA_SERVICE_TIMEOUT` permanece en:

```text
30
```

## Doble click y requests largas

El boton de segmentacion se deshabilita con:

```text
segmentacionLoading=true
```

Los tabs y cambios de muestra tambien quedan bloqueados mientras hay segmentacion activa. Esto evita dos requests simultaneos desde la UI sobre la misma seleccion y evita abandonar silenciosamente una request BLOOD larga.

## Refresh del navegador

Despues de recargar la pagina, el estado persistido se recupera desde backend:

- muestras;
- historial;
- effective;
- BORRADOR pendiente.

El estado UI se reinicia:

- zoom;
- pan;
- rotacion;
- seleccion;
- herramienta activa.

Ese comportamiento es aceptado.

## Empty states

Estados esperados:

- sin caso: `No hay imagenes disponibles`;
- sin muestras SALIVA: `No hay muestras de saliva cargadas.`;
- sin muestras SANGRE: `No hay muestras de sangre cargadas.`;
- coleccion vacia no se muestra como error rojo.

## Upload

`RegistroView.vue` conserva un unico flujo de carga de imagenes con selector de tipo:

```text
SALIVA -> POST /api/muestras/
SANGRE -> POST /api/muestras-sangre/
```

Payload multipart:

```text
imagen=<file>
analisis=<id>
```

No se agrego validacion MIME avanzada.

## Archivos invalidos

Backend usa `ImageField`. No se implemento validacion adicional de contenido corrupto, extension o antivirus en este sprint.

Pendiente:

```text
Definir validacion de archivos clinicos/imagenes en un sprint especifico.
```

## Labels

Fuente canonica frontend:

```text
apps/web/Frontend/src/domain/segmentationTypes.js
```

SALIVA:

```text
membrana
nucleo
micronucleo
```

SANGRE:

```text
membrana
micronucleo
```

Backend mantiene la misma regla en:

```text
apps/web/Backend/api/services/segmentation/types.py
```

## Resumen de conteo, capas y DRAW

`SegmentationCountSummary.vue` recibe filas calculadas desde la configuracion activa.

`OverlayLayersCard.vue` recibe `overlayLabels` derivado del resultado activo.

`DRAW` usa `editableDrawingLabels` desde la configuracion activa:

- SALIVA: 3 opciones;
- SANGRE: 2 opciones;
- `nucleo` no aparece en sangre.

## Overlay geometry

No se modifico:

- calculo de `object-fit: contain`;
- offsets;
- escalas;
- SVG;
- zoom;
- pan;
- rotacion;
- simplificacion de poligonos;
- coordenadas normalizadas.

## Performance BLOOD

La validacion manual previa con aproximadamente 350 objetos fue PASS.

No se detecto una razon suficiente para optimizacion prematura. La deuda principal sigue siendo el tiempo CPU de inferencia, no el render del overlay.

## Raw IDs duplicados y Vue keys

BLOOD real puede devolver raw IDs duplicados. El frontend no usa `source.raw_id` como key.

Keys relevantes:

- galeria: `sampleType-id_muestra`;
- overlay: key defensiva con `selectionKey`, indice, id normalizado y label;
- capas: label;
- resumen: label;
- handles/draft: indices locales.

## Request races

Protecciones confirmadas o reforzadas:

- historial se aplica solo si `isCurrentSample(muestraId, sampleType)`;
- effective/revision tienen proteccion por `activeResultadoId`;
- segmentacion aplica respuesta/error solo si la muestra y tipo siguen activos;
- cambio de tab y muestra queda bloqueado durante segmentacion.

## Case Summary

`SideBar.vue` mantiene resumen agregado solo para saliva.

En tab `SANGRE` se muestra una nota neutral para no presentar metricas salivales como multimodales.

No se creo agregado BLOOD todavia.

## Textos

Se corrigio un texto ambiguo de contador en la lista de casos para aclarar que el conteo mostrado corresponde a saliva.

No se cambiaron textos cientificos ni contratos de labels.

## API service

`segmentationService.js` conserva funciones comunes y resuelve endpoints por `sampleType`.

No se duplico logica HTTP en `MainContent.vue`.

## Backend constraints y revisiones

Validado por tests:

- `SALIVA`: `muestra != null`, `muestra_sangre == null`;
- `SANGRE`: `muestra == null`, `muestra_sangre != null`;
- `SANGRE + nucleo` se rechaza;
- `SANGRE + membrana/micronucleo` se acepta;
- `VALIDADA` es inmutable;
- effective ignora BORRADOR y prioriza VALIDADA.

## Validaciones automaticas

Frontend:

```text
npm.cmd run build
```

Resultado:

```text
PASS fuera del sandbox
88 modules transformed
```

Dentro del sandbox se reprodujo el fallo conocido de Vite/esbuild por `Acceso denegado`.

Backend:

```text
python manage.py check
python manage.py makemigrations --check
python -m pytest
python manage.py test
```

Resultados:

```text
manage.py check = PASS
makemigrations --check = PASS, No changes detected
pytest = 141 passed, 2 skipped
manage.py test = 116 tests, OK
```

Diff:

```text
git diff --check = PASS
```

## Checklist manual recomendado

SALIVA:

- seleccionar paciente/caso;
- tab `Saliva`;
- seleccionar muestra;
- verificar historial/effective;
- ejecutar segmentacion;
- revisar overlay/capas/resumen;
- entrar a `EDIT`;
- probar `DRAW`, `VERTEX`, guardar BORRADOR y validar;
- confirmar effective `VALIDADA`.

SANGRE:

- cargar o seleccionar `MuestraSangre`;
- tab `Sangre`;
- confirmar ausencia de `nucleo`;
- ejecutar segmentacion;
- confirmar mensaje de proceso largo;
- revisar historial/effective;
- probar capas, overlay, zoom/pan/rotacion;
- entrar a `EDIT`;
- probar `DRAW`, `VERTEX`, guardar BORRADOR y validar.

Estados cruzados:

- cambiar SALIVA -> SANGRE;
- cambiar SANGRE -> SALIVA;
- cambiar muestra del mismo tipo;
- intentar cambiar muestra/tipo durante segmentacion;
- recargar navegador y confirmar recuperacion desde backend.

## Deudas y blockers

- Evaluar ejecucion asincrona BLOOD por inferencia CPU de aproximadamente 120 segundos.
- Definir resumen multimodal de caso.
- Definir validacion formal de archivos subidos.
- Mantener pendiente la revision/eliminacion del archivo untracked extrano de raiz en una tarea separada.

## Conclusion

```text
Sprint 16D = PASS CON OBSERVACIONES
```

Las observaciones corresponden a validacion manual pendiente y deudas conocidas; no se detecto blocker tecnico automatizado.
