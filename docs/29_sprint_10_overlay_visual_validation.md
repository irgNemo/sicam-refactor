# Sprint 10 - Overlay Visual Validation and Alignment Adjustments

## Fecha

2026-07-09 08:08:26 -06:00

## Referencia Git

- Rama: `master`
- Commit: `594edae`

## Objetivo

Validar tecnicamente la alineacion del overlay SVG de segmentacion sobre la imagen seleccionada y aplicar ajustes minimos para facilitar inspeccion visual.

No se agrego edicion manual, no se guardo geometria y no se modificaron backend, microservicios, endpoints ni dependencias.

## Archivos modificados

- `apps/web/Frontend/src/components/MainContent.vue`

## Revision del calculo de alineacion

El calculo de `object-fit: contain` implementado en Sprint 8 se mantiene:

- usa `naturalWidth` y `naturalHeight` de la imagen;
- usa el rectangulo renderizado del elemento `img`;
- calcula `displayedImageWidth` y `displayedImageHeight`;
- calcula `offsetX` y `offsetY`;
- proyecta puntos con `offset + coordenada * escala`.

La formula sigue siendo coherente con `object-fit: contain`, siempre que el SVG y el `img` compartan el mismo rectangulo base.

## Revision de contenedor y CSS

La imagen y el SVG se renderizan dentro de:

```text
.img-placeholder
```

Ese contenedor tiene:

```css
position: relative;
overflow: hidden;
```

El SVG usa:

```css
position: absolute;
inset: 0;
pointer-events: none;
```

Esto mantiene el mismo sistema de coordenadas entre el contenedor, la imagen y el overlay.

## Problemas detectados

Se detectaron dos puntos menores:

1. El SVG tenia `position: absolute` e `inset: 0`, pero no declaraba explicitamente `width: 100%`, `height: 100%` ni `display: block`.
2. El estado vacio de imagen estaba asociado con el `v-else` del SVG, por lo que podia mostrarse cuando habia imagen seleccionada pero no existian poligonos dibujables.

## Ajustes realizados

### Refuerzo del SVG overlay

Se reforzo `.segmentation-svg-overlay` con:

```css
display: block;
width: 100%;
height: 100%;
```

El SVG conserva:

```css
position: absolute;
inset: 0;
pointer-events: none;
```

### Estado vacio

El estado vacio ahora depende de:

```vue
v-if="!imagenSeleccionada"
```

Asi no se muestra encima de una imagen seleccionada cuando todavia no hay poligonos.

### Diagnostico visual opcional

Se agrego un modo apagado por defecto:

```text
Diagnostico visual
```

Cuando se activa, dibuja dentro del SVG:

- borde de la caja base del SVG;
- borde de la caja visible real de la imagen bajo `object-fit: contain`;
- bounding box de los poligonos visibles.

El diagnostico no intercepta clicks porque el SVG conserva `pointer-events: none`.

## Comportamiento de UI

El panel de diagnostico textual existente se conserva.

El nuevo control permite inspeccionar rapidamente si:

- el SVG ocupa el mismo rectangulo que la imagen;
- la caja visible calculada coincide con el area real de la imagen;
- los poligonos proyectados caen dentro del area esperada.

Los controles de visibilidad por etiqueta del Sprint 9 se mantienen.

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

Clasificacion: limitacion conocida del sandbox con Vite/esbuild, no error del codigo modificado.

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
dist/assets/index-zxOg9Y_f.css
dist/assets/index-FvdtiyEO.js
built in 1.15s
```

Advertencia no bloqueante:

```text
PowerShell no pudo cargar profile.ps1 por Execution_Policies.
```

La advertencia no impidio el build.

## Limitaciones

- No se realizo inspeccion manual en navegador con imagenes reales.
- No se agrego seleccion avanzada de objetos.
- No se agrego edicion manual.
- No se guardan cambios de geometria.
- No se usa canvas.
- Si las coordenadas normalizadas no corresponden al `naturalWidth` y `naturalHeight` de la imagen mostrada, el overlay podria requerir una transformacion adicional en un sprint posterior.

## Resultado general

PASS WITH WARNINGS

El overlay mantiene la formula de alineacion correcta para `object-fit: contain`, el SVG queda reforzado para ocupar el mismo rectangulo base y se agrega diagnostico visual opcional para validacion manual posterior.

## Pendientes para Sprint 11

- Validar visualmente con imagenes reales en navegador.
- Confirmar que las coordenadas normalizadas usan el mismo sistema de referencia que la imagen original.
- Evaluar controles de opacidad si el overlay dificulta inspeccion.
- Evaluar resaltado de objetos sin edicion manual.
- Considerar canvas solo si el numero de poligonos afecta rendimiento.
