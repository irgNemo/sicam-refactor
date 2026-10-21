"""Hierarchy and sensitivity experiments without database or clinical images."""
from unittest import TestCase
import numpy as np
from api.test_calibration import disk
from api.services.calibration.review import (hierarchy_axis, grid_projections,
    circle_sensitivity, diameter_perturbation, CIRCLE_PERTURBATIONS, statistics)


class GridHierarchyTests(TestCase):
    def setUp(self):
        self.p = 50+np.arange(21)*20.
        self.heights = np.where(np.arange(21)%5 == 0, 500., 150.)

    def test_five_to_one_observed_groups_and_autoconsistency(self):
        result = hierarchy_axis(self.p, self.heights, 20., 100.)
        self.assertEqual(result['geometry_status'], 'OBSERVED_FIVE_DIVISION_HIERARCHY')
        self.assertEqual(result['complete_observed_groups'], 4)
        self.assertEqual(result['n_minor'], 16)
        self.assertEqual(result['n_major'], 5)
        self.assertEqual(result['major_every_n_minor'], 5)
        self.assertEqual(result['scale_minor_um_per_px'], .5)
        self.assertEqual(result['scale_major_um_per_px'], .5)
        self.assertEqual(result['self_consistency_symmetric_percent'], 0)

    def test_hierarchy_on_generated_image_both_axes(self):
        pixels = np.full((600,600),210,np.uint8)
        for i in range(26):
            position = 50+i*20
            lo,hi = (30,570) if i%5 == 0 else (250,350)
            pixels[lo:hi,position-1:position+2] = 20
        for axis, image in (('x', pixels), ('y', pixels.T.copy())):
            data = grid_projections(image,0)['axes'][axis]
            r = hierarchy_axis(data['positions_px'],data['heights_px'],20.,100.)
            self.assertEqual(r['geometry_status'],'OBSERVED_FIVE_DIVISION_HIERARCHY')
            self.assertEqual(r['complete_observed_groups'],5)

    def test_ratio_five_without_phase_alignment_is_ambiguous(self):
        p = self.p.copy()
        p[np.arange(21)%5 == 0] += 7
        result = hierarchy_axis(p, self.heights,20.,100.)
        self.assertEqual(result['ratio'],5)
        self.assertEqual(result['geometry_status'],'AMBIGUOUS_GRID_PERIODICITY')
        self.assertIsNone(result['scale_minor_um_per_px'])

    def test_nonhierarchical_periodicities_ambiguous(self):
        r = hierarchy_axis(self.p,self.heights,20.,90.)
        self.assertEqual(r['geometry_status'],'AMBIGUOUS_GRID_PERIODICITY')

    def test_sparse_extrapolation_does_not_invent_observed_subdivisions(self):
        # Short marks outside a central lattice; no complete observed bracket.
        p = np.array([-60,-40,-20,0,100,200,300,400,420,440,460.])
        h = np.array([150,150,150,500,500,500,500,500,150,150,150.])
        r = hierarchy_axis(p,h,20.,100.)
        self.assertTrue(r['geometric_agreement'])
        self.assertEqual(r['complete_observed_groups'],0)
        self.assertIsNone(r['scale_minor_um_per_px'])
        self.assertEqual(r['geometry_status'],'AMBIGUOUS_GRID_PERIODICITY')
        self.assertTrue(r['spatial_variation']['inferred_intervals'])

    def test_missing_length_evidence_remains_ambiguous(self):
        r = hierarchy_axis(self.p,np.ones(21)*100,20.,100.)
        self.assertEqual(r['geometry_status'],'AMBIGUOUS_GRID_PERIODICITY')

    def test_small_jitter_spatial_residuals_and_repeatability(self):
        p=self.p+np.random.default_rng(18).normal(0,.1,len(self.p))
        a=hierarchy_axis(p,self.heights,20.,100.)
        self.assertEqual(a,hierarchy_axis(p,self.heights,20.,100.))
        self.assertEqual(a['geometry_status'],'OBSERVED_FIVE_DIVISION_HIERARCHY')
        self.assertLess(a['max_abs_lattice_residual_px'],.5)
        self.assertEqual(len(a['spatial_variation']['nonoverlapping_subsets']),3)


class CircleSensitivityTests(TestCase):
    def test_identical_strategy_both_sizes_and_determinism(self):
        strategies=[]
        for size, radius in ((70,65),(150,140)):
            pixels=disk(radii=(radius,radius),noise=2,blur=1)
            a=circle_sensitivity(pixels,size)
            self.assertEqual(a,circle_sensitivity(pixels,size))
            self.assertFalse(a['failed_experiments'])
            strategies.append([(r['experiment'],r['parameters']) for r in a['experiments']])
            self.assertLess(a['summaries']['scale_x_um_per_px']['relative_range_percent'],2)
            self.assertLess(a['summaries']['scale_y_um_per_px']['relative_range_percent'],2)
        self.assertEqual(strategies[0],strategies[1])
        self.assertEqual(len(strategies[0]),len(CIRCLE_PERTURBATIONS))

    def test_total_diameter_changes_are_not_radial_offsets(self):
        rows=diameter_perturbation(100,10)
        self.assertEqual(rows[0]['diameter_delta_px'],-3)
        self.assertEqual(rows[0]['scale_um_per_px'],10/97)
        self.assertEqual(rows[-1]['scale_um_per_px'],10/103)
        self.assertGreater(abs(rows[-1]['scale_change_percent']),
                           abs(diameter_perturbation(200,20)[-1]['scale_change_percent']))

    def test_sample_statistics_and_zero_singleton(self):
        r=statistics([1,2,3])
        self.assertEqual(r['sample_sd'],1)
        self.assertEqual(r['mad'],1)
        self.assertEqual(r['relative_range_percent'],100)
        self.assertIsNone(statistics([0])['cv_percent'])
        self.assertIsNone(statistics([]))
