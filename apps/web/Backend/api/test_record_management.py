"""18U-A: isolated DB/storage only. No engines, imports or real records."""
import copy
from tempfile import TemporaryDirectory
from unittest.mock import patch
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from rest_framework.test import APIClient
from api.models import (Institution, SicamUserProfile, Paciente, Caso, AnalisisPred, MuestraSaliva,
 MuestraSangre, AcquisitionProfile, Calibration, AcquisitionSeries, LifecycleEvent, ResultadoCaracterizacion,
 ResultadoSegmentacion)
from api.test_acquisition import upload, image_bytes
from api.services.acquisition import physical_compatibility

@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class RecordManagementTests(TestCase):
    def setUp(self):
        temp=TemporaryDirectory();self.addCleanup(temp.cleanup)
        media=override_settings(MEDIA_ROOT=temp.name);media.enable();self.addCleanup(media.disable)
        self.tenant=Institution.objects.create(code='TEST_U',name='Synthetic')
        self.other_tenant=Institution.objects.create(code='OTHER_U',name='Synthetic')
        self.users={}
        for role in ['ADMIN','OPERATOR','REVIEWER']:
            u=get_user_model().objects.create_user(role);SicamUserProfile.objects.create(user=u,institution=self.tenant,role=role,must_change_password=False);self.users[role]=u
        self.patient,self.analysis=self.context('A',self.tenant)
        self.other,self.other_analysis=self.context('B',self.tenant)
        self.foreign,self.foreign_analysis=self.context('C',self.other_tenant)
        self.profile=AcquisitionProfile.objects.create(institution=self.tenant,name='TEST',image_width_px=32,image_height_px=32,image_mode='RGB')
        self.cal=Calibration.objects.create(acquisition_profile=self.profile,label='TEST',scale_x_um_per_px='.1',scale_y_um_per_px='.2',source_width_px=32,source_height_px=32,method='synthetic',algorithm_version='test')
        self.series=AcquisitionSeries.objects.create(patient=self.patient,acquisition_profile=self.profile,calibration=self.cal,label='TEST')
        self.sample=self.sample_for();self.client=APIClient();self.client.force_authenticate(self.users['ADMIN'])

    def context(self,key,tenant):
        p=Paciente.objects.create(institution=tenant,nombre='PRIVATE',apellido='NEVER EXPOSE',identificacion=key,fecha_nacimiento='2000-01-01')
        c=Caso.objects.create(paciente=p,titulo='PRIVATE CASE')
        return p,AnalisisPred.objects.create(id_paciente_fk=p,id_caso_fk=c)
    def sample_for(self,model=MuestraSaliva,analysis=None,**kwargs):
        return model.objects.create(analisis=analysis or self.analysis,imagen=upload(kwargs.pop('content',None)),**kwargs)
    def payload(self,samples=None,series=None):
        return {'series_id':(series or self.series).pk,'samples':[{'type':'SANGRE' if isinstance(s,MuestraSangre) else 'SALIVA','id':s.pk} for s in (samples or [self.sample])]}
    def preview(self,data=None):return self.client.post('/api/record-management/series/preview/',data or self.payload(),format='json')
    def assign(self,data=None):
        data=data or self.payload();p=self.preview(data);self.assertEqual(p.status_code,200,p.data)
        return self.client.post('/api/record-management/series/assign/',{**data,'preview_token':p.data['preview_token'],'confirm':True},format='json')

    def test_preview_has_zero_writes_and_compatible_assignment(self):
        response=self.preview();self.assertEqual(response.status_code,200,response.data)
        self.assertEqual(response.data['results'][0]['compatibility']['status'],'COMPATIBLE_PROVISIONAL')
        self.sample.refresh_from_db();self.assertIsNone(self.sample.acquisition_series_id)
        self.assertEqual(self.assign().status_code,200);self.sample.refresh_from_db();self.assertEqual(self.sample.acquisition_series_id,self.series.pk)
        self.assertEqual(LifecycleEvent.objects.count(),0);self.assertEqual(ResultadoCaracterizacion.objects.count(),0)

    def test_bulk_saliva_blood_same_patient_and_idempotence(self):
        blood=self.sample_for(MuestraSangre);data=self.payload([self.sample,blood])
        self.assertEqual(self.assign(data).status_code,200);r=self.assign(data)
        self.assertTrue(all(x['already_assigned'] for x in r.data['results']))
        self.assertEqual(MuestraSaliva.objects.count(),1);self.assertEqual(MuestraSangre.objects.count(),1)

    def test_mixed_patient_and_foreign_series_blocked(self):
        s=self.sample_for(analysis=self.other_analysis)
        self.assertEqual(self.preview(self.payload([self.sample,s])).status_code,409)
        series=AcquisitionSeries.objects.create(patient=self.other,acquisition_profile=self.profile,label='OTHER')
        self.assertEqual(self.preview(self.payload(series=series)).status_code,409)
        self.sample.refresh_from_db();self.assertIsNone(self.sample.acquisition_series_id)

    def test_cross_tenant_and_reviewer_denied(self):
        s=self.sample_for(analysis=self.foreign_analysis)
        self.assertEqual(self.preview(self.payload([self.sample,s])).status_code,404)
        self.client.force_authenticate(self.users['REVIEWER']);self.assertEqual(self.preview().status_code,403)
        self.assertEqual(self.client.get('/api/record-management/images/').status_code,200)

    def test_operator_uses_existing_institution_write_policy(self):
        self.client.force_authenticate(self.users['OPERATOR']);self.assertEqual(self.assign().status_code,200)

    def test_invalid_series_duplicates_and_confirmation(self):
        data=self.payload();data['series_id']=9999;self.assertEqual(self.preview(data).status_code,404)
        data=self.payload([self.sample,self.sample]);self.assertEqual(self.preview(data).status_code,400)
        p=self.preview();r=self.client.post('/api/record-management/series/assign/',{**self.payload(),'preview_token':p.data['preview_token']},format='json');self.assertEqual(r.status_code,400)

    def test_existing_series_and_physical_snapshot_unchanged(self):
        self.assertEqual(self.assign().status_code,200)
        result=ResultadoSegmentacion.objects.create(muestra=self.sample,tipo_muestra='SALIVA',estado='COMPLETADO',respuesta_json={},resultado_normalizado={})
        char=ResultadoCaracterizacion.objects.create(resultado_segmentacion=result,source_type='AUTOMATICO',algorithm_version='2.2',resultado_json={'snapshot':'synthetic'})
        before=copy.deepcopy(char.resultado_json)
        other=AcquisitionSeries.objects.create(patient=self.patient,acquisition_profile=self.profile,label='OTHER')
        self.assertEqual(self.preview(self.payload(series=other)).status_code,409)
        char.refresh_from_db();self.assertEqual(before,char.resultado_json)

    def test_no_series_physical_history_is_not_rewritten(self):
        result=ResultadoSegmentacion.objects.create(muestra=self.sample,tipo_muestra='SALIVA',estado='COMPLETADO',respuesta_json={})
        c=ResultadoCaracterizacion.objects.create(resultado_segmentacion=result,source_type='AUTOMATICO',algorithm_version='2.2',resultado_json={'physical_status':'NO_ACQUISITION_SERIES'})
        self.assertEqual(self.assign().status_code,200);c.refresh_from_db()
        self.assertEqual(c.resultado_json,{'physical_status':'NO_ACQUISITION_SERIES'});self.assertEqual(ResultadoCaracterizacion.objects.count(),1)

    def test_resolution_and_mode_mismatch_associate_without_physical_units(self):
        for content,status in [(image_bytes((16,16)),'RESOLUTION_MISMATCH'),(image_bytes(mode='L'),'IMAGE_MODE_MISMATCH')]:
            s=self.sample_for(content=content);r=self.assign(self.payload([s]));self.assertEqual(r.status_code,200)
            c=r.data['results'][0]['compatibility'];self.assertEqual(c['status'],status);self.assertFalse(c['compatible_for_physical_units'])

    def test_no_calibration_allowed_retired_blocked(self):
        plain=AcquisitionSeries.objects.create(patient=self.patient,acquisition_profile=self.profile,label='NO CAL')
        r=self.assign(self.payload(series=plain));self.assertEqual(r.data['results'][0]['compatibility']['status'],'NO_CALIBRATION')
        self.cal.status='RETIRED';self.cal.save();fresh=self.sample_for()
        self.assertEqual(self.preview(self.payload([fresh])).status_code,409)
        options=self.client.get('/api/record-management/series/',{'patient':self.patient.pk}).data
        self.assertNotIn(self.series.pk,[x['id'] for x in options])

    def test_archived_and_stale_preview_blocked(self):
        from django.utils import timezone
        p=self.preview();self.sample.archived_at=timezone.now();self.sample.save()
        r=self.client.post('/api/record-management/series/assign/',{**self.payload(),'preview_token':p.data['preview_token'],'confirm':True},format='json');self.assertEqual(r.status_code,409)
        self.sample.archived_at=None;self.sample.save();p=self.preview();self.series.label='Changed';self.series.save()
        r=self.client.post('/api/record-management/series/assign/',{**self.payload(),'preview_token':p.data['preview_token'],'confirm':True},format='json');self.assertEqual(r.status_code,409)

    def test_transaction_rollback_after_second_save_failure(self):
        other=self.sample_for();data=self.payload([self.sample,other]);preview=self.preview(data);original=MuestraSaliva.save
        def save(obj,*args,**kwargs):
            if obj.pk==other.pk:raise ValidationError('Synthetic write failure')
            return original(obj,*args,**kwargs)
        with patch.object(MuestraSaliva,'save',save):
            r=self.client.post('/api/record-management/series/assign/',{**data,'preview_token':preview.data['preview_token'],'confirm':True},format='json')
        self.assertEqual(r.status_code,400);self.sample.refresh_from_db();self.assertIsNone(self.sample.acquisition_series_id)

    def test_lists_pagination_filters_privacy_and_scoping(self):
        self.sample_for(analysis=self.foreign_analysis)
        for route in ['patients','cases','images']:
            r=self.client.get('/api/record-management/'+route+'/');self.assertEqual(r.status_code,200,r.data)
            self.assertNotIn('PRIVATE',str(r.data));self.assertNotIn('fecha_nacimiento',str(r.data))
        r=self.client.get('/api/record-management/images/',{'patient':self.patient.pk,'series':'none','type':'SALIVA'})
        self.assertEqual(r.data['count'],1);self.assertIsNone(r.data['results'][0]['series'])
        self.assertEqual(r.data['results'][0]['dimensions'],{'width':32,'height':32})
        self.assertEqual(self.client.get('/api/record-management/images/',{'page':'bad'}).status_code,400)
        for _ in range(21):self.sample_for()
        r=self.client.get('/api/record-management/images/',{'page':2});self.assertEqual(len(r.data['results']),2)

    def test_page_query_count_does_not_grow_per_image(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        self.assign()
        with CaptureQueriesContext(connection) as one:self.client.get('/api/record-management/images/')
        for _ in range(5):self.sample_for(acquisition_series=self.series)
        with CaptureQueriesContext(connection) as many:self.client.get('/api/record-management/images/')
        self.assertLessEqual(len(many),len(one)+1)

    def test_batched_compatibility_equals_existing_contract(self):
        self.assign();self.sample.refresh_from_db()
        self.assertEqual(physical_compatibility(self.sample),physical_compatibility(self.sample,series=self.sample.acquisition_series,patient_id=self.patient.pk))

    def test_retry_identical_confirmed_request_is_noop(self):
        data=self.payload();p=self.preview(data);body={**data,'preview_token':p.data['preview_token'],'confirm':True}
        for _ in range(2):
            r=self.client.post('/api/record-management/series/assign/',body,format='json');self.assertEqual(r.status_code,200,r.data)
        self.assertTrue(r.data['results'][0]['already_assigned'])
        self.assertEqual(LifecycleEvent.objects.count(),0)

    def test_tampered_token_and_unavailable_profile_blocked(self):
        p=self.preview();r=self.client.post('/api/record-management/series/assign/',{**self.payload(),'preview_token':p.data['preview_token']+'bad','confirm':True},format='json')
        self.assertEqual(r.status_code,409)
        self.profile.active=False;self.profile.save()
        self.assertEqual(self.preview().status_code,409)
        self.assertEqual(self.client.get('/api/record-management/series/',{'patient':self.patient.pk}).data,[])

    def test_archived_listing_roles_and_patient_series_options(self):
        from django.utils import timezone
        self.sample.archived_at=timezone.now();self.sample.save()
        self.assertEqual(self.client.get('/api/record-management/images/').data['count'],0)
        self.assertEqual(self.client.get('/api/record-management/images/',{'include_archived':'true'}).data['count'],1)
        self.client.force_authenticate(self.users['OPERATOR'])
        self.assertEqual(self.client.get('/api/record-management/images/',{'include_archived':'true'}).data['count'],0)
        self.assertEqual(self.client.get('/api/record-management/series/',{'patient':self.foreign.pk}).status_code,404)
        self.assertEqual(self.client.get('/api/record-management/series/',{'patient':self.other.pk}).data,[])

    def pseudonymize(self, patient, initials='EJT'):
        patient.identity_mode='PSEUDONYMIZED';patient.nombre='';patient.apellido=''
        patient.initials=initials;patient.external_id_namespace='HOSPITAL'
        patient.external_patient_id='EXT-'+patient.identificacion
        patient.full_clean();patient.save()

    def test_lookup_duplicate_initials_minimal_identity_and_tenant_roles(self):
        for p in [self.patient,self.other,self.foreign]:self.pseudonymize(p)
        for role in self.users:
            self.client.force_authenticate(self.users[role])
            r=self.client.get('/api/pacientes/lookup/',{'q':'ej'})
            self.assertEqual(r.status_code,200,r.data)
            self.assertEqual([x['id'] for x in r.data['results']],[self.patient.pk,self.other.pk])
            self.assertEqual({x['identificacion'] for x in r.data['results']},{'A','B'})
            for item in r.data['results']:
                self.assertEqual(set(item),{'id','initials','identificacion','identity_mode','external_id_namespace','external_patient_id'})
        admin=get_user_model().objects.create_superuser(username='platform',password='synthetic')
        self.client.force_authenticate(admin)
        self.assertEqual(self.client.get('/api/pacientes/lookup/',{'q':'EJT'}).data['count'],3)

    def test_lookup_shared_fields_with_management_and_empty(self):
        self.pseudonymize(self.patient)
        for query in ['ejt','EXT-A','hospital']:
            lookup=self.client.get('/api/pacientes/lookup/',{'q':query}).data
            management=self.client.get('/api/record-management/patients/',{'search':query}).data
            self.assertEqual([x['id'] for x in lookup['results']],[self.patient.pk])
            self.assertEqual([x['id'] for x in management['results']],[self.patient.pk])
        self.assertEqual(self.client.get('/api/pacientes/lookup/',{'q':'B'}).data['results'][0]['id'],self.other.pk)
        self.assertEqual(self.client.get('/api/pacientes/lookup/',{'q':'no-match'}).data['count'],0)
        self.assertEqual(self.client.get('/api/pacientes/lookup/',{'q':'PRIVATE'}).data['count'],0)

    def test_lookup_archive_policy_and_unauthenticated(self):
        from django.utils import timezone
        self.pseudonymize(self.patient)
        self.patient.archived_at=timezone.now();self.patient.save()
        self.assertEqual(self.client.get('/api/pacientes/lookup/',{'q':'EJT'}).data['count'],0)
        self.assertEqual(self.client.get('/api/pacientes/lookup/',{'q':'EJT','include_archived':'true'}).data['count'],1)
        for role in ['OPERATOR','REVIEWER']:
            self.client.force_authenticate(self.users[role])
            self.assertEqual(self.client.get('/api/pacientes/lookup/',{'q':'EJT','include_archived':'true'}).data['count'],0)
        self.client.force_authenticate(None)
        self.assertIn(self.client.get('/api/pacientes/lookup/').status_code,[401,403])

    def test_lookup_pagination_is_bounded_and_stable(self):
        for index in range(23):
            patient,_=self.context(f'LOOKUP-{index:02}',self.tenant)
        first=self.client.get('/api/pacientes/lookup/',{'q':'lookup'}).data
        second=self.client.get('/api/pacientes/lookup/',{'q':'lookup','page':2}).data
        self.assertEqual(first['count'],23);self.assertEqual(len(first['results']),20)
        self.assertEqual(len(second['results']),3)
        self.assertFalse({x['id'] for x in first['results']} & {x['id'] for x in second['results']})
        self.assertEqual(self.client.get('/api/pacientes/lookup/',{'page':'invalid'}).status_code,404)

    def test_context_filters_use_actual_fk_with_duplicate_initials(self):
        for p in [self.patient,self.other]:self.pseudonymize(p)
        other_sample=self.sample_for(analysis=self.other_analysis)
        case=self.other_analysis.id_caso_fk_id
        cases=self.client.get('/api/record-management/cases/',{'patient':self.other.pk}).data['results']
        self.assertEqual([x['id'] for x in cases],[case])
        self.assertEqual(cases[0]['patient_identity']['identificacion'],'B')
        images=self.client.get('/api/record-management/images/',{'patient':self.other.pk,'case':case}).data['results']
        self.assertEqual([x['id'] for x in images],[other_sample.pk])
        self.assertEqual(images[0]['patient_identity']['id'],self.other.pk)
        for invalid in [self.patient.pk,self.foreign.pk]:
            self.assertEqual(self.client.get('/api/record-management/images/',{'patient':invalid,'case':case}).data['count'],0)
