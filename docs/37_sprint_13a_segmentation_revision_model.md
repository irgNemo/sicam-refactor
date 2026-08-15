# Sprint 13A - Revision experta de segmentacion

## Fecha

2026-08-14 09:09:05 -06:00

## Referencia Git

- Rama: `master`
- Commit base observado: `5012b7b`

## Motivacion

SICAM ya persiste resultados automaticos de segmentacion en `ResultadoSegmentacion`:

- `respuesta_json`
- `resultado_normalizado`
- `estado`
- `tipo_muestra`
- timestamps

El resultado automatico sirve como punto de partida, pero no equivale a una validacion experta.

Registro operativo:

```text
AUTOMATICO != VALIDADO
```

El especialista debe poder corregir falsos positivos, agregar mascaras manuales y guardar trabajo parcial sin modificar el resultado automatico original.

## Diferencia entre automatico y revision experta

`ResultadoSegmentacion` conserva la salida automatica original.

`RevisionSegmentacion` representa un snapshot editable completo, separado y versionado, asociado al resultado automatico que le dio origen.

El API de revisiones no modifica:

- `ResultadoSegmentacion.respuesta_json`
- `ResultadoSegmentacion.resultado_normalizado`

## Modelo creado

Modelo:

```text
RevisionSegmentacion
```

Campos:

- `id_revision_segmentacion`
- `resultado_segmentacion`
- `numero_revision`
- `estado`
- `resultado_editado`
- `resumen`
- `creado_en`
- `actualizado_en`
- `validado_en`

No se agrego `autor` ni `validado_por` porque el dominio actual no tiene autenticacion/autoria consolidada para este flujo. Queda documentado como pendiente.

## Migracion

Migracion creada:

```text
apps/web/Backend/api/migrations/0004_revisionsegmentacion_and_more.py
```

Operaciones:

- Crea `RevisionSegmentacion`.
- Agrega constraint unica por `(resultado_segmentacion, numero_revision)`.
- Agrega constraint unica parcial para un solo `BORRADOR` activo por `resultado_segmentacion`.

## Estados

Estados permitidos:

```text
BORRADOR
VALIDADA
```

Transicion permitida:

```text
BORRADOR -> VALIDADA
```

No se permite:

```text
VALIDADA -> BORRADOR
```

Una revision `VALIDADA` es inmutable. Intentar modificarla por API devuelve:

```text
409 Conflict
```

Validar nuevamente una revision ya validada tambien devuelve:

```text
409 Conflict
```

## Versionado

Cada `ResultadoSegmentacion` puede tener una cadena de revisiones:

```text
Revision 1
Revision 2
Revision 3
...
```

Reglas:

- Si existe un `BORRADOR` activo, `POST /api/resultados-segmentacion/{id}/revisiones/` devuelve ese mismo borrador.
- No se crea una revision nueva por cada guardado.
- Cuando un `BORRADOR` pasa a `VALIDADA`, queda cerrado.
- Una correccion posterior crea `numero_revision = max + 1`.
- Si ya existe una revision validada, el nuevo borrador parte del snapshot validado mas reciente.
- Si no existe revision validada, el primer borrador parte de `ResultadoSegmentacion.resultado_normalizado`.

## Contrato JSON de revision

`resultado_editado` guarda un snapshot completo:

```json
{
  "version": "1.0",
  "base_result_id": 7,
  "objects": [
    {
      "id": 1,
      "label": "membrana",
      "geometry": {
        "type": "polygon",
        "points": [[0, 0], [10, 0], [10, 10]]
      },
      "provenance": {
        "origin": "automatic",
        "base_object_id": 1
      }
    },
    {
      "id": 31,
      "label": "micronucleo",
      "geometry": {
        "type": "polygon",
        "points": [[2, 2], [6, 2], [6, 6]]
      },
      "provenance": {
        "origin": "manual",
        "base_object_id": null
      }
    }
  ]
}
```

`version` corresponde al contrato de revision, no al contrato del resultado normalizado automatico.

## Provenance

Cada objeto debe declarar:

