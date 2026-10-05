# Sprint 18J — Piloto end-to-end ImageJ

Estado: **CLOSED / PASS**. Cierre documentado durante Sprint 18K sobre HEAD
`0b7bded24eb8f15f7ca71a367249e7837649da6e`.

## Evidencia técnica

Se importaron J01–J04 como bases manuales y se ejecutó segmentación selectiva
`ALT_CPSAM_MORPHOLOGICAL_V1`, target `MEMBRANES`, por asignación explícita del
investigador. La salida se incorporó en borradores; las bases manuales quedaron
intactas. No se validaron revisiones automáticamente.

| Piloto | Muestra | Resultado | Borrador generado | Membranas antes → después | N | MN |
|---|---:|---:|---:|---|---:|---:|
| J01 | 42 | 6 | 5 | 0 → 4 | 3 | 1 |
| J02 | 43 | 7 | 6 | 0 → 4 | 5 | 1 |
| J03 | 44 | 8 | 7 | 0 → 2 | 5 | 1 |
| J04 | 45 | 9 | 8 | 0 → 4 | 4 | 1 |

Estos valores corresponden a la finalización técnica del piloto, antes de la
edición humana posterior. La igualdad completa y los hashes de los objetos
núcleo/micronúcleo antes y después dieron **PASS** en las cuatro muestras.
La reimportación individual devolvió `ALREADY_IMPORTED`.

Evidencia local temporal: `/tmp/sicam18j/pilot_results.csv`,
`/tmp/sicam18j/invariants.json` y `/tmp/sicam18j/final_integrity.json`.
Regresión técnica registrada: backend 250 passed / 2 skipped; frontend selectivo
39 passed, caracterización 22 passed y build PASS.

## Aceptación humana

**Revisión visual humana: PASS. Edición manual posterior: PASS.** Ambos resultados
fueron confirmados explícitamente por el investigador en la solicitud de Sprint
18K. Esta confirmación cierra el estado visual pendiente de los artefactos técnicos
anteriores; no implica que el agente haya automatizado ni repetido esa revisión.
No se reportaron bugs funcionales bloqueantes.

## Exclusiones y continuidad

- `CURRENT_REAL_ACCEPTANCE = DEFERRED`: la única muestra histórica con CURRENT
  explícito tiene BORRADOR activo. No modificarla para forzar una aceptación.
- `PAIR_008`: `UNSUPPORTED_POLYGON_TOPOLOGY / REAL_HOLE`, estado
  `PENDING_MANUAL_TOPOLOGY_REVIEW`. No importar parcialmente ni rellenar el hueco.
- Sprint 18K importa únicamente las parejas manuales aptas pendientes; no ejecuta
  segmentación, Characterization ni cambios sobre revisiones humanas existentes.

No se incluyen datos clínicos identificables ni imágenes en este documento.
