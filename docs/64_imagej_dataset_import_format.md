# Formato de importación ImageJ → SICAM

Contrato `imagej-gray-v1`; convertidor `1.0`. Este flujo importa anotaciones
manuales SALIVA. No ejecuta segmentación ni caracterización. No importa clase,
diagnóstico, tratamiento, grupo experimental ni variables clínicas.

## Estructura oficial

```text
dataset/
├── pacientes.xlsx
└── pacientes/
    └── ACL/
        ├── ACL_106.5,40.jpg
        ├── ACL_106.5,40.tif
        ├── ACL_106.5,41.jpg
        └── ACL_106.5,41.tif
```

Los nombres del árbol son ejemplos del contrato, no información clínica.
Cada carpeta identifica `patient_key`. Las imágenes de este lote corresponden
siempre al **Caso 1** del paciente. No se deduce el caso del nombre ni del nivel
de carpetas. Las carpetas no representan clases clínicas.

Imágenes fuente: `.jpg`, `.jpeg`, `.png`. Máscaras: `.tif`, `.tiff`.
La pareja exige mismo directorio y basename literal idéntico: no quitar puntos,
comas, guiones, espacios internos ni sufijos. Las extensiones no distinguen
mayúsculas. Más de una imagen/máscara por basename o basenames que difieren sólo
en mayúsculas son ambiguos. No se emparejan archivos entre carpetas.

## Archivo de pacientes

Formato estándar: XLSX con una sola hoja y encabezados en fila 1:

| Campo | Contenido |
| --- | --- |
| `patient_key` | Texto que corresponde a la carpeta |
| `patient_id` | ID externo del hospital; preferentemente texto para conservar ceros |
| `initials` | Iniciales del paciente pseudonimizado |
| `birth_date` | Fecha Excel serial entera o texto ISO `YYYY-MM-DD` |

Matching carpeta ↔ patient_key: `strip().casefold()` e igualdad exacta.
`ACL != ACL2`. No hay contains, prefijos ni similitud. Una clave con varias filas
produce `PATIENT_MATCH_AMBIGUOUS`; sin fila, `PATIENT_NOT_FOUND`.

`patient_id` es único dentro del namespace obligatorio de la importación, no la
PK Django ni las iniciales. IDs externos duplicados en el Excel bloquean su
lectura. Números Excel sólo se aceptan enteros no negativos de hasta 15 dígitos;
no pueden recuperar ceros iniciales ya perdidos por Excel. IDs de texto conservan
sus ceros. Las fechas son obligatorias: `MISSING_BIRTH_DATE` / `INVALID_BIRTH_DATE`
impiden importar. No se inventa una fecha. Se reconoce la época 1900/1904 de Excel
con rechazo del día ficticio 1900-02-29. No se aceptan fórmulas en campos usados.

Adapter explícito `--patients-format ijc1` para **BD_IJC1.xlsx**: una sola hoja,
encabezados en fila 2. Mapping fijo:

- `patient_key` ← `Iniciales`
- `external_patient_id` ← `ID`
- `initials` ← `Iniciales`
- `birth_date` ← `Fecha de nacimiento`

Otras columnas de datos no se consumen. No hace falta reescribir el Excel actual.
El lector sólo lee celdas; no evalúa fórmulas ni modifica el archivo. Las filas
sin carpeta no crean pacientes.

## Máscaras y clases opcionales

TIFF monocanal gris uint8, una sola página, sin paleta. Imagen y máscara deben
medir exactamente lo mismo. Orientación EXIF distinta de 1 se rechaza; no se
rota, redimensiona, interpola ni convierte una máscara RGB silenciosamente.

| Valor | Contrato raster | Objeto SICAM |
| ---: | --- | --- |
| 0 | Background | Ninguno |
| 85 | Micronucleus | `micronucleo` |
| 170 | **Cell region** | `membrana`, mediante contorno exterior |
| 255 | Nucleus | `nucleo` |

Todas las clases son opcionales. Son válidos `{0}`, `{0,85}`, `{0,255}`,
`{0,170}`, `{0,85,255}`, `{0,170,255}`, `{0,85,170}` y `{0,85,170,255}` si su
geometría también es representable. Un valor diferente genera
`UNEXPECTED_MASK_VALUE`. No se reclasifican objetos por tamaño.

## Cómo etiquetar 170

Dibujar un ROI cerrado y **rellenar la región celular** con 170. Después, los
núcleos 255 y micronúcleos 85 pueden ocupar parte de ese interior, sustituyendo
170 en esos píxeles porque el TIFF tiene un único canal.

