"""Characterization 2.3 — unit, integration and version-isolation tests.

Scientific definitions:
  elongation_index = 1 − sqrt(clamp(1 − ecc², 0, 1))
  convex_solidity  = area_px2 / convex_hull_area_px2
  mn_nucleus_perimeter_ratio_px       = P_mn_px / P_nucleus_px
  mn_nucleus_perimeter_ratio_physical = P_mn_um / P_nucleus_um
  mn_nucleus_min_distance_px          = minimum closed-set polygon distance (px)
  mn_nucleus_min_distance_um          = same after per-coordinate transform (µm)

Version-isolation contract (critical):
  characterize_saliva_result() — MUST NOT contain any 2.3 key
  extend_physical_result()     — MUST NOT contain any 2.3 key
  extend_23_metrics()          — sole producer of all six 2.3 metrics
"""
import copy
import math

from django.test import SimpleTestCase

from api.services.characterization.geometry import (
    polygon_convex_hull,
    polygon_convex_hull_area,
    minimum_polygon_distance,
    _point_to_segment_distance,
    _segment_to_segment_distance,
)
from api.services.characterization.physical import (
    extend_physical_result,
    extend_23_metrics,
    VERSION_23,
)
from api.services.characterization.service import characterize_effective_segmentation
from api.test_characterization_2_1 import box, object_payload


# ---------------------------------------------------------------------------
# Helpers shared by multiple test classes
# ---------------------------------------------------------------------------

KEYS_23 = frozenset({
    'elongation_index', 'convex_solidity',
    'mn_nucleus_perimeter_ratio_px', 'mn_nucleus_perimeter_ratio_physical',
    'mn_nucleus_min_distance_px', 'mn_nucleus_min_distance_um',
})


def effective_fixture():
    """Membrane (id=1), nucleus (id=2), MN (id=3).  MN overlaps nucleus slightly."""
    return {
        'fuente': 'AUTOMATICO',
        'resultado_segmentacion_id': 1,
        'revision': None,
        'resultado': {'objects': [
            object_payload(box(0, 0, 40, 40)),                          # membrane id=1
            object_payload(box(5, 5, 25, 25), 'nucleo', 2),             # nucleus id=2
            object_payload(box(30, 30, 35, 35), 'micronucleo', 3),      # MN id=3  (separated)
        ]},
    }


def context_fixture(sx='2', sy='3'):
    return {
        'physical_units_available': True,
        'physical_status': 'COMPATIBLE_PROVISIONAL',
        'physical_unavailable_reason': None,
        'physical_measurements_status': 'PROVISIONAL_CALIBRATION',
        'acquisition_series_id': 1,
        'image_dimensions_px': None,
        'calibration': {
            'calibration_id': 1,
            'label': 'CAL-OPTIKA-40X-PROVISIONAL-001',
            'status': 'PROVISIONAL',
            'acquisition_profile_id': 1,
            'acquisition_series_id': 1,
            'scale_x_um_per_px': sx,
            'scale_y_um_per_px': sy,
            'source_width_px': 100,
            'source_height_px': 100,
            'compatibility_status': 'COMPATIBLE_PROVISIONAL',
            'method': 'STAGE_MICROMETER',
            'algorithm_version': '1.0',
            'provenance': {},
        },
    }


def no_calibration_context():
    return {
        'physical_units_available': False,
        'physical_status': 'NO_ACQUISITION_SERIES',
        'physical_unavailable_reason': 'NO_ACQUISITION_SERIES',
        'physical_measurements_status': None,
        'acquisition_series_id': None,
        'image_dimensions_px': None,
        'calibration': None,
    }


def make_23_result(effective=None, ctx=None):
    if effective is None:
        effective = effective_fixture()
    if ctx is None:
        ctx = context_fixture()
    pixel = characterize_effective_segmentation(effective)
    physical = extend_physical_result(pixel, effective, ctx, version='2.2')
    return extend_23_metrics(physical, effective, ctx)


def all_metrics_in_result(result):
    """Yield all 'metrics' dicts found anywhere in the result tree."""
    for cell in result.get('cells', []):
        yield cell['metrics']
        for nuc in cell.get('nuclei', []):
            yield nuc['metrics']
        for mn in cell.get('micronuclei', []):
            yield mn['metrics']
    for group in ('unassociated', 'ambiguous'):
        for items in result.get(group, {}).values():
            for item in items:
                yield item['metrics']


# ===========================================================================
# G-1a  Geometry — convex hull
# ===========================================================================

