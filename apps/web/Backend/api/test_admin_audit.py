"""Read-only administrative surfaces, with isolated tenant/storage fixtures."""
import copy
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from api import test_access as fixtures
from api.models import LifecycleEvent, Paciente, Calibration, AcquisitionSeries

@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class AdministrativeAuditTests(TestCase):
    user=fixtures.AccessTests.user
    domain=fixtures.AccessTests.domain
    as_user=fixtures.AccessTests.as_user
    setUp=fixtures.AccessTests.setUp

    def event(self,tenant=None,**metadata):
        return LifecycleEvent.objects.create(institution=tenant or self.a,actor=self.users['ADMIN_A'],action='HARD_DELETE',target_type='paciente',target_id='999999',reason='Synthetic audit test',metadata={'dependencies':{},'password':'must-not-leak','token':'must-not-leak',**metadata})

    def test_roles_scopes_immutability(self):
        a,b=self.event(),self.event(self.b)
        for role in ['OPERATOR_A','REVIEWER_A']:
            self.as_user(role)
            for path in ['events/','options/','archived/','health/']:self.assertEqual(self.client.get('/api/admin-audit/'+path).status_code,403)
        self.as_user('ADMIN_A');data=self.client.get('/api/admin-audit/events/').data
        self.assertEqual(data['count'],1);self.assertEqual(data['results'][0]['id'],a.pk)
        self.assertEqual(self.client.get(f'/api/admin-audit/events/{b.pk}/').status_code,404)
        for path in ['events/','options/','archived/','health/']:self.assertEqual(self.client.get('/api/admin-audit/'+path,{'institution':self.b.pk}).status_code,404)
        for role in ['ADMIN_A',self.superuser]:
            self.as_user(role);self.assertEqual(self.client.post('/api/admin-audit/events/',{},format='json').status_code,405)
            for method in ('patch','delete'):self.assertEqual(getattr(self.client,method)(f'/api/admin-audit/events/{a.pk}/',{},format='json').status_code,405)
        self.assertEqual(self.client.get('/api/admin-audit/events/').data['count'],2)
        self.assertEqual(self.client.get('/api/admin-audit/events/',{'institution':self.b.pk}).data['count'],1)

    def test_pagination_filters_dates_options(self):
        events=[self.event() for _ in range(28)];LifecycleEvent.objects.filter(pk=events[0].pk).update(created_at=timezone.now()-timedelta(days=4))
        data=self.client.get('/api/admin-audit/events/').data;self.assertEqual(len(data['results']),25);self.assertIsNotNone(data['next'])
        self.assertEqual(len(self.client.get('/api/admin-audit/events/',{'page':2}).data['results']),3)
        today=timezone.localdate().isoformat()
        data=self.client.get('/api/admin-audit/events/',{'date_from':today,'date_to':today,'action':'HARD_DELETE','target_type':'paciente','actor':self.users['ADMIN_A'].pk}).data
        self.assertEqual(data['count'],27)
        for params in [{'action':'PURGE'},{'target_type':'made-up'},{'actor':'x'},{'date_from':'nonsense'},{'date_from':'2026-02-03','date_to':'2026-02-01'}]:self.assertEqual(self.client.get('/api/admin-audit/events/',params).status_code,400)
        options=self.client.get('/api/admin-audit/options/').data;self.assertEqual(options['actions'],['HARD_DELETE'])
        self.assertNotIn(self.users['ADMIN_B'].pk,[u['id'] for u in options['actors']])

    def test_deleted_target_private_metadata_test_evidence(self):
        e=self.event(media_cleanup=[{'filename':'TEST_LIFECYCLE_example.png','sha256':'a'*64,'status':'DELETED','path':'/private/secret','password':'secret'}])
        data=self.client.get(f'/api/admin-audit/events/{e.pk}/').data
        self.assertTrue(data['target_deleted']);self.assertTrue(data['is_test'])
        for secret in ['must-not-leak','/private/secret','password']:self.assertNotIn(secret,str(data))
        e=self.event();self.assertFalse(self.client.get(f'/api/admin-audit/events/{e.pk}/').data['is_test'])
        self.assertEqual(LifecycleEvent.objects.get(pk=e.pk).metadata['password'],'must-not-leak')

    def test_current_target_safe_description(self):
        p=self.da['pacientes'];p.nombre='TEST_LIFECYCLE_CONTROL';p.save()
        e=LifecycleEvent.objects.create(institution=self.a,actor=self.users['ADMIN_A'],action='ARCHIVE',target_type='paciente',target_id=str(p.pk),reason='Synthetic',metadata={})
        data=self.client.get(f'/api/admin-audit/events/{e.pk}/').data
        self.assertFalse(data['target_deleted']);self.assertTrue(data['is_test']);self.assertEqual(data['description'],f'paciente #{p.pk}')

    def test_archived_filters_restore_conflicts(self):
        p,other,case=self.da['pacientes'],self.db['pacientes'],self.da['casos']
        for obj in [p,other,case]:type(obj).objects.filter(pk=obj.pk).update(archived_at=timezone.now(),archived_by=self.users['ADMIN_A'],archive_reason='Synthetic')
        r=self.client.get('/api/admin-audit/archived/',{'type':'pacientes','archived_by':self.users['ADMIN_A'].pk,'search':str(p.pk)})
        self.assertEqual(r.data['count'],1);self.assertEqual(r.data['results'][0]['id'],p.pk)
        self.assertEqual(self.client.get('/api/admin-audit/archived/',{'type':'pacientes','search':str(other.pk)}).data['count'],0)
        self.assertEqual(self.client.get('/api/admin-audit/archived/',{'type':'bogus'}).status_code,400)
        data={'action':'RESTORE','reason':'Synthetic restore','confirm':True}
        r=self.client.post(f'/api/lifecycle/casos/{case.pk}/',data,format='json');self.assertEqual(r.status_code,409);self.assertEqual(r.data['code'],'PARENT_ARCHIVED')
        self.assertEqual(self.client.post(f'/api/lifecycle/pacientes/{p.pk}/',data,format='json').status_code,200)
        self.assertEqual(self.client.get('/api/admin-audit/archived/',{'type':'pacientes'}).data['count'],0)
        self.assertEqual(self.client.get('/api/admin-audit/archived/',{'type':'casos'}).data['count'],1)

    def test_retired_metrics_and_user_dates(self):
        c=self.da['calibrations'];c.status='RETIRED';c.save()
        data=self.client.get('/api/admin-audit/archived/',{'type':'calibrations'}).data
        self.assertEqual(data['count'],1);self.assertEqual(data['results'][0]['status'],'RETIRED')
        inst=self.client.get('/api/institutions/').data;self.assertEqual(len(inst),1);self.assertEqual(inst[0]['operational_summary']['active_admins'],1)
        users=self.client.get('/api/users/').data
        for field in ['last_login','date_joined','must_change_password']:self.assertIn(field,users[0])
        self.as_user('OPERATOR_A');self.assertIsNone(self.client.get('/api/institutions/').data[0]['operational_summary'])

    def health(self,files=False):
        r=self.client.get('/api/admin-audit/health/',{'check_files':str(files).lower()});self.assertEqual(r.status_code,200,r.data)
        return {i['code']:i for i in r.data['checks']}

    def test_health_readonly_no_implicit_file_checks(self):
        before=copy.deepcopy(list(Paciente.objects.values()))
        with patch('django.core.files.storage.filesystem.FileSystemStorage.exists',side_effect=AssertionError('No I/O')):checks=self.health()
        self.assertEqual(checks['DATABASE_CONNECTIVITY']['status'],'OK');self.assertEqual(checks['MEDIA_REFERENCES']['status'],'NOT_CHECKED')
        self.assertEqual(checks['LEGACY_INSTITUTION_OWNERSHIP']['status'],'PLATFORM_ONLY');self.assertEqual(checks['AUTHORSHIP_CONSISTENCY']['count'],0)
        self.assertEqual(list(Paciente.objects.values()),before);self.assertEqual(LifecycleEvent.objects.count(),0)

    def test_health_missing_files_tenant_scoped(self):
        own,other=self.da['muestras'],self.db['muestras']
        own.imagen.storage.delete(own.imagen.name);other.imagen.storage.delete(other.imagen.name)
        issues=self.health(True)['MEDIA_REFERENCES']['issues']
        self.assertTrue(any(i['resource_type']=='muestrasaliva' and i['id']==own.pk for i in issues))
        self.assertFalse(any(i['resource_type']=='muestrasaliva' and i['id']==other.pk for i in issues))

    def test_health_legacy_and_incomplete_profiles_platform_only(self):
        p=Paciente.objects.create(nombre='Synthetic',apellido='Only',identificacion='legacy-audit',fecha_nacimiento='2000-01-01')
        u=get_user_model().objects.create_user('unowned-synthetic')
        self.as_user(self.superuser);checks=self.health()
        self.assertIn(p.pk,[i['id'] for i in checks['LEGACY_INSTITUTION_OWNERSHIP']['issues']]);self.assertIn(u.pk,[i['id'] for i in checks['USER_PROFILES']['issues']])
        self.as_user('ADMIN_A');self.assertEqual(self.health()['USER_PROFILES']['count'],0)

    def test_health_inconsistent_acquisition_and_author(self):
        Calibration.objects.filter(pk=self.da['calibrations'].pk).update(source_width_px=99)
        AcquisitionSeries.objects.filter(pk=self.da['acquisition-series'].pk).update(acquisition_profile=self.db['acquisition-profiles'])
        Paciente.objects.filter(pk=self.da['pacientes'].pk).update(created_by=self.users['ADMIN_B'])
        checks=self.health()
        for name in ['CALIBRATION_PROFILE_CONSISTENCY','SERIES_PATIENT_INSTITUTION_CONSISTENCY','AUTHORSHIP_CONSISTENCY']:self.assertEqual(checks[name]['count'],1)

    @override_settings(PRIVATE_MEDIA_DELIVERY='nginx')
    def test_x_accel_requires_permission_and_internal_url(self):
        sample=self.da['muestras'];url=f'/api/private-media/saliva/{sample.pk}/'
        r=self.client.get(url);self.assertEqual(r.status_code,200);self.assertTrue(r['X-Accel-Redirect'].startswith('/_sicam_private_media/'));self.assertEqual(r.content,b'');self.assertEqual(r['Cache-Control'],'private, no-store')
        self.assertEqual(self.client.get(r['X-Accel-Redirect']).status_code,404);self.assertEqual(self.client.get(sample.imagen.url).status_code,404)
        self.as_user('ADMIN_B');self.assertEqual(self.client.get(url).status_code,404)
        self.as_user(None);self.assertEqual(self.client.get(url).status_code,403)

    @override_settings(PRIVATE_MEDIA_DELIVERY='nginx')
    def test_x_accel_missing_and_escape_denied(self):
        sample=self.da['muestras'];path=Path(sample.imagen.path);path.unlink()
        self.assertEqual(self.client.get(f'/api/private-media/saliva/{sample.pk}/').status_code,404)
        path.symlink_to('/etc/hosts');self.assertEqual(self.client.get(f'/api/private-media/saliva/{sample.pk}/').status_code,404);path.unlink()

    def test_admin_console_event_readonly(self):
        from django.contrib import admin
        from django.test import RequestFactory
        r=RequestFactory().get('/admin/');r.user=self.superuser;m=admin.site._registry[LifecycleEvent]
        self.assertFalse(m.has_add_permission(r));self.assertFalse(m.has_change_permission(r));self.assertFalse(m.has_delete_permission(r))

    def test_sensitive_admin_reads_never_cache_and_cleanup_warning_scoped(self):
        e=self.event(media_cleanup=[{'status':'MEDIA_DELETE_FAILED'}])
        self.event(self.b,media_cleanup=[{'status':'PENDING_DELETE'}])
        response=self.client.get('/api/admin-audit/events/')
        self.assertEqual(response['Cache-Control'],'private, no-store')
        check=self.health()['LIFECYCLE_CONSISTENCY'];self.assertEqual(check['count'],1);self.assertEqual(check['issues'][0]['id'],e.pk)

    def test_all_media_kinds_authorized_for_both_delivery_modes(self):
        from api.models import ImageJImportRecord
        from django.core.files.uploadedfile import SimpleUploadedFile
        record=ImageJImportRecord.objects.create(dataset_key='synthetic',patient_namespace='test',external_patient_id='test',patient_key='test',case_number=1,logical_basename='synthetic',image_sha256='a'*64,mask_sha256='b'*64,sample_key='c'*64,annotation_key='d'*64,logical_key='e'*64,converter_version='test',contract_version='test',source_mask_file=SimpleUploadedFile('synthetic.tif',b'synthetic-test-only'),paciente=self.da['pacientes'],caso=self.da['casos'],muestra=self.da['muestras'],resultado=self.da['resultados-segmentacion'])
        targets=[('saliva',self.da['muestras'].pk),('sangre',self.da['muestras-sangre'].pk),('calibration',self.da['calibration-references'].pk),('imagej-mask',record.pk)]
        Paciente.objects.filter(pk=self.da['pacientes'].pk).update(archived_at=timezone.now(),archive_reason='Synthetic')
        for delivery in ['django','nginx']:
            with override_settings(PRIVATE_MEDIA_DELIVERY=delivery):
                for kind,pk in targets:
                    url=f'/api/private-media/{kind}/{pk}/'
                    self.as_user('ADMIN_A');response=self.client.get(url);self.assertEqual(response.status_code,200);response.close()
                    self.as_user('ADMIN_B');self.assertEqual(self.client.get(url).status_code,404)
                    self.as_user(None);self.assertEqual(self.client.get(url).status_code,403)

    def test_derived_authorship_and_orphan_fk_detection_on_platform(self):
        from api.models import RevisionSegmentacion, MuestraSaliva
        revision=self.da['revisiones-segmentacion'];RevisionSegmentacion.objects.filter(pk=revision.pk).update(created_by=self.users['ADMIN_B'])
        self.assertTrue(any(i['resource_type']=='revisionsegmentacion' for i in self.health()['AUTHORSHIP_CONSISTENCY']['issues']))
        sample=self.da['muestras'];original=sample.analisis_id
        try:
            MuestraSaliva.objects.filter(pk=sample.pk).update(analisis_id=999999)
            self.as_user(self.superuser)
            issues=self.health()['ORPHAN_REFERENCES']['issues']
            self.assertTrue(any(i['resource_type']=='muestrasaliva' and i['id']==sample.pk for i in issues))
        finally:
            MuestraSaliva.objects.filter(pk=sample.pk).update(analisis_id=original)


    def test_retired_time_and_actor_come_from_event_not_later_notes(self):
        c=self.da['calibrations']
        response=self.client.post(f'/api/lifecycle/calibrations/{c.pk}/',{'action':'RETIRE','reason':'Synthetic','confirm':True},format='json')
        self.assertEqual(response.status_code,200)
        event=LifecycleEvent.objects.get(pk=response.data['event_id'])
        # Simulate a later administrative note, without rewriting the retirement event.
        Calibration.objects.filter(pk=c.pk).update(updated_at=timezone.now()+timedelta(days=2),updated_by=self.users['OPERATOR_A'])
        data=self.client.get('/api/admin-audit/archived/',{'type':'calibrations','archived_by':self.users['ADMIN_A'].pk}).data
        self.assertEqual(data['count'],1)
        self.assertEqual(data['results'][0]['archived_at'],event.created_at)
        self.assertEqual(data['results'][0]['archived_by'],self.users['ADMIN_A'].pk)
        e=self.event();LifecycleEvent.objects.filter(pk=e.pk).update(metadata=[])
        self.assertEqual(self.client.get(f'/api/admin-audit/events/{e.pk}/').status_code,200)
