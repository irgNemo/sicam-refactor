# SALIVA ALT — Cellpose-SAM alternativo

Servicio independiente: `ALT_CPSAM_MORPHOLOGICAL_V1`, algoritmo `1.0`,
Cellpose **4.0.8**, modelo **cpsam**, CPU, puerto **8003**.
Django enruta esta estrategia desde 18B y el selector SALIVA la ofrece desde
18C. SALIVA CURRENT continúa en 8001 como default. ALT no está validado para
BLOOD ni se ofrece en ese flujo.

Instalación general: [guía WSL](../../docs/developer_environment_setup_wsl.md).
Operación conjunta: [manual cotidiano](../../docs/30_developer_startup_and_test_data.md).

## Instalación y ejecución

Desde WSL, en el repositorio de trabajo:

```bash
conda create -n sicam-saliva-alt python=3.10.20 pip -y
conda activate sicam-saliva-alt
cd ~/repos/sicam-refactor/apps/segmentation-saliva-alt
python -m pip install -r requirements.txt
python -m pip check
python -m uvicorn app.main:app --host 127.0.0.1 --port 8003
```

Usar exclusivamente `sicam-saliva-alt`; no instalar estas dependencias en
`sicam` ni `sicam-blood`. Se fijan versiones CPU, sin extras GUI.
`requirements.txt` incluye `-c constraints.txt`: el comando anterior aplica
los constraints del repositorio, incluidas dependencias transitivas. Los paquetes de
pruebas sólo se instalan al usar `requirements-test.txt`.
Opcionalmente, antes de arrancar, reproducir el límite de threads de los smokes:

```bash
export OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4
```

Limita recursos, no parámetros científicos.

Provisionar antes `~/.cellpose/models/cpsam`, o el directorio definido por
`CELLPOSE_LOCAL_MODELS_PATH`. El servicio exige **1233587898 bytes** y SHA-256
`e1440429eb384f95afe32bcba6510f90d518eaedc917ede549bed6804004abe2`.
Reutiliza el artefacto validado de BLOOD sin copiarlo ni modificarlo. Si falta,
no coincide o Cellpose no es 4.0.8, el startup falla antes de cargar el modelo.
No descarga pesos automáticamente ni utiliza fallback.

```bash
curl --fail http://127.0.0.1:8003/docs
curl --fail http://127.0.0.1:8003/openapi.json
```

Esperar startup completo: el lifespan verifica y precarga el modelo antes de
servir esos GET. No hay health dedicado. Para inferencia usar `POST /segmentar`
con una imagen SALIVA autorizada; `/tmp/sicam18a-synthetic.png` era un artefacto
temporal del sprint, no una fixture disponible al clonar. Una imagen de
4928×4928 tardó aproximadamente 170–180 s en CPU; es una referencia, no SLA.
Apagar con Ctrl+C.

`file` es el campo multipart existente en SICAM. Respuesta:

```json
{"objetos": [{"id": 7, "tipo": "nucleo", "puntos": [[30, 10], [49, 10], [49, 19], [30, 19]]}]}
```

Tipos: `membrana`, `nucleo`, `micronucleo`; coordenadas `[x,y]` en píxeles
de la imagen original. Varios objetos pueden compartir el mismo `id` crudo.
Los metadatos de estrategia aparecen en startup y documentación, sin añadir
campos al contrato. Una imagen no decodificable devuelve 400; falta de `file`,
422; fallos internos, 500. Una sola inferencia CPU a la vez por proceso;
usar un worker para no duplicar el modelo en memoria.

## Pruebas sin modelo

```bash
python -m pip install -r requirements-test.txt
python -m pytest -q
```

`requirements-test.txt` incluye el requirements de runtime y, por tanto, sus
constraints, además de pytest/httpx. Es opcional para ejecutar el servicio.

Los tests usan imágenes sintéticas y un modelo simulado, sin cargar cpsam.
La morfología conserva la eliminación de anucleadas, labels compartidos,
área nuclear combinada y resize temporal a 512×512 (incluye deformación de
rectángulos). No se ha comparado calidad ni optimizado thresholds.

Auditoría, limitaciones y evidencia:
[Sprint 18A](../../docs/58_sprint_18a_alt_saliva_segmentation_service.md).
