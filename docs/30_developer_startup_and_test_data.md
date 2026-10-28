# SICAM — Arranque cotidiano y datos de prueba

Manual operativo canónico WSL, actualizado para el estado posterior a 18C.
Para crear ambientes, instalar dependencias, configurar `.env` o provisionar
modelos desde cero, seguir primero la
[guía de instalación WSL](developer_environment_setup_wsl.md).
Los comandos siguientes son Bash y suponen el repo en `~/repos/sicam-refactor`.

## Arquitectura y prerrequisitos

```text
Vue/Vite :5173 -> Django REST :8000 -> SQLite
                       +-> SALIVA CURRENT :8001
                       +-> BLOOD          :8002
                       +-> SALIVA ALT     :8003
```

| Ambiente | Uso | Versión validada |
|---|---|---|
| `sicam` | Django + SALIVA CURRENT | Python 3.10.20 |
| `sicam-blood` | BLOOD | Python 3.10.21 |
| `sicam-saliva-alt` | SALIVA ALT | Python 3.10.20 / Cellpose 4.0.8 |
| nvm | Frontend | Node 24.17.0 / npm 11.13.0 |

Modelos ya provisionados: CURRENT usa
`apps/segmentation-saliva/segmentacion_core/membranas_500_125`; BLOOD y ALT
pueden compartir `~/.cellpose/models/cpsam`. Ver rutas alternativas, checksums
y diferencias entre vendorizado y PyPI en la guía de instalación.

Después de incorporar cambios del repositorio que incluyan migraciones:

```bash
cd ~/repos/sicam-refactor/apps/web/Backend
conda activate sicam
python manage.py migrate
python manage.py showmigrations
python manage.py check
```

Aplicar las migraciones versionadas, incluida `0007_saliva_segmentation_strategy`.
No generar migraciones para arrancar. Si la instalación usa PostgreSQL,
asegurar primero que esa base esté disponible; SQLite no requiere otro proceso.

## Stack completo: cinco terminales

Una terminal por proceso. Django puede arrancar sin los microservicios, pero
hay que esperar que esté listo el correspondiente antes de pulsar Segmentar.

### Terminal 1 — Django

```bash
cd ~/repos/sicam-refactor/apps/web/Backend
conda activate sicam
python manage.py runserver 127.0.0.1:8000
```

### Terminal 2 — Frontend

```bash
cd ~/repos/sicam-refactor/apps/web/Frontend
nvm use 24.17.0
npm run dev -- --host 127.0.0.1 --port 5173
```

Si Vite anuncia otro puerto por estar 5173 ocupado, resolver la colisión antes
de probar; CORS está configurado para los orígenes documentados.

### Terminal 3 — SALIVA CURRENT

