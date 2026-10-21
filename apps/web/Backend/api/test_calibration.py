"""Generated, nonclinical fixtures. Numerical tolerances are engineering tests,
not acceptance thresholds for real calibration patterns. No database is used.
"""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

import cv2
import numpy as np
from PIL import Image

from api.services.calibration.circle import measure_circle
from api.services.calibration.common import MeasurementError
from api.services.calibration.engine import measure_image, consensus
from api.services.calibration.grid import measure_grid
from api.services.calibration.cli import run


def disk(center=(240, 250), radii=(100, 100), noise=0, blur=0, gradient=False, angle=0):
    y, x = np.mgrid[:512, :512].astype(float)
    a = np.radians(angle)
    u = (x-center[0])*np.cos(a)+(y-center[1])*np.sin(a)
    v = -(x-center[0])*np.sin(a)+(y-center[1])*np.cos(a)
    distance = (np.sqrt((u/radii[0])**2+(v/radii[1])**2)-1)*min(radii)
    pixels = 20+190*np.clip(distance+.5, 0, 1)
    if gradient:
        pixels *= .65+.35*x/512
    if blur:
        pixels = cv2.GaussianBlur(pixels, (0, 0), blur)
    if noise:
        pixels += np.random.default_rng(18).normal(0, noise, pixels.shape)
    return np.clip(pixels, 0, 255).astype(np.uint8)


def grid(noise=0, blur=0, gradient=False, angle=0, missing=False, outlier=False):
    pixels = np.full((512, 512), 210., dtype=float)
    xs = list(range(55, 456, 40))
    ys = list(range(55, 456, 50))
    if missing:
        xs.remove(215)
        ys.remove(255)
    if outlier:
        xs.append(232)
        ys.append(322)
    for x in xs:
        pixels[25:487, x-1:x+2] = 20
    for y in ys:
        pixels[y-1:y+2, 25:487] = 20
    if gradient:
        pixels *= .65+.35*np.arange(512)[None, :]/512
    if angle:
        pixels = cv2.warpAffine(pixels, cv2.getRotationMatrix2D((255.5, 255.5), angle, 1), (512, 512), borderValue=210)
    if blur:
        pixels = cv2.GaussianBlur(pixels, (0, 0), blur)
    if noise:
        pixels += np.random.default_rng(19).normal(0, noise, pixels.shape)
    return np.clip(pixels, 0, 255).astype(np.uint8)


class CircleCalibrationTests(TestCase):
    def test_circle_clean_noise_blur_gradient_shifted(self):
        for options in ({}, {'noise': 8}, {'blur': 2}, {'gradient': True}, {'center': (150, 340)},
                        {'noise': 6, 'blur': 1.5, 'gradient': True}):
            with self.subTest(options=options):
                result = measure_circle(disk(**options), 70)
                self.assertEqual(result['measurement_status'], 'MEASURED')
                for axis in ('x', 'y'):
                    self.assertAlmostEqual(result[f'scale_{axis}_um_per_px'], .35, delta=.0035)
                self.assertLess(result['fit_metrics']['fit_residual_px'], 1)
                self.assertGreater(result['fit_metrics']['inlier_fraction'], .8)

    def test_known_ellipse_anisotropy(self):
        result = measure_circle(disk(radii=(110, 80)), 70)
        self.assertAlmostEqual(result['scale_x_um_per_px'], 70/220, delta=.003)
        self.assertAlmostEqual(result['scale_y_um_per_px'], 70/160, delta=.003)
        self.assertAlmostEqual(result['anisotropy_percent'], 100*60/190, delta=.5)
        self.assertGreater(result['fit_metrics']['circle_fit_residual_px'], 8)
        self.assertLess(result['fit_metrics']['fit_residual_px'], .5)

    def test_rotated_ellipse_extents(self):
        result = measure_circle(disk(radii=(110, 80), angle=20), 70)
        a = np.radians(20)
        dx = 2*np.sqrt((110*np.cos(a))**2+(80*np.sin(a))**2)
        dy = 2*np.sqrt((110*np.sin(a))**2+(80*np.cos(a))**2)
        self.assertAlmostEqual(result['fit_metrics']['diameter_x_px'], dx, delta=1)
        self.assertAlmostEqual(result['fit_metrics']['diameter_y_px'], dy, delta=1)

    def test_clipped_and_near_edge(self):
        for center in ((30, 250), (102, 250)):
            with self.subTest(center=center), self.assertRaises(MeasurementError) as caught:
                measure_circle(disk(center=center), 70)
            self.assertEqual(caught.exception.status, 'CLIPPED_REFERENCE_OBJECT')

    def test_multiple_comparable_disks_ambiguous(self):
        pixels = np.minimum(disk(center=(140, 250), radii=(75, 75)), disk(center=(370, 250), radii=(75, 75)))
        with self.assertRaises(MeasurementError) as caught:
            measure_circle(pixels, 70)
        self.assertEqual(caught.exception.status, 'AMBIGUOUS_REFERENCE_OBJECT')

    def test_blank_is_not_measured(self):
        with self.assertRaises(MeasurementError):
            measure_circle(np.full((256, 256), 200, np.uint8), 70)

    def test_deterministic(self):
        pixels = disk(noise=5, gradient=True)
        self.assertEqual(measure_circle(pixels, 70), measure_circle(pixels, 70))


