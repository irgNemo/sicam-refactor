"""Sprint 18B: SALIVA routing/provenance and independent BLOOD regressions."""
from copy import deepcopy
from datetime import date
from io import BytesIO
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from requests.exceptions import ConnectionError, HTTPError, Timeout
from rest_framework.test import APITestCase

from api.models import AnalisisPred, Caso, MuestraSaliva, MuestraSangre, Paciente, ResultadoSegmentacion
from api.segmentation_strategies import SalivaSegmentationStrategy as Strategy
from api.services.segmentation.factory import get_segmentation_client
from api.services.segmentation.strategies import resolve_saliva_segmentation_service

CURRENT = Strategy.CURRENT_CUSTOM_V1
ALT = Strategy.ALT_CPSAM_MORPHOLOGICAL_V1
RAW = {'objetos': [
    {'id': 7, 'tipo': 'membrana', 'puntos': [[1, 1], [30, 1], [30, 30], [1, 30]]},
    {'id': 7, 'tipo': 'nucleo', 'puntos': [[5, 5], [10, 5], [10, 10], [5, 10]]},
    {'id': 7, 'tipo': 'nucleo', 'puntos': [[15, 5], [20, 5], [20, 10], [15, 10]]},
    {'id': 7, 'tipo': 'micronucleo', 'puntos': [[22, 22], [25, 22], [25, 25]]},
]}
SERVICES = {
    'SALIVA': {'url': 'http://127.0.0.1:8001', 'timeout': 30},
    'SANGRE': {'url': 'http://127.0.0.1:8002', 'timeout': 240},
}


@override_settings(SEGMENTATION_SERVICES=SERVICES,
                   SALIVA_ALT_SEGMENTATION_SERVICE={'url': 'http://127.0.0.1:8003', 'timeout': 240})
