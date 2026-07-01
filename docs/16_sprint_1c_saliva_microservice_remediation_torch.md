# Sprint 1C Remediation 3 - Saliva torch CPU Dependency

## Fecha de remediacion

2026-06-26 21:37:28 -06:00

## Alcance

Remediacion controlada del bloqueo por `torch` en el microservicio de saliva usando PyTorch CPU-only para validacion local de imports.

Directorio validado:

```text
apps/segmentation-saliva
```

No se ejecuto segmentacion real, no se levanto el servicio, no se cargaron modelos pesados y no se modifico codigo fuente.

## Referencia Git

- Rama: `master`
- Commit: `6e1a39e`

## Entorno Python verificado

```text
C:\Users\israe\miniconda3\envs\sicam\python.exe
Python 3.10.20
```

## Diagnostico previo

Antes de esta remediacion, `torch` no estaba instalado en `sicam`:

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -c "import importlib.util; print(importlib.util.find_spec('torch') is not None)"
```

Resultado:

```text
False
```

El bloqueo observado era:

```text
NameError: name 'torch' is not defined
```

Ubicacion:

```text
segmentacion_core/cellpose/dynamics.py
```

## Cambio aplicado

Se agrego `torch` a:

```text
apps/segmentation-saliva/requirements.txt
```

Tambien se agrego una nota indicando que `torch` es una dependencia runtime especial del `cellpose/` vendorizado y que, para validacion local CPU-only, debe instalarse con el indice oficial CPU de PyTorch.

No se agregaron `torchvision`, `torchaudio`, CUDA, `mxnet`, `cellpose` externo, modelos ni dependencias GPU.

## Instalacion en entorno `sicam`

Comando ejecutado:

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -m pip install torch --index-url https://download.pytorch.org/whl/cpu
```

Resultado:

```text
Successfully installed torch-2.12.1+cpu
```

Dependencias instaladas por `pip` para PyTorch CPU-only:

```text
MarkupSafe
filelock
fsspec
jinja2
mpmath
setuptools
sympy
torch
```

Advertencia: `pip` ajusto `setuptools` dentro del entorno `sicam` para satisfacer la version requerida por `torch`.

## Validaciones repetidas

### Sintaxis Python

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -m compileall -q app segmentacion_core
```

Resultado:

```text
PASS
```

### Version de `torch` y CUDA

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -c "import torch; print(torch.__version__); print(torch.cuda.is_available())"
```

Resultado:

```text
2.12.1+cpu
False
```

Conclusion: PASS. La instalacion es CPU-only y CUDA no esta disponible.

### Import de `segmentacion_core.seg_membranas`

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -c "import segmentacion_core.seg_membranas; print('seg_membranas import ok')"
```

Resultado:

```text
ModuleNotFoundError: No module named 'natsort'
```

Ubicacion observada:

```text
segmentacion_core/cellpose/io.py
```

Conclusion: FAIL.

Clasificacion: dependencia liviana faltante.

`natsort` no se instalo porque esta remediacion autorizaba unicamente PyTorch CPU-only.

### Imports livianos internos

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -c "import app.utils.poligonos; import segmentacion_core.model.cytoplasm; import segmentacion_core.model.nuclei; import segmentacion_core.model.micronuclei; import segmentacion_core.seg_nucleos; import segmentacion_core.seg_micronucleos; print('imports livianos ok')"
```

Resultado:

```text
imports livianos ok
```

Conclusion: PASS.

## Nuevo bloqueo

El bloqueo por `torch` quedo resuelto con instalacion CPU-only, pero `segmentacion_core.seg_membranas` sigue sin importar por falta de `natsort`.

Verificacion adicional:

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -c "import importlib.util; print(importlib.util.find_spec('natsort') is not None)"
```

Resultado:

```text
False
```

`natsort` se clasifica como dependencia liviana, pero requiere una remediacion separada y aprobada antes de instalarse o agregarse a `requirements.txt`.

## Cambios realizados

- Modificado: `apps/segmentation-saliva/requirements.txt`
- Creado: `docs/16_sprint_1c_saliva_microservice_remediation_torch.md`

## Conclusion

FAIL

Sprint 1C sigue en FAIL. La remediacion resolvio el bloqueo por `torch` usando PyTorch CPU-only, pero el import de `segmentacion_core.seg_membranas` ahora queda bloqueado por `natsort`.

## Siguiente paso recomendado

Abrir una remediacion incremental separada para `natsort`:

- Agregar unicamente `natsort` a `apps/segmentation-saliva/requirements.txt`.
- Instalarlo en `sicam`.
- Repetir las mismas validaciones livianas.
- No ejecutar segmentacion, no levantar el servicio y no cargar modelos.
