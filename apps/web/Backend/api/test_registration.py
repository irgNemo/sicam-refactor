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
