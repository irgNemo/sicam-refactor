"""
Clientes para microservicios de segmentación.

Proporciona interfaces para comunicación con servicios de segmentación de:
- Muestras salivales
- Muestras de sangre
"""

from .base_client import SegmentationClient
from .saliva_client import SalivaSegmentationClient
from .blood_client import BloodSegmentationClient
from .exceptions import (
    SegmentationServiceError,
    SegmentationTimeoutError,
    SegmentationConnectionError,
    InvalidSegmentationResponseError,
)
from .factory import get_segmentation_client, segment_image

__all__ = [
    # Clientes base
    'SegmentationClient',
    'SalivaSegmentationClient',
    'BloodSegmentationClient',
    # Excepciones
    'SegmentationServiceError',
    'SegmentationTimeoutError',
    'SegmentationConnectionError',
    'InvalidSegmentationResponseError',
    # Factory y helpers
    'get_segmentation_client',
    'segment_image',
]