No dibujar sólo una línea fina de membrana, un segmento abierto ni una región
con interior de fondo. Mantener células distintas separadas; no usar conexiones
sólo diagonales para unir partes de un objeto.

El convertidor extrae componentes 170 y su contorno externo. Al rasterizar ese
contorno, los píxeles interiores adicionales al componente sólo pueden ser 85 o
255. Esos interiores forman parte de la región celular; no son huecos reales.
Un interior con fondo 0 o con otro componente 170 se rechaza. No se rellena
fondo ni se altera la máscara original. Núcleos/MN se extraen también como
objetos independientes: no se persisten asociaciones celulares inferidas.

## Conversión y límites

Conectividad 8 por valor; comprobación adicional de conectividad 4 para detectar
puentes diagonales. `findContours(RETR_TREE, CHAIN_APPROX_NONE)`, sin
`approxPolyDP` ni simplificación. Un componente → un polígono simple; lista sin
repetir el punto inicial, al menos tres vértices distintos, área positiva,
coordenadas enteras originales dentro de la imagen, sin autointersecciones.

La tolerancia de rasterización es **0 píxeles diferentes** usando Pillow
`ImageDraw.polygon`, el mismo tipo de rasterización usado en SICAM. Para N/MN se
exige igualdad con el componente; para cell region se permiten únicamente las
oclusiones interiores 85/255 descritas arriba. No se afirma que el área continua
del polígono sea igual al área contada en píxeles.

Se rechaza la pareja completa (`SKIP_PAIR`, requiere `MANUAL_REVIEW`) ante
`REAL_HOLE`, `MULTIPLE_EXTERIORS`, `DIAGONAL_BRIDGE`, `SELF_INTERSECTION`,
`DEGENERATE_CONTOUR` o falta de equivalencia raster. El reporte muestra
`UNSUPPORTED_POLYGON_TOPOLOGY` y el primer motivo encontrado. No se elimina sólo
un objeto ni se repara GT. Tocar el borde no es error si las demás reglas pasan.

Ejemplos válidos: fondo solamente; núcleo sólido sin membrana; MN sólido sin
núcleo; célula rellena sola; célula rellena con interiores nucleares 255/85.
Ejemplos inválidos: valor 84, dimensiones diferentes, agujero de fondo en un
núcleo, dos regiones unidas sólo por una esquina, contorno degenerado o nombres
sin pareja exacta. Un raster con valores válidos todavía puede tener topología
inválida.

## Comando y piloto

Ejecutar desde `apps/web/Backend`, en un entorno con sus requirements instalados
y una BD con la migración `0008_imagej_manual_import` aplicada:

```sh
python manage.py import_imagej_dataset \
  --source <dataset-root> \
  --patients-file <pacientes.xlsx> \
  --dataset-key ijc1-case1 \
  --patient-namespace ijc1 \
  --case-number 1 \
  --dry-run
```

`--case-number` tiene default 1; otros valores no se admiten en esta versión.
`--patient <patient_key>` es repetible y exacto; `--limit N` procesa las primeras
N entradas de pairing en orden determinista (incluye entradas rechazables).
`--strict` detiene en el primer error de pareja; por defecto continúa.

Layouts adicionales, siempre explícitos:

- `--layout legacy-flat`: ROOT/PATIENT/files, estructura actual del dataset.
- `--layout legacy-repeated`: ROOT/PATIENT/PATIENT/files, con repetición literal
  exacta y sin hermanos/archivos paralelos.

No se siguen symlinks ni se adivinan niveles de carpetas. Para el Excel actual
combinar el layout correspondiente con `--patients-format ijc1`.

El comando escribe un reporte JSON en stdout con aliases, estados, acciones y
conteos. No imprime fechas de nacimiento, IDs hospitalarios ni nombres de
archivos de pacientes. Exit 0 = sin errores; exit 2 = parejas rechazadas;
error global de argumentos/Excel = exit 1. El exit 2 no significa que se
repararon las parejas ni que el importador falló en detectar un defecto.

**`--dry-run` no escribe BD ni storage.** Sin ese flag se persiste; ejecutar una
importación real requiere aprobación explícita del responsable. En Sprint 18H
se autorizó solamente dry-run real. No existen `--force` ni `--overwrite`.

## Después de importar

Base `MANUAL`, estrategia NULL, visible como **Anotación manual**, todavía no
VALIDADA. Al pulsar Editar se crea el BORRADOR normal. Se pueden editar N/MN,
agregar membranas, guardar y validar. BORRADOR nunca es efectivo. El TIFF y la
imagen se conservan byte a byte en storage gestionado; el resultado no depende
de la carpeta externa. Una reimportación idéntica no altera borradores ni
revisiones validadas; cambios de imagen/máscara producen conflictos.
