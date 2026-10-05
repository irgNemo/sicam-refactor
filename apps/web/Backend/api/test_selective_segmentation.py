"""18I: synthetic masks only; no calls to a real segmentation service."""
from copy import deepcopy
from datetime import date
from io import BytesIO
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, connection
from django.db.migrations.executor import MigrationExecutor
from django.test import override_settings
from django.utils import timezone
from PIL import Image
from rest_framework.test import APITestCase, APITransactionTestCase

from api.models import (Paciente, Caso, AnalisisPred, MuestraSaliva, MuestraSangre,
                        ResultadoSegmentacion, RevisionSegmentacion, SegmentationExecution)
from api.services.segmentation.normalizers import normalize_segmentation_result
from api.services.segmentation.revisions import build_revision_snapshot_from_normalized, calculate_revision_summary
from api.services.segmentation.effective import resolve_effective_segmentation

from api.services.segmentation.exceptions import SegmentationTimeoutError, SegmentationConnectionError

CURRENT = 'CURRENT_CUSTOM_V1'
ALT = 'ALT_CPSAM_MORPHOLOGICAL_V1'
RAW = {'objetos': [{'id': 7, 'tipo': label, 'puntos': [[1, 1], [8, 1], [8, 8], [1, 8]]}
                   for label in ('membrana', 'nucleo', 'micronucleo')]}


