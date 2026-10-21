"""Synthetic acquisition tests; no real images, calibration or working DB writes."""
import hashlib
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models.deletion import ProtectedError
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework.test import APIClient

from api.models import (Paciente, Caso, AnalisisPred, MuestraSaliva, MuestraSangre,
                        AcquisitionProfile, Calibration, CalibrationReference, AcquisitionSeries)
from api.services.acquisition import physical_compatibility, can_use_physical_units


def image_bytes(size=(32, 32), mode='RGB'):
    stream = BytesIO()
    Image.new(mode, size).save(stream, 'PNG')
    return stream.getvalue()


def upload(content=None, name='synthetic.png'):
    return SimpleUploadedFile(name, image_bytes() if content is None else content, 'image/png')


class AcquisitionTests(TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(prefix='sic am-acquisition-'.replace(' ', ''))
        self.addCleanup(self.temp.cleanup)
        self.media = override_settings(MEDIA_ROOT=self.temp.name)
        self.media.enable()
        self.addCleanup(self.media.disable)
        self.patient = Paciente.objects.create(nombre='Synthetic', apellido='Acquisition',
            identificacion='acq-test', fecha_nacimiento='2000-01-01')
        self.other = Paciente.objects.create(nombre='Synthetic', apellido='Other',
            identificacion='acq-other', fecha_nacimiento='2000-01-01')
        self.case = Caso.objects.create(paciente=self.patient, titulo='Synthetic')
        self.analysis = AnalisisPred.objects.create(id_paciente_fk=self.patient, id_caso_fk=self.case)
        self.profile = AcquisitionProfile.objects.create(name='Synthetic', image_width_px=32, image_height_px=32)
        self.calibration = self.make_calibration()
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(username='acquisition-test')
        self.client.force_authenticate(self.user)

    def make_calibration(self, **overrides):
        return Calibration.objects.create(**{
            'acquisition_profile': self.profile, 'label': 'Synthetic only',
            'scale_x_um_per_px': Decimal('0.055233934047693'),
            'scale_y_um_per_px': Decimal('0.055010060892106'),
            'source_width_px': 32, 'source_height_px': 32,
            'method': 'synthetic', 'algorithm_version': 'test-1', **overrides,
        })

    def make_series(self, **overrides):
        return AcquisitionSeries.objects.create(**{
            'patient': self.patient, 'acquisition_profile': self.profile,
            'calibration': self.calibration, 'label': 'Synthetic series', **overrides,
        })

    def make_sample(self, model=MuestraSaliva, **overrides):
        return model.objects.create(**{'analisis': self.analysis, 'imagen': upload(), **overrides})

    def reference_data(self, **overrides):
        return {'calibration': self.calibration.pk, 'pattern_type': 'CIRCLE',
                'source_filename': 'synthetic.png', 'source_sha256': hashlib.sha256(image_bytes()).hexdigest(),
                'source_width_px': 32, 'source_height_px': 32, 'known_dimension_um': '70.000000000000000',
                'measurement_status': 'AMBIGUOUS', **overrides}

    def test_profile_unknown_optics_optional_and_positive_dimensions(self):
        self.assertEqual(self.profile.camera_model, '')
        self.assertIsNone(self.profile.objective_magnification)
        with self.assertRaises(ValidationError):
            AcquisitionProfile.objects.create(name='Invalid', image_width_px=0, image_height_px=32)

    def test_scale_precision_and_default_provisional(self):
        self.calibration.refresh_from_db()
        self.assertEqual(self.calibration.scale_x_um_per_px, Decimal('0.055233934047693'))
        self.assertEqual(self.calibration.scale_y_um_per_px, Decimal('0.055010060892106'))
        self.assertEqual(self.calibration.status, 'PROVISIONAL')

    def test_nonpositive_scale_and_resolution_rejected(self):
        for kwargs in ({'scale_x_um_per_px': 0}, {'scale_y_um_per_px': -1}, {'source_width_px': 16}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValidationError):
                self.make_calibration(**kwargs)

    def test_series_without_calibration_and_multiple_per_patient(self):
        first = self.make_series(calibration=None)
        second = self.make_series()
        self.assertNotEqual(first.pk, second.pk)
        sample = self.make_sample(acquisition_series=first)
        self.assertEqual(physical_compatibility(sample)['status'], 'NO_CALIBRATION')
        first.calibration = self.calibration
        first.save()
        self.assertTrue(can_use_physical_units(sample))

    def test_profile_calibration_mismatch_rejected(self):
        other = AcquisitionProfile.objects.create(name='Other', image_width_px=32, image_height_px=32)
        with self.assertRaisesMessage(ValidationError, 'PROFILE_MISMATCH'):
            self.make_series(acquisition_profile=other)

    def test_sample_patient_coherence_both_types(self):
        series = self.make_series()
        other_series = self.make_series(patient=self.other)
        for model in (MuestraSaliva, MuestraSangre):
            with self.subTest(model=model):
                self.assertTrue(can_use_physical_units(self.make_sample(model, acquisition_series=series)))
                with self.assertRaisesMessage(ValidationError, 'PATIENT_MISMATCH'):
                    self.make_sample(model, acquisition_series=other_series)

    def test_associated_analysis_cannot_change_patient(self):
        self.make_sample(acquisition_series=self.make_series())
        self.analysis.id_paciente_fk = self.other
        with self.assertRaisesMessage(ValidationError, 'PATIENT_MISMATCH'):
            self.analysis.save()
        other_case = Caso.objects.create(paciente=self.other, titulo='Other')
        response = self.client.patch(f'/api/analisis/{self.analysis.pk}/', {
            'id_paciente_fk': self.other.pk, 'id_caso_fk': other_case.pk}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_historical_profile_and_calibration_are_immutable(self):
        self.profile.image_width_px = 16
        with self.assertRaisesMessage(ValidationError, 'IMMUTABLE'):
            self.profile.save()
        self.calibration.scale_x_um_per_px = Decimal('0.06')
        with self.assertRaisesMessage(ValidationError, 'IMMUTABLE'):
            self.calibration.save()

    def test_series_and_sample_links_cannot_be_repointed(self):
        series = self.make_series()
        sample = self.make_sample(acquisition_series=series)
        sample.acquisition_series = None
        with self.assertRaisesMessage(ValidationError, 'IMMUTABLE'):
            sample.save()
        series.patient = self.other
        with self.assertRaisesMessage(ValidationError, 'IMMUTABLE'):
            series.save()

    def test_same_filename_upload_cannot_replace_bound_image(self):
        sample = self.make_sample(acquisition_series=self.make_series())
        sample.imagen = upload(name=sample.imagen.name)
        with self.assertRaisesMessage(ValidationError, 'IMMUTABLE'):
            sample.save()

    def test_calibration_lifecycle_and_retired_historical_link(self):
        series = self.make_series()
        sample = self.make_sample(acquisition_series=series)
        self.calibration.status = 'VALIDATED'
        self.calibration.save()
        self.assertEqual(physical_compatibility(sample)['status'], 'COMPATIBLE')
        self.calibration.status = 'RETIRED'
        self.calibration.save()
        self.assertEqual(physical_compatibility(sample)['status'], 'CALIBRATION_RETIRED')
        self.assertFalse(can_use_physical_units(sample))
        series.notes = 'Historical relationship retained'
        series.save()
        self.assertEqual(series.calibration_id, self.calibration.pk)
        with self.assertRaisesMessage(ValidationError, 'CALIBRATION_RETIRED'):
            self.make_series()
        with self.assertRaises(ProtectedError):
            self.calibration.delete()
        self.calibration.status = 'PROVISIONAL'
        with self.assertRaises(ValidationError):
            self.calibration.save()

    def test_referenced_entities_cannot_be_deleted(self):
        series = self.make_series()
        self.make_sample(acquisition_series=series)
        for instance in (series, self.profile, self.patient):
            with self.subTest(model=type(instance)), self.assertRaises(ProtectedError):
                instance.delete()

    def test_large_original_provisional_then_validated(self):
        profile = AcquisitionProfile.objects.create(name='4928', image_width_px=4928, image_height_px=4928)
        calibration = self.make_calibration(acquisition_profile=profile, source_width_px=4928, source_height_px=4928)
        series = self.make_series(acquisition_profile=profile, calibration=calibration)
        sample = self.make_sample(acquisition_series=series, imagen=upload(image_bytes((4928, 4928))))
        before = Path(sample.imagen.path).read_bytes()
        result = physical_compatibility(sample)
        self.assertEqual(result['status'], 'COMPATIBLE_PROVISIONAL')
        self.assertEqual(result['calibration_status'], 'PROVISIONAL')
        self.assertEqual(result['scale_x_um_per_px'], '0.055233934047693')
        self.assertTrue(can_use_physical_units(sample))
        calibration.status = 'VALIDATED'
        calibration.save()
        self.assertEqual(physical_compatibility(sample)['status'], 'COMPATIBLE')
        self.assertEqual(Path(sample.imagen.path).read_bytes(), before)

    def test_half_resolution_never_rescales(self):
        profile = AcquisitionProfile.objects.create(name='4928', image_width_px=4928, image_height_px=4928)
        calibration = self.make_calibration(acquisition_profile=profile, source_width_px=4928, source_height_px=4928)
        series = self.make_series(acquisition_profile=profile, calibration=calibration)
        sample = self.make_sample(acquisition_series=series, imagen=upload(image_bytes((2464, 2464))))
        before = Path(sample.imagen.path).read_bytes()
        with patch.object(Image.Image, 'resize', side_effect=AssertionError('No resize')):
            result = physical_compatibility(sample)
        self.assertEqual(result['status'], 'RESOLUTION_MISMATCH')
        self.assertFalse(result['compatible_for_physical_units'])
        self.assertNotIn('scale_x_um_per_px', result)
        self.assertNotIn('scale_y_um_per_px', result)
        self.assertEqual(Path(sample.imagen.path).read_bytes(), before)
        calibration.refresh_from_db()
        self.assertEqual(calibration.scale_x_um_per_px, Decimal('0.055233934047693'))

    def test_no_series_preserves_pixel_workflow(self):
        sample = self.make_sample()
        self.assertEqual(physical_compatibility(sample)['status'], 'NO_ACQUISITION_SERIES')
        self.assertFalse(can_use_physical_units(sample))

    def test_invalid_and_missing_original(self):
        sample = self.make_sample(acquisition_series=self.make_series(), imagen=upload(b'not an image'))
        self.assertEqual(physical_compatibility(sample)['status'], 'INVALID_IMAGE')
        Path(sample.imagen.path).unlink()
        self.assertEqual(physical_compatibility(sample)['status'], 'INVALID_IMAGE')

    def test_declared_mode_mismatch(self):
        profile = AcquisitionProfile.objects.create(name='Mode', image_width_px=32, image_height_px=32, image_mode='L')
        calibration = self.make_calibration(acquisition_profile=profile)
        sample = self.make_sample(acquisition_series=self.make_series(acquisition_profile=profile, calibration=calibration))
        self.assertEqual(physical_compatibility(sample)['status'], 'IMAGE_MODE_MISMATCH')

    def test_service_defensively_rechecks_patient_and_profile(self):
        series = self.make_series()
        sample = self.make_sample(acquisition_series=series)
        # Deliberate invalid fixture via bypass, NOT supported application writes.
        AcquisitionSeries.objects.filter(pk=series.pk).update(patient=self.other)
        self.assertEqual(physical_compatibility(sample)['status'], 'PATIENT_MISMATCH')
        other_profile = AcquisitionProfile.objects.create(name='Other', image_width_px=32, image_height_px=32)
        AcquisitionSeries.objects.filter(pk=series.pk).update(patient=self.patient, acquisition_profile=other_profile)
        self.assertEqual(physical_compatibility(sample)['status'], 'PROFILE_MISMATCH')

    def test_api_auth_required_all_new_routes(self):
        self.client.force_authenticate(None)
        for route in ('acquisition-profiles', 'calibrations', 'calibration-references', 'acquisition-series', 'acquisition-compatibility/SALIVA/1'):
            with self.subTest(route=route):
                self.assertIn(self.client.get(f'/api/{route}/').status_code, (401, 403))
                self.assertIn(self.client.post(f'/api/{route}/', {}, format='json').status_code, (401, 403, 405))

    def test_profile_api_crud_without_delete(self):
        response = self.client.post('/api/acquisition-profiles/', {'name': 'API', 'image_width_px': 32, 'image_height_px': 32}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        route = f"/api/acquisition-profiles/{response.data['id']}/"
        self.assertEqual(self.client.get(route).status_code, 200)
        self.assertEqual(self.client.get('/api/acquisition-profiles/').status_code, 200)
        self.assertEqual(self.client.patch(route, {'notes': 'Metadata'}, format='json').status_code, 200)
        self.assertEqual(self.client.put(route, {'name': 'Updated', 'image_width_px': 32, 'image_height_px': 32}, format='json').status_code, 200)
        self.assertEqual(self.client.delete(route).status_code, 405)

    def test_calibration_api_create_update_status_and_no_numeric_overwrite(self):
        data = {'acquisition_profile': self.profile.pk, 'label': 'API', 'scale_x_um_per_px': '0.055233934047693',
                'scale_y_um_per_px': '0.055010060892106', 'source_width_px': 32, 'source_height_px': 32,
                'method': 'synthetic', 'algorithm_version': 'test'}
        response = self.client.post('/api/calibrations/', data, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        route = f"/api/calibrations/{response.data['id']}/"
        self.assertEqual(self.client.patch(route, {'notes': 'Reviewed', 'status': 'VALIDATED'}, format='json').status_code, 200)
        self.assertEqual(self.client.patch(route, {'scale_x_um_per_px': '0.1'}, format='json').status_code, 400)
        self.assertEqual(self.client.delete(route).status_code, 405)
        self.assertEqual(self.client.get(route).status_code, 200)
        self.assertEqual(self.client.get('/api/calibrations/').status_code, 200)

    def test_series_api_patient_and_profile_coherence(self):
        data = {'patient': self.patient.pk, 'acquisition_profile': self.profile.pk, 'calibration': self.calibration.pk, 'label': 'API'}
        response = self.client.post('/api/acquisition-series/', data, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        route = f"/api/acquisition-series/{response.data['id']}/"
        self.assertEqual(self.client.patch(route, {'notes': 'Metadata'}, format='json').status_code, 200)
        self.assertEqual(self.client.patch(route, {'patient': self.other.pk}, format='json').status_code, 400)
        self.assertEqual(self.client.get(route).status_code, 200)
        self.assertEqual(self.client.get('/api/acquisition-series/').status_code, 200)
        self.assertEqual(self.client.delete(route).status_code, 405)

    def test_sample_api_assigns_series_both_types_and_keeps_legacy_optional(self):
        series = self.make_series()
        other_series = self.make_series(patient=self.other)
        for route in ('muestras', 'muestras-sangre'):
            with self.subTest(route=route):
                response = self.client.post(f'/api/{route}/', {'analisis': self.analysis.pk, 'imagen': upload()}, format='multipart')
                self.assertEqual(response.status_code, 201, response.data)
                self.assertIsNone(response.data['acquisition_series'])
                detail = f"/api/{route}/{response.data['id_muestra']}/"
                self.assertEqual(self.client.patch(detail, {'acquisition_series': other_series.pk}, format='multipart').status_code, 400)
                self.assertEqual(self.client.patch(detail, {'acquisition_series': series.pk}, format='multipart').status_code, 200)
                self.assertEqual(self.client.patch(detail, {'acquisition_series': ''}, format='multipart').status_code, 400)

    def test_anonymous_upload_legacy_allowed_but_series_binding_rejected(self):
        series = self.make_series()
        self.client.force_authenticate(None)
        response = self.client.post('/api/muestras/', {'analisis': self.analysis.pk, 'imagen': upload()}, format='multipart')
        self.assertEqual(response.status_code, 201)
        response = self.client.patch(f"/api/muestras/{response.data['id_muestra']}/", {'acquisition_series': series.pk}, format='multipart')
        self.assertEqual(response.status_code, 400)

    def test_compatibility_api_both_types_and_missing_sample(self):
        for sample_type, model in (('SALIVA', MuestraSaliva), ('SANGRE', MuestraSangre)):
            sample = self.make_sample(model, acquisition_series=self.make_series())
            response = self.client.get(f'/api/acquisition-compatibility/{sample_type}/{sample.pk}/')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data['status'], 'COMPATIBLE_PROVISIONAL')
        self.assertEqual(self.client.get('/api/acquisition-compatibility/INVALID/1/').status_code, 404)
        self.assertEqual(self.client.get('/api/acquisition-compatibility/SALIVA/9999/').status_code, 404)

    def test_reference_metadata_without_image_and_append_only(self):
        response = self.client.post('/api/calibration-references/', self.reference_data(), format='json')
        self.assertEqual(response.status_code, 201, response.data)
        route = f"/api/calibration-references/{response.data['id']}/"
        self.assertEqual(self.client.get(route).status_code, 200)
        self.assertEqual(self.client.get('/api/calibration-references/').status_code, 200)
        self.assertEqual(self.client.patch(route, {'diagnostics': {'changed': True}}, format='json').status_code, 400)
        self.assertEqual(self.client.delete(route).status_code, 405)

    def test_reference_optional_file_is_verified_and_stored_verbatim(self):
        response = self.client.post('/api/calibration-references/', self.reference_data(source_image=upload()), format='multipart')
        self.assertEqual(response.status_code, 201, response.data)
        reference = CalibrationReference.objects.get(pk=response.data['id'])
        self.assertEqual(Path(reference.source_image.path).read_bytes(), image_bytes())
        self.assertTrue(reference.source_image.name.startswith(f'calibration/references/{self.calibration.pk}/'))
        response = self.client.patch(f'/api/calibration-references/{reference.pk}/', {'source_image': upload()}, format='multipart')
        self.assertEqual(response.status_code, 400)

    def test_bad_reference_hash_or_dimensions_does_not_create_files(self):
        for overrides in ({'source_sha256': '0' * 64}, {'source_width_px': 64}):
            with self.subTest(overrides=overrides):
                response = self.client.post('/api/calibration-references/', self.reference_data(source_image=upload(), **overrides), format='multipart')
                self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(CalibrationReference.objects.exists())
        self.assertEqual(list(Path(self.temp.name).rglob('*')), [])

    def test_reference_cannot_be_added_after_use(self):
        self.make_series()
        response = self.client.post('/api/calibration-references/', self.reference_data(), format='json')
        self.assertEqual(response.status_code, 400)

    def test_measured_reference_requires_scales_and_matching_dimensions(self):
        response = self.client.post('/api/calibration-references/', self.reference_data(measurement_status='MEASURED'), format='json')
        self.assertEqual(response.status_code, 400)
        response = self.client.post('/api/calibration-references/', self.reference_data(
            measurement_status='MEASURED', measured_scale_x_um_per_px='0.055', measured_scale_y_um_per_px='0.056'), format='json')
        self.assertEqual(response.status_code, 201, response.data)

    def test_retired_cannot_be_assigned_later_to_uncalibrated_series(self):
        series = self.make_series(calibration=None)
        self.calibration.status = 'RETIRED'
        self.calibration.save()
        response = self.client.patch(f'/api/acquisition-series/{series.pk}/',
                                     {'calibration': self.calibration.pk}, format='json')
        self.assertEqual(response.status_code, 400)
        series.refresh_from_db()
        self.assertIsNone(series.calibration_id)

    def test_calibration_provenance_and_method_are_not_silently_overwritten(self):
        route = f'/api/calibrations/{self.calibration.pk}/'
        for data in ({'provenance': {'changed': True}}, {'method': 'different'}, {'algorithm_version': 'different'}):
            with self.subTest(data=data):
                self.assertEqual(self.client.patch(route, data, format='json').status_code, 400)
        self.calibration.refresh_from_db()
        self.assertEqual(self.calibration.provenance, {})
        self.assertEqual(self.calibration.method, 'synthetic')
        self.assertEqual(self.calibration.algorithm_version, 'test-1')

    def test_reference_storage_compensated_when_database_insert_fails(self):
        data = self.reference_data(source_image=upload())
        data['calibration'] = self.calibration
        reference = CalibrationReference(**data)
        with patch.object(CalibrationReference, '_do_insert', side_effect=RuntimeError('Synthetic DB failure')):
            with self.assertRaisesMessage(RuntimeError, 'Synthetic DB failure'):
                reference.save()
        self.assertFalse(CalibrationReference.objects.exists())
        self.assertFalse(any(p.is_file() for p in Path(self.temp.name).rglob('*')))
