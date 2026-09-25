# Sprint 18C — Selector frontend de estrategia SALIVA

## Baseline y alcance

Precheck del 2026-09-23 en `/home/israel/repos/sicam-refactor`:
`master`, working tree limpio, HEAD inicial
`4ccdbde9fe01bdb845b1cdf03015735260684c34`
(`Add backend saliva segmentation strategies`). Los cinco commits iniciales
fueron `4ccdbde`, `065c073`, `7a3036f`, `93badea`, `f5df193`.
Se leyeron los cierres 18A/18B y la documentación frontend 17H.

Se incorpora selección explícita exclusivamente para nuevas segmentaciones
SALIVA y presentación de la provenance entregada por backend. ALT sólo se
ha probado con SALIVA; no se afirma que sea mejor ni que tenga validación
científica comparativa. BLOOD conserva su flujo, sin selección múltiple.

No se modifican backend, migraciones, normalizadores, microservicios,
algoritmos, modelos, dependencias ni Characterization. No se reescriben
los documentos 58 y 59. No hubo staging, commit ni push.

## Auditoría y punto de integración

| Responsabilidad | Componente o módulo existente |
|---|---|
| Contexto de paciente/caso/muestra/resultado y navegación protegida | `App.vue`, `SideBar.vue` |
| Segmentación SALIVA y BLOOD, loading/error/success, historial, visor/editor | `MainContent.vue` |
| Ejecutar, resumen inmediato, selección de resultado, efectivo y última segmentación | `SegmentationResultPanel.vue` |
| POST por tipo de muestra y GET de historial | `services/segmentationService.js` |
| Transporte compartido | `services/apiClient.js`, Axios sin timeout configurado |
| Revisión, guardado, validación y efectivo | `useSegmentationRevision.js`, `segmentationRevisionService.js` |
| Polígonos, selección, draw, vértices, undo/redo | `useSegmentationEditor.js`, `SegmentationOverlay.vue` |
| Proyección, pan y zoom | `useSegmentationViewport.js`, `MainContent.vue` |
| Caracterización | `CaracterizacionView.vue`, `CharacterizationResultPanel.vue`, servicio y renderers existentes |

Flujo previo: botón → `MainContent.ejecutarSegmentacion` →
`segmentarMuestra` → Django → respuesta inmediata → recarga de historial →
selección del nuevo resultado → carga de efectivo y revisiones → notificación
al contexto del caso. El flujo es síncrono, sin polling, AbortController ni
timeout frontend; el temporizador de Registro no participa en segmentación.

No existía un selector de estrategia ni un componente de radios reutilizable
para esta función. Se usa un control SALIVA pequeño con inputs nativos; no
se incorpora una librería. El editor y sus herramientas permanecen intactos.

## Selector y contrato

`src/domain/segmentationStrategies.js` centraliza valores API, labels,
descripciones y fallback de presentación:

| Valor API | Label UI | Descripción |
|---|---|---|
| `CURRENT_CUSTOM_V1` | Modelo SICAM | Modelo de segmentación utilizado actualmente por SICAM. |
| `ALT_CPSAM_MORPHOLOGICAL_V1` | Cellpose-SAM alternativo | Método alternativo disponible para imágenes de saliva. |

`SalivaSegmentationControl.vue` sólo se instancia cuando el tipo es SALIVA.
Contiene el estado `selectedStrategy`, inicialmente CURRENT, radios y botón.
El panel se identifica mediante la clave tipo/ID de muestra: cambiar de muestra
reinicia CURRENT. Volver a montar la vista también reinicia CURRENT. No se
guarda la preferencia en storage ni en sesiones, y cambiar de resultado
histórico no selecciona automáticamente una estrategia para la próxima ejecución.

El grupo se titula **Método de segmentación** y aclara **Para una nueva
segmentación**. Usa `fieldset`, `legend`, labels envolventes y radios del
mismo grupo: selección y navegación de teclado nativas. El foco visible
conserva el estilo global. El fieldset y el botón quedan disabled durante
procesamiento; además se comprueba loading antes de emitir o ejecutar.

SALIVA emite la estrategia como un valor de esa ejecución; el panel la pasa
a `MainContent`, y el servicio realiza el mismo POST de antes con JSON explícito:

```http
POST /api/muestras/{id}/segmentar/
Content-Type: application/json

{"segmentation_strategy":"CURRENT_CUSTOM_V1"}
```

Para ALT, el valor es `ALT_CPSAM_MORPHOLOGICAL_V1`. El servicio también usa
CURRENT como default para llamadas SALIVA sin tercer argumento. No se alteran
rutas ni otros campos del request.

BLOOD conserva `POST /api/muestras-sangre/{id}/segmentar/` **sin cuerpo**.
El servicio no envía `segmentation_strategy` ni siquiera si un llamador pasa
accidentalmente un argumento SALIVA. No se monta el control SALIVA ni se crea
su estado de selección en BLOOD. Su aviso de procesamiento largo se conserva.

