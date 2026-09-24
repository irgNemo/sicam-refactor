"""
Factory y utilities para clientes de segmentación.

Proporciona funciones helper para obtener el cliente correcto
y ejecutar segmentación.
"""

from typing import Dict
from django.conf import settings

from .base_client import SegmentationClient
from .saliva_client import SalivaSegmentationClient
from .blood_client import BloodSegmentationClient
from .exceptions import SegmentationServiceError
from .types import SampleType, normalize_sample_type
from .strategies import resolve_saliva_segmentation_service


def get_segmentation_client(
    sample_type: str, *, segmentation_strategy=None,
) -> SegmentationClient:
    """
    Factory para obtener el cliente de segmentación correcto.
    
    Args:
        sample_type: Tipo de muestra 'SALIVA' o 'SANGRE'
        segmentation_strategy: Estrategia SALIVA opcional; omitida usa CURRENT.
        
    Returns:
        SegmentationClient: Cliente configurado para el tipo de muestra
        
    Raises:
        SegmentationServiceError: Si el tipo de muestra no está configurado
        
    Ejemplo:
        >>> client = get_segmentation_client('SALIVA')
        >>> result = client.segment(image_bytes)
    """
    sample_type = normalize_sample_type(sample_type)

    if sample_type == SampleType.SALIVA:
        config = resolve_saliva_segmentation_service(segmentation_strategy)
        return SalivaSegmentationClient(config['url'], config['timeout'])
    if segmentation_strategy is not None:
        raise ValueError('segmentation_strategy is only supported for SALIVA samples')
    
    # Obtener configuración desde settings
    services_config = getattr(settings, 'SEGMENTATION_SERVICES', {})
    
    if sample_type not in services_config:
        raise SegmentationServiceError(
            f"Tipo de muestra no configurado: {sample_type}. "
            f"Tipos disponibles: {list(services_config.keys())}"
        )
    
    config = services_config[sample_type]
    base_url = config['url']
    timeout = config.get('timeout', 30)
    
    # Crear cliente específico
    if sample_type == SampleType.BLOOD:
        return BloodSegmentationClient(base_url, timeout)
    else:
        raise SegmentationServiceError(
            f"Tipo de muestra desconocido: {sample_type}"
        )


def segment_image(
    sample_type: str, image_file: bytes, filename: str = 'image.jpg',
    *, segmentation_strategy=None,
) -> Dict:
    """
    Segmentar una imagen usando el servicio correcto.
    
    Esta es la función principal a usar en vistas y servicios.
    
    Args:
        sample_type: Tipo de muestra 'SALIVA' o 'SANGRE'
        segmentation_strategy: Estrategia SALIVA opcional; omitida usa CURRENT.
        image_file: Contenido de imagen como bytes
        filename: Nombre del archivo (default: 'image.jpg')
        
    Returns:
        Dict: Respuesta del microservicio con objetos segmentados
        
    Raises:
        SegmentationTimeoutError: Si el servicio excede timeout
        SegmentationConnectionError: Si no hay conexión
        InvalidSegmentationResponseError: Si la respuesta es inválida
        SegmentationServiceError: Para otros errores
        
    Ejemplo:
        >>> from django.core.files.uploadedfile import UploadedFile
        >>> image_bytes = request.FILES['imagen'].read()
        >>> result = segment_image('SALIVA', image_bytes)
        >>> print(result['objetos'])  # Array de objetos segmentados
    """
    client = get_segmentation_client(sample_type, segmentation_strategy=segmentation_strategy)
    return client.segment(image_file, filename)
