# CODEX Handoff — SICAM

## 1. Propósito

Este documento permite que una sesión nueva de Codex continúe SICAM desde el
estado real del repositorio al 11 de septiembre de 2026, sin depender del
historial del chat. Las marcas usadas son:

- **HECHO VERIFICADO**: confirmado en código, Git, archivos o comandos.
- **DECISIÓN TOMADA**: criterio ya adoptado y documentado.
- **PENDIENTE**: trabajo todavía no implementado.
- **HISTÓRICO**: antecedente de la estación Windows anterior; no debe usarse
  como configuración de WSL salvo que una verificación explícita lo confirme.

Este cambio es sólo documental y no modifica lógica funcional.

## 2. Estado Git exacto

**HECHO VERIFICADO**

```text
Repositorio observado: /home/israel/repos/sicam-refactor
Rama: master
HEAD: f5df1934d274769ad7ff848f0dbc9c4a711f71c7
Último commit: f5df193 Add the developer enviroment setup md file
Tracking: origin/master
Diferencia: master está ahead 1
Commits sólo en local: f5df193
Commits sólo en remoto: ninguno
Remoto verificado con: git fetch origin, 11 de septiembre de 2026
Working tree antes del cierre documental: sólo este handoff sin seguimiento
```

Últimos commits relevantes:

```text
f5df193 Add the developer enviroment setup md file
7618954 Document reproducible WSL development environment
4045393 Add saliva morphometric characterization backend
410060d Define saliva morphometric characterization contract
baae5d9 Document morphological characterization legacy audit
191d0d2 Analisys obout implementation of characterization module
628ca83 Harden characterization state and navigation
f2b70e1 Update SICAM development startup guide
828c65f Add characterization frontend workflow
b3a29ba Add effective segmentation characterization core
2bd9f14 Add end-to-end blood segmentation workflow
a611cf2 Add end-to-end blood segmentation support
df40f0a Add blood sample persistence support
56d69e9 Generalize segmentation domain for multiple sample types
dccd962 Extract segmentation revision and effective result state
7eae175 Extract segmentation overlay and editor state
224a029 Refactor segmentation frontend components and preserve styling
8113a40 Use validated revisions as effective segmentation results
ba8a2a5 Add expert segmentation revision validation
2b13126 Complete expert segmentation contour editing
```

**ESTADO DE PUBLICACIÓN:** `origin/master` está en `7618954`, confirmado después
de ejecutar `git fetch origin`. El commit local `f5df193` aún no está publicado.
Este handoff se incorpora al control de versiones mediante el commit documental
de cierre de migración. Mientras ese commit y `f5df193` no lleguen al remoto, un
clon nuevo no contiene el baseline WSL completo.

## 3. Objetivo general

SICAM (Sistema de Captura y Análisis de Micronúcleos) integra pacientes, casos,
análisis e imágenes con segmentación asistida, revisión experta y
caracterización cuantitativa. El refactor mantiene un monorepo donde Vue ofrece
la interfaz, Django conserva y orquesta el dominio, dos servicios FastAPI
segmentan SALIVA y SANGRE, y la caracterización consume el resultado efectivo
persistido sin volver a ejecutar Cellpose.

## 4. Arquitectura actual

**HECHO VERIFICADO**

```text
Vue 3 + Vite :5173
        |
        v
Django 5 + DRF :8000
   |       |       |
   |       |       +--> SQLite local / PostgreSQL configurable
   |       +----------> BLOOD FastAPI :8002  POST /api/v1/segmentar
   +------------------> SALIVA FastAPI :8001 POST /segmentar
```

La caracterización vive dentro de Django; no es otro microservicio. Django lee
`apps/web/Backend/.env`; Vue usa
`apps/web/Frontend/src/services/apiClient.js` y
`VITE_API_BASE_URL`. Las URLs de segmentación están en
`settings.SEGMENTATION_SERVICES`.

Flujo de dominio:

```text
Paciente -> Caso -> AnalisisPred -> MuestraSaliva/MuestraSangre
-> ResultadoSegmentacion -> RevisionSegmentacion
-> ResultadoCaracterizacion
```

## 5. Estructura relevante