class SalivaStrategyIntegrationTests(APITestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        override = override_settings(MEDIA_ROOT=self.temp.name)
        override.enable()
        self.addCleanup(override.disable)
        patient = Paciente.objects.create(nombre='Demo', apellido='18B', fecha_nacimiento=date(2000, 1, 1), identificacion='18B-test')
        case = Caso.objects.create(paciente=patient, titulo='18B test')
        analysis = AnalisisPred.objects.create(id_paciente_fk=patient, id_caso_fk=case)
        data = BytesIO()
        Image.new('RGB', (32, 32), 'white').save(data, format='PNG')
        self.saliva = MuestraSaliva.objects.create(analisis=analysis, imagen=SimpleUploadedFile('saliva.png', data.getvalue()))
        self.blood = MuestraSangre.objects.create(analisis=analysis, imagen=SimpleUploadedFile('blood.png', data.getvalue()))
        patcher = patch('api.services.segmentation.base_client.requests.post')
        self.post = patcher.start()
        self.addCleanup(patcher.stop)
        self.post.return_value = Mock()
        self.post.return_value.json.return_value = deepcopy(RAW)

    def segment(self, payload=None, blood=False, format='json'):
        sample = self.blood if blood else self.saliva
        route = 'muestras-sangre' if blood else 'muestras'
        response = self.client.post(f'/api/{route}/{sample.pk}/segmentar/', payload or {}, format=format)
        return response

    def result(self, response):
        self.assertEqual(response.status_code, 200, response.data)
        return ResultadoSegmentacion.objects.get(pk=response.data['resultado_segmentacion']['id'])

    def test_saliva_omitted_strategy_routes_and_persists_current(self):
        r = self.result(self.segment())
        self.assertEqual(r.segmentation_strategy, CURRENT)
        self.assertEqual(self.post.call_args.args[0], 'http://127.0.0.1:8001/segmentar')
        self.assertEqual(self.post.call_args.kwargs['timeout'], 30)
        self.assertIn('file', self.post.call_args.kwargs['files'])

    def test_saliva_explicit_strategies_route_persist_and_serialize(self):
        for strategy, port, timeout in [(CURRENT, 8001, 30), (ALT, 8003, 240)]:
            with self.subTest(strategy=strategy):
                response = self.segment({'segmentation_strategy': strategy})
                r = self.result(response)
                self.assertEqual(r.segmentation_strategy, strategy)
                self.assertEqual(response.data['resultado_segmentacion']['segmentation_strategy'], strategy)
                self.assertEqual(self.post.call_args.args[0], f'http://127.0.0.1:{port}/segmentar')
                self.assertEqual(self.post.call_args.kwargs['timeout'], timeout)
                self.assertEqual(r.respuesta_json, RAW)
                self.assertEqual(r.resultado_normalizado, response.data['resultado_normalizado'])
        history = self.client.get(f'/api/muestras/{self.saliva.pk}/resultados-segmentacion/')
        self.assertEqual(history.status_code, 200)
        self.assertEqual([item['segmentation_strategy'] for item in history.data], [ALT, CURRENT])

    def test_form_request_and_empty_legacy_request(self):
        self.assertEqual(self.result(self.segment({'segmentation_strategy': ALT}, format='multipart')).segmentation_strategy, ALT)
        response = self.client.post(f'/api/muestras/{self.saliva.pk}/segmentar/')
        self.assertEqual(self.result(response).segmentation_strategy, CURRENT)

    def test_invalid_strategy_rejected_before_http_or_persistence(self):
        for value in ['UNKNOWN', '', None, ['ALT'], {'strategy': ALT}, 1]:
            with self.subTest(value=value):
                response = self.segment({'segmentation_strategy': value})
                self.assertEqual(response.status_code, 400)
        self.post.assert_not_called()
        self.assertEqual(ResultadoSegmentacion.objects.count(), 0)

    def test_alt_repeated_raw_ids_use_shared_normalizer(self):
        alt = self.result(self.segment({'segmentation_strategy': ALT}))
        current = self.result(self.segment())
        self.assertEqual(alt.resultado_normalizado, current.resultado_normalizado)
        nuclei = [o for o in alt.resultado_normalizado['objects'] if o['label'] == 'nucleo']
        self.assertEqual(len({o['id'] for o in nuclei}), 2)
        self.assertEqual([o['source']['raw_id'] for o in nuclei], [7, 7])

    def test_alt_timeout_connection_http_and_invalid_responses_do_not_persist(self):
        for error, expected in [(Timeout('slow'), 504), (ConnectionError('offline'), 503)]:
            with self.subTest(error=error):
                self.post.side_effect = error
                self.assertEqual(self.segment({'segmentation_strategy': ALT}).status_code, expected)
        self.post.side_effect = None
        self.post.return_value.raise_for_status.side_effect = HTTPError('500 Internal Server Error')
        self.assertEqual(self.segment({'segmentation_strategy': ALT}).status_code, 502)
        self.post.return_value.raise_for_status.side_effect = None
        self.post.return_value.json.side_effect = ValueError('bad json')
        self.assertEqual(self.segment({'segmentation_strategy': ALT}).status_code, 502)
        self.post.return_value.json.side_effect = None
        self.post.return_value.json.return_value = {'wrong': []}
        self.assertEqual(self.segment({'segmentation_strategy': ALT}).status_code, 502)
        self.assertEqual(ResultadoSegmentacion.objects.count(), 0)

    def test_effective_and_validated_revisions_keep_parent_strategy(self):
        for strategy in [CURRENT, ALT]:
            with self.subTest(strategy=strategy):
                result = self.result(self.segment({'segmentation_strategy': strategy}))
                base = f'/api/resultados-segmentacion/{result.pk}'
                draft = self.client.post(base + '/revisiones/', {}, format='json')
                self.assertEqual(draft.status_code, 201, draft.data)
                self.assertNotIn('segmentation_strategy', draft.data)
                effective = self.client.get(base + '/efectivo/').data
                self.assertEqual(effective['fuente'], 'AUTOMATICO')
                self.assertEqual(effective['segmentation_strategy'], strategy)
                validation = self.client.post(f"/api/revisiones-segmentacion/{draft.data['id_revision_segmentacion']}/validar/")
                self.assertEqual(validation.status_code, 200, validation.data)
                effective = self.client.get(base + '/efectivo/').data
                self.assertEqual(effective['fuente'], 'VALIDADA')
                self.assertEqual(effective['segmentation_strategy'], strategy)
                result.refresh_from_db()
                self.assertEqual(result.segmentation_strategy, strategy)
                characterization = self.client.post(base + '/caracterizar/')
                self.assertEqual(characterization.status_code, 201, characterization.data)
                self.assertEqual(characterization.data['source_type'], 'VALIDADA')
                self.assertEqual(characterization.data['algorithm_version'], '2.0')

    def test_characterization_is_independent_of_saliva_strategy(self):
        payloads = []
        for strategy in [CURRENT, ALT]:
            result = self.result(self.segment({'segmentation_strategy': strategy}))
            response = self.client.post(f'/api/resultados-segmentacion/{result.pk}/caracterizar/')
            self.assertEqual(response.status_code, 201, response.data)
            self.assertEqual(response.data['algorithm_version'], '2.0')
            payload = deepcopy(response.data['resultado_json'])
            payload.pop('source')
            payloads.append(payload)
        self.assertEqual(payloads[0], payloads[1])

    def test_blood_unchanged_null_history_effective_and_counts_only(self):
        blood_raw = deepcopy(RAW)
        blood_raw['objetos'] = [o for o in blood_raw['objetos'] if o['tipo'] != 'nucleo']
        self.post.return_value.json.return_value = blood_raw
        response = self.segment(blood=True)
        result = self.result(response)
        self.assertIsNone(result.segmentation_strategy)
        self.assertIsNone(response.data['resultado_segmentacion']['segmentation_strategy'])
        self.assertEqual(self.post.call_args.args[0], 'http://127.0.0.1:8002/api/v1/segmentar')
        self.assertEqual(self.post.call_args.kwargs['timeout'], 240)
        history = self.client.get(f'/api/muestras-sangre/{self.blood.pk}/resultados-segmentacion/')
        self.assertEqual(history.status_code, 200)
        self.assertIsNone(history.data[0]['segmentation_strategy'])
        base = f'/api/resultados-segmentacion/{result.pk}'
        effective = self.client.get(base + '/efectivo/').data
        self.assertEqual(effective['fuente'], 'AUTOMATICO')
        self.assertIsNone(effective['segmentation_strategy'])
        response = self.client.post(base + '/caracterizar/')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['algorithm_version'], '1.0')
        self.assertEqual(response.data['resultado_json']['counts'], {'membrana': 1, 'micronucleo': 1})
        self.assertEqual(response.data['resultado_json']['indices'], {})

    def test_blood_rejects_strategy_without_contacting_any_service(self):
        for value in [CURRENT, ALT, 'UNKNOWN', '', None]:
            with self.subTest(value=value):
                response = self.segment({'segmentation_strategy': value}, blood=True)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.data['error'], 'segmentation_strategy is only supported for SALIVA samples')
        self.post.assert_not_called()
        self.assertEqual(ResultadoSegmentacion.objects.count(), 0)

    def test_blood_failure_keeps_existing_error_result_with_null_strategy(self):
        self.post.side_effect = ConnectionError('offline')
        response = self.segment(blood=True)
        self.assertEqual(response.status_code, 503)
        result = ResultadoSegmentacion.objects.get()
        self.assertEqual(result.estado, 'ERROR')
        self.assertIsNone(result.segmentation_strategy)

    def test_resolver_honors_independent_settings_and_blood_bypasses_it(self):
        with override_settings(SEGMENTATION_SERVICES={'SALIVA': {'url': 'http://current.example', 'timeout': 41}}):
            current = resolve_saliva_segmentation_service()
            self.assertEqual(current, {'strategy': CURRENT, 'url': 'http://current.example', 'timeout': 41})
        with override_settings(SALIVA_ALT_SEGMENTATION_SERVICE={'url': 'http://alt.example', 'timeout': 321}):
            service = resolve_saliva_segmentation_service(ALT)
            self.assertEqual(service, {'strategy': ALT, 'url': 'http://alt.example', 'timeout': 321})
            client = get_segmentation_client('SALIVA', segmentation_strategy=ALT)
            self.assertEqual(client.timeout, 321)
            self.assertEqual(client.base_url, 'http://alt.example')
        with patch('api.services.segmentation.factory.resolve_saliva_segmentation_service') as resolver:
            self.assertEqual(get_segmentation_client('BLOOD').get_endpoint(), '/api/v1/segmentar')
            resolver.assert_not_called()
            with self.assertRaises(ValueError):
                get_segmentation_client('BLOOD', segmentation_strategy=ALT)


