# Sprint 4 - Frontend Segmentation Integration

## Fecha

2026-07-02 23:19:18 -06:00

## Referencia Git

- Rama: `master`
- Commit: `9ecd4b9`

## Objetivo

Agregar una integracion frontend minima para invocar desde la UI existente el endpoint Django:

```text
POST /api/muestras/{id}/segmentar/
```

La integracion mantiene a Django como orquestador. El frontend no llama directamente a los microservicios FastAPI.

## Componente modificado

```text
apps/web/Frontend/src/components/MainContent.vue
```

Este componente fue elegido porque ya muestra la galeria de `muestras_saliva`, permite seleccionar una muestra y renderiza la imagen seleccionada.

## Servicio creado

```text
apps/web/Frontend/src/services/segmentationService.js
```

Funcion creada:

```javascript
segmentarMuestra(muestraId)
```

Implementacion:

```javascript
apiClient.post(`/api/muestras/${muestraId}/segmentar/`)
```

El servicio usa `apiClient`, por lo que conserva compatibilidad con:

```text
VITE_API_BASE_URL
```

## Endpoint consumido

```text
POST /api/muestras/{id}/segmentar/
```

La ruta se consume como:

```text
/api/muestras/{id}/segmentar/
```

## Comportamiento de UI

En `MainContent.vue` se agrego una accion minima visible cuando existe una muestra seleccionada:

```text
Ejecutar segmentacion
```

La UI muestra:

- estado de carga: `Segmentando...`;
- error basico si falla la peticion;
- metadata de `resultado_segmentacion` cuando el endpoint responde exitosamente;
- conteo basico de objetos usando `objetos.length`.

Metadata mostrada:

- `resultado_segmentacion.id`;
- `resultado_segmentacion.estado`;
- `resultado_segmentacion.tipo_muestra`;
- conteo de `objetos`.

Al cambiar la muestra seleccionada, el estado local de segmentacion se limpia para evitar mezclar resultados entre imagenes.

## Manejo de errores

Si el backend responde con:

```json
{
  "error": "..."
}
```

la UI muestra ese mensaje. Si no hay mensaje estructurado, usa:

```text
No fue posible segmentar la muestra
```

No se agrego manejo especializado por codigo HTTP en este sprint.

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
dist/assets/index-CoZ5S7ta.css
dist/assets/index-BkprioNj.js
built in 1.12s
```

Advertencia no bloqueante:

```text
PowerShell no pudo cargar profile.ps1 por Execution_Policies.
```

La advertencia ocurre antes del comando y no impidio el build.

## Limitaciones

- No se visualizan poligonos.
- No se dibujan mascaras.
- No se agrego edicion manual de objetos.
- No se consulta historial persistido de `ResultadoSegmentacion`.
- No se actualiza el resumen global del sidebar despues de segmentar.
- No se agregaron rutas nuevas.
- No se modifico `package.json`.
- No se modifico backend.
- No se modificaron microservicios.

## Resultado general

PASS WITH WARNINGS

La integracion frontend minima compila correctamente y queda conectada al endpoint Django mediante `apiClient`.

## Pendientes para el siguiente sprint

- Definir si se consultara historial de `ResultadoSegmentacion`.
- Agregar visualizacion de resultados persistidos si se expone endpoint de lectura.
- Definir estrategia para renderizar objetos, poligonos o mascaras.
- Evaluar refresco de resumenes despues de segmentar.
- Mantener el frontend consumiendo solo Django REST, no microservicios directamente.
