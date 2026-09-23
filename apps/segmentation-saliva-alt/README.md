# SALIVA ALT — Sprint 18A

Servicio independiente: `ALT_CPSAM_MORPHOLOGICAL_V1`, algoritmo `1.0`,
Cellpose **4.0.8**, modelo **cpsam**, CPU, puerto **8003**.
No está conectado a Django ni al frontend. SALIVA actual continúa en 8001.

## Instalación y ejecución

Desde WSL, en el repositorio de trabajo:

```bash
conda create -n sicam-saliva-alt python=3.10.20 pip -y
conda activate sicam-saliva-alt
cd ~/repos/sicam-refactor/apps/segmentation-saliva-alt
python -m pip install -r requirements.txt
python -m pip check
OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 \
  python -m uvicorn app.main:app --host 127.0.0.1 --port 8003
```

Usar exclusivamente `sicam-saliva-alt`; no instalar estas dependencias en
`sicam` ni `sicam-blood`. Se fijan versiones CPU, sin extras GUI.
`constraints.txt` fija también dependencias transitivas; los paquetes de
pruebas sólo se instalan al usar `requirements-test.txt`.
Las variables de threads limitan recursos, no parámetros científicos.

Provisionar antes `~/.cellpose/models/cpsam`, o el directorio definido por
`CELLPOSE_LOCAL_MODELS_PATH`. El servicio exige **1233587898 bytes** y SHA-256
`e1440429eb384f95afe32bcba6510f90d518eaedc917ede549bed6804004abe2`.
Reutiliza el artefacto validado de BLOOD sin copiarlo ni modificarlo. Si falta,
no coincide o Cellpose no es 4.0.8, el startup falla antes de cargar el modelo.
No descarga pesos automáticamente ni utiliza fallback.

```bash
curl --fail http://127.0.0.1:8003/docs
curl --fail http://127.0.0.1:8003/openapi.json
curl --fail -F 'file=@/tmp/sicam18a-synthetic.png;type=image/png' \
  http://127.0.0.1:8003/segmentar
```

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

Los tests usan imágenes sintéticas y un modelo simulado, sin cargar cpsam.
La morfología conserva la eliminación de anucleadas, labels compartidos,
área nuclear combinada y resize temporal a 512×512 (incluye deformación de
rectángulos). No se ha comparado calidad ni optimizado thresholds.

Auditoría, limitaciones y evidencia:
[Sprint 18A](../../docs/58_sprint_18a_alt_saliva_segmentation_service.md).
