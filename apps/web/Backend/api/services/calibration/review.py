"""18S-A.1 experiments, not a scientific acceptance policy or a new calibration.

Hierarchy evidence uses only grid geometry. Circle perturbations are fixed for
both diameters. Default 18S-A measurements and consensus rules remain unchanged.
"""
import cv2
import numpy as np
from .common import MeasurementError, normalized_gray, dark_mask
from .circle import measure_circle
from .grid import projection_centers, periodicities, fit_lattice
from .engine import percent_difference

# One factor at a time; identical settings for all disk sizes. Never tuned per file.
CIRCLE_PERTURBATIONS = (
    ('baseline', {}),
    ('smoothing_0.7px', {'smoothing_sigma': .7}),
    ('smoothing_1.5px', {'smoothing_sigma': 1.5}),
    ('smoothing_2px', {'smoothing_sigma': 2.0}),
    ('radial_720', {'radial_points': 720}),
    ('radial_2880', {'radial_points': 2880}),
    ('rejection_3MAD', {'rejection_mad': 3.0}),
    ('rejection_6MAD', {'rejection_mad': 6.0}),
)


def statistics(values):
    values = np.asarray(values, dtype=np.float64)
    if not len(values):
        return None
    mean, median = float(values.mean()), float(np.median(values))
    sd = float(values.std(ddof=1)) if len(values) > 1 else None
    return dict(n=len(values), mean=mean, median=median, sample_sd=sd,
                cv_percent=100*sd/mean if sd is not None and mean else None,
                mad=float(np.median(abs(values-median))), min=float(values.min()),
                max=float(values.max()), relative_range_percent=100*float(np.ptp(values))/mean if mean else None)


def circle_sensitivity(gray, physical_diameter):
    rows = []
    for name, options in CIRCLE_PERTURBATIONS:
        row = {'experiment': name, 'parameters': options.copy()}
        try:
            r = measure_circle(gray, physical_diameter, **options)
            row.update(status=r['measurement_status'])
            for key in ('diameter_x_px', 'diameter_y_px', 'fit_residual_px', 'inlier_fraction'):
                row[key] = r['fit_metrics'][key]
            for key in ('scale_x_um_per_px', 'scale_y_um_per_px', 'anisotropy_percent'):
                row[key] = r[key]
        except MeasurementError as error:
            row['status'] = error.status
        rows.append(row)
    good = [r for r in rows if r['status'] == 'MEASURED']
    keys = ('diameter_x_px', 'diameter_y_px', 'scale_x_um_per_px', 'scale_y_um_per_px', 'anisotropy_percent')
    return dict(label='ALGORITHMIC_SENSITIVITY_NOT_MEASUREMENT_UNCERTAINTY', experiments=rows,
                summaries={k: statistics([r[k] for r in good]) for k in keys},
                failed_experiments=[r['experiment'] for r in rows if r['status'] != 'MEASURED'])


def diameter_perturbation(diameter_px, physical_diameter):
    """Delta is total diameter, not a radial shift of both edges."""
    if diameter_px <= 3 or physical_diameter <= 0:
        raise ValueError('Positive physical diameter and diameter_px > 3 required')
    scale = physical_diameter/diameter_px
    return [dict(diameter_delta_px=delta, diameter_px=diameter_px+delta,
                 scale_um_per_px=physical_diameter/(diameter_px+delta),
                 scale_delta_um_per_px=physical_diameter/(diameter_px+delta)-scale,
                 scale_change_percent=100*(diameter_px/(diameter_px+delta)-1))
            for delta in (-3., -2., -1., -.5, .5, 1., 2., 3.)]


