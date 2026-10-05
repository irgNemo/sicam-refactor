# Sprint 18K — Importación completa del dataset ImageJ apto

**SPRINT 18K = PASS WITH DATA EXCLUSIONS**

Se importaron exactamente las 18 parejas aptas pendientes de `ijc1-case1`.
El dataset queda con 23 parejas importadas; `PAIR_008` permanece excluida por
`UNSUPPORTED_POLYGON_TOPOLOGY / REAL_HOLE`, en
`PENDING_MANUAL_TOPOLOGY_REVIEW`. No se modificó ni importó parcialmente su TIFF.

## Precondiciones y respaldo

- Rama `master`, HEAD `0b7bded24eb8f15f7ca71a367249e7837649da6e`.
- Working tree inicialmente limpio.
- Migraciones `0008_imagej_manual_import` y `0009_selective_saliva_segmentation`
  aplicadas; sin migraciones pendientes. No se aplicó ninguna migración en 18K.
- Django check: 0 incidencias. SQLite integrity_check: `ok`.
- Cierre técnico y humano de 18J documentado en
  [67_sprint_18j_end_to_end_pilot.md](67_sprint_18j_end_to_end_pilot.md).

BD resuelta desde settings:
`/home/israel/repos/sicam-refactor/apps/web/Backend/db.sqlite3`.
MEDIA_ROOT: `/home/israel/repos/sicam-refactor/apps/web/Backend/media`.

Backup nuevo y retenido: `/tmp/sicam18k_backup_20261005_023558/`
(el sufijo es una marca UTC). Contiene `database/db.sqlite3`, `media/`,
`manifest.txt`, `hashes.txt` y `RECOVERY.md`.

La copia de BD se hizo bajo bloqueo exclusivo SQLite, sin WAL/journal pendiente.
Se verificaron tamaño, mtime y SHA-256 idénticos; el backup es legible e íntegro.
SHA-256 de BD previa y backup:
`ced1428f79cb7a106670557447276cbcd4597642dc119db04ff6e74ac14ca47d`.
Tamaño: 1,622,016 bytes. Media previo: 52 archivos, 184,882,167 bytes;
se verificaron estructura, tamaños y hashes de la copia completa.
Antes de retomar la ejecución se confirmó que la BD seguía coincidiendo con ese
backup. Tras importar se verificó nuevamente la integridad del respaldo.

## Preflight e importación

Dry-run completo sobre el dataset real, layout `legacy-flat`, formato de Excel
`ijc1`, namespace `ijc1`, dataset `ijc1-case1`, Caso 1:

| Estado | Antes | Después |
|---|---:|---:|
| ALREADY_IMPORTED | 5 | 23 |
| WOULD_IMPORT | 18 | 0 |
| UNSUPPORTED_POLYGON_TOPOLOGY / REAL_HOLE | 1 | 1 |
| Total parejas | 24 | 24 |

Ambos dry-runs terminaron con código 2 exclusivamente por el rechazo conocido
`PAIR_008`. No hubo conflictos de paciente, pairing, dimensiones, máscara, hashes
ni versiones. Se identificaron y cotejaron los 6 pacientes con el Excel.

Antes de persistir se listaron patient_key, basename, dimensiones y conteos de
las 18 parejas. La lista técnica queda en `/tmp/sicam18k/pending_manifest.json`
y `/tmp/sicam18k/prepare.log`; no contiene fechas de nacimiento ni identificadores
hospitalarios. Se preservan fuera de Git los nombres técnicos del dataset.

Se creó `/tmp/sicam18k/approved_source/` con **sólo las 18 parejas aprobadas**,
conservando nombres, estructura y bytes mediante comprobación SHA-256. El
importador existente ejecutó transacciones independientes por pareja y `--strict`
para detener el lote ante cualquier error inesperado. No se cambió código.

Comando real ejecutado desde `apps/web/Backend`, con Python del entorno `sicam`:

```bash
python -B manage.py import_imagej_dataset \
  --source /tmp/sicam18k/approved_source \
  --patients-file /mnt/c/Users/israe/Documents/sicam-refactor/etiquetado_manual/BD_IJC1.xlsx \
  --dataset-key ijc1-case1 \
  --patient-namespace ijc1 \
  --case-number 1 \
  --layout legacy-flat \
  --patients-format ijc1 \
  --strict
```

Resultado: 18 `IMPORTED`, 0 errores, exit 0. Se crearon 2 pacientes,
2 casos y 2 análisis; se reutilizaron los otros 4 pacientes/casos/análisis.
Las muestras nuevas son 46–63 y los resultados 10–27.

## Persistencia y objetos

