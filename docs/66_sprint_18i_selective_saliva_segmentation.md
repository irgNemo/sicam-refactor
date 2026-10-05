# Sprint 18I — Segmentación selectiva SALIVA

Fecha de validación: 2026-10-04. Baseline: `1a11f71f2d69f294e0b3c9e9eb1efe8e738f695f`.
Implementación y pruebas sintéticas; **no aceptación real**.

## Contrato HTTP

Se conserva `POST /api/muestras/{sample_id}/segmentar/` y el nombre
`segmentation_strategy` (`CURRENT_CUSTOM_V1` / `ALT_CPSAM_MORPHOLOGICAL_V1`).
No se introduce alias `strategy` en la petición.

- `target=ALL` es el default al omitir target. Mantiene respuesta, normalización,
  provenance y creación de una nueva base automática históricas. No sobrescribe
  ni elimina resultados/revisiones anteriores.
- `MEMBRANES`: reemplazar membranas; preservar núcleos y micronúcleos completos.
- `NUCLEI_AND_MICRONUCLEI`: reemplazar N/MN; preservar membranas completas.
- Target inválido: 400. BLOOD rechaza `target` con 400; su frontend no lo envía.

Para parciales, primero obtener
`GET /api/resultados-segmentacion/{result_id}/selective-context/`. Devuelve
`source_token`, `source_kind`, `revision_id`, `revision_updated_at` y `summary`.
La fuente es BORRADOR si existe, última VALIDADA si no, y base en otro caso.

Ejemplo de POST parcial (IDs ilustrativos):

```json
{
  "segmentation_strategy": "ALT_CPSAM_MORPHOLOGICAL_V1",
  "target": "MEMBRANES",
  "resultado_segmentacion_id": 123,
  "source_token": "<SHA-256 devuelto por selective-context>",
  "confirm_replacement": true
}
```

Padre y token son obligatorios para parciales. El padre debe estar COMPLETADO,
ser SALIVA y pertenecer a la muestra. La selección explícita admite resultados
históricos; no sustituye el padre por el último resultado de otra ejecución.
La respuesta 200 contiene `target`, `execution_id`, `resultado_segmentacion`
(mismo padre y origen) y `revision` completa BORRADOR para el editor.

## Merge y estados

`api/services/segmentation/selective.py::perform_partial` orquesta:

1. Transacción corta: lock del padre, preflight, captura de token/snapshot y
   ejecución PENDING con checkpoint durable.
2. Fuera de transacción: llamada completa al microservicio con routing y timeout
   existentes; normalización y validación de toda su respuesta.
3. Nueva transacción corta: lock del mismo padre, revalidación del token, filtro
   de categorías, reserva de IDs, merge y persistencia del BORRADOR + ejecución.

No se envía target al microservicio ni se cambian algoritmos/thresholds.
Los objetos preservados se copian completos: ID, puntos, source, provenance y
metadata. Se mantiene su orden relativo. Se añaden después los nuevos objetos
seleccionados en el orden de su respuesta normalizada. No hay append de la
categoría reemplazada, matching, IoU, asociaciones ni renormalización de los
objetos preservados. Una categoría automática vacía reemplaza por `[]`.

| Fuente | Destino parcial | Effective después del merge |
|---|---|---|
| Base MANUAL | Nuevo BORRADOR | Base MANUAL |
| Base AUTOMATIC | Nuevo BORRADOR | Base AUTOMATIC |
| VALIDADA sin draft | Nuevo BORRADOR desde VALIDADA | Misma VALIDADA |
| BORRADOR, incluso basado en VALIDADA | Mismo BORRADOR | Base/VALIDADA previa |

La base científica (raw, normalizado, strategy, origin, timestamps) y la VALIDADA
no se modifican. Sólo avanza el contador editorial técnico del padre. La
constraint existente garantiza un BORRADOR por resultado. Validar posteriormente
el BORRADOR combinado lo promueve a effective mediante el resolver existente.
No se ejecuta Characterization automáticamente.

## Concurrencia y confirmación

`source_token` es SHA-256 de JSON canónico (`sort_keys=True`, UTF-8,
`ensure_ascii=False`, separadores `(',', ':')`, sin NaN). Incluye identidad,
contenido y timestamp de la base, y IDs/números/estados/timestamps/payloads/resúmenes
de sus revisiones. Está derivado de estado durable, no de memoria del proceso.
Detecta creación de draft, guardado, validación, cambio de fuente o cambio de
contenido durante HTTP. Las reservas de IDs no invalidan el snapshot.

