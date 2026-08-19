# Sprint 13E - Validacion experta BORRADOR a VALIDADA

## Objetivo

Sprint 13E cierra el ciclo editorial minimo de una revision experta:

```text
BORRADOR -> VALIDADA
```

No implementa resultado efectivo. En este sprint, `NAVIGATE` continua mostrando el resultado automatico de `ResultadoSegmentacion`.

## Contrato backend verificado

Endpoint usado:

```text
POST /api/revisiones-segmentacion/{id}/validar/
```

Implementacion verificada:

```text
apps/web/Backend/api/views.py
RevisionSegmentacionViewSet.validar()
```

Comportamiento real:

- exito: HTTP 200 con `RevisionSegmentacionSerializer`;
- si la revision ya esta `VALIDADA`: HTTP 409;
- si `resultado_editado` no valida: HTTP 400;
- asigna `estado = VALIDADA`;
- asigna `validado_en`;
- recalcula `resumen`;
- no modifica `ResultadoSegmentacion.respuesta_json`;
- no modifica `ResultadoSegmentacion.resultado_normalizado`.

Campos relevantes devueltos por serializer:

- `id_revision_segmentacion`;
- `resultado_segmentacion`;
- `numero_revision`;
- `estado`;
- `resultado_editado`;
- `resumen`;
- `creado_en`;
- `actualizado_en`;
- `validado_en`.

## Servicio frontend

Se agrego:

```text
validateRevision(revisionId)
```

en:

```text
apps/web/Frontend/src/services/segmentationRevisionService.js
```

La funcion usa el `apiClient` existente y hace:

```text
POST /api/revisiones-segmentacion/{revisionId}/validar/
```

No envia `resultado_editado` y no hace `PATCH` implicito.

## Condicion canValidateRevision

La validacion solo se habilita cuando:

```text
viewerMode === EDIT
editorTool in SELECT, VERTEX
activeRevision.estado === BORRADOR
isDraftDirty === false
draftPolygonPoints.length === 0
isValidatingRevision === false
no hay draftPointDrag
no hay vertexDrag
no hay pan activo
```

Si hay cambios sin guardar, se muestra:

```text
Guarda los cambios antes de validar la revision.
```

Si hay una mascara en construccion:

```text
Finaliza o cancela la mascara en construccion antes de validar.
```

## Confirmacion

Antes del POST se usa confirmacion explicita con `window.confirm`.

El texto deja claro que:

- la revision quedara `VALIDADA`;
- ya no podra editarse;
- el resultado automatico se conserva como referencia historica.

No afirma que la revision validada sustituya al resultado automatico.

## Flujo de exito

Despues de una respuesta exitosa:

- `activeRevision` toma la respuesta del backend;
- `activeRevision.estado` queda como `VALIDADA`;
- `workingObjects` se sincroniza desde `activeRevision.resultado_editado.objects`;
- `isDraftDirty = false`;
- `undoStack` y `redoStack` se limpian;
- se limpian selecciones e interacciones temporales;
- `pendingDraftRevision = null`;
- `latestValidatedRevision` toma la revision validada;
- `viewerMode = NAVIGATE`;
- `editorTool = SELECT`.

La salida a `NAVIGATE` evita dejar controles editoriales sobre una revision inmutable.

## Flujo de error

Si el POST falla:

- la UI permanece en `EDIT`;
- `activeRevision` sigue siendo el BORRADOR local;
- `workingObjects` no se pierde;
- `isDraftDirty` no cambia;
- Undo/Redo no se limpian;
- se muestra un mensaje util.

Si el backend responde HTTP 409, se muestra:

```text
La revision ya no esta disponible como BORRADOR.
```

y se refresca el estado auxiliar de revisiones.

## Inmutabilidad

Una revision `VALIDADA` no queda editable en la UI porque la vista regresa a `NAVIGATE`.

El backend tambien bloquea:

- `PATCH` contra revision `VALIDADA`;
- segundo `POST validar` contra una revision ya `VALIDADA`.

## latestValidatedRevision

La consulta existente:

```text
GET /api/resultados-segmentacion/{id}/revisiones/
```

se reutiliza para distinguir:

- `pendingDraftRevision`;
- `latestValidatedRevision`.

`latestValidatedRevision` se selecciona explicitamente por mayor `numero_revision`, no por orden implicito del arreglo.

Prioridad visual:

- si existe BORRADOR, se muestra `Revision pendiente`;
- si no existe BORRADOR y existe VALIDADA, se muestra `Revision validada`.

## Separacion 13E vs 13F

Validar una revision no modifica `ResultadoSegmentacion.resultado_normalizado` ni `respuesta_json`.

En Sprint 13E `NAVIGATE` continua mostrando el resultado automatico. La seleccion del resultado efectivo se implementara en Sprint 13F.

## Nueva revision posterior

Despues de validar `Revision #1`, si el usuario pulsa `Editar`, el frontend no reutiliza la revision `VALIDADA`.

Se usa el flujo backend existente:

```text
POST /api/resultados-segmentacion/{id}/revisiones/
```

El backend debe crear `Revision #2 BORRADOR` partiendo del snapshot de la ultima revision `VALIDADA`.

## Tests backend existentes inspeccionados

La suite existente en `apps/web/Backend/api/tests.py` cubre:

- BORRADOR a VALIDADA;
- asignacion de `validado_en`;
- inmutabilidad de `VALIDADA`;
- segundo validar devuelve conflicto;
- siguiente BORRADOR posterior a VALIDADA parte de la revision validada;
- listado de revisiones ordenado.

No se modifico backend y no se agregaron tests backend en este sprint.

## Validacion manual requerida

1. Editar una revision BORRADOR.
2. Hacer cambios y confirmar que `Validar revision` queda deshabilitado.
3. Guardar borrador.
4. Confirmar que `Validar revision` queda habilitado.
5. Abrir confirmacion y cancelar; nada debe cambiar.
6. Confirmar validacion; debe volver a `NAVIGATE`.
7. Ver indicador `Revision validada`.
8. Confirmar que `NAVIGATE` sigue mostrando automatico.
9. Pulsar `Editar` otra vez y confirmar `Revision #2 - BORRADOR`.
10. Confirmar que #2 parte del snapshot validado de #1.
11. Probar DRAW incompleto: validar no debe estar disponible.
12. Simular error/409 si es posible y confirmar que no se pierde trabajo.

## Limitaciones

Sprint 13E no implementa:

- resultado efectivo;
- uso de VALIDADA como overlay oficial en `NAVIGATE`;
- cambios en Resumen del Caso;
- roles/permisos;
- autor de validacion;
- firma digital;
- rechazo de revision;
- reportes CSV/PDF.
