# Sprint 1C Remediation 2 - Saliva numba Dependency

## Fecha de remediacion

2026-06-26 21:24:53 -06:00

## Alcance

Remediacion minima e incremental del bloqueo por `numba` detectado despues de resolver `tqdm` en el microservicio de saliva.

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

Antes de esta remediacion, `numba` no estaba instalado en `sicam`:

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -c "import importlib.util; print(importlib.util.find_spec('numba') is not None)"
```

Resultado:

```text
False
```

## Cambio aplicado

Se agrego unicamente `numba` a:

```text
apps/segmentation-saliva/requirements.txt
```

El archivo ahora incluye las remediaciones incrementales autorizadas:

```text
tqdm
numba
```

No se agregaron `torch`, `mxnet`, `cellpose`, dependencias GPU, modelos ni artefactos pesados.

## Instalacion en entorno `sicam`

`conda` no esta disponible directamente en `PATH`, por lo que se uso su ruta explicita:

```powershell
& 'C:\Users\israe\miniconda3\Scripts\conda.exe' install -n sicam -c conda-forge numba -y
```

Resultado:

```text
numba 0.65.1 instalado en sicam
```

Conda resolvio dependencias compiladas de `numba`, incluyendo `llvmlite` y bibliotecas numericas. No se instalaron modelos, pesos, `torch`, `mxnet` ni dependencias GPU.

## Validaciones repetidas

### Sintaxis Python

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -m compileall -q app segmentacion_core
```

Resultado:

```text
PASS
```

### Version de `numba`

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -c "import numba; print(numba.__version__)"
```

Resultado:

```text
0.65.1
```

Conclusion: PASS.

### Import de `segmentacion_core.seg_membranas`

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -c "import segmentacion_core.seg_membranas; print('seg_membranas import ok')"
```

Resultado:

```text
NameError: name 'torch' is not defined
```

Ubicacion observada:

```text
segmentacion_core/cellpose/dynamics.py
```

Conclusion: FAIL.

Clasificacion: dependencia pesada o especial no instalada.

`torch` no se instalo porque esta fuera del alcance autorizado para esta remediacion.

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

El bloqueo por `numba` quedo resuelto, pero `segmentacion_core.seg_membranas` sigue sin importar correctamente porque el `cellpose/` vendorizado depende de `torch`.

Verificacion adicional:

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -c "import importlib.util; print(importlib.util.find_spec('torch') is not None)"
```

Resultado:

```text
False
```

`torch` debe tratarse como dependencia pesada o especial. No debe instalarse sin una decision explicita sobre version, canal de instalacion, CPU/GPU y compatibilidad con el entorno `sicam`.

## Cambios realizados

- Modificado: `apps/segmentation-saliva/requirements.txt`
- Creado: `docs/16_sprint_1c_saliva_microservice_remediation_numba.md`

## Conclusion

FAIL

Sprint 1C sigue en FAIL. La remediacion resolvio `numba`, pero el import de `segmentacion_core.seg_membranas` ahora queda bloqueado por `torch`.

## Siguiente paso recomendado

Abrir una decision tecnica separada para `torch`:

- Definir si se instalara build CPU o GPU.
- Definir canal recomendado para Windows y Python `3.10.20`.
- Confirmar compatibilidad con el `cellpose/` vendorizado.
- Evitar descargar modelos o ejecutar segmentacion durante la validacion.
