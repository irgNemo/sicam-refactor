# Sprint 18S-D.1 — Limpieza controlada y aceptación real de Characterization 2.2

## Alcance y decisión del investigador

Aceptación ejecutada el 2026-10-22, zona America/Mexico_City. Se autorizaron la
eliminación de dos uploads TIFF accidentales y una sola caracterización real 2.2,
con segunda solicitud idempotente. No se validaron revisiones ni ejecutaron ALT,
CURRENT, BLOOD, calibración o backfill.

Rama `master`, HEAD `fde13690405ada3affc55075f50c800d87e4f79f`.
18S-D estaba sin commit: 7 archivos tracked modificados y 4 nuevos. Se comprobó
que eran exclusivamente su implementación, tests y docs/84; `git diff --check`
pasó. Se preservaron byte-exactamente todos esos archivos mediante SHA-256
pre/post. **No se modificó código en 18S-D.1**; el único archivo nuevo versionable
de este paso es este documento.

## Auditoría de las cuatro muestras

Se usaron consultas ORM y SQLite `query_only=ON`, lectura técnica Pillow y collector
de Django; ningún preview ni imagen se adjunta. Se identifica al paciente sólo por
su PK, sin nombres ni datos clínicos personales.

Las cuatro son SALIVA, paciente **8**, caso **8**, análisis **8**, serie **2**,
perfil **1**, calibración **1**, resolución **4928×4928**. No había muestras SANGRE
con serie. Se verificó que eran las cuatro únicas muestras con AcquisitionSeries.

| Sample | Filename | Formato/modo | Valores | Compatibilidad inicial | Segmentación / revisiones / caracterización |
| --- | --- | --- | --- | --- | --- |
| 64 | `EJT_05-12-25_102.531_2.jpg` | JPEG / RGB | >257 colores | COMPATIBLE_PROVISIONAL | Ninguna / ninguna / ninguna |
| 65 | `EJT_05-12-25_102.531_2.tif` | TIFF / L | 0,85,255 | IMAGE_MODE_MISMATCH | Ninguna / ninguna / ninguna |
| 66 | `EJT_05-12-25_11451_2.jpg` | JPEG / RGB | >257 colores | COMPATIBLE_PROVISIONAL | Resultado 28 AUTOMATIC / ninguna / 23 (2.1) |
| 67 | `EJT_05-12-25_11451_2.tif` | TIFF / L | 0,85,255 | IMAGE_MODE_MISMATCH | Ninguna / ninguna / ninguna |

Las TIFF tienen una página, modo L y exactamente el contrato de máscara ImageJ
0=fondo, 85=micronúcleo, 255=núcleo. Cada TIFF comparte basename y dimensiones con
su JPEG RGB en la misma serie/paciente/caso/análisis. Sus timestamps de upload son
contiguos a las RGB (2026-10-21 19:56:11–12 UTC). Esta evidencia técnica, junto con
la identificación explícita del investigador de los uploads como errores, permitió
identificar inequívocamente **65 y 67**; no se decidió borrar sólo por extensión.

`MEDIA_ROOT` detectado por settings:
`/home/israel/repos/sicam-refactor/apps/web/Backend/media`.
Todos los filenames anteriores tenían ruta relativa
`muestras/saliva/2026/10/<filename>` bajo ese directorio.
Las extensiones eran `.jpg`, `.tif`, `.jpg`, `.tif`, respectivamente.

### Configuración física preservada

- Serie 2 conserva su paciente y asociaciones originales.
- Perfil 1: **OPTIKA 40x**, microscopio **OPTIKA B-1000FLHBO**,
  cámara **OPTIKA C-B25+**, adaptador **M-114**, objetivo **40x**, **4928×4928 RGB**.
- Calibración 1: **CAL-OPTIKA-40X-PROVISIONAL-001**, **PROVISIONAL**.
- sx = **0.055233934048 µm/px**; sy = **0.055010060892 µm/px**.
- Los ceros finales de las cadenas Decimal de API no cambian estos valores.

