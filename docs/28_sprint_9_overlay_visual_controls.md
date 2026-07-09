# Sprint 9 - Overlay Visual Controls

## Fecha

2026-07-09 07:39:44 -06:00

## Referencia Git

- Rama: `master`
- Commit: `dbb9ac4`

## Objetivo

Agregar controles visuales basicos para inspeccionar el overlay SVG sin implementar edicion manual ni guardar cambios de geometria.

## Archivos modificados

- `apps/web/Frontend/src/components/MainContent.vue`

No se modificaron:

- backend
- microservicios
- endpoints
- `apps/web/Frontend/package.json`
- servicios frontend

## Asignacion de colores

Se agrego una paleta local fija en `data()`:

```javascript
overlayPalette
```

Cada etiqueta (`label`) se asigna a un color segun su posicion en la lista alfabetica de etiquetas:

```text
overlayLabelNames
```

Si hay mas etiquetas que colores disponibles, la paleta se reutiliza con modulo:

```text
index % overlayPalette.length
```

El color se aplica al `polygon` mediante estilo dinamico:

```vue
:style="{ fill: polygon.fill, stroke: polygon.stroke }"
```

## Visibilidad por etiqueta

Estado agregado:

```javascript
overlayLabelVisibility = {}
```

Por defecto, todas las etiquetas quedan visibles.

La visibilidad se reinicializa cuando:

- cambia la muestra seleccionada;
- se carga historial de segmentacion;
- se ejecuta segmentacion y llega una nueva respuesta.

Funcion agregada:

```javascript
toggleOverlayLabel(label)
```

El filtrado se aplica antes de renderizar `overlayPolygons`:

```text
overlayLabelVisibility[label] !== false
```

## Comportamiento de UI

Se agrego la seccion compacta:

```text
Etiquetas del overlay
```

Cada etiqueta muestra:

- checkbox de visibilidad;
- swatch de color;
- nombre de etiqueta;
- conteo de poligonos dibujables para esa etiqueta.

La seccion solo aparece si existen etiquetas derivadas de poligonos dibujables.

## Validacion de geometria

Se mantiene la validacion previa:

- solo objetos con `geometry.type === "polygon"`;
- solo puntos validos;
- solo poligonos con al menos 3 puntos proyectados;
- no falla si `resultado_normalizado` es `null`;
- no falla si `objects` no es arreglo.

## Comandos ejecutados

Desde:

```text
apps/web/Frontend
```

### Build inicial en sandbox

```powershell
npm.cmd run build
```

Resultado:

```text
FAIL
```

Motivo:

```text
Cannot read directory "../../../../../../..": Acceso denegado.
Could not resolve ".../apps/web/Frontend/vite.config.js"
```

Clasificacion: limitacion conocida del sandbox al resolver `vite.config.js` con Vite/esbuild, no error del codigo modificado.

### Build con permisos elevados

```powershell
npm.cmd run build
```

Resultado:

```text
PASS
vite v7.3.0 building client environment for production...
71 modules transformed.
dist/index.html
dist/assets/index-DAZ22Ito.css
dist/assets/index-BcouYqYA.js
built in 1.04s
```

Advertencia no bloqueante:

```text
PowerShell no pudo cargar profile.ps1 por Execution_Policies.
```

La advertencia no impidio el build.

## Limitaciones

- No hay edicion manual.
- No se guardan cambios de geometria.
- No se agregan herramientas avanzadas.
- No se usa canvas.
- La paleta es fija y local.
- Si hay muchas etiquetas, los colores pueden repetirse.
- No se valida visualmente alineacion con imagenes reales en este sprint.

## Resultado general

PASS WITH WARNINGS

El overlay SVG ahora tiene colores por etiqueta, leyenda compacta y controles de visibilidad por etiqueta.

## Pendientes para Sprint 10

- Validar alineacion visual con imagenes reales.
- Agregar colores especificos por etiquetas conocidas si se formalizan.
- Evaluar controles de opacidad.
- Evaluar seleccion o resaltado de objetos sin permitir edicion.
- Considerar canvas si el numero de poligonos afecta rendimiento.
