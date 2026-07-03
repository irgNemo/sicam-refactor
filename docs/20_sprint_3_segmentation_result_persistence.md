# Sprint 3 - Segmentation Result Persistence

## Fecha

2026-07-02 22:48:52 -06:00

## Referencia Git

- Rama: `master`
- Commit: `af14e53`

## Objetivo

Agregar persistencia minima del resultado JSON de segmentacion en Django, sin redisenar el dominio y sin generalizar `MuestraSaliva`.

## Modelo creado

Modelo:

```text
ResultadoSegmentacion
```

Archivo:

```text
apps/web/Backend/api/models.py
```

## Campos

```text
id_resultado_segmentacion: AutoField primary key
muestra: ForeignKey a MuestraSaliva, related_name='resultados_segmentacion'
tipo_muestra: CharField max_length=20, default='SALIVA'
respuesta_json: JSONField
estado: CharField max_length=20, default='COMPLETADO'
error: TextField blank=True, null=True
creado_en: DateTimeField auto_now_add=True
actualizado_en: DateTimeField auto_now=True
```

## Migracion creada

```text
apps/web/Backend/api/migrations/0002_resultadosegmentacion.py
```

La migracion crea la tabla para `ResultadoSegmentacion` y no altera modelos existentes.

## Politica de persistencia

Cada ejecucion exitosa del endpoint:

```text
POST /api/muestras/{id}/segmentar/
```

crea un nuevo `ResultadoSegmentacion`.

No se sobrescriben resultados anteriores. Esta politica preserva trazabilidad y evita decidir todavia una semantica de "ultimo resultado".

En errores del cliente o microservicio no se guarda resultado exitoso.

## Endpoint modificado

Archivo:

```text
apps/web/Backend/api/views.py
```

Accion:

```text
MuestraSalivaViewSet.segmentar
```

Despues de una respuesta exitosa de:

```python
segment_image('SALIVA', image_bytes, filename=muestra.imagen.name)
```

se crea:

```python
ResultadoSegmentacion.objects.create(
    muestra=muestra,
    tipo_muestra='SALIVA',
    respuesta_json=result,
    estado='COMPLETADO',
)
```

## Respuesta del endpoint

Se conserva el JSON original del microservicio en la raiz de la respuesta y se agrega metadata minima:

```json
{
  "objetos": [
    {
      "id": 1,
      "tipo": "membrana",
      "puntos": [[10, 20]]
    }
  ],
  "resultado_segmentacion": {
    "id": 1,
    "estado": "COMPLETADO",
    "tipo_muestra": "SALIVA",
    "creado_en": "2026-07-02T22:48:52.000000+00:00"
  }
}
```

Esto mantiene compatibilidad con consumidores que leen `objetos`.

## Admin

Se registro `ResultadoSegmentacion` en:

```text
apps/web/Backend/api/admin.py
```

Configuracion:

- `list_display`
- `list_filter`
- `search_fields`

## Pruebas agregadas

Archivo:

```text
apps/web/Backend/api/tests.py
```

Cobertura agregada:

- Respuesta exitosa crea un `ResultadoSegmentacion`.
- Respuesta exitosa guarda `respuesta_json` correctamente.
- La respuesta conserva `objetos` y agrega `resultado_segmentacion`.
- Llamada repetida crea un nuevo registro y no sobrescribe el anterior.
- Muestra inexistente no crea resultado.
- Muestra sin imagen no crea resultado.
- Timeout no crea resultado.
- Error de conexion no crea resultado.
- Respuesta invalida no crea resultado.
- Error general del servicio no crea resultado.

Todas las llamadas al cliente de segmentacion se hacen con mocks. No se llamaron microservicios reales.

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
  api\migrations\0002_resultadosegmentacion.py
    - Create model ResultadoSegmentacion
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
26 passed, 2 skipped in 1.48s
```

Conclusion: PASS.

### Django test

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' manage.py test
```

Resultado:

```text
Found 8 test(s).
System check identified no issues (0 silenced).
Ran 8 tests in 0.162s
OK
```

Conclusion: PASS.

## Limitaciones

- Solo se soporta `SALIVA`.
- No se crea `ImagenMuestra`.
- No se generaliza el dominio para sangre.
- No se expone CRUD/API publica para consultar `ResultadoSegmentacion`.
- No se guardan errores como registros con `estado='ERROR'`.
- No se ejecuta segmentacion real.
- No se levantan microservicios.
- No se descargan modelos.

## Resultado general

PASS

Sprint 3 agrega persistencia JSON minima para segmentaciones exitosas de `MuestraSaliva`, manteniendo compatibilidad con el endpoint de Sprint 2.

## Pendientes para Sprint 4

- Integrar el flujo frontend minimo contra `POST /api/muestras/{id}/segmentar/`.
- Decidir si el frontend debe mostrar metadata de `resultado_segmentacion`.
- Definir una vista o endpoint para consultar resultados historicos.
- Mantener compatibilidad con `objetos`.
- No generalizar todavia a sangre salvo sprint dedicado.
