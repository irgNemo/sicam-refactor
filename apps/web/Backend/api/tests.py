import shutil
import tempfile
from datetime import date
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import (
    AnalisisPred,
    Caso,
    MuestraSaliva,
    Paciente,
    ResultadoSegmentacion,
)
from .services.segmentation.exceptions import (
    InvalidSegmentationResponseError,
    SegmentationConnectionError,
    SegmentationServiceError,
    SegmentationTimeoutError,
)


class MuestraSalivaSegmentationEndpointTests(APITestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self.media_root)
        self.override.enable()

        self.paciente = Paciente.objects.create(
            nombre='Paciente',
            apellido='Prueba',
            fecha_nacimiento=date(1990, 1, 1),
            identificacion='PAC-001',
        )
        self.caso = Caso.objects.create(
            paciente=self.paciente,
            titulo='Caso prueba',
        )
        self.analisis = AnalisisPred.objects.create(
            id_paciente_fk=self.paciente,
            id_caso_fk=self.caso,
        )

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.media_root, ignore_errors=True)

    def _create_muestra(self, content=b'fake image bytes'):
        return MuestraSaliva.objects.create(
            analisis=self.analisis,
            imagen=SimpleUploadedFile(
                'sample.jpg',
                content,
                content_type='image/jpeg',
            ),
        )

    def _url(self, muestra_id):
        return reverse('muestra-segmentar', kwargs={'pk': muestra_id})

    @patch('api.views.segment_image')
    def test_segmentar_muestra_success(self, mock_segment_image):
        muestra = self._create_muestra()
        expected_response = {
            'objetos': [
                {'id': 1, 'tipo': 'membrana', 'puntos': [[10, 20]]}
            ]
        }
        mock_segment_image.return_value = expected_response

        response = self.client.post(self._url(muestra.id_muestra))

        assert response.status_code == status.HTTP_200_OK
        assert response.data['objetos'] == expected_response['objetos']
        assert response.data['resultado_segmentacion']['estado'] == 'COMPLETADO'
        assert response.data['resultado_segmentacion']['tipo_muestra'] == 'SALIVA'
        mock_segment_image.assert_called_once()
        sample_type, image_bytes = mock_segment_image.call_args.args[:2]
        assert sample_type == 'SALIVA'
        assert image_bytes == b'fake image bytes'
        assert mock_segment_image.call_args.kwargs['filename'].endswith('.jpg')

        resultado = ResultadoSegmentacion.objects.get(muestra=muestra)
        assert resultado.tipo_muestra == 'SALIVA'
        assert resultado.estado == 'COMPLETADO'
        assert resultado.respuesta_json == expected_response

    @patch('api.views.segment_image')
    def test_segmentar_muestra_repeated_success_creates_new_result(
        self,
        mock_segment_image
    ):
        muestra = self._create_muestra()
        mock_segment_image.return_value = {
            'objetos': [
                {'id': 1, 'tipo': 'membrana', 'puntos': [[10, 20]]}
            ]
        }

        first_response = self.client.post(self._url(muestra.id_muestra))
        second_response = self.client.post(self._url(muestra.id_muestra))

        assert first_response.status_code == status.HTTP_200_OK
        assert second_response.status_code == status.HTTP_200_OK
        assert ResultadoSegmentacion.objects.filter(muestra=muestra).count() == 2
        assert (
            first_response.data['resultado_segmentacion']['id']
            != second_response.data['resultado_segmentacion']['id']
        )

    def test_segmentar_muestra_not_found(self):
        response = self.client.post(self._url(999999))

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert ResultadoSegmentacion.objects.count() == 0

    @patch('api.views.segment_image')
    def test_segmentar_muestra_without_image(self, mock_segment_image):
        muestra = MuestraSaliva.objects.create(
            analisis=self.analisis,
            imagen='',
        )

        response = self.client.post(self._url(muestra.id_muestra))

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data
        mock_segment_image.assert_not_called()
        assert ResultadoSegmentacion.objects.count() == 0

    @patch('api.views.segment_image')
    def test_segmentar_muestra_timeout(self, mock_segment_image):
        muestra = self._create_muestra()
        mock_segment_image.side_effect = SegmentationTimeoutError('timeout')

        response = self.client.post(self._url(muestra.id_muestra))

        assert response.status_code == status.HTTP_504_GATEWAY_TIMEOUT
        assert 'error' in response.data
        assert ResultadoSegmentacion.objects.count() == 0

    @patch('api.views.segment_image')
    def test_segmentar_muestra_connection_error(self, mock_segment_image):
        muestra = self._create_muestra()
        mock_segment_image.side_effect = SegmentationConnectionError('down')

        response = self.client.post(self._url(muestra.id_muestra))

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert 'error' in response.data
        assert ResultadoSegmentacion.objects.count() == 0

    @patch('api.views.segment_image')
    def test_segmentar_muestra_invalid_response(self, mock_segment_image):
        muestra = self._create_muestra()
        mock_segment_image.side_effect = InvalidSegmentationResponseError(
            'invalid'
        )

        response = self.client.post(self._url(muestra.id_muestra))

        assert response.status_code == status.HTTP_502_BAD_GATEWAY
        assert 'error' in response.data
        assert ResultadoSegmentacion.objects.count() == 0

    @patch('api.views.segment_image')
    def test_segmentar_muestra_service_error(self, mock_segment_image):
        muestra = self._create_muestra()
        mock_segment_image.side_effect = SegmentationServiceError('service')

        response = self.client.post(self._url(muestra.id_muestra))

        assert response.status_code == status.HTTP_502_BAD_GATEWAY
        assert 'error' in response.data
        assert ResultadoSegmentacion.objects.count() == 0


