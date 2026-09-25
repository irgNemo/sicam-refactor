# SALIVA CURRENT — Modelo SICAM

Estrategia `CURRENT_CUSTOM_V1`, puerto **8001**, ambiente **sicam**,
Python **3.10.20**, CPU. Django y el selector SALIVA ya están integrados.

## Instalación específica

Crear `sicam` según la [guía WSL](../../docs/developer_environment_setup_wsl.md).
Desde ese ambiente, la secuencia CPU validada del componente es:

```bash
cd ~/repos/sicam-refactor/apps/segmentation-saliva
conda activate sicam
python -m pip install torch==2.12.1+cpu --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt
python -m pip check
```

El runtime usa **`segmentacion_core/cellpose` vendorizado**, no Cellpose PyPI.
No seguir el comentario heredado que sugiere instalar Cellpose externo.
Django comparte `sicam`; sus requirements se instalan desde la guía canónica.
Las dependencias científicas de CURRENT no están completamente fijadas.

Modelo obligatorio externo, ignorado por Git:

```text
apps/segmentation-saliva/segmentacion_core/membranas_500_125
```

Provisionar y comprobar tamaño/hash según la guía WSL. El loader
`app/services/segmentador.py` resuelve esa ruta desde el directorio del servicio.
No se sustituye por cpsam.

## Arranque

```bash
cd ~/repos/sicam-refactor/apps/segmentation-saliva
conda activate sicam
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

Importar la aplicación carga el modelo; esperar startup completo antes de
verificar `http://127.0.0.1:8001/docs` y `/openapi.json`.
Endpoint de inferencia: `POST /segmentar`, multipart `file`. No hay health
separado. Para checks sin inferencia usar sólo los GET anteriores una vez listo.
El servicio ejecuta el pipeline; no es necesario arrancar scripts del core
por separado. Apagar con Ctrl+C.

Arranque conjunto, datos de prueba y errores:
[manual cotidiano](../../docs/30_developer_startup_and_test_data.md).