## Presentación, históricos y revisiones

La provenance siempre procede del backend:

- Respuesta inmediata: `resultado_segmentacion.segmentation_strategy`.
- Historial: `segmentation_strategy` de cada resultado, tanto en la tarjeta
  única como en las opciones del selector de resultados completados y la
  tarjeta de última segmentación. Distintas estrategias pueden coexistir.
- Efectivo: `segmentation_strategy` del endpoint efectivo, heredada del padre.

La selección local no se utiliza para atribuir resultados. Los históricos
migrados con CURRENT muestran **Modelo SICAM**. SALIVA null, ausente o con
valor desconocido muestra **Método no disponible**, sin inferir CURRENT.
En BLOOD no se renderiza el campo, incluido su null deliberado.

Estado editorial y método permanecen separados. Se conserva la presentación
**Automático** o **Revisión #n validada**, acompañada del método del padre.
VALIDADA sigue teniendo precedencia sobre AUTOMATICO y un BORRADOR no se
convierte en efectivo. No se añade estrategia a requests de revisión ni se
permite modificar la provenance de una revisión. Elegir otro método sólo
afecta una nueva ejecución de segmentación.

No se cambia el cálculo, renderer ni workflow de Characterization, ni se
agregan ramas CURRENT/ALT. También se conservan guards de navegación,
contexto de muestra y guards contra respuestas de resultados obsoletos.

## Loading y errores

Se mantienen el indicador existente, bloqueo de ejecuciones duplicadas y
actualización de loading en el flujo habitual. No se añade polling, abort,
temporizador ni timeout menor al timeout ALT backend de 240 s. Axios conserva
`timeout=0` (sin límite frontend configurado).

400, 502, 503 y 504 usan `segmentacionError` y el mecanismo de mensajes
existente: mensaje `error` del backend si existe, o el mensaje genérico actual.
No hay reintento automático, fallback silencioso ni ejecución de CURRENT tras
fallar ALT. Los radios vuelven a habilitarse al terminar la petición.

## Pruebas reproducibles

`package.json` no tiene script `test`. Se agrega
`tests/segmentationStrategies.test.mjs`, ejecutable con el runner nativo Node
y los paquetes Vue/Vite ya instalados, sin dependencias ni scripts nuevos:

```bash
cd apps/web/Frontend
node --test tests/*.test.mjs
npm run build
node_modules/.bin/eslint src/domain/segmentationStrategies.js \
  src/components/segmentation/SalivaSegmentationControl.vue \
  src/components/segmentation/SegmentationResultPanel.vue \
  src/components/MainContent.vue src/services/segmentationService.js \
  tests/segmentationStrategies.test.mjs
```

**20 pruebas PASS, 0 omitidas**, ejecución final detallada en 1.20 s.
Incluyen mapping/fallback, requests CURRENT/ALT/BLOOD, interacción reactiva
de radios CURRENT→ALT, remount por muestra, disabled, bloqueo de doble submit,
provenance backend independiente del default local, historial mixto,
AUTOMATICO/VALIDADA × CURRENT/ALT, borrador pendiente, errores sin fallback,
guard de respuesta obsoleta, validación editorial sin strategy en request,
polígonos/selección/vértices/draw/undo-redo, proyección/pan/zoom y presentación
Characterization SALIVA v1/v2 y BLOOD v1 independiente de la estrategia.

Las pruebas combinan SSR, transporte Axios simulado y un host Vue mínimo para
eventos reactivos. **No equivalen a pruebas visuales en navegador.** El host no
simula navegación de teclado ni layout CSS; éstos requieren revisión manual.
Se desactivan WebSocket y dependency scanning del servidor Vite usado en tests.
Durante preparación se corrigieron expectativas del HTML scoped y el wrapper
SSR del host de pruebas; no requirieron cambios funcionales adicionales.
El sandbox devolvía sólo el contenedor del archivo con `node --test`; la
ejecución final fuera del sandbox confirmó explícitamente los 20 casos.

Build: **PASS**, Vite 7.3.0, 101 módulos, 1.88 s; sin warnings.
ESLint sobre los archivos afectados: **PASS**, sin `--fix` ni cambios ajenos.
No se ejecutó `npm audit fix` ni se actualizaron paquetes/lockfiles.

Regresión backend existente, sin modificar sus archivos:

```bash
PYTHONDONTWRITEBYTECODE=1 /home/israel/miniconda3/envs/sicam/bin/python -m pytest \
  api/tests.py::RevisionSegmentacionTests \
  api/tests.py::CharacterizationCoreTests -q -p no:cacheprovider
```

Resultado: **73 passed**, 1.80 s, desde `apps/web/Backend`.

## Smoke de integración real y límite visual

