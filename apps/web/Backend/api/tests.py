import shutil
import tempfile
from copy import deepcopy
from datetime import date
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
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
from .services.segmentation.normalizers import normalize_segmentation_result
from .management.commands.seed_demo_data import (
    DEMO_IDENTIFICACION,
    DEMO_IMAGE_NAME,
)


class SeedDemoDataCommandTests(APITestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self.media_root)
        self.override.enable()

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.media_root, ignore_errors=True)

    def _call_command(self, **options):
        output = StringIO()
        call_command('seed_demo_data', stdout=output, **options)
        return output.getvalue()

    def _write_image(self, directory, filename, content=b'demo image bytes'):
        path = Path(directory) / filename
        path.write_bytes(content)
        return path

    def _get_demo_analisis(self):
        paciente = Paciente.objects.get(identificacion=DEMO_IDENTIFICACION)
        caso = Caso.objects.get(paciente=paciente)
        return AnalisisPred.objects.get(
            id_paciente_fk=paciente,
            id_caso_fk=caso,
        )

    def test_seed_demo_data_creates_minimum_flow(self):
        output = self._call_command()

        paciente = Paciente.objects.get(identificacion=DEMO_IDENTIFICACION)
        caso = Caso.objects.get(paciente=paciente)
        analisis = AnalisisPred.objects.get(
            id_paciente_fk=paciente,
            id_caso_fk=caso,
        )
        muestra = MuestraSaliva.objects.get(analisis=analisis)

        assert muestra.imagen.name
        assert muestra.imagen.storage.exists(muestra.imagen.name)
        assert 'Paciente creado' in output
        assert 'Muestras creadas: 1' in output

    def test_seed_demo_data_is_safe_to_run_twice(self):
        self._call_command()
        second_output = self._call_command()

        assert Paciente.objects.filter(identificacion=DEMO_IDENTIFICACION).count() == 1
        assert Caso.objects.count() == 1
        assert AnalisisPred.objects.count() == 1
        assert MuestraSaliva.objects.count() == 1
        assert 'Paciente existente' in second_output
        assert 'Muestras existentes: 1' in second_output

    def test_seed_demo_data_rejects_missing_image_path(self):
        missing_path = str(Path(self.media_root) / 'missing-demo-image.png')

        with self.assertRaises(CommandError):
            self._call_command(image_path=missing_path)

        assert not Paciente.objects.filter(
            identificacion=DEMO_IDENTIFICACION
        ).exists()

    def test_seed_demo_data_does_not_delete_existing_data(self):
        existing = Paciente.objects.create(
            nombre='Paciente',
            apellido='Existente',
            fecha_nacimiento=date(1985, 5, 20),
            identificacion='NO-BORRAR-001',
        )

        self._call_command()

        assert Paciente.objects.filter(pk=existing.pk).exists()
        assert Paciente.objects.filter(identificacion=DEMO_IDENTIFICACION).exists()

    def test_seed_demo_data_image_dir_creates_multiple_muestras(self):
        image_dir = Path(self.media_root) / 'source-images'
        image_dir.mkdir()
        self._write_image(image_dir, 'b.png')
        self._write_image(image_dir, 'a.jpg')
        self._write_image(image_dir, 'c.tiff')

        output = self._call_command(image_dir=str(image_dir))

        analisis = self._get_demo_analisis()
        image_names = sorted(
            Path(muestra.imagen.name).name
            for muestra in MuestraSaliva.objects.filter(analisis=analisis)
        )
        assert image_names == ['a.jpg', 'b.png', 'c.tiff']
        assert 'Muestras creadas: 3' in output

    def test_seed_demo_data_image_dir_second_run_does_not_duplicate(self):
        image_dir = Path(self.media_root) / 'source-images'
        image_dir.mkdir()
        self._write_image(image_dir, 'a.jpg')
        self._write_image(image_dir, 'b.png')

        self._call_command(image_dir=str(image_dir))
        output = self._call_command(image_dir=str(image_dir))

        assert MuestraSaliva.objects.count() == 2
        assert 'Muestras creadas: 0' in output
        assert 'Muestras existentes: 2' in output

    def test_seed_demo_data_image_dir_new_file_creates_only_new_muestra(self):
        image_dir = Path(self.media_root) / 'source-images'
        image_dir.mkdir()
        self._write_image(image_dir, 'a.jpg')
        self._write_image(image_dir, 'b.png')

        self._call_command(image_dir=str(image_dir))
        self._write_image(image_dir, 'c.tif')
        output = self._call_command(image_dir=str(image_dir))

        assert MuestraSaliva.objects.count() == 3
        assert 'Muestras creadas: 1' in output
        assert 'Muestras existentes: 2' in output

    def test_seed_demo_data_rejects_missing_image_dir(self):
        missing_dir = str(Path(self.media_root) / 'missing-dir')

        with self.assertRaises(CommandError):
            self._call_command(image_dir=missing_dir)

        assert not Paciente.objects.filter(
            identificacion=DEMO_IDENTIFICACION
        ).exists()

    def test_seed_demo_data_empty_image_dir_does_not_break(self):
        image_dir = Path(self.media_root) / 'empty-source'
        image_dir.mkdir()

        output = self._call_command(image_dir=str(image_dir))

        assert Paciente.objects.filter(identificacion=DEMO_IDENTIFICACION).exists()
        assert MuestraSaliva.objects.count() == 0
        assert 'Muestras creadas: 0' in output
        assert 'Archivos ignorados: 0' in output

    def test_seed_demo_data_unsupported_file_is_ignored(self):
        image_dir = Path(self.media_root) / 'source-images'
        image_dir.mkdir()
        self._write_image(image_dir, 'notes.txt')

        output = self._call_command(image_dir=str(image_dir))

        assert MuestraSaliva.objects.count() == 0
        assert 'Archivos ignorados: 1' in output

    def test_seed_demo_data_image_option_still_works(self):
        image_path = self._write_image(self.media_root, 'single.jpeg')

        output = self._call_command(image_path=str(image_path))

        muestra = MuestraSaliva.objects.get()
        assert Path(muestra.imagen.name).name == 'single.jpeg'
        assert 'Muestras creadas: 1' in output

    def test_seed_demo_data_image_and_image_dir_are_deduplicated_by_basename(self):
        image_dir = Path(self.media_root) / 'source-images'
        image_dir.mkdir()
        image_path = self._write_image(self.media_root, 'same.png')
        self._write_image(image_dir, 'same.png')
        self._write_image(image_dir, 'other.png')

        output = self._call_command(
            image_path=str(image_path),
            image_dir=str(image_dir),
        )

        image_names = sorted(
            Path(muestra.imagen.name).name
            for muestra in MuestraSaliva.objects.all()
        )
        assert image_names == ['other.png', 'same.png']
        assert 'Muestras creadas: 2' in output
        assert 'Archivos ignorados: 1' in output

    def test_seed_demo_data_deduplicates_synthetic_image_by_basename(self):
        self._call_command()
        muestra = MuestraSaliva.objects.get()

        assert Path(muestra.imagen.name).name == DEMO_IMAGE_NAME