class GridCalibrationTests(TestCase):
    def test_known_pitch_noise_blur_gradient_missing_outlier(self):
        for options in ({}, {'noise': 8}, {'blur': 1.2}, {'gradient': True}, {'missing': True}, {'outlier': True},
                        {'noise': 5, 'blur': 1, 'gradient': True}):
            with self.subTest(options=options):
                result = measure_grid(grid(**options), 10, 'uniform_lattice')
                self.assertEqual(result['measurement_status'], 'MEASURED')
                self.assertAlmostEqual(result['scale_x_um_per_px'], .25, delta=.0025)
                self.assertAlmostEqual(result['scale_y_um_per_px'], .20, delta=.002)
                metrics = result['fit_metrics']
                self.assertGreaterEqual(metrics['n_marks_x'], 9)
                self.assertGreaterEqual(metrics['n_marks_y'], 7)
                self.assertLess(metrics['residual_x_px'], 1)
                if options.get('outlier'):
                    self.assertTrue(metrics['rejected_marks_x_px'])
                    self.assertTrue(metrics['rejected_marks_y_px'])

    def test_small_rotation(self):
        # The unequal-pitch fixture rotates as an already sampled image; compare
        # normal pitches (40/50), not a physically anisotropic acquisition.
        result = measure_grid(grid(angle=4), 10, 'uniform_lattice')
        self.assertAlmostEqual(abs(result['rotation_deg']), 4, delta=.3)
        self.assertAlmostEqual(result['fit_metrics']['pitch_x_px'], 40, delta=.4)
        self.assertAlmostEqual(result['fit_metrics']['pitch_y_px'], 50, delta=.5)
        self.assertAlmostEqual(result['scale_x_um_per_px'], .25, delta=.0025)
        self.assertAlmostEqual(result['scale_y_um_per_px'], .20, delta=.002)

    def test_unknown_physical_family_excluded(self):
        with self.assertRaises(MeasurementError) as caught:
            measure_grid(grid(), 10)
        self.assertEqual(caught.exception.status, 'AMBIGUOUS_GRID_PERIODICITY')
        self.assertTrue(caught.exception.metrics['periodicity_candidates_x'])

    def test_multiple_periodicities_tied_remain_ambiguous(self):
        pixels = np.full((512, 512), 210, dtype=np.uint8)
        positions = [45, 85, 125, 165, 215, 265, 315]
        for position in positions:
            pixels[25:487, position-1:position+2] = 20
            pixels[position-1:position+2, 25:487] = 20
        with self.assertRaises(MeasurementError) as caught:
            measure_grid(pixels, 10, 'uniform_lattice')
        self.assertEqual(caught.exception.status, 'AMBIGUOUS_GRID_PERIODICITY')

    def test_no_resize_grid(self):
        with patch('cv2.resize', side_effect=AssertionError('resize forbidden')):
            result = measure_grid(grid(angle=4), 10, 'uniform_lattice')
        self.assertEqual(result['measurement_status'], 'MEASURED')

    def test_deterministic(self):
        self.assertEqual(measure_grid(grid(noise=5), 10, 'uniform_lattice'),
                         measure_grid(grid(noise=5), 10, 'uniform_lattice'))