```text
apps/
├── web/
│   ├── Backend/
│   │   ├── api/{migrations,services,models.py,serializers.py,tests.py,views.py}
│   │   ├── config/
│   │   ├── manage.py
│   │   ├── requirements.txt
│   │   └── .env.example
│   └── Frontend/
│       ├── src/{components,composables,domain,services,views}
│       ├── package.json
│       ├── package-lock.json
│       └── .env.example
├── segmentation-saliva/{app,segmentacion_core,requirements.txt}
└── segmentation-blood/{app,segmentacion_core,main.py,requirements.txt,pyproject.toml}
docs/
```

Caracterización:

```text
apps/web/Backend/api/services/characterization/service.py
apps/web/Backend/api/services/characterization/saliva.py
apps/web/Backend/api/services/characterization/geometry.py
apps/web/Backend/api/services/characterization/intensity.py
apps/web/Backend/api/services/characterization/types.py
apps/web/Frontend/src/views/CaracterizacionView.vue
apps/web/Frontend/src/components/characterization/CharacterizationResultPanel.vue
apps/web/Frontend/src/services/characterizationService.js
```

## 6. Cambios realizados

**HECHO VERIFICADO**

- Se consolidaron tres repositorios heredados en el monorepo y se limpiaron
  artefactos locales.
- Django usa variables de entorno y clientes HTTP por tipo de muestra.
- Se implementaron endpoints de segmentación, persistencia, normalización e
  históricos.
- Vue integra selección Paciente/Caso/tipo/muestra/resultado.
- Se implementaron overlay SVG, zoom/pan, responsive, revisión experta,
  máscaras, edición de vértices, BORRADOR y validación.
- El resultado efectivo y el editor se extrajeron a servicios/composables.
- Se generalizó el flujo para SALIVA y SANGRE.
- La UI conserva contexto mínimo en `sessionStorage`:
  `sicam.uiContext.v1`.
- Caracterización confirmada: 17A auditoría legacy; 17B core; 17C frontend
  inicial; 17D hardening; 17E auditoría morfológica; 17F contrato SALIVA v2;
  17G backend SALIVA v2.

Sprint 17G está en código:

- `geometry.py`: área, perímetro, centroide, circularidad, punto/polígono y
  auto-intersección.
- `intensity.py`: imagen gris, dimensiones e intensidad media por máscara.
- `saliva.py`: medición, asociaciones, celdas, no asociados, ambiguos,
  warnings y resumen.
- SALIVA usa `algorithm_version/schema_version 2.0`.
- BLOOD permanece `counts-only 1.0`.
- Las pruebas están en `api/tests.py`; no hubo migraciones ni endpoints nuevos.

Setup WSL:

- `7618954` creó la guía, enlazó `docs/30...` y agregó `natsort` a BLOOD.
- `f5df193` registró la instalación y smokes reales en Ubuntu WSL2.
- El gap previo de `natsort` está **resuelto**.
- Segment Anything quedó fijado a
  `dca509fe793f601edb92606367a655c15ac00fdf`.
- La migración Windows -> WSL quedó validada el 11 de septiembre de 2026.
- El modelo BLOOD `cpsam` de ambas estaciones produjo exactamente el mismo
  tamaño y SHA-256.

## 7. Decisiones técnicas

**DECISIONES TOMADAS**

- Resultado efectivo: última `VALIDADA > AUTOMATICO`; `BORRADOR` se excluye.
  Así una edición incompleta no altera resultados vigentes.
- Caracterización: snapshot idempotente por resultado, fuente, revisión y
  versión. Backend decide `vigente`.
- SALIVA actual: contrato 2.0 morfométrico. SALIVA 1.0 histórica conserva
  `counts/indices`. BLOOD sigue 1.0 counts-only por falta de regla científica
  versionada.
- Los cálculos científicos viven en backend. Frontend sólo presenta; en 17H
  únicamente puede derivar `genotoxicity_index * 100` como otra representación
  del mismo ratio.
- Entornos separados: `sicam` para Django+SALIVA y `sicam-blood` sólo para
  BLOOD, evitando el conflicto nativo/OpenMP Torch/scikit-image.
- El repo debe vivir en `/home/<usuario>/...`, evitando `/mnt/c/...` por I/O
  y file watching.

## 8. Entornos y dependencias

**HECHO VERIFICADO EN ESTA MÁQUINA**