Las RGB **64 y 66** permanecen en serie 2 y son ambas
`COMPATIBLE_PROVISIONAL` después de la limpieza. La 64 no tiene segmentación;
no se segmentó para esta aceptación. La 66 ya tenía resultado 28 COMPLETADO,
estrategia ALT_CPSAM_MORPHOLOGICAL_V1, fuente efectiva AUTOMATICO y conteos
**M=10, N=13, MN=11**, sin VALIDADA ni BORRADOR. Se preservó todo ese contenido.

### Respuestas completas de compatibilidad antes de borrar

Sample 64:

```json
{
  "compatible_for_physical_units": true,
  "status": "COMPATIBLE_PROVISIONAL",
  "reasons": [],
  "acquisition_series_id": 2,
  "calibration_id": 1,
  "calibration_status": "PROVISIONAL",
  "profile": {
    "id": 1,
    "name": "OPTIKA 40x",
    "image_width_px": 4928,
    "image_height_px": 4928,
    "image_mode": "RGB"
  },
  "source_dimensions": {
    "width": 4928,
    "height": 4928
  },
  "scale_x_um_per_px": "0.055233934048000",
  "scale_y_um_per_px": "0.055010060892000"
}
```

Sample 65:

```json
{
  "compatible_for_physical_units": false,
  "status": "IMAGE_MODE_MISMATCH",
  "reasons": [
    "IMAGE_MODE_MISMATCH"
  ],
  "acquisition_series_id": 2,
  "calibration_id": 1,
  "calibration_status": "PROVISIONAL",
  "profile": {
    "id": 1,
    "name": "OPTIKA 40x",
    "image_width_px": 4928,
    "image_height_px": 4928,
    "image_mode": "RGB"
  },
  "source_dimensions": {
    "width": 4928,
    "height": 4928
  }
}
```

Sample 66:

```json
{
  "compatible_for_physical_units": true,
  "status": "COMPATIBLE_PROVISIONAL",
  "reasons": [],
  "acquisition_series_id": 2,
  "calibration_id": 1,
  "calibration_status": "PROVISIONAL",
  "profile": {
    "id": 1,
    "name": "OPTIKA 40x",
    "image_width_px": 4928,
    "image_height_px": 4928,
    "image_mode": "RGB"
  },
  "source_dimensions": {
    "width": 4928,
    "height": 4928
  },
  "scale_x_um_per_px": "0.055233934048000",
  "scale_y_um_per_px": "0.055010060892000"
}
```

Sample 67:

```json
{
  "compatible_for_physical_units": false,
  "status": "IMAGE_MODE_MISMATCH",
  "reasons": [
    "IMAGE_MODE_MISMATCH"
  ],
  "acquisition_series_id": 2,
  "calibration_id": 1,
  "calibration_status": "PROVISIONAL",
  "profile": {
    "id": 1,
    "name": "OPTIKA 40x",
    "image_width_px": 4928,
    "image_height_px": 4928,
    "image_mode": "RGB"
  },
  "source_dimensions": {
    "width": 4928,
    "height": 4928
  }
}
```

## Dependencias y seguridad del delete

Se inspeccionaron todas las FK concretas de los modelos registrados y el cascade
real mediante `django.db.models.deletion.Collector`.

Para **cada TIFF 65 y 67**:

- `ResultadoAnalisis.muestra`: 0 referencias.
- `ResultadoSegmentacion.muestra`: 0 referencias; por tanto 0 revisiones,
  VALIDADA, BORRADOR y caracterizaciones derivadas.
- `ImageJImportRecord.muestra`: 0 referencias.
- Collector: únicamente `api.MuestraSaliva` con el ID objetivo; sin fast deletes
  de otros objetos y sin field updates.
- Se verificó además que ningún otro FileField compartiera su nombre de storage,
  que no fueran symlinks y que las rutas estuvieran dentro del MEDIA_ROOT esperado.

La RGB 66 sí posee trabajo científico, incluido un SegmentationExecution protegido
(`6f2c25ed-dbab-4fc0-ab4c-230f36bd3735`). Su collector impediría borrar la cadena.
Esto se registró sólo como evidencia de auditoría; **no se intentó eliminar esa RGB**.