class CalibrationContractTests(TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root/'reference.png'
        Image.fromarray(disk()).save(self.source, dpi=(72, 72))
        self.entry = dict(pattern_type='circle', known_diameter_um=70, objective_magnification=40,
                          expected_dimensions_px=[512, 512])

    def test_no_resize_original_hash_and_resolution(self):
        before = hashlib.sha256(self.source.read_bytes()).hexdigest()
        with patch('cv2.resize', side_effect=AssertionError('resize forbidden')), patch.object(Image.Image, 'resize', side_effect=AssertionError('resize forbidden')):
            result = measure_image(self.source, self.entry)
        self.assertEqual(result['measurement_status'], 'MEASURED')
        self.assertEqual(result['source_width_px'], 512)
        self.assertEqual(result['source_height_px'], 512)
        self.assertEqual(result['sha256'], before)
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(), before)

    def test_dimension_mismatch_stops_before_measurement(self):
        with patch('api.services.calibration.engine.measure_circle') as measure:
            result = measure_image(self.source, {**self.entry, 'expected_dimensions_px': [4928, 4928]})
        self.assertEqual(result['measurement_status'], 'SOURCE_DIMENSION_MISMATCH')
        measure.assert_not_called()
        with Image.open(self.source) as image:
            self.assertEqual(image.size, (512, 512))

    def test_dpi_never_changes_scale(self):
        other = self.root/'other.png'
        Image.fromarray(disk()).save(other, dpi=(300, 300))
        a, b = measure_image(self.source, self.entry), measure_image(other, self.entry)
        for axis in ('x', 'y'):
            self.assertEqual(a[f'scale_{axis}_um_per_px'], b[f'scale_{axis}_um_per_px'])
        self.assertIn('DPI_IGNORED_FOR_MICROSCOPIC_SCALE', a['warnings'])

    def test_missing_invalid_and_explicit_physical_dimension(self):
        self.assertEqual(measure_image(self.root/'missing', self.entry)['measurement_status'], 'REAL_CALIBRATION_FILES_MISSING')
        invalid = self.root/'invalid.jpg'
        invalid.write_text('not an image')
        self.assertEqual(measure_image(invalid, self.entry)['measurement_status'], 'INVALID_SOURCE_IMAGE')
        for value in (None, 0, -1, float('nan'), True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                measure_image(self.source, {**self.entry, 'known_diameter_um': value})

    def test_consensus_statistics_and_exclusion(self):
        a = measure_image(self.source, self.entry)
        b = {**a, 'source_file': 'other', 'scale_x_um_per_px': .40, 'scale_y_um_per_px': .42}
        excluded = {**a, 'source_file': 'grid', 'measurement_status': 'AMBIGUOUS_GRID_PERIODICITY'}
        result = consensus([a, b, excluded])
        self.assertEqual(result['status'], 'PROVISIONAL_ONLY')
        self.assertEqual(result['n_methods'], 2)
        self.assertEqual(len(result['excluded']), 1)
        x = [a['scale_x_um_per_px'], .40]
        self.assertAlmostEqual(result['statistics']['x']['standard_deviation'], np.std(x, ddof=1))
        self.assertEqual(result['provisional_median_scale_x'], np.median(x))
        self.assertEqual(consensus([excluded])['status'], 'INSUFFICIENT_MEASURED_METHODS')
        self.assertEqual(consensus([a, {**b, 'source_width_px': 1024}])['status'], 'INCOMPATIBLE_ACQUISITION')

    def test_cli_outputs_determinism_and_safety(self):
        manifest = self.root/'manifest.json'
        entry = {**self.entry, 'file': str(self.source)}
        manifest.write_text(json.dumps([entry]))
        output = self.root/'output'
        a = run(manifest, output)
        b = run(manifest, output)
        self.assertEqual(a, b)
        self.assertTrue((output/'results.json').is_file())
        self.assertTrue((output/'report.txt').is_file())
        self.assertTrue((output/'01-diagnostic.png').is_file())
        with self.assertRaises(ValueError):
            run(manifest, self.root)
        manifest.write_text(json.dumps([entry, entry]))
        with self.assertRaises(ValueError):
            run(manifest, output)