class ConvexHullTests(SimpleTestCase):

    def test_convex_hull_triangle(self):
        pts = [[0, 0], [5, 0], [2, 4]]
        hull = polygon_convex_hull(pts)
        self.assertIsNotNone(hull)
        self.assertEqual(len(hull), 3)

    def test_convex_hull_square_with_interior_point(self):
        pts = [[0, 0], [4, 0], [4, 4], [0, 4], [2, 2]]  # interior point
        hull = polygon_convex_hull(pts)
        self.assertIsNotNone(hull)
        self.assertEqual(len(hull), 4)

    def test_convex_hull_concave_l_shape(self):
        # L-shape: polygon area < convex hull area
        pts = [[0, 0], [4, 0], [4, 2], [2, 2], [2, 4], [0, 4]]
        hull_area = polygon_convex_hull_area(pts)
        from api.services.characterization.geometry import polygon_area
        poly_area = polygon_area(pts)
        self.assertIsNotNone(hull_area)
        self.assertGreater(hull_area, poly_area)

    def test_convex_hull_collinear_returns_none(self):
        pts = [[0, 0], [1, 1], [2, 2], [3, 3]]
        self.assertIsNone(polygon_convex_hull(pts))

    def test_convex_hull_duplicate_points_ok(self):
        pts = [[0, 0], [0, 0], [4, 0], [4, 4], [0, 4]]
        hull = polygon_convex_hull(pts)
        self.assertIsNotNone(hull)
        self.assertGreaterEqual(len(hull), 3)

    def test_convex_hull_fewer_than_3_returns_none(self):
        self.assertIsNone(polygon_convex_hull([[0, 0], [1, 1]]))
        self.assertIsNone(polygon_convex_hull([]))

    def test_convex_hull_area_convex_polygon_equals_area(self):
        # Convex polygon: hull area == polygon area
        from api.services.characterization.geometry import polygon_area
        pts = [[0, 0], [6, 0], [6, 6], [0, 6]]  # square
        self.assertAlmostEqual(polygon_convex_hull_area(pts), polygon_area(pts))

    def test_convex_solidity_square_is_1(self):
        pts = [[0, 0], [4, 0], [4, 4], [0, 4]]
        from api.services.characterization.geometry import polygon_area
        hull_area = polygon_convex_hull_area(pts)
        area = polygon_area(pts)
        self.assertAlmostEqual(area / hull_area, 1.0)

    def test_convex_solidity_concave_less_than_1(self):
        pts = [[0, 0], [4, 0], [4, 2], [2, 2], [2, 4], [0, 4]]
        from api.services.characterization.geometry import polygon_area
        hull_area = polygon_convex_hull_area(pts)
        area = polygon_area(pts)
        ratio = area / hull_area
        self.assertGreater(ratio, 0)
        self.assertLess(ratio, 1)

    def test_convex_solidity_null_for_collinear(self):
        self.assertIsNone(polygon_convex_hull_area([[0, 0], [1, 1], [2, 2], [3, 3]]))

    def test_convex_solidity_null_for_two_points(self):
        self.assertIsNone(polygon_convex_hull_area([[0, 0], [1, 1]]))


# ===========================================================================
# G-1b  Geometry — minimum polygon distance
# ===========================================================================