La limpieza usó una transacción, volvió a comprobar baseline, IDs, hashes,
dependencias y collector, y exigió retorno exacto:
`(2, {'api.MuestraSaliva': 2})`. Sólo entonces eliminó los dos archivos identificados.
Las comparaciones de todos los demás registros y media se hicieron antes del commit.
El script temporal incluía rollback de BD y restauración de los archivos objetivo
si ocurría un fallo; no fue necesario restaurar.

## Backup verificado

Ubicación:
`/tmp/sicam18sd1_backup_20261022T160309Z/`

- `database/db.sqlite3`: backup consistente mediante API backup de SQLite,
  tamaño **4616192 bytes**.
- `media_manifest.json`: tamaño y SHA-256 de los **95** media previos.
- `media/`: copias byte-exactas recuperables de **las dos TIFF objetivo**, conservando
  rutas relativas. No es una copia completa de los otros 93 media; éstos tienen
  manifest y no se modifican durante esta operación.
- `baseline.json`, `manifest.txt`, `hashes.txt`, `RECOVERY.md`.
- Directorio privado fuera del repositorio; no versionado.

SHA-256 de BD original previa:
`c50400eee7a0fc8aa1127b74511a27d4ac13bed363d7386f7ee2b83073711941`

SHA-256 del archivo SQLite de backup:
`64db252272da963efba4984002c5e95c0e16caf67ee908b0b5ec9e5faa1c5a3a`

Los hashes de archivo difieren porque SQLite backup puede cambiar metadata de
páginas/cabecera. Se verificaron íntegramente los valores de **las 26 tablas** entre
original y copia mediante conexiones SQLite equivalentes, además de
`integrity_check=ok` y `foreign_key_check=[]`. Se confirmó que el original no cambió
durante el backup. Las copias de ambas TIFF coinciden con sus SHA-256 originales.

| Archivo retirado | SHA-256 original y copia de backup |
| --- | --- |
| `EJT_05-12-25_102.531_2.tif` | `1488d651311c871b06a1f18d223b1b2f227620a30ddb34205c7489abd5589009` |
| `EJT_05-12-25_11451_2.tif` | `774321f0d8e8fcfcc5b8e16f4cdf49d9553e9229de7e2f705cbc818a07a06fa0` |

## Limpieza e integridad

Eliminación completada: **2026-10-22T10:04:06.400974-06:00** (America/Mexico_City),
**2026-10-22T16:04:06.400974+00:00** UTC.

- Muestras totales: **69 → 67**. SALIVA: **67 → 65**; SANGRE: **2 → 2**.
- Media: **95 → 93**; muestras 65/67 y sus TIFF ya no existen en BD/media.
- Todos los demás registros de las 26 tablas permanecieron idénticos tras delete.
- Los 93 media restantes conservaron tamaño y SHA-256 exactos.
- Las RGB conservan sus hashes:
  - 64: `e9602e7378b90f07e890a54bd01e029945dd2d6c37d89511368857f64e9d0577`.
  - 66: `c5f1746e953a77d8ad527cf13c734a3f3a4c3ec2700747793c521dfccfdec887`.
- Integridad SQLite `ok`; FK sin infracciones, tras delete y al cierre.
- No se modificaron pacientes, casos, análisis, series, perfiles, calibraciones,
  referencias, originales externos ni geometrías científicas.
- La regla **IMAGE_MODE_MISMATCH permanece intacta**. Desaparecen esas incidencias
  porque se retiraron las máscaras mal cargadas, no por relajar compatibilidad.

## Aceptación real de Characterization

Muestra elegida: **66**, resultado **28**, paciente/caso/análisis **8/8/8**.
Era elegible sin intervención científica: COMPLETADO, effective AUTOMATICO, geometrías
existentes y calibración provisional compatible. Se respetaron tanto el resolver
VALIDADA/base como el guard de base MANUAL; no se inventaron ni validaron revisiones.