class SegmentationResultNormalizerTests(APITestCase):
    def test_normalizer_calculates_total_objects_and_counts_by_label(self):
        raw_result = {
            'objetos': [
                {'id': 1, 'tipo': 'membrana', 'puntos': [[10, 20]]},
                {'id': 2, 'tipo': 'nucleo', 'puntos': [[30, 40]]},
                {'id': 3, 'tipo': 'membrana', 'puntos': [[50, 60]]},
            ]
        }

        result = normalize_segmentation_result(raw_result, sample_type='SALIVA')

        assert result['version'] == '1.1'
        assert result['sample_type'] == 'SALIVA'
        assert result['summary']['total_objects'] == 3
        assert result['summary']['counts_by_label'] == {
            'membrana': 2,
            'nucleo': 1,
        }

    def test_normalizer_uses_unique_sequential_ids_and_preserves_raw_ids(self):
        raw_result = {
            'objetos': [
                {'id': 255, 'tipo': 'nucleo', 'puntos': [[10, 20]]},
                {'id': 255, 'tipo': 'nucleo', 'puntos': [[30, 40]]},
                {'id': 255, 'tipo': 'micronucleo', 'puntos': [[50, 60]]},
            ]
        }

        result = normalize_segmentation_result(raw_result, sample_type='SALIVA')
        normalized_objects = result['objects']

        assert [obj['id'] for obj in normalized_objects] == [1, 2, 3]
        assert len({obj['id'] for obj in normalized_objects}) == 3
        assert [obj['source']['raw_id'] for obj in normalized_objects] == [
            255,
            255,
            255,
        ]
        assert [obj['source']['raw_type'] for obj in normalized_objects] == [
            'nucleo',
            'nucleo',
            'micronucleo',
        ]

    def test_normalizer_preserves_summary_when_raw_ids_are_duplicated(self):
        raw_result = {
            'objetos': [
                {'id': 255, 'tipo': 'membrana', 'puntos': []},
                {'id': 255, 'tipo': 'membrana', 'puntos': []},
                {'id': 255, 'tipo': 'nucleo', 'puntos': []},
                {'id': 255, 'tipo': 'micronucleo', 'puntos': []},
            ]
        }

        result = normalize_segmentation_result(raw_result, sample_type='SALIVA')

        assert result['summary']['total_objects'] == 4
        assert result['summary']['counts_by_label'] == {
            'membrana': 2,
            'nucleo': 1,
            'micronucleo': 1,
        }

    def test_normalizer_does_not_mutate_raw_result(self):
        raw_result = {
            'objetos': [
                {'id': 255, 'tipo': 'nucleo', 'puntos': [[10, 20]]}
            ]
        }
        original = deepcopy(raw_result)

        normalize_segmentation_result(raw_result, sample_type='SALIVA')

        assert raw_result == original

    def test_normalizer_without_objects_returns_empty_objects(self):
        result = normalize_segmentation_result({}, sample_type='SALIVA')

        assert result['objects'] == []
        assert result['summary']['total_objects'] == 0
        assert result['summary']['counts_by_label'] == {}

    def test_normalizer_keeps_incomplete_object_without_geometry(self):
        raw_result = {
            'objetos': [
                {'id': 1, 'tipo': 'membrana'}
            ]
        }

        result = normalize_segmentation_result(raw_result, sample_type='SALIVA')

        assert result['objects'][0]['id'] == 1
        assert result['objects'][0]['label'] == 'membrana'
        assert result['objects'][0]['geometry'] is None
        assert result['objects'][0]['source']['raw_id'] == 1
        assert result['objects'][0]['source']['raw_type'] == 'membrana'
        assert result['summary']['total_objects'] == 1

    def test_normalizer_requires_dict_raw_result(self):
        try:
            normalize_segmentation_result([], sample_type='SALIVA')
        except ValueError as exc:
            assert 'objeto JSON' in str(exc)
        else:
            raise AssertionError('normalize_segmentation_result must fail')


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
        assert response.data['resultado_normalizado']['version'] == '1.1'
        assert response.data['resultado_normalizado']['sample_type'] == 'SALIVA'
        assert response.data['resultado_normalizado']['summary'] == {
            'total_objects': 1,
            'counts_by_label': {'membrana': 1},
        }
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
        assert resultado.resultado_normalizado['version'] == '1.1'
        assert resultado.resultado_normalizado == response.data['resultado_normalizado']

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

    @patch('api.views.segment_image')
    def test_segmentar_muestra_without_objects_persists_empty_normalized_result(
        self,
        mock_segment_image
    ):
        muestra = self._create_muestra()
        mock_segment_image.return_value = {}

        response = self.client.post(self._url(muestra.id_muestra))

        assert response.status_code == status.HTTP_200_OK
        assert response.data['resultado_normalizado']['objects'] == []
        assert response.data['resultado_normalizado']['summary']['total_objects'] == 0

        resultado = ResultadoSegmentacion.objects.get(muestra=muestra)
        assert resultado.respuesta_json == {}
        assert resultado.resultado_normalizado['objects'] == []

    @patch('api.views.segment_image')
    def test_segmentar_muestra_incomplete_object_does_not_break_normalization(
        self,
        mock_segment_image
    ):
        muestra = self._create_muestra()
        mock_segment_image.return_value = {
            'objetos': [
                {'id': 1, 'tipo': 'membrana'}
            ]
        }

        response = self.client.post(self._url(muestra.id_muestra))

        assert response.status_code == status.HTTP_200_OK
        normalized_object = response.data['resultado_normalizado']['objects'][0]
        assert normalized_object['label'] == 'membrana'
        assert normalized_object['geometry'] is None

    @patch('api.views.segment_image')
    def test_segmentar_muestra_invalid_raw_result_does_not_create_result(
        self,
        mock_segment_image
    ):
        muestra = self._create_muestra()
        mock_segment_image.return_value = []

        response = self.client.post(self._url(muestra.id_muestra))

        assert response.status_code == status.HTTP_502_BAD_GATEWAY
        assert 'error' in response.data
        assert ResultadoSegmentacion.objects.count() == 0

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
            resultado_normalizado={
                'version': '1.0',
                'sample_type': 'SALIVA',
                'objects': [
                    {
                        'id': 1,
                        'label': 'membrana',
                        'geometry': {
                            'type': 'polygon',
                            'points': [[10, 20]],
                        },
                        'source': {
                            'raw_type': 'membrana',
                        },
                    }
                ],
                'summary': {
                    'total_objects': 1,
                    'counts_by_label': {
                        'membrana': 1,
                    },
                },
            },
        )

        response = self.client.get(self._url(muestra.id_muestra))

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]['id'] == resultado.id_resultado_segmentacion
        assert response.data[0]['tipo_muestra'] == 'SALIVA'
        assert response.data[0]['estado'] == 'COMPLETADO'
        assert response.data[0]['respuesta_json'] == resultado.respuesta_json
        assert (
            response.data[0]['resultado_normalizado']
            == resultado.resultado_normalizado
        )
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