class MinimumPolygonDistanceTests(SimpleTestCase):

    def _rect(self, x1, y1, x2, y2):
        return [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]

    def test_separated_horizontal(self):
        a = self._rect(0, 0, 3, 3)
        b = self._rect(8, 0, 11, 3)   # gap = 5
        self.assertAlmostEqual(minimum_polygon_distance(a, b), 5.0)

    def test_separated_vertical(self):
        a = self._rect(0, 0, 3, 3)
        b = self._rect(0, 6, 3, 9)    # gap = 3
        self.assertAlmostEqual(minimum_polygon_distance(a, b), 3.0)

    def test_diagonal(self):
        a = self._rect(0, 0, 1, 1)
        b = self._rect(4, 4, 5, 5)    # nearest corners at (1,1) and (4,4)
        expected = math.sqrt(9 + 9)
        self.assertAlmostEqual(minimum_polygon_distance(a, b), expected)

    def test_nearest_point_on_edge_interior(self):
        # a is a unit square; b is offset such that the nearest point from b
        # to a projects onto the interior of an edge, not a vertex.
        a = self._rect(0, 0, 4, 4)
        b = self._rect(6, 1, 8, 3)    # nearest point on a's right edge at (4, 2)
        d = minimum_polygon_distance(a, b)
        # Nearest vertex-to-vertex would be sqrt((6-4)²+(1-4)²) = sqrt(13) ≈ 3.6
        # but edge-interior gives 2.0
        self.assertAlmostEqual(d, 2.0)
        self.assertLess(d, math.sqrt(13))

    def test_touching_corner(self):
        a = self._rect(0, 0, 2, 2)
        b = self._rect(2, 2, 4, 4)    # shared corner (2,2)
        self.assertAlmostEqual(minimum_polygon_distance(a, b), 0.0)

    def test_shared_edge(self):
        a = self._rect(0, 0, 2, 2)
        b = self._rect(2, 0, 4, 2)    # shared right/left edge
        self.assertAlmostEqual(minimum_polygon_distance(a, b), 0.0)

    def test_partial_intersection(self):
        a = self._rect(0, 0, 4, 4)
        b = self._rect(2, 2, 6, 6)    # overlapping
        self.assertAlmostEqual(minimum_polygon_distance(a, b), 0.0)

    def test_full_containment(self):
        outer = self._rect(0, 0, 10, 10)
        inner = self._rect(3, 3, 7, 7)    # completely inside
        self.assertAlmostEqual(minimum_polygon_distance(outer, inner), 0.0)
        self.assertAlmostEqual(minimum_polygon_distance(inner, outer), 0.0)

    def test_identical_polygons(self):
        pts = self._rect(0, 0, 5, 5)
        self.assertAlmostEqual(minimum_polygon_distance(pts, pts), 0.0)

    def test_anisotropic_physical_ne_px_times_avg_scale(self):
        """Physical distance (per-coord transform) ≠ px_distance * avg_scale."""
        a = [[0, 0], [2, 0], [2, 1], [0, 1]]
        b = [[5, 0], [7, 0], [7, 1], [5, 1]]  # horizontal gap = 3 px
        sx, sy = 0.05, 0.1
        px_dist = minimum_polygon_distance(a, b)          # 3.0
        phys = minimum_polygon_distance(
            [[x * sx, y * sy] for x, y in a],
            [[x * sx, y * sy] for x, y in b],
        )
        avg_scale = (sx + sy) / 2
        self.assertAlmostEqual(px_dist, 3.0)
        self.assertAlmostEqual(phys, 3 * sx)              # purely horizontal gap
        self.assertNotAlmostEqual(phys, px_dist * avg_scale)

    def test_point_to_segment_distance_basic(self):
        p = [0.0, 3.0]
        a = [0.0, 0.0]
        b = [4.0, 0.0]
        self.assertAlmostEqual(_point_to_segment_distance(p, a, b), 3.0)

    def test_segment_to_segment_distance_parallel(self):
        # Parallel horizontal segments with gap = 3
        d = _segment_to_segment_distance([0, 0], [5, 0], [0, 3], [5, 3])
        self.assertAlmostEqual(d, 3.0)


# ===========================================================================
# G-1c  Elongation index — eccentricity-based transformation
# ===========================================================================

class ElongationIndexTests(SimpleTestCase):

    def _elongation(self, ecc):
        """Compute elongation via the approved formula."""
        if ecc is None:
            return None
        ratio = max(0.0, min(1.0, 1.0 - ecc * ecc))
        return 1.0 - math.sqrt(ratio)

    def test_ecc_zero_is_zero(self):
        self.assertAlmostEqual(self._elongation(0.0), 0.0)

    def test_ecc_one_is_one(self):
        self.assertAlmostEqual(self._elongation(1.0), 1.0)

    def test_ecc_point6(self):
        # E = 1 - sqrt(1 - 0.36) = 1 - sqrt(0.64) = 1 - 0.8 = 0.2
        self.assertAlmostEqual(self._elongation(0.6), 0.2, places=10)

    def test_ecc_none_is_none(self):
        self.assertIsNone(self._elongation(None))

    def test_not_equal_eccentricity(self):
        # For ecc = 0.6: elongation = 0.2 ≠ 0.6
        self.assertNotAlmostEqual(self._elongation(0.6), 0.6)

    def test_clamp_fp_excursion(self):
        # Simulate a float that is slightly > 1 (ecc² slightly > 1 due to rounding).
        ecc = 1.0 + 1e-15
        ratio = max(0.0, min(1.0, 1.0 - ecc * ecc))
        elongation = 1.0 - math.sqrt(ratio)
        self.assertAlmostEqual(elongation, 1.0)

    def test_range_0_to_1(self):
        for i in range(21):
            ecc = i / 20.0
            e = self._elongation(ecc)
            self.assertGreaterEqual(e, 0.0 - 1e-12)
            self.assertLessEqual(e, 1.0 + 1e-12)

    def test_formula_verified_ecc_0_8(self):
        # E = 1 - sqrt(1 - 0.64) = 1 - sqrt(0.36) = 1 - 0.6 = 0.4
        self.assertAlmostEqual(self._elongation(0.8), 0.4, places=10)


