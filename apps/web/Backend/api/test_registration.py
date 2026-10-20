from unittest.mock import patch

from django.test import TestCase
from rest_framework import serializers
from rest_framework.test import APIClient

from api.models import Paciente, Caso, AnalisisPred
from api.serializers import AnalisisSerializer


class RegistrationTests(TestCase):
    """Synthetic records, Django test database only; no media writes."""

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