Se invocó la ruta normal:
`POST /api/resultados-segmentacion/28/caracterizar/`

Se resolvió mediante el router Django y se ejercitó el viewset DRF normal, servicio
de aplicación, compatibilidad, resolver efectivo, persistencia y serializer. Se
utilizó APIRequestFactory dentro del proceso, **sin simular conversiones ni llamar
helpers físicos para fabricar el resultado**, sin servidor HTTP adicional ni cambios
de autenticación. Es aceptación real de persistencia/API, no prueba de transporte HTTP.

| Solicitud | Status de respuesta | ID | Duración |
| --- | ---: | ---: | ---: |
| Primera | 201 | 24 | 20.421751 s |
| Segunda, después de commit de la primera | 200 | 24 | 0.670869 s |

La segunda solicitud devolvió el mismo JSON y no cambió ningún byte de BD ni media.
Sólo se creó **una** fila nueva en ResultadoCaracterizacion. Las 23 históricas siguen
intactas, incluidas 2.0/2.1. Ninguna otra tabla cambió durante la caracterización.

Resultado persistido:

- `characterization_id=24`, `version=algorithm_version=schema_version=2.2`.
- `physical_units_available=true`.
- `physical_status=COMPATIBLE_PROVISIONAL`.
- `physical_measurements_status=PROVISIONAL_CALIBRATION`.
- Snapshot: calibración **1**, etiqueta **CAL-OPTIKA-40X-PROVISIONAL-001**,
  status **PROVISIONAL**, perfil **1**, serie **2**, dimensiones **4928×4928**.
- sx snapshot `0.055233934048000`; sy snapshot `0.055010060892000`.
- Método `AUTOMATIC_MULTI_REFERENCE`, versión `calibration-provisional-v1/18S-A.1`.
- Provenance de calibración conservada, incluida su condición provisional.
  El valor isotrópico auxiliar aparece en la provenance heredada como evidencia,
  **no se usa en los cálculos geométricos**.

Effective segmentation hash:
`27fb0be3b1dc4eb7bdfe8ed45b51850f93444672606a4b33b8752730e198914b`

Fingerprint:
`c80144bf271ed7e977040a69a288a14c44efc4eb93f311a07b95d320c0526b1e`

## Comprobación numérica con precisión persistida

Entidad elegida: **región celular/membrana 1**, contorno original de **72 puntos**.

| Magnitud | Píxeles | Físico persistido |
| --- | ---: | ---: |
| Área | 589536.5 px² | 1791.2607157863686 µm² |
| Perímetro | 3710.6635929959393 px | 204.62452391626837 µm |
| Centroide X | 904.376160198167 px | 49.95225318696904 µm |
| Centroide Y | 1053.2595652121058 px | 57.93987281739939 µm |

Área:
`589536.5 × 0.055233934048 × 0.055010060892 = 1791.2607157863686`.

Perímetro: suma independiente de
`sqrt((dx × sx)^2 + (dy × sy)^2)` sobre los 72 segmentos, incluido cierre:
**204.62452391626843 µm**, igual al persistido dentro de tolerancia de coma flotante
`rel_tol=1e-12, abs_tol=1e-12`. La multiplicación incorrecta por escala media daría
**204.5391891851433 µm**, que no es el valor almacenado.

Centroide: `[904.376160198167 × sx, 1053.2595652121058 × sy]` coincide exactamente con
`[49.95225318696904, 57.93987281739939]`. Posición relativa al origen de la imagen.

Distancia MN–núcleo: **membrana 2, MN 24, núcleo 12**. Se conserva esa asociación.

- Distancia pixelaria: **162.57541936172328 px**.
- Delta de centroides: **[-56.87220508073369, -152.3033790494983] px**.
- Distancia física almacenada y comprobada: **8.947745638538953 µm**.
- Fórmula: `hypot(-56.87220508073369 × sx, -152.3033790494983 × sy)`.

### Features no espaciales y regresión real 2.1

