# Sprint 13F - Resultado efectivo VALIDADA sobre AUTOMATICO

## Objetivo

Sprint 13F introduce el concepto de resultado efectivo para un `ResultadoSegmentacion`.

El resultado efectivo es una resolucion calculada; no se persiste como una copia adicional.

## Definicion

Para un `ResultadoSegmentacion` concreto:

```text
si existe una o mas RevisionSegmentacion VALIDADA:
    resultado efectivo = RevisionSegmentacion VALIDADA con mayor numero_revision
si no existe VALIDADA:
    resultado efectivo = resultado_normalizado automatico
```

Una revision `BORRADOR` nunca se utiliza como resultado efectivo.

## Servicio backend

Se creo:

```text
apps/web/Backend/api/services/segmentation/effective.py
```

Funciones principales:

```text
get_latest_validated_revision(resultado_segmentacion)
resolve_effective_segmentation(resultado_segmentacion)
```

La prioridad `VALIDADA > AUTOMATICO` queda centralizada en backend para evitar duplicarla en views, serializers o frontend.

## Contrato API

Se agrego el endpoint:

```text
GET /api/resultados-segmentacion/{id}/efectivo/
```

Respuesta sin revision validada:

```json
{
  "resultado_segmentacion_id": 123,
  "fuente": "AUTOMATICO",
  "revision": null,
  "resultado": {},
  "resumen": {}
}
```

Respuesta con revision validada:

```json
{
  "resultado_segmentacion_id": 123,
  "fuente": "VALIDADA",
  "revision": {
    "id_revision_segmentacion": 45,
    "numero_revision": 2,
    "estado": "VALIDADA",
    "validado_en": "..."
  },
  "resultado": {},
  "resumen": {}
}
```

Cuando `fuente` es `VALIDADA`, `resultado` es exactamente `RevisionSegmentacion.resultado_editado` y `resumen` es `RevisionSegmentacion.resumen`.

Cuando `fuente` es `AUTOMATICO`, `resultado` es `ResultadoSegmentacion.resultado_normalizado` y `resumen` es su `summary`.

## NAVIGATE

En `NAVIGATE`, el overlay y el `Resumen de Conteo` ahora consumen el mismo resultado efectivo:

```text
effectiveSegmentation.resultado.objects
effectiveSegmentation.resumen
```

Esto evita combinaciones inconsistentes como overlay validado con conteo automatico.

Si no existe revision validada, la vista conserva el comportamiento anterior usando el automatico.

Si existe revision validada, se muestra:

```text
Resultado mostrado: Revision #N validada
```

Si no existe revision validada, se muestra:

```text
Resultado mostrado: Automatico
```

## EDIT

`EDIT` mantiene la semantica previa:

```text
EDIT -> workingObjects del BORRADOR
```

No usa `effectiveSegmentation` para construir manualmente el estado editorial. El backend sigue decidiendo desde que snapshot nace una nueva revision.

Caso importante:

```text
#1 VALIDADA
#2 BORRADOR
```

Resultado:

- `NAVIGATE` muestra `#1 VALIDADA`;
- `EDIT` muestra `#2 BORRADOR`;
- `BORRADOR` no altera el resultado oficial.

## Resumen del Caso

`GET /api/casos/{id}/resumen-segmentacion/` mantiene la politica existente para elegir el `ResultadoSegmentacion` por muestra:

```text
ultimo ResultadoSegmentacion COMPLETADO por muestra
```

Para ese resultado seleccionado, ahora usa `resolve_effective_segmentation(...)` y suma el `resumen` efectivo.

No se cambio la politica entre multiples corridas automaticas.

## Estrategia ORM

Para `Resumen del Caso`, los resultados seleccionados se cargan con `prefetch_related` filtrado a revisiones `VALIDADA` y ordenado por `-numero_revision`.

Esto evita resolver la ultima revision validada con una query independiente por cada muestra.

## Historial y legacy

El resultado efectivo se resuelve por `ResultadoSegmentacion`, no por muestra completa.

Si el usuario selecciona un resultado historico especifico, `/efectivo/` resuelve las revisiones asociadas a ese resultado concreto.

Sin revision validada, siguen soportados automaticos `resultado_normalizado` version `1.0` y `1.1`.

Con revision validada creada sobre legacy, el resultado efectivo usa el snapshot editorial validado.

## Inmutabilidad

Sprint 13F no modifica:

- `ResultadoSegmentacion.respuesta_json`;
- `ResultadoSegmentacion.resultado_normalizado`;
- `RevisionSegmentacion.resultado_editado`;
- modelos;
- migraciones.

No hubo backfill.

## Frontend

Se agrego estado separado:

```text
effectiveSegmentation
effectiveSegmentationLoading
effectiveSegmentationError
```

No se reutiliza `activeRevision`, porque `activeRevision` representa contexto editorial y `effectiveSegmentation` representa el resultado oficial mostrado.

Al cambiar el resultado activo:

- se limpia el resultado efectivo previo;
- se solicita `/efectivo/`;
- se evita mostrar geometria de otra muestra;
- se ignoran respuestas tardias si ya cambio el resultado activo.

Despues de validar una revision, el frontend refresca:

- `effectiveSegmentation`;
- revisiones pendientes;
- `Resumen del Caso` mediante el evento existente `segmentation-completed`.

## Pruebas

Backend:

- sin revisiones usa `AUTOMATICO`;
- solo `BORRADOR` usa `AUTOMATICO`;
- `VALIDADA` usa su snapshot y resumen;
- `VALIDADA + BORRADOR` usa la `VALIDADA`;
- multiples `VALIDADA` usan mayor `numero_revision`;
- endpoint `/efectivo/` devuelve automatico o validada segun corresponda;
- `Resumen del Caso` suma la revision validada y no el borrador;
- `respuesta_json` y `resultado_normalizado` permanecen intactos.

Frontend:

- `npm.cmd run build` completado correctamente fuera del sandbox.

## Validaciones

Comandos ejecutados:

```powershell
python manage.py check
python manage.py test api
python manage.py makemigrations --check
python -m pytest
python manage.py test
npm.cmd run build
```

Resultados:

- `python manage.py check`: PASS;
- `python manage.py test api`: PASS, 93 tests;
- `python manage.py makemigrations --check`: PASS, `No changes detected`;
- `python -m pytest`: PASS, 111 passed, 2 skipped;
- `python manage.py test`: PASS, 93 tests;
- `npm.cmd run build`: PASS fuera del sandbox.

## Limitaciones

- No se implemento toggle para comparar automatico contra validado.
- No se implemento diff visual.
- No se agrego autor, firma, permisos ni rollback de revisiones.
- No se cambio la politica para elegir entre multiples corridas automaticas de una misma muestra.
- No se backfillearon historicos.

## Checklist manual pendiente

1. Imagen A: crear cambios, guardar, validar y confirmar que `NAVIGATE` muestra inmediatamente la revision validada.
2. Cambiar a Imagen B y volver a Imagen A; confirmar que A sigue mostrando la validada.
3. Crear `BORRADOR` #2 sobre una validada; confirmar que `NAVIGATE` muestra #1 y `EDIT` muestra #2.
4. Validar #2; confirmar que `NAVIGATE` y `Resumen del Caso` pasan a #2.
5. Confirmar que `Capas visibles`, zoom, pan, rotacion y ajuste siguen funcionando.