class SelectiveSegmentationTests(APITestCase):
    def setUp(self):
        directory = TemporaryDirectory(); self.addCleanup(directory.cleanup)
        config = override_settings(MEDIA_ROOT=directory.name); config.enable(); self.addCleanup(config.disable)
        patient = Paciente.objects.create(nombre='Synthetic', apellido='Test', fecha_nacimiento=date(2000, 1, 1), identificacion='18I')
        case = Caso.objects.create(paciente=patient, titulo='Synthetic')
        analysis = AnalisisPred.objects.create(id_paciente_fk=patient, id_caso_fk=case)
        image = BytesIO(); Image.new('RGB', (16, 16)).save(image, format='PNG')
        self.sample = MuestraSaliva.objects.create(analisis=analysis, imagen=SimpleUploadedFile('fixture.png', image.getvalue()))
        self.blood = MuestraSangre.objects.create(analisis=analysis, imagen=SimpleUploadedFile('blood.png', image.getvalue()))
        normalized = normalize_segmentation_result(RAW)
        for obj in normalized['objects']:
            obj['provenance'] = {'origin': 'manual', 'base_object_id': None, 'custom': {'keep': [1, 2]}}
            obj['metadata'] = {'keep': ['exact', obj['label']]}
        self.base = ResultadoSegmentacion.objects.create(muestra=self.sample, tipo_muestra='SALIVA',
            base_origin='MANUAL', segmentation_strategy=None, respuesta_json=deepcopy(RAW), resultado_normalizado=normalized)
        self.url = f'/api/muestras/{self.sample.pk}/segmentar/'
        self.context_url = f'/api/resultados-segmentacion/{self.base.pk}/selective-context/'
        mock = patch('api.views.segment_image', return_value=deepcopy(RAW))
        self.segment = mock.start(); self.addCleanup(mock.stop)

    def payload(self, target='MEMBRANES', **extra):
        context = self.client.get(self.context_url)
        self.assertEqual(context.status_code, 200, context.data)
        return {'target': target, 'segmentation_strategy': ALT, 'resultado_segmentacion_id': self.base.pk,
                'source_token': context.data['source_token'], 'confirm_replacement': True, **extra}

    def run_partial(self, target='MEMBRANES', **extra):
        response = self.client.post(self.url, self.payload(target, **extra), format='json')
        self.assertEqual(response.status_code, 200, response.data)
        return RevisionSegmentacion.objects.get(pk=response.data['revision']['id_revision_segmentacion'])

    def draft(self, validated=False):
        snapshot = build_revision_snapshot_from_normalized(self.base)
        return RevisionSegmentacion.objects.create(resultado_segmentacion=self.base, numero_revision=1,
            estado='VALIDADA' if validated else 'BORRADOR', resultado_editado=snapshot,
            resumen=calculate_revision_summary(snapshot), validado_en=timezone.now() if validated else None)

    def assert_preserved(self, before, after, labels):
        self.assertEqual([o for o in before['objects'] if o['label'] in labels],
                         [o for o in after['objects'] if o['label'] in labels])

    def test_omitted_and_explicit_all_keep_legacy_full_base(self):
        for payload in ({}, {'target': 'ALL'}, {'target': 'ALL', 'segmentation_strategy': ALT}):
            response = self.client.post(self.url, payload, format='json')
            self.assertEqual(response.status_code, 200)
            result = ResultadoSegmentacion.objects.get(pk=response.data['resultado_segmentacion']['id'])
            self.assertEqual(result.base_origin, 'AUTOMATIC')
            self.assertEqual(result.respuesta_json, RAW)
            self.assertEqual(result.resultado_normalizado, normalize_segmentation_result(RAW))
            self.assertFalse(result.revisiones.exists())
            execution = result.executions.get()
            self.assertEqual((execution.target, execution.status), ('ALL', 'COMPLETED'))
            self.assertIsNone(execution.normalized_response)

    def test_invalid_target_and_missing_preconditions_no_call(self):
        for payload in ({'target': 'bad'}, {'target': None}, {'target': 'MEMBRANES'},
                        {'target': 'NUCLEI_AND_MICRONUCLEI', 'resultado_segmentacion_id': self.base.pk}):
            self.assertEqual(self.client.post(self.url, payload, format='json').status_code, 400)
        self.segment.assert_not_called()

    def test_blood_rejects_any_saliva_target(self):
        for target in ('ALL', 'MEMBRANES', 'NUCLEI_AND_MICRONUCLEI'):
            response = self.client.post(f'/api/muestras-sangre/{self.blood.pk}/segmentar/', {'target': target}, format='json')
            self.assertEqual(response.status_code, 400)
        self.segment.assert_not_called()

    def test_manual_empty_membranes_alt_and_current_preserve_entire_objects(self):
        for strategy in (ALT, CURRENT):
            with self.subTest(strategy=strategy):
                # Keep the existing draft on the second pass, still preserving exact N/MN.
                if not self.base.revisiones.exists():
                    self.base.resultado_normalizado['objects'] = self.base.resultado_normalizado['objects'][1:]
                    self.base.save()
                snapshot = deepcopy(self.base.resultado_normalizado)
                raw_base = deepcopy(self.base.respuesta_json)
                draft = self.run_partial(segmentation_strategy=strategy)
                self.assert_preserved(snapshot, draft.resultado_editado, {'nucleo', 'micronucleo'})
                self.base.refresh_from_db()
                self.assertEqual(self.base.resultado_normalizado, snapshot)
                self.assertEqual(self.base.respuesta_json, raw_base)
                self.assertEqual(self.base.base_origin, 'MANUAL'); self.assertIsNone(self.base.segmentation_strategy)
                self.assertEqual(resolve_effective_segmentation(self.base)['fuente'], 'MANUAL')
                execution = self.base.executions.latest('created_at')
                self.assertEqual(execution.status, 'COMPLETED'); self.assertEqual(execution.strategy, strategy)
                self.assertEqual(execution.counts['total_objects'], 3)
                membrane = next(o for o in draft.resultado_editado['objects'] if o['label'] == 'membrana')
                self.assertEqual(membrane['source']['raw_id'], 7)
                self.assertEqual(membrane['provenance'], {'origin': 'automatic', 'base_object_id': None,
                    'strategy': strategy, 'segmentation_execution_id': str(execution.pk), 'execution_object_id': 1})
                self.assertEqual(self.base.revisiones.filter(estado='BORRADOR').count(), 1)

    def test_automatic_base_uses_editorial_snapshot_without_changing_base(self):
        self.base.base_origin = 'AUTOMATIC'; self.base.segmentation_strategy = CURRENT
        self.base.resultado_normalizado = normalize_segmentation_result(RAW); self.base.save()
        expected = build_revision_snapshot_from_normalized(self.base)
        original = deepcopy(self.base.resultado_normalizado)
        draft = self.run_partial()
        self.assert_preserved(expected, draft.resultado_editado, {'nucleo', 'micronucleo'})
        self.base.refresh_from_db(); self.assertEqual(original, self.base.resultado_normalizado)
        self.assertEqual(resolve_effective_segmentation(self.base)['fuente'], 'AUTOMATICO')

    def test_validated_is_immutable_for_both_targets_and_validation_promotes_merge(self):
        for target, preserved in [('MEMBRANES', {'nucleo', 'micronucleo'}), ('NUCLEI_AND_MICRONUCLEI', {'membrana'})]:
            with self.subTest(target=target):
                if not self.base.revisiones.exists(): validated = self.draft(True)
                else: validated = self.base.revisiones.latest('numero_revision')
                old = deepcopy(validated.resultado_editado); old_time = validated.actualizado_en
                draft = self.run_partial(target)
                self.assert_preserved(old, draft.resultado_editado, preserved)
                validated.refresh_from_db(); self.assertEqual(validated.resultado_editado, old)
                self.assertEqual(validated.actualizado_en, old_time)
                self.assertEqual(resolve_effective_segmentation(self.base)['revision']['id_revision_segmentacion'], validated.pk)
                response = self.client.post(f'/api/revisiones-segmentacion/{draft.pk}/validar/', {'expected_updated_at': draft.actualizado_en.isoformat()}, format='json')
                self.assertEqual(response.status_code, 200)
                self.assertEqual(resolve_effective_segmentation(self.base)['resultado'], draft.resultado_editado)

    def test_active_draft_second_target_uses_latest_manual_correction_and_checkpoint(self):
        draft = self.run_partial()
        corrected = deepcopy(draft.resultado_editado)
        membrane = next(o for o in corrected['objects'] if o['label'] == 'membrana')
        membrane['geometry']['points'][0] = [2, 3]; membrane['metadata'] = {'expert': 'keep'}
        response = self.client.patch(f'/api/revisiones-segmentacion/{draft.pk}/', {'resultado_editado': corrected, 'expected_updated_at': draft.actualizado_en.isoformat()}, format='json')
        self.assertEqual(response.status_code, 200)
        updated = self.run_partial('NUCLEI_AND_MICRONUCLEI')
        self.assertEqual(updated.pk, draft.pk)
        self.assert_preserved(corrected, updated.resultado_editado, {'membrana'})
        execution = self.base.executions.latest('created_at')
        self.assertEqual(execution.checkpoint['snapshot'], corrected)
        self.assertEqual(execution.checkpoint['revision_id'], draft.pk)
        self.assertEqual(len({o['id'] for o in updated.resultado_editado['objects']}), 3)
        self.assertTrue(all(o['source']['raw_id'] == 7 for o in updated.resultado_editado['objects']))

    def test_empty_auto_replaces_selected_class_with_empty(self):
        for target, labels in [('MEMBRANES', {'nucleo','micronucleo'}), ('NUCLEI_AND_MICRONUCLEI', set())]:
            self.segment.return_value = {'objetos': []}
            draft = self.run_partial(target)
            self.assertEqual({o['label'] for o in draft.resultado_editado['objects']}, labels)

    def test_no_confirmation_when_selected_empty_without_draft(self):
        self.base.resultado_normalizado['objects'] = self.base.resultado_normalizado['objects'][1:]; self.base.save()
        self.run_partial(confirm_replacement=False)
        response = self.client.post(self.url, self.payload(confirm_replacement=False), format='json')
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data['code'], 'REPLACEMENT_CONFIRMATION_REQUIRED')

    def test_existing_objects_without_confirmation_blocked(self):
        response = self.client.post(self.url, self.payload(confirm_replacement=False), format='json')
        self.assertEqual(response.status_code, 409); self.segment.assert_not_called()

    def test_stale_preflight_rejected_without_computation(self):
        payload = self.payload(); self.draft()
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data['code'], 'SEGMENTATION_SOURCE_CHANGED'); self.segment.assert_not_called()

    def test_concurrent_edit_during_call_cancels_without_mutating_new_draft(self):
        draft = self.draft()
        changed = deepcopy(draft.resultado_editado); changed['objects'][1]['metadata']['changed'] = True
        def concurrent(*args, **kwargs):
            self.client.patch(f'/api/revisiones-segmentacion/{draft.pk}/', {'resultado_editado': changed}, format='json')
            return deepcopy(RAW)
        self.segment.side_effect = concurrent
        response = self.client.post(self.url, self.payload(), format='json')
        self.assertEqual(response.status_code, 409); self.assertEqual(response.data['code'], 'SEGMENTATION_SOURCE_CHANGED')
        draft.refresh_from_db(); self.assertEqual(draft.resultado_editado, changed)
        self.assertEqual(self.base.executions.get().status, 'CANCELLED')
        self.assertEqual(self.base.executions.get().counts['total_objects'], 3)

    def test_two_requests_same_version_only_one_commits(self):
        payload = self.payload(); entered = False
        def concurrent(*args, **kwargs):
            nonlocal entered
            if not entered:
                entered = True
                inner = self.client.post(self.url, payload, format='json')
                self.assertEqual(inner.status_code, 200)
            return deepcopy(RAW)
        self.segment.side_effect = concurrent
        outer = self.client.post(self.url, payload, format='json')
        self.assertEqual(outer.status_code, 409)
        self.assertEqual(self.base.executions.filter(status='COMPLETED').count(), 1)
        self.assertEqual(self.base.executions.filter(status='CANCELLED').count(), 1)
        self.assertEqual(self.base.revisiones.count(), 1)

    def test_timeout_connection_invalid_payload_do_not_touch_draft(self):
        draft = self.draft(); before = deepcopy(draft.resultado_editado); updated_at = draft.actualizado_en
        for error in (SegmentationTimeoutError('secret'), SegmentationConnectionError('secret'), RuntimeError('secret')):
            self.segment.side_effect = error
            response = self.client.post(self.url, self.payload(), format='json')
            self.assertGreaterEqual(response.status_code, 500); self.assertNotIn('secret', str(response.data))
            draft.refresh_from_db(); self.assertEqual(draft.resultado_editado, before); self.assertEqual(draft.actualizado_en, updated_at)
            self.assertEqual(self.base.executions.latest('created_at').status, 'FAILED')
        self.segment.side_effect = None; self.segment.return_value = {'objetos':[{'tipo':'other','puntos':[]}]}
        response = self.client.post(self.url, self.payload(), format='json')
        self.assertEqual(response.status_code, 502)

    def test_persistence_failure_rolls_back_snapshot_and_id_counter(self):
        draft = self.draft(); before = deepcopy(draft.resultado_editado)
        counter = self.base.next_editorial_id
        save = SegmentationExecution.save
        def fail(instance, *args, **kwargs):
            if instance.status == 'COMPLETED': raise IntegrityError('synthetic failure')
            return save(instance, *args, **kwargs)
        with patch.object(SegmentationExecution, 'save', fail):
            response = self.client.post(self.url, self.payload(), format='json')
        self.assertEqual(response.status_code, 500)
        draft.refresh_from_db(); self.assertEqual(draft.resultado_editado, before)
        self.base.refresh_from_db(); self.assertEqual(self.base.next_editorial_id, counter)
        execution = self.base.executions.get(); self.assertEqual(execution.status, 'FAILED')
        self.assertEqual(execution.checkpoint['snapshot'], before)
        self.assertEqual(execution.normalized_response, normalize_segmentation_result(RAW))

    def test_allocator_does_not_reuse_retired_or_reserved_ids(self):
        draft = self.draft()
        retired = deepcopy(draft.resultado_editado); retired['objects'][0]['id'] = 900
        response = self.client.patch(f'/api/revisiones-segmentacion/{draft.pk}/', {'resultado_editado': retired}, format='json')
        self.assertEqual(response.status_code, 200)
        retired['objects'] = retired['objects'][1:]
        self.client.patch(f'/api/revisiones-segmentacion/{draft.pk}/', {'resultado_editado': retired}, format='json')
        reserve_url = f'/api/resultados-segmentacion/{self.base.pk}/reserve-object-id/'
        reserved = self.client.post(reserve_url).data['id']
        self.assertGreater(reserved, 900)
        updated = self.run_partial()
        membrane = next(o for o in updated.resultado_editado['objects'] if o['label'] == 'membrana')
        self.assertGreater(membrane['id'], reserved)

    def test_stale_editor_save_and_validation_cannot_overwrite_merge(self):
        draft = self.draft(); old = self.client.get(f'/api/revisiones-segmentacion/{draft.pk}/').data
        self.run_partial()
        response = self.client.patch(f'/api/revisiones-segmentacion/{draft.pk}/', {
            'resultado_editado': old['resultado_editado'], 'expected_updated_at': old['actualizado_en']}, format='json')
        self.assertEqual(response.status_code, 409)
        response = self.client.post(f'/api/revisiones-segmentacion/{draft.pk}/validar/', {
            'expected_updated_at': old['actualizado_en']}, format='json')
        self.assertEqual(response.status_code, 409)

    def test_source_base_and_validated_changes_during_computation_detected(self):
        def mutate(*args, **kwargs):
            self.base.resultado_normalizado['objects'][0]['metadata']['edit'] = 1
            self.base.save()
            return RAW
        self.segment.side_effect = mutate
        response = self.client.post(self.url, self.payload(), format='json')
        self.assertEqual(response.status_code, 409)
        self.assertFalse(self.base.revisiones.exists())

    def test_context_for_foreign_sample_rejected(self):
        data = self.payload(); data['resultado_segmentacion_id'] = 999999
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, 400); self.segment.assert_not_called()

    def test_no_precondition_on_post_merge_editorial_writes_is_rejected(self):
        draft = self.run_partial()
        url = f'/api/revisiones-segmentacion/{draft.pk}/'
        self.assertEqual(self.client.patch(url, {'resultado_editado': draft.resultado_editado}, format='json').status_code, 409)
        self.assertEqual(self.client.post(url+'validar/', {}, format='json').status_code, 409)
        draft.refresh_from_db(); self.assertEqual(draft.estado, 'BORRADOR')

    def test_validated_and_its_new_draft_use_draft_edits_as_source(self):
        validated = self.draft(True)
        response = self.client.post(f'/api/resultados-segmentacion/{self.base.pk}/revisiones/')
        self.assertEqual(response.status_code, 201)
        draft = RevisionSegmentacion.objects.get(pk=response.data['id_revision_segmentacion'])
        snapshot = deepcopy(draft.resultado_editado)
        snapshot['objects'][1]['geometry']['points'][0] = [2, 2]
        draft.resultado_editado = snapshot; draft.save()
        merged = self.run_partial()
        self.assertEqual(merged.pk, draft.pk)
        self.assert_preserved(snapshot, merged.resultado_editado, {'nucleo', 'micronucleo'})
        self.assertEqual(resolve_effective_segmentation(self.base)['revision']['id_revision_segmentacion'], validated.pk)

    def test_source_change_by_validation_during_calculation_cancels(self):
        draft = self.draft()
        def validate(*args, **kwargs):
            self.client.post(f'/api/revisiones-segmentacion/{draft.pk}/validar/', {}, format='json')
            return RAW
        self.segment.side_effect = validate
        response = self.client.post(self.url, self.payload(), format='json')
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.base.revisiones.count(), 1)
        draft.refresh_from_db(); self.assertEqual(draft.estado, 'VALIDADA')

    def test_all_service_failure_durable_without_new_base(self):
        self.segment.side_effect = SegmentationTimeoutError('synthetic timeout')
        response = self.client.post(self.url, {'target':'ALL'}, format='json')
        self.assertEqual(response.status_code, 504)
        self.assertEqual(ResultadoSegmentacion.objects.count(), 1)
        self.assertEqual(SegmentationExecution.objects.get().status, 'FAILED')

    def test_ids_repeat_across_raw_types_but_never_editorial_or_across_replacements(self):
        first = self.run_partial('NUCLEI_AND_MICRONUCLEI')
        retired = {o['id'] for o in first.resultado_editado['objects'] if o['label'] != 'membrana'}
        updated = self.run_partial('NUCLEI_AND_MICRONUCLEI')
        fresh = {o['id'] for o in updated.resultado_editado['objects'] if o['label'] != 'membrana'}
        self.assertFalse(retired & fresh)
        self.assertTrue(all(o['source']['raw_id'] == 7 for o in updated.resultado_editado['objects']))


    def test_checkpoint_restoration_uses_existing_guarded_editorial_api(self):
        initial = self.draft()
        before = deepcopy(initial.resultado_editado)
        merged = self.run_partial()
        execution = self.base.executions.get()
        response = self.client.patch(f'/api/revisiones-segmentacion/{merged.pk}/', {
            'resultado_editado': execution.checkpoint['snapshot'],
            'expected_updated_at': merged.actualizado_en.isoformat(),
        }, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        merged.refresh_from_db()
        self.assertEqual(merged.resultado_editado, before)
        self.assertEqual(merged.estado, 'BORRADOR')
        self.assertEqual(self.base.revisiones.count(), 1)
        self.base.refresh_from_db()
        self.assertGreater(self.base.next_editorial_id, max(o['id'] for o in before['objects']))



class SelectiveTransactionTests(APITransactionTestCase):
    setUp = SelectiveSegmentationTests.setUp
    payload = SelectiveSegmentationTests.payload

    def test_microservice_call_runs_outside_transaction(self):
        seen = []
        def remote(*args, **kwargs):
            seen.append(connection.in_atomic_block)
            return deepcopy(RAW)
        self.segment.side_effect = remote
        response = self.client.post(self.url, self.payload(), format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(seen, [False])
        response = self.client.post(self.url, {'target': 'ALL'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(seen, [False, False])

    def test_migration_seeds_counter_from_history_without_altering_annotations(self):
        executor = MigrationExecutor(connection)
        leafs = executor.loader.graph.leaf_nodes()
        try:
            executor.migrate([('api', '0008_imagej_manual_import')])
            old_apps = executor.loader.project_state([('api', '0008_imagej_manual_import')]).apps
            Result = old_apps.get_model('api', 'ResultadoSegmentacion')
            Revision = old_apps.get_model('api', 'RevisionSegmentacion')
            result = Result.objects.get(pk=self.base.pk)
            snapshot = {'objects':[{'id':700,'label':'nucleo','geometry':{'type':'polygon','points':[[1,1],[2,1],[2,2]]},
                                    'provenance':{'origin':'manual','base_object_id':None}}]}
            Revision.objects.create(resultado_segmentacion_id=result.pk, numero_revision=1,
                resultado_editado=snapshot, resumen={'total_objects':1}, estado='VALIDADA')
            original_base = deepcopy(result.resultado_normalizado)
            executor = MigrationExecutor(connection); executor.migrate(leafs)
            self.base.refresh_from_db()
            self.assertEqual(self.base.next_editorial_id, 701)
            self.assertEqual(self.base.resultado_normalizado, original_base)
            self.assertEqual(self.base.revisiones.get().resultado_editado, snapshot)
        finally:
            MigrationExecutor(connection).migrate(leafs)
