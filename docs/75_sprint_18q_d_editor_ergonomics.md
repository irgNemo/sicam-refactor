# Sprint 18Q-D — Ergonomía del editor de Segmentación

## Baseline

- Rama: `master`.
- HEAD: `dbfc1037694b23acdfa6660fb00e0e9dd17ffd95`.
- Estado inicial: working tree limpio después de 18Q-C/C.1.
- Alcance: presentación del editor y feedback de guardado, exclusivamente frontend.
- Sin commit ni push.

## Inspección de la implementación

| Responsabilidad | Ubicación |
| --- | --- |
| Navegar/Editar, badge de revisión y herramientas generales | `SegmentationEditorToolbar.vue` |
| Objeto seleccionado, herramientas de contorno, dibujo y acciones de revisión | `MainContent.vue` |
| Objetos de trabajo, selección, geometría, undo/redo y conteos | `useSegmentationEditor.js` |
| Saving, errores, carga de revisiones y effective | `useSegmentationRevision.js` |
| Requests y precondiciones de versión | `segmentationRevisionService.js` |
| Cursores geométricos y handles | `SegmentationOverlay.vue` |
| Capas visibles y conteo | `OverlayLayersCard.vue`, `SegmentationCountSummary.vue` |

Antes, la barra general ofrecía Seleccionar/Mover/Dibujar/Editar contorno.
Deshacer/Rehacer, guardar y validar aparecían en el mismo panel derecho que las
herramientas contextuales. El tipo a dibujar se elegía mediante un select separado
de la barra principal.

## Reorganización

- Navegar/Editar mantienen su fila independiente y el badge superior
  `Revisión #N · BORRADOR`.
- `Mover` pasa a **Mover vista**, conservando `PAN`, evento, handler y comportamiento.
- Deshacer/Rehacer pasan a la barra general, usando los mismos handlers y
  `canUndo`/`canRedo`. Conservan el bloqueo de interacción durante segmentación
  o reserva de ID.
- Al activar Dibujar aparecen opciones visibles para los tipos editables existentes.
  SALIVA ofrece Membranas, Núcleos y Micronúcleos; BLOOD conserva sus tipos propios.
  Los botones usan `drawingLabel`, el mismo estado del select anterior, y
  `aria-pressed` identifica el tipo activo.
- Objeto seleccionado conserva tipo, ID editorial real y provenance disponible.
  Sin selección muestra **Ninguno** e instrucciones. No se generan identificadores.
- Editar contorno contiene Mover puntos, Agregar punto y Eliminar punto con sus
  restricciones existentes. No contiene acciones globales ni persistencia.
- Guardar borrador y Validar revisión ocupan una sección independiente:
  **Acciones de revisión**. Su visibilidad conserva la regla previa SELECT/VERTEX.
  El aviso `BORRADOR · No efectivo` sólo aparece para una revisión BORRADOR.
- Las instrucciones y acciones de finalizar/cancelar una máscara siguen en el
  contexto de dibujo. Capas visibles conserva exactamente la ubicación de 18Q-A.

Eliminación existente:

| Función | Estado |
| --- | --- |
| Eliminar máscara | `EXISTS_AND_EXPOSED` |
| Eliminar punto de contorno | `EXISTS_AND_EXPOSED` |
| Eliminar punto de máscara en construcción | `EXISTS_AND_EXPOSED` |

No se añadió lógica destructiva. Se mantienen handlers y restricciones de mínimo
de tres puntos. Se retiran únicamente el computed de título contextual y el CSS
del select que quedaron sin uso.

## Cursor de Guardar borrador: causa y corrección

La causa identificada en código es `.btn-segment:disabled { cursor: wait; }`
en `MainContent.vue`. `canSaveDraft` también devuelve false sin cambios pendientes,
durante un dibujo incompleto o un arrastre; esas condiciones no significan que
exista una petición. Por eso un botón inactivo podía mostrar espera al pasar el
mouse.