| Componente | Runtime |
|---|---|
| Ubuntu WSL2 | 26.04 LTS, x86_64 |
| Miniconda | 26.7.1 documentado |
| `sicam` | Python 3.10.20 |
| `sicam-blood` | Python 3.10.21 |
| Node/npm | 24.17.0 / 11.13.0 mediante nvm 0.40.7 |
| Django | 5.0.1 |
| SALIVA | FastAPI 0.141.1, Uvicorn 0.52.4 |
| Frontend | Vue 3.5.x, Vite 7.3.0 |
| BLOOD | Torch 2.12.1+cpu, torchvision 0.27.1+cpu |

Rutas observadas, que deben resolverse otra vez si cambia el usuario:

```text
/home/israel/miniconda3
/home/israel/miniconda3/envs/sicam
/home/israel/miniconda3/envs/sicam-blood
/home/israel/.nvm
/home/israel/repos/sicam-refactor
```

Django tiene requirements pinneados. SALIVA y gran parte de BLOOD no están
pinneados; la instalación resolvió NumPy 2.2.6, OpenCV 5.0.0.93,
scikit-image 0.25.2, scikit-learn 1.7.2, SciPy 1.15.3, Numba 0.67.0 y
natsort 8.4.0. BLOOD expone Cellpose vendorizado mediante `-e .`; no instalar
Cellpose externo. Frontend usa Vue, Axios, Vite y ESLint con lockfile v3.

## 9. Modelos externos

Los modelos están ignorados por Git y no llegan con un clon.

### SALIVA

**VERIFICADO EL 11-09-2026**

```text
Ruta relativa:
apps/segmentation-saliva/segmentacion_core/membranas_500_125
Tamaño: 26551763 bytes
SHA-256: fa6ac42f593ac7b86d665e48e69161f427fcb11ec9dd5c02fa4a2722245d0f2c
Fuente: copia confiable de la estación SICAM anterior
```

Debe copiarse a la misma ruta relativa del nuevo clon y verificarse.

### BLOOD

**VERIFICADO EN WSL Y CONTRASTADO CON WINDOWS EL 11-09-2026**

```text
Ruta por defecto: ~/.cellpose/models/cpsam
Tamaño: 1233587898 bytes
SHA-256: e1440429eb384f95afe32bcba6510f90d518eaedc917ede549bed6804004abe2
Fuente: https://huggingface.co/mouseland/cellpose-sam/resolve/main/cpsam
```

La computadora Windows anterior y esta instalación WSL produjeron exactamente
el mismo tamaño y SHA-256 para `cpsam`. La transferencia del modelo queda
validada.

`CELLPOSE_LOCAL_MODELS_PATH` permite otra carpeta. Provisionarlo antes evita
la descarga implícita de 1.23 GB.

## 10. Estado de componentes

### Django

**HECHO VERIFICADO**

- Migraciones locales hasta `api.0006`; SQLite es default y PostgreSQL es
  configurable.
- `python manage.py check` al preparar este handoff:
  `System check identified no issues (0 silenced)`.
- Existen datos demo sintéticos locales. Base y `media/` no son código.
- No existe `/api/health/`, aunque documentación antigua lo menciona.

### SALIVA FastAPI

- Expone `POST /segmentar`.
- Modelo presente; startup real y `/docs`/`openapi.json` dieron HTTP 200.
- No hay health dedicado. Importar `app.main` carga el modelo.
- La caracterización SALIVA ocurre en Django, no aquí.
- El comentario de requirements que sugiere Cellpose PyPI es obsoleto.

### BLOOD FastAPI

- Expone `POST /api/v1/segmentar`.
- El lifespan precarga Cellpose-SAM; modelo presente y verificado.
- Startup HTTP 200; imports Torch/scikit-image pasaron en ambos órdenes.
- Timeout Django default: 240 s.
- Caracterización sigue membranas/micronúcleos counts-only 1.0.

## 11. Comandos operativos

Guía canónica: `docs/developer_environment_setup_wsl.md`.