Token discrepante: 409 `SEGMENTATION_SOURCE_CHANGED`, sin aplicar respuesta.
La ejecución iniciada termina CANCELLED. Dos peticiones con el mismo token no
pueden aplicar ambas: la primera cambia el snapshot/versionado.

Todos los escritores editoriales (crear draft, guardar, validar y merge) usan el
mismo lock del padre. En SQLite se adquiere mediante UPDATE neutro al principio
de la transacción; `SELECT FOR UPDATE` solo no protege SQLite. En motores con
locks por fila también serializa al mismo padre. Nunca se retiene durante HTTP.

Guardar y validar desde el frontend envían `expected_updated_at`. Los clientes
históricos pueden omitirlo en revisiones anteriores al flujo selectivo; después
de una ejecución COMPLETED en ese draft se exige la precondición, incluso a un
cliente antiguo (409 `REVISION_PRECONDITION_REQUIRED`). Una precondición obsoleta
rechaza la escritura y no sobrescribe el merge.

Backend exige `confirm_replacement=true` cuando hay objetos seleccionados o un
BORRADOR activo. Frontend confirma reemplazo y posible resultado vacío; para un
draft también informa del checkpoint. Con categoría vacía y sin draft no pide
confirmación. ALL advierte cuando hay objetos existentes y conserva el historial.
Los cambios locales sin guardar, dibujo incompleto, drag o guardado en curso
bloquean la solicitud antes de contactar al backend. Se bloquean interacciones
editoriales durante el cálculo. La confirmación es una precondición explícita de
API; el servidor no puede inspeccionar cambios aún locales al navegador.

## IDs y provenance

`ResultadoSegmentacion.next_editorial_id` es un contador persistente creciente.
La migración lo inicializa por encima de los IDs de base y todas las revisiones.
Las reservas y merges lo actualizan bajo el mismo lock. También avanza al guardar
IDs editoriales de clientes históricos. El dibujo SALIVA reserva un ID mediante
`POST /api/resultados-segmentacion/{id}/reserve-object-id/` antes de finalizar el
polígono. BLOOD conserva su comportamiento. Cancelar después de reservar puede
dejar huecos admisibles; no se reciclan IDs mediante el asignador.

No se puede reconstruir retrospectivamente un ID borrado antes de 0009 si no
quedó en ningún snapshot durable. La garantía de no reutilización del asignador
es prospectiva desde la migración. No es una autenticación de IDs arbitrarios
inventados por clientes externos: éstos siguen sujetos al contrato editorial.

Objetos preservados mantienen su provenance completa. Los automáticos nuevos:

```json
{
  "origin": "automatic",
  "base_object_id": null,
  "strategy": "ALT_CPSAM_MORPHOLOGICAL_V1",
  "segmentation_execution_id": "<UUID>",
  "execution_object_id": 1
}
```

`execution_object_id` referencia al objeto normalizado de esa ejecución;
`source.raw_id` conserva el ID del microservicio, que puede repetirse entre
objetos/clases. No se inventa correspondencia con la base. Se conserva el vínculo
legacy `base_object_id` positivo para objetos automáticos anteriores. El esquema
acepta ambos tipos de provenance. Editar geometría no recalcula su origen.

## Ejecución, checkpoint y recuperación

`SegmentationExecution` guarda UUID, padre/destino, strategy, target, estado,
metadata de solicitud, token de origen, checkpoint, respuesta normalizada,
conteos completos devueltos, timestamps y código de error sanitizado.
Estados: PENDING, COMPLETED, FAILED, CANCELLED.

En parciales se conserva la respuesta completa normalizada para trazabilidad,
pero sólo las categorías solicitadas entran en el draft. En ALL la respuesta ya
está en la nueva base: se guarda referencia al padre, no otra copia del payload.
Un ALL fallido puede tener padre NULL porque nunca llegó a crear una base.

El checkpoint contiene snapshot fuente completo, resumen, token, ID y número de
revisión. Existe antes de cualquier modificación del draft. Error HTTP o de
normalización: FAILED sin escritura editorial. Fallo al persistir: rollback del
snapshot, contador y actualización COMPLETED; se registra FAILED fuera de esa
transacción. El checkpoint permanece disponible.

