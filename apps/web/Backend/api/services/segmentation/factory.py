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


def get_segmentation_client(sample_type: str) -> SegmentationClient:
    """
    Factory para obtener el cliente de segmentación correcto.
    
    Args:
        sample_type: Tipo de muestra 'SALIVA' o 'SANGRE'
        
    Returns:
        SegmentationClient: Cliente configurado para el tipo de muestra
        
    Raises:
        SegmentationServiceError: Si el tipo de muestra no está configurado
        
    Ejemplo:
        >>> client = get_segmentation_client('SALIVA')
        >>> result = client.segment(image_bytes)
    """
    sample_type = sample_type.upper()
    
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
    if sample_type == 'SALIVA':
        return SalivaSegmentationClient(base_url, timeout)
    elif sample_type == 'SANGRE':
        return BloodSegmentationClient(base_url, timeout)
    else:
        raise SegmentationServiceError(
            f"Tipo de muestra desconocido: {sample_type}"
        )


def segment_image(sample_type: str, image_file: bytes, filename: str = 'image.jpg') -> Dict:
    """
    Segmentar una imagen usando el servicio correcto.
    
    Esta es la función principal a usar en vistas y servicios.
    
    Args:
        sample_type: Tipo de muestra 'SALIVA' o 'SANGRE'
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
    client = get_segmentation_client(sample_type)
    return client.segment(image_file, filename)