Se revisaron el handler `saveDraft`, `canSaveDraft` y `saveActiveDraft`.
No hay handler de hover que inicie guardado. `isSavingDraft` se activa al entrar
en la operación async y se restablece en `finally`, tanto en éxito como en error.
`saveDraft` vuelve a comprobar `canSaveDraft`; su dependencia de `isSavingDraft`
ya bloquea un segundo envío. No fue necesaria una modificación del composable.

Corrección limitada al botón Guardar:

- Habilitado/inactivo: conserva `cursor: pointer`.
- Deshabilitado por precondiciones: `cursor: not-allowed`.
- Guardado real: clase `is-saving`, `aria-busy=true`, texto `Guardando...` y
  `cursor: progress`; prevalece sobre el estilo disabled.
- Al terminar: se retira el indicador ocupado; tras éxito queda deshabilitado
  si no hay cambios, y tras error conserva cambios y permite reintentar mediante
  el mecanismo existente.

Los botones deshabilitados de la barra general también usan `not-allowed`, evitando
presentar undo/redo sin historial como una operación pendiente.

## Invariantes

No se modifican endpoints, payloads, `expected_updated_at`, manejo de conflictos,
source, IDs editoriales, `source.raw_id`, validación ni resolución de effective.
BORRADOR sigue sin ser efectivo. Se conservan bases MANUAL/AUTOMATIC y selección
histórica. El contenido de Segmentación/Resultado actual/Historial de 18Q-C/C.1
no cambia. Tampoco se modifican backend, microservicios, Characterization,
dependencias ni datos reales.

## Validación

Con Node **24.17.0**, desde `apps/web/Frontend`:

| Comando | Resultado |
| --- | --- |
| `node tests/segmentationStrategies.test.mjs` | 58 passed, 0 failed |
| `node tests/characterization21.test.mjs` | 22 passed, 0 failed |
| `npm run build` | PASS |
| `git diff --check` | PASS |

Cinco pruebas nuevas cubren:

1. Mover vista, estado activo, eventos undo/redo, disponibilidad y selección del tipo.
2. Tipo/ID del objeto, estado vacío y separación del workflow editorial.
3. Guardado exitoso: estado inactivo, bloqueo de doble clic, payload con versión,
   feedback durante request y recuperación.
4. Guardado fallido: error y disponibilidad para reintentar, sin quedar ocupado.
5. Primera membrana sobre objetos sintéticos N/MN: conteo y capa visible
   inmediatos, preservación de N/MN y undo/redo.

Los requests de las pruebas usan adaptadores simulados. No se abrió, editó ni
guardó sample 56 real. El caso sintético reproduce M=0, N>0, MN>0 para verificar
el flujo sin persistencia. Las pruebas previas de contorno, validación, effective,
navegación y capas también pasan.

## Responsive, accesibilidad y revisión pendiente

La toolbar admite wrap; el panel conserva su ancho, permite envolver texto y
usa columnas de contenido que pueden reducirse. Se mantienen botones nativos,
foco de navegador, estados disabled y `aria-pressed`; se añade `aria-busy` al
guardado. No se cambian los cursores del visor ni de las herramientas geométricas.

No hay navegador automatizado disponible en este entorno. Las pruebas de render
y eventos no sustituyen la revisión visual. Pendiente en desktop y laptop estrecha:

- Borrador existente: herramienta activa, objeto seleccionado y undo/redo.
- Sin membranas: dibujar la primera y comprobar alineación, capas y conteo.
- Contorno: mover/agregar/eliminar puntos y conservar restricciones.
- Guardar: hover sin espera, feedback durante request y recuperación.
- Validar: comprobar ubicación y flujo con aprobación humana; no se validó
  ninguna revisión real en este sprint.
- Ausencia de overflow, cortes y solapamientos.

## Archivos

- `apps/web/Frontend/src/components/MainContent.vue`
- `apps/web/Frontend/src/components/segmentation/SegmentationEditorToolbar.vue`
- `apps/web/Frontend/tests/segmentationStrategies.test.mjs`
- `docs/75_sprint_18q_d_editor_ergonomics.md`

**SPRINT 18Q-D = READY_FOR_VISUAL_REVIEW**
