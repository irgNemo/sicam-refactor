# Sprint 17H - Frontend de caracterizacion morfometrica SALIVA v2

## Fecha

2026-09-13

## Referencia Git

- Rama: `master`
- Commit base: `93badea339b5feb644f15defe9ea33202652e8ad`
- Baseline Windows a WSL: cerrado, limpio y sincronizado antes de iniciar 17H.

## Objetivo

Presentar en el frontend el contrato persistido de caracterizacion morfometrica
SALIVA v2 implementado en Sprint 17G, sin cambiar el backend, los formatos
persistidos ni los contratos API. La implementacion conserva el renderer legado
para SALIVA v1 y BLOOD v1, la seleccion historica, los estados de vigencia y el
contexto compartido de navegacion.

## Alcance implementado

- seleccion estricta entre SALIVA v2 y el renderer legado;
- resumen morfometrico y estados de indices;
- calidad de asociaciones;
- una fila por cada elemento persistido en `cells`;
- detalle de membranas, nucleos y micronucleos;
- secciones de objetos no asociados y ambiguos;
- agrupacion de advertencias estructuradas;
- carga independiente de la segmentacion efectiva;
- overlay SVG de solo lectura sobre la imagen de la muestra;
- proteccion contra respuestas tardias al cambiar muestra o resultado;
- estilos responsive y overflow local para tablas y detalles extensos.

Quedaron fuera de alcance y no se modificaron:

- Django, modelos, migraciones, serializers, views, URLs y servicios
  cientificos;
- microservicios SALIVA y BLOOD;
- dependencias y lockfiles;
- contratos API y formatos persistidos;
- `App.vue`, `MainContent.vue`, SideBar, TopBar y el editor de segmentacion;
- exportaciones CSV/PDF y capacidades morfometricas nuevas para BLOOD.

## Arquitectura frontend

### Seleccion del renderer

`CharacterizationResultPanel.vue` mantiene los estados y acciones existentes y
delega unicamente el payload SALIVA v2 al componente nuevo
`SalivaMorphometricResult.vue`. La funcion pura de deteccion y los formateadores
de presentacion viven en:

```text
apps/web/Frontend/src/domain/characterizationPresentation.js
```

La deteccion exige simultaneamente:

```javascript
resultado_json.sample_type === "SALIVA" &&
resultado_json.schema_version === "2.0"
```

No se consulta `algorithm_version`, no se infiere la version por antiguedad y no
se aceptan campos parciales como heuristica.

### Presentacion SALIVA v2

`SalivaMorphometricResult.vue` consume directamente `resultado_json` y presenta:

- `summary`, incluidos totales, clases nucleares y estados cientificos;
- `association_quality`, incluidas sus tasas ya calculadas;
- `cells`, con una fila por elemento y detalle desplegable;
- `unassociated` y `ambiguous` en grupos independientes;
- `candidate_membrane_ids` cuando estan presentes;
- `warnings` agrupadas por `code`, con `object_id`, `message` y contexto
  adicional.

Los valores ausentes o `null` se presentan como `—`. Las longitudes usan `px` y
las areas `px²`. No se muestran micrometros ni otras unidades fisicas.

Los indices, tasas, asociaciones, clases, geometria, intensidad y promedios se
presentan sin recalculo. La unica transformacion cientifica en frontend es la
representacion porcentual de `genotoxicity_index`, multiplicada por 100.
`cytotoxicity_index` y las tasas de asociacion permanecen como los cocientes
persistidos.

### Compatibilidad SALIVA v1 y BLOOD v1

Cualquier payload que no cumpla ambas condiciones de SALIVA v2 sigue la ruta
legada. Esta ruta conserva:

- `counts` e `indices` de SALIVA v1;
- advertencias v1 basadas en cadenas;
- conteos de membranas y micronucleos de BLOOD v1;
- el mensaje de capacidades cientificas pendientes para BLOOD;
- los estados vigente, desactualizado y pendiente;
- las acciones de caracterizar y actualizar.