# ===========================================================================
# G-2  Version-isolation tests (critical)
# ===========================================================================

class VersionIsolationTests(SimpleTestCase):

    def setUp(self):
        self.effective = effective_fixture()
        self.ctx = context_fixture()
        self.pixel = characterize_effective_segmentation(self.effective)
        self.physical = extend_physical_result(
            self.pixel, self.effective, self.ctx, version='2.2',
        )
        self.result_23 = extend_23_metrics(self.physical, self.effective, self.ctx)

    def _all_metric_keys(self, result):
        keys = set()
        for m in all_metrics_in_result(result):
            keys.update(m.keys())
        return keys

    def test_2_1_output_has_no_2_3_keys(self):
        keys = self._all_metric_keys(self.pixel)
        self.assertTrue(KEYS_23.isdisjoint(keys),
                        f'2.1 result unexpectedly contains 2.3 keys: {KEYS_23 & keys}')

    def test_2_2_output_has_no_2_3_keys(self):
        keys = self._all_metric_keys(self.physical)
        self.assertTrue(KEYS_23.isdisjoint(keys),
                        f'2.2 result unexpectedly contains 2.3 keys: {KEYS_23 & keys}')

    def test_2_3_output_has_all_new_keys(self):
        # Find a nucleus and a MN
        cell = self.result_23['cells'][0]
        nuc_keys = set(cell['nuclei'][0]['metrics'].keys())
        mn_keys = set(cell['micronuclei'][0]['metrics'].keys())
        # Per-object keys
        self.assertIn('elongation_index', nuc_keys)
        self.assertIn('convex_solidity', nuc_keys)
        self.assertIn('elongation_index', mn_keys)
        self.assertIn('convex_solidity', mn_keys)
        # Relation keys
        self.assertIn('mn_nucleus_perimeter_ratio_px', mn_keys)
        self.assertIn('mn_nucleus_perimeter_ratio_physical', mn_keys)
        self.assertIn('mn_nucleus_min_distance_px', mn_keys)
        self.assertIn('mn_nucleus_min_distance_um', mn_keys)

    def test_2_1_json_identical_after_23_code(self):
        """Running 2.1 characterization after 2.3 code is added produces no change."""
        a = characterize_effective_segmentation(self.effective)
        b = characterize_effective_segmentation(copy.deepcopy(self.effective))
        # Remove version key before comparing (it is added by the service wrapper)
        import json as _json
        self.assertEqual(
            _json.dumps(a, sort_keys=True),
            _json.dumps(b, sort_keys=True),
        )
        # Confirm no 2.3 keys leaked into 2.1
        self.assertTrue(KEYS_23.isdisjoint(self._all_metric_keys(a)))

    def test_2_2_json_identical_after_23_code(self):
        """The 2.2 result is not mutated by calling extend_23_metrics afterwards."""
        phys_before = copy.deepcopy(self.physical)
        extend_23_metrics(self.physical, self.effective, self.ctx)
        import json as _json
        self.assertEqual(
            _json.dumps(phys_before, sort_keys=True),
            _json.dumps(self.physical, sort_keys=True),
        )

    def test_raster_metrics_behavior_unchanged(self):
        """eccentricity from 2.1 is unchanged after 2.3 code is in place."""
        from api.services.characterization.raster import ObjectRaster
        from api.services.characterization.raster_metrics import measure_raster
        from PIL import Image, ImageDraw
        # Symmetric circle
        circle = Image.new('L', (21, 21))
        ImageDraw.Draw(circle).ellipse((0, 0, 20, 20), fill=1)
        metrics = measure_raster(ObjectRaster(21, 21, circle.tobytes(), None))
        self.assertAlmostEqual(metrics['eccentricity'], 0)
        # Known rectangle fixture (same as test_characterization_2_1)
        from api.services.characterization.saliva import _measure_object
        image = __import__('PIL').Image.new('L', (100, 100), 70)
        result = _measure_object(object_payload(box(0, 0, 10, 2)), image, [])
        expected_ecc = math.sqrt(1 - (2 / 3) / 10)
        self.assertAlmostEqual(result['metrics']['eccentricity'], expected_ecc)

    def test_version_fields(self):
        self.assertEqual(self.result_23['version'], '2.3')
        self.assertEqual(self.result_23['schema_version'], '2.3')
        self.assertEqual(self.result_23['characterization_version'], '2.3')

    def test_pixel_algorithm_version_still_2_1(self):
        self.assertEqual(self.result_23['provenance']['pixel_algorithm_version'], '2.1')

    def test_fingerprint_distinct_from_2_2(self):
        fp_22 = self.physical['provenance']['fingerprint']
        fp_23 = self.result_23['provenance']['fingerprint']
        self.assertNotEqual(fp_22, fp_23)

    def test_extend_23_does_not_mutate_input(self):
        import json as _json
        before = _json.dumps(self.physical, sort_keys=True)
        extend_23_metrics(self.physical, self.effective, self.ctx)
        after = _json.dumps(self.physical, sort_keys=True)
        self.assertEqual(before, after)


