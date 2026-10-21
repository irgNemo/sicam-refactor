"""Graduation candidates; physical family selection must never use circle scales."""
import cv2
import numpy as np
from .common import MeasurementError, normalized_gray, dark_mask, scales


def rotation(gray):
    # scale=1 disables LSD's default 0.8 downsampling.
    detected = cv2.createLineSegmentDetector(cv2.LSD_REFINE_STD, 1.0).detect(gray)[0]
    if detected is None:
        raise MeasurementError('INSUFFICIENT_GRID_MARKS')
    lines = detected.reshape(-1, 4).astype(np.float64)
    delta = lines[:, 2:]-lines[:, :2]
    lengths = np.linalg.norm(delta, axis=1)
    angles = np.degrees(np.arctan2(delta[:, 1], delta[:, 0]))
    deviations = (angles+45) % 90-45
    valid = (lengths >= max(10, min(gray.shape)*.02)) & (abs(deviations) <= 15)
    if valid.sum() < 4:
        raise MeasurementError('INSUFFICIENT_GRID_MARKS')
    order = np.argsort(deviations[valid])
    weights = lengths[valid][order]
    index = np.searchsorted(np.cumsum(weights), weights.sum()/2)
    angle = float(deviations[valid][order][index])
    return angle, lines[valid].tolist()


def projection_centers(profile):
    profile = cv2.GaussianBlur(profile.astype(np.float64)[None, :], (0, 0), 1.0)[0]
    # Orthogonal lines contribute a pedestal, especially after blur.
    profile = np.maximum(profile - np.median(profile), 0)
    above = profile > max(3., .12*profile.max())
    runs = np.flatnonzero(np.diff(np.r_[False, above, False]))
    centers, heights = [], []
    for start, end in runs.reshape(-1, 2):
        if start == 0 or end == len(profile):
            continue  # partial edge marks are not a center reference
        indices = np.arange(start, end, dtype=np.float64)
        weights = profile[start:end]
        centers.append(float(np.average(indices, weights=weights)))
        heights.append(float(weights.max()))
    return np.asarray(centers), np.asarray(heights)


def fit_lattice(positions, pitch_guess):
    """Deterministic phase search + robust position/index fit; gaps retain indices."""
    positions = np.sort(np.asarray(positions, dtype=np.float64))
    best = None
    for anchor in positions:
        pitch, intercept = pitch_guess, anchor
        for _ in range(5):
            indices = np.rint((positions-intercept)/pitch)
            residual = positions-(intercept+pitch*indices)
            keep = abs(residual) <= max(1., .12*pitch)
            # Multiple marks cannot occupy one division index.
            for index in np.unique(indices[keep]):
                members = np.flatnonzero(keep & (indices == index))
                if len(members) > 1:
                    keep[members] = False
                    keep[members[np.argmin(abs(residual[members]))]] = True
            if keep.sum() < 3:
                break
            design = np.column_stack((np.ones(keep.sum()), indices[keep]))
            intercept, pitch = np.linalg.lstsq(design, positions[keep], rcond=None)[0]
        if keep.sum() < 3 or pitch <= 0:
            continue
        residual = positions-(intercept+pitch*indices)
        rmse = float(np.sqrt(np.mean(residual[keep]**2)))
        score = (int(keep.sum()), -rmse)
        if best is None or score > best[0]:
            variance = float(np.sum((positions[keep]-positions[keep].mean())**2))
            best = (score, dict(pitch_px=float(pitch), intercept_px=float(intercept), n_marks=int(keep.sum()),
                residual_px=rmse, r_squared=float(1-np.sum(residual[keep]**2)/variance),
                positions_px=positions.tolist(), indices=indices.astype(int).tolist(),
                used_positions_px=positions[keep].tolist(), rejected_positions_px=positions[~keep].tolist(),
                missing_indices=int(np.ptp(indices[keep])+1-keep.sum())))
    return best[1] if best else None


