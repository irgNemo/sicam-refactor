# Sprint 6 - Frontend Normalized Segmentation Result Display

## Fecha

2026-07-08 19:45:55 -06:00

## Referencia Git

- Rama: `master`
- Commit: `c3e8f75`

## Objetivo

Actualizar el frontend para mostrar informacion basada en `resultado_normalizado`, sin dibujar poligonos, mascaras ni overlays sobre la imagen.

## Archivos modificados

- `apps/web/Frontend/src/components/MainContent.vue`

No se modificaron:

- `apps/web/Frontend/src/services/apiClient.js`
- `apps/web/Frontend/src/services/segmentationService.js`
- `apps/web/Frontend/package.json`
- backend
- microservicios

## Comportamiento agregado

Se agrego una seccion compacta:

```text
Resultado normalizado
```

La seccion se muestra cuando existe un resultado activo de segmentacion:

- ultimo resultado historico persistido, si existe;
- respuesta inmediata de `POST /api/muestras/{id}/segmentar/`, si aun no hay historial cargado.

Cuando existe `resultado_normalizado`, la UI muestra:

- version;
- tipo de muestra;
- total de objetos;
- conteo por etiqueta;
- lista compacta de hasta 5 objetos normalizados.

La lista compacta muestra:

```text
ID | Etiqueta | Geometria | Puntos
```

El numero de puntos se calcula desde:

```text
geometry.points.length
```

si `geometry.points` existe y es arreglo.

## Uso de resultado_normalizado

La fuente principal es:

```text
resultado_normalizado
```

Campos usados:

```text
version
sample_type
summary.total_objects
summary.counts_by_label
objects
objects[].id
objects[].label
objects[].geometry.type
objects[].geometry.points
```

No se interpreta ni valida geometricamente el poligono en el frontend.

## Fallback para historicos sin normalizacion

Si un resultado no tiene `resultado_normalizado`, la UI muestra:

```text
Este resultado no tiene representacion normalizada.
```

Tambien mantiene un conteo heredado usando:

- `respuesta_json.objetos.length` para resultados historicos;
- `objetos.length` para la respuesta inmediata del `POST`.

Esto mantiene compatibilidad con resultados persistidos antes de Sprint 5.

## Endpoints consumidos

Sin cambios respecto a sprints previos:

```text
POST /api/muestras/{id}/segmentar/
GET /api/muestras/{id}/resultados-segmentacion/
```

El frontend sigue consumiendo solo Django REST.

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
dist/assets/index-floIN92a.css
dist/assets/index-B4ht6ZBH.js
built in 1.07s
```

Advertencias no bloqueantes:

```text
PowerShell no pudo cargar profile.ps1 por Execution_Policies.
npm aviso una nueva version mayor disponible.
```

Ninguna advertencia impidio el build.

## Limitaciones

- Solo se muestran hasta 5 objetos normalizados.
- No se dibujan poligonos.
- No se dibujan mascaras.
- No se agregan overlays sobre la imagen.
- No se agrega edicion manual.
- No se valida geometria en frontend.
- No se modifica el resumen global del sidebar.
- No se agregan dependencias.

## Resultado general

PASS WITH WARNINGS

El frontend ya muestra resultados normalizados cuando estan disponibles y mantiene compatibilidad con resultados historicos sin `resultado_normalizado`.

## Pendientes para Sprint 7

- Definir si se renderizara una tabla completa de objetos.
- Preparar visualizacion de `geometry.points` sobre la imagen.
- Definir escala/coordenadas de imagen antes de dibujar overlays.
- Evaluar controles de visibilidad por etiqueta.
- Mantener fallback para historicos con `resultado_normalizado = null`.