La ausencia historica de una clave de conteo conserva el valor cero. Un valor
explicitamente `null` se muestra como `—` y nunca se convierte en cero.

### Segmentacion efectiva

`CaracterizacionView.vue` usa el servicio existente:

```text
GET /api/resultados-segmentacion/{id}/efectivo/
```

El frontend no decide la precedencia de revisiones. Presenta la respuesta
resuelta por el backend, que selecciona la ultima revision `VALIDADA` o el
resultado `AUTOMATICO` cuando no existe una validada. Un `BORRADOR` no forma
parte de este contrato.

La imagen se obtiene de la muestra seleccionada y los objetos del bloque
`effectiveSegmentation.resultado.objects`.

### Overlay de solo lectura

`CharacterizationEffectiveOverlay.vue` es independiente de
`SegmentationOverlay.vue`. Reutiliza solamente:

- `calculateOverlayContainment`;
- `scalePolygonPointsToOverlay`;
- paletas y configuracion de etiquetas de `segmentationTypes.js`.

El componente contiene una imagen, un SVG sin eventos de edicion y controles
locales para mostrar u ocultar capas. Permite seleccionar celulas para consulta,
sin editar objetos o vertices. No permite dibujar o mover, no crea revisiones, no genera borradores y no realiza
solicitudes de escritura. `ResizeObserver` y el evento `resize` mantienen la
proyeccion alineada con el contenedor.

#### Decision visual final: sin etiquetas persistentes (2026-09-15)

Tras la inspeccion visual manual se retiraron las etiquetas "Célula X" sobre
la imagen porque se superponian y dificultaban su lectura. Se eliminaron el
texto SVG, sus fondos, el posicionamiento de etiquetas y el CSS exclusivo.
No se sustituyen por numeros flotantes ni badges sobre la imagen.

La identificacion se realiza mediante seleccion bidireccional overlay-tabla,
con `selectedCellId` como fuente unica en `CharacterizationResultPanel.vue`.
La tabla conserva la identificacion "Célula <membrane_id>" mediante la etiqueta
persistida de cada celula y el ID de membrana consultable en el detalle.
El overlay conserva los `aria-label` de las membranas y muestra la seleccion
mediante contorno enfatizado y halo, manteniendo los colores por tipo.
Los nucleos y micronucleos se resaltan exclusivamente mediante las relaciones
persistidas en `cell.nuclei` y `cell.micronuclei`.

El clic en membrana sigue seleccionando la fila y desplazando suavemente el
contenedor local de la tabla cuando es necesario. El clic en tabla sigue
resaltando la membrana y sus asociados. No se modifican IDs, contratos,
calculos cientificos, request guards ni compatibilidad v1.

### Historicos y request guards

Se conserva la implementacion previa para:

- filtrar resultados `COMPLETADO`;
- ordenar por fecha e ID descendentes;
- seleccionar el resultado mas reciente;
- restaurar una seleccion valida desde el contexto compartido;
- usar el resultado mas reciente cuando la seleccion restaurada deja de ser
  valida;
- generar o actualizar una caracterizacion;
- presentar estados vigente, desactualizado y pendiente.

La carga efectiva tiene su propio `effectiveSegmentationRequestId`. Una
respuesta solo se aplica cuando coinciden el token de solicitud y el ID del
resultado actualmente seleccionado. Cada reinicio de contexto incrementa el
token y limpia carga, error y datos efectivos. Esto impide que una respuesta de
otra muestra o resultado reemplace el contexto actual.

No se cambio `App.vue`, la estructura de `sessionStorage` ni las protecciones de
navegacion y borradores del editor.

## Archivos modificados

- `apps/web/Frontend/src/views/CaracterizacionView.vue`
- `apps/web/Frontend/src/components/characterization/CharacterizationResultPanel.vue`

## Archivos creados

