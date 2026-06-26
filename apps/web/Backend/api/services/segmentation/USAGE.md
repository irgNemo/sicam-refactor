# Clientes de Microservicios de Segmentación

## Descripción

Los clientes de segmentación proporcionan interfaces para comunicación con los microservicios de segmentación de:
- Muestras salivales (endpoint: `/segmentar`)
- Muestras de sangre (endpoint: `/api/v1/segmentar`)

## Estructura

```
api/services/segmentation/
├── __init__.py              # Exports públicos
├── base_client.py           # Clase base abstracta
├── saliva_client.py         # Cliente para saliva
├── blood_client.py          # Cliente para sangre
├── exceptions.py            # Excepciones personalizadas
├── factory.py               # Factory pattern y helpers
└── USAGE.md                 # Esta documentación
```

## Uso rápido

### Forma simple (recomendada)

```python
from api.services.segmentation import segment_image

# En una vista o servicio
try:
    image_bytes = request.FILES['imagen'].read()
    result = segment_image('SALIVA', image_bytes)
    
    print(result)  # {'objetos': [...]}
    
except SegmentationTimeoutError:
    # El servicio tardó demasiado
    return Response({'error': 'Segmentación tardó demasiado'}, status=500)
    
except SegmentationConnectionError:
    # El servicio no está disponible
    return Response({'error': 'Servicio de segmentación no disponible'}, status=503)
    
except InvalidSegmentationResponseError as e:
    # Respuesta inválida o corrupta
    return Response({'error': f'Respuesta inválida: {str(e)}'}, status=500)
```

### Forma avanzada (con cliente directo)

```python
from api.services.segmentation import get_segmentation_client

# Obtener cliente
client = get_segmentation_client('SANGRE')

# Usar cliente
try:
    result = client.segment(image_bytes)
    print(result['objetos'])  # Array de objetos segmentados
    
except Exception as e:
    # Manejar error
    print(f"Error: {e}")
```

## Ejemplos de uso en vistas

### Ejemplo 1: Upload con segmentación inmediata

```python
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

from api.models import MuestraSaliva
from api.serializers import MuestraSalivaSerializer
from api.services.segmentation import segment_image, SegmentationServiceError

class MuestraSalivaViewSet(viewsets.ModelViewSet):
    queryset = MuestraSaliva.objects.all()
    serializer_class = MuestraSalivaSerializer
    
    @action(detail=True, methods=['post'])
    def segmentar(self, request, pk=None):
        """
        POST /api/muestras/{id}/segmentar/
        
        Ejecutar segmentación en muestra existente.
        """
        muestra = self.get_object()
        
        try:
            # Leer imagen desde archivo
            image_bytes = muestra.imagen.read()
            
            # Llamar cliente de segmentación
            result = segment_image('SALIVA', image_bytes, filename=muestra.imagen.name)
            
            return Response({
                'status': 'success',
                'objetos': result['objetos'],
                'fecha_segmentacion': timezone.now(),
            })
            
        except SegmentationTimeoutError:
            return Response(
                {'error': 'Timeout en segmentación'},
                status=status.HTTP_504_GATEWAY_TIMEOUT
            )
        except SegmentationConnectionError:
            return Response(
                {'error': 'Servicio no disponible'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
```

### Ejemplo 2: Upload con segmentación asíncrona (Celery)

```python
# tasks.py (con Celery)
from celery import shared_task
from api.services.segmentation import segment_image
from api.models import ResultadoSegmentacion, MuestraSaliva

@shared_task
def run_segmentation(sample_id, sample_type):
    """
    Tarea asíncrona para ejecutar segmentación.
    """
    try:
        muestra = MuestraSaliva.objects.get(id=sample_id)
        image_bytes = muestra.imagen.read()
        
        # Ejecutar segmentación
        result = segment_image(sample_type, image_bytes)
        
        # Guardar resultado
        ResultadoSegmentacion.objects.create(
            muestra=muestra,
            objetos_json=result['objetos'],
            algoritmo='cellpose-saliva',
            estado='procesado',
        )
        
    except Exception as e:
        # Log del error
        print(f"Error en segmentación: {e}")
```

### Ejemplo 3: Manejo granular de errores

```python
from api.services.segmentation import (
    get_segmentation_client,
    SegmentationServiceError,
    SegmentationTimeoutError,
    SegmentationConnectionError,
    InvalidSegmentationResponseError,
)

def procesar_muestra(image_bytes, sample_type):
    """Procesar imagen con manejo detallado de errores."""
    
    client = get_segmentation_client(sample_type)
    
    try:
        result = client.segment(image_bytes)
        return {'success': True, 'objetos': result['objetos']}
        
    except SegmentationTimeoutError as e:
        # Registrar en logs, notificar admin, reintentar
        logger.error(f"Timeout en segmentación: {e}")
        return {
            'success': False,
            'error': 'timeout',
            'message': 'Segmentación tardó demasiado',
        }
        
    except SegmentationConnectionError as e:
        # Servicio no disponible
        logger.error(f"Conexión rechazada: {e}")
        return {
            'success': False,
            'error': 'connection_error',
            'message': 'Servicio no disponible',
        }
        
    except InvalidSegmentationResponseError as e:
        # Respuesta corrupta o contrato roto
        logger.error(f"Respuesta inválida: {e}")
        return {
            'success': False,
            'error': 'invalid_response',
            'message': 'Respuesta del servicio inválida',
        }
        
    except SegmentationServiceError as e:
        # Error genérico
        logger.error(f"Error de segmentación: {e}")
        return {
            'success': False,
            'error': 'generic_error',
            'message': 'Error en segmentación',
        }
```

