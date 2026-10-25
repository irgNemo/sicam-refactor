"""Lifecycle acceptance uses only isolated synthetic DB/storage."""
import copy
from unittest.mock import patch
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from api import test_access as fixture_module
from api.test_acquisition import upload
from api.models import (Paciente, Caso, AnalisisPred, MuestraSaliva, MuestraSangre,
    AcquisitionSeries, AcquisitionProfile, Calibration, ResultadoCaracterizacion,
    RevisionSegmentacion, LifecycleEvent)
from api.services.lifecycle import dependencies


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class LifecycleTests(TestCase):
    user = fixture_module.AccessTests.user
    domain = fixture_module.AccessTests.domain
    as_user = fixture_module.AccessTests.as_user
    setUp = fixture_module.AccessTests.setUp

    def preview(self, route, obj):
        return self.client.get(f'/api/lifecycle/{route}/{obj.pk}/')

    def run_action(self, route, obj, action, **data):
        return self.client.post(f'/api/lifecycle/{route}/{obj.pk}/',
            {'action':action,'reason':'Synthetic correction','confirm':True,**data},format='json')

    def empty_patient(self):
        return Paciente.objects.create(institution=self.a,nombre='Sensitive name',apellido='Never copied',identificacion='empty',fecha_nacimiento='2000-01-01')

    def test_empty_patient_delete_surviving_private_event(self):
        patient=self.empty_patient();pk=patient.pk
        self.assertIn('HARD_DELETE',self.preview('pacientes',patient).data['allowed_actions'])
        self.assertEqual(self.run_action('pacientes',patient,'HARD_DELETE').status_code,200)
        self.assertFalse(Paciente.objects.filter(pk=pk).exists())
        event=LifecycleEvent.objects.get();self.assertEqual(event.target_id,str(pk))
        self.assertEqual(event.actor,self.users['ADMIN_A']);self.assertEqual(event.institution,self.a)
        self.assertNotIn('Sensitive',str(event.metadata)+event.target_display)
        self.assertEqual(self.run_action('pacientes',patient,'HARD_DELETE').status_code,404)
        self.assertEqual(LifecycleEvent.objects.count(),1)

    def test_full_graph_counts_and_scientific_history_archive_restore(self):
        patient=self.da['pacientes'];revision=self.da['revisiones-segmentacion']
        before=copy.deepcopy(revision.resultado_editado)
        counts=self.preview('pacientes',patient).data['dependencies']
        for name in ('Caso','AnalisisPred','MuestraSaliva','MuestraSangre','ResultadoSegmentacion','RevisionSegmentacion','AcquisitionSeries'):
            self.assertGreater(counts[name],0)
        self.assertEqual(self.run_action('pacientes',patient,'HARD_DELETE').status_code,409)
        self.assertEqual(self.run_action('pacientes',patient,'ARCHIVE').status_code,200)
        self.assertEqual(self.client.get('/api/pacientes/').data,[])
        self.assertEqual(len(self.client.get('/api/pacientes/?include_archived=true').data),1)
        for route in ('casos','analisis','muestras','muestras-sangre','acquisition-series'):
            self.assertEqual(self.client.get(f'/api/{route}/').data,[])
            self.assertEqual(self.client.get(f'/api/{route}/{self.da[route].pk}/').status_code,404)
        url=f'/api/resultados-segmentacion/{self.da["resultados-segmentacion"].pk}/'
        self.assertEqual(self.client.post(url+'caracterizar/').status_code,404)
        self.assertEqual(self.client.get(url+'efectivo/?include_archived=true').status_code,200)
        self.assertEqual(self.run_action('pacientes',patient,'RESTORE').status_code,200)
        patient.refresh_from_db();self.assertIsNotNone(patient.archived_by_id)
        self.assertEqual(patient.archive_reason,'Synthetic correction')
        revision.refresh_from_db();self.assertEqual(revision.resultado_editado,before)
        self.assertEqual(list(LifecycleEvent.objects.order_by('pk').values_list('action',flat=True)),['ARCHIVE','RESTORE'])

    def test_child_archive_survives_parent_restore_and_parent_conflict(self):
        patient=self.da['pacientes'];sample=self.da['muestras']
        self.assertEqual(self.run_action('muestras',sample,'ARCHIVE').status_code,200)
        self.assertEqual(self.run_action('pacientes',patient,'ARCHIVE').status_code,200)
        denied=self.run_action('muestras',sample,'RESTORE')
        self.assertEqual(denied.status_code,409);self.assertEqual(denied.data['code'],'PARENT_ARCHIVED')
        self.run_action('pacientes',patient,'RESTORE')
        self.assertEqual(self.client.get('/api/muestras/').data,[])
        self.assertEqual(self.run_action('muestras',sample,'RESTORE').status_code,200)

    def test_reason_confirmation_and_duplicate_action(self):
        patient=self.da['pacientes']
        for bad in ('', ' ', None, 123, 'x'*2001):
            self.assertEqual(self.run_action('pacientes',patient,'ARCHIVE',reason=bad).status_code,400)
        self.assertEqual(self.run_action('pacientes',patient,'ARCHIVE',confirm=False).status_code,400)
        self.assertEqual(LifecycleEvent.objects.count(),0)
        self.assertEqual(self.run_action('pacientes',patient,'ARCHIVE').status_code,200)
        self.assertEqual(self.run_action('pacientes',patient,'ARCHIVE').status_code,409)
        self.assertEqual(LifecycleEvent.objects.count(),1)

    def test_sample_creator_delete_media_and_missing_endpoint(self):
        for route,model in [('muestras',MuestraSaliva),('muestras-sangre',MuestraSangre)]:
            sample=model.objects.create(analisis=self.da['analisis'],imagen=upload(),created_by=self.users['OPERATOR_A'])
            name=sample.imagen.name;storage=sample.imagen.storage;pk=sample.pk
            self.as_user('OPERATOR_A')
            with self.captureOnCommitCallbacks(execute=True):
                response=self.run_action(route,sample,'HARD_DELETE')
            self.assertEqual(response.status_code,200,response.data)
            self.assertFalse(storage.exists(name));self.assertFalse(model.objects.filter(pk=pk).exists())
            kind='saliva' if model is MuestraSaliva else 'sangre'
            self.assertEqual(self.client.get(f'/api/private-media/{kind}/{pk}/').status_code,404)
            event=LifecycleEvent.objects.get(pk=response.data['event_id'])
            self.assertEqual(event.metadata['media_cleanup'][0]['status'],'DELETED')
            self.assertEqual(len(event.metadata['media_cleanup'][0]['sha256']),64)

    def test_shared_media_preserved_and_delete_failure_logged(self):
        sample=MuestraSaliva.objects.create(analisis=self.da['analisis'],imagen=self.da['muestras'].imagen.name)
        name=sample.imagen.name;storage=sample.imagen.storage
        with self.captureOnCommitCallbacks(execute=True):response=self.run_action('muestras',sample,'HARD_DELETE')
        self.assertTrue(storage.exists(name))
        self.assertEqual(LifecycleEvent.objects.get(pk=response.data['event_id']).metadata['media_cleanup'][0]['status'],'SHARED_FILE_RETAINED')
        sample=MuestraSaliva.objects.create(analisis=self.da['analisis'],imagen=upload());pk=sample.pk
        with patch.object(sample.imagen.storage,'delete',side_effect=OSError('synthetic')),self.captureOnCommitCallbacks(execute=True):
            response=self.run_action('muestras',sample,'HARD_DELETE')
        self.assertEqual(response.status_code,200)
        self.assertFalse(MuestraSaliva.objects.filter(pk=pk).exists())
        self.assertEqual(LifecycleEvent.objects.get(pk=response.data['event_id']).metadata['media_cleanup'][0]['status'],'MEDIA_DELETE_FAILED')

    def test_sample_derived_data_prevents_delete_and_archive_keeps_media(self):
        sample=self.da['muestras'];name=sample.imagen.name
        self.assertEqual(self.run_action('muestras',sample,'HARD_DELETE').status_code,409)
        self.assertEqual(self.run_action('muestras',sample,'ARCHIVE').status_code,200)
        self.assertTrue(sample.imagen.storage.exists(name))
        media=self.client.get(f'/api/private-media/saliva/{sample.pk}/');self.assertEqual(media.status_code,200);media.close()
        self.as_user('ADMIN_B');self.assertEqual(self.client.get(f'/api/private-media/saliva/{sample.pk}/').status_code,404)

    def test_role_and_institution_matrix_no_privilege_bypass(self):
        sample=MuestraSaliva.objects.create(analisis=self.da['analisis'],imagen=upload(),created_by=self.users['ADMIN_A'])
        for role in ('OPERATOR_A','REVIEWER_A'):
            self.as_user(role)
            self.assertEqual(self.run_action('muestras',sample,'HARD_DELETE').status_code,403)
            self.assertEqual(self.run_action('pacientes',self.da['pacientes'],'ARCHIVE').status_code,403)
            self.assertEqual(self.run_action('calibrations',self.da['calibrations'],'RETIRE').status_code,403)
        self.as_user('OPERATOR_A');sample.created_by_id=None
        # Legacy NULL creator is never "mine".
        MuestraSaliva.objects.filter(pk=sample.pk).update(created_by=None)
        self.assertEqual(self.run_action('muestras',sample,'HARD_DELETE').status_code,403)
        for role in ('ADMIN_A','OPERATOR_A','REVIEWER_A'):
            self.as_user(role)
            for route in self.db:
                self.assertEqual(self.preview(route,self.db[route]).status_code,404)
                for action in ('ARCHIVE','RESTORE','HARD_DELETE','RETIRE'):
                    self.assertEqual(self.run_action(route,self.db[route],action).status_code,404)
        self.as_user(self.superuser)
        self.assertEqual(self.run_action('muestras',sample,'HARD_DELETE').status_code,200)

    def test_series_used_archive_and_restore_context(self):
        series=self.da['acquisition-series'];sample=self.da['muestras']
        sample.acquisition_series=series;sample.save()
        self.assertEqual(self.run_action('acquisition-series',series,'HARD_DELETE').status_code,409)
        self.assertEqual(self.run_action('acquisition-series',series,'ARCHIVE').status_code,200)
        self.as_user('OPERATOR_A')
        response=self.client.post('/api/muestras/',{'analisis':self.da['analisis'].pk,'acquisition_series':series.pk,'imagen':upload()},format='multipart')
        self.assertEqual(response.status_code,400)
        self.as_user('ADMIN_A');profile=self.da['acquisition-profiles']
        self.run_action('acquisition-profiles',profile,'ARCHIVE')
        self.assertEqual(self.run_action('acquisition-series',series,'RESTORE').data['code'],'PROFILE_UNAVAILABLE')
        self.run_action('acquisition-profiles',profile,'RESTORE')
        self.run_action('calibrations',self.da['calibrations'],'RETIRE')
        self.assertEqual(self.run_action('acquisition-series',series,'RESTORE').data['code'],'CALIBRATION_RETIRED')
        # Existing sample/effective history survives metadata archival/retirement.
        self.assertEqual(self.client.get(f'/api/resultados-segmentacion/{self.da["resultados-segmentacion"].pk}/efectivo/').status_code,200)

    def test_empty_series_creator_and_unused_profile(self):
        series=self.da['acquisition-series']
        AcquisitionSeries.objects.filter(pk=series.pk).update(created_by=self.users['OPERATOR_A'])
        self.as_user('OPERATOR_A');self.assertEqual(self.run_action('acquisition-series',series,'HARD_DELETE').status_code,200)
        self.as_user('ADMIN_A')
        profile=AcquisitionProfile.objects.create(institution=self.a,name='Unused',image_width_px=32,image_height_px=32)
        self.assertEqual(self.run_action('acquisition-profiles',profile,'HARD_DELETE').status_code,200)

    def test_used_profile_scientific_lock_and_admin_metadata(self):
        profile=self.da['acquisition-profiles'];url=f'/api/acquisition-profiles/{profile.pk}/'
        self.assertEqual(self.run_action('acquisition-profiles',profile,'HARD_DELETE').status_code,409)
        self.assertEqual(self.client.patch(url,{'image_width_px':64},format='json').status_code,400)
        self.assertEqual(self.client.patch(url,{'notes':'Administrative note','name':'Updated label'},format='json').status_code,200)
        self.assertEqual(self.run_action('acquisition-profiles',profile,'ARCHIVE').status_code,200)
        self.assertEqual(self.client.post('/api/acquisition-series/',{'patient':self.da['pacientes'].pk,'acquisition_profile':profile.pk,'label':'Blocked'},format='json').status_code,400)

    def test_calibration_retire_immutable_snapshot_and_status_api_guard(self):
        result=self.da['resultados-segmentacion']
        response=self.client.post(f'/api/resultados-segmentacion/{result.pk}/caracterizar/')
        self.assertEqual(response.status_code,201)
        char=ResultadoCaracterizacion.objects.get();payload=copy.deepcopy(char.resultado_json)
        calibration=self.da['calibrations'];url=f'/api/calibrations/{calibration.pk}/'
        self.assertEqual(self.client.patch(url,{'status':'RETIRED'},format='json').status_code,400)
        self.assertEqual(self.client.patch(url,{'status':'VALIDATED'},format='json').status_code,400)
        self.assertEqual(self.run_action('calibrations',calibration,'HARD_DELETE').status_code,409)
        self.assertEqual(self.run_action('calibrations',calibration,'RETIRE').status_code,200)
        self.assertEqual(self.run_action('calibrations',calibration,'RESTORE').status_code,409)
        char.refresh_from_db();self.assertEqual(char.resultado_json,payload)
        self.assertEqual(self.run_action('characterizations',char,'HARD_DELETE').status_code,409)

    def test_unused_calibration_without_evidence_delete(self):
        calibration=Calibration.objects.create(acquisition_profile=self.da['acquisition-profiles'],label='Unused',scale_x_um_per_px='0.1',scale_y_um_per_px='0.1',source_width_px=32,source_height_px=32,method='synthetic',algorithm_version='test')
        self.assertEqual(self.run_action('calibrations',calibration,'HARD_DELETE').status_code,200)

    def test_revision_result_and_users_institutions_no_delete_even_platform(self):
        self.as_user(self.superuser)
        for route,obj in [('revisiones-segmentacion',self.da['revisiones-segmentacion']),('resultados-segmentacion',self.da['resultados-segmentacion']),('calibration-references',self.da['calibration-references']),('users',self.users['ADMIN_A']),('institutions',self.a)]:
            self.assertEqual(self.run_action(route,obj,'HARD_DELETE').status_code,409)

    def test_preview_not_authority_when_dependency_added(self):
        p=self.empty_patient();self.assertIn('HARD_DELETE',self.preview('pacientes',p).data['allowed_actions'])
        case=Caso.objects.create(paciente=p,titulo='New dependency')
        self.assertEqual(self.run_action('pacientes',p,'HARD_DELETE').status_code,409)
        self.assertTrue(Caso.objects.filter(pk=case.pk).exists());self.assertEqual(LifecycleEvent.objects.count(),0)

    def test_event_failure_rolls_back_archive(self):
        with patch('api.models.LifecycleEvent.objects.create',side_effect=RuntimeError('synthetic')):
            with self.assertRaises(RuntimeError):self.run_action('pacientes',self.da['pacientes'],'ARCHIVE')
        self.da['pacientes'].refresh_from_db();self.assertIsNone(self.da['pacientes'].archived_at)

    def test_ordinary_patch_cannot_set_lifecycle_fields(self):
        p=self.da['pacientes']
        self.client.patch(f'/api/pacientes/{p.pk}/',{'archived_at':'2026-01-01T00:00:00Z','archive_reason':'bypass'},format='json')
        p.refresh_from_db();self.assertIsNone(p.archived_at);self.assertEqual(p.archive_reason,'')

    def test_case_analysis_empty_delete_and_used_archive_nested_lists(self):
        p=self.empty_patient();case=Caso.objects.create(paciente=p,titulo='Empty')
        self.assertEqual(self.run_action('casos',case,'HARD_DELETE').status_code,200)
        case=Caso.objects.create(paciente=p,titulo='Empty analysis')
        analysis=AnalisisPred.objects.create(id_paciente_fk=p,id_caso_fk=case)
        self.assertEqual(self.run_action('analisis',analysis,'HARD_DELETE').status_code,200)
        used=self.da['analisis']
        self.assertEqual(self.run_action('analisis',used,'HARD_DELETE').status_code,409)
        self.assertEqual(self.run_action('analisis',used,'ARCHIVE').status_code,200)
        self.assertEqual(self.client.get(f'/api/casos/{self.da["casos"].pk}/analisis/').data,[])
        self.assertEqual(self.client.get(f'/api/casos/{self.da["casos"].pk}/resumen-segmentacion/').data['total_muestras'],0)
        self.assertEqual(self.run_action('analisis',used,'RESTORE').status_code,200)
        self.run_action('casos',self.da['casos'],'ARCHIVE')
        self.assertEqual(self.client.get(f'/api/pacientes/{self.da["pacientes"].pk}/casos/').data,[])

    def test_operator_cannot_include_archived(self):
        self.run_action('pacientes',self.da['pacientes'],'ARCHIVE');self.as_user('OPERATOR_A')
        self.assertEqual(self.client.get('/api/pacientes/?include_archived=true').data,[])
        self.assertEqual(self.client.get(f'/api/casos/{self.da["casos"].pk}/?include_archived=true').status_code,404)

    def test_unbound_pending_execution_blocks_archive_and_delete(self):
        from api.models import SegmentationExecution
        sample=MuestraSaliva.objects.create(analisis=self.da['analisis'],imagen=upload())
        execution=SegmentationExecution.objects.create(strategy='CURRENT_CUSTOM_V1',target='ALL',request_metadata={'sample_id':sample.pk})
        preview=self.preview('muestras',sample).data
        self.assertEqual(preview['allowed_actions'],[])
        self.assertEqual(preview['dependencies']['PendingSegmentationExecution'],1)
        self.assertIn({'code':'RESOURCE_BUSY'},preview['warnings'])
        self.assertEqual(self.run_action('muestras',sample,'ARCHIVE').status_code,409)
        execution.status='FAILED';execution.save()
        self.assertEqual(self.run_action('muestras',sample,'HARD_DELETE').status_code,409)
        self.assertEqual(self.run_action('muestras',sample,'ARCHIVE').status_code,200)

    def test_hard_delete_rollback_preserves_media_and_record(self):
        from django.db import transaction
        from api.services.lifecycle import execute_lifecycle
        sample=MuestraSaliva.objects.create(analisis=self.da['analisis'],imagen=upload());pk=sample.pk
        storage,name=sample.imagen.storage,sample.imagen.name
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            with self.assertRaises(RuntimeError), transaction.atomic():
                execute_lifecycle(sample,self.users['ADMIN_A'],'HARD_DELETE','Synthetic rollback')
                raise RuntimeError('rollback')
        self.assertEqual(callbacks,[])
        self.assertTrue(MuestraSaliva.objects.filter(pk=pk).exists());self.assertTrue(storage.exists(name))
        self.assertEqual(LifecycleEvent.objects.count(),0)

    def test_json_only_snapshot_reference_prevents_delete_and_profile_mutation(self):
        profile=AcquisitionProfile.objects.create(institution=self.a,name='Snapshot-bound',image_width_px=32,image_height_px=32)
        calibration=Calibration.objects.create(acquisition_profile=profile,label='Snapshot-bound',scale_x_um_per_px='0.1',scale_y_um_per_px='0.1',source_width_px=32,source_height_px=32,method='synthetic',algorithm_version='test')
        char=ResultadoCaracterizacion.objects.create(resultado_segmentacion=self.da['resultados-segmentacion'],source_type='AUTOMATICO',sample_type='SALIVA',algorithm_version='2.2',resultado_json={'calibration':{'calibration_id':calibration.pk,'acquisition_profile_id':profile.pk}})
        self.assertEqual(dependencies(calibration)['ResultadoCaracterizacion'],1)
        self.assertEqual(self.run_action('calibrations',calibration,'HARD_DELETE').status_code,409)
        self.assertEqual(self.run_action('characterizations',char,'ARCHIVE').status_code,409)
        self.assertEqual(self.client.patch(f'/api/acquisition-profiles/{profile.pk}/',{'image_width_px':64},format='json').status_code,400)

    def test_validated_revision_and_platform_console_delete_protected(self):
        from django.contrib import admin
        from django.test import RequestFactory
        from api.models import ResultadoSegmentacion
        draft=self.da['revisiones-segmentacion'];url=f'/api/revisiones-segmentacion/{draft.pk}/'
        self.assertEqual(self.client.post(url+'validar/').status_code,200)
        self.assertEqual(self.run_action('revisiones-segmentacion',draft,'HARD_DELETE').status_code,409)
        request=RequestFactory().get('/admin/');request.user=self.superuser
        for model in (ResultadoSegmentacion,RevisionSegmentacion,ResultadoCaracterizacion):
            self.assertFalse(admin.site._registry[model].has_delete_permission(request))

    def test_institution_deactivation_requires_warning_confirmation(self):
        self.as_user(self.superuser);url=f'/api/institutions/{self.b.pk}/'
        self.assertEqual(self.client.patch(url,{'active':False},format='json').status_code,400)
        self.b.refresh_from_db();self.assertTrue(self.b.active)
        self.assertEqual(self.client.patch(url,{'active':False,'confirm_deactivation':True},format='json').status_code,200)
        # A fresh request/session resolves the current institution, not a fixture's cached relation.
        self.as_user(type(self.superuser).objects.get(pk=self.users['ADMIN_B'].pk))
        self.assertEqual(self.client.get('/api/pacientes/').status_code,403)

    def test_new_relations_rejected_with_archived_ancestors(self):
        patient=self.da['pacientes'];self.run_action('pacientes',patient,'ARCHIVE')
        self.assertEqual(self.client.post('/api/casos/',{'paciente':patient.pk,'titulo':'Blocked'},format='json').status_code,400)
        self.assertEqual(self.client.post('/api/analisis/',{'id_paciente_fk':patient.pk,'id_caso_fk':self.da['casos'].pk},format='json').status_code,400)
        response=self.client.post('/api/muestras/',{'analisis':self.da['analisis'].pk,'imagen':upload()},format='multipart')
        self.assertEqual(response.status_code,400)

    def test_import_domain_does_not_reuse_archived_patient(self):
        from types import SimpleNamespace
        from api.services.imagej.importer import resolve_domain
        from api.services.imagej.contracts import ImportProblem
        p=self.da['pacientes']
        Paciente.objects.filter(pk=p.pk).update(external_id_namespace='synthetic',external_patient_id='01',initials='SYN')
        p.refresh_from_db();self.run_action('pacientes',p,'ARCHIVE')
        row=SimpleNamespace(external_id='01',initials='SYN',birth_date=p.fecha_nacimiento)
        with self.assertRaises(ImportProblem) as ctx:resolve_domain(row,'synthetic',institution=self.a)
        self.assertEqual(ctx.exception.code,'RESOURCE_ARCHIVED')

    def test_blood_result_not_persisted_if_sample_archived_during_call(self):
        sample=self.da['muestras-sangre']
        def remote(*args,**kwargs):
            self.assertEqual(self.run_action('muestras-sangre',sample,'ARCHIVE').status_code,200)
            return {'objetos':[{'id':1,'tipo':'nucleo','puntos':[[1,1],[3,1],[2,3]]}]}
        with patch('api.views.segment_image',side_effect=remote):
            response=self.client.post(f'/api/muestras-sangre/{sample.pk}/segmentar/',{},format='json')
        self.assertEqual(response.status_code,409,response.data)
        self.assertFalse(sample.resultados_segmentacion.exists())
