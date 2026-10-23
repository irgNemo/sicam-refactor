from api.testing import tenant_fixture
"""2.2 numerical/persistence acceptance. All writes use test DB and /tmp media."""
import copy
import math
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone
from PIL import Image
from api.testing import PlatformClient as APIClient

from api import test_acquisition as acq
from api.test_characterization_2_1 import box, object_payload
from api.models import (ResultadoSegmentacion, ResultadoCaracterizacion, RevisionSegmentacion,
                        AcquisitionProfile, Calibration, AcquisitionSeries)
from api.services.characterization.physical import (
    FEATURE_DIMENSIONS, PHYSICAL_FIELDS, extend_physical_result, fingerprint, canonical_hash,
)
from api.services.characterization.service import (
    characterize_effective_segmentation, get_or_create_resultado_caracterizacion,
    is_characterization_current,
)
from api.services.segmentation.effective import resolve_effective_segmentation


def effective_fixture():
    return {'fuente': 'AUTOMATICO', 'resultado_segmentacion_id': 1, 'revision': None,
            'resultado': {'objects': [
                object_payload(box(0, 0, 30, 30)),
                object_payload(box(2, 2, 6, 6), 'nucleo', 2),
                object_payload(box(8, 9, 10, 11), 'micronucleo', 3),
                object_payload(box(40, 40, 44, 44), 'nucleo', 4),
                object_payload(box(50, 50, 51, 51), 'micronucleo', 5),
            ]}}


def context_fixture():
    return {'physical_units_available': True, 'physical_status': 'COMPATIBLE_PROVISIONAL',
            'physical_unavailable_reason': None,
            'physical_measurements_status': 'PROVISIONAL_CALIBRATION',
            'calibration': {'calibration_id': 1, 'status': 'PROVISIONAL',
                            'scale_x_um_per_px': '2', 'scale_y_um_per_px': '3'}}


def pixel_projection(value):
    # Remove only the declared additive physical keys, not arbitrary new data.
    if isinstance(value, list):
        return [pixel_projection(v) for v in value]
    if isinstance(value, dict):
        return {k: pixel_projection(v) for k, v in value.items() if k not in PHYSICAL_FIELDS.values()}
    return value


