# Sprint 1C Remediation 4 - Saliva natsort Dependency

## Fecha de remediacion

2026-07-01 14:41:16 -06:00

## Alcance

Remediacion minima e incremental del bloqueo por `natsort` en el microservicio de saliva.

Directorio validado:

```text
apps/segmentation-saliva
```

No se ejecuto segmentacion real, no se levanto el servicio, no se cargaron modelos pesados y no se modifico codigo fuente.

## Referencia Git

- Rama: `master`
- Commit: `6e1a39e`

## Diagnostico previo

Antes de esta remediacion, `natsort` no estaba instalado en `sicam`:

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -c "import importlib.util; print(importlib.util.find_spec('natsort') is not None)"
```

Resultado:

```text
False
```

El bloqueo observado era:

```text
ModuleNotFoundError: No module named 'natsort'
```

Ubicacion:

```text
segmentacion_core/cellpose/io.py
```

## Cambio aplicado

Se agrego unicamente `natsort` a:

```text
apps/segmentation-saliva/requirements.txt
```

El archivo ahora incluye las dependencias runtime incrementales autorizadas para el `cellpose/` vendorizado:

```text
tqdm
numba
torch
natsort
```

No se agregaron modelos, CUDA, dependencias GPU, `mxnet`, `cellpose` externo, `torchvision` ni `torchaudio`.

## Instalacion en entorno `sicam`

Primer intento dentro del sandbox:

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -m pip install natsort
```

Resultado:

```text
FAIL por bloqueo de red del sandbox
```

Instalacion fuera del sandbox:

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -m pip install natsort
```

Resultado:

```text
Successfully installed natsort-8.4.0
```

## Validaciones repetidas

### Sintaxis Python

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -m compileall -q app segmentacion_core
```

Resultado:

```text
PASS
```

### Version de `natsort`

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -c "import natsort; print(natsort.__version__)"
```

Resultado:

```text
8.4.0
```

Conclusion: PASS.

### Import de `segmentacion_core.seg_membranas`

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -c "import segmentacion_core.seg_membranas; print('seg_membranas import ok')"
```

Resultado:

```text
seg_membranas import ok
```

Conclusion: PASS.

### Imports livianos internos

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -c "import app.utils.poligonos; import segmentacion_core.model.cytoplasm; import segmentacion_core.model.nuclei; import segmentacion_core.model.micronuclei; import segmentacion_core.seg_nucleos; import segmentacion_core.seg_micronucleos; print('imports livianos ok')"
```

Resultado:

```text
imports livianos ok
```

Conclusion: PASS.

## Advertencias

- La validacion sigue siendo liviana: no se ejecuto segmentacion real.
- No se levanto el servicio FastAPI.
- No se cargo explicitamente el modelo `membranas_500_125`.
- `membranas_500_125` debe seguir tratado como artefacto externo ignorado por Git.
- `torch` quedo instalado como CPU-only en una remediacion previa; CUDA no fue instalada ni habilitada.

## Cambios realizados

- Modificado: `apps/segmentation-saliva/requirements.txt`
- Creado: `docs/16_sprint_1c_saliva_microservice_remediation_natsort.md`

## Conclusion

PASS WITH WARNINGS

Las validaciones livianas solicitadas para Sprint 1C pasan despues de agregar `natsort`. El microservicio de saliva puede compilarse e importar `segmentacion_core.seg_membranas` sin ejecutar segmentacion real ni cargar modelos pesados.

## Siguiente paso recomendado

Cerrar Sprint 1C como validacion liviana aprobada con advertencias y continuar con Sprint 1D para el microservicio de sangre, manteniendo la misma regla: no ejecutar segmentacion real ni cargar modelos pesados durante la validacion tecnica.
