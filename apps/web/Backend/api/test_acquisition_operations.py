import hashlib
import json
from decimal import Decimal
from io import BytesIO, StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image

from api import test_acquisition as acquisition_fixtures
from api.test_calibration import disk, grid
from api.models import AcquisitionProfile, Calibration, CalibrationReference, AcquisitionSeries
from api.services.acquisition.optika_seed import seed_optika, REFERENCES, SX, SY


class AcquisitionOperationsTests(TestCase):
    setUp = acquisition_fixtures.AcquisitionTests.setUp
    make_calibration = acquisition_fixtures.AcquisitionTests.make_calibration
    make_series = acquisition_fixtures.AcquisitionTests.make_series

    def automatic_profile(self):
        return AcquisitionProfile.objects.create(name='Synthetic microscope', image_width_px=512,
                image_height_px=512, image_mode='L', objective_magnification=40)

    def payload(self, profile, patterns=('CIRCLE',), token='', **overrides):
        refs, files = [], {}
        for index, pattern in enumerate(patterns):
            stream = BytesIO()
            Image.fromarray(disk() if pattern == 'CIRCLE' else grid()).save(stream, 'PNG')
            refs.append({'pattern_type': pattern, 'known_dimension_um': '70' if pattern == 'CIRCLE' else '10',
                         **({'grid_reference': 'uniform_lattice'} if pattern == 'GRADUATED_GRID' else {})})
            files[f'reference_{index}'] = SimpleUploadedFile(f'ref{index}.png', stream.getvalue(), 'image/png')
        return {'acquisition_profile': profile.pk, 'label': 'Synthetic automatic', 'references': json.dumps(refs),
                'source_token': token, **files, **overrides}

    def preview(self, profile, patterns=('CIRCLE',)):
        response = self.client.post('/api/calibrations/automatic-preview/', self.payload(profile, patterns), format='multipart')
        self.assertEqual(response.status_code, 200, response.data)
        return response.data['review']

    def test_single_circle_preview_then_atomic_create(self):
        profile = self.automatic_profile()
        before = Calibration.objects.count()
        review = self.preview(profile)
        self.assertTrue(review['usable'])
        self.assertEqual(Calibration.objects.count(), before)
        response = self.client.post('/api/calibrations/automatic/', self.payload(profile, token=review['source_token']), format='multipart')
        self.assertEqual(response.status_code, 201, response.data)
        calibration = Calibration.objects.get(pk=response.data['calibration']['id'])
        self.assertEqual(calibration.status, 'PROVISIONAL')
        self.assertEqual(calibration.references.count(), 1)
        reference = calibration.references.get()
        self.assertEqual(hashlib.sha256(Path(reference.source_image.path).read_bytes()).hexdigest(), reference.source_sha256)
        self.assertTrue(calibration.provenance['important_pending_18s_a2'])

    def test_multiple_circle_grid_reuse_engine(self):
        profile = self.automatic_profile()
        for patterns in (('GRADUATED_GRID',), ('CIRCLE','GRADUATED_GRID')):
            with self.subTest(patterns=patterns):
                review = self.preview(profile, patterns)
                self.assertTrue(review['usable'])
                response = self.client.post('/api/calibrations/automatic/', self.payload(profile, patterns, review['source_token']), format='multipart')
                self.assertEqual(response.status_code, 201, response.data)
                self.assertEqual(Calibration.objects.get(pk=response.data['calibration']['id']).references.count(), len(patterns))

    def test_ambiguous_grid_excluded_and_not_upgraded(self):
        profile = self.automatic_profile()
        payload = self.payload(profile, ('CIRCLE', 'GRADUATED_GRID'))
        metadata = json.loads(payload['references']); metadata[1].pop('grid_reference'); payload['references'] = json.dumps(metadata)
        response = self.client.post('/api/calibrations/automatic-preview/', payload, format='multipart')
        self.assertEqual(response.status_code, 200, response.data)
        review = response.data['review']
        self.assertTrue(review['usable'])
        self.assertEqual(review['results'][1]['measurement_status'], 'AMBIGUOUS_GRID_PERIODICITY')
        self.assertEqual(review['status'], 'PROVISIONAL')

    def test_no_measurable_scale_creates_nothing(self):
        profile = self.automatic_profile()
        payload = self.payload(profile, ('GRADUATED_GRID',))
        metadata = json.loads(payload['references']); metadata[0].pop('grid_reference'); payload['references'] = json.dumps(metadata)
        count = Calibration.objects.count()
        response = self.client.post('/api/calibrations/automatic/', payload, format='multipart')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Calibration.objects.count(), count)
        self.assertFalse(CalibrationReference.objects.exists())
        self.assertFalse(any(p.is_file() for p in Path(self.temp.name).rglob('*')))

    def test_atomic_rollback_cleans_earlier_reference_files(self):
        profile = self.automatic_profile()
        review = self.preview(profile, ('CIRCLE', 'CIRCLE'))
        original = CalibrationReference.save
        count = Calibration.objects.count()
        calls = []
        def fail_second(instance, *args, **kwargs):
            calls.append(instance)
            if len(calls) == 2:
                raise RuntimeError('Synthetic persistence failure')
            return original(instance, *args, **kwargs)
        with patch.object(CalibrationReference, 'save', fail_second):
            with self.assertRaisesMessage(RuntimeError, 'Synthetic persistence failure'):
                self.client.post('/api/calibrations/automatic/', self.payload(profile, ('CIRCLE','CIRCLE'), review['source_token']), format='multipart')
        self.assertEqual(Calibration.objects.count(), count)
        self.assertFalse(CalibrationReference.objects.exists())
        self.assertFalse(any(p.is_file() for p in Path(self.temp.name).rglob('*')))

    def test_engine_exception_no_partial_data(self):
        count = Calibration.objects.count()
        with patch('api.services.acquisition.automatic.measure_image', side_effect=RuntimeError('Synthetic engine failure')):
            with self.assertRaisesMessage(RuntimeError, 'Synthetic engine failure'):
                self.client.post('/api/calibrations/automatic/', self.payload(self.automatic_profile()), format='multipart')
        self.assertEqual(Calibration.objects.count(), count)
        self.assertFalse(CalibrationReference.objects.exists())

    def test_stale_preview_and_invalid_upload_rejected(self):
        profile = self.automatic_profile()
        review = self.preview(profile)
        payload = self.payload(profile, token=review['source_token'])
        refs = json.loads(payload['references']); refs[0]['known_dimension_um'] = '80'; payload['references'] = json.dumps(refs)
        response = self.client.post('/api/calibrations/automatic/', payload, format='multipart')
        self.assertEqual(response.status_code, 400)
        response = self.client.post('/api/calibrations/automatic-preview/', self.payload(profile, reference_0=SimpleUploadedFile('x.png', b'broken', 'image/png')), format='multipart')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(CalibrationReference.objects.exists())

    def test_auto_requires_explicit_metadata_and_matching_resolution(self):
        profile = self.automatic_profile()
        payload = self.payload(profile, references='[{"pattern_type":"CIRCLE"}]')
        self.assertEqual(self.client.post('/api/calibrations/automatic-preview/', payload, format='multipart').status_code, 400)
        profile.image_width_px = 256; profile.save()
        self.assertFalse(self.preview(profile)['usable'])

    def test_seed_first_second_exact_values_and_references(self):
        count = Calibration.objects.count()
        output = StringIO(); call_command('seed_optika_40x_calibration', stdout=output)
        first = json.loads(output.getvalue()); second = seed_optika()
        self.assertEqual(first['status'], 'CREATED'); self.assertEqual(second['status'], 'ALREADY_PRESENT')
        calibration = Calibration.objects.get(pk=first['calibration_id'])
        self.assertEqual((calibration.scale_x_um_per_px, calibration.scale_y_um_per_px), (SX,SY))
        self.assertEqual(calibration.status, 'PROVISIONAL')
        self.assertEqual(Calibration.objects.count(), count+1)
        self.assertEqual(calibration.references.count(), 3)
        self.assertEqual(calibration.references.get(pattern_type='GRADUATED_GRID').measurement_status, 'AMBIGUOUS_GRID_PERIODICITY')
        self.assertEqual(calibration.provenance['circle_150']['sx'], '0.054382897123')
        self.assertFalse(AcquisitionSeries.objects.exists())

    def test_seed_wrong_hash_before_any_write(self):
        count = AcquisitionProfile.objects.count()
        with TemporaryDirectory() as source:
            (Path(source)/REFERENCES[0][0]).write_bytes(b'not the approved file')
            with self.assertRaisesMessage(CommandError, 'SOURCE_HASH_MISMATCH'):
                seed_optika(source)
        self.assertEqual(AcquisitionProfile.objects.count(), count)
        self.assertFalse(CalibrationReference.objects.exists())

    def test_seed_conflicting_label_not_overwritten(self):
        first = seed_optika()
        calibration = Calibration.objects.get(pk=first['calibration_id'])
        calibration.status = 'RETIRED'; calibration.save()
        with self.assertRaisesMessage(CommandError, 'EXISTING_CALIBRATION_CONFLICT'):
            seed_optika()
        calibration.refresh_from_db(); self.assertEqual(calibration.status, 'RETIRED')

    def test_series_patient_filter_and_authentication(self):
        own = self.make_series(); self.make_series(patient=self.other)
        response = self.client.get('/api/acquisition-series/', {'patient': self.patient.pk})
        self.assertEqual([item['id'] for item in response.data], [own.pk])
        self.assertEqual(self.client.get('/api/acquisition-series/', {'patient':'bad'}).status_code, 400)
        self.assertEqual(self.client.get('/api/acquisition-operator/').status_code, 200)
        self.client.force_authenticate(None)
        self.assertIn(self.client.get('/api/acquisition-operator/').status_code, (401,403))
        self.assertIn(self.client.post('/api/calibrations/automatic-preview/', self.payload(self.automatic_profile()), format='multipart').status_code, (401,403))

    def test_anonymous_legacy_upload_gets_backend_physical_status(self):
        from api.test_acquisition import upload
        self.client.force_authenticate(None)
        for route in ('muestras', 'muestras-sangre'):
            response = self.client.post(f'/api/{route}/', {'analisis': self.analysis.pk, 'imagen': upload()}, format='multipart')
            self.assertEqual(response.status_code, 201, response.data)
            self.assertEqual(response.data['physical_compatibility']['status'], 'NO_ACQUISITION_SERIES')

    def test_uploaded_resolution_mismatch_preserves_success_and_pixel_processing(self):
        from api.test_acquisition import upload, image_bytes
        series = self.make_series()
        for route in ('muestras', 'muestras-sangre'):
            response = self.client.post(f'/api/{route}/', {'analisis': self.analysis.pk, 'imagen': upload(image_bytes((16,16))), 'acquisition_series': series.pk}, format='multipart')
            self.assertEqual(response.status_code, 201, response.data)
            self.assertEqual(response.data['physical_compatibility']['status'], 'RESOLUTION_MISMATCH')
            self.assertFalse(response.data['physical_compatibility']['compatible_for_physical_units'])

    def test_post_upload_check_failure_does_not_invalidate_confirmed_upload(self):
        from api.test_acquisition import upload
        with patch('api.services.acquisition.physical_compatibility', side_effect=RuntimeError('Synthetic unavailable check')):
            response = self.client.post('/api/muestras/', {'analisis': self.analysis.pk, 'imagen': upload()}, format='multipart')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['physical_compatibility']['status'], 'CHECK_FAILED')

    def test_audit_read_only_aliases_and_no_series_assignment(self):
        from api.test_acquisition import upload
        from api.models import MuestraSaliva
        sample = MuestraSaliva.objects.create(analisis=self.analysis, imagen=upload())
        output = StringIO(); call_command('audit_historical_acquisition', width=32, height=32, stdout=output)
        report = json.loads(output.getvalue())
        row = next(row for row in report['patients'] if row['samples'])
        self.assertEqual(row['resolution_matches_only'], 1)
        self.assertTrue(row['patient_alias'].startswith('PATIENT_'))
        self.assertNotIn(self.patient.identificacion, output.getvalue())
        sample.refresh_from_db(); self.assertIsNone(sample.acquisition_series_id)
        self.assertFalse(AcquisitionSeries.objects.exists())

    def test_profile_reports_physical_editability_without_changing_schema(self):
        response = self.client.get(f'/api/acquisition-profiles/{self.profile.pk}/')
        self.assertTrue(response.data['physical_fields_locked'])
        profile = self.automatic_profile()
        response = self.client.get(f'/api/acquisition-profiles/{profile.pk}/')
        self.assertFalse(response.data['physical_fields_locked'])
        response = self.client.patch(f'/api/acquisition-profiles/{profile.pk}/', {'objective_magnification':'20'}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        profile.refresh_from_db(); self.assertEqual(profile.objective_magnification, Decimal('20'))