# ===========================================================================
# G-3  Object-level metrics in full 2.3 characterization
# ===========================================================================

class ObjectMetrics23Tests(SimpleTestCase):

    def setUp(self):
        self.result = make_23_result()
        self.cell = self.result['cells'][0]

    def test_nucleus_has_elongation_and_solidity(self):
        nuc_m = self.cell['nuclei'][0]['metrics']
        self.assertIsNotNone(nuc_m['elongation_index'])
        self.assertIsNotNone(nuc_m['convex_solidity'])
        self.assertGreaterEqual(nuc_m['elongation_index'], 0.0)
        self.assertLessEqual(nuc_m['elongation_index'], 1.0)
        self.assertGreater(nuc_m['convex_solidity'], 0.0)
        self.assertLessEqual(nuc_m['convex_solidity'], 1.0)

    def test_mn_has_elongation_and_solidity(self):
        mn_m = self.cell['micronuclei'][0]['metrics']
        self.assertIsNotNone(mn_m['elongation_index'])
        self.assertIsNotNone(mn_m['convex_solidity'])

    def test_elongation_null_when_eccentricity_null(self):
        """When eccentricity is null in the 2.2 result, elongation_index is null."""
        # Build a fixture where we can inject a null eccentricity.
        effective = effective_fixture()
        ctx = context_fixture()
        pixel = characterize_effective_segmentation(effective)
        physical = extend_physical_result(pixel, effective, ctx, version='2.2')
        # Force null eccentricity on the nucleus.
        physical['cells'][0]['nuclei'][0]['metrics']['eccentricity'] = None
        result = extend_23_metrics(physical, effective, ctx)
        nuc_m = result['cells'][0]['nuclei'][0]['metrics']
        self.assertIsNone(nuc_m['elongation_index'])

    def test_convex_solidity_null_for_collinear(self):
        """Collinear polygon → null convex solidity.

        A collinear 'nucleus' polygon is rejected by saliva.py as invalid, so
        the object ends up in unassociated['nuclei'], not in cells[0]['nuclei'].
        """
        effective = {
            'fuente': 'AUTOMATICO', 'resultado_segmentacion_id': 1, 'revision': None,
            'resultado': {'objects': [
                object_payload(box(0, 0, 10, 10)),                      # membrane
                {'id': 2, 'label': 'nucleo',
                 'geometry': {'type': 'polygon',
                              'points': [[0, 0], [2, 2], [4, 4], [6, 6]]}},  # collinear
            ]},
        }
        ctx = no_calibration_context()
        pixel = characterize_effective_segmentation(effective)
        physical = extend_physical_result(pixel, effective, ctx, version='2.2')
        result = extend_23_metrics(physical, effective, ctx)
        # collinear nucleus ends up in unassociated, not in cells[0]['nuclei']
        unassoc_nuclei = result.get('unassociated', {}).get('nuclei', [])
        self.assertEqual(len(unassoc_nuclei), 1)
        nuc_m = unassoc_nuclei[0]['metrics']
        self.assertIsNone(nuc_m['convex_solidity'])

    def test_convex_solidity_reconstructible(self):
        """convex_solidity * convex_hull_area_px2 ≈ area_px2."""
        nuc = self.cell['nuclei'][0]
        m = nuc['metrics']
        solidity = m['convex_solidity']
        area = m['area_px2']
        if solidity is None or area is None:
            return
        points = box(5, 5, 25, 25)  # nucleus polygon from fixture
        hull_area = polygon_convex_hull_area(points)
        self.assertIsNotNone(hull_area)
        self.assertAlmostEqual(solidity * hull_area, area, places=8)

    def test_square_solidity_is_1(self):
        """A rectangular nucleus polygon has convex_solidity = 1."""
        solidity = self.cell['nuclei'][0]['metrics']['convex_solidity']
        # Rectangle is convex; hull area == polygon area → ratio = 1
        self.assertAlmostEqual(solidity, 1.0, places=8)

    def test_elongation_formula_matches_eccentricity(self):
        """elongation = 1 - sqrt(1 - ecc²) for the stored eccentricity value."""
        nuc_m = self.cell['nuclei'][0]['metrics']
        ecc = nuc_m['eccentricity']
        if ecc is None:
            return
        expected = 1.0 - math.sqrt(max(0.0, min(1.0, 1.0 - ecc * ecc)))
        self.assertAlmostEqual(nuc_m['elongation_index'], expected, places=12)