def periodicities(positions, heights):
    if len(positions) < 3:
        return []
    groups = [('all', positions)]
    sorted_heights = np.sort(heights)
    gaps = sorted_heights[1:]/np.maximum(sorted_heights[:-1], 1)
    if len(gaps) and gaps.max() > 1.6:
        split = np.argmax(gaps)
        threshold = np.sqrt(sorted_heights[split]*sorted_heights[split+1])
        groups.extend([('long_marks', positions[heights >= threshold]), ('short_marks', positions[heights < threshold])])
    candidates = []
    for name, group in groups:
        if len(group) < 3:
            continue
        differences = np.diff(group)
        # Modes of adjacent gaps supply guesses; no expected physical-scale range.
        clusters = []
        for gap in sorted(differences[differences > 2]):
            if clusters and gap < np.median(clusters[-1])*1.15:
                clusters[-1].append(gap)
            else:
                clusters.append([gap])
        for cluster in clusters:
            candidate = fit_lattice(group, float(np.median(cluster)))
            if candidate is None:
                continue
            candidate['family'] = name
            candidate['adjacent_gap_support'] = int(np.sum(abs(differences-candidate['pitch_px']) <= max(1., .12*candidate['pitch_px'])))
            old = next((c for c in candidates if abs(c['pitch_px']/candidate['pitch_px']-1) < .05), None)
            if old is None:
                candidates.append(candidate)
            elif (candidate['n_marks'], -candidate['residual_px']) > (old['n_marks'], -old['residual_px']):
                candidates[candidates.index(old)] = candidate
    return sorted(candidates, key=lambda c: (-c['n_marks'], c['residual_px']))


def measure_grid(gray, division_um, reference_family=None):
    normalized, illumination = normalized_gray(gray)
    mask, threshold = dark_mask(normalized)
    angle, lines = rotation(normalized)
    h, w = gray.shape
    matrix = cv2.getRotationMatrix2D(((w-1)/2, (h-1)/2), angle, 1.0)
    c, s = abs(matrix[0, 0]), abs(matrix[0, 1])
    nw, nh = int(np.ceil(w*c+h*s)), int(np.ceil(h*c+w*s))
    matrix[:, 2] += [(nw-w)/2, (nh-h)/2]
    # Rigid rotation at unit scale, padded to avoid clipping: never a resize.
    aligned = cv2.warpAffine(mask, matrix, (nw, nh), flags=cv2.INTER_NEAREST, borderValue=0)
    px, hx = projection_centers(np.sum(aligned > 0, axis=0))
    py, hy = projection_centers(np.sum(aligned > 0, axis=1))
    x, y = periodicities(px, hx), periodicities(py, hy)
    metrics = dict(n_detected_centers_x=len(px), n_detected_centers_y=len(py),
                   detected_centers_x_px=px.tolist(), detected_centers_y_px=py.tolist(),
                   periodicity_candidates_x=x, periodicity_candidates_y=y,
                   estimated_rotation_deg=angle, original_to_aligned=matrix.tolist(),
                   detected_segments_original_px=lines, illumination_plane=illumination,
                   otsu_threshold=threshold, reference_family=reference_family)
    if not x or not y:
        raise MeasurementError('INSUFFICIENT_GRID_MARKS', metrics)
    # Image periodicity alone cannot certify which marks have a physical size.
    # uniform_lattice is an explicit pattern contract, not an inferred choice.
    if reference_family != 'uniform_lattice':
        raise MeasurementError('AMBIGUOUS_GRID_PERIODICITY', metrics)
    selected = []
    for candidates in (x, y):
        ranked = sorted(candidates, key=lambda c: c['adjacent_gap_support'], reverse=True)
        # With an explicitly uniform pattern, repeated adjacent spacings identify
        # the fundamental. Missing marks produce harmonics; isolated outliers
        # can produce subharmonics with many artificial missing indices.
        if ranked[0]['adjacent_gap_support'] < 2 or (len(ranked) > 1 and ranked[0]['adjacent_gap_support'] == ranked[1]['adjacent_gap_support']):
            raise MeasurementError('AMBIGUOUS_GRID_PERIODICITY', metrics)
        selected.append(ranked[0])
    x, y = selected
    metrics.update(n_marks_x=x['n_marks'], n_marks_y=y['n_marks'], pitch_x_px=x['pitch_px'], pitch_y_px=y['pitch_px'],
                   residual_x_px=x['residual_px'], residual_y_px=y['residual_px'],
                   r_squared_x=x['r_squared'], r_squared_y=y['r_squared'],
                   rejected_marks_x_px=x['rejected_positions_px'], rejected_marks_y_px=y['rejected_positions_px'])
    # Convert rotated normal spacings to original sensor-axis scales under the
    # stated diagonal (no shear) scale model. At zero rotation: sx=D/pitch_x.
    cos2 = np.cos(np.radians(angle))**2
    sin2 = 1-cos2
    inverse_squared = np.linalg.solve([[cos2, sin2], [sin2, cos2]],
                                     [(x['pitch_px']/division_um)**2, (y['pitch_px']/division_um)**2])
    if np.any(inverse_squared <= 0):
        raise MeasurementError('INVALID_GRID_AXIS_GEOMETRY', metrics)
    sx, sy = 1/np.sqrt(inverse_squared)
    return {**scales(sx, sy), 'rotation_deg': angle, 'fit_metrics': metrics,
            'measurement_status': 'MEASURED', 'warnings': ['GRID_DIAGONAL_SCALE_MODEL_NO_SHEAR']}
