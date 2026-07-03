# Sprint 2 - Django Segmentation Endpoint

## Fecha

2026-07-02 16:35:49 -06:00

## Referencia Git

- Rama: `master`
- Commit: `3d9b53d`

## Objetivo

Implementar un endpoint Django minimo para solicitar segmentacion de una muestra existente usando los clientes de segmentacion ya disponibles en:

```text
apps/web/Backend/api/services/segmentation/
```

Django queda como orquestador del flujo. El frontend no debe llamar directamente a los microservicios.

## Ruta implementada

```text
POST /api/muestras/{id}/segmentar/
```

La ruta se implemento como accion DRF en:

```text
MuestraSalivaViewSet
```

El router existente ya registraba:

```python
router.register(r'muestras', MuestraSalivaViewSet, basename='muestra')
```

Por eso no fue necesario modificar `api/urls.py`.

## Archivos modificados

- `apps/web/Backend/api/views.py`
- `apps/web/Backend/api/tests.py`
- `docs/19_sprint_2_django_segmentation_endpoint.md`

No se modificaron modelos Django, serializers, migraciones, frontend, microservicios ni algoritmos de segmentacion.

## Cliente usado

La vista usa el helper:

```python
segment_image('SALIVA', image_bytes, filename=muestra.imagen.name)
```

Origen:

```text
api.services.segmentation.factory.segment_image
```

En este sprint solo se soporta `SALIVA`, porque el dominio actual expone `MuestraSaliva` y todavia no existe un modelo comun como `ImagenMuestra`.

## Alcance funcional

El endpoint:

1. Recibe el ID de una muestra existente.
2. Busca la muestra mediante `MuestraSalivaViewSet.get_object()`.
3. Verifica que la muestra tenga imagen asociada.
4. Lee los bytes del archivo de imagen.
5. Llama al cliente de segmentacion de saliva.
6. Devuelve directamente la respuesta JSON del microservicio.

Formato esperado de respuesta:

```json
{
  "objetos": [
    {
      "id": 1,
      "tipo": "membrana",
      "puntos": [[10, 20]]
    }
  ]
}
```

## Manejo de errores

Casos cubiertos:

- Muestra inexistente: `404`.
- Muestra sin imagen: `400`.
- Imagen no legible: `400`.
- Imagen vacia: `400`.
- Timeout del microservicio: `504`.
- Microservicio no disponible o error de conexion: `503`.
- Respuesta invalida del microservicio: `502`.
- Error general del servicio de segmentacion: `502`.
- Error inesperado: `500`.

## Limitaciones

- No se persiste el resultado JSON en base de datos.
- No se crea `ImagenMuestra`.
- No se generaliza el dominio para sangre.
- No se llama al microservicio real durante pruebas.
- No se ejecuta segmentacion real.
- No se levantan microservicios.
- No se descargan modelos.

## Pruebas agregadas

Archivo:

```text
apps/web/Backend/api/tests.py
```

Se agregaron pruebas con mocks para:

- Muestra existente con imagen y respuesta exitosa mockeada.
- Muestra inexistente.
- Muestra sin imagen.
- Timeout del cliente de segmentacion.
- Error de conexion del cliente.
- Respuesta invalida del cliente.
- Error general del cliente de segmentacion.

El caso "tipo no soportado" no aplica directamente a este endpoint porque `MuestraSalivaViewSet` representa solo muestras de saliva. La generalizacion a otros tipos queda fuera de Sprint 2.

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
25 passed, 2 skipped in 1.22s
```

Conclusion: PASS.

### Django test

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' manage.py test
```

Resultado:

```text
Found 7 test(s).
System check identified no issues (0 silenced).
Ran 7 tests in 0.149s
OK
```

Conclusion: PASS.

## Resultado general

PASS

El endpoint Django minimo de segmentacion fue implementado y validado con pruebas mockeadas, sin llamadas reales a microservicios y sin persistencia de resultados.

## Pendientes para Sprint 3

- Definir donde persistir el resultado JSON de segmentacion.
- Agregar campo o modelo de persistencia sin romper compatibilidad.
- Guardar la respuesta del microservicio asociada a la muestra.
- Definir estados del flujo si se requiere trazabilidad.
- Agregar pruebas de persistencia.
- Mantener compatibilidad con el endpoint `POST /api/muestras/{id}/segmentar/`.