- `apps/web/Frontend/src/components/characterization/SalivaMorphometricResult.vue`
- `apps/web/Frontend/src/components/characterization/CharacterizationEffectiveOverlay.vue`
- `apps/web/Frontend/src/domain/characterizationPresentation.js`
- `docs/57_sprint_17h_saliva_morphometric_frontend.md`

## Criterios de aceptacion

- [x] SALIVA v2 se detecta solo con tipo SALIVA y `schema_version` 2.0.
- [x] Los payloads SALIVA v1 y BLOOD v1 usan el renderer legado.
- [x] Se presentan resumen, indices, estados, clases y calidad de asociaciones.
- [x] Cada elemento de `cells` produce una fila consultable.
- [x] Se presentan membranas, nucleos y micronucleos con sus metricas
  persistidas.
- [x] No asociados, ambiguos, candidatos y advertencias tienen secciones
  legibles.
- [x] Los valores `null` no se convierten en cero.
- [x] Solo el indice de genotoxicidad se transforma visualmente a porcentaje.
- [x] La segmentacion efectiva usa el endpoint existente.
- [x] El overlay es de solo lectura y no comparte comportamiento de edicion.
- [x] Las respuestas tardias se descartan por token e ID de resultado.
- [x] Las tablas y detalles extensos usan overflow local.
- [x] Existen reglas responsive para los puntos de trabajo de 1440, 1280 y
  1024 px.

## Validaciones ejecutadas

### Frontend

```text
npm run build
PASS - 98 modulos transformados

npx eslint . --no-cache
PASS
```

Se ejecutaron aserciones Node sobre las funciones puras:

- deteccion positiva SALIVA v2;
- rechazo SALIVA v1, BLOOD v1 y SANGRE con `schema_version` 2.0;
- conversion porcentual de genotoxicidad;
- preservacion visual de `null` como `—` y de cero como cero.

Resultado: `10 presentation assertions passed`.

Se renderizaron los componentes mediante Vue SSR y payloads controlados en
memoria. Se verificaron:

- SALIVA v2 con valores `null` y estado `NOT_COMPUTABLE`;
- celula sin nucleos y celula binucleada;
- micronucleo asociado y sus metricas de dependencia;
- objeto no asociado;
- objeto ambiguo con dos membranas candidatas;
- advertencia estructurada;
- fallback SALIVA v1 con advertencia de texto;
- fallback BLOOD v1 con conteos y mensaje legado.

Resultado: `SSR validation passed without persisted data changes`.

El overlay se renderizo tambien con fuentes controladas `AUTOMATICO` y
`VALIDADA`; se verifico la etiqueta automatica y la revision validada con su
numero. Resultado: `Automatic and VALIDADA effective-source rendering passed`.

Tambien pasaron aserciones de proyeccion sobre una imagen contenida y del guard
de resultado efectivo para token vigente, token obsoleto e ID distinto.

La base local se consulto en modo de solo lectura. El snapshot SALIVA v2
`VALIDADA` existente contiene 30 celulas, 9 anucleadas, celulas con
micronucleos, un micronucleo no asociado y dos advertencias estructuradas.

### Backend y baseline

```text
python manage.py check
System check identified no issues (0 silenced).

python manage.py makemigrations --check
No changes detected

python -m pytest api/tests.py::RevisionSegmentacionTests \
  api/tests.py::CharacterizationCoreTests -q
73 passed in 2.07s

python -m pytest -q
172 passed, 2 skipped in 3.48s

python manage.py test
147 tests, OK in 1.666s

sicam: python -m pip check
No broken requirements found.

sicam-blood: python -m pip check
No broken requirements found.
```

Los dos tests omitidos son los mismos casos del baseline que requieren servicios
o recursos externos.

## Reorganizacion visual de cierre

La zona superior de caracterizacion se reorganizo en dos niveles. El primero
contiene la galeria de muestras y la muestra seleccionada. El segundo contiene
el resultado de caracterizacion con el ancho completo disponible. La busqueda
de casos del SideBar no se modifico.

En escritorio, la zona de seleccion usa una columna flexible para la galeria y
una columna estable para la muestra seleccionada:

