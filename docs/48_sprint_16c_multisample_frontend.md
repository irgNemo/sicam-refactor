# Sprint 16C - Frontend multimuestra Saliva/Sangre

## Fecha

```text
2026-08-26 16:57:52 -06:00
```

## Proposito

Incorporar `SANGRE` al frontend de segmentacion reutilizando el editor comun existente. No se creo un segundo editor, no se duplico `MainContent.vue`, no se modifico backend y no se tocaron microservicios ni algoritmos cientificos.

## UX implementada

Se agregaron tabs compactos en la galeria:

```text
Saliva | Sangre
```

El tipo activo determina:

- listado de muestras;
- endpoint de segmentacion;
- endpoint de historial;
- labels disponibles;
- palette;
- opciones de dibujo;
- filas de conteo;
- capas visibles.

El default sigue siendo `SALIVA` para preservar el comportamiento existente.

## Estado `activeSampleType`

`App.vue` mantiene `activeSampleType` como estado compartido de la pantalla de segmentacion.

`MainContent.vue` recibe ese valor por prop y emite:

```text
sample-type-changed
```

Valores canonicos:

```text
SALIVA
SANGRE
```

La fuente canonica de labels y nombres visibles es:

```text
apps/web/Frontend/src/domain/segmentationTypes.js
```

## Routing de services

`segmentationService.js` resuelve endpoints por tipo de muestra:

```text
SALIVA -> /api/muestras/
SANGRE -> /api/muestras-sangre/
```

Funciones actualizadas:

```text
listarMuestras(sampleType)
segmentarMuestra(muestraId, sampleType)
obtenerResultadosSegmentacion(muestraId, sampleType)
```

`apiClient.js` no se modifico.

## Listado y galeria

### Saliva

La galeria conserva el origen actual:

```text
GET /api/analisis/
analisisActual.muestras_saliva
```

### Sangre

La galeria usa:

```text
GET /api/muestras-sangre/
```

Luego filtra en frontend por:

```text
MuestraSangre.analisis == AnalisisPred.id_analisis
```

Esto evita cambiar `AnalisisSerializer`, que por ahora solo anida `muestras_saliva`.

## Upload de muestras

El backend ya exponia carga multipart para sangre mediante:

```text
POST /api/muestras-sangre/
imagen=<file>
analisis=<id>
```

`RegistroView.vue` ahora permite elegir:

```text
Saliva
Sangre
```

Para saliva usa:

```text
POST /api/muestras/
```

Para sangre usa:

```text
POST /api/muestras-sangre/
```

No se agregaron endpoints nuevos.

## Segmentacion

El boton unico de segmentacion se mantiene. El endpoint se resuelve por tipo:

```text
SALIVA -> POST /api/muestras/{id}/segmentar/
SANGRE -> POST /api/muestras-sangre/{id}/segmentar/
```

Durante `SANGRE`, el panel muestra:

```text
Segmentando muestra de sangre... Este proceso puede tardar varios minutos.
```

El cambio de tab queda deshabilitado mientras `segmentacionLoading=true` para evitar lanzar o mezclar requests sincronas largas.

## Timeout frontend

`apiClient.js` no define timeout propio de Axios.

Resultado:

```text
El frontend no impone un timeout menor al backend para BLOOD.
```

El timeout efectivo sigue controlado por Django:

```text
SALIVA_SERVICE_TIMEOUT=30
BLOOD_SERVICE_TIMEOUT=240
```

## Historial

El historial usa el endpoint correspondiente:

```text
SALIVA -> GET /api/muestras/{id}/resultados-segmentacion/
SANGRE -> GET /api/muestras-sangre/{id}/resultados-segmentacion/
```

Al cambiar de tab o muestra se limpia:

- muestra seleccionada;
- resultado activo;
- historial;
- resultado efectivo;
- revision activa;
- borrador pendiente;
- objetos de trabajo;
- seleccion editorial;
- undo/redo;
- mediciones del visor;
- zoom, rotacion y pan.

Esto evita mostrar overlay o historial stale entre saliva y sangre.

## Resultado efectivo y revisiones

El resultado efectivo permanece comun:

```text
GET /api/resultados-segmentacion/{id}/efectivo/
```

Las revisiones se siguen manejando con:

```text
useSegmentationRevision.js
segmentationRevisionService.js
```

No se creo version especifica para sangre.

