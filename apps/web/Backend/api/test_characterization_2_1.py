"""Independent numerical fixtures for SALIVA 2.1 (stdlib + Pillow only)."""
import copy
import json
import math
import tempfile
from pathlib import Path

from django.test import SimpleTestCase
from PIL import Image, ImageDraw

from api.services.characterization.intensity import mean_gray_intensity
from api.services.characterization.raster import ObjectRaster, rasterize_object
from api.services.characterization.raster_metrics import measure_raster, measure_texture
from api.services.characterization.saliva import _measure_object
from api.services.characterization.service import characterize_effective_segmentation


def box(x1, y1, x2, y2):
    return [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]


def object_payload(points, label='membrana', object_id=1):
    return {'id': object_id, 'label': label,
            'geometry': {'type': 'polygon', 'points': points}}


class RasterMetrics21Tests(SimpleTestCase):
    def measure(self, points, image):
        warnings = []
        result = _measure_object(object_payload(points), image, warnings)
        return result['metrics'], [w['code'] for w in warnings]

    def test_eccentricity_circle_rectangle_and_translation(self):
        # Symmetric raster circle: equal central moments, zero eccentricity.
        circle = Image.new('L', (21, 21))
        ImageDraw.Draw(circle).ellipse((0, 0, 20, 20), fill=1)
        metrics = measure_raster(ObjectRaster(21, 21, circle.tobytes(), None))
        self.assertAlmostEqual(metrics['eccentricity'], 0)
        # Inclusive rectangle has 11 x 3 pixels: variances 10 and 2/3.
        expected = math.sqrt(1 - (2 / 3) / 10)
        image = Image.new('L', (100, 100), 70)
        first, _ = self.measure(box(0, 0, 10, 2), image)
        moved, _ = self.measure(box(41, 53, 51, 55), image)
        self.assertAlmostEqual(first['eccentricity'], expected)
        self.assertEqual(first['eccentricity'], moved['eccentricity'])
        self.assertGreater(first['eccentricity'], .9)
        self.assertTrue(0 <= first['eccentricity'] <= 1)
        self.assertEqual(first['centroid_px'], [5, 1])
        self.assertEqual(moved['centroid_px'], [46, 54])

    def test_std_population_normalization_translation_and_legacy_mean(self):
        # Four mask pixels [0, 0, 255, 255]: population mean/std both .5.
        image = Image.new('L', (12, 12), 37)
        for x, y, value in [(1, 1, 0), (2, 1, 0), (1, 2, 255), (2, 2, 255),
                            (7, 8, 0), (8, 8, 0), (7, 9, 255), (8, 9, 255)]:
            image.putpixel((x, y), value)
        first, _ = self.measure(box(1, 1, 2, 2), image)
        moved, _ = self.measure(box(7, 8, 8, 9), image)
        self.assertEqual(first['mean_gray_intensity'], .5)
        self.assertEqual(first['std_gray_intensity'], .5)
        for key in ('mean_gray_intensity', 'std_gray_intensity', 'texture', 'eccentricity'):
            self.assertEqual(first[key], moved[key])
        self.assertEqual(mean_gray_intensity(box(1, 1, 2, 2), image), .5)

    def test_constant_glcm_and_std(self):
        metrics, warnings = self.measure(box(1, 1, 3, 3), Image.new('L', (5, 5), 128))
        self.assertEqual(metrics['std_gray_intensity'], 0)
        self.assertEqual(metrics['mean_gray_intensity'], 128 / 255)
        self.assertEqual(metrics['texture'], {
            'contrast': 0, 'homogeneity': 1, 'energy': 1, 'entropy': 0,
            'correlation': None, 'valid_angles': 4, 'valid_pairs': 20,
        })
        self.assertEqual(warnings, ['TEXTURE_CORRELATION_UNDEFINED'])

    def test_checkerboard_quantization_four_angles_and_unweighted_average(self):
        image = Image.new('L', (2, 2))
        image.putdata([0, 255, 255, 0])
        metrics, _ = self.measure(box(0, 0, 1, 1), image)
        texture = metrics['texture']
        # Horizontal/vertical: two symmetric off-diagonal entries, correlation
        # -1, entropy 1. Diagonals: one constant entry, correlation undefined.
        self.assertEqual(texture['valid_angles'], 4)
        self.assertEqual(texture['valid_pairs'], 6)  # 2+1+2+1, before symmetry
        self.assertEqual(texture['contrast'], 31 ** 2 / 2)
        self.assertAlmostEqual(texture['homogeneity'], (1 + 1 / 962) / 2)
        self.assertAlmostEqual(texture['energy'], (1 + math.sqrt(.5)) / 2)
        self.assertEqual(texture['entropy'], .5)
        self.assertEqual(texture['correlation'], -1)  # skip constant angles
        self.assertEqual(self.measure(box(0, 0, 1, 1), image)[0], metrics)

    def test_quantization_bin_boundaries_and_one_orientation(self):
        # 7 -> 0, 8 -> 1, 255 -> 31. Symmetric probabilities all 1/4.
        raster = ObjectRaster(3, 1, bytes([1, 1, 1]), bytes([7, 8, 255]))
        texture = measure_texture(raster)
        self.assertEqual(texture['valid_pairs'], 2)
        self.assertEqual(texture['valid_angles'], 1)
        self.assertEqual(texture['contrast'], (1 + 30 ** 2) / 2)
        self.assertEqual(texture['energy'], .5)
        self.assertEqual(texture['entropy'], 2)

    def test_outside_polygon_and_bbox_cannot_contaminate_photometry(self):
        points = [[1, 1], [8, 1], [1, 8]]
        mask = Image.new('L', (10, 10))
        ImageDraw.Draw(mask).polygon([tuple(p) for p in points], fill=1, outline=1)
        dark, light = Image.new('L', (10, 10), 0), Image.new('L', (10, 10), 255)
        for y in range(10):
            for x in range(10):
                if mask.getpixel((x, y)):
                    dark.putpixel((x, y), (13 * x + 27 * y) % 256)
                    light.putpixel((x, y), (13 * x + 27 * y) % 256)
        self.assertNotEqual(dark.getpixel((8, 8)), light.getpixel((8, 8)))
        first, _ = self.measure(points, dark)
        second, _ = self.measure(points, light)
        for key in ('mean_gray_intensity', 'std_gray_intensity', 'texture'):
            self.assertEqual(first[key], second[key])

    def test_crop_preserves_full_image_pillow_2_0_pixels_and_mean(self):
        image = Image.new('L', (20, 20))
        image.putdata([(index * 17) % 256 for index in range(400)])
        polygons = [box(0, 0, 19, 19), box(3.8, 4.2, 12.9, 15.7),
                    [[2.9, 3.1], [16.8, 5.9], [12.2, 17.7], [7.1, 9.9]],
                    [[2, 2], [13, 2], [13, 5], [5, 5], [5, 13], [2, 13]]]
        for points in polygons:
            mask = Image.new('L', image.size)
            ImageDraw.Draw(mask).polygon([tuple(p) for p in points], fill=1, outline=1)
            values = [v for v, inside in zip(image.getdata(), mask.getdata()) if inside]
            metrics, _ = self.measure(points, image)
            self.assertEqual(metrics['mean_gray_intensity'], sum(values) / len(values) / 255)
            self.assertEqual(sum(rasterize_object(points, image).mask), len(values))
            expected_std = math.sqrt(sum((v / 255 - metrics['mean_gray_intensity']) ** 2 for v in values) / len(values))
            self.assertAlmostEqual(metrics['std_gray_intensity'], expected_std)

    def test_single_pixel_empty_and_sparse_masks_no_nan(self):
        image = Image.new('L', (4, 4), 85)
        metrics, warnings = self.measure(box(1.1, 1.1, 1.4, 1.4), image)
        self.assertIsNone(metrics['eccentricity'])
        self.assertEqual(metrics['std_gray_intensity'], 0)
        self.assertEqual(metrics['texture']['valid_pairs'], 0)
        self.assertIn('TEXTURE_INSUFFICIENT_PAIRS', warnings)
        empty = measure_raster(ObjectRaster(0, 0, b'', b''))
        self.assertIsNone(empty['std_gray_intensity'])
        self.assertIsNone(empty['eccentricity'])
        sparse = measure_raster(ObjectRaster(3, 1, bytes([1, 0, 1]), bytes([0, 255, 255])))
        self.assertEqual(sparse['texture']['valid_pairs'], 0)
        self.assertEqual(sparse['eccentricity'], 1)
        json.dumps([metrics, empty, sparse], allow_nan=False)

    def test_degenerate_and_self_intersecting_follow_existing_policy(self):
        for points, code in [([[1, 1], [2, 2]], 'INVALID_POINTS'),
                             ([[0, 0], [1, 0], [2, 0]], 'DEGENERATE_POLYGON'),
                             ([[0, 0], [4, 4], [0, 4], [4, 0]], 'SELF_INTERSECTING_POLYGON')]:
            effective = {'fuente': 'AUTOMATICO', 'resultado': {'objects': [object_payload(points)]}}
            result = characterize_effective_segmentation(effective, sample_type='SALIVA')
            metrics = result['cells'][0]['metrics']
            self.assertIsNone(metrics['eccentricity'])
            self.assertIsNone(metrics['std_gray_intensity'])
            self.assertTrue(all(metrics['texture'][key] is None for key in ('contrast', 'correlation', 'entropy')))
            codes = [warning['code'] for warning in result['warnings']]
            self.assertIn(code, codes)
            self.assertEqual(codes.count('ECCENTRICITY_NOT_COMPUTABLE'), 1)
            json.dumps(result, allow_nan=False)

    def test_image_unavailable_and_coordinate_mismatch_preserve_geometry(self):
        points = box(1, 1, 5, 3)
        no_image, _ = self.measure(points, None)
        mismatch, warnings = self.measure(points, Image.new('L', (2, 2)))
        self.assertIsNotNone(no_image['eccentricity'])
        for metrics in (no_image, mismatch):
            self.assertEqual(metrics['area_px2'], 8)
            self.assertIsNone(metrics['mean_gray_intensity'])
            self.assertIsNone(metrics['std_gray_intensity'])
        self.assertIn('COORDINATE_SPACE_MISMATCH', warnings)

    def test_current_alt_identical_all_types_and_existing_relative_metrics(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'original.png'
            Image.new('RGB', (32, 32), (128, 128, 128)).save(path)
            effective = {'fuente': 'AUTOMATICO', 'resultado_segmentacion_id': 12,
                         'resultado': {'objects': [
                             object_payload(box(0, 0, 30, 30)),
                             object_payload(box(5, 5, 9, 9), 'nucleo', 2),
                             object_payload(box(11, 6, 13, 8), 'micronucleo', 3)]}}
            original = copy.deepcopy(effective)
            results = []
            for strategy in ('CURRENT_CUSTOM_V1', 'ALT_CPSAM_MORPHOLOGICAL_V1'):
                results.append(characterize_effective_segmentation(
                    {**effective, 'segmentation_strategy': strategy}, sample_type='SALIVA', image_path=path))
            self.assertEqual(results[0], results[1])
            self.assertEqual(effective, original)
            result = results[0]
            self.assertEqual(result['schema_version'], '2.1')
            cell = result['cells'][0]
            for obj in (cell, cell['nuclei'][0], cell['micronuclei'][0]):
                self.assertIsNotNone(obj['metrics']['eccentricity'])
                self.assertEqual(obj['metrics']['std_gray_intensity'], 0)
                self.assertEqual(obj['metrics']['texture']['valid_angles'], 4)
            mn = cell['micronuclei'][0]
            self.assertEqual(mn['nucleus_id'], 2)
            self.assertEqual(mn['metrics']['distance_to_nucleus_px'], 5)
            self.assertEqual(mn['metrics']['area_fraction_to_nucleus'], .25)
            self.assertEqual(mn['metrics']['intensity_fraction_to_nucleus'], 1)
            self.assertEqual(result['summary']['genotoxicity_index'], 1)
            self.assertEqual(result['summary']['cytotoxicity_index'], 0)
            self.assertEqual(result['methodology']['texture']['gray_levels'], 32)
            json.dumps(result, allow_nan=False)

    def test_blood_contract_stays_counts_only_1_0(self):
        result = characterize_effective_segmentation(
            {'fuente': 'AUTOMATICO', 'resultado': {'objects': [object_payload(box(0, 0, 2, 2))]}},
            sample_type='SANGRE')
        self.assertEqual(result['version'], '1.0')
        self.assertEqual(result['counts'], {'membrana': 1, 'micronucleo': 0})
        for key in ('eccentricity', 'std_gray_intensity', 'texture', 'methodology', 'schema_version'):
            self.assertNotIn(key, json.dumps(result))
