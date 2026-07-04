# Sprint 4B - Segmentation Results Read API

## Fecha

2026-07-03 19:23:29 -06:00

## Referencia Git

- Rama: `master`
- Commit: `e8fa575`

## Objetivo

Agregar una API minima de lectura para consultar resultados historicos de segmentacion asociados a una `MuestraSaliva`, sin modificar frontend, microservicios ni politica de persistencia.

## Ruta implementada

```text
GET /api/muestras/{id}/resultados-segmentacion/
```

La ruta se implemento como accion DRF en:

```text
MuestraSalivaViewSet
```

Detalle tecnico:

```python
@action(detail=True, methods=['get'], url_path='resultados-segmentacion')
def resultados_segmentacion(self, request, pk=None):
    ...
```

El router existente ya registra:

```python
router.register(r'muestras', MuestraSalivaViewSet, basename='muestra')
```

Por eso no fue necesario modificar `api/urls.py`.

## Serializer creado

Archivo:

```text
apps/web/Backend/api/serializers.py
```

Serializer:

```text
ResultadoSegmentacionSerializer
```

Campos expuestos:

```text
id
tipo_muestra
estado
respuesta_json
creado_en
actualizado_en
```

El campo `id` se mapea desde:

```text
id_resultado_segmentacion
```

No se modifico el modelo.

## Ordenamiento

Los resultados se devuelven del mas reciente al mas antiguo:

```python
order_by('-creado_en', '-id_resultado_segmentacion')
```

El segundo criterio evita ambiguedad cuando dos registros tienen timestamps muy cercanos.

## Archivos modificados

- `apps/web/Backend/api/serializers.py`
- `apps/web/Backend/api/views.py`
- `apps/web/Backend/api/tests.py`

## Archivos creados

- `docs/22_sprint_4b_segmentation_results_read_api.md`

## Pruebas agregadas

Archivo:

```text
apps/web/Backend/api/tests.py
```

Clase agregada:

```text
MuestraSalivaSegmentationResultsReadTests
```

Cobertura:

- muestra existente sin resultados devuelve lista vacia;
- muestra existente con resultado devuelve lista;
- respuesta incluye `id`, `tipo_muestra`, `estado`, `respuesta_json`, `creado_en` y `actualizado_en`;
- resultados se ordenan del mas reciente al mas antiguo;
- muestra inexistente devuelve `404`.

Las pruebas crean datos locales en base de datos de test. No se llama a microservicios y no se ejecuta segmentacion real.

## Comandos ejecutados

Desde:

```text
apps/web/Backend
```

### Django check

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' manage.py check
```

Resultado:

```text
System check identified no issues (0 silenced).
```

Conclusion: PASS.

### Pytest

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -m pytest
```

Resultado:

```text
30 passed, 2 skipped in 1.40s
```

Conclusion: PASS.

### Django test

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' manage.py test
```

Resultado:

```text
Found 12 test(s).
System check identified no issues (0 silenced).
Ran 12 tests in 0.233s
OK
```

Conclusion: PASS.

## Limitaciones

- Solo consulta resultados asociados a `MuestraSaliva`.
- No generaliza el dominio a sangre.
- No crea `ImagenMuestra`.
- No modifica la politica de persistencia: cada ejecucion exitosa sigue creando un nuevo `ResultadoSegmentacion`.
- No agrega filtros, paginacion ni busqueda.
- No expone un `ViewSet` independiente para `ResultadoSegmentacion`.
- No modifica frontend.

## Resultado general

PASS

La API minima de lectura queda disponible para que el frontend consulte resultados historicos persistidos de segmentacion por muestra.

## Pendientes para frontend

- Crear funcion en `segmentationService.js` para consumir `GET /api/muestras/{id}/resultados-segmentacion/`.
- Cargar resultados historicos al seleccionar una muestra.
- Mostrar ultimo resultado persistido o historial compacto.
- Mantener el frontend consumiendo solo Django REST.
- No renderizar poligonos o mascaras hasta un sprint dedicado.