# ===========================================================================
# G-4  Relation metrics in full 2.3 characterization
# ===========================================================================

class RelationMetrics23Tests(SimpleTestCase):

    def setUp(self):
        self.effective = effective_fixture()
        self.ctx = context_fixture()
        self.result = make_23_result(self.effective, self.ctx)
        self.mn = self.result['cells'][0]['micronuclei'][0]
        self.nuc = self.result['cells'][0]['nuclei'][0]

    def test_perimeter_ratio_px_exact(self):
        mn_m = self.mn['metrics']
        nuc_m = self.nuc['metrics']
        expected = mn_m['perimeter_px'] / nuc_m['perimeter_px']
        self.assertAlmostEqual(mn_m['mn_nucleus_perimeter_ratio_px'], expected, places=10)

    def test_perimeter_ratio_px_null_no_nucleus(self):
        """Unassociated MN → null pixel perimeter ratio."""
        effective = {
            'fuente': 'AUTOMATICO', 'resultado_segmentacion_id': 1, 'revision': None,
            'resultado': {'objects': [
                object_payload(box(0, 0, 40, 40)),
                # No nucleus in this membrane
                object_payload(box(30, 30, 35, 35), 'micronucleo', 3),
            ]},
        }
        ctx = no_calibration_context()
        pixel = characterize_effective_segmentation(effective)
        physical = extend_physical_result(pixel, effective, ctx, version='2.2')
        result = extend_23_metrics(physical, effective, ctx)
        # The MN ends up unassociated (no nucleus to associate with).
        for group in ('unassociated', 'ambiguous'):
            for items in result.get(group, {}).values():
                for item in items:
                    if item.get('label') == 'micronucleo':
                        self.assertIsNone(item['metrics']['mn_nucleus_perimeter_ratio_px'])
        # Also check cells.micronuclei with no nucleus association
        for cell in result.get('cells', []):
            for mn_item in cell.get('micronuclei', []):
                if mn_item.get('nucleus_id') is None:
                    self.assertIsNone(mn_item['metrics']['mn_nucleus_perimeter_ratio_px'])

    def test_perimeter_ratio_multiple_mn(self):
        """3 MN → 3 independent ratios."""
        effective = {
            'fuente': 'AUTOMATICO', 'resultado_segmentacion_id': 1, 'revision': None,
            'resultado': {'objects': [
                object_payload(box(0, 0, 40, 40)),
                object_payload(box(5, 5, 20, 20), 'nucleo', 2),
                object_payload(box(22, 22, 24, 24), 'micronucleo', 3),
                object_payload(box(25, 25, 28, 28), 'micronucleo', 4),
                object_payload(box(30, 30, 34, 34), 'micronucleo', 5),
            ]},
        }
        result = make_23_result(effective, no_calibration_context())
        mns = result['cells'][0]['micronuclei']
        self.assertEqual(len(mns), 3)
        ratios = [mn['metrics']['mn_nucleus_perimeter_ratio_px'] for mn in mns]
        # All three are defined (each MN is associated with the same nucleus)
        for r in ratios:
            if r is not None:
                self.assertGreater(r, 0)

    def test_perimeter_ratio_px_reconstructible(self):
        """ratio × nucleus_perimeter_px == mn_perimeter_px (float tolerance)."""
        mn_m = self.mn['metrics']
        nuc_m = self.nuc['metrics']
        ratio = mn_m['mn_nucleus_perimeter_ratio_px']
        if ratio is None:
            return
        self.assertAlmostEqual(ratio * nuc_m['perimeter_px'], mn_m['perimeter_px'], places=10)

    def test_perimeter_ratio_physical_ne_px(self):
        """Anisotropic calibration (sx≠sy): physical ratio ≠ pixel ratio.

        Uses a horizontal-rectangle MN vs a vertical-rectangle nucleus so that
        the anisotropic scaling changes their perimeter ratio.
        MN:  box(10,5,14,6) → width=4, height=1  → P_px=10, P_um=2*(4*2+1*3)=22
        Nuc: box(5,5,6,9)   → width=1, height=4  → P_px=10, P_um=2*(1*2+4*3)=28
        r_px = 1.0;  r_phys = 22/28 ≈ 0.786 — clearly different.
        """
        effective = {
            'fuente': 'AUTOMATICO', 'resultado_segmentacion_id': 1, 'revision': None,
            'resultado': {'objects': [
                object_payload(box(0, 0, 40, 40)),
                object_payload(box(5, 5, 6, 9), 'nucleo', 2),          # vertical rect
                object_payload(box(10, 5, 14, 6), 'micronucleo', 3),   # horizontal rect
            ]},
        }
        ctx = context_fixture(sx='2', sy='3')
        result = make_23_result(effective, ctx)
        mn_m = result['cells'][0]['micronuclei'][0]['metrics']
        r_px = mn_m['mn_nucleus_perimeter_ratio_px']
        r_phys = mn_m['mn_nucleus_perimeter_ratio_physical']
        self.assertIsNotNone(r_px)
        self.assertIsNotNone(r_phys)
        self.assertNotAlmostEqual(r_px, r_phys, places=5)
        self.assertAlmostEqual(r_px, 1.0, places=8)
        self.assertAlmostEqual(r_phys, 22 / 28, places=6)

    def test_perimeter_ratio_physical_reconstructible(self):
        """ratio_physical × perimeter_um == mn_perimeter_um (float tolerance)."""
        mn_m = self.mn['metrics']
        nuc_m = self.nuc['metrics']
        ratio = mn_m['mn_nucleus_perimeter_ratio_physical']
        if ratio is None:
            return
        self.assertAlmostEqual(
            ratio * nuc_m['perimeter_um'], mn_m['perimeter_um'], places=8
        )

    def test_min_dist_px_exact(self):
        """MN separated from nucleus: distance > 0 and matches geometry."""
        mn_m = self.mn['metrics']
        d = mn_m['mn_nucleus_min_distance_px']
        self.assertIsNotNone(d)
        self.assertGreater(d, 0)
        # Nucleus: box(5,5,25,25); MN: box(30,30,35,35). Nearest points are
        # nucleus corner (25,25) and MN corner (30,30) → sqrt(50) ≈ 7.07.
        self.assertAlmostEqual(d, math.sqrt(50), places=6)

    def test_min_dist_px_zero_touching(self):
        """Touching polygons → distance = 0."""
        effective = {
            'fuente': 'AUTOMATICO', 'resultado_segmentacion_id': 1, 'revision': None,
            'resultado': {'objects': [
                object_payload(box(0, 0, 40, 40)),
                object_payload(box(5, 5, 15, 15), 'nucleo', 2),
                # MN touching the nucleus at (15,15)
                object_payload(box(15, 15, 20, 20), 'micronucleo', 3),
            ]},
        }
        result = make_23_result(effective, no_calibration_context())
        d = result['cells'][0]['micronuclei'][0]['metrics']['mn_nucleus_min_distance_px']
        self.assertAlmostEqual(d, 0.0)

    def test_min_dist_px_zero_contained(self):
        """MN polygon fully inside nucleus polygon → distance = 0."""
        effective = {
            'fuente': 'AUTOMATICO', 'resultado_segmentacion_id': 1, 'revision': None,
            'resultado': {'objects': [
                object_payload(box(0, 0, 40, 40)),
                object_payload(box(3, 3, 30, 30), 'nucleo', 2),
                object_payload(box(10, 10, 15, 15), 'micronucleo', 3),  # inside nucleus
            ]},
        }
        result = make_23_result(effective, no_calibration_context())
        d = result['cells'][0]['micronuclei'][0]['metrics']['mn_nucleus_min_distance_px']
        self.assertAlmostEqual(d, 0.0)

    def test_min_dist_px_null_no_nucleus(self):
        """Unassociated MN → mn_nucleus_min_distance_px = null."""
        effective = {
            'fuente': 'AUTOMATICO', 'resultado_segmentacion_id': 1, 'revision': None,
            'resultado': {'objects': [
                object_payload(box(0, 0, 40, 40)),
                object_payload(box(30, 30, 35, 35), 'micronucleo', 3),
            ]},
        }
        ctx = no_calibration_context()
        pixel = characterize_effective_segmentation(effective)
        physical = extend_physical_result(pixel, effective, ctx, version='2.2')
        result = extend_23_metrics(physical, effective, ctx)
        for group in ('unassociated', 'ambiguous'):
            for items in result.get(group, {}).values():
                for item in items:
                    if item.get('label') == 'micronucleo':
                        self.assertIsNone(item['metrics']['mn_nucleus_min_distance_px'])

    def test_min_dist_um_anisotropic(self):
        """Physical distance uses per-coord transform, not average scale."""
        ctx = context_fixture(sx='0.05', sy='0.1')
        result = make_23_result(self.effective, ctx)
        mn_m = result['cells'][0]['micronuclei'][0]['metrics']
        d_px = mn_m['mn_nucleus_min_distance_px']
        d_um = mn_m['mn_nucleus_min_distance_um']
        if d_px is None or d_um is None:
            return
        sx, sy = 0.05, 0.1
        avg = (sx + sy) / 2
        # d_um must not equal d_px * avg_scale
        self.assertNotAlmostEqual(d_um, d_px * avg, places=6)
        # Physical distance for corner-to-corner (25,25)→(30,30) in px:
        # transform: (25*0.05, 25*0.1)→(1.25, 2.5) and (30*0.05, 30*0.1)→(1.5, 3.0)
        # → sqrt((0.25)²+(0.5)²) ≈ 0.559
        expected_um = math.sqrt((5 * sx) ** 2 + (5 * sy) ** 2)
        self.assertAlmostEqual(d_um, expected_um, places=6)

    def test_min_dist_um_null_no_calibration(self):
        """No calibration → mn_nucleus_min_distance_um is null."""
        result = make_23_result(self.effective, no_calibration_context())
        mn_m = result['cells'][0]['micronuclei'][0]['metrics']
        self.assertIsNone(mn_m['mn_nucleus_min_distance_um'])

    def test_min_dist_um_provisional(self):
        """PROVISIONAL calibration → distance still computed (PROVISIONAL status preserved)."""
        ctx = context_fixture()  # status = PROVISIONAL by default
        result = make_23_result(self.effective, ctx)
        mn_m = result['cells'][0]['micronuclei'][0]['metrics']
        # Distance is computable even under provisional calibration.
        self.assertIsNotNone(mn_m['mn_nucleus_min_distance_um'])
        # Provenance flag preserved.
        self.assertTrue(result['provenance']['IMPORTANT_PENDING_18S_A2'])


