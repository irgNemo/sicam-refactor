import shutil
import tempfile
import json
from copy import deepcopy
from datetime import date
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.db import IntegrityError, transaction
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
    RevisionSegmentacion,
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



class RevisionSegmentacionTests(APITestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self.media_root)
        self.override.enable()

        self.paciente = Paciente.objects.create(
            nombre='Paciente',
            apellido='Revision',
            fecha_nacimiento=date(1991, 3, 10),
            identificacion='PAC-REV-001',
        )
        self.caso = Caso.objects.create(
            paciente=self.paciente,
            titulo='Caso revision',
        )
        self.analisis = AnalisisPred.objects.create(
            id_paciente_fk=self.paciente,
            id_caso_fk=self.caso,
        )
        self.muestra = MuestraSaliva.objects.create(
            analisis=self.analisis,
            imagen=SimpleUploadedFile(
                'revision.jpg',
                b'fake image bytes',
                content_type='image/jpeg',
            ),
        )
        self.resultado = self._create_resultado()

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.media_root, ignore_errors=True)

    def _resultado_revisiones_url(self, resultado_id=None):
        return reverse(
            'resultado-segmentacion-revisiones',
            kwargs={
                'pk': resultado_id or self.resultado.id_resultado_segmentacion
            }
        )

    def _revision_url(self, revision_id):
        return reverse(
            'revision-segmentacion-detail',
            kwargs={'pk': revision_id}
        )

    def _validar_url(self, revision_id):
        return reverse(
            'revision-segmentacion-validar',
            kwargs={'pk': revision_id}
        )

    def _normalized(self, version='1.1'):
        return {
            'version': version,
            'sample_type': 'SALIVA',
            'objects': [
                {
                    'id': 1,
                    'label': 'membrana',
                    'geometry': {
                        'type': 'polygon',
                        'points': [[0, 0], [10, 0], [10, 10]],
                    },
                    'source': {
                        'raw_id': 255,
                        'raw_type': 'membrana',
                    },
                },
                {
                    'id': 2,
                    'label': 'nucleo',
                    'geometry': {
                        'type': 'polygon',
                        'points': [[1, 1], [5, 1], [5, 5]],
                    },
                    'source': {
                        'raw_id': 255,
                        'raw_type': 'nucleo',
                    },
                },
            ],
            'summary': {
                'total_objects': 2,
                'counts_by_label': {
                    'membrana': 1,
                    'nucleo': 1,
                },
            },
        }

    def _create_resultado(self, normalized=None):
        return ResultadoSegmentacion.objects.create(
            muestra=self.muestra,
            tipo_muestra='SALIVA',
            respuesta_json={'objetos': [{'id': 255}]},
            resultado_normalizado=normalized or self._normalized(),
            estado='COMPLETADO',
        )

    def _create_draft(self):
        response = self.client.post(self._resultado_revisiones_url())
        assert response.status_code == status.HTTP_201_CREATED
        return RevisionSegmentacion.objects.get(
            pk=response.data['id_revision_segmentacion']
        )

    def _manual_object(self, object_id=3, label='micronucleo'):
        return {
            'id': object_id,
            'label': label,
            'geometry': {
                'type': 'polygon',
                'points': [[2, 2], [6, 2], [6, 6]],
            },
            'provenance': {
                'origin': 'manual',
                'base_object_id': None,
            },
        }

    def _patch_snapshot(self, revision, snapshot):
        return self.client.patch(
            self._revision_url(revision.id_revision_segmentacion),
            {'resultado_editado': snapshot},
            format='json',
        )

    def test_model_unique_revision_number_per_resultado(self):
        draft = self._create_draft()

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                RevisionSegmentacion.objects.create(
                    resultado_segmentacion=self.resultado,
                    numero_revision=draft.numero_revision,
                    estado=RevisionSegmentacion.ESTADO_VALIDADA,
                    resultado_editado=draft.resultado_editado,
                    resumen=draft.resumen,
                )

    def test_model_unique_active_draft_per_resultado(self):
        draft = self._create_draft()

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                RevisionSegmentacion.objects.create(
                    resultado_segmentacion=self.resultado,
                    numero_revision=2,
                    estado=RevisionSegmentacion.ESTADO_BORRADOR,
                    resultado_editado=draft.resultado_editado,
                    resumen=draft.resumen,
                )

    def test_revision_has_valid_state_and_timestamps(self):
        revision = self._create_draft()

        assert revision.estado == RevisionSegmentacion.ESTADO_BORRADOR
        assert revision.creado_en is not None
        assert revision.actualizado_en is not None
        assert revision.validado_en is None

    def test_first_draft_is_created_from_automatic_result(self):
        revision = self._create_draft()

        assert revision.numero_revision == 1
        assert revision.resultado_editado['version'] == '1.0'
        assert (
            revision.resultado_editado['base_result_id']
            == self.resultado.id_resultado_segmentacion
        )
        assert revision.resultado_editado['objects'][0]['id'] == 1
        assert revision.resultado_editado['objects'][0]['provenance'] == {
            'origin': 'automatic',
            'base_object_id': 1,
        }
        assert revision.resumen == {
            'counts_by_label': {
                'membrana': 1,
                'nucleo': 1,
                'micronucleo': 0,
            },
            'total_objects': 2,
        }

    def test_create_draft_twice_returns_same_active_draft(self):
        first = self.client.post(self._resultado_revisiones_url())
        second = self.client.post(self._resultado_revisiones_url())

        assert first.status_code == status.HTTP_201_CREATED
        assert second.status_code == status.HTTP_200_OK
        assert (
            first.data['id_revision_segmentacion']
            == second.data['id_revision_segmentacion']
        )
        assert RevisionSegmentacion.objects.count() == 1

    def test_automatic_original_remains_intact_when_draft_is_created(self):
        original_raw = deepcopy(self.resultado.respuesta_json)
        original_normalized = deepcopy(self.resultado.resultado_normalizado)

        self._create_draft()
        self.resultado.refresh_from_db()

        assert self.resultado.respuesta_json == original_raw
        assert self.resultado.resultado_normalizado == original_normalized

    def test_validating_revision_one_allows_revision_two_from_validated(self):
        revision_one = self._create_draft()
        edited = deepcopy(revision_one.resultado_editado)
        edited['objects'].append(self._manual_object())

        patch_response = self._patch_snapshot(revision_one, edited)
        assert patch_response.status_code == status.HTTP_200_OK

        validate_response = self.client.post(
            self._validar_url(revision_one.id_revision_segmentacion)
        )
        assert validate_response.status_code == status.HTTP_200_OK

        second_response = self.client.post(self._resultado_revisiones_url())
        assert second_response.status_code == status.HTTP_201_CREATED
        assert second_response.data['numero_revision'] == 2
        assert len(second_response.data['resultado_editado']['objects']) == 3
        assert second_response.data['resumen']['counts_by_label'] == {
            'membrana': 1,
            'nucleo': 1,
            'micronucleo': 1,
        }

    def test_patch_valid_draft_recalculates_summary_and_ignores_client_summary(self):
        revision = self._create_draft()
        edited = deepcopy(revision.resultado_editado)
        edited['objects'].append(self._manual_object())

        response = self.client.patch(
            self._revision_url(revision.id_revision_segmentacion),
            {
                'resultado_editado': edited,
                'resumen': {
                    'counts_by_label': {'membrana': 999},
                    'total_objects': 999,
                },
            },
            format='json',
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['resumen'] == {
            'counts_by_label': {
                'membrana': 1,
                'nucleo': 1,
                'micronucleo': 1,
            },
            'total_objects': 3,
        }

    def test_valid_manual_and_automatic_provenance_are_accepted(self):
        revision = self._create_draft()
        edited = deepcopy(revision.resultado_editado)
        edited['objects'].append(self._manual_object())

        response = self._patch_snapshot(revision, edited)

        assert response.status_code == status.HTTP_200_OK

    def test_patch_rejects_invalid_label(self):
        revision = self._create_draft()
        edited = deepcopy(revision.resultado_editado)
        edited['objects'][0]['label'] = 'plaqueta'

        response = self._patch_snapshot(revision, edited)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_patch_rejects_duplicate_ids(self):
        revision = self._create_draft()
        edited = deepcopy(revision.resultado_editado)
        edited['objects'][1]['id'] = edited['objects'][0]['id']

        response = self._patch_snapshot(revision, edited)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_patch_rejects_polygon_with_less_than_three_points(self):
        revision = self._create_draft()
        edited = deepcopy(revision.resultado_editado)
        edited['objects'][0]['geometry']['points'] = [[0, 0], [1, 1]]

        response = self._patch_snapshot(revision, edited)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_patch_rejects_non_numeric_point(self):
        revision = self._create_draft()
        edited = deepcopy(revision.resultado_editado)
        edited['objects'][0]['geometry']['points'][0] = ['x', 0]

        response = self._patch_snapshot(revision, edited)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_patch_rejects_nan_and_infinity(self):
        revision = self._create_draft()

        for invalid_value in [float('nan'), float('inf')]:
            edited = deepcopy(revision.resultado_editado)
            edited['objects'][0]['geometry']['points'][0] = [invalid_value, 0]

            response = self.client.generic(
                'PATCH',
                self._revision_url(revision.id_revision_segmentacion),
                data=json.dumps({'resultado_editado': edited}, allow_nan=True),
                content_type='application/json',
            )

            assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_patch_rejects_invalid_geometry(self):
        revision = self._create_draft()
        edited = deepcopy(revision.resultado_editado)
        edited['objects'][0]['geometry']['type'] = 'box'

        response = self._patch_snapshot(revision, edited)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_patch_rejects_manual_object_with_base_object_id(self):
        revision = self._create_draft()
        edited = deepcopy(revision.resultado_editado)
        manual_object = self._manual_object()
        manual_object['provenance']['base_object_id'] = 1
        edited['objects'].append(manual_object)

        response = self._patch_snapshot(revision, edited)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_patch_rejects_automatic_object_without_base_object_id(self):
        revision = self._create_draft()
        edited = deepcopy(revision.resultado_editado)
        edited['objects'][0]['provenance']['base_object_id'] = None

        response = self._patch_snapshot(revision, edited)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_validated_revision_is_immutable(self):
        revision = self._create_draft()
        validate_response = self.client.post(
            self._validar_url(revision.id_revision_segmentacion)
        )
        assert validate_response.status_code == status.HTTP_200_OK

        edited = deepcopy(revision.resultado_editado)
        edited['objects'].append(self._manual_object())
        patch_response = self._patch_snapshot(revision, edited)

        assert patch_response.status_code == status.HTTP_409_CONFLICT

    def test_validating_validated_revision_again_returns_conflict(self):
        revision = self._create_draft()
        first = self.client.post(self._validar_url(revision.id_revision_segmentacion))
        second = self.client.post(self._validar_url(revision.id_revision_segmentacion))

        assert first.status_code == status.HTTP_200_OK
        assert second.status_code == status.HTTP_409_CONFLICT

    def test_patch_cannot_change_state_or_revision_metadata(self):
        revision = self._create_draft()

        response = self.client.patch(
            self._revision_url(revision.id_revision_segmentacion),
            {
                'estado': RevisionSegmentacion.ESTADO_VALIDADA,
                'numero_revision': 99,
                'validado_en': '2026-01-01T00:00:00Z',
            },
            format='json',
        )

        revision.refresh_from_db()
        assert response.status_code == status.HTTP_200_OK
        assert revision.estado == RevisionSegmentacion.ESTADO_BORRADOR
        assert revision.numero_revision == 1
        assert revision.validado_en is None

    def test_resultado_not_found_returns_404(self):
        response = self.client.post(self._resultado_revisiones_url(999999))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_revision_not_found_returns_404(self):
        response = self.client.get(self._revision_url(999999))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_list_revisions_ordered(self):
        revision_one = self._create_draft()
        self.client.post(self._validar_url(revision_one.id_revision_segmentacion))
        self.client.post(self._resultado_revisiones_url())

        response = self.client.get(self._resultado_revisiones_url())

        assert response.status_code == status.HTTP_200_OK
        assert [item['numero_revision'] for item in response.data] == [1, 2]

    def test_get_revision_detail(self):
        revision = self._create_draft()

        response = self.client.get(self._revision_url(revision.id_revision_segmentacion))

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id_revision_segmentacion'] == revision.id_revision_segmentacion

    def test_validation_endpoint_recalculates_summary(self):
        revision = self._create_draft()
        edited = deepcopy(revision.resultado_editado)
        edited['objects'].append(self._manual_object())
        self._patch_snapshot(revision, edited)

        response = self.client.post(self._validar_url(revision.id_revision_segmentacion))

        assert response.status_code == status.HTTP_200_OK
        assert response.data['estado'] == RevisionSegmentacion.ESTADO_VALIDADA
        assert response.data['validado_en'] is not None
        assert response.data['resumen']['total_objects'] == 3

    def test_patch_invalid_snapshot_does_not_change_original_resultado(self):
        original_raw = deepcopy(self.resultado.respuesta_json)
        original_normalized = deepcopy(self.resultado.resultado_normalizado)
        revision = self._create_draft()
        edited = deepcopy(revision.resultado_editado)
        edited['objects'][0]['label'] = 'invalido'

        self._patch_snapshot(revision, edited)
        self.resultado.refresh_from_db()

        assert self.resultado.respuesta_json == original_raw
        assert self.resultado.resultado_normalizado == original_normalized

    def test_creates_draft_from_normalized_version_1_0(self):
        resultado = self._create_resultado(normalized=self._normalized(version='1.0'))

        response = self.client.post(
            self._resultado_revisiones_url(resultado.id_resultado_segmentacion)
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['resultado_editado']['version'] == '1.0'
        assert response.data['resumen']['total_objects'] == 2

    def test_creates_draft_from_normalized_version_1_1(self):
        resultado = self._create_resultado(normalized=self._normalized(version='1.1'))

        response = self.client.post(
            self._resultado_revisiones_url(resultado.id_resultado_segmentacion)
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['resultado_editado']['version'] == '1.0'
        assert response.data['resumen']['total_objects'] == 2