Stack temporal: frontend 5173, Django 8000, CURRENT 8001 y luego ALT 8003.
Vite, API Django y OpenAPI del servicio correspondiente respondieron 200.
Django usó `/tmp/sicam18c-smoke.sqlite3` y `/tmp/sicam18c-media`, con paciente,
caso y muestras demo. La base habitual no se utilizó para estas escrituras.
Los artefactos de smoke, scripts y logs se guardaron exclusivamente en `/tmp`.

La micrografía SALIVA autorizada en 18A se leyó sin modificar el original.
CURRENT usó una copia reducida a 512×512 en almacenamiento temporal; ALT usó
los bytes de la imagen completa JPEG RGB 4928×4928. Son muestras temporales
distintas: no se presentan sus conteos como comparación científica.

Se ejecutaron el método real `MainContent.ejecutarSegmentacion` y el servicio
Axios frontend desde Node contra Django y los microservicios reales. Un
interceptor registró sólo URL, body y timeout, sin tokens/cookies/credenciales.
No se sustituyó el transporte de este smoke por mocks.

| Verificación | CURRENT | ALT |
|---|---|---|
| POST del frontend | CURRENT explícito | ALT explícito |
| HTTP | 200 | 200 |
| Duración del flujo, incluido refresco de historial/efectivo | 0.85 s | 177.43 s |
| Objetos | 0 | 7: 3 membranas, 3 núcleos, 1 MN |
| Historial y efectivo | Modelo SICAM | Cellpose-SAM alternativo |
| Efectivo | AUTOMATICO, CURRENT | AUTOMATICO, ALT |
| Render SSR completo de MainContent | 0 polígonos, resultado y labels presentes | 7 polígonos y labels presentes |

CURRENT emitió `no mask pixels found`; se obtuvo un resultado completado vacío.
Este smoke verifica integración y provenance, **no detección positiva CURRENT**.
ALT mantuvo loading=true en observaciones a los 30, 60, 90, 120 y 150 s, y sólo
liberó loading al completar. Se comprobó que una segunda ejecución durante
loading no enviara otro POST. No hubo timeout ni fallback.

ALT conserva los avisos de Cellpose sobre resizing deprecated y de Torch
sobre sparse invariant checks documentados en 18A; la inferencia terminó 200.
No se ajustaron umbrales ni se emitió juicio de calidad científica.

BLOOD: una muestra sintética temporal de UI se consultó desde Django y se
renderizó con `MainContent` completo, sin radios ni label de método. La suite
verifica el POST sin cuerpo mediante adapter Axios simulado. **No se ejecutó
inferencia BLOOD, y nunca se envió una imagen BLOOD a ALT.**

Evidencia temporal:

- `/tmp/sicam18c-current-evidence.json`, `/tmp/sicam18c-alt-evidence.json`.
- `/tmp/sicam18c-current-result.json`, `/tmp/sicam18c-alt-result.json`.
- `/tmp/sicam18c-real-render-evidence.json`.
- `/tmp/sicam18c-{current,alt,blood}-main-ssr.html`.
- `/tmp/sicam18c-frontend-smoke.mjs`, `/tmp/sicam18c-render-real.mjs`.

**Smoke visual CURRENT/ALT/BLOOD y Network DevTools: PENDING.** No hay
navegador automatizable instalado ni herramienta de navegador disponible.
La captura de requests se hizo en el cliente Axios de Node; no se afirma
haber inspeccionado Network en navegador. Los fragmentos SSR verifican
estructura y datos, no la presentación visual ni interacción real con ratón.

Para cerrar esta parte: en un navegador, abrir la muestra SALIVA de prueba,
comprobar CURRENT inicial, elegir ALT, revisar los bodies en Network, disabled
y loading hasta completar, labels de historial/efectivo, polígonos, teclado y
ausencia del control en BLOOD. No es necesario evaluar calidad científica.

## Archivos y cierre

Archivos existentes modificados:

- `apps/web/Frontend/src/components/MainContent.vue`.
- `apps/web/Frontend/src/components/segmentation/SegmentationResultPanel.vue`.
- `apps/web/Frontend/src/services/segmentationService.js`.

Archivos nuevos:

- `apps/web/Frontend/src/domain/segmentationStrategies.js`.
- `apps/web/Frontend/src/components/segmentation/SalivaSegmentationControl.vue`.
- `apps/web/Frontend/tests/segmentationStrategies.test.mjs`.
- Este documento.

Los diffs de backend, tres microservicios, Characterization, editor SVG,
composables de revisión/editor/viewport y docs 58/59 permanecen vacíos.
No se detectó un defecto de contrato que requiriese cambio backend.
`git diff --check`: PASS; staging vacío. La imagen, JSON, base demo y logs
no aparecen entre archivos a versionar. Se apagaron los procesos temporales
de CURRENT, ALT, Django y Vite; puertos 8001, 8003, 8000 y 5173 libres.

```text
SPRINT 18C = PASS WITH VISUAL SMOKE PENDING
```

Implementación y validación técnica completas; pendiente aceptación visual
en navegador. Sin staging, commit ni push.
