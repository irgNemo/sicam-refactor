# Clientes de segmentación Django

La integración ya existe: las acciones de muestras en `api/views.py` leen la
imagen, resuelven el cliente, normalizan y persisten `ResultadoSegmentacion`.
No hay que crear un nuevo endpoint, modelo ni tarea Celery para instalar SICAM.
El flujo actual es síncrono y no hace fallback silencioso entre estrategias.

## Routing y configuración

| Tipo / estrategia | Servicio | Endpoint upstream |
|---|---|---|
| SALIVA / CURRENT_CUSTOM_V1 (default) | CURRENT :8001 | `/segmentar` |
| SALIVA / ALT_CPSAM_MORPHOLOGICAL_V1 | ALT :8003 | `/segmentar` |
| SANGRE / sin estrategia | BLOOD :8002 | `/api/v1/segmentar` |

Todos los upstream reciben multipart `file`. Sus respuestas contienen
`objetos`, con `id`, `tipo` y `puntos` en coordenadas de imagen.
Los IDs raw pueden repetirse; la normalización es responsabilidad de Django.

Variables, URLs y timeouts reales: ver el
[README backend](../../../README_DEVELOPMENT.md) y
[guía canónica de instalación](../../../../../../docs/developer_environment_setup_wsl.md).
No editar `settings.py` para cambiar una URL local: usar `.env`.
CURRENT tiene timeout 30 s; ALT y BLOOD, 240 s.

## Uso interno

Ejemplo desde un contexto Django ya inicializado, con bytes de una imagen
SALIVA de prueba autorizada. Esta llamada **ejecuta inferencia**, no es un check
de instalación ni persiste por sí sola:

```python
from api.services.segmentation import segment_image
from api.segmentation_strategies import SalivaSegmentationStrategy

raw = segment_image(
    'SALIVA', image_bytes, filename='saliva-demo.jpg',
    segmentation_strategy=SalivaSegmentationStrategy.ALT_CPSAM_MORPHOLOGICAL_V1,
)
```

Omitir `segmentation_strategy` para CURRENT. BLOOD usa
`segment_image('SANGRE', blood_image_bytes)` sin esa opción. Para operar el flujo
completo y persistir, usar las acciones Django existentes:

```text
POST /api/muestras/{id}/segmentar/        # JSON segmentation_strategy opcional
POST /api/muestras-sangre/{id}/segmentar/ # sin campo strategy
```

Django expone provenance en respuesta, historial y efectivo. El campo es NULL
para BLOOD; no inferir que eso significa CURRENT. Las revisiones no cambian
la estrategia del resultado padre.

## Errores y pruebas

Excepciones existentes: `SegmentationServiceError`, `SegmentationTimeoutError`,
`SegmentationConnectionError`, `InvalidSegmentationResponseError`. Las acciones
SALIVA manejan timeout 504, conexión 503 y fallo upstream/contrato 502; estrategia
inválida devuelve 400 antes de llamar al servicio. No introducir retries ni
cambio de modelo como parte del arranque.

Desde `apps/web/Backend`, ambiente `sicam`:

```bash
python -m pytest api/services/segmentation/tests.py api/test_saliva_strategies.py -q
```

Los tests normales simulan HTTP. Los comandos de arranque reales, cada uno en
su directorio y ambiente, están en el
[manual cotidiano](../../../../../../docs/30_developer_startup_and_test_data.md).
BLOOD usa `main:app`, CURRENT y ALT `app.main:app`. No existen módulos ejecutables
`apps.segmentation-saliva.main` ni `apps.segmentation-blood.main`.