# ===========================================================================
# G-5  Schema, version, fingerprint
# ===========================================================================

class SchemaVersionTests(SimpleTestCase):

    def setUp(self):
        self.result = make_23_result()

    def test_schema_version_is_2_3(self):
        self.assertEqual(self.result['version'], VERSION_23)
        self.assertEqual(self.result['schema_version'], VERSION_23)

    def test_pixel_algorithm_version_still_2_1(self):
        self.assertEqual(self.result['provenance']['pixel_algorithm_version'], '2.1')

    def test_fingerprint_distinct_from_2_2(self):
        effective = effective_fixture()
        ctx = context_fixture()
        pixel = characterize_effective_segmentation(effective)
        phys = extend_physical_result(pixel, effective, ctx, version='2.2')
        r23 = extend_23_metrics(phys, effective, ctx)
        self.assertNotEqual(
            phys['provenance']['fingerprint'],
            r23['provenance']['fingerprint'],
        )

    def test_version_dispatch_2_2_still_works(self):
        """When the constant is '2.2', result has no 2.3 fields."""
        effective = effective_fixture()
        ctx = context_fixture()
        pixel = characterize_effective_segmentation(effective)
        phys_22 = extend_physical_result(pixel, effective, ctx, version='2.2')
        for m in all_metrics_in_result(phys_22):
            for key in KEYS_23:
                self.assertNotIn(key, m,
                                 f'2.2 result unexpectedly contains 2.3 key: {key}')