| Modelo | Antes | Después | Incremento |
|---|---:|---:|---:|
| Paciente | 5 | 7 | 2 |
| Caso | 5 | 7 | 2 |
| AnalisisPred | 5 | 7 | 2 |
| MuestraSaliva | 45 | 63 | 18 |
| ResultadoSegmentacion | 9 | 27 | 18 |
| RevisionSegmentacion | 8 | 8 | 0 |
| ResultadoCaracterizacion | 3 | 3 | 0 |
| ImageJImportRecord | 5 | 23 | 18 |
| SegmentationExecution | 7 | 7 | 0 |

Los conteos previos son los del backup nuevo de 18K, que preserva el estado
posterior a la revisión humana; no se reutilizaron los conteos antiguos de 18J.

Las 18 bases nuevas son SALIVA, `COMPLETADO`, `base_origin=MANUAL`,
`segmentation_strategy=NULL`; no tienen revisiones y su fuente efectiva es
`MANUAL`. Objetos nuevos: **0 membranas, 92 núcleos, 29 micronúcleos**.
Las 23 bases importadas suman **0 membranas, 114 núcleos, 34 micronúcleos**.
Estos conteos describen las bases manuales, no los borradores del piloto.

Para cada pareja nueva se comprobó:

- Conteos iguales a los componentes de conectividad 8 de valores 255 y 85 del TIFF.
- `origin=manual`, `base_object_id=null`, IDs editoriales únicos y raw IDs conservados.
- Polígonos válidos, dentro de bounds, sin degeneración/autointersección.
- Rasterización de los polígonos idéntica a las clases del TIFF, sin alterar GT.
- Referencias coherentes a paciente, Caso 1, análisis, muestra y resultado.

## Storage, idempotencia e integridad

- Media: **52 → 88 archivos**, incremento exacto **18 JPG + 18 TIFF**.
  Tamaño final: 703,174,139 bytes.
- Hashes de imagen y TIFF correctos para las **23/23** parejas importadas
  (incluidas las 18 nuevas); ambos archivos están en storage Django.
  Abrirlos ya no depende de las rutas externas ni del Excel.
- 23 registros READY, con logical_key, sample_key y annotation_key únicos y
  recalculados; versiones y relaciones correctas. Ninguno para `PAIR_008`.
- Dry-run final: **23 ALREADY_IMPORTED, 0 WOULD_IMPORT, 1 REAL_HOLE**.
  SHA-256 de BD idéntico antes/después de ese dry-run.
- No se repitió una importación real completa: el dry-run final y la idempotencia
  individual ya probada en el piloto satisfacen la alternativa autorizada.
- **211 filas preexistentes** de todas las tablas comparadas por clave primaria
  y todos sus valores: intactas, incluidas revisiones y trabajo humano previo.
- Los 52 archivos previos de media permanecen intactos; sólo se añadieron los
  36 archivos propiedad de estas nuevas importaciones.
- **49/49 originales**, incluido el Excel: mismos hashes y tamaños.
- SQLite integrity_check `ok`, foreign_key_check sin infracciones.
  Django check final: 0 incidencias.

Regresión backend en BD de pruebas en memoria, sin servicios reales:
**250 passed, 2 skipped**. Los dos tests omitidos requieren microservicios reales.
Frontend sin cambios funcionales; no fue necesario repetir su build.

## Evidencia local y alcance

Artefactos retenidos bajo `/tmp/sicam18k/`:

- `bulk_import_results.csv`: 18 filas con patient_key/basename, estados, IDs,
  N/MN/M, comprobación de hashes y fuente efectiva.
- `final_counts.json`, `integrity.json`, `excluded_pairs.json`.
- `pre_dry_run.json`, `real_import.json`, `final_dry_run.json` y sus stderr.
- `backend_tests.log`, `django_check.log`, `pending_manifest.json`, `prepare.log`.

Sin bugs funcionales detectados ni errores de datos nuevos. Única exclusión:
`PAIR_008`, pendiente de revisión manual de topología. No se ejecutó CURRENT,
ALT/SAM, segmentación, Characterization, validación ni creación de borradores;
no se iniciaron microservicios. Tampoco se modificaron código, requirements,
modelos ni migraciones.

Los únicos archivos nuevos visibles en Git son este documento y el cierre de
18J. `git diff --check` sin incidencias. Sin staging, commit ni push.

Siguiente fase recomendada, separada y pendiente de autorización: ejecución
controlada `ALT_CPSAM_MORPHOLOGICAL_V1` + `MEMBRANES` para las anotaciones
importadas todavía sin membranas, preservando N/MN y revisiones existentes.
ALT/SAM es la asignación explícita del investigador para este dataset.
`CURRENT_REAL_ACCEPTANCE` continúa diferida y su muestra histórica no fue tocada.