- 360 px a partir de 1440 px;
- 350 px entre 1200 y 1439 px;
- 340 px entre 1024 y 1199 px.

Por debajo de 1024 px ambas secciones pasan a flujo vertical. La tarjeta de
muestra seleccionada conserva la imagen, metadatos, selector historico y estados
que ya existian.

La galeria usa miniaturas homogeneas en una cuadricula con filas de 132 px. Su
altura maxima es de tres filas completas, 416 px incluidos los dos espacios de
10 px. Las muestras adicionales se consultan mediante scroll vertical dentro de
la galeria. La pagina no crece por el numero de muestras y el estado seleccionado
conserva borde, fondo y realce visual.

Los breakpoints de columnas son:

- 5 columnas desde 1440 px;
- 4 columnas entre 1200 y 1439 px;
- 3 columnas entre 1024 y 1199 px;
- 3 columnas por debajo de 1024 px mientras hay ancho util completo;
- 2 columnas por debajo de 768 px;
- 1 columna por debajo de 480 px.

Dentro de SALIVA v2, el resultado sigue este orden:

1. resumen morfometrico y clases nucleares compactas;
2. indices cientificos, area y circularidad nuclear promedio;
3. calidad de asociaciones en tarjetas separadas para nucleos y micronucleos;
4. segmentacion efectiva;
5. tabla resumida de celulas con detalle expandible;
6. objetos no asociados, ambiguos y advertencias.

La tabla principal de celulas conserva identificacion, clasificacion, conteos y
estado de asociacion. Los IDs de membrana y origen, junto con las metricas, se
mantienen en el detalle expandible. El ancho minimo y el scroll horizontal estan
limitados al contenedor de la tabla.

La vista principal oculta overflow horizontal y permite solamente scroll
vertical de pagina. Las tablas administran su propio overflow y el overlay limita
su altura entre 320 y 520 px en escritorio para no dominar el resultado.

## Validacion responsive

Las reglas CSS verificadas producen 5 columnas de galeria a 1440 px, 4 a
1280 px y 3 a 1024 px. La muestra seleccionada permanece lateral en esos tres
anchos y el resultado ocupa una fila completa. Las tarjetas cientificas reducen
columnas bajo 1440 px. Las tablas conservan ancho minimo y scroll horizontal
local; los detalles de celulas permanecen dentro del contenedor con overflow.

La validacion posterior a la reorganizacion produjo:

```text
npm run build
PASS - 98 modulos transformados en 1.82s

npx eslint . --no-cache
PASS

git diff --check
PASS
```

El render SSR confirmo que SALIVA v1 y BLOOD v1 permanecen en el renderer
legado, SALIVA v2 conserva su deteccion estricta y las secciones aparecen en el
orden visual documentado. Una comparacion de los bloques `script` verifico que
los request guards, el endpoint efectivo y el despacho funcional no cambiaron
durante esta pasada.

No hay navegador headless instalado en este entorno. Por ello se verificaron el
build, el render SSR, las reglas CSS y los contenedores de overflow, pero queda
pendiente una inspeccion visual interactiva real a 1440, 1280 y 1024 px antes
de considerar cerrada la aceptacion visual.

## Limitaciones conocidas

- El repositorio no configura un framework de tests frontend. Las regresiones
  se validaron con aserciones Node, render SSR, build y ESLint sin agregar
  dependencias.
- La base local no contiene snapshots persistidos SALIVA v1 ni BLOOD v1. Sus
  rutas se verificaron con payloads controlados en memoria.
- La base local no contiene un caso ambiguo ni una celula multinucleada en el
  snapshot vigente; ambos se cubrieron con el payload SSR controlado.
- La inspeccion visual interactiva responsive queda pendiente por ausencia de
  navegador automatizable en WSL.

## Estado de control de cambios

Sprint 17H queda implementado y validado sin commit ni push. La revision y
aprobacion del diff deben ocurrir antes de crear el commit.