```bash
cd ~/repos/sicam-refactor/apps/segmentation-saliva
conda activate sicam
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

Estrategia `CURRENT_CUSTOM_V1`, label **Modelo SICAM**. Carga el modelo
personalizado al importar la aplicación. No instalar Cellpose PyPI en `sicam`.

### Terminal 4 — BLOOD

```bash
cd ~/repos/sicam-refactor/apps/segmentation-blood
conda activate sicam-blood
python -m uvicorn main:app --host 127.0.0.1 --port 8002
```

**BLOOD = `main:app`**: el archivo ASGI es `main.py` en la raíz del
microservicio. No está en el subdirectorio `app`. Su lifespan precarga
Cellpose/cpsam; `/docs` puede tardar en estar disponible.

### Terminal 5 — SALIVA ALT

```bash
cd ~/repos/sicam-refactor/apps/segmentation-saliva-alt
conda activate sicam-saliva-alt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8003
```

Estrategia `ALT_CPSAM_MORPHOLOGICAL_V1`, label **Cellpose-SAM alternativo**.
Usa CPU y verifica versión, tamaño y hash de cpsam durante startup. No descarga
pesos ni cambia silenciosamente de estrategia. Para reproducir el límite de
recursos usado en smokes, opcionalmente exportar antes del comando:

```bash
export OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4
```

Estas variables limitan threads; no cambian thresholds científicos.

En los tres microservicios esperar `Application startup complete` y después
verificar HTTP. Crear el proceso no significa que el modelo ya esté listo.

## Arrancar sólo lo necesario

| Flujo | Procesos requeridos |
|---|---|
| Navegación, UI y consulta de históricos | Django + Frontend |
| Nueva segmentación SALIVA CURRENT | Django + Frontend + CURRENT |
| Nueva segmentación SALIVA ALT | Django + Frontend + ALT |
| Probar ambas opciones del selector | Django + Frontend + CURRENT + ALT |
| Nueva segmentación BLOOD | Django + Frontend + BLOOD |
| Full stack | Los cinco procesos |
| Caracterización de resultados existentes | Django + Frontend; imágenes y resultados disponibles |

Characterization vive en Django y no reejecuta Cellpose. No tiene un sexto
servicio ni un puerto adicional. ALT sólo está habilitado para SALIVA; no se
utiliza para BLOOD.

## Checks rápidos de disponibilidad

Ejecutar sólo los checks de los procesos que se hayan levantado:

```bash
curl --fail http://127.0.0.1:8000/api/
curl --fail http://127.0.0.1:8000/api/pacientes/
curl --fail http://127.0.0.1:5173/ >/dev/null
curl --fail http://127.0.0.1:8001/docs >/dev/null
curl --fail http://127.0.0.1:8001/openapi.json >/dev/null
curl --fail http://127.0.0.1:8002/docs >/dev/null
curl --fail http://127.0.0.1:8002/openapi.json >/dev/null
curl --fail http://127.0.0.1:8003/docs >/dev/null
curl --fail http://127.0.0.1:8003/openapi.json >/dev/null
```

Django registra `/api/` mediante DRF y `/api/pacientes/`. No registra
`/api/health/`; tampoco hay `/health` dedicado en estos microservicios.
Un 404 en la raíz Django `/` no significa que el backend esté caído.
Estos GET no ejecutan segmentación; el startup sí carga modelos.

## Configuración cotidiana

No copiar `.env.example` sobre un `.env` configurado. Revisar las variables
reales en la [guía de instalación](developer_environment_setup_wsl.md#6-configuración-base-y-frontend).
Valores locales de routing:

| Método / tipo | URL del servicio | Timeout Django |
|---|---|---:|
| CURRENT | `http://127.0.0.1:8001` | 30 s |
| ALT | `http://127.0.0.1:8003` | 240 s |
| BLOOD | `http://localhost:8002` (o 127.0.0.1 configurado explícitamente) | 240 s |

Frontend: `VITE_API_BASE_URL=http://127.0.0.1:8000`. Reiniciar Django o Vite si
se cambia su `.env`. No apuntar el frontend directamente a los microservicios.

## Datos mínimos reproducibles

Desde Backend con `sicam`:

```bash
cd ~/repos/sicam-refactor/apps/web/Backend
conda activate sicam
python manage.py seed_demo_data
```

El comando existe en `api/management/commands/seed_demo_data.py`. Crea o reutiliza
un paciente ficticio (`SICAM-DEMO-001`), caso, `AnalisisPred` y `MuestraSaliva`.
Sin argumentos usa un **PNG transparente de 1×1**, embebido en el comando:
sirve para poblar la galería, **no para inferencia o detección positiva**.
No crea muestras BLOOD ni resultados de segmentación.

No hay un directorio de fixtures versionadas ni un paso `loaddata` requerido.
No se necesita un archivo externo `test_image.jpg` para crear estos datos demo.

Para imágenes SALIVA de prueba autorizadas y locales, reemplazar las rutas:

```bash
python manage.py seed_demo_data --image /ruta/autorizada/saliva.png
python manage.py seed_demo_data --image-dir /ruta/autorizada/saliva
```

Admite combinar ambos argumentos. `--image-dir` no es recursivo y acepta
`.jpg`, `.jpeg`, `.png`, `.tif`, `.tiff`. Evita duplicados por nombre base dentro
del análisis demo; repetir no elimina ni sobrescribe registros existentes.
Las imágenes se copian mediante storage a `MEDIA_ROOT`, que por defecto es
`apps/web/Backend/media/`, ignorado por Git.

La micrografía real autorizada en los smokes 18A–18C **no es una fixture
versionada** ni debe asumirse disponible en una WSL nueva. Sus artefactos de
`/tmp` son temporales. No copiar imágenes clínicas/reales al repositorio ni
confundir el PNG sintético con una validación científica.

## Carga manual y flujo de resultados