def grid_projections(gray, angle):
    normalized, _ = normalized_gray(gray)
    mask, _ = dark_mask(normalized)
    h, w = gray.shape
    matrix = cv2.getRotationMatrix2D(((w-1)/2, (h-1)/2), angle, 1.)
    c, s = abs(matrix[0, 0]), abs(matrix[0, 1])
    nw, nh = int(np.ceil(w*c+h*s)), int(np.ceil(h*c+w*s))
    matrix[:, 2] += [(nw-w)/2, (nh-h)/2]
    aligned = cv2.warpAffine(mask, matrix, (nw, nh), flags=cv2.INTER_NEAREST, borderValue=0)
    output = {'angle_deg': angle, 'original_to_aligned': matrix.tolist(), 'axes': {}}
    for axis, dimension in (('x', 0), ('y', 1)):
        positions, heights = projection_centers(np.sum(aligned > 0, axis=dimension))
        output['axes'][axis] = {'positions_px': positions.tolist(), 'heights_px': heights.tolist(),
                                'candidates': periodicities(positions, heights)}
    return output


def spatial_variation(positions, indices):
    """Missing marks are explicit: gap/5 is an inferred unit pitch, not 5 observations."""
    positions, indices = np.asarray(positions), np.asarray(indices)
    di, dp = np.diff(indices), np.diff(positions)
    valid = di > 0
    mid = (positions[1:]+positions[:-1])[valid]/2
    unit = dp[valid]/di[valid]
    intervals = [dict(midpoint_px=float(m), pitch_per_minor_index_px=float(u),
                      index_span=int(span), observed_single_interval=bool(span == 1))
                 for m, u, span in zip(mid, unit, di[valid])]
    subsets = []
    for name, subset in zip(('first', 'middle', 'last'), np.array_split(np.arange(len(positions)), 3)):
        row = {'subset': name, 'n_marks': len(subset)}
        if len(subset) >= 3 and np.ptp(indices[subset]) > 0:
            slope, intercept = np.polyfit(indices[subset], positions[subset], 1)
            row.update(pitch_px=float(slope), residual_px=float(np.sqrt(np.mean((positions[subset]-intercept-slope*indices[subset])**2))))
        else:
            row.update(status='INSUFFICIENT_INDEPENDENT_MARKS')
        subsets.append(row)
    trend = None
    if len(mid) >= 3:
        slope, intercept = np.polyfit(mid, unit, 1)
        trend = dict(slope_px_per_px=float(slope), intercept_px=float(intercept),
                     fitted_change_across_observed_span_percent=float(100*slope*np.ptp(mid)/unit.mean()),
                     r_squared=float(1-np.sum((unit-intercept-slope*mid)**2)/np.sum((unit-unit.mean())**2)) if np.ptp(unit) else None)
    return dict(intervals=intervals, all_intervals=statistics(unit),
                directly_observed_minor_intervals=statistics(unit[di[valid] == 1]),
                inferred_intervals=statistics(unit[di[valid] > 1]), nonoverlapping_subsets=subsets,
                linear_trend=trend, optical_distortion_status='NOT_ESTABLISHED_SINGLE_IMAGE',
                caveat='Position dependence can include clipping, mark geometry and extraction; no optical correction.')


