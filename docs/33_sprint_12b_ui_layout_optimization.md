# Sprint 12B - UI Layout Optimization

## Fecha

2026-08-13

## Alcance

Optimizacion de jerarquia visual y densidad de informacion en la pantalla de segmentacion.

No se modificaron backend, APIs, modelos, normalizador, microservicios, contratos `1.0/1.1`, persistencia, logica de segmentacion, logica de visibilidad, ni calculo matematico del overlay.

## Informacion Tecnica Retirada

Se retiro de la interfaz visible el bloque `Resultado normalizado`.

Ya no se muestran al usuario final:

- `version` del resultado normalizado.
- `sample_type` tecnico.
- IDs internos.
- tipo de geometria.
- numero de puntos.
- tabla tecnica de objetos normalizados.

La informacion operativa sigue disponible mediante:

- `Resumen de Conteo`.
- `Objetos Detectados`.
- overlay SVG.
- historial compacto.

## Diagnostico de Overlay Retirado

Se retiro de la UI el bloque `Diagnostico de overlay`, incluyendo:

- tamaño natural de imagen;
- tamaño renderizado;
- escala X/Y;
- caja visible;
- offsets;
- conteos de poligonos;
- puntos validos;
- primeros puntos escalados;
- checkbox `Diagnostico visual`;
- rectangulos SVG de diagnostico.

Se preservo la logica funcional necesaria para el overlay:

- `overlayContainment`;
- `validPolygonPoints`;
- `scalePoint`;
- `scalePolygonPoints`;
- `overlayDrawableObjects`;
- `overlayVisibleDrawableObjects`;
- `overlayPolygons`;
- `image-transform-layer`;
- SVG operativo;
- zoom, rotacion y ajuste.

## Cambios del Visor

El visor dejo de depender de un contenedor excesivamente alto.

Cambios principales:

- `.main-card` ya no fuerza un minimo alto grande.
- `.img-placeholder` usa altura responsive:

```css
height: clamp(380px, 50vh, 560px);
```

- En laptop `1024px - 1439px`, la altura baja a:

```css
height: clamp(320px, 46vh, 460px);
```

- En `< 1024px`, usa:

```css
height: clamp(300px, 50vh, 420px);
```

Esto reduce espacio vacio vertical y hace que la imagen aparezca antes en la primera pantalla.

## Scroll Interno de Galeria

La galeria ya no debe alargar la pagina segun el numero de imagenes.

Cambios:

- `.gallery-column` tiene `max-height` responsive.
- `.gallery-header` permanece visible como encabezado.
- `.gallery-grid` mantiene scroll vertical interno con `overflow-y: auto`.
- Se preserva seleccion de imagen, estado activo y thumbnails existentes.

## Historial Compacto

Se conserva la funcionalidad de historial persistido, pero con presentacion compacta.

Antes mostraba una tarjeta extensa con:

- estado;
- tipo;
- fecha;
- objetos;
- ultimo resultado.

Ahora muestra:

```text
Ultima segmentacion
fecha · objetos · estado
```

Tambien conserva el indicador del numero de resultados historicos.

## Componentes y Logica Preservados

Se preservo:

- ejecucion de segmentacion;
- carga de historial;
- overlay SVG;
- visibilidad por etiquetas desde `Objetos Detectados`;
- conteos de objetos por etiqueta;
- zoom;
- rotacion;
- ajuste;
- resize;
- seleccion de imagenes;
- responsive de Sprint 12.

## Validacion Automatica

```powershell
npm.cmd run build
```

Resultado:

```text
PASS
```

Nota: dentro del sandbox fallo por el problema conocido de permisos de Windows/esbuild al resolver `vite.config.js`. Ejecutado fuera del sandbox, el build paso correctamente.

## Checklist Manual

Validar a `100%` de zoom:

### Entrada a muestra

- La imagen es visible sin desplazarse mucho.
- No hay gran espacio vacio arriba de la imagen.

### Galeria

- Encabezado `Galeria` visible.
- Contador visible.
- Thumbnails con scroll vertical interno.
- Seleccionar imagenes sigue funcionando.
- La galeria no determina la altura total de la pagina.

### Panel derecho

- No aparece `Resultado normalizado`.
- No aparece `Diagnostico de overlay`.
- `Resumen de Conteo` permanece.
- Ejecutar segmentacion permanece.
- Historial aparece compacto.

### Overlay

- Overlay alineado.
- Visibilidad por etiquetas funciona.
- `Zoom` funciona.
- `Rotar` funciona.
- `Ajustar` funciona.
- Resize conserva alineacion.

### Responsive

- `1366x768`.
- `1280x800`.
- `1440x900`.
- Sin scroll horizontal global.
- Scroll vertical permitido si falta alto.

## Limitaciones

- No se agrego modal ni selector avanzado de historial.
- No se implemento paginacion ni lazy loading de galeria.
- No se realizo validacion visual automatizada con capturas.
- El diagnostico visual del overlay fue retirado de la UI operativa; puede recuperarse en un sprint futuro como modo de desarrollador si hace falta.

## Conclusion

Sprint 12B queda implementado como optimizacion de UI y layout, manteniendo intacta la funcionalidad validada end-to-end.
