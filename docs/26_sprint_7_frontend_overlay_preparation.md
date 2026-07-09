# Sprint 7 - Frontend Overlay Preparation

## Fecha

2026-07-08 20:56:59 -06:00

## Referencia Git

- Rama: `master`
- Commit: `a4d7c6f`

## Objetivo

Preparar el frontend para dibujar en un sprint posterior los poligonos de `resultado_normalizado.objects[].geometry.points` sobre la imagen seleccionada.

En este sprint no se implemento overlay visual final, no se dibujaron poligonos y no se agrego edicion manual.

## Archivos modificados

- `apps/web/Frontend/src/components/MainContent.vue`

No se modificaron:

- `apps/web/Frontend/src/services/segmentationService.js`
- `apps/web/Frontend/package.json`
- backend
- microservicios
- endpoints

## Medicion de imagen

Se agrego `ref` y evento `load` al elemento principal de imagen:

```vue
ref="mainImage"
@load="onMainImageLoad"
```

Estado agregado:

```javascript
imageNaturalSize = { width: 0, height: 0 }
imageRenderedSize = { width: 0, height: 0 }
```

La medicion usa:

- `image.naturalWidth`;
- `image.naturalHeight`;
- `image.getBoundingClientRect().width`;
- `image.getBoundingClientRect().height`.

La medicion se recalcula:

- cuando carga la imagen;
- al seleccionar una nueva muestra;
- al cambiar el tamano de ventana mediante `resize`.

Al desmontar el componente se remueve el listener de `resize`.

## Calculo de escala

El diagnostico calcula:

```text
scaleX = renderedWidth / naturalWidth
scaleY = renderedHeight / naturalHeight
```

Si falta algun tamano o alguno es `0`, la escala se reporta como:

```text
No disponible
```

## Validacion y escalamiento de puntos

Funciones agregadas:

```javascript
validPolygonPoints(points)
scalePoint(point)
scalePolygonPoints(points)
```

Reglas:

- `points` debe ser arreglo;
- cada punto valido debe ser arreglo con al menos dos coordenadas;
- las dos primeras coordenadas deben ser numericas;
- puntos invalidos se ignoran;
- solo se consideran objetos con `geometry.type === "polygon"`;
- no se valida si el poligono esta cerrado o si la geometria es correcta.

## Diagnostico mostrado en UI

Se agrego una seccion compacta:

```text
Diagnostico de overlay
```

La UI muestra:

- tamano natural;
- tamano renderizado;
- escala X;
- escala Y;
- numero de objetos con `geometry.type = "polygon"`;
- numero de objetos con puntos validos;
- primeros puntos escalados del primer poligono valido, si existen.

Si no hay `resultado_normalizado`, muestra:

```text
Sin resultado normalizado para diagnosticar coordenadas.
```

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
dist/assets/index-Dxi5datU.css
dist/assets/index-D3QCQ89H.js
built in 1.23s
```

Advertencia no bloqueante:

```text
PowerShell no pudo cargar profile.ps1 por Execution_Policies.
```

La advertencia no impidio el build.

## Limitaciones

- No se dibujan poligonos.
- No se dibujan mascaras.
- No se agregan overlays sobre la imagen.
- No se agrega edicion manual.
- La medicion usa el rectangulo del elemento `<img>`.
- Como la imagen usa `object-fit: contain`, todavia no se calculan offsets internos de letterboxing.
- No se valida cierre de poligonos.
- No se validan coordenadas fuera de rango.
- No se agregan dependencias.

## Resultado general

PASS WITH WARNINGS

El frontend queda preparado para diagnosticar escala y puntos transformados antes de implementar un overlay real.

## Pendientes para Sprint 8

- Calcular la caja visible real de la imagen bajo `object-fit: contain`.
- Calcular offsets internos por letterboxing.
- Dibujar poligonos sobre la imagen usando coordenadas escaladas y offset.
- Agregar controles de visibilidad por etiqueta.
- Mantener diagnostico mientras se valida el overlay visual.