class CasoSegmentationSummaryTests(APITestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self.media_root)
        self.override.enable()

        self.paciente = Paciente.objects.create(
            nombre='Paciente',
            apellido='Resumen',
            fecha_nacimiento=date(1990, 1, 1),
            identificacion='PAC-SUM-001',
        )
        self.caso = Caso.objects.create(
            paciente=self.paciente,
            titulo='Caso resumen',
        )
        self.analisis = AnalisisPred.objects.create(
            id_paciente_fk=self.paciente,
            id_caso_fk=self.caso,
        )

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.media_root, ignore_errors=True)

    def _url(self, caso_id=None):
        return reverse(
            'caso-resumen-segmentacion',
            kwargs={'pk': caso_id or self.caso.id_caso}
        )

    def _create_muestra(self, filename='sample.jpg'):
        return MuestraSaliva.objects.create(
            analisis=self.analisis,
            imagen=SimpleUploadedFile(
                filename,
                b'fake image bytes',
                content_type='image/jpeg',
            ),
        )

    def _normalized_result(self, counts=None, total=None, version='1.1'):
        counts = counts or {}
        if total is None:
            total = sum(counts.values())

        return {
            'version': version,
            'sample_type': 'SALIVA',
            'objects': [],
            'summary': {
                'total_objects': total,
                'counts_by_label': counts,
            },
        }

    def _create_result(
        self,
        muestra,
        *,
        estado='COMPLETADO',
        counts=None,
        total=None,
        normalized=None,
        version='1.1'
    ):
        if normalized is None:
            normalized = self._normalized_result(
                counts=counts,
                total=total,
                version=version,
            )

        return ResultadoSegmentacion.objects.create(
            muestra=muestra,
            tipo_muestra='SALIVA',
            estado=estado,
            respuesta_json={'objetos': []},
            resultado_normalizado=normalized,
        )

    def _assert_invariant(self, data):
        assert (
            data['muestras_segmentadas']
            + data['muestras_pendientes']
            + data['muestras_resultado_invalido']
            == data['total_muestras']
        )

    def test_resumen_segmentacion_not_found(self):
        response = self.client.get(self._url(999999))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_resumen_segmentacion_case_without_samples(self):
        response = self.client.get(self._url())

        assert response.status_code == status.HTTP_200_OK
        assert response.data == {
            'caso_id': self.caso.id_caso,
            'total_muestras': 0,
            'muestras_segmentadas': 0,
            'muestras_pendientes': 0,
            'muestras_resultado_invalido': 0,
            'counts_by_label': {
                'membrana': 0,
                'nucleo': 0,
                'micronucleo': 0,
            },
            'total_objects': 0,
        }

    def test_resumen_segmentacion_samples_without_results_are_pending(self):
        self._create_muestra('one.jpg')
        self._create_muestra('two.jpg')

        response = self.client.get(self._url())

        assert response.status_code == status.HTTP_200_OK
        assert response.data['total_muestras'] == 2
        assert response.data['muestras_segmentadas'] == 0
        assert response.data['muestras_pendientes'] == 2
        assert response.data['muestras_resultado_invalido'] == 0
        self._assert_invariant(response.data)

    def test_resumen_segmentacion_one_valid_completed_sample(self):
        muestra = self._create_muestra()
        self._create_result(
            muestra,
            counts={'membrana': 3, 'nucleo': 2, 'micronucleo': 1},
        )

        response = self.client.get(self._url())

        assert response.status_code == status.HTTP_200_OK
        assert response.data['muestras_segmentadas'] == 1
        assert response.data['muestras_pendientes'] == 0
        assert response.data['muestras_resultado_invalido'] == 0
        assert response.data['counts_by_label'] == {
            'membrana': 3,
            'nucleo': 2,
            'micronucleo': 1,
        }
        assert response.data['total_objects'] == 6
        self._assert_invariant(response.data)

    def test_resumen_segmentacion_aggregates_multiple_valid_samples(self):
        first = self._create_muestra('first.jpg')
        second = self._create_muestra('second.jpg')
        self._create_result(first, counts={'membrana': 3, 'nucleo': 2})
        self._create_result(second, counts={'membrana': 4, 'micronucleo': 5})

        response = self.client.get(self._url())

        assert response.status_code == status.HTTP_200_OK
        assert response.data['muestras_segmentadas'] == 2
        assert response.data['counts_by_label'] == {
            'membrana': 7,
            'nucleo': 2,
            'micronucleo': 5,
        }
        assert response.data['total_objects'] == 14
        self._assert_invariant(response.data)

    def test_resumen_segmentacion_uses_only_latest_completed_per_sample(self):
        muestra = self._create_muestra()
        self._create_result(muestra, counts={'membrana': 100})
        self._create_result(muestra, counts={'membrana': 1, 'nucleo': 2})

        response = self.client.get(self._url())

        assert response.status_code == status.HTTP_200_OK
        assert response.data['counts_by_label'] == {
            'membrana': 1,
            'nucleo': 2,
            'micronucleo': 0,
        }
        assert response.data['total_objects'] == 3

    def test_resumen_segmentacion_uses_previous_completed_when_latest_is_error(self):
        muestra = self._create_muestra()
        self._create_result(muestra, counts={'nucleo': 4})
        self._create_result(
            muestra,
            estado='ERROR',
            counts={'nucleo': 999},
        )

        response = self.client.get(self._url())

        assert response.status_code == status.HTTP_200_OK
        assert response.data['muestras_segmentadas'] == 1
        assert response.data['counts_by_label']['nucleo'] == 4
        assert response.data['total_objects'] == 4

    def test_resumen_segmentacion_latest_completed_invalid_does_not_fallback(self):
        muestra = self._create_muestra()
        self._create_result(muestra, counts={'membrana': 5})
        self._create_result(
            muestra,
            normalized={
                'version': '1.1',
                'summary': None,
            },
        )

        response = self.client.get(self._url())

        assert response.status_code == status.HTTP_200_OK
        assert response.data['muestras_segmentadas'] == 0
        assert response.data['muestras_resultado_invalido'] == 1
        assert response.data['counts_by_label'] == {
            'membrana': 0,
            'nucleo': 0,
            'micronucleo': 0,
        }
        self._assert_invariant(response.data)

    def test_resumen_segmentacion_accepts_valid_version_1_0(self):
        muestra = self._create_muestra()
        self._create_result(
            muestra,
            counts={'micronucleo': 3},
            version='1.0',
        )

        response = self.client.get(self._url())

        assert response.status_code == status.HTTP_200_OK
        assert response.data['muestras_segmentadas'] == 1
        assert response.data['counts_by_label']['micronucleo'] == 3

    def test_resumen_segmentacion_accepts_valid_version_1_1(self):
        muestra = self._create_muestra()
        self._create_result(
            muestra,
            counts={'membrana': 2},
            version='1.1',
        )

        response = self.client.get(self._url())

        assert response.status_code == status.HTTP_200_OK
        assert response.data['muestras_segmentadas'] == 1
        assert response.data['counts_by_label']['membrana'] == 2

    def test_resumen_segmentacion_missing_label_defaults_to_zero(self):
        muestra = self._create_muestra()
        self._create_result(muestra, counts={'membrana': 2})

        response = self.client.get(self._url())

        assert response.status_code == status.HTTP_200_OK
        assert response.data['counts_by_label'] == {
            'membrana': 2,
            'nucleo': 0,
            'micronucleo': 0,
        }

    def test_resumen_segmentacion_calculates_missing_total_objects(self):
        muestra = self._create_muestra()
        self._create_result(
            muestra,
            normalized={
                'version': '1.0',
                'summary': {
                    'counts_by_label': {
                        'membrana': 2,
                        'nucleo': 3,
                    },
                },
            },
        )

        response = self.client.get(self._url())

        assert response.status_code == status.HTTP_200_OK
        assert response.data['muestras_segmentadas'] == 1
        assert response.data['total_objects'] == 5
        assert response.data['counts_by_label'] == {
            'membrana': 2,
            'nucleo': 3,
            'micronucleo': 0,
        }

    def test_resumen_segmentacion_invalid_summary_does_not_break_endpoint(self):
        muestra = self._create_muestra()
        self._create_result(
            muestra,
            normalized={
                'version': '1.1',
                'summary': 'invalid',
            },
        )

        response = self.client.get(self._url())

        assert response.status_code == status.HTTP_200_OK
        assert response.data['muestras_resultado_invalido'] == 1
        assert response.data['total_objects'] == 0
        self._assert_invariant(response.data)

    def test_resumen_segmentacion_non_numeric_counts_are_invalid(self):
        muestra = self._create_muestra()
        self._create_result(
            muestra,
            normalized=self._normalized_result(
                counts={'membrana': 'many'},
                total=1,
            ),
        )

        response = self.client.get(self._url())

        assert response.status_code == status.HTTP_200_OK
        assert response.data['muestras_segmentadas'] == 0
        assert response.data['muestras_resultado_invalido'] == 1
        self._assert_invariant(response.data)

    def test_resumen_segmentacion_incoherent_total_objects_is_invalid(self):
        muestra = self._create_muestra()
        self._create_result(
            muestra,
            counts={'membrana': 2},
            total=5,
        )

        response = self.client.get(self._url())

        assert response.status_code == status.HTTP_200_OK
        assert response.data['muestras_resultado_invalido'] == 1
        assert response.data['total_objects'] == 0
        self._assert_invariant(response.data)
