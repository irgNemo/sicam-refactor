"""
Cliente para microservicio de segmentación de muestras salivales.

Interfaz con el servicio FastAPI en apps/segmentation-saliva/.
"""

from typing import Dict
from .base_client import SegmentationClient
from .exceptions import InvalidSegmentationResponseError


class SalivaSegmentationClient(SegmentationClient):
    """
    Cliente para segmentación de muestras salivales.
    
    Comunicación con: POST /segmentar
    URL: configurable via settings.SEGMENTATION_SERVICES['SALIVA']['url']
    Timeout: configurable via settings.SEGMENTATION_SERVICES['SALIVA']['timeout']
    
    Respuesta esperada:
    {
        "objetos": [
            {
                "id": 1,
                "tipo": "membrana",
                "puntos": [[10, 20], [12, 25]]
            },
            {
                "id": 2,
                "tipo": "nucleo",
                "puntos": [[30, 40], [32, 45]]
            },
            {
                "id": 3,
                "tipo": "micronucleo",
                "puntos": [[50, 60], [52, 65]]
            }
        ]
    }
    """

    def get_endpoint(self) -> str:
        """Retorna el endpoint del servicio de saliva."""
        return '/segmentar'

    def validate_response(self, data: Dict) -> None:
        """
        Valida que la respuesta tenga la estructura esperada.
        
        Verifica:
        - Campo 'objetos' existe
        - 'objetos' es una lista
        - Cada objeto tiene campos requeridos: id, tipo, puntos
        
        Args:
            data: Datos JSON de la respuesta
            
        Raises:
            InvalidSegmentationResponseError: Si la estructura es inválida
        """
        if not isinstance(data, dict):
            raise InvalidSegmentationResponseError(
                f"Respuesta debe ser un diccionario, obtuvo: {type(data)}"
            )
        
        if 'objetos' not in data:
            raise InvalidSegmentationResponseError(
                "Respuesta no contiene campo 'objetos'"
            )
        
        objetos = data['objetos']
        if not isinstance(objetos, list):
            raise InvalidSegmentationResponseError(
                f"Campo 'objetos' debe ser lista, obtuvo: {type(objetos)}"
            )
        
        # Validar estructura de cada objeto
        for idx, obj in enumerate(objetos):
            if not isinstance(obj, dict):
                raise InvalidSegmentationResponseError(
                    f"Objeto {idx} debe ser diccionario, obtuvo: {type(obj)}"
                )
            
            required_fields = {'id', 'tipo', 'puntos'}
            missing_fields = required_fields - set(obj.keys())
            if missing_fields:
                raise InvalidSegmentationResponseError(
                    f"Objeto {idx} falta campos requeridos: {missing_fields}"
                )
            
            # Validar que puntos es lista de coordenadas
            if not isinstance(obj['puntos'], list):
                raise InvalidSegmentationResponseError(
                    f"Objeto {idx} - 'puntos' debe ser lista, obtuvo: {type(obj['puntos'])}"
                )