def hierarchy_axis(positions, heights, small_pitch, large_pitch, division_um=10.):
    """Test independent short/long families, phase, indices and OBSERVED groups.

    12% pitch is a geometric matching tolerance inherited from fit_lattice, not
    a scientific scale acceptance bound. No circle measurement is an input.
    A complete bracket requires two long marks and all FOUR interior short marks.
    Sparse lattice extrapolation alone never upgrades physical identification.
    """
    p, heights = np.asarray(positions, dtype=np.float64), np.asarray(heights, dtype=np.float64)
    ratio = large_pitch/small_pitch
    out = dict(ratio=ratio, absolute_deviation_from_5=abs(ratio-5),
               percent_deviation_from_5=100*abs(ratio-5)/5,
               pitch_minor_baseline_px=small_pitch, pitch_major_baseline_px=large_pitch,
               geometry_status='AMBIGUOUS_GRID_PERIODICITY', scale_minor_um_per_px=None,
               scale_major_um_per_px=None)
    sorted_heights = np.sort(heights)
    gaps = sorted_heights[1:]/np.maximum(sorted_heights[:-1], 1)
    if len(p) < 6 or not len(gaps) or gaps.max() <= 1.6:
        return {**out, 'reason': 'NO_DISTINCT_SHORT_LONG_MARK_FAMILIES'}
    split = int(np.argmax(gaps))
    threshold = float(np.sqrt(sorted_heights[split]*sorted_heights[split+1]))
    is_major = heights >= threshold
    short_fit = fit_lattice(p[~is_major], small_pitch)
    long_fit = fit_lattice(p[is_major], large_pitch)
    if short_fit is None or long_fit is None:
        return {**out, 'reason': 'INSUFFICIENT_INDEPENDENT_FAMILY_MARKS'}
    # Anchor phase at the first long mark, then number from the first observed
    # mark. Gaps retain missing indices; inferred points never enter fitting.
    origin = float(p[is_major][0])
    indices = np.rint((p-origin)/small_pitch).astype(int)
    phase_residual = p-(origin+indices*small_pitch)
    indices -= indices.min()
    short_phase = ((origin-short_fit['intercept_px']+short_fit['pitch_px']/2) % short_fit['pitch_px'])-short_fit['pitch_px']/2
    major_indices = indices[is_major]
    major_every = np.diff(major_indices)
    tolerance = .12*small_pitch
    match = (abs(phase_residual) <= tolerance)
    unique = len(np.unique(indices)) == len(indices)
    geometric_agreement = bool(unique and match.all() and (major_every == 5).all()
                               and abs(short_phase) <= tolerance and abs(ratio-5) <= .12)
    groups = []
    long_positions = np.flatnonzero(is_major)
    for left, right in zip(long_positions[:-1], long_positions[1:]):
        internal = np.arange(left+1, right)
        expected = np.arange(indices[left]+1, indices[left]+5)
        observed = indices[internal]
        complete = bool(indices[right]-indices[left] == 5 and np.array_equal(observed, expected)
                        and not is_major[internal].any() and match[left:right+1].all())
        groups.append(dict(left_px=float(p[left]), right_px=float(p[right]),
                           left_index=int(indices[left]), right_index=int(indices[right]),
                           observed_interior_indices=observed.tolist(),
                           missing_interior_indices=sorted(set(expected.tolist())-set(observed.tolist())),
                           fully_observed_five_intervals=complete))
    observed_count = sum(g['fully_observed_five_intervals'] for g in groups)
    out.update(n_minor=int((~is_major).sum()), n_major=int(is_major.sum()),
               major_every_n_minor=5 if geometric_agreement else None,
               short_long_height_threshold_px=threshold, independent_minor_fit=short_fit,
               independent_major_fit=long_fit, minor_phase_at_first_major_px=float(short_phase),
               major_minor_phase_rms_px=float(np.sqrt(np.mean(phase_residual[is_major]**2))),
               max_abs_lattice_residual_px=float(abs(phase_residual).max()),
               rejected_positions_px=p[~match].tolist(), complete_observed_groups=observed_count,
               geometric_agreement=geometric_agreement, groups=groups,
               marks=[dict(position_px=float(pos), index=int(index), kind='major' if major else 'minor',
                           height_px=float(height), residual_px=float(res), accepted=bool(keep))
                      for pos,index,major,height,res,keep in zip(p,indices,is_major,heights,phase_residual,match)],
               spatial_variation=spatial_variation(p, indices))
    if geometric_agreement and observed_count:
        a, b = division_um/small_pitch, 5*division_um/large_pitch
        out.update(geometry_status='OBSERVED_FIVE_DIVISION_HIERARCHY',
                   scale_minor_um_per_px=a, scale_major_um_per_px=b,
                   self_consistency_absolute_um_per_px=abs(a-b),
                   self_consistency_symmetric_percent=percent_difference(a,b),
                   interpretation='Declared division applied to the observed five-subdivision hierarchy; provisional.')
    else:
        out['reason'] = 'NO_COMPLETE_OBSERVED_FIVE_INTERVAL_GROUP' if geometric_agreement else 'INCONSISTENT_SPATIAL_HIERARCHY'
    return out