class PhysicalGeometryTests(SimpleTestCase):
    def setUp(self):
        self.effective = effective_fixture()
        self.pixel = characterize_effective_segmentation(self.effective)
        self.physical = extend_physical_result(self.pixel, self.effective, context_fixture())

    def test_area_all_objects_summary_and_centroids(self):
        cell = self.physical['cells'][0]
        for obj in [cell, *cell['nuclei'], *cell['micronuclei'],
                    *self.physical['unassociated']['nuclei'], *self.physical['unassociated']['micronuclei']]:
            m = obj['metrics']
            self.assertEqual(m['area_um2'], m['area_px2'] * 6)
            self.assertEqual(m['centroid_um'], [m['centroid_px'][0]*2, m['centroid_px'][1]*3])
        self.assertEqual(self.physical['summary']['mean_nucleus_area_um2'], 96)
        self.assertNotEqual(cell['metrics']['area_um2'], cell['metrics']['area_px2'] * 2.5**2)

    def test_oblique_perimeter_not_mean_scale(self):
        effective = effective_fixture()
        effective['resultado']['objects'] = [object_payload([[0, 0], [4, 0], [1, 3]])]
        pixel = characterize_effective_segmentation(effective)
        result = extend_physical_result(pixel, effective, context_fixture())
        metrics = result['cells'][0]['metrics']
        expected = 8 + math.sqrt(6**2+9**2) + math.sqrt(2**2+9**2)
        self.assertAlmostEqual(metrics['perimeter_um'], expected)
        self.assertNotAlmostEqual(metrics['perimeter_um'], metrics['perimeter_px']*2.5)

    def test_mn_distance_keeps_associated_nucleus_and_diagonal(self):
        mn = self.physical['cells'][0]['micronuclei'][0]
        self.assertEqual(mn['nucleus_id'], 2)
        self.assertAlmostEqual(mn['metrics']['distance_to_nucleus_um'], math.sqrt((5*2)**2+(6*3)**2))
        self.assertIsNone(self.physical['unassociated']['micronuclei'][0]['metrics']['distance_to_nucleus_um'])

    def test_anisotropy_cannot_change_nearest_nucleus(self):
        effective = effective_fixture()
        effective['resultado']['objects'] = [
            object_payload(box(0,0,30,30)), object_payload(box(9,7,11,9),'nucleo',2),
            object_payload(box(6,9,8,11),'nucleo',3), object_payload(box(9,9,11,11),'micronucleo',4)]
        context = context_fixture()
        context['calibration']['scale_y_um_per_px'] = '100'
        result = extend_physical_result(characterize_effective_segmentation(effective),effective,context)
        mn = result['cells'][0]['micronuclei'][0]
        self.assertEqual(mn['nucleus_id'],2)  # nearest in pixel space, NOT physical
        self.assertEqual(mn['metrics']['distance_to_nucleus_um'],200)

    def test_deep_pixel_equivalence_and_no_input_mutation(self):
        before = copy.deepcopy((self.pixel, self.effective))
        for key in ('cells','summary','unassociated','ambiguous','warnings','source','methodology'):
            self.assertEqual(pixel_projection(self.physical[key]), self.pixel[key])
        self.assertEqual((self.pixel,self.effective),before)
        self.assertEqual(self.pixel['version'],'2.1')

    def test_intensity_texture_eccentricity_exact_with_image(self):
        with TemporaryDirectory() as tmp:
            path=Path(tmp)/'synthetic.png'
            image=Image.new('L',(64,64)); image.putdata([(i*17)%256 for i in range(4096)]);image.save(path)
            pixel=characterize_effective_segmentation(self.effective,image_path=path)
            physical=extend_physical_result(pixel,self.effective,context_fixture())
        for key in ('cells','summary','unassociated','ambiguous','warnings','methodology'):
            self.assertEqual(pixel_projection(physical[key]),pixel[key])
        self.assertEqual(physical['methodology']['texture']['distance_px'],1)
        self.assertEqual(physical['methodology']['texture']['gray_levels'],32)
        self.assertTrue(physical['methodology']['texture']['symmetric'])
        self.assertEqual(physical['methodology']['texture']['angles_deg'],[0,45,90,135])

    def test_ambiguous_invalid_and_degenerate_preserve_nulls(self):
        effective=effective_fixture()
        effective['resultado']['objects'] += [object_payload(box(0,0,30,30),'membrana',6),
            object_payload([[0,0],[1,1]],'nucleo',7),
            object_payload([[0,0],[2,2],[4,4]],'nucleo',8),
            object_payload([[0,0],[4,4],[0,4],[4,0]],'nucleo',9),
            {'id':10, 'label':'nucleo','geometry':None}]
        pixel=characterize_effective_segmentation(effective)
        result=extend_physical_result(pixel,effective,context_fixture())
        self.assertEqual(pixel_projection(result['ambiguous']),pixel['ambiguous'])
        for obj in result['unassociated']['nuclei']:
            if obj['id'] in (7,8,9,10):
                self.assertIsNone(obj['metrics']['centroid_um'])
        json.dumps(result,allow_nan=False)

    def test_feature_registry_covers_object_metrics_and_physical_fields(self):
        for obj in [self.pixel['cells'][0],*self.pixel['cells'][0]['nuclei'],*self.pixel['cells'][0]['micronuclei']]:
            for key,value in obj['metrics'].items():
                if key=='texture':
                    self.assertTrue(set(value)<=FEATURE_DIMENSIONS.keys())
                else:self.assertIn(key,FEATURE_DIMENSIONS)
        self.assertEqual(FEATURE_DIMENSIONS['eccentricity'],'DIMENSIONLESS')
        self.assertEqual(FEATURE_DIMENSIONS['std_gray_intensity'],'INTENSITY')

    def test_fingerprint_canonical_context_and_object_order(self):
        context=context_fixture()
        first=fingerprint(self.effective,context)
        self.assertEqual(first,fingerprint(self.effective,dict(reversed(list(context.items())))))
        for field,value in [('calibration_id',2),('scale_x_um_per_px','4'),('status','VALIDATED')]:
            other=copy.deepcopy(context);other['calibration'][field]=value
            self.assertNotEqual(first[1],fingerprint(self.effective,other)[1])
        other=copy.deepcopy(self.effective);other['resultado']['objects'].reverse()
        self.assertNotEqual(first[0],fingerprint(other,context)[0])