```bash
# Inicialización
source ~/miniconda3/etc/profile.d/conda.sh
export NVM_DIR="$HOME/.nvm"
source "$NVM_DIR/nvm.sh"

# SALIVA :8001
cd apps/segmentation-saliva
conda activate sicam
python -m pip check
python -m compileall -q app segmentacion_core
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001

# BLOOD :8002
cd apps/segmentation-blood
conda activate sicam-blood
python -m pip check
python -m compileall -q app segmentacion_core main.py
python -c "import torch; from skimage.segmentation import find_boundaries; print('PASS')"
python -c "from skimage.segmentation import find_boundaries; import torch; print('PASS')"
python -m uvicorn main:app --host 127.0.0.1 --port 8002

# Django :8000
cd apps/web/Backend
conda activate sicam
python manage.py migrate
python manage.py check
python manage.py showmigrations
python -m pytest -q
python manage.py test
python manage.py runserver 127.0.0.1:8000

# Vue :5173
cd apps/web/Frontend
nvm use 24.17.0
npm ci
npm run build
npm run dev -- --host 127.0.0.1 --port 5173
```

Verificar `/docs` de ambos FastAPI, `http://127.0.0.1:8000/api/` y Vite.
No lanzar varios `conda run` en paralelo desde una automatización.

## 12. Pruebas y resultados

**Sprint 17G registrado**

```text
CharacterizationCoreTests: 31 passed
manage.py check: 0 issues
makemigrations --check: No changes detected
pytest completo: 172 passed, 2 skipped in 4.03s
Django test runner: 147 tests, OK
```

Dos tests omitidos requieren servicios e imagen `test_image.jpg`.

**Smokes registrados**

- SALIVA AUTOMATICO v2 y VALIDADA v2 sobre datos locales: source, versión,
  asociaciones, morfometría, intensidad y warnings confirmados.
- BLOOD: resultado 21, caracterización 15, versión 1.0, AUTOMATICO,
  `membrana=350`, `micronucleo=1`, `indices={}`.
- Clasificación 17G: `PASS WITH WARNINGS`; warnings esperados por calidad de
  geometría/asociación, sin anomalías matemáticas.
- El primer smoke DRF falló por host `testserver`; pasó con
  `HTTP_HOST=127.0.0.1`, sin cambiar código.
- Setup WSL: `pip check`, migraciones, cuatro startups, HTTP 200, build Vite,
  integración Django-servicios, CORS y hashes de modelos: PASS.

## 13. Problemas resueltos, pendientes y riesgos

| Hallazgo | Estado |
|---|---|
| BLOOD importaba `natsort` sin declararlo | Resuelto en `7618954` |
| Conflicto Torch/scikit-image | Resuelto con `sicam-blood` aislado |
| Segment Anything apuntaba a rama móvil | Resuelto con commit fijo |
| Modelos externos sin trazabilidad | Resuelto con rutas/tamaños/hashes |
| Migración Windows -> WSL | Validada; entorno WSL y modelos contrastados |
| README describe integraciones terminadas como pendientes | Pendiente documental |
| Documento menciona `/api/health/` inexistente | Pendiente documental |
| Dependencias científicas abiertas | Deuda: crear estrategia de lock/pins |
| `npm ci`: 18 vulnerabilidades (2 low, 4 moderate, 12 high) | Pendiente; no se ejecutó audit fix |
| BLOOD morfométrico | Pendiente de decisión científica |
| Backfill de caracterizaciones históricas | No implementado |
| Intensidad por máscara | Posible optimización futura |
| Sprint 17H | Pendiente inmediato |

Riesgos: no mezclar entornos; los startups usan modelos pesados; un clon omite
modelos, `.env`, SQLite, `media/` y `node_modules`; no versionar secretos,
datos clínicos ni artefactos locales.

## 14. Documentos que deben leerse

1. `docs/CODEX_HANDOFF_SICAM.md`.
2. `docs/developer_environment_setup_wsl.md`.
3. `docs/30_developer_startup_and_test_data.md`.
4. `docs/13_architecture_baseline.md`.
5. `docs/42_sprint_13f_effective_segmentation.md`.
6. `docs/49_sprint_16d_multisample_hardening.md`.
7. `docs/50_sprint_17a_characterization_legacy_audit.md`.
8. `docs/51_sprint_17b_characterization_core.md`.
9. `docs/52_sprint_17c_characterization_frontend.md`.
10. `docs/53_sprint_17d_characterization_hardening.md`.
11. `docs/54_sprint_17e_morphological_characterization_audit.md`.
12. `docs/55_sprint_17f_saliva_morphometric_contract.md`.
13. `docs/56_sprint_17g_saliva_morphometric_backend.md`.

Los docs 01–12 y README son históricos; confirmar sus pendientes contra código.

## 15. Rutas Windows históricas

