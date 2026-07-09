# Sprint 8 - Frontend SVG Overlay

## Fecha

2026-07-08 21:02:41 -06:00

## Referencia Git

- Rama: `master`
- Commit: `4a7143c`

## Objetivo

Dibujar un overlay SVG inicial sobre la imagen seleccionada usando poligonos de:

```text
resultado_normalizado.objects[].geometry.points
```

El overlay respeta `object-fit: contain` mediante calculo de caja visible, offsets y escala.

## Archivos modificados

- `apps/web/Frontend/src/components/MainContent.vue`

No se modificaron:

- backend
- microservicios
- endpoints
- `apps/web/Frontend/package.json`
- servicios frontend

## Calculo de object-fit contain

Se agrego el computed:

```javascript
overlayContainment
```

Entrada:

```text
naturalWidth
naturalHeight
containerWidth = imageRenderedSize.width
containerHeight = imageRenderedSize.height
```

Calculo:

```text
imageAspect = naturalWidth / naturalHeight
containerAspect = containerWidth / containerHeight
```

Si `containerAspect > imageAspect`:

```text
displayedImageHeight = containerHeight
displayedImageWidth = containerHeight * imageAspect
offsetX = (containerWidth - displayedImageWidth) / 2
offsetY = 0
```

Si no:

```text
displayedImageWidth = containerWidth
displayedImageHeight = containerWidth / imageAspect
offsetX = 0
offsetY = (containerHeight - displayedImageHeight) / 2
```

Escala:

```text
scaleX = displayedImageWidth / naturalWidth
scaleY = displayedImageHeight / naturalHeight
```

## Calculo de coordenadas de overlay

Para cada punto original:

```text
overlayX = offsetX + x * scaleX
overlayY = offsetY + y * scaleY
```

La funcion `scalePoint(point)` ahora usa `overlayContainment` para aplicar escala y offset.

## Estructura del SVG overlay

Se agrego un `svg` dentro del contenedor de imagen:

```vue
<svg
  v-if="overlayPolygons.length"
  class="segmentation-svg-overlay"
  :width="imageRenderedSize.width"
  :height="imageRenderedSize.height"
  :viewBox="`0 0 ${imageRenderedSize.width} ${imageRenderedSize.height}`"
>
  <polygon ... />
</svg>
```

CSS:

```css
.segmentation-svg-overlay {
  inset: 0;
  pointer-events: none;
  position: absolute;
  z-index: 2;
}
```

El overlay no intercepta clicks.

## Validacion de puntos y poligonos

Se reutiliza `validPolygonPoints(points)`:

- `points` debe ser arreglo;
- cada punto debe ser arreglo;
- cada punto debe tener al menos dos coordenadas;
- las dos primeras coordenadas deben ser numericas.

`overlayPolygons`:

- ignora objetos sin `geometry`;
- ignora objetos cuyo `geometry.type` no sea `polygon`;
- ignora objetos sin puntos validos;
- ignora poligonos con menos de 3 puntos validos;
- no falla si `resultado_normalizado` es `null`;
- no falla si `objects` no es arreglo.

## Comportamiento de UI

Cuando existe imagen seleccionada, medicion valida y poligonos normalizados validos:

- se dibujan poligonos SVG sobre la imagen;
- se mantiene el diagnostico textual;
- se agregan al diagnostico:
  - caja visible;
  - offset;
  - numero de poligonos dibujables.

No se agrego edicion manual ni controles avanzados.

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
dist/assets/index-DX4N3vaV.css
dist/assets/index-B4rERiSm.js
built in 1.05s
```

Advertencia no bloqueante:

```text
PowerShell no pudo cargar profile.ps1 por Execution_Policies.
```

La advertencia no impidio el build.

## Limitaciones

- Overlay inicial, no herramienta final.
- No hay edicion manual.
- No se guardan cambios de geometria.
- No hay controles de visibilidad por etiqueta.
- Todos los poligonos usan el mismo estilo visual.
- No se valida si las coordenadas estan fuera del rango natural de la imagen.
- No se valida cierre de poligonos.
- No se usa canvas.
- No se agregan dependencias.

## Resultado general

PASS WITH WARNINGS

El frontend ya puede dibujar un overlay SVG inicial alineado con la imagen visible bajo `object-fit: contain`.

## Pendientes para Sprint 9

- Validar visualmente alineacion con imagenes reales.
- Agregar colores por etiqueta.
- Agregar controles de visibilidad por etiqueta.
- Manejar poligonos muy grandes o numerosos.
- Evaluar si se mantiene SVG o si se migra a canvas para rendimiento.