class SalivaStrategyMigrationTests(TransactionTestCase):
    def test_backfill_preserves_existing_payloads_dates_revisions_and_characterizations(self):
        old_target = [('api', '0006_resultadocaracterizacion_and_more')]
        new_target = [('api', '0007_saliva_segmentation_strategy')]
        executor = MigrationExecutor(connection)
        self.addCleanup(lambda: MigrationExecutor(connection).migrate(new_target))
        executor.migrate(old_target)
        old = executor.loader.project_state(old_target).apps
        patient = old.get_model('api', 'Paciente').objects.create(nombre='Migration', apellido='Test', fecha_nacimiento=date(2000, 1, 1), identificacion='18B-migration')
        case = old.get_model('api', 'Caso').objects.create(paciente=patient, titulo='Migration test')
        analysis = old.get_model('api', 'AnalisisPred').objects.create(id_paciente_fk=patient, id_caso_fk=case)
        saliva = old.get_model('api', 'MuestraSaliva').objects.create(analisis=analysis, imagen='unused.png')
        blood = old.get_model('api', 'MuestraSangre').objects.create(analisis=analysis, imagen='unused-blood.png')
        Result = old.get_model('api', 'ResultadoSegmentacion')
        for kwargs in [dict(muestra=saliva, tipo_muestra='SALIVA'), dict(muestra_sangre=blood, tipo_muestra='SANGRE')]:
            r = Result.objects.create(**kwargs, respuesta_json=RAW, resultado_normalizado={'objects': []}, estado='COMPLETADO')
            old.get_model('api', 'RevisionSegmentacion').objects.create(resultado_segmentacion=r, numero_revision=1, estado='BORRADOR', resultado_editado={'objects': []}, resumen={'total_objects': 0})
            old.get_model('api', 'ResultadoCaracterizacion').objects.create(resultado_segmentacion=r, source_type='AUTOMATICO', sample_type=r.tipo_muestra, algorithm_version='1.0', resultado_json={'historic': True})
        Result.objects.create(muestra=saliva, tipo_muestra='SALIVA', respuesta_json={}, estado='ERROR', error='historic error')
        names = ['ResultadoSegmentacion', 'RevisionSegmentacion', 'ResultadoCaracterizacion']
        before = {name: list(old.get_model('api', name).objects.order_by('pk').values()) for name in names}
        executor = MigrationExecutor(connection)
        executor.migrate(new_target)
        new = executor.loader.project_state(new_target).apps
        for name in names:
            after = list(new.get_model('api', name).objects.order_by('pk').values())
            if name == 'ResultadoSegmentacion':
                for row in after:
                    value = row.pop('segmentation_strategy')
                    self.assertEqual(value, CURRENT if row['muestra_id'] else None)
            self.assertEqual(after, before[name])