class PhysicalPersistenceTests(TestCase):
    # Reuse setup helpers without inheriting/discovering the acquisition suite.
    setUp = acq.AcquisitionTests.setUp
    make_calibration = acq.AcquisitionTests.make_calibration
    make_sample = acq.AcquisitionTests.make_sample
    make_series = acq.AcquisitionTests.make_series

    def result(self, series=True, image=None):
        sample=self.make_sample(acquisition_series=self.make_series() if series else None,
                                **({'imagen':image} if image else {}))
        return ResultadoSegmentacion.objects.create(muestra=sample,tipo_muestra='SALIVA',
            estado='COMPLETADO',respuesta_json={},resultado_normalizado=effective_fixture()['resultado'])

    def characterize(self,result):
        return get_or_create_resultado_caracterizacion(result)[0]

    def test_provisional_api_e2e_4928_and_idempotence(self):
        self.profile=AcquisitionProfile.objects.create(name='4928 synthetic',image_width_px=4928,image_height_px=4928,image_mode='RGB')
        self.calibration=self.make_calibration(source_width_px=4928,source_height_px=4928,
            scale_x_um_per_px='0.055233934048',scale_y_um_per_px='0.055010060892')
        result=self.result(image=acq.upload(acq.image_bytes((4928,4928))))
        url=f'/api/resultados-segmentacion/{result.pk}/caracterizar/'
        first=self.client.post(url);second=self.client.post(url)
        self.assertEqual(first.status_code,201,first.data)
        self.assertEqual(second.status_code,200,second.data)
        self.assertEqual(first.data['id'],second.data['id'])
        data=first.data['resultado_json']
        self.assertEqual(data['version'],'2.2')
        self.assertTrue(data['physical_units_available'])
        self.assertEqual(data['physical_status'],'COMPATIBLE_PROVISIONAL')
        self.assertEqual(data['calibration']['source_width_px'],4928)
        self.assertEqual(data['calibration']['acquisition_series_id'],result.muestra.acquisition_series_id)
        self.assertEqual(data['image_dimensions_px'],{'width':4928,'height':4928})
        self.assertEqual(data['cells'][0]['metrics']['area_um2'],900*.055233934048*.055010060892)
        self.assertNotIn('0.0551219974698993',json.dumps(data))

    def test_validated_retired_and_snapshot_immutable(self):
        result=self.result();first=self.characterize(result);before=copy.deepcopy(first.resultado_json)
        self.calibration.status='VALIDATED';self.calibration.label='Validated label';self.calibration.save()
        self.assertFalse(is_characterization_current(first))
        second=self.characterize(result)
        self.assertNotEqual(first.pk,second.pk)
        self.assertEqual(second.resultado_json['physical_measurements_status'],'VALIDATED_CALIBRATION')
        self.calibration.status='RETIRED';self.calibration.save()
        third=self.characterize(result)
        self.assertFalse(third.resultado_json['physical_units_available'])
        self.assertEqual(third.resultado_json['physical_unavailable_reason'],'CALIBRATION_RETIRED')
        self.assertNotIn('area_um2',third.resultado_json['cells'][0]['metrics'])
        first.refresh_from_db();self.assertEqual(first.resultado_json,before)

    def test_without_series_then_compatible_creates_new_record(self):
        result=self.result(series=False)
        first=self.characterize(result)
        self.assertEqual(first.resultado_json['physical_status'],'NO_ACQUISITION_SERIES')
        self.assertEqual(first.resultado_json['cells'][0]['metrics']['area_px2'],900)
        sample=result.muestra;sample.acquisition_series=self.make_series();sample.save()
        second=self.characterize(result)
        self.assertNotEqual(first.pk,second.pk)
        self.assertTrue(second.resultado_json['physical_units_available'])

    def test_no_calibration_then_calibration_creates_new_record(self):
        self.calibration=None
        result=self.result();first=self.characterize(result)
        self.assertEqual(first.resultado_json['physical_status'],'NO_CALIBRATION')
        series=result.muestra.acquisition_series;series.calibration=self.make_calibration();series.save()
        second=self.characterize(result)
        self.assertNotEqual(first.pk,second.pk)
        self.assertTrue(second.resultado_json['physical_units_available'])

    def test_resolution_and_mode_mismatch_remain_pixel_only(self):
        for image,reason in [(acq.upload(acq.image_bytes((16,16))),'RESOLUTION_MISMATCH'),
                              (acq.upload(acq.image_bytes(mode='L')),'IMAGE_MODE_MISMATCH')]:
            self.profile.image_mode='RGB'
            # Before creation, this test-only fixture adjustment bypasses the
            # immutability guard; production never changes linked profiles.
            AcquisitionProfile.objects.filter(pk=self.profile.pk).update(image_mode='RGB')
            record=self.characterize(self.result(image=image))
            self.assertEqual(record.resultado_json['physical_status'],reason)
            self.assertNotIn('perimeter_um',record.resultado_json['cells'][0]['metrics'])
            self.assertEqual(record.resultado_json['cells'][0]['metrics']['perimeter_px'],120)

    def test_different_calibration_same_segmentation_new_result(self):
        result=self.result();first=self.characterize(result)
        calibration2=self.make_calibration(label='Second',scale_x_um_per_px='0.1')
        # Simulates a future authorized reassociation in test DB only. Current
        # acquisition domain deliberately forbids changing a bound calibration.
        AcquisitionSeries.objects.filter(pk=result.muestra.acquisition_series_id).update(calibration=calibration2)
        second=self.characterize(result)
        self.assertNotEqual(first.pk,second.pk)
        self.assertNotEqual(first.resultado_json['cells'][0]['metrics']['area_um2'],second.resultado_json['cells'][0]['metrics']['area_um2'])
        first.refresh_from_db()
        self.assertEqual(first.resultado_json['calibration']['calibration_id'],self.calibration.pk)

    def test_historical_21_full_record_unchanged(self):
        result=self.result()
        historical=ResultadoCaracterizacion.objects.create(resultado_segmentacion=result,
            source_type='AUTOMATICO',sample_type='SALIVA',algorithm_version='2.1',
            resultado_json=characterize_effective_segmentation(resolve_effective_segmentation(result),image_path=result.muestra.imagen.path))
        before=copy.deepcopy(ResultadoCaracterizacion.objects.filter(pk=historical.pk).values().get())
        current=self.characterize(result)
        self.assertNotEqual(current.pk,historical.pk)
        self.assertEqual(ResultadoCaracterizacion.objects.filter(pk=historical.pk).values().get(),before)
        self.assertFalse(is_characterization_current(historical))
        self.assertTrue(is_characterization_current(current))

    def test_effective_validated_and_draft_never_consumed(self):
        result=self.result()
        first=self.characterize(result)
        validated=RevisionSegmentacion.objects.create(resultado_segmentacion=result,numero_revision=1,
            estado='VALIDADA',resultado_editado=copy.deepcopy(result.resultado_normalizado),resumen={},validado_en=timezone.now())
        draft=RevisionSegmentacion.objects.create(resultado_segmentacion=result,numero_revision=2,
            estado='BORRADOR',resultado_editado={'objects':[]},resumen={})
        second=self.characterize(result)
        self.assertEqual(second.revision_segmentacion_id,validated.pk)
        self.assertEqual(second.resultado_json['summary']['total_membranes'],1)
        self.assertEqual(second.resultado_json['provenance']['effective_segmentation_hash'],canonical_hash(validated.resultado_editado))
        self.assertFalse(is_characterization_current(first))
        draft.refresh_from_db();self.assertEqual(draft.estado,'BORRADOR')

    def test_manual_guard_and_base_snapshot_unchanged(self):
        result=self.result();result.base_origin='MANUAL';result.save()
        before=copy.deepcopy(result.resultado_normalizado)
        with self.assertRaisesMessage(ValueError,'valide'):
            self.characterize(result)
        result.refresh_from_db();self.assertEqual(result.resultado_normalizado,before)
        self.assertEqual(ResultadoCaracterizacion.objects.count(),0)

    def test_compatibility_authority_denials_never_fabricate_units(self):
        result=self.result()
        for reason in ('PROFILE_MISMATCH','PATIENT_MISMATCH','INVALID_CALIBRATION','INVALID_IMAGE'):
            with patch('api.services.characterization.physical.physical_compatibility',return_value={
                'compatible_for_physical_units':False,'status':reason}):
                data=self.characterize(result).resultado_json
                self.assertEqual(data['physical_unavailable_reason'],reason)
                self.assertFalse(data['physical_units_available'])
                self.assertNotIn('area_um2',data['cells'][0]['metrics'])

    def test_changed_base_payload_changes_fingerprint(self):
        result=self.result();first=self.characterize(result)
        result.resultado_normalizado['objects'].pop();result.save()
        second=self.characterize(result)
        self.assertNotEqual(first.pk,second.pk)
        self.assertFalse(is_characterization_current(first))

    def test_exact_4928_profile_2464_image_no_resampling(self):
        self.profile=AcquisitionProfile.objects.create(name='4928 mismatch',image_width_px=4928,image_height_px=4928)
        self.calibration=self.make_calibration(source_width_px=4928,source_height_px=4928)
        result=self.result(image=acq.upload(acq.image_bytes((2464,2464))))
        path=Path(result.muestra.imagen.path)
        before=path.read_bytes()
        data=self.characterize(result).resultado_json
        self.assertEqual(data['physical_status'],'RESOLUTION_MISMATCH')
        self.assertEqual(data['image_dimensions_px'],{'width':2464,'height':2464})
        self.assertNotIn('area_um2',data['cells'][0]['metrics'])
        self.assertEqual(path.read_bytes(),before)

    def test_unreadable_original_preserves_21_geometry_warning_no_physical(self):
        result=self.result()
        Path(result.muestra.imagen.path).write_bytes(b'invalid synthetic image')
        data=self.characterize(result).resultado_json
        self.assertEqual(data['physical_status'],'INVALID_IMAGE')
        self.assertFalse(data['physical_units_available'])
        self.assertNotIn('area_um2',data['cells'][0]['metrics'])
        self.assertEqual(data['cells'][0]['metrics']['area_px2'],900)
        self.assertIsNone(data['cells'][0]['metrics']['mean_gray_intensity'])
        self.assertIn('IMAGE_UNAVAILABLE',[w['code'] for w in data['warnings']])
