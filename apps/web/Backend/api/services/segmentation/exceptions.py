"""
Excepciones personalizadas para clientes de segmentación.

Define errores específicos que pueden ocurrir durante la comunicación
con microservicios de segmentación.
"""


class SegmentationServiceError(Exception):
    """
    Excepción base para errores de servicio de segmentación.
    
    Representa cualquier error que ocurra durante la llamada a un servicio
    de segmentación o procesamiento de su respuesta.
    """
    pass


class SegmentationTimeoutError(SegmentationServiceError):
    """
    Error cuando el servicio de segmentación excede el timeout.
    
    Indica que la solicitud tardó demasiado en recibir respuesta.
    El timeout está configurado en settings.py mediante:
    - SALIVA_SERVICE_TIMEOUT
    - BLOOD_SERVICE_TIMEOUT
    """
    pass


class SegmentationConnectionError(SegmentationServiceError):
    """
    Error de conexión al servicio de segmentación.
    
    Indica que no se pudo establecer conexión con el microservicio:
    - Servicio no disponible
    - Host/puerto incorrectos
    - Problemas de red
    """
    pass


class InvalidSegmentationResponseError(SegmentationServiceError):
    """
    Error cuando la respuesta del servicio es inválida.
    
    Indica que:
    - La respuesta no es JSON válido
    - Falta el campo 'objetos' esperado
    - La estructura no coincide con el contrato esperado
    """
    pass
