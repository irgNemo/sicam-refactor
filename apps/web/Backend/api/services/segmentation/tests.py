"""
Tests unitarios para clientes de segmentación.

Ejecutar con:
    pytest api/services/segmentation/tests.py
    
O con cobertura:
    pytest api/services/segmentation/tests.py --cov=api.services.segmentation
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from requests.exceptions import Timeout, ConnectionError as RequestsConnectionError

from .base_client import SegmentationClient
from .saliva_client import SalivaSegmentationClient
from .blood_client import BloodSegmentationClient
from .factory import get_segmentation_client, segment_image
from .exceptions import (
    SegmentationTimeoutError,
    SegmentationConnectionError,
    InvalidSegmentationResponseError,
    SegmentationServiceError,
)


class TestSalivaSegmentationClient:
    """Tests para cliente de saliva."""

    def test_get_endpoint(self):
        """Test que endpoint sea correcto."""
        client = SalivaSegmentationClient('http://localhost:8001', timeout=30)
        assert client.get_endpoint() == '/segmentar'

    def test_validate_response_valid(self):
        """Test validación con respuesta válida."""
        client = SalivaSegmentationClient('http://localhost:8001')
        
        valid_response = {
            'objetos': [
                {'id': 1, 'tipo': 'membrana', 'puntos': [[10, 20]]},
                {'id': 2, 'tipo': 'nucleo', 'puntos': [[30, 40]]},
            ]
        }
        
        # No debe lanzar excepción
        client.validate_response(valid_response)

    def test_validate_response_missing_objetos(self):
        """Test validación sin campo objetos."""
        client = SalivaSegmentationClient('http://localhost:8001')
        
        invalid_response = {'data': []}
        
        with pytest.raises(InvalidSegmentationResponseError):
            client.validate_response(invalid_response)

    def test_validate_response_objetos_not_list(self):
        """Test validación con objetos no lista."""
        client = SalivaSegmentationClient('http://localhost:8001')
        
        invalid_response = {'objetos': 'not_a_list'}
        
        with pytest.raises(InvalidSegmentationResponseError):
            client.validate_response(invalid_response)

    def test_validate_response_missing_required_fields(self):
        """Test validación objeto sin campos requeridos."""
        client = SalivaSegmentationClient('http://localhost:8001')
        
        invalid_response = {
            'objetos': [
                {'id': 1, 'tipo': 'membrana'}  # Falta 'puntos'
            ]
        }
        
        with pytest.raises(InvalidSegmentationResponseError):
            client.validate_response(invalid_response)

    @patch('requests.post')
    def test_segment_success(self, mock_post):
        """Test segmentación exitosa."""
        client = SalivaSegmentationClient('http://localhost:8001', timeout=30)
        
        expected_response = {
            'objetos': [
                {'id': 1, 'tipo': 'membrana', 'puntos': [[10, 20]]}
            ]
        }
        
        mock_response = Mock()
        mock_response.json.return_value = expected_response
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        image_bytes = b'fake_image_data'
        result = client.segment(image_bytes, filename='test.jpg')
        
        assert result == expected_response
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert 'http://localhost:8001/segmentar' in call_args[0]
        assert call_args[1]['timeout'] == 30

    @patch('requests.post')
    def test_segment_timeout(self, mock_post):
        """Test timeout en segmentación."""
        client = SalivaSegmentationClient('http://localhost:8001', timeout=5)
        
        mock_post.side_effect = Timeout('Request timeout')
        
        with pytest.raises(SegmentationTimeoutError):
            client.segment(b'fake_image')

    @patch('requests.post')
    def test_segment_connection_error(self, mock_post):
        """Test error de conexión."""
        client = SalivaSegmentationClient('http://localhost:8001')
        
        mock_post.side_effect = RequestsConnectionError('Connection refused')
        
        with pytest.raises(SegmentationConnectionError):
            client.segment(b'fake_image')

    @patch('requests.post')
    def test_segment_invalid_json(self, mock_post):
        """Test respuesta JSON inválida."""
        client = SalivaSegmentationClient('http://localhost:8001')
        
        mock_response = Mock()
        mock_response.json.side_effect = ValueError('Invalid JSON')
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        with pytest.raises(InvalidSegmentationResponseError):
            client.segment(b'fake_image')

    @patch('requests.post')
    def test_segment_invalid_response_structure(self, mock_post):
        """Test estructura de respuesta inválida."""
        client = SalivaSegmentationClient('http://localhost:8001')
        
        mock_response = Mock()
        mock_response.json.return_value = {'invalid': 'data'}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        with pytest.raises(InvalidSegmentationResponseError):
            client.segment(b'fake_image')


class TestBloodSegmentationClient:
    """Tests para cliente de sangre."""

    def test_get_endpoint(self):
        """Test que endpoint sea correcto."""
        client = BloodSegmentationClient('http://localhost:8002', timeout=30)
        assert client.get_endpoint() == '/api/v1/segmentar'

    def test_validate_response_valid(self):
        """Test validación con respuesta válida."""
        client = BloodSegmentationClient('http://localhost:8002')
        
        valid_response = {
            'objetos': [
                {'id': 1, 'tipo': 'membrana', 'puntos': [[10, 20]]},
                {'id': 2, 'tipo': 'micronucleo', 'puntos': [[30, 40]]},
            ]
        }
        
        # No debe lanzar excepción
        client.validate_response(valid_response)

    @patch('requests.post')
    def test_segment_success(self, mock_post):
        """Test segmentación exitosa."""
        client = BloodSegmentationClient('http://localhost:8002', timeout=30)
        
        expected_response = {
            'objetos': [
                {'id': 1, 'tipo': 'membrana', 'puntos': [[10, 20]]}
            ]
        }
        
        mock_response = Mock()
        mock_response.json.return_value = expected_response
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        result = client.segment(b'fake_image')
        
        assert result == expected_response
        call_args = mock_post.call_args
        assert 'http://localhost:8002/api/v1/segmentar' in call_args[0]


class TestFactory:
    """Tests para factory y helpers."""

    @patch('api.services.segmentation.factory.settings')
    def test_get_segmentation_client_saliva(self, mock_settings):
        """Test obtener cliente de saliva."""
        mock_settings.SEGMENTATION_SERVICES = {
            'SALIVA': {
                'url': 'http://localhost:8001',
                'timeout': 30,
            }
        }
        
        client = get_segmentation_client('SALIVA')
        
        assert isinstance(client, SalivaSegmentationClient)
        assert client.base_url == 'http://localhost:8001'
        assert client.timeout == 30

    @patch('api.services.segmentation.factory.settings')
    def test_get_segmentation_client_sangre(self, mock_settings):
        """Test obtener cliente de sangre."""
        mock_settings.SEGMENTATION_SERVICES = {
            'SANGRE': {
                'url': 'http://localhost:8002',
                'timeout': 45,
            }
        }
        
        client = get_segmentation_client('SANGRE')
        
        assert isinstance(client, BloodSegmentationClient)
        assert client.base_url == 'http://localhost:8002'
        assert client.timeout == 45

    @patch('api.services.segmentation.factory.settings')
    def test_get_segmentation_client_case_insensitive(self, mock_settings):
        """Test que obtener cliente sea case-insensitive."""
        mock_settings.SEGMENTATION_SERVICES = {
            'SALIVA': {
                'url': 'http://localhost:8001',
                'timeout': 30,
            }
        }
        
        # Probar con lowercase
        client1 = get_segmentation_client('saliva')
        assert isinstance(client1, SalivaSegmentationClient)
        
        # Probar con mixedcase
        client2 = get_segmentation_client('SaLiVa')
        assert isinstance(client2, SalivaSegmentationClient)

    @patch('api.services.segmentation.factory.settings')
    def test_get_segmentation_client_not_found(self, mock_settings):
        """Test error cuando tipo no está configurado."""
        mock_settings.SEGMENTATION_SERVICES = {}
        
        with pytest.raises(SegmentationServiceError):
            get_segmentation_client('SALIVA')

    @patch.object(SalivaSegmentationClient, 'segment')
    @patch('api.services.segmentation.factory.settings')
    def test_segment_image_helper(self, mock_settings, mock_segment):
        """Test función helper segment_image."""
        mock_settings.SEGMENTATION_SERVICES = {
            'SALIVA': {
                'url': 'http://localhost:8001',
                'timeout': 30,
            }
        }
        
        expected_result = {
            'objetos': [
                {'id': 1, 'tipo': 'membrana', 'puntos': [[10, 20]]}
            ]
        }
        mock_segment.return_value = expected_result
        
        result = segment_image('SALIVA', b'fake_image', filename='test.jpg')
        
        assert result == expected_result
        mock_segment.assert_called_once()


class TestIntegration:
    """Tests de integración (requieren servicios reales)."""

    @pytest.mark.skip(reason="Requiere servicios reales ejecutándose")
    def test_real_segmentation_saliva(self):
        """Test con servicio real de saliva."""
        # Este test solo se ejecuta si servicios están corriendo
        client = SalivaSegmentationClient('http://localhost:8001', timeout=30)
        
        # Leer imagen de prueba
        with open('test_image.jpg', 'rb') as f:
            image_bytes = f.read()
        
        result = client.segment(image_bytes)
        
        assert 'objetos' in result
        assert isinstance(result['objetos'], list)

    @pytest.mark.skip(reason="Requiere servicios reales ejecutándose")
    def test_real_segmentation_blood(self):
        """Test con servicio real de sangre."""
        client = BloodSegmentationClient('http://localhost:8002', timeout=30)
        
        with open('test_image.jpg', 'rb') as f:
            image_bytes = f.read()
        
        result = client.segment(image_bytes)
        
        assert 'objetos' in result
        assert isinstance(result['objetos'], list)