**HISTÓRICO; NO USAR COMO CONFIGURACIÓN NUEVA**

```text
C:\Users\israe\miniconda3\envs\sicam\python.exe
%USERPROFILE%\.cellpose\models\cpsam
C:\Users\israe\.codex\attachments\...
```

Los attachments no pertenecen al repo. En WSL resolver de nuevo:

```text
/home/<usuario>/repos/sicam-refactor
/home/<usuario>/miniconda3/envs/sicam
/home/<usuario>/miniconda3/envs/sicam-blood
/home/<usuario>/.cellpose/models/cpsam
```

No hardcodear `israel` en archivos versionados.

## 16. Último punto exacto

Antes del commit documental de cierre se confirmó `master`, HEAD `f5df193` y
`origin/master` en `7618954` después de `git fetch origin`. La rama local está
ahead 1, sin commits sólo en remoto ni divergencia.

La migración Windows -> WSL queda formalmente validada: los entornos y smokes
WSL están documentados, y el modelo BLOOD de 1233587898 bytes coincide entre
ambas computadoras con SHA-256
`e1440429eb384f95afe32bcba6510f90d518eaedc917ede549bed6804004abe2`.

La auditoría previa a 17H concluyó:

- `CaracterizacionView.vue` preserva selección, resultado histórico y guards.
- `App.vue` preserva `sicam.uiContext.v1` y dirty guards.
- `characterizationService.js` es sólo transporte.
- Sólo existe `CharacterizationResultPanel.vue` en componentes de
  caracterización.
- El panel sigue pre-17H: no presenta resumen v2, asociación, tabla por célula,
  detalles, no asociados/ambiguos ni overlay read-only.
- Backend sí tiene contrato científico suficiente.
- Los polígonos deben leerse del endpoint existente
  `GET /api/resultados-segmentacion/{id}/efectivo/`; no se duplican en la
  caracterización.
- Ese endpoint ya aplica `VALIDADA > AUTOMATICO` e ignora BORRADOR.
- No existe `docs/57_sprint_17h_saliva_morphometric_frontend.md`.

Se preparó conceptualmente una carga read-only del resultado efectivo con guard
propio, pero la edición falló/abortó antes de escribir. Después,
`git status --short` y `git diff --stat` seguían vacíos. **Sprint 17H no está
implementado.**

## 17. Próximo paso recomendado

Implementar Sprint 17H sólo en frontend y crear
`docs/57_sprint_17h_saliva_morphometric_frontend.md`.

Criterios mínimos:

1. Detectar SALIVA v2 sólo con `sample_type == SALIVA` y
   `schema_version == "2.0"`.
2. Conservar SALIVA 1.0 mediante `counts/indices` y BLOOD 1.0 counts-only.
3. Presentar `summary`, `association_quality`, warnings agrupados,
   `cells`, `unassociated` y `ambiguous` directamente.
4. Una fila por `resultado_json.cells`; detalle de membrana, núcleos y MN.
5. Null se muestra `—` o `No disponible`, nunca 0.
6. Imagen original + objetos efectivos + SVG read-only.
7. No recalcular geometría, intensidad, asociaciones o índices; sólo porcentaje
   equivalente de genotoxicidad.
8. Preservar current/stale, acción explícita, selección histórica, request
   guards, session storage, dirty guards y responsive.
9. No tocar backend, microservicios, modelos, migraciones o requirements; no
   agregar npm; no implementar CSV/PDF.
10. Validar build, Django check, `git diff --check`, búsquedas estáticas y
    smoke manual 1440/1280/1024.
11. No hacer commit ni push sin autorización.

```text
BACKEND SALIVA v2 = READY
FRONTEND SALIVA v2 = NOT IMPLEMENTED
NEXT SPRINT = 17H
REPOSITORY BASE FOR 17H = commit documental de cierre posterior a f5df193
```


## 18. Estado del cierre de migración

```text
WINDOWS_TO_WSL_MIGRATION = VALIDATED
BLOOD_MODEL_CROSS_HOST_CHECK = PASS
SPRINT_17H = NOT STARTED
NEXT ACTION = create documentation-only migration closure commit
```

El baseline de código sigue en `f5df193`; el siguiente commit sólo debe contener
este handoff y las correcciones documentales del SHA-256 de BLOOD. No se
modificó ningún archivo funcional ni se hizo push.