1. En **Registro**, crear paciente y caso con análisis.
2. En **Agregar Imágenes**, seleccionar tipo, paciente/caso/análisis y cargar
   imágenes de prueba autorizadas. BLOOD se carga por este flujo o por su API,
   no por `seed_demo_data`.
3. En **Segmentación**, seleccionar paciente, caso y muestra.
4. SALIVA muestra **Modelo SICAM** por defecto. Elegir **Cellpose-SAM
   alternativo** sólo para una nueva segmentación SALIVA.
5. Ejecutar y esperar. El selector queda disabled durante procesamiento; no
   hay timeout frontend propio ni fallback automático si ALT falla.
6. Revisar el resultado, historial y método persistido por backend. Cambiar la
   elección no modifica la provenance de resultados anteriores.
7. Editar/guardar BORRADOR y validar si corresponde. VALIDADA tiene precedencia
   sobre AUTOMATICO; BORRADOR nunca es el resultado efectivo.
8. En **Caracterización**, seleccionar un resultado COMPLETADO y caracterizar
   su efectivo. SALIVA v2 muestra morfometría; históricos SALIVA v1 y BLOOD v1
   conservan sus contratos. BLOOD no adquiere morfometría por usar este stack.

Endpoints relevantes:

```text
POST /api/pacientes/
POST /api/casos/
POST /api/analisis/
POST /api/muestras/                            # multipart imagen + analisis
POST /api/muestras-sangre/                     # multipart imagen + analisis
POST /api/muestras/{id}/segmentar/             # JSON segmentation_strategy
POST /api/muestras-sangre/{id}/segmentar/       # sin segmentation_strategy
GET  /api/muestras/{id}/resultados-segmentacion/
GET  /api/muestras-sangre/{id}/resultados-segmentacion/
GET  /api/resultados-segmentacion/{id}/efectivo/
POST /api/resultados-segmentacion/{id}/caracterizar/
GET  /api/resultados-segmentacion/{id}/caracterizaciones/
```

CURRENT/ALT usan respectivamente `CURRENT_CUSTOM_V1` y
`ALT_CPSAM_MORPHOLOGICAL_V1` en el JSON SALIVA. Si se omite el campo al llamar
la API SALIVA, Django usa CURRENT. BLOOD rechaza el campo, incluso null.

ALT observó 170–180 s en CPU con una micrografía 4928×4928; BLOOD también puede
requerir minutos. Son referencias, no SLA. No juzgar calidad científica a
partir de disponibilidad HTTP, conteos de una muestra o tiempos.

Para inspección del overlay, comprobar que `resultado_normalizado.objects`
contiene polígonos, que la imagen cargó, que las capas están visibles y que el
resultado efectivo seleccionado es el esperado. No se requiere alterar geometría.

## Validaciones rápidas y regresión

Backend, desde su directorio con `sicam`:

```bash
python manage.py check
python manage.py showmigrations
python -m pip check
python -m pytest -q
python manage.py test
```

Frontend, desde su directorio con `nvm use 24.17.0`:

```bash
node --test tests/*.test.mjs
npm run build
```

No existe script `npm test`. No actualizar dependencias para arrancar.
Para BLOOD y ALT, en sus respectivos ambientes: `python -m pip check` y
`python -m uvicorn --version`. Verificación estructural desde la raíz:

```bash
ls apps/segmentation-saliva/app/main.py \
   apps/segmentation-blood/main.py \
   apps/segmentation-saliva-alt/app/main.py
```

No importar `app.main` de CURRENT para validaciones livianas: carga el modelo.
No invocar loaders, endpoints POST ni descargar pesos como parte de un check
estructural. Los tests ALT opcionales están descritos en su README.

## Diagnóstico y apagado

| Problema | Comprobación |
|---|---|
| `conda` no está disponible | `source ~/miniconda3/etc/profile.d/conda.sh`, activar el ambiente; no usar Python del sistema |
| `nvm` no está disponible | `source ~/.nvm/nvm.sh`; usar Node de WSL |
| BLOOD no encuentra el módulo ASGI | Ejecutar `main:app` desde la raíz de `apps/segmentation-blood` |
| BLOOD no importa `cellpose` / `natsort` | Revisar ambiente e instalación local `-e .`; requirements ya declara natsort |
| `cpsam` falta / hash ALT no coincide | Verificar cache y provisionar según instalación; no cambiar thresholds |
| Conflicto nativo/OpenMP BLOOD | Usar `sicam-blood`; no mezclar con `sicam` ni recomendar variables para ocultar el problema |
| Error 503 al segmentar | Revisar servicio de la estrategia elegida, puerto, startup completo y URL Django |
| Error 504 / demora larga | Revisar carga CPU, tamaño de imagen y timeout de ese servicio; no cambiar automáticamente de método |
| Galería vacía | Revisar paciente/caso/análisis y seed/carga de imágenes |
| Imagen no carga | Revisar archivo en MEDIA_ROOT y `DEBUG=True`; Django sirve `/media/` sólo en desarrollo |
| No hay caracterización vigente | Seleccionar COMPLETADO y verificar efectivo e imagen disponible |
| Cambios de `.env` no se aplican | Reiniciar el proceso correspondiente |

