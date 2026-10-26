"""Tenant boundary tests with real session/CSRF and synthetic isolated storage."""
import copy
import hashlib
from io import StringIO
from tempfile import TemporaryDirectory
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.management import call_command, CommandError
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from api.models import (Institution, SicamUserProfile, Paciente, Caso, AnalisisPred, MuestraSaliva,
    MuestraSangre, AcquisitionProfile, AcquisitionSeries, Calibration, CalibrationReference,
    ResultadoSegmentacion, RevisionSegmentacion, ResultadoCaracterizacion)
from api.test_acquisition import upload, image_bytes
from api.services.segmentation.normalizers import normalize_segmentation_result
from api.services.segmentation.revisions import build_revision_snapshot_from_normalized, calculate_revision_summary

User = get_user_model()
PASSWORD = 'Synthetic-only-938!X'
RAW = {'objetos': [{'id': 1, 'tipo': 'membrana', 'puntos': [[2,2],[25,2],[25,25],[2,25]]},
                   {'id': 1, 'tipo': 'nucleo', 'puntos': [[5,5],[10,5],[10,10],[5,10]]}]}


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class AccessTests(TestCase):
    def setUp(self):
        directory = TemporaryDirectory(); self.addCleanup(directory.cleanup)
        config = override_settings(MEDIA_ROOT=directory.name); config.enable(); self.addCleanup(config.disable)
        self.a = Institution.objects.create(code='A', name='Synthetic A')
        self.b = Institution.objects.create(code='B', name='Synthetic B')
        self.users = {f'{role}_{tenant.code}': self.user(role, tenant) for tenant in (self.a,self.b) for role in ('ADMIN','OPERATOR','REVIEWER')}
        self.superuser = User.objects.create_superuser('platform', password=PASSWORD)
        self.client = APIClient()
        self.da, self.db = self.domain(self.a), self.domain(self.b)
        self.as_user('ADMIN_A')

    def user(self, role, institution, **kwargs):
        user = User.objects.create_user(f'{role}_{institution.code}', password=PASSWORD)
        SicamUserProfile.objects.create(user=user, institution=institution, role=role, must_change_password=False, **kwargs)
        return user

    def as_user(self, key):
        self.client.force_authenticate(self.users[key] if isinstance(key,str) else key)

    def domain(self, tenant):
        patient = Paciente.objects.create(institution=tenant, nombre='Synthetic', apellido='Fixture', identificacion='same-id', fecha_nacimiento='2000-01-01')
        case = Caso.objects.create(paciente=patient, titulo='Synthetic', case_number=1)
        analysis = AnalisisPred.objects.create(id_paciente_fk=patient,id_caso_fk=case)
        saliva = MuestraSaliva.objects.create(analisis=analysis,imagen=upload())
        blood = MuestraSangre.objects.create(analisis=analysis,imagen=upload())
        profile = AcquisitionProfile.objects.create(institution=tenant,name='Synthetic',image_width_px=32,image_height_px=32)
        calibration = Calibration.objects.create(acquisition_profile=profile,label='Synthetic',scale_x_um_per_px='0.1',scale_y_um_per_px='0.1',source_width_px=32,source_height_px=32,method='synthetic',algorithm_version='synthetic')
        reference = CalibrationReference.objects.create(calibration=calibration,source_image=upload(),source_filename='synthetic.png',source_sha256=hashlib.sha256(image_bytes()).hexdigest(),source_width_px=32,source_height_px=32,pattern_type='CIRCLE',known_dimension_um='70',measurement_status='AMBIGUOUS')
        series = AcquisitionSeries.objects.create(patient=patient,acquisition_profile=profile,calibration=calibration,label='Synthetic')
        result = ResultadoSegmentacion.objects.create(muestra=saliva,tipo_muestra='SALIVA',estado='COMPLETADO',resultado_normalizado=normalize_segmentation_result(RAW),respuesta_json=RAW)
        snapshot = build_revision_snapshot_from_normalized(result)
        revision = RevisionSegmentacion.objects.create(resultado_segmentacion=result,numero_revision=1,resultado_editado=snapshot,resumen=calculate_revision_summary(snapshot))
        return dict(pacientes=patient,casos=case,analisis=analysis,muestras=saliva,**{'muestras-sangre':blood,'acquisition-profiles':profile,'calibrations':calibration,'calibration-references':reference,'acquisition-series':series,'resultados-segmentacion':result,'revisiones-segmentacion':revision})

    def test_list_and_detail_scopes_every_model_and_role(self):
        for role in ('ADMIN','OPERATOR','REVIEWER'):
            self.as_user(f'{role}_A')
            for route, obj in self.db.items():
                with self.subTest(role=role,route=route):
                    if route not in ('resultados-segmentacion','revisiones-segmentacion'):
                        response=self.client.get(f'/api/{route}/')
                        self.assertEqual(response.status_code,200,response.data)
                        self.assertEqual(len(response.data),1)
                    url = f'/api/{route}/{obj.pk}/' + ('efectivo/' if route=='resultados-segmentacion' else '')
                    self.assertEqual(self.client.get(url).status_code,404)
                    response=self.client.patch(f'/api/{route}/{obj.pk}/',{},format='json')
                    self.assertIn(response.status_code,(403,404,405))

    def test_nested_and_action_enumeration_denied_without_side_effects(self):
        for role in ('ADMIN','OPERATOR','REVIEWER'):
            self.as_user(f'{role}_A')
            for route, action in [('pacientes','casos'),('casos','analisis'),('casos','resumen-segmentacion'),('muestras','resultados-segmentacion'),('resultados-segmentacion','caracterizaciones'),('resultados-segmentacion','selective-context'),('resultados-segmentacion','revisiones')]:
                self.assertEqual(self.client.get(f'/api/{route}/{self.db[route].pk}/{action}/').status_code,404)
            for route,action in [('muestras','segmentar'),('muestras-sangre','segmentar'),('resultados-segmentacion','caracterizar'),('resultados-segmentacion','reserve-object-id'),('resultados-segmentacion','revisiones'),('revisiones-segmentacion','validar')]:
                response=self.client.post(f'/api/{route}/{self.db[route].pk}/{action}/',{},format='json')
                self.assertIn(response.status_code,(403,404))
            self.assertEqual(self.client.get(f'/api/acquisition-compatibility/SALIVA/{self.db["muestras"].pk}/').status_code,404)
        self.assertEqual(ResultadoCaracterizacion.objects.count(),0)

    def test_related_ids_cannot_cross_institution(self):
        pairs=[('casos',{'paciente':self.db['pacientes'].pk,'titulo':'Synthetic'}),
               ('analisis',{'id_paciente_fk':self.db['pacientes'].pk,'id_caso_fk':self.db['casos'].pk}),
               ('acquisition-series',{'patient':self.da['pacientes'].pk,'acquisition_profile':self.db['acquisition-profiles'].pk,'label':'Synthetic'}),
               ('acquisition-series',{'patient':self.db['pacientes'].pk,'acquisition_profile':self.da['acquisition-profiles'].pk,'label':'Synthetic'}),
               ('acquisition-series',{'patient':self.da['pacientes'].pk,'acquisition_profile':self.da['acquisition-profiles'].pk,'calibration':self.db['calibrations'].pk,'label':'Synthetic'}),
               ('calibrations',{'acquisition_profile':self.db['acquisition-profiles'].pk}),
               ('calibration-references',{'calibration':self.db['calibrations'].pk})]
        for route,payload in pairs:
            with self.subTest(route=route): self.assertEqual(self.client.post(f'/api/{route}/',payload,format='json').status_code,400)
        for route in ('muestras','muestras-sangre'):
            self.assertEqual(self.client.post(f'/api/{route}/',{'analisis':self.db['analisis'].pk,'imagen':upload()},format='multipart').status_code,400)
        self.assertEqual(self.client.post('/api/calibrations/automatic-preview/',{'acquisition_profile':self.db['acquisition-profiles'].pk,'references':'[]'},format='multipart').status_code,400)

    def test_role_matrix_mutations(self):
        for role in ('ADMIN','OPERATOR','REVIEWER'):
            self.as_user(f'{role}_A')
            for route in ('pacientes','casos','analisis','muestras','muestras-sangre','acquisition-series','acquisition-profiles','calibrations','calibration-references','users','institutions'):
                response=self.client.post(f'/api/{route}/',{},format='json')
                permitted = role=='ADMIN' and route!='institutions' or role=='OPERATOR' and route in ('pacientes','casos','analisis','muestras','muestras-sangre','acquisition-series')
                with self.subTest(role=role,route=route): self.assertEqual(response.status_code==403,not permitted,response.data)

    def test_operator_creates_owned_patient_and_immutable_authors(self):
        self.as_user('OPERATOR_A')
        payload=dict(nombre='Synthetic',apellido='New',identificacion='new',fecha_nacimiento='2000-01-01',created_by=self.users['ADMIN_B'].pk)
        denied=self.client.post('/api/pacientes/',{**payload,'institution':self.b.pk},format='json')
        self.assertEqual(denied.status_code,400)
        response=self.client.post('/api/pacientes/',payload,format='json');self.assertEqual(response.status_code,201,response.data)
        patient=Paciente.objects.get(pk=response.data['id_paciente'])
        self.assertEqual(patient.institution,self.a);self.assertEqual(patient.created_by,self.users['OPERATOR_A'])
        self.as_user('ADMIN_A')
        response=self.client.patch(f'/api/pacientes/{patient.pk}/',{'nombre':'Updated','created_by':self.users['ADMIN_A'].pk},format='json')
        self.assertEqual(response.status_code,200,response.data);patient.refresh_from_db()
        self.assertEqual(patient.created_by,self.users['OPERATOR_A']);self.assertEqual(patient.updated_by,self.users['ADMIN_A'])

    def test_case_and_analysis_nested_authorship(self):
        response=self.client.post('/api/casos/crear-con-analisis/',{'paciente':self.da['pacientes'].pk,'titulo':'New','crear_analisis':True},format='json')
        self.assertEqual(response.status_code,201,response.data)
        case=Caso.objects.order_by('-pk').first();self.assertEqual(case.created_by,self.users['ADMIN_A'])
        self.assertEqual(AnalisisPred.objects.get(id_caso_fk=case).created_by,self.users['ADMIN_A'])

    def test_revision_roles_and_snapshot_immutability(self):
        revision=self.da['revisiones-segmentacion'];url=f'/api/revisiones-segmentacion/{revision.pk}/'
        before=copy.deepcopy(revision.resultado_editado)
        self.as_user('OPERATOR_A');self.assertEqual(self.client.post(url+'validar/').status_code,403)
        saved=self.client.patch(url,{'resultado_editado':before},format='json');self.assertEqual(saved.status_code,200,saved.data)
        revision.refresh_from_db();self.assertEqual(revision.updated_by,self.users['OPERATOR_A'])
        self.as_user('REVIEWER_A');validated=self.client.post(url+'validar/');self.assertEqual(validated.status_code,200,validated.data)
        revision.refresh_from_db();self.assertEqual(revision.estado,'VALIDADA');self.assertEqual(revision.resultado_editado,before)
        self.assertEqual(revision.updated_by,self.users['REVIEWER_A'])
        effective=self.client.get(f'/api/resultados-segmentacion/{self.da["resultados-segmentacion"].pk}/efectivo/')
        self.assertEqual(effective.data['fuente'],'VALIDADA')

    def test_legacy_hidden_superuser_sees_all_without_backfill(self):
        legacy=Paciente.objects.create(nombre='Synthetic',apellido='Legacy',identificacion='legacy',fecha_nacimiento='2000-01-01')
        self.assertEqual(self.client.get(f'/api/pacientes/{legacy.pk}/').status_code,404)
        self.as_user(self.superuser)
        self.assertEqual(len(self.client.get('/api/pacientes/').data),3)
        legacy.refresh_from_db();self.assertIsNone(legacy.institution);self.assertIsNone(legacy.created_by)

    def test_missing_profile_inactive_institution_and_inactive_user_fail_closed(self):
        user=User.objects.create_user('no-profile',password=PASSWORD);self.as_user(user)
        self.assertEqual(self.client.get('/api/pacientes/').status_code,403)
        self.a.active=False;self.a.save();self.as_user(User.objects.get(pk=self.users['ADMIN_A'].pk))
        self.assertEqual(self.client.get('/api/pacientes/').status_code,403)
        self.a.active=True;self.a.save();user=self.users['OPERATOR_A'];user.is_active=False;user.save();self.as_user(user)
        self.assertEqual(self.client.get('/api/pacientes/').status_code,403)

    def test_users_scoping_no_escalation_and_no_delete(self):
        self.assertEqual(len(self.client.get('/api/users/').data),3)
        other=self.users['ADMIN_B'];self.assertEqual(self.client.get(f'/api/users/{other.pk}/').status_code,404)
        self.assertEqual(self.client.patch(f'/api/users/{other.pk}/',{'role':'OPERATOR'},format='json').status_code,404)
        payload={'username':'new-user','role':'OPERATOR','temporary_password':PASSWORD,'confirmation':PASSWORD}
        self.assertEqual(self.client.post('/api/users/',{**payload,'institution':self.b.pk},format='json').status_code,400)
        self.assertEqual(self.client.post('/api/users/',{**payload,'is_superuser':True},format='json').status_code,400)
        created=self.client.post('/api/users/',payload,format='json');self.assertEqual(created.status_code,201,created.data)
        user=User.objects.get(pk=created.data['id']);self.assertTrue(user.check_password(PASSWORD));self.assertNotEqual(user.password,PASSWORD)
        self.assertNotIn(PASSWORD,str(created.data));self.assertTrue(created.data['must_change_password'])
        self.assertIn(self.client.delete(f'/api/users/{user.pk}/').status_code,(403,405))
        self.assertEqual(self.client.delete(f'/api/institutions/{self.a.pk}/').status_code,403)

    def test_last_admin_guard_and_superuser_exception(self):
        url=f'/api/users/{self.users["ADMIN_A"].pk}/'
        for payload in ({'is_active':False},{'role':'OPERATOR'}):self.assertEqual(self.client.patch(url,payload,format='json').status_code,400)
        self.as_user(self.superuser);self.assertEqual(self.client.patch(url,{'role':'OPERATOR'},format='json').status_code,200)
        created=self.client.post('/api/institutions/',{'code':'C','name':'Synthetic C'},format='json');self.assertEqual(created.status_code,201)
        self.assertEqual(self.client.patch(f'/api/institutions/{self.a.pk}/',{'code':'OTHER'},format='json').status_code,400)

    def test_media_authenticated_scoped_and_public_path_removed(self):
        for kind,route,field in [('saliva','muestras','imagen'),('sangre','muestras-sangre','imagen'),('calibration','calibration-references','source_image')]:
            own,other=self.da[route],self.db[route]
            response=self.client.get(f'/api/private-media/{kind}/{own.pk}/');self.assertEqual(response.status_code,200);response.close()
            self.assertEqual(self.client.get(f'/api/private-media/{kind}/{other.pk}/').status_code,404)
            self.assertEqual(self.client.get(getattr(own,field).url).status_code,404)
            serialized=self.client.get(f'/api/{route}/{own.pk}/').data
            self.assertIn('/api/private-media/',serialized[field]);self.assertNotIn('/media/',serialized[field])
        self.as_user(None);self.assertEqual(self.client.get(f'/api/private-media/saliva/{self.da["muestras"].pk}/').status_code,403)

    def test_global_patient_identifier_becomes_tenant_unique_without_changing_values(self):
        self.assertEqual(self.da['pacientes'].identificacion,self.db['pacientes'].identificacion)
        for tenant in (self.a,self.b):
            p=Paciente(institution=tenant,identity_mode='PSEUDONYMIZED',external_id_namespace='external-hospital',external_patient_id='007',initials='SYN',identificacion='same-pseudo',fecha_nacimiento='2000-01-01')
            p.full_clean();p.save()
        with self.assertRaises(IntegrityError),transaction.atomic():
            Paciente.objects.create(institution=self.a,nombre='Synthetic',apellido='Duplicate',identificacion='same-id',fecha_nacimiento='2000-01-01')

    def test_series_model_rejects_cross_tenant_even_without_request(self):
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            AcquisitionSeries.objects.create(patient=self.da['pacientes'],acquisition_profile=self.db['acquisition-profiles'],label='Invalid')

    def test_bootstrap_and_legacy_assignment_dryrun_idempotent(self):
        out=StringIO();call_command('bootstrap_institution',code='A',name='Must not replace',stdout=out)
        self.a.refresh_from_db();self.assertEqual(self.a.name,'Synthetic A')
        patient=Paciente.objects.create(nombre='Synthetic',apellido='Legacy',identificacion='legacy',fecha_nacimiento='2000-01-01')
        call_command('assign_legacy_institution',institution='A',dry_run=True,stdout=StringIO());patient.refresh_from_db();self.assertIsNone(patient.institution)
        with self.assertRaises(CommandError):call_command('assign_legacy_institution',institution='A',stdout=StringIO())
        call_command('assign_legacy_institution',institution='A',confirm_all_unassigned=True,stdout=StringIO())
        call_command('assign_legacy_institution',institution='A',confirm_all_unassigned=True,stdout=StringIO());patient.refresh_from_db()
        self.assertEqual(patient.institution,self.a);self.assertIsNone(patient.created_by);self.assertEqual(patient.identificacion,'legacy')

    def test_characterization_request_author_is_preserved_on_idempotent_read(self):
        result=self.da['resultados-segmentacion'];url=f'/api/resultados-segmentacion/{result.pk}/caracterizar/'
        self.as_user('OPERATOR_A');response=self.client.post(url)
        self.assertEqual(response.status_code,201,response.data)
        record=ResultadoCaracterizacion.objects.get();payload=copy.deepcopy(record.resultado_json)
        self.assertEqual(record.created_by,self.users['OPERATOR_A'])
        self.as_user('REVIEWER_A');self.assertEqual(self.client.post(url).status_code,200)
        record.refresh_from_db();self.assertEqual(record.created_by,self.users['OPERATOR_A']);self.assertEqual(record.resultado_json,payload)

    def test_new_draft_author_and_active_draft_reuse(self):
        result=self.da['resultados-segmentacion'];RevisionSegmentacion.objects.filter(resultado_segmentacion=result).delete()
        url=f'/api/resultados-segmentacion/{result.pk}/revisiones/'
        self.as_user('OPERATOR_A');response=self.client.post(url);self.assertEqual(response.status_code,201,response.data)
        draft=RevisionSegmentacion.objects.get(resultado_segmentacion=result)
        self.assertEqual(draft.created_by,self.users['OPERATOR_A'])
        self.as_user('REVIEWER_A');self.assertEqual(self.client.post(url).status_code,200)
        draft.refresh_from_db();self.assertEqual(draft.updated_by,self.users['OPERATOR_A'])

    def test_other_tenant_filtered_search_and_series_query(self):
        response=self.client.get('/api/acquisition-series/',{'patient':self.db['pacientes'].pk})
        self.assertEqual(response.status_code,200);self.assertEqual(response.data,[])
        response=self.client.get('/api/pacientes/',{'institution':self.b.pk,'search':'Synthetic'})
        self.assertEqual(len(response.data),1);self.assertEqual(response.data[0]['institution'],self.a.pk)

    def test_inactive_profile_cannot_create_series(self):
        profile=self.da['acquisition-profiles'];profile.active=False;profile.save()
        self.as_user('OPERATOR_A')
        response=self.client.post('/api/acquisition-series/',{'patient':self.da['pacientes'].pk,'acquisition_profile':profile.pk,'label':'New'},format='json')
        self.assertEqual(response.status_code,400,response.data)

    def test_author_cannot_be_changed_through_model_or_api(self):
        from django.core.exceptions import ValidationError
        case=self.da['casos'];case.created_by=self.users['ADMIN_A']
        with self.assertRaises(ValidationError):case.save()
        case.refresh_from_db();self.assertIsNone(case.created_by)

    def test_platform_console_does_not_offer_user_or_institution_deletion(self):
        from django.contrib import admin
        from django.test import RequestFactory
        request=RequestFactory().get('/admin/');request.user=self.superuser
        self.assertTrue(admin.site.has_permission(request))
        self.assertFalse(admin.site._registry[User].has_delete_permission(request,self.users['ADMIN_A']))
        self.assertFalse(admin.site._registry[Institution].has_delete_permission(request,self.a))
        request.user=self.users['ADMIN_A'];self.assertFalse(admin.site.has_permission(request))


