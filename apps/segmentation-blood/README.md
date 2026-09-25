# BLOOD — Segmentación de sangre

Ambiente **sicam-blood**, Python **3.10.21**, CPU, puerto **8002**.
No tiene selector de estrategias SALIVA. No usar SALIVA ALT para imágenes BLOOD.

## Instalación específica

Crear el ambiente según la [guía WSL](../../docs/developer_environment_setup_wsl.md).
Ejecutar desde el directorio del componente:

```bash
cd ~/repos/sicam-refactor/apps/segmentation-blood
conda activate sicam-blood
python -m pip install torch==2.12.1+cpu torchvision==0.27.1+cpu \
  --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt
python -m pip check
python -c "import cellpose; print(cellpose.__file__)"
```

`-e .` en requirements instala el `pyproject.toml` local, que expone
`segmentacion_core/cellpose` como `cellpose`. No instalar Cellpose PyPI ni
resolver `-e .` desde otra carpeta. `natsort` ya está declarado. Segment Anything
está fijado en requirements al commit oficial
`dca509fe793f601edb92606367a655c15ac00fdf`, no a una rama móvil.

## Modelo

Provisionar `~/.cellpose/models/cpsam` antes de arrancar. También admite
`CELLPOSE_LOCAL_MODELS_PATH` como directorio de cache. Tamaño **1233587898 bytes**,
SHA-256 `e1440429eb384f95afe32bcba6510f90d518eaedc917ede549bed6804004abe2`.
Puede reutilizar el mismo archivo externo que ALT; no se versiona.
Ver provisión y comprobación en la guía WSL. Si falta, el vendorizado puede
intentar descargarlo durante startup.

## Arranque: BLOOD = main:app

```bash
cd ~/repos/sicam-refactor/apps/segmentation-blood
conda activate sicam-blood
python -m uvicorn main:app --host 127.0.0.1 --port 8002
```

**El módulo ASGI es `main.py` en la raíz del microservicio.** Su lifespan
precarga Cellpose/cpsam; esperar `Application startup complete` antes de
verificar:

```bash
curl --fail http://127.0.0.1:8002/docs >/dev/null
curl --fail http://127.0.0.1:8002/openapi.json >/dev/null
```

Endpoint de inferencia: `POST /api/v1/segmentar`, multipart `file`.
No hay endpoint health dedicado. Puede tardar minutos en CPU; no es un SLA.
Django usa `BLOOD_SERVICE_TIMEOUT=240`. Detener con Ctrl+C.

No usar `sicam` como sustituto de este entorno ni añadir variables OpenMP para
ocultar conflictos. Arranque del stack y pruebas:
[manual cotidiano](../../docs/30_developer_startup_and_test_data.md).
