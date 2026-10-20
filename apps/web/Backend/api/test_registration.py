from unittest.mock import patch
from datetime import timedelta
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone
from PIL import Image
from rest_framework import serializers
from rest_framework.test import APIClient

from api.models import Paciente, Caso, AnalisisPred, MuestraSaliva, MuestraSangre
from api.serializers import AnalisisSerializer


class RegistrationTests(TestCase):
    """Synthetic records in test DB; uploads use temporary media outside repo."""

    def setUp(self):
        self.client = APIClient()
        self.patient = Paciente.objects.create(
            nombre='Synthetic', apellido='Registration', identificacion='registration-1',
            fecha_nacimiento='2000-01-01',
        )
        self.other = Paciente.objects.create(
            nombre='Synthetic', apellido='Other', identificacion='registration-2',
            fecha_nacimiento='2000-01-01',
        )
        self.payload = {'paciente': self.patient.pk, 'titulo': 'Synthetic case', 'descripcion': ''}

    def test_atomic_case_and_analysis(self):
        response = self.client.post('/api/casos/crear-con-analisis/', self.payload, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        case = Caso.objects.get()
        analysis = AnalisisPred.objects.get()
        self.assertEqual(response.data['caso']['id_caso'], case.pk)
        self.assertEqual(response.data['analisis']['id_analisis'], analysis.pk)
        self.assertEqual((case.paciente_id, analysis.id_paciente_fk_id), (self.patient.pk, self.patient.pk))
        self.assertEqual(analysis.id_caso_fk_id, case.pk)
        self.assertEqual(analysis.estado, 0)
        self.assertIsNone(case.case_number)

    def test_invalid_case_creates_nothing(self):
        response = self.client.post('/api/casos/crear-con-analisis/', {
            **self.payload, 'titulo': '',
        }, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Caso.objects.exists())
        self.assertFalse(AnalisisPred.objects.exists())

    def test_invalid_analysis_rolls_back_saved_case(self):
        def reject_analysis(serializer, attrs):
            self.assertEqual(Caso.objects.count(), 1, 'Case must already exist inside transaction')
            raise serializers.ValidationError({'id_caso_fk': 'Synthetic analysis rejection'})

        with patch.object(AnalisisSerializer, 'validate', reject_analysis):
            response = self.client.post('/api/casos/crear-con-analisis/', self.payload, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Caso.objects.exists())
        self.assertFalse(AnalisisPred.objects.exists())

    def test_existing_case_and_analysis_endpoints(self):
        response = self.client.post('/api/casos/', self.payload, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertFalse(AnalisisPred.objects.exists())
        response = self.client.post('/api/analisis/', {
            'id_paciente_fk': self.patient.pk, 'id_caso_fk': response.data['id_caso'], 'estado': 0,
        }, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(AnalisisPred.objects.count(), 1)

    def test_analysis_rejects_mismatched_patient_on_create(self):
        case = Caso.objects.create(**{**self.payload, 'paciente': self.patient})
        response = self.client.post('/api/analisis/', {
            'id_paciente_fk': self.other.pk, 'id_caso_fk': case.pk,
        }, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('id_caso_fk', response.data)
        self.assertFalse(AnalisisPred.objects.exists())

    def test_partial_and_full_updates_enforce_relation(self):
        case = Caso.objects.create(paciente=self.patient, titulo='Synthetic A')
        other_case = Caso.objects.create(paciente=self.other, titulo='Synthetic B')
        analysis = AnalisisPred.objects.create(id_paciente_fk=self.patient, id_caso_fk=case)
        url = f'/api/analisis/{analysis.pk}/'
        for payload in [{'id_paciente_fk': self.other.pk}, {'id_caso_fk': other_case.pk}]:
            response = self.client.patch(url, payload, format='json')
            self.assertEqual(response.status_code, 400)
        response = self.client.put(url, {
            'id_paciente_fk': self.patient.pk, 'id_caso_fk': other_case.pk, 'estado': 1,
        }, format='json')
        self.assertEqual(response.status_code, 400)
        analysis.refresh_from_db()
        self.assertEqual((analysis.id_paciente_fk_id, analysis.id_caso_fk_id), (self.patient.pk, case.pk))
        response = self.client.patch(url, {'estado': 1}, format='json')
        self.assertEqual(response.status_code, 200)
        response = self.client.patch(url, {
            'id_paciente_fk': self.other.pk, 'id_caso_fk': other_case.pk,
        }, format='json')
        self.assertEqual(response.status_code, 200)

    def test_existing_case_allows_multiple_open_analyses_without_modifying_case(self):
        case = Caso.objects.create(paciente=self.patient, titulo='Synthetic existing', descripcion='Unchanged')
        before = Caso.objects.filter(pk=case.pk).values().get()
        self.assertFalse(case.analisis.exists())
        for explicit_state in (False, True):
            payload = {'id_paciente_fk': self.patient.pk, 'id_caso_fk': case.pk}
            if explicit_state:
                payload['estado'] = 0
            response = self.client.post('/api/analisis/', payload, format='json')
            self.assertEqual(response.status_code, 201, response.data)
            analysis = AnalisisPred.objects.get(pk=response.data['id_analisis'])
            self.assertEqual((analysis.estado, analysis.id_paciente_fk_id, analysis.id_caso_fk_id),
                             (0, self.patient.pk, case.pk))
        self.assertEqual(case.analisis.count(), 2)
        self.assertEqual(Caso.objects.filter(pk=case.pk).values().get(), before)

    def test_direct_sample_posts_enforce_closed_analysis_for_both_sample_types(self):
        case = Caso.objects.create(paciente=self.patient, titulo='Synthetic uploads')
        with TemporaryDirectory(prefix='sicam18rd-test-media-') as media, self.settings(MEDIA_ROOT=media):
            for model, endpoint in [(MuestraSaliva, '/api/muestras/'), (MuestraSangre, '/api/muestras-sangre/')]:
                for state in (0, 1, 2):
                    with self.subTest(sample=model.__name__, state=state):
                        analysis = AnalisisPred.objects.create(id_paciente_fk=self.patient, id_caso_fk=case, estado=state)
                        image = BytesIO()
                        Image.new('RGB', (4, 4)).save(image, format='PNG')
                        upload = SimpleUploadedFile('synthetic.png', image.getvalue(), content_type='image/png')
                        before = model.objects.count()
                        files_before = {str(p) for p in Path(media).rglob('*') if p.is_file()}
                        response = self.client.post(endpoint, {'analisis': analysis.pk, 'imagen': upload}, format='multipart')
                        self.assertEqual(response.status_code, 400 if state == 2 else 201, response.data)
                        self.assertEqual(model.objects.count(), before + (state != 2))
                        analysis.refresh_from_db()
                        self.assertEqual(analysis.estado, state)
                        if state == 2:
                            self.assertIn('análisis cerrado', str(response.data['analisis']))
                            self.assertEqual({str(p) for p in Path(media).rglob('*') if p.is_file()}, files_before)
                        else:
                            self.assertTrue(Path(model.objects.get(pk=response.data['id_muestra']).imagen.path).is_file())

    def test_birth_date_on_create_for_both_identity_modes(self):
        today = timezone.localdate()
        for mode in (Paciente.IDENTIFIED, Paciente.PSEUDONYMIZED):
            for offset in (-1, 0, 1):
                with self.subTest(mode=mode, offset=offset):
                    key = f'birth-{mode}-{offset}'
                    payload = {'identity_mode': mode, 'identificacion': key,
                               'fecha_nacimiento': str(today + timedelta(days=offset))}
                    if mode == Paciente.IDENTIFIED:
                        payload.update(nombre='Synthetic', apellido='Date')
                    else:
                        payload.update(initials='TEST', external_id_namespace='synthetic', external_patient_id=key)
                    before = Paciente.objects.count()
                    response = self.client.post('/api/pacientes/', payload, format='json')
                    self.assertEqual(response.status_code, 400 if offset > 0 else 201, response.data)
                    self.assertEqual(Paciente.objects.count(), before + (offset <= 0))
                    if offset > 0:
                        self.assertIn('no puede ser futura', str(response.data['fecha_nacimiento']))

    def test_birth_date_on_put_and_patch_for_both_identity_modes(self):
        today = timezone.localdate()
        pseudo = Paciente.objects.create(
            identity_mode=Paciente.PSEUDONYMIZED, initials='TEST',
            external_id_namespace='synthetic', external_patient_id='date-update',
            identificacion='date-update', fecha_nacimiento=today - timedelta(days=10),
        )
        for patient in (self.patient, pseudo):
            for method in ('put', 'patch'):
                for offset in (-1, 0, 1):
                    with self.subTest(mode=patient.identity_mode, method=method, offset=offset):
                        patient.refresh_from_db()
                        before = Paciente.objects.filter(pk=patient.pk).values().get()
                        payload = {'fecha_nacimiento': str(today + timedelta(days=offset))}
                        if method == 'put':
                            payload.update({key: getattr(patient, key) for key in (
                                'identity_mode', 'nombre', 'apellido', 'identificacion', 'initials',
                                'external_id_namespace', 'external_patient_id',
                            )})
                        response = getattr(self.client, method)(f'/api/pacientes/{patient.pk}/', payload, format='json')
                        self.assertEqual(response.status_code, 400 if offset > 0 else 200, response.data)
                        if offset > 0:
                            self.assertIn('no puede ser futura', str(response.data['fecha_nacimiento']))
                            self.assertEqual(Paciente.objects.filter(pk=patient.pk).values().get(), before)
            response = self.client.patch(f'/api/pacientes/{patient.pk}/', {'telefono': '5550000000'}, format='json')
            self.assertEqual(response.status_code, 200, response.data)


class PseudonymizedRegistrationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.payload = dict(identity_mode='PSEUDONYMIZED', initials='ACL',
                            external_id_namespace='test', external_patient_id='007',
                            fecha_nacimiento='2000-01-01')

    def create_patient(self, **overrides):
        response = self.client.post('/api/pacientes/', {**self.payload, **overrides}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        return Paciente.objects.get(pk=response.data['id_paciente'])

    def test_identified_default_required_fields_and_unique_identifier(self):
        for payload in ([1, 2], 'not-an-object'):
            self.assertEqual(self.client.post('/api/pacientes/', payload, format='json').status_code, 400)
        data = dict(nombre='Synthetic', apellido='Registration', identificacion='TEST', fecha_nacimiento='2000-01-01')
        for field in ('nombre', 'apellido', 'identificacion'):
            for missing in (True, False):
                with self.subTest(field=field, missing=missing):
                    invalid = dict(data)
                    if missing:
                        invalid.pop(field)
                    else:
                        invalid[field] = ''
                    response = self.client.post('/api/pacientes/', invalid, format='json')
                    self.assertEqual(response.status_code, 400, response.data)
                    self.assertIn(field, response.data)
        self.assertEqual(Paciente.objects.count(), 0)
        response = self.client.post('/api/pacientes/', data, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['identity_mode'], 'IDENTIFIED')
        self.assertEqual(response.data['identificacion'], 'TEST')
        self.assertEqual(self.client.post('/api/pacientes/', data, format='json').status_code, 400)
        url = f"/api/pacientes/{response.data['id_paciente']}/"
        self.assertEqual(self.client.put(url, {k:v for k,v in data.items() if k != 'identificacion'}, format='json').status_code, 400)
        for field in ('nombre', 'apellido', 'identificacion'):
            self.assertEqual(self.client.patch(url, {field: ''}, format='json').status_code, 400)
        self.assertEqual(self.client.patch(url, {'telefono': '5550000000'}, format='json').status_code, 200)

    def test_generated_identifier_exact_imagej_formula_and_no_fictitious_data(self):
        from api.services.patient_identity import pseudonymized_identification
        patient = self.create_patient()
        self.assertEqual(patient.identificacion, 'ext:e8c598b817db5cd4a9c49cc752763a9e')
        self.assertEqual(patient.identificacion, pseudonymized_identification('test', '007'))
        self.assertEqual(pseudonymized_identification('test', '007'), pseudonymized_identification('test', '007'))
        self.assertEqual((patient.nombre, patient.apellido, patient.email, patient.telefono), ('', '', None, None))
        other = self.create_patient(external_id_namespace='another', identificacion='client-must-not-control-this')
        self.assertNotEqual(patient.identificacion, other.identificacion)
        self.assertEqual(other.identificacion, pseudonymized_identification('another', '007'))

    def test_duplicate_authority_is_field_error_and_other_namespace_is_allowed(self):
        self.create_patient()
        response = self.client.post('/api/pacientes/', self.payload, format='json')
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn('Ya existe un paciente con este ID', str(response.data['external_patient_id']))
        self.create_patient(external_id_namespace='another')
        self.assertEqual(Paciente.objects.count(), 2)

    def test_missing_empty_forbidden_fields_and_future_birthdate(self):
        for field in ('initials', 'external_id_namespace', 'external_patient_id', 'fecha_nacimiento'):
            for missing in (True, False):
                with self.subTest(field=field, missing=missing):
                    payload = dict(self.payload)
                    if missing:
                        payload.pop(field)
                    else:
                        payload[field] = ' '
                    response = self.client.post('/api/pacientes/', payload, format='json')
                    self.assertEqual(response.status_code, 400, response.data)
                    self.assertIn(field, response.data)
        for field in ('nombre', 'apellido'):
            response = self.client.post('/api/pacientes/', {**self.payload, field: 'Not allowed'}, format='json')
            self.assertEqual(response.status_code, 400)
            self.assertIn(field, response.data)
        response = self.client.post('/api/pacientes/', {
            **self.payload, 'fecha_nacimiento': str(timezone.localdate() + timedelta(days=1)),
        }, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('fecha_nacimiento', response.data)
        self.assertEqual(Paciente.objects.count(), 0)

    def test_trim_preserves_case_and_leading_zeroes(self):
        from api.services.patient_identity import pseudonymized_identification
        patient = self.create_patient(initials=' aCl ', external_id_namespace=' Hospital ', external_patient_id=' 0007 ')
        self.assertEqual((patient.initials, patient.external_id_namespace, patient.external_patient_id), ('aCl', 'Hospital', '0007'))
        self.assertEqual(patient.identificacion, pseudonymized_identification('Hospital', '0007'))

    def test_put_patch_authority_keeps_generated_identifier_coherent(self):
        from api.services.patient_identity import pseudonymized_identification
        patient = self.create_patient()
        url = f'/api/pacientes/{patient.pk}/'
        for method, payload, namespace, external_id in (
            ('patch', {'external_patient_id': '008'}, 'test', '008'),
            ('patch', {'external_id_namespace': 'new'}, 'new', '008'),
            ('put', {**self.payload, 'external_id_namespace': 'final', 'external_patient_id': '009'}, 'final', '009'),
        ):
            response = getattr(self.client, method)(url, payload, format='json')
            self.assertEqual(response.status_code, 200, response.data)
            patient.refresh_from_db()
            self.assertEqual(patient.identificacion, pseudonymized_identification(namespace, external_id))
        self.create_patient(external_id_namespace='taken', external_patient_id='009')
        for payload in ({'external_id_namespace': 'taken'}, {'external_patient_id': ''}, {'initials': ''}, {'nombre': 'Not allowed'}):
            before = Paciente.objects.filter(pk=patient.pk).values().get()
            response = self.client.patch(url, payload, format='json')
            self.assertEqual(response.status_code, 400, response.data)
            self.assertEqual(Paciente.objects.filter(pk=patient.pk).values().get(), before)

    def test_unrelated_patch_preserves_legacy_identifier_and_cannot_override_it(self):
        patient = Paciente.objects.create(**self.payload, identificacion='legacy-preserved')
        url = f'/api/pacientes/{patient.pk}/'
        response = self.client.patch(url, {'initials': 'EDIT', 'identificacion': 'tampered'}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        patient.refresh_from_db()
        self.assertEqual(patient.identificacion, 'legacy-preserved')
        self.assertEqual(patient.initials, 'EDIT')

    def test_generated_identifier_collision_rejected_without_writing(self):
        from api.services.patient_identity import pseudonymized_identification
        Paciente.objects.create(nombre='Synthetic', apellido='Collision', fecha_nacimiento='2000-01-01',
                                identificacion=pseudonymized_identification('test', '007'))
        response = self.client.post('/api/pacientes/', self.payload, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('external_patient_id', response.data)
        self.assertEqual(Paciente.objects.count(), 1)