class MuestraSalivaSegmentationResultsReadTests(APITestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self.media_root)
        self.override.enable()

        self.paciente = Paciente.objects.create(
            nombre='Paciente',
            apellido='Lectura',
            fecha_nacimiento=date(1990, 1, 1),
            identificacion='PAC-READ-001',
        )
        self.caso = Caso.objects.create(
            paciente=self.paciente,
            titulo='Caso lectura',
        )
        self.analisis = AnalisisPred.objects.create(
            id_paciente_fk=self.paciente,
            id_caso_fk=self.caso,
        )

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.media_root, ignore_errors=True)

    def _create_muestra(self):
        return MuestraSaliva.objects.create(
            analisis=self.analisis,
            imagen=SimpleUploadedFile(
                'sample.jpg',
                b'fake image bytes',
                content_type='image/jpeg',
            ),
        )

    def _url(self, muestra_id):
        return reverse(
            'muestra-resultados-segmentacion',
            kwargs={'pk': muestra_id}
        )

    def test_resultados_segmentacion_empty_list(self):
        muestra = self._create_muestra()

        response = self.client.get(self._url(muestra.id_muestra))

        assert response.status_code == status.HTTP_200_OK
        assert response.data == []

    def test_resultados_segmentacion_returns_saved_results(self):
        muestra = self._create_muestra()
        resultado = ResultadoSegmentacion.objects.create(
            muestra=muestra,
            tipo_muestra='SALIVA',
            estado='COMPLETADO',
            respuesta_json={
                'objetos': [
                    {'id': 1, 'tipo': 'membrana', 'puntos': [[10, 20]]}
                ]
            },
        )

        response = self.client.get(self._url(muestra.id_muestra))

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]['id'] == resultado.id_resultado_segmentacion
        assert response.data[0]['tipo_muestra'] == 'SALIVA'
        assert response.data[0]['estado'] == 'COMPLETADO'
        assert response.data[0]['respuesta_json'] == resultado.respuesta_json
        assert 'creado_en' in response.data[0]
        assert 'actualizado_en' in response.data[0]

    def test_resultados_segmentacion_orders_newest_first(self):
        muestra = self._create_muestra()
        first_result = ResultadoSegmentacion.objects.create(
            muestra=muestra,
            tipo_muestra='SALIVA',
            estado='COMPLETADO',
            respuesta_json={'objetos': [{'id': 1}]},
        )
        second_result = ResultadoSegmentacion.objects.create(
            muestra=muestra,
            tipo_muestra='SALIVA',
            estado='COMPLETADO',
            respuesta_json={'objetos': [{'id': 2}]},
        )

        response = self.client.get(self._url(muestra.id_muestra))

        assert response.status_code == status.HTTP_200_OK
        assert response.data[0]['id'] == second_result.id_resultado_segmentacion
        assert response.data[1]['id'] == first_result.id_resultado_segmentacion

    def test_resultados_segmentacion_not_found(self):
        response = self.client.get(self._url(999999))

        assert response.status_code == status.HTTP_404_NOT_FOUND