class SessionTests(TestCase):
    def setUp(self):
        self.tenant=Institution.objects.create(code='TEST',name='Synthetic')
        self.user=User.objects.create_user('synthetic',password=PASSWORD)
        self.profile=SicamUserProfile.objects.create(user=self.user,institution=self.tenant,role='OPERATOR',must_change_password=True)
        self.client=APIClient(enforce_csrf_checks=True)

    def csrf(self):
        return self.client.get('/api/auth/me/').data['csrf_token']

    def login(self):
        return self.client.post('/api/auth/login/',{'username':'synthetic','password':PASSWORD},format='json',HTTP_X_CSRFTOKEN=self.csrf())

    def test_login_requires_csrf_and_invalid_login_is_generic(self):
        self.assertEqual(self.client.post('/api/auth/login/',{'username':'synthetic','password':PASSWORD},format='json').status_code,403)
        self.assertEqual(self.client.post('/api/auth/login/',{'username':'synthetic','password':'invalid'},format='json',HTTP_X_CSRFTOKEN=self.csrf()).status_code,403)
        self.assertEqual(self.login().status_code,200)
        self.assertTrue(self.client.get('/api/auth/me/').data['user']['must_change_password'])

    def test_forced_password_change_gate_validators_session_rotation_logout(self):
        response=self.login();self.assertEqual(response.status_code,200)
        token=response.data['csrf_token'];self.assertEqual(self.client.get('/api/pacientes/').status_code,403)
        url='/api/auth/password/'
        for payload in ({'current_password':'wrong','new_password':'changed'}, {'current_password':PASSWORD,'new_password':'123','confirmation':'123'}):
            self.assertEqual(self.client.post(url,payload,format='json',HTTP_X_CSRFTOKEN=token).status_code,400)
        payload={'current_password':PASSWORD,'new_password':'Synthetic-Changed-827!Z','confirmation':'Synthetic-Changed-827!Z'}
        self.assertEqual(self.client.post(url,payload,format='json').status_code,403)
        changed=self.client.post(url,payload,format='json',HTTP_X_CSRFTOKEN=token);self.assertEqual(changed.status_code,200,changed.data)
        self.assertFalse(changed.data['user']['must_change_password']);self.assertEqual(self.client.get('/api/pacientes/').status_code,200)
        self.assertEqual(self.client.post('/api/pacientes/',{},format='json').status_code,403)
        self.assertEqual(self.client.post('/api/auth/logout/',{},format='json').status_code,403)
        self.assertEqual(self.client.post('/api/auth/logout/',{},format='json',HTTP_X_CSRFTOKEN=changed.data['csrf_token']).status_code,200)
        self.assertIsNone(self.client.get('/api/auth/me/').data['user']);self.assertEqual(self.client.get('/api/pacientes/').status_code,403)

    def test_inactive_user_and_institution_cannot_login(self):
        self.user.is_active=False;self.user.save();self.assertEqual(self.login().status_code,403)
        self.user.is_active=True;self.user.save();self.tenant.active=False;self.tenant.save();self.assertEqual(self.login().status_code,403)

    def test_session_csrf_patch_and_lifecycle_remain_tenant_scoped(self):
        self.profile.role = 'ADMIN'
        self.profile.must_change_password = False
        self.profile.save()
        response = self.login()
        self.assertEqual(response.status_code, 200)
        headers = {'HTTP_X_CSRFTOKEN': response.data['csrf_token']}
        payload = {
            'nombre': 'Synthetic', 'apellido': 'Session',
            'identificacion': 'TEST_CSRF', 'fecha_nacimiento': '2000-01-01',
        }
        created = self.client.post('/api/pacientes/', payload, format='json', **headers)
        self.assertEqual(created.status_code, 201, created.data)
        patient = Paciente.objects.get(pk=created.data['id_paciente'])
        self.assertEqual(patient.institution_id, self.tenant.pk)
        detail = f'/api/pacientes/{patient.pk}/'
        lifecycle = f'/api/lifecycle/pacientes/{patient.pk}/'
        action = {'action': 'ARCHIVE', 'reason': 'Synthetic CSRF check', 'confirm': True}
        for invalid_headers in ({}, {'HTTP_X_CSRFTOKEN': 'invalid'}):
            self.assertEqual(self.client.patch(detail, {'nombre': 'Blocked'},
                             format='json', **invalid_headers).status_code, 403)
            self.assertEqual(self.client.post(lifecycle, action,
                             format='json', **invalid_headers).status_code, 403)
        patient.refresh_from_db()
        self.assertEqual(patient.nombre, 'Synthetic')
        self.assertIsNone(patient.archived_at)
        self.assertEqual(self.client.patch(detail, {'nombre': 'Updated'},
                         format='json', **headers).status_code, 200)
        self.assertEqual(self.client.post(lifecycle, action,
                         format='json', **headers).status_code, 200)
        action['action'] = 'RESTORE'
        self.assertEqual(self.client.post(lifecycle, action,
                         format='json', **headers).status_code, 200)
        other = Institution.objects.create(code='OTHER_CSRF', name='Synthetic other')
        foreign = Paciente.objects.create(
            institution=other, nombre='Foreign', apellido='Synthetic',
            identificacion='OTHER_CSRF', fecha_nacimiento='2000-01-01',
        )
        self.assertEqual(self.client.get(f'/api/pacientes/{foreign.pk}/').status_code, 404)
        self.assertEqual(self.client.post(f'/api/lifecycle/pacientes/{foreign.pk}/',
                         action, format='json', **headers).status_code, 404)