```text
provenance.origin
provenance.base_object_id
```

Para objetos automaticos:

```json
{
  "origin": "automatic",
  "base_object_id": 1
}
```

Para objetos manuales:

```json
{
  "origin": "manual",
  "base_object_id": null
}
```

Las mascaras eliminadas no se guardan como delta; se infieren comparando el `resultado_normalizado` original contra el snapshot completo de la revision.

## Compatibilidad con resultados normalizados legacy

Algunos `ResultadoSegmentacion.resultado_normalizado` historicos fueron creados con contrato `version = "1.0"`. En esos resultados, varios objetos automaticos podian compartir el mismo `objects[].id`, especialmente nucleos y micronucleos derivados del identificador raw `255`.

`RevisionSegmentacion` requiere IDs unicos dentro de `resultado_editado.objects`, por lo que el primer `BORRADOR` ya no copia ciegamente el ID automatico como identidad editorial.

La conversion `ResultadoSegmentacion -> RevisionSegmentacion` separa:

- `resultado_editado.objects[].id`: identidad editorial unica dentro del snapshot editable.
- `resultado_editado.objects[].provenance.base_object_id`: ID original que tenia el objeto en el resultado automatico.

Estrategia determinista:

- Si el ID automatico es entero positivo y no se ha usado todavia en el snapshot, se conserva como ID editorial.
- Si el ID automatico esta duplicado o no puede usarse como identidad editorial, se asigna el siguiente entero positivo disponible.
- La asignacion respeta el orden original de `resultado_normalizado.objects`.
- Los IDs originales validos que aparecen mas adelante se reservan para evitar colisiones futuras.

Ejemplo legacy:

```text
Resultado normalizado:
1, 255, 255, 255

Revision editable:
1, 255, 2, 3

provenance.base_object_id:
1, 255, 255, 255
```

Para resultados modernos `version = "1.1"` con IDs ya unicos, los IDs editoriales se preservan sin renumeracion.

No se modifica:

- `ResultadoSegmentacion.respuesta_json`
- `ResultadoSegmentacion.resultado_normalizado`
- registros historicos existentes

No se agrego `base_object_index` porque el contrato actual puede distinguir los objetos dentro de la revision mediante el ID editorial unico, y `base_object_id` conserva la trazabilidad hacia el automatico original. En historicos legacy puede haber varios objetos con el mismo `base_object_id`, lo cual refleja fielmente el origen del dato.

## Validacion estructural

Antes de persistir `resultado_editado`, Django valida:

- `resultado_editado` es objeto JSON.
- `objects` es lista.
- IDs enteros positivos.
- IDs unicos dentro del snapshot.
- Labels permitidos:
  - `membrana`
  - `nucleo`
  - `micronucleo`
- `geometry` existe.
- `geometry.type == "polygon"`.
- `geometry.points` es lista.
- Cada punto tiene exactamente dos coordenadas numericas.
- No se aceptan `NaN` ni `Infinity`.
- Cada poligono tiene al menos 3 puntos.
- `provenance.origin` es `automatic` o `manual`.
- Objetos automaticos requieren `base_object_id` entero positivo.
- Objetos manuales requieren `base_object_id = null`.

No se clamplean coordenadas ni se corrigen datos invalidos silenciosamente.

No se validan limites de imagen porque el contrato normalizado actual no expone metadatos confiables de ancho/alto natural.

## Resumen calculado por backend

El cliente no es autoridad para:

- `counts_by_label`
- `total_objects`

Django recalcula `RevisionSegmentacion.resumen` desde `resultado_editado.objects` en cada guardado y al validar.

Estructura:

```json
{
  "counts_by_label": {
    "membrana": 15,
    "nucleo": 12,
    "micronucleo": 4
  },
  "total_objects": 31
}
```

Las etiquetas ausentes se guardan con `0`.

## Endpoints

### Listar revisiones

```text
GET /api/resultados-segmentacion/{id}/revisiones/
```

Devuelve revisiones ordenadas por `numero_revision`.

### Crear u obtener borrador

