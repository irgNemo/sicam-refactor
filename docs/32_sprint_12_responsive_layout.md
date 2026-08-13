# Sprint 12 - Responsive Laptop/Desktop Layout

## Fecha

2026-08-12

## Alcance

Ajuste de layout/CSS para que la pantalla de segmentacion sea operable a `100%` de zoom del navegador en laptop y desktop.

No se modificaron backend, APIs, normalizador, microservicios, modelos, contratos, logica de segmentacion, coordenadas del overlay, SVG, zoom, rotacion ni ajuste.

## Causas Raiz

La pantalla exigia mas ancho y alto del disponible en laptops porque combinaba contenedores fijos con ausencia de breakpoints:

- `.app` usaba `height: calc(100vh - 60px)`.
- `.content` usaba `height: 100vh`, ignorando que ya estaba dentro de `.app`.
- `body` bloqueaba el scroll con `overflow: hidden`.
- `.sidebar` tenia `width: 340px` fijo.
- `.gallery-column` tenia `width: 240px` fijo.
- `.viewer-column` imponia `min-height: 700px`.
- `.objects-card` imponia `height: 250px`.
- Faltaban `min-width: 0` en hijos flex/grid relevantes.

## Reglas CSS Reemplazadas

### Altura global

- `body` ahora permite scroll normal con `overflow: auto`.
- `.app` usa `min-height: calc(100vh - 60px)` en lugar de altura fija.
- `.content` ya no usa `height: 100vh`; ahora respeta el espacio disponible y puede crecer.

### Sidebar

- `.sidebar` reemplazo ancho fijo por:

```css
width: clamp(300px, 24vw, 340px);
flex: 0 0 clamp(300px, 24vw, 340px);
```

- En laptop usa `260px` a `280px`.
- En `< 1024px` se apila arriba y limita su altura con scroll interno.

### MainContent

- `.layout-grid` paso a CSS Grid con:

```css
grid-template-columns: 240px minmax(0, 1fr);
```

- `.split-view` paso a CSS Grid con:

```css
grid-template-columns: minmax(0, 1fr) minmax(300px, 0.62fr);
```

- Se agregaron `min-width: 0` en contenedores clave.
- `.viewer-column` ya no fuerza `min-height: 700px`.
- `.main-card` usa un minimo flexible con `clamp()`.
- `.objects-card` ya no usa `height: 250px`; ahora usa `height: auto` y `min-height`.

## Breakpoints

### `>= 1440px`

Se conserva el aspecto desktop lo mas cercano posible:

- sidebar amplio;
- galeria de `240px`;
- visor y panel derecho en dos columnas;
- `Objetos Detectados` debajo del visor.

### `1024px - 1439px`

Modo laptop compacto:

- sidebar entre `260px` y `280px`;
- galeria entre `176px` y `196px`;
- galeria con thumbnails en dos columnas;
- gaps y paddings reducidos;
- panel derecho entre `280px` y `320px`;
- visor flexible;
- `Objetos Detectados` a ancho completo debajo.

### `< 1024px`

Fallback basico:

- `.app` se apila verticalmente;
- sidebar se coloca arriba con altura maxima y scroll interno;
- galeria se coloca encima del visor;
- imagen y panel derecho se apilan;
- `Objetos Detectados` queda debajo;
- no se implemento un rediseño movil completo.

## Validacion Automatica

```powershell
npm.cmd run build
```

Resultado:

```text
PASS
```

Nota: el build dentro del sandbox fallo por el problema conocido de permisos de Windows/esbuild al resolver `vite.config.js`. Ejecutado fuera del sandbox, el build paso correctamente.

## Checklist Manual

Validar a `100%` de zoom del navegador:

- `1366x768`
- `1280x800`
- `1440x900`
- `1024x768`

Verificar:

- TopBar completo.
- Sidebar usable.
- Galeria visible.
- Imagen visible.
- Panel derecho usable.
- `Objetos Detectados` accesible.
- Sin scroll horizontal global.
- Scroll vertical funcional cuando falte alto.
- Overlay alineado.
- `Zoom`, `Rotar` y `Ajustar` correctos.
- Cambio de muestra mantiene layout estable.

## Limitaciones

- No se hizo validacion visual automatizada con capturas.
- El rango `< 1024px` tiene fallback basico, no una experiencia movil completa.
- En laptops muy bajas puede haber scroll vertical, lo cual queda permitido por criterio del sprint.

## Conclusion

Sprint 12 queda implementado a nivel CSS/layout y listo para validacion manual en navegador.