Se comparó contra la caracterización histórica **23 (2.1)** de esta misma muestra:
tras excluir únicamente los nuevos campos físicos y cambios de versión, **todos los
campos existentes coinciden exactamente**, incluidos geometría pixelaria, asociaciones,
ratios, summary, warnings, intensidad, excentricidad y textura. No se recalculó ni
sobrescribió el registro 23.

Ejemplo de membrana 1, idéntico a 2.1 y sin unidades µm:

- Excentricidad: `0.8213823851278335`.
- Circularidad: `0.538043508971418`.
- Intensidad media: `0.7215830145973486`.
- Desviación estándar: `0.15358188907469192`.

GLCM conserva **32 niveles, d=1 px, 0°/45°/90°/135°, symmetric=true,
normalized=true, mean_over_valid_angles**. No hay normalización física de textura.

## API/frontend y revisión visual

El JSON real de la caracterización 24 se renderizó con los componentes Vue actuales
mediante SSR. Verificación **PASS**: versiones, etiqueta, estado Provisional,
texto provisional, ambos dominios de unidades, sx/sy y ausencia del texto de
calibración validada. No se generaron imágenes/previews ni se cambiaron componentes.

No se encontró navegador automatizable instalado. La comprobación SSR no sustituye
la inspección visual humana de layout/interacción. **Revisión visual pendiente**.

Localización: paciente PK **8**, caso PK **8**, análisis PK **8**, muestra **66**,
`EJT_05-12-25_11451_2.jpg`, resultado **28**, caracterización vigente **24**.

Checklist para el investigador:

- [ ] Abrir Caracterización de muestra 66/resultado 28; aparece versión 2.2.
- [ ] Calibración CAL-OPTIKA-40X-PROVISIONAL-001, estado **Provisional**.
- [ ] Texto: “Las medidas físicas utilizan una calibración provisional.”
- [ ] Consultar región celular 1: área **1791.261 µm²** y debajo **589536.50 px²**.
- [ ] Perímetro **204.625 µm** y debajo **3710.66 px**.
- [ ] Centroide **(49.952, 57.940) µm**, con dato secundario pixelario.
- [ ] Región celular 2, MN 24/núcleo 12: **8.948 µm** y **162.58 px**.
- [ ] Detalle de calibración muestra sx/sy separados y resolución 4928×4928.
- [ ] Excentricidad, intensidad y GLCM no se muestran en µm.
- [ ] Historial conserva caracterización 23 de versión 2.1.

No hace falta volver a segmentar ni iniciar microservicios. Si la aplicación no está
arrancada, comandos conocidos (terminales separadas):

```bash
cd ~/repos/sicam-refactor/apps/web/Backend
conda activate sicam
python manage.py runserver 127.0.0.1:8000
```

```bash
cd ~/repos/sicam-refactor/apps/web/Frontend
nvm use 24.17.0
npm run dev -- --host 127.0.0.1 --port 5173
```

No se arrancaron procesos persistentes durante esta aceptación.

## Regresiones y checks

| Validación reejecutada | Resultado |
| --- | --- |
| Backend completo | 345 PASS |
| Characterization 2.2, incluido arriba | 22 PASS |
| Motor de calibración, incluido arriba | 29 PASS |
| Acquisition, Registro, ImageJ, segmentation/effective/revisions | Incluidos en backend completo, PASS |
| Frontend Characterization 2.1 | 22 PASS |
| Frontend Characterization 2.2 | 15 PASS |
| Frontend Registro | 40 PASS |
| Frontend Adquisición | 18 PASS |
| Frontend Segmentación/editor | 59 PASS |
| Render SSR con respuesta real 24 | PASS |
| npm run build | PASS, Node 24.17.0, 113 módulos |
| Django check, antes y después | PASS |
| makemigrations --check --dry-run, antes y después | No changes detected |
| SQLite integrity / foreign keys, backup y BD final | ok / sin infracciones |

Las suites se ejecutaron sobre la implementación 18S-D existente sin modificaciones;
las pruebas backend utilizan su BD de tests. No hubo migraciones.

## Baseline actualizado