def review_grid(gray, baseline):
    angle = baseline['fit_metrics']['estimated_rotation_deg']
    corrected, uncorrected = grid_projections(gray, angle), grid_projections(gray, 0.)
    axes = {}
    for axis in ('x', 'y'):
        candidates = sorted(baseline['fit_metrics']['periodicity_candidates_'+axis], key=lambda c:c['pitch_px'])
        if len(candidates) != 2:
            axes[axis] = {'geometry_status': 'AMBIGUOUS_GRID_PERIODICITY', 'reason': 'EXPECTED_TWO_CANDIDATE_FAMILIES_NOT_AVAILABLE'}
            continue
        small, large = candidates
        data = corrected['axes'][axis]
        result = hierarchy_axis(data['positions_px'],data['heights_px'],small['pitch_px'],large['pitch_px'])
        comparisons = []
        for label, after in (('minor',small),('major',large)):
            before_candidates = uncorrected['axes'][axis]['candidates']
            before = min(before_candidates, key=lambda c:abs(c['pitch_px']/after['pitch_px']-1)) if before_candidates else None
            comparisons.append(dict(family=label, before_rotation=before, after_rotation=after,
                                    pitch_change_percent=percent_difference(before['pitch_px'],after['pitch_px']) if before else None,
                                    rigid_rotation_analytic_pitch_factor=float(np.cos(np.radians(angle)))))
        result['rotation_comparison'] = comparisons
        # Compare the SAME observed marks. Padding can expose clipped edge marks
        # that an unrotated projection excluded; mixing sets confounds RMS.
        dimension = 0 if axis == 'x' else 1
        matrix = np.asarray(corrected['original_to_aligned'])
        other_center = (gray.shape[0 if axis == 'x' else 1]-1)/2
        old_positions = np.asarray(uncorrected['axes'][axis]['positions_px'])
        mapped = (matrix[dimension, dimension]*old_positions
                  + matrix[dimension, 1-dimension]*other_center + matrix[dimension, 2])
        old_common, new_common, common_indices = [], [], []
        marks = result.get('marks', [])
        matched = set()
        for old, projected in zip(old_positions, mapped):
            if not marks:
                break
            index = int(np.argmin([abs(m['position_px']-projected) for m in marks]))
            if index not in matched and abs(marks[index]['position_px']-projected) < .25*small['pitch_px']:
                matched.add(index)
                old_common.append(float(old)); new_common.append(marks[index]['position_px'])
                common_indices.append(marks[index]['index'])
        if len(old_common) >= 3:
            common = {'n_marks': len(old_common), 'indices': common_indices,
                      'only_after_rotation_positions_px': [m['position_px'] for i,m in enumerate(marks) if i not in matched]}
            for label, values in (('before',old_common),('after',new_common)):
                slope, intercept = np.polyfit(common_indices, values, 1)
                residual = np.asarray(values)-intercept-slope*np.asarray(common_indices)
                common[label] = dict(pitch_px=float(slope), residual_px=float(np.sqrt(np.mean(residual**2))))
            common['pitch_change_percent'] = percent_difference(common['before']['pitch_px'],common['after']['pitch_px'])
            common['spatial_variation_after'] = spatial_variation(new_common, common_indices)
            result['rotation_common_marks'] = common
        axes[axis] = result
    identified = all(a['geometry_status'] == 'OBSERVED_FIVE_DIVISION_HIERARCHY' for a in axes.values())
    return dict(status='GEOMETRICALLY_IDENTIFIED_PROVISIONAL' if identified else 'AMBIGUOUS_GRID_PERIODICITY',
                estimated_rotation_deg=angle, original_to_aligned=corrected['original_to_aligned'], axes=axes,
                grid_scale_x=axes['x'].get('scale_minor_um_per_px') if identified else None,
                grid_scale_y=axes['y'].get('scale_minor_um_per_px') if identified else None,
                interpretation_policy='Independent short/long families, aligned phase, five indices per major interval and at least one fully observed five-interval group PER AXIS.',
                no_circle_information_used=True)