Detener **cada proceso iniciado** con `Ctrl+C` y esperar su salida. Comprobar:

```bash
ss -ltn '( sport = :5173 or sport = :8000 or sport = :8001 or sport = :8002 or sport = :8003 )'
```

No dejar inferencias o servidores huérfanos. Mantener fuera de Git `.env`,
SQLite, `media/`, modelos, cachés, `node_modules/`, `dist/` e imágenes reales.
Actualizar este manual si cambian ambientes, puertos, entrypoints o comandos;
las instalaciones completas corresponden a la guía WSL.

## Login local: host canónico, cookies y persistencia de sesión

Revisión del 28/10/2026, rama `master`, HEAD inicial
`ae75308f9f617c7278d8eb7a43ba95a612e92598`. El árbol inicial estaba **limpio**:
18U-B/B.1 ya estaba incorporado en ese commit. Ningún archivo de autenticación
estaba modificado y no se alteró Dataset Builder durante esta revisión.

### Causa comprobada y corrección mínima

El frontend configura `VITE_API_BASE_URL=http://127.0.0.1:8000` tanto en `.env`
local como en `.env.example`; Axios usa URL absoluta, `withCredentials: true`,
`withXSRFToken: true` y header `X-CSRFToken`. No hay proxy Vite.
Ambos orígenes están permitidos por CORS y CSRF en desarrollo. Sin embargo,
`http://localhost:5173` → `http://127.0.0.1:8000` cruza **sitios** distintos.
Una cookie `SameSite=Lax` no se envía en esas llamadas fetch/XHR, incluso con
credenciales habilitadas. CORS y trusted origins no sustituyen la cookie CSRF.
Referencia: [MDN — credenciales y SameSite](https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API/Using_Fetch#including_credentials).

Se reprodujo en Chrome instalado, con perfiles temporales separados y backend
Django aislado en `127.0.0.1:18001`, SQLite sintético en `/tmp` y un usuario de
prueba. Se conservaron las mismas políticas de cookies, CORS y CSRF del proceso
activo (`DEBUG=True`). No se probaron contraseñas reales ni se crearon sesiones
reales para el experimento. El puerto alternativo evita tocar la base real;
no cambia la relación de sitios de las peticiones.

| Entrada frontend antes del arreglo | Origin / Referer | API Host de la réplica | Sec-Fetch-Site | Login POST |
|---|---|---|---|---|
| `http://127.0.0.1:5173/` | `http://127.0.0.1:5173` / mismo origen con `/` | `127.0.0.1:18001` | `same-site` | 200, usuario autenticado |
| `http://localhost:5173/` | `http://localhost:5173` / mismo origen con `/` | `127.0.0.1:18001` | `cross-site` | 403, `CSRF cookie not set` |

En ambos casos, `/api/auth/me/` devolvió 200 y token CSRF en el cuerpo, y el
preflight/CORS permitió la petición. Desde localhost el POST llevaba
`X-CSRFToken` pero **ninguna cookie**. No era un 401, rechazo de contraseña,
fallo de red ni fallo de CORS. Una prueba backend confirma que ese rechazo
ocurre antes de llamar a `authenticate`.

La réplica con `DEBUG=False` y cookies Secure reprodujo la misma diferencia en
Chrome; no es necesario cambiar Secure para resolver el cruce de sitios.
Se contrastó el backend real sólo mediante GET anónimo a
`http://127.0.0.1:8000/api/auth/me/`, con ambos Origin: 200, CORS explícito y
cookie CSRF. No se leyó el perfil personal del navegador ni se afirma conocer
la cookie concreta de la sesión previamente observada por Israel.

La corrección está en `Frontend/dev/canonicalOrigin.mjs` y `vite.config.js`:
Vite de desarrollo responde **307 temporal, Cache-Control: no-store** a GET/HEAD
entrantes por localhost cuando la API HTTP configurada usa `127.0.0.1`.
El destino usa `127.0.0.1`, conserva puerto, ruta y query del frontend. No
redirige POST ni transporta credenciales enviadas. No aplica a producción,
HTTPS ni configuraciones de API remota/relativa. Tras el arreglo se verificó:

- `http://localhost:5173/` → 307 → `http://127.0.0.1:5173/` → 200.
- Chrome entrando por localhost terminó en el origen canónico y completó
  login, `/me` autenticado, logout, `/me` anónimo y segundo login/logout.
- Se mantiene el acceso directo normal por `127.0.0.1:5173`.

Se evaluó usar `/api` relativo con proxy Vite. Requeriría cambiar el contrato de
URL absoluta compartido por otros consumidores y la entrega de medios; no hace
falta para este problema. Se conserva la arquitectura y se establece **un solo
host canónico**. Localhost funciona como entrada redirigida, no como una segunda
sesión que comparta cookies por alias.

### Contrato de cookies y autenticación

| Propiedad | `sessionid` | `csrftoken` |
|---|---|---|
| Domain | ausente, host-only `127.0.0.1` | ausente, host-only `127.0.0.1` |
| Path | `/` | `/` |
| SameSite | `Lax` | `Lax` |
| HttpOnly | sí | no |
| Secure del proceso de desarrollo activo (`DEBUG=True`) | no | no |
| Persistencia observada | 1 209 600 s (14 días) | 31 449 600 s |

Los puertos no separan cookies del mismo host. Localhost e IP son hosts/sitios
diferentes; sus cookies no se convierten en compartidas por autorizar CORS.
No se amplió Domain, no se usó SameSite=None, no se desactivó CSRF ni se cambió
ninguna política backend/producción. Producción continúa exigiendo sus cookies
Secure, HTTPS y orígenes explícitos.

El servidor activo se inició con `DEBUG=True` heredado; una shell sin esa
variable carga actualmente `DEBUG=False` y por política habilita cookies Secure.
Para una reproducción inequívoca de desarrollo HTTP, declarar explícitamente
el ambiente de desarrollo y DEBUG **en esa terminal**, como abajo. No cambiar
variables del despliegue de producción para este propósito.

`AuthGate` inicializa la sesión mediante `/api/auth/me/`. Una sesión válida
persistente hace que devuelva usuario y se abra la aplicación sin pedir otra
vez credenciales. Reiniciar Vite/Django no borra cookies ni sesiones SQLite.
`SESSION_EXPIRE_AT_BROWSER_CLOSE=False`, edad de sesión 14 días y
`SESSION_SAVE_EVERY_REQUEST=False`: no es una autenticación accidental.
Sin sesión válida, `/me` devuelve **200 con `user: null`**, no 401; AuthGate
muestra login. Los recursos protegidos devuelven 403 sin acceso operativo.

No se restaura autenticación desde localStorage/sessionStorage. Allí sólo se
conserva contexto de UI e identificador de contexto; el usuario y token CSRF
se toman del servidor. Logout ejecuta `django.contrib.auth.logout`, elimina la
sesión del servidor, expira `sessionid` y limpia usuario/contexto frontend.
Reutilizar la cookie anterior no restaura acceso. El siguiente login vuelve a
adquirir CSRF y funciona. Pruebas con ADMIN, OPERATOR y REVIEWER verifican
reapertura con cookie vigente, logout, replay rechazado y re-login. Usuarios e
instituciones inactivos y peticiones sin CSRF siguen rechazados.

### Reproducción manual para Israel

1. Detener Django y Vite de sus terminales con Ctrl+C. No es necesario iniciar
   los servicios de segmentación para probar autenticación.
2. Iniciar Django en una terminal:

   ```bash
   cd ~/repos/sicam-refactor/apps/web/Backend
   conda activate sicam
   export DJANGO_ENV=development DJANGO_DEBUG=True
   python manage.py runserver 127.0.0.1:8000
   ```

3. Iniciar Vite en otra terminal, conservando
   `VITE_API_BASE_URL=http://127.0.0.1:8000` en su `.env`:

   ```bash
   cd ~/repos/sicam-refactor/apps/web/Frontend
   nvm use 24.17.0
   npm run dev -- --host 127.0.0.1 --port 5173
   ```

4. Abrir **http://127.0.0.1:5173/**. Con cookie de sesión vigente, se espera
   entrada directa; sin ella, se espera login. Puede compararse con una ventana
   privada para obtener un contexto sin cookies previas.
5. Cerrar sesión. Verificar pantalla de login y `/api/auth/me/` con
   `user: null`; `sessionid` debe expirar.
6. Entrar con credenciales existentes. Verificar login POST 200 y `/me` con
   usuario. No imprimir ni compartir contraseña, cookies ni tokens.
7. Refrescar: debe persistir la sesión. Cerrar sesión otra vez y refrescar o
   volver atrás: ninguna petición protegida debe recuperar acceso sin login.
8. Abrir **http://localhost:5173/**: debe cambiar a **127.0.0.1:5173** antes
   de cargar la aplicación. Repetir login/logout en ese destino. Reiniciar
   Vite si aún no recoge la configuración actualizada.
9. En DevTools comparar URL, Origin, Referer y cookies enviadas. API real:
   `http://127.0.0.1:8000/api/auth/{me,login,logout}/`. Con host canónico, las
   llamadas son cross-origin por puerto, pero same-site por esquema/host.

La revisión no ejecuta segmentación, Characterization ni generación de datasets.
El HTML temporal de diagnóstico y sus servidores aislados se retiraron al
terminar; los servidores de trabajo del usuario permanecen activos.

### Validación final de la revisión de autenticación

- Backend dirigido: **6 passed** (`api/test_access.py::SessionTests`).
- Frontend dirigido: **17 passed** (14 auth + 3 host canónico).
- Backend completo una vez: **491 passed, 2 skipped**, cero fallos;
  36 avisos existentes de deprecación Django. No cambió código backend de
  ejecución; se amplió su cobertura de regresión de sesiones/CSRF.
- Frontend completo una vez: **226 passed**, cero fallos, ejecutando cada uno
  de los 11 archivos de tests en proceso separado con
  `node --test --test-isolation=none tests/<archivo>.test.mjs`.
- `npm run build` una vez: PASS; mismos hashes de assets de aplicación que
  antes, dado que el arreglo está en el servidor de desarrollo.
- `manage.py check`: sin incidencias; `makemigrations --check --dry-run`:
  sin cambios; `pip check`: sin dependencias rotas (sólo aviso de caché no
  escribible). No hay migración ni dependencias nuevas.
- Comparación de hashes antes/después de todas las filas de cada tabla real:
  idénticas; `integrity_check = ok`, `foreign_key_check = []`.
  LifecycleEvents **53 → 53**, Characterization **27 → 27**, incluida la 24;
  tablas Dataset/Patient/Sample **2/9/36 → 2/9/36**. Calibraciones y los **95**
  nombres/hashes de media idénticos. No se restableció ninguna contraseña.
- Archivos de este arreglo: `Backend/api/test_access.py`,
  `Frontend/vite.config.js`, `Frontend/dev/canonicalOrigin.mjs`,
  `Frontend/tests/auth.test.mjs`, `Frontend/tests/devOrigin.test.mjs` y este
  documento, bajo `apps/web` salvo el documento. Todos los archivos de
  Dataset Builder y docs/93 se conservan sin cambios.
- `git diff --check`: PASS; `git status --short`: cuatro modificados y dos
  entradas nuevas (directorio `dev/` y test). Sin staging, commit ni push.

Evidencia local temporal: `/tmp/sicam_auth_debug_ip.html`,
`/tmp/sicam_auth_debug_localhost.html`, `/tmp/sicam_auth_fixed_localhost.html`,
`/tmp/sicam_auth_network_debug.log`, `/tmp/sicam_auth_targeted_backend.log`,
`/tmp/sicam_auth_targeted_frontend.log`, `/tmp/sicam_auth_full_backend.log`,
`/tmp/sicam_auth_full_frontend.log` y `/tmp/sicam_auth_build.log`. Las trazas
resumen nombres/atributos de cookies con valores censurados. La prueba del
navegador confirma el transporte real de cookies, complementando los tests
Django, cuyo cliente no aplica por sí mismo las restricciones SameSite.

AUTH REVIEW = ROOT_CAUSE_FIXED