Recuperación de una operación exitosa, sólo con autorización del operador:
consultar `SegmentationExecution.checkpoint` vía ORM, revisar que corresponde al
padre/draft, recuperar la versión actual del BORRADOR y usar el PATCH editorial
existente con `resultado_editado=checkpoint.snapshot` y `expected_updated_at`
actual. Si hubo ediciones posteriores se deben revisar antes; no restaurarlas
silenciosamente. No alterar VALIDADA ni decrementar el contador de IDs. Este
camino se prueba con fixtures. No se implementa un botón de restauración ni un
endpoint público de lectura de ejecuciones en este sprint.

Un corte de proceso o caída total de BD puede dejar PENDING para auditoría;
no hay reconciliador de trabajos asíncronos. El checkpoint y las transacciones
impiden un merge parcial persistido. La recuperación de estos incidentes es
operativa y nunca reintenta automáticamente contra otro modelo.

## Frontend

Selector sólo SALIVA: Membranas / Núcleos y micronúcleos / Todo. Default siempre
Todo, también para ImageJ; no se cambia silenciosamente según origen.
Loading indica el target solicitado. El frontend no realiza merge: carga la
revisión enviada por Django, cambia a EDIT, limpia selección/undo/redo y conserva
el snapshot anterior si hay error. La presentación del resultado editado es
neutral: “Borrador en edición”; no atribuye toda la revisión a un único modelo.
El método mostrado en tarjetas de historial sigue describiendo la base.

## Migración, pruebas y límites de aceptación

Una sola migración: `0009_selective_saliva_segmentation` (contador, modelo
SegmentationExecution y backfill). Se aplica sólo en tests y SQLite temporal bajo
`/tmp/sicam18i_validation/`; **no aplicada a la BD de trabajo**.

Pruebas nuevas cubren ambos targets/modelos, fuentes manual/automática/VALIDADA/
BORRADOR, copia profunda de objetos, checkpoint y restauración, guardado obsoleto,
empty output, errores, rollback, IDs retirados/reservados, raw IDs repetidos,
concurrencia intercalada, exclusión de BLOOD, ALL histórico, migración y llamada
HTTP fuera de transacción. Las pruebas de frontend usan Vue real y HTTP simulado;
no equivalen a aceptación visual en un navegador.

La prueba histórica de migración 0007 se corrige para restaurar los leaf nodes
actuales al terminar: antes dejaba el esquema de test en 0007 y contaminaba las
pruebas transaccionales posteriores. No cambia la migración histórica.

No se modifican requirements, ImageJ/importador, Characterization 2.1, BLOOD,
microservicios, modelos científicos ni dataset. No se ejecutan pipelines reales,
importación ni aceptación sobre la muestra ACL. No commit ni push.

## Resultado de validación

- Backend completo: **250 passed, 2 skipped**. Omitidos únicamente los tests que
  requieren microservicios reales; ninguno se arrancó para este sprint.
- Frontend estrategias/editor/selectiva: **39 passed**.
- Frontend Characterization 2.1: **22 passed**.
- Vite build: **PASS**.
- Django `check`: **PASS**, cero problemas.
- `makemigrations --check`: **PASS**, sin cambios pendientes de generar.
- 0009 aplicada y backfill verificado exclusivamente en BD temporal/tests.
- Regresiones ImageJ, manual base, CURRENT/ALT ALL, BLOOD y Characterization 2.1:
  incluidas en las suites completas y sin fallos.
- BD de trabajo y sus 44 archivos media: SHA-256, tamaño y mtime idénticos al
  precheck. 0009 continúa sin aplicar allí. No nuevas importaciones ni cambios en
  el BORRADOR real.
- `git diff --check`: **PASS**. Cambios de 18I sin staging, commit ni push.

La respuesta automática normalizada y sus conteos se registran antes de intentar
el merge final: también quedan disponibles si una versión obsoleta cancela la
aplicación o si la persistencia editorial revierte. La transición COMPLETED y el
BORRADOR se confirman juntos.

**SPRINT 18I = PASS** (implementación y regresión sintética). La aplicación de la
migración en la BD de trabajo y la aceptación real controlada requieren una tarea
posterior expresamente autorizada.
