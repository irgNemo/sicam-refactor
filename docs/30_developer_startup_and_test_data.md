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