## Labels y palette

### SALIVA

```text
membrana
nucleo
micronucleo
```

### SANGRE

```text
membrana
micronucleo
```

No se muestra `nucleo` como opcion de dibujo en `SANGRE`.

Los colores vienen de `segmentationTypes.js`. Se preservan los colores actuales de saliva y se reutilizan los definidos para sangre.

## Capas visibles y resumen

`OverlayLayersCard.vue` permanece generico y recibe `overlayLabels` ya filtrado por el resultado/tipo activo.

`SegmentationCountSummary.vue` recibe filas calculadas desde la configuracion activa:

- `SALIVA`: 3 filas;
- `SANGRE`: 2 filas.

No se muestra `nucleo=0` en sangre.

## Overlay y editor

`SegmentationOverlay.vue` no recibio condiciones especificas por tipo de muestra.

El overlay sigue usando:

- `objects`;
- `palette`;
- labels visibles;
- coordenadas normalizadas;
- zoom;
- pan;
- rotacion;
- DRAW;
- VERTEX;
- Undo/Redo.

El editor reutiliza `useSegmentationEditor.js`. Al cambiar a `SANGRE`, `drawingLabel` se restablece a un label valido del tipo activo.

## Resumen del Caso

`GET /api/casos/{id}/resumen-segmentacion/` sigue orientado a `MuestraSaliva`.

Decision Sprint 16C:

```text
En tab SANGRE no se muestran metricas agregadas de saliva como si fueran multimodales.
```

`SideBar.vue` muestra una nota neutral indicando que el resumen agregado actual corresponde a saliva y que las metricas de sangre se revisan desde la muestra seleccionada.

## Validaciones ejecutadas

Build dentro del sandbox:

```text
npm.cmd run build
FAIL por fallo conocido de Vite/esbuild: Acceso denegado al resolver vite.config.js.
```

Build fuera del sandbox:

```text
npm.cmd run build
PASS
88 modules transformed
dist/index.html
dist/assets/index-B02KCO1v.css
dist/assets/index-r5xxkZAv.js
```

Revision de diff:

```text
git diff --check
PASS
```

Con advertencias CRLF del working copy, sin errores de whitespace.

Busqueda de logs temporales:

```text
console.debug = sin nuevos usos
console.table = sin nuevos usos
```

Existe un `console.log` legacy en `SideBar.vue` para `verAnalisis()`, no introducido por este sprint.

## Regresion manual SALIVA requerida

Checklist:

- tab `Saliva`;
- seleccionar muestra;
- ejecutar segmentacion;
- historial;
- overlay;
- `EDIT`;
- `DRAW`;
- `VERTEX`;
- guardar borrador;
- validar revision;
- volver a `NAVIGATE`;
- verificar que labels disponibles sean `membrana`, `nucleo`, `micronucleo`.

## Smoke manual BLOOD requerido

Checklist:

- cargar al menos una `MuestraSangre` desde `Registro` o API;
- tab `Sangre`;
- seleccionar muestra;
- ejecutar segmentacion;
- esperar aproximadamente 2 minutos;
- confirmar mensaje de proceso largo;
- revisar historial;
- revisar overlay;
- revisar `Resumen de Conteo`;
- revisar `Capas visibles`;
- entrar a `EDIT`;
- confirmar que `DRAW` solo ofrece `membrana` y `micronucleo`;
- probar `VERTEX`;
- guardar borrador;
- validar revision;
- volver a `NAVIGATE`;
- confirmar que no aparece `nucleo` como label de sangre.

## Limitaciones

- `AnalisisSerializer` todavia no anida `muestras_sangre`; el frontend lista sangre mediante endpoint independiente.
- No se implemento job queue, polling, Celery, Redis ni WebSocket.
- La segmentacion BLOOD sigue siendo request HTTP sincrono y puede tardar alrededor de 120 segundos en CPU.
- El resumen agregado de caso sigue sin semantica multimodal.
- No se agregaron pruebas frontend automatizadas porque el proyecto no tiene framework de tests frontend configurado.

## Deuda async

Evaluar ejecucion asincrona de segmentacion BLOOD debido al tiempo de inferencia CPU.

## Conclusion

```text
PASS WITH MANUAL VALIDATION PENDING
```

La integracion frontend multimuestra queda compilada y lista para validacion manual end-to-end con muestras reales de sangre.
