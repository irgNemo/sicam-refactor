# Sprint 12C - Resumenes operativos de muestra y caso

## Fecha

2026-08-13 11:11:46 -06:00

## Referencia Git

- Rama: `master`
- Commit base observado: `0aad47b`

## Objetivo

Agregar resumenes operativos basados en resultados normalizados persistidos, sin modificar microservicios, algoritmos, modelos ni endpoints existentes.

## Backend

Se agrego el endpoint:

```text
GET /api/casos/{id}/resumen-segmentacion/
```

La accion se implemento en `CasoViewSet` y resume las muestras de saliva asociadas al caso mediante `AnalisisPred`.

Contrato de respuesta:

```json
{
  "caso_id": 3,
  "total_muestras": 38,
  "muestras_segmentadas": 12,
  "muestras_pendientes": 25,
  "muestras_resultado_invalido": 1,
  "counts_by_label": {
    "membrana": 180,
    "nucleo": 142,
    "micronucleo": 27
  },
  "total_objects": 349
}
```

La regla operativa queda preservada:

```text
muestras_segmentadas + muestras_pendientes + muestras_resultado_invalido = total_muestras
```

## Politica de seleccion de resultados

Por cada `MuestraSaliva`, el backend selecciona como maximo un `ResultadoSegmentacion`:

- Solo considera resultados con `estado="COMPLETADO"`.
- Ordena por `-creado_en`, `-id_resultado_segmentacion`.
- Si existe un resultado `ERROR` mas reciente, usa el `COMPLETADO` previo.
- Si el `COMPLETADO` mas reciente es invalido, la muestra se clasifica como `muestras_resultado_invalido` y no se hace fallback a resultados validos anteriores.

La consulta usa `OuterRef` y `Subquery` para obtener el ultimo resultado completado por muestra, evitando consultas N+1 sobre historiales completos.

## Validacion de resumen normalizado

Un resultado es utilizable si:

- `resultado_normalizado` es un objeto JSON.
- `summary` es un objeto.
- `summary.counts_by_label` es un objeto.
- Los conteos son numericos.
- `summary.total_objects` es numerico o puede calcularse desde `counts_by_label`.
- Si `summary.total_objects` existe, debe ser coherente con la suma de conteos.

Las etiquetas faltantes se reportan como `0`.

No se exige `version="1.1"`; se aceptan historicos `1.0` si cumplen la estructura.

## Frontend

`MainContent.vue` dejo de usar resultados heredados de `imagenSeleccionada.resultados?.[0]` para `Resumen de Conteo`.

Ahora usa:

```text
resultadoNormalizadoActivo.summary
```

El resultado activo sigue siendo:

```text
ultimoResultadoSegmentacion || segmentacionResultado
```

El resumen muestra:

- Membranas
- Nucleos
- Micronucleos
- Total

Si no existe `resultado_normalizado` activo, se mantiene el estado vacio.

`SideBar.vue` consume el nuevo endpoint de caso y muestra:

- Imagenes totales.
- Muestras segmentadas.
- Muestras pendientes.
- Membranas.
- Nucleos.
- Micronucleos.
- Indicador discreto para resultados no utilizables.

Despues de una segmentacion exitosa, `MainContent.vue` emite `segmentation-completed`, `App.vue` coordina el evento y `SideBar.vue` refresca el resumen del caso seleccionado.

## Archivos modificados

- `apps/web/Backend/api/views.py`
- `apps/web/Backend/api/tests.py`
- `apps/web/Frontend/src/App.vue`
- `apps/web/Frontend/src/components/MainContent.vue`
- `apps/web/Frontend/src/components/SideBar.vue`
- `apps/web/Frontend/src/services/segmentationService.js`
- `docs/34_sprint_12c_operational_summaries.md`

## Pruebas agregadas

Se agregaron pruebas para:

- Caso inexistente devuelve `404`.
- Caso sin muestras devuelve resumen en ceros.
- Muestras sin resultados quedan pendientes.
- Resultado completado valido cuenta como segmentado.
- Agregacion de multiples muestras.
- Uso exclusivo del ultimo `COMPLETADO`.
- Uso del `COMPLETADO` previo cuando el ultimo registro es `ERROR`.
- `COMPLETADO` invalido mas reciente no hace fallback.
- Compatibilidad con `version="1.0"`.
- Compatibilidad con `version="1.1"`.
- Etiquetas faltantes reportadas como `0`.
- `total_objects` faltante calculado desde conteos.
- Resumen invalido sin romper endpoint.
- Conteos no numericos marcados como invalidos.
- `total_objects` incoherente marcado como invalido.

## Validaciones ejecutadas

Backend:

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' manage.py check
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' manage.py makemigrations --check
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -m pytest
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' manage.py test
```

Resultados:

- `manage.py check`: PASS.
- `makemigrations --check`: PASS, sin cambios detectados.
- `pytest`: PASS, `68 passed, 2 skipped`.
- `manage.py test`: PASS, `50 tests`.

Frontend:

```powershell
npm.cmd run build
```

Resultado:

- En sandbox fallo por el bloqueo conocido de Vite/esbuild al resolver `vite.config.js`.
- Fuera del sandbox: PASS, build generado correctamente.
- Advertencia no bloqueante: PowerShell no pudo cargar `profile.ps1` por politica local de ejecucion de scripts despues del build.

## Checklist manual

- Seleccionar paciente y caso con muestras.
- Confirmar que `Resumen del Caso` muestra total de imagenes.
- Confirmar que segmentadas, pendientes e invalidas suman el total.
- Ejecutar segmentacion sobre una muestra.
- Confirmar que `Resumen de Conteo` usa el resultado normalizado activo.
- Confirmar que `Resumen del Caso` se refresca tras la segmentacion.
- Confirmar que historicos `1.0` siguen mostrando conteos si tienen `summary` valido.
- Confirmar que historicos sin `resultado_normalizado` conservan el estado vacio en el resumen de conteo.

## Limitaciones

- El resumen de caso aun esta centrado en `MuestraSaliva`.
- No integra sangre todavia.
- No persiste ni corrige historicos invalidos.
- No realiza backfill de resultados anteriores.
- No agrega visualizaciones nuevas sobre el overlay.

## Pendientes

- Validacion manual end-to-end con varias imagenes y resultados historicos mixtos.
- Evaluar si en un sprint posterior se agrega una API comun cuando exista `ImagenMuestra`.
- Definir politica de backfill si se decide normalizar historicos antiguos.
