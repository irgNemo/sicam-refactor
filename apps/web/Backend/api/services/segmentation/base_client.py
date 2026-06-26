"""
Cliente base abstracto para servicios de segmentación.

Define la interfaz común para todos los clientes de segmentación.
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional
import requests
from requests.exceptions import (
    Timeout,
    ConnectionError,
    RequestException,
)

from .exceptions import (
    SegmentationServiceError,
    SegmentationTimeoutError,
    SegmentationConnectionError,
    InvalidSegmentationResponseError,
)


class SegmentationClient(ABC):
    """
    Cliente base abstracto para segmentación.
    
    Subclases deben implementar:
    - get_endpoint(): retorna el path del endpoint (ej: '/segmentar')
    - validate_response(data): valida que la respuesta sea válida
    """

    def __init__(self, base_url: str, timeout: int = 30):
        """
        Inicializar cliente de segmentación.
        
        Args:
            base_url: URL base del servicio (ej: 'http://localhost:8001')
            timeout: Timeout en segundos para la solicitud (default: 30)
        """
        self.base_url = base_url.rstrip('/')  # Eliminar trailing slash
        self.timeout = timeout

    @abstractmethod
    def get_endpoint(self) -> str:
        """
        Retorna el endpoint específico del servicio.
        
        Returns:
            str: Path del endpoint (ej: '/segmentar', '/api/v1/segmentar')
        """
        pass

    @abstractmethod
    def validate_response(self, data: Dict) -> None:
        """
        Valida que la respuesta tenga la estructura esperada.
        
        Args:
            data: Datos JSON de la respuesta
            
        Raises:
            InvalidSegmentationResponseError: Si la estructura es inválida
        """
        pass

    def segment(self, image_file: bytes, filename: str = 'image.jpg') -> Dict:
        """
        Enviar imagen para segmentación.
        
        Args:
            image_file: Contenido de imagen como bytes
            filename: Nombre del archivo (default: 'image.jpg')
            
        Returns:
            Dict: Respuesta JSON del microservicio con estructura:
                {
                    "objetos": [
                        {
                            "id": 1,
                            "tipo": "membrana",
                            "puntos": [[10, 20], [12, 25]]
                        }
                    ]
                }
                
        Raises:
            SegmentationTimeoutError: Si la solicitud excede el timeout
            SegmentationConnectionError: Si no hay conexión
            InvalidSegmentationResponseError: Si la respuesta es inválida
            SegmentationServiceError: Para otros errores
        """
        url = f"{self.base_url}{self.get_endpoint()}"
        
        try:
            # Preparar payload multipart con archivo
            files = {'file': (filename, image_file)}
            
            # Hacer POST request con timeout
            response = requests.post(
                url,
                files=files,
                timeout=self.timeout,
            )
            
            # Verificar status code
            response.raise_for_status()
            
            # Parsear respuesta JSON
            try:
                data = response.json()
            except ValueError as e:
                raise InvalidSegmentationResponseError(
                    f"No se puede parsear respuesta JSON: {str(e)}"
                )
            
            # Validar estructura de respuesta
            self.validate_response(data)
            
            return data

        except Timeout:
            raise SegmentationTimeoutError(
                f"Timeout ({self.timeout}s) en {url}"
            )
        
        except ConnectionError as e:
            raise SegmentationConnectionError(
                f"Error de conexión a {url}: {str(e)}"
            )
        
        except InvalidSegmentationResponseError:
            # Re-lanzar excepciones de validación
            raise
        
        except RequestException as e:
            # Capturar otros errores de requests (ej: status code 4xx/5xx)
            raise SegmentationServiceError(
                f"Error en solicitud a {url}: {str(e)}"
            )
        
        except Exception as e:
            # Capturar excepciones inesperadas
            raise SegmentationServiceError(
                f"Error inesperado en segmentación: {str(e)}"
            )