| Entidad | Antes | Después |
| --- | ---: | ---: |
| Paciente | 8 | 8 |
| Caso | 8 | 8 |
| AnalisisPred | 8 | 8 |
| MuestraSaliva | 67 | 65 |
| MuestraSangre | 2 | 2 |
| ResultadoSegmentacion | 28 | 28 |
| RevisionSegmentacion | 27 | 27 |
| ResultadoCaracterizacion | 23 | 24 |
| ImageJImportRecord | 23 | 23 |
| SegmentationExecution | 27 | 27 |
| AcquisitionSeries | 2 | 2 |
| AcquisitionProfile | 1 | 1 |
| Calibration | 1 | 1 |
| CalibrationReference | 3 | 3 |

- Total muestras: **67**; con serie **2**, sin serie **65**.
- Compatibilidad: **2 COMPATIBLE_PROVISIONAL**, **65 NO_ACQUISITION_SERIES**;
  **0 IMAGE_MODE_MISMATCH**, **0 COMPATIBLE** y 0 otros estados.
- Caracterizaciones: **2 de 2.0**, **21 de 2.1**, **1 de 2.2**; total **24**.
- Media: **93**. Todos los no objetivo idénticos a pre.
- Únicas mutaciones autorizadas: quitar muestras 65/67, quitar sus media, añadir
  caracterización 24. Ninguna revisión, ejecución ni resultado base cambió.
- SHA-256 final BD: `992e5988e8db90abe02aebf677effe5fa54cf734f88bf250372ffd86c19eba4b`.

Evidencia temporal privada en `/tmp/sicam18sd1/`: snapshots `pre.json`,
`post-delete.json`, `post-characterization.json`, `final.json`; `samples.json`,
`backup.json`, `cleanup-result.json`, `acceptance-result.json`, respuestas API de
ambas llamadas, validación SSR y logs de suites/build/checks. No se versiona contenido
científico de salida ni archivos media. Los scripts temporales tienen precondiciones
estrictas y **no son comandos de mantenimiento reutilizables**.

## Pendientes y siguiente bloque

- **IMPORTANT_PENDING_18S_A2**: repetibilidad, rotación 0°/90°, tolerancias del patrón,
  anisotropía, incertidumbre y criterios científicos siguen pendientes. La prueba
  demuestra el contrato operativo/fórmulas; no valida metrológicamente la calibración.
- `HISTORICAL_ACQUISITION_ASSOCIATION = PENDING_MANUAL_CONFIRMATION`.
- `RETIRED_RECALCULATION_POLICY = PENDING_DECISION`.
- `DURABLE_UPLOAD_IDEMPOTENCY`: pendiente, sin cambios.
- `GLCM_PHYSICAL_DISTANCE_NORMALIZATION = PENDING_SCIENTIFIC_DECISION`.
- `USER_INSTITUTION_PERMISSION_MODEL = NEXT_PRIORITY`.
- `DATA_LIFECYCLE_DELETE_ARCHIVE_RESTORE = AFTER_USER_PERMISSION_MODEL`.

Recomendación para **18T-A**: diseñar e implementar, con alcance aprobado, el modelo
de usuarios/instituciones/permisos y propiedad/acceso de datos. Después abordar
eliminación/archivo/restauración. Esta operación puntual no añade delete genérico,
papelera, soft delete, restore, roles ni audit log.

## Git final y clasificación

18S-D preservado exactamente: 7 tracked modificados + 4 archivos nuevos previos.
18S-D.1 añade sólo `docs/85_sprint_18s_d1_real_physical_characterization_acceptance.md`.
Total final: **7 modificados y 5 untracked**, staging vacío. No hay nuevos cambios de
código ni cambios a IMAGE_MODE_MISMATCH o al motor de calibración.

`git diff --stat` tracked se mantiene en **7 archivos, 130 inserciones, 26
eliminaciones**; los nuevos sin seguimiento no aparecen en ese stat.
`git diff --check`: PASS. No staging, commit ni push.

SPRINT 18S-D.1 = READY_FOR_COMMIT_WITH_MANUAL_VISUAL_REVIEW