```text
POST /api/resultados-segmentacion/{id}/revisiones/
```

Semantica:

- Si existe `BORRADOR`, devuelve ese borrador con `200`.
- Si no existe, crea un borrador con `201`.
- Si hay revision validada previa, clona la ultima validada.
- Si no hay validada previa, transforma `resultado_normalizado` automatico.

### Obtener revision

```text
GET /api/revisiones-segmentacion/{id}/
```

### Guardar borrador

```text
PATCH /api/revisiones-segmentacion/{id}/
```

Permite actualizar:

- `resultado_editado`

Ignora o bloquea cambios no autorizados a:

- `resultado_segmentacion`
- `numero_revision`
- `estado`
- `resumen`
- `validado_en`

### Validar revision

```text
POST /api/revisiones-segmentacion/{id}/validar/
```

Acciones:

- exige estado `BORRADOR`;
- revalida snapshot;
- recalcula `resumen`;
- cambia estado a `VALIDADA`;
- asigna `validado_en`;
- impide modificaciones posteriores.

## Concurrencia

La creacion de borrador usa:

```text
transaction.atomic()
select_for_update()
```

Ademas, la base de datos protege:

- unicidad de `(resultado_segmentacion, numero_revision)`;
- un solo `BORRADOR` activo por `resultado_segmentacion`.

La constraint unica parcial funciona como salvaguarda final ante concurrencia.

## Compatibilidad 1.0 / 1.1

La creacion de borrador acepta resultados automaticos normalizados historicos:

- `version = "1.0"`
- `version = "1.1"`

La condicion real es que contengan `objects` con geometria utilizable.

El snapshot de revision siempre usa:

```text
version = "1.0"
```

porque pertenece al nuevo contrato de revision experta.

## Tests agregados

Cobertura agregada para:

- `numero_revision` unico por `ResultadoSegmentacion`.
- Un solo `BORRADOR` activo.
- Estados y timestamps.
- Primer borrador desde automatico.
- Doble POST devuelve mismo borrador.
- Inmutabilidad de `respuesta_json`.
- Inmutabilidad de `resultado_normalizado`.
- Validar revision 1.
- Crear revision 2 desde revision 1 validada.
- No volver al automatico original tras validar.
- Validacion de labels.
- IDs duplicados.
- Poligonos con menos de 3 puntos.
- Puntos no numericos.
- `NaN` / `Infinity`.
- Geometria invalida.
- Provenance manual.
- Provenance automatic.
- Summary recalculado por backend.
- Summary falso enviado por cliente ignorado.
- `BORRADOR` editable.
- `VALIDADA` inmutable.
- Validar `VALIDADA` nuevamente devuelve conflicto.
- No permitir regresar a `BORRADOR`.
- Resultado inexistente devuelve `404`.
- Revision inexistente devuelve `404`.
- Listado ordenado.
- PATCH valido.
- PATCH invalido.
- Endpoint `validar`.
- Compatibilidad con automaticos normalizados `1.0`.
- Compatibilidad con automaticos normalizados `1.1`.

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
- `pytest`: PASS, `96 passed, 2 skipped`.
- `manage.py test`: PASS, `78 tests`.

## Limitaciones

- No hay `autor` ni `validado_por` todavia.
- No hay editor grafico.
- No hay operaciones delta ni bitacora de cambios.
- No hay backfill de resultados historicos.
- No hay resultado efectivo para reportes.
- No se integran revisiones al `Resumen del Caso`.
- No se implementa creacion grafica de poligonos.
- No se implementa eliminacion desde UI.

## Fuera de alcance respetado

No se implemento:

- editor SVG;
- drag de vertices;
- nuevo poligono desde Vue;
- eliminacion desde UI;
- undo/redo;
- autosave frontend;
- resultado efectivo en reportes;
- caracterizacion;
- reentrenamiento.

No se modifico:

- `apps/segmentation-saliva`;
- `apps/segmentation-blood`;
- normalizer `1.1`;
- overlay existente;
- Zoom/Pan/Rotar;
- responsive;
- frontend funcional.
