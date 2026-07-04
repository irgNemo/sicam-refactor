# Sprint 5 - Segmentation Result Normalization

## Fecha

2026-07-03 20:07:58 -06:00

## Referencia Git

- Rama: `master`
- Commit: `cd3114e`

## Objetivo

Agregar una capa de normalizacion en Django para conservar la respuesta cruda del microservicio y, ademas, generar una representacion interna estable para futuros usos del frontend, visualizacion de resultados e integracion gradual de sangre.

## Campo agregado

Modelo:

```text
ResultadoSegmentacion
```

Archivo:

```text
apps/web/Backend/api/models.py
```

Campo:

```python
resultado_normalizado = models.JSONField(blank=True, null=True)
```

No se elimino ni modifico `respuesta_json`.

## Migracion creada

Archivo:

```text
apps/web/Backend/api/migrations/0003_resultadosegmentacion_resultado_normalizado.py
```

Operacion:

```text
AddField resultado_normalizado to ResultadoSegmentacion
```

El campo permite `blank=True` y `null=True` para mantener compatibilidad con resultados ya existentes.

## Normalizador implementado

Archivo:

```text
apps/web/Backend/api/services/segmentation/normalizers.py
```

Funcion principal:

```python
normalize_segmentation_result(raw_result, sample_type="SALIVA")
```

En este sprint solo se soporta:

```text
SALIVA
```

## Estructura normalizada

Ejemplo:

```json
{
  "version": "1.0",
  "sample_type": "SALIVA",
  "objects": [
    {
      "id": 1,
      "label": "membrana",
      "geometry": {
        "type": "polygon",
        "points": [[10, 20]]
      },
      "source": {
        "raw_type": "membrana"
      }
    }
  ],
  "summary": {
    "total_objects": 1,
    "counts_by_label": {
      "membrana": 1
    }
  }
}
```

## Politica de tolerancia

- Si `raw_result` no es `dict`, se lanza `ValueError`.
- Si falta `objetos`, se normaliza como lista vacia.
- Si `objetos` no es lista, se lanza `ValueError`.
- Si un objeto no tiene `tipo`, se usa `desconocido`.
- Si un objeto no tiene `puntos`, se conserva con `geometry = None`.
- Si un objeto no es `dict`, se conserva como `source.raw_object` con `label = desconocido`.
- No se valida todavia si los puntos forman un poligono valido.

## Endpoints afectados

### POST segmentacion

Ruta:

```text
POST /api/muestras/{id}/segmentar/
```

Cambios:

- conserva `respuesta_json`;
- genera `resultado_normalizado`;
- guarda ambos en `ResultadoSegmentacion`;
- mantiene `objetos` en la raiz de la respuesta;
- agrega `resultado_normalizado` en la respuesta.

Si la normalizacion falla por resultado invalido, el endpoint responde `502` y no persiste `ResultadoSegmentacion`.

### GET resultados historicos

Ruta:

```text
GET /api/muestras/{id}/resultados-segmentacion/
```

Cambios:

- `ResultadoSegmentacionSerializer` ahora incluye `resultado_normalizado`.

## Archivos modificados

- `apps/web/Backend/api/models.py`
- `apps/web/Backend/api/serializers.py`
- `apps/web/Backend/api/views.py`
- `apps/web/Backend/api/tests.py`

## Archivos creados

- `apps/web/Backend/api/services/segmentation/normalizers.py`
- `apps/web/Backend/api/migrations/0003_resultadosegmentacion_resultado_normalizado.py`
- `docs/24_sprint_5_segmentation_result_normalization.md`

## Pruebas agregadas

Archivo:

```text
apps/web/Backend/api/tests.py
```

Cobertura del normalizador:

- calcula `summary.total_objects`;
- calcula `summary.counts_by_label`;
- `raw_result` sin `objetos` produce `objects = []`;
- objeto incompleto sin `puntos` no rompe normalizacion;
- `raw_result` no `dict` lanza `ValueError`.

Cobertura de endpoints:

- respuesta exitosa de `POST` guarda `resultado_normalizado`;
- respuesta exitosa de `POST` devuelve `resultado_normalizado`;
- respuesta sin `objetos` se normaliza con `total_objects = 0`;
- objeto incompleto no rompe el endpoint;
- resultado invalido no crea `ResultadoSegmentacion`;
- `GET /api/muestras/{id}/resultados-segmentacion/` incluye `resultado_normalizado`;
- errores del microservicio no crean resultados.

Todas las pruebas usan datos locales o mocks. No se llamaron microservicios reales.

## Comandos ejecutados

Desde:

```text
apps/web/Backend
```

### Crear migracion

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' manage.py makemigrations api
```

Resultado:

```text
Migrations for 'api':
  api\migrations\0003_resultadosegmentacion_resultado_normalizado.py
    - Add field resultado_normalizado to resultadosegmentacion
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

### Migraciones pendientes

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' manage.py makemigrations --check
```

Resultado:

```text
No changes detected
```

Conclusion: PASS.

### Pytest

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -m pytest
```

Resultado:

```text
37 passed, 2 skipped in 1.46s
```

Conclusion: PASS.

### Django test

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' manage.py test
```

Resultado:

```text
Found 19 test(s).
System check identified no issues (0 silenced).
Ran 19 tests in 0.230s
OK
```

Conclusion: PASS.

## Limitaciones

- Solo se soporta `SALIVA`.
- No se generaliza `MuestraSaliva`.
- No se crea `ImagenMuestra`.
- No se integra sangre.
- No se modifica frontend.
- No se renderizan poligonos ni mascaras.
- No se valida geometricamente el poligono.
- No se normalizan campos especificos futuros como confianza, area o bounding boxes.
- No se modifican microservicios ni algoritmos.

## Resultado general

PASS

Sprint 5 agrega una representacion normalizada persistida y expuesta por API, manteniendo compatibilidad con `respuesta_json` y con `objetos` en la raiz de la respuesta del endpoint de segmentacion.

## Pendientes para Sprint 6

- Definir si el frontend debe consumir `resultado_normalizado` en lugar de `respuesta_json`.
- Preparar visualizacion de `objects.geometry`.
- Definir normalizacion equivalente para sangre cuando se integre el dominio comun.
- Evaluar metadatos adicionales como algoritmo, version, confianza o escala de imagen.
- Mantener compatibilidad con historicos que tengan `resultado_normalizado = null`.