## Configuración requerida

Asegurar que `settings.py` tiene configuradas las URLs de microservicios:

```python
# config/settings.py

SEGMENTATION_SERVICES = {
    'SALIVA': {
        'url': env('SALIVA_SEGMENTATION_SERVICE_URL', default='http://localhost:8001'),
        'timeout': env.int('SALIVA_SERVICE_TIMEOUT', default=30),
    },
    'SANGRE': {
        'url': env('BLOOD_SEGMENTATION_SERVICE_URL', default='http://localhost:8002'),
        'timeout': env.int('BLOOD_SERVICE_TIMEOUT', default=30),
    },
}
```

Y en `.env`:

```env
SALIVA_SEGMENTATION_SERVICE_URL=http://localhost:8001
SALIVA_SERVICE_TIMEOUT=30

BLOOD_SEGMENTATION_SERVICE_URL=http://localhost:8002
BLOOD_SERVICE_TIMEOUT=30
```

## Excepciones

### SegmentationServiceError
Excepción base para todos los errores de segmentación.

```python
except SegmentationServiceError:
    # Captura cualquier error de segmentación
    pass
```

### SegmentationTimeoutError
El servicio excedió el timeout configurado.

```python
except SegmentationTimeoutError:
    # Reintentar después o reportar al usuario
    pass
```

### SegmentationConnectionError
No se pudo conectar con el servicio.

```python
except SegmentationConnectionError:
    # El servicio no está disponible
    # Usar caché, queue, o notificar admin
    pass
```

### InvalidSegmentationResponseError
La respuesta no tiene la estructura esperada.

```python
except InvalidSegmentationResponseError as e:
    # Problema con el contrato de respuesta
    logger.error(f"Contrato roto: {e}")
```

## Contrato de respuesta esperado

### Saliva

```json
{
    "objetos": [
        {
            "id": 1,
            "tipo": "membrana",
            "puntos": [[10, 20], [12, 25], [15, 28]]
        },
        {
            "id": 1,
            "tipo": "nucleo",
            "puntos": [[30, 40], [32, 45]]
        },
        {
            "id": 1,
            "tipo": "micronucleo",
            "puntos": [[50, 60], [52, 65]]
        }
    ]
}
```

### Sangre

```json
{
    "objetos": [
        {
            "id": 1,
            "tipo": "membrana",
            "puntos": [[10, 20], [12, 25]]
        },
        {
            "id": 1,
            "tipo": "micronucleo",
            "puntos": [[30, 40], [32, 45]]
        }
    ]
}
```

## Testing

### Test unitario básico

```python
import pytest
from unittest.mock import Mock, patch
from api.services.segmentation import segment_image
from api.services.segmentation import InvalidSegmentationResponseError

def test_segment_saliva_success():
    """Test exitoso de segmentación de saliva."""
    image_bytes = b'fake image data'
    
    with patch('requests.post') as mock_post:
        mock_response = Mock()
        mock_response.json.return_value = {
            'objetos': [
                {'id': 1, 'tipo': 'membrana', 'puntos': [[10, 20]]}
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        result = segment_image('SALIVA', image_bytes)
        
        assert 'objetos' in result
        assert len(result['objetos']) == 1
        assert result['objetos'][0]['tipo'] == 'membrana'

def test_segment_invalid_response():
    """Test con respuesta inválida."""
    image_bytes = b'fake image data'
    
    with patch('requests.post') as mock_post:
        mock_response = Mock()
        mock_response.json.return_value = {'invalid': 'data'}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        with pytest.raises(InvalidSegmentationResponseError):
            segment_image('SALIVA', image_bytes)
```

### Test de integración (con servidor real)

```bash
# 1. Asegurar que servicios estén corriendo
python -m apps.segmentation-saliva.main &    # puerto 8001
python -m apps.segmentation-blood.main &     # puerto 8002

# 2. Ejecutar test
cd apps/web/Backend
python manage.py test api.tests.test_segmentation_clients

# 3. Detener servicios
kill %1 %2
```

## Debugging

### Verificar conexión a servicios

```python
from api.services.segmentation import get_segmentation_client

# Saliva
saliva_client = get_segmentation_client('SALIVA')
print(f"Saliva URL: {saliva_client.base_url}")
print(f"Saliva endpoint: {saliva_client.get_endpoint()}")
print(f"Saliva timeout: {saliva_client.timeout}")

# Sangre
blood_client = get_segmentation_client('SANGRE')
print(f"Blood URL: {blood_client.base_url}")
print(f"Blood endpoint: {blood_client.get_endpoint()}")
print(f"Blood timeout: {blood_client.timeout}")
```

### Hacer request manual

```bash
# Test saliva
curl -X POST http://localhost:8001/segmentar \
  -F "file=@path/to/image.jpg"

# Test blood
curl -X POST http://localhost:8002/api/v1/segmentar \
  -F "file=@path/to/image.jpg"
```

## Próximos pasos

- [ ] Crear modelo `ResultadoSegmentacion` para persistir resultados
- [ ] Crear viewset para exponer `/api/muestras/{id}/segmentar/`
- [ ] Agregar soporte para Celery (tareas asíncronas)
- [ ] Agregar retry logic con exponential backoff
- [ ] Implementar caché de resultados
- [ ] Agregar metrics/logging detallado
