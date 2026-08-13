# Sprint 12E - Zoom Out y Pan del visor

## Fecha

2026-08-13 16:34:52 -06:00

## Referencia Git

- Rama: `master`
- Commit base observado: `3b0e00c`

## Objetivo

Agregar `Zoom Out` y pan por arrastre al visor de muestra, manteniendo imagen y SVG overlay sincronizados mediante el mismo `image-transform-layer`.

No se modificaron backend, APIs, modelos, microservicios, normalizador, geometria del overlay, calculo de coordenadas, `Capas visibles`, `Resumen de Conteo` ni `Resumen del Caso`.

## Estado agregado

Se agrego estado minimo de pan en `MainContent.vue`:

```text
panX
panY
isPanning
panStartPointerX
panStartPointerY
panStartX
panStartY
```

El estado existente se mantiene:

```text
imageZoom
imageRotation
```

## Transform final

La transformacion se aplica al wrapper comun que contiene imagen y SVG:

```text
image-transform-layer
```

Transform final:

```text
translate(panX, panY) scale(imageZoom) rotate(imageRotation)
```

Como imagen y overlay permanecen dentro del mismo wrapper, Zoom, Rotar y Pan afectan a ambos de forma conjunta.

## Zoom Out

Se agrego un boton visible junto a Zoom In:

```text
Zoom +
Zoom -
Rotar
Ajustar
```

Reglas:

```text
ZOOM_MIN = 1
ZOOM_MAX = 2
ZOOM_STEP = 0.25
```

Comportamiento:

- Zoom In no supera `2.0`.
- Zoom Out no baja de `1.0`.
- Al volver a `1.0`, el pan se restaura a `0,0`.

## Pan

El pan se activa solo cuando:

```text
imageZoom > 1
```

Interaccion:

```text
clic izquierdo sostenido + arrastrar
```

Se usan pointer events:

- `pointerdown`
- `pointermove`
- `pointerup`
- `pointercancel`
- `lostpointercapture`

La imagen tiene `draggable="false"` y `@dragstart.prevent` para evitar arrastre nativo.

## Cursores

Cuando `imageZoom <= 1`:

```text
cursor default
```

Cuando `imageZoom > 1`:

```text
cursor grab
```

Durante el arrastre:

```text
cursor grabbing
```

## Limites del pan

Los limites se calculan desde:

- `imageRenderedSize.width`
- `imageRenderedSize.height`
- `imageZoom`
- `imageRotation`

Para rotaciones `90` y `270`, el calculo usa la caja visible rotada de forma conservadora intercambiando ancho y alto antes de aplicar zoom.

Formula conceptual:

```text
transformedWidth = rotatedSideways ? height * zoom : width * zoom
transformedHeight = rotatedSideways ? width * zoom : height * zoom

maxX = max(0, (transformedWidth - width) / 2)
maxY = max(0, (transformedHeight - height) / 2)
```

El pan queda limitado a:

```text
-maxX <= panX <= maxX
-maxY <= panY <= maxY
```

Al cambiar zoom, rotar o recalcular medidas del visor, el pan se vuelve a limitar con `clampImagePan()`.

## Rotacion

`Rotar` mantiene incrementos de `90` grados.

El pan sigue aplicandose sobre el mismo wrapper comun; por tanto la alineacion imagen-overlay se conserva. Los limites consideran rotaciones `0`, `90`, `180` y `270`.

## Ajustar

`Ajustar` restaura:

```text
imageZoom = 1
imageRotation = 0
panX = 0
panY = 0
isPanning = false
```

## Cambio de muestra

Al seleccionar otra muestra se reutiliza `resetImageView()`, por lo que se reinician:

- Zoom.
- Rotacion.
- Pan.
- Estado de arrastre.

## Validacion automatica

Comando:

```powershell
npm.cmd run build
```

Resultado:

- En sandbox fallo por el bloqueo conocido de Vite/esbuild al resolver `vite.config.js`.
- Fuera del sandbox: PASS, build generado correctamente.
- Advertencia no bloqueante: PowerShell no pudo cargar `profile.ps1` por politica local de ejecucion de scripts despues del build.

## Checklist manual

1. Zoom In: `1.0 -> 1.25 -> 1.5 -> 1.75 -> 2.0`.
2. Confirmar que Zoom In no supera `2.0`.
3. Zoom Out: `2.0 -> 1.75 -> 1.5 -> 1.25 -> 1.0`.
4. Confirmar que Zoom Out no baja de `1.0`.
5. En `1.0`, confirmar que pan no se activa.
6. En `>1.0`, arrastrar la imagen y confirmar cursor `grab/grabbing`.
7. Confirmar que imagen y overlay permanecen alineados durante pan.
8. Confirmar que no se puede perder completamente la imagen fuera del visor.
9. Probar `zoom + rotar + pan` en `0`, `90`, `180` y `270` grados.
10. Probar `Ajustar` y confirmar `zoom=1`, `rotation=0`, `pan=0,0`.
11. Cambiar de muestra y confirmar reset completo.
12. Confirmar que `Capas visibles` siguen funcionando despues de zoom/pan.
13. Probar viewport `1366x768`.
14. Confirmar que no aparece scroll horizontal global nuevo.

## Limitaciones conocidas

- Los limites de pan con rotacion usan una caja conservadora basada en rotaciones de `90` grados.
- No se agrego soporte tactil avanzado, aunque el uso de pointer events deja una base compatible.
- No se agrego paneo con teclado, rueda del mouse, minimap ni slider de zoom.

## Pendientes

- Validacion manual con overlay real y rotaciones en `90`/`270`.
- Evaluar en un sprint posterior soporte tactil fino si la UI se usa en tablets.
