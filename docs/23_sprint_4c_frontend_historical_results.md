# Sprint 4C - Frontend Historical Segmentation Results

## Fecha

2026-07-03 19:39:05 -06:00

## Referencia Git

- Rama: `master`
- Commit: `1bb5e7e`

## Objetivo

Actualizar el frontend para consultar y mostrar resultados historicos de segmentacion asociados a la muestra seleccionada, consumiendo unicamente Django REST.

## Servicio modificado

Archivo:

```text
apps/web/Frontend/src/services/segmentationService.js
```

Funcion agregada:

```javascript
obtenerResultadosSegmentacion(muestraId)
```

Endpoint consumido:

```text
GET /api/muestras/{id}/resultados-segmentacion/
```

La funcion usa `apiClient`, por lo que conserva compatibilidad con:

```text
VITE_API_BASE_URL
```

## Componente modificado

Archivo:

```text
apps/web/Frontend/src/components/MainContent.vue
```

El componente mantiene la accion de Sprint 4 para ejecutar:

```text
POST /api/muestras/{id}/segmentar/
```

y ahora tambien consulta el historial persistido con:

```text
GET /api/muestras/{id}/resultados-segmentacion/
```

## Comportamiento de UI

Al seleccionar una muestra:

- se limpia el estado local de segmentacion inmediata;
- se limpia el historial anterior;
- se solicita el historial persistido de la muestra seleccionada.

La UI muestra una seccion compacta:

```text
Historial persistido
```

Estados mostrados:

- `Cargando historial...`;
- error basico si falla el `GET`;
- `Sin resultados historicos` si la lista esta vacia;
- ultimo resultado persistido si existen resultados.

Del ultimo resultado persistido se muestra:

- `id`;
- `estado`;
- `tipo_muestra`;
- `creado_en` formateado con `toLocaleString("es-MX")`;
- conteo basico de `respuesta_json.objetos.length`.

Tambien se muestra el total de resultados historicos cuando la lista no esta vacia.

## Refresco posterior a segmentacion

Despues de una segmentacion exitosa mediante:

```text
POST /api/muestras/{id}/segmentar/
```

el componente vuelve a consultar:

```text
GET /api/muestras/{id}/resultados-segmentacion/
```

Esto permite reflejar el resultado que Django persistio en `ResultadoSegmentacion`.

## Manejo de errores

Si falla la carga de historial, el componente muestra:

```text
No fue posible cargar el historial
```

o el mensaje `error` devuelto por Django si existe.

El error de historial no bloquea la accion de segmentar. El error de segmentacion sigue manejandose de forma separada.

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

Clasificacion: limitacion del sandbox al resolver `vite.config.js` con Vite/esbuild, no error del codigo modificado.

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
dist/assets/index-C-co5_aq.css
dist/assets/index-DcWietAP.js
built in 1.18s
```

Advertencia no bloqueante:

```text
PowerShell no pudo cargar profile.ps1 por Execution_Policies.
```

La advertencia ocurre antes del comando y no impidio el build.

## Limitaciones

- Solo se muestra el ultimo resultado persistido y el total de resultados.
- No se renderiza una tabla historica completa.
- No se visualizan poligonos.
- No se dibujan mascaras.
- No se agrega edicion manual.
- No se modifica backend.
- No se modifican microservicios.
- No se agregan dependencias.
- No se modifica `package.json`.

## Resultado general

PASS WITH WARNINGS

La UI ya consulta y muestra el historial persistido por muestra, y refresca ese historial despues de ejecutar una nueva segmentacion.

## Pendientes

- Definir una vista historica completa si se requiere auditoria visual.
- Definir si se mostrara mas de un resultado persistido.
- Agregar renderizado de objetos, poligonos o mascaras en un sprint dedicado.
- Evaluar refresco de resumenes globales despues de segmentar.
- Mantener el frontend consumiendo solo Django REST.
