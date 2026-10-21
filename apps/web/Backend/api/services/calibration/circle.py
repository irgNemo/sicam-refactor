"""One algorithm for all dark disk references; no expected physical scale."""
import cv2
import numpy as np
from .common import (MeasurementError, normalized_gray, dark_mask, fit_ellipse,
                     ellipse_residual, ellipse_metrics, scales)


def measure_circle(gray, known_diameter_um, *, smoothing_sigma=1.0,
                   radial_points=1440, rejection_mad=4.5):
    # Optional study parameters; defaults retain the 18S-A calculation exactly.
    if isinstance(radial_points, bool) or not isinstance(radial_points, int) or radial_points < 360:
        raise ValueError('radial_points must be an integer >= 360')
    if not np.isfinite(rejection_mad) or rejection_mad <= 0:
        raise ValueError('rejection_mad must be positive and finite')
    normalized, illumination = normalized_gray(gray, smoothing_sigma=smoothing_sigma)
    mask, threshold = dark_mask(normalized)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    h, w = gray.shape
    candidates = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < max(50, h*w*.0005) or len(contour) < 6:
            continue
        perimeter = cv2.arcLength(contour, True)
        solidity = area/max(cv2.contourArea(cv2.convexHull(contour)), 1)
        circularity = 4*np.pi*area/max(perimeter*perimeter, 1)
        if solidity < .8 or circularity < .45:
            continue
        x, y, bw, bh = cv2.boundingRect(contour)
        inside = np.zeros((bh, bw), dtype=np.uint8)
        cv2.drawContours(inside, [contour - [x, y]], -1, 1, -1)
        fill = np.mean(mask[y:y+bh, x:x+bw][inside > 0] > 0)
        if fill < .85:  # A dark ring/grid is not the declared filled disk.
            continue
        candidates.append((area, contour, dict(area_px2=area, circularity=float(circularity),
            solidity=float(solidity), dark_fill_fraction=float(fill), bbox=[x, y, bw, bh],
            clipped=bool(x <= 4 or y <= 4 or x+bw >= w-4 or y+bh >= h-4))))
    candidates.sort(key=lambda item: -item[0])
    info = {'candidates': [c[2] for c in candidates], 'otsu_threshold': threshold,
            'illumination_plane': illumination}
    if not candidates:
        raise MeasurementError('NO_REFERENCE_DETECTED', info)
    if len(candidates) > 1 and candidates[1][0] >= .5*candidates[0][0]:
        raise MeasurementError('AMBIGUOUS_REFERENCE_OBJECT', info)
    _, contour, selected = candidates[0]
    if selected['clipped']:
        raise MeasurementError('CLIPPED_REFERENCE_OBJECT', info)
    initial = fit_ellipse(contour[:, 0, :])
    center, radii, axes = initial
    # Radial profiles sampled from the original-resolution, normalized image.
    angles = np.linspace(0, 2*np.pi, radial_points, endpoint=False, dtype=np.float64)
    directions = np.column_stack((np.cos(angles), np.sin(angles)))
    radial = 1/np.sqrt(np.sum(((directions @ axes)/radii)**2, axis=1))
    search = max(6., .02*float(radii.max()))
    offsets = np.arange(-search, search+.25, .25)
    xy = center + (radial[:, None]+offsets[None, :])[:, :, None]*directions[:, None, :]
    profiles = cv2.remap(normalized.astype(np.float32), xy[:, :, 0].astype(np.float32),
                         xy[:, :, 1].astype(np.float32), cv2.INTER_LINEAR,
                         borderMode=cv2.BORDER_REPLICATE).astype(np.float64)
    gradient = np.gradient(profiles, .25, axis=1)
    peak = np.argmax(gradient[:, 1:-1], axis=1)+1
    rows = np.arange(len(peak))
    g0, gm, gp = gradient[rows, peak], gradient[rows, peak-1], gradient[rows, peak+1]
    delta = np.divide(.5*(gm-gp), gm-2*g0+gp, out=np.zeros(len(peak)), where=abs(gm-2*g0+gp)>1e-12)
    delta = np.clip(delta, -.5, .5)
    points = center+(radial + offsets[peak]+.25*delta)[:, None]*directions
    valid = (peak > 1) & (peak < len(offsets)-2) & (g0 > 2)
    if valid.sum() < 30:
        raise MeasurementError('INSUFFICIENT_EDGE_POINTS', info)
    keep = valid.copy()
    for _ in range(5):
        ellipse = fit_ellipse(points[keep])
        residual = ellipse_residual(points, ellipse)
        med = np.median(residual[keep])
        mad = 1.4826*np.median(abs(residual[keep]-med))
        keep = valid & (abs(residual-med) <= max(.75, rejection_mad*mad))
        if keep.sum() < 30:
            raise MeasurementError('INSUFFICIENT_EDGE_POINTS', info)
    ellipse = fit_ellipse(points[keep])
    sectors = np.floor(angles/(2*np.pi)*36).astype(int)
    if len(np.unique(sectors[keep])) < 36:
        raise MeasurementError('INCOMPLETE_REFERENCE_EDGE', info)
    metrics = ellipse_metrics(ellipse)
    if (metrics['center_x_px']-metrics['diameter_x_px']/2 <= 4
            or metrics['center_x_px']+metrics['diameter_x_px']/2 >= w-4
            or metrics['center_y_px']-metrics['diameter_y_px']/2 <= 4
            or metrics['center_y_px']+metrics['diameter_y_px']/2 >= h-4):
        raise MeasurementError('CLIPPED_REFERENCE_OBJECT', info)
    # Independent circle least-squares fit and radial residual, float64.
    p = points[keep]
    origin = p.mean(axis=0)
    local = p-origin
    coef = np.linalg.lstsq(np.column_stack((2*local, np.ones(len(p)))), np.sum(local*local, axis=1), rcond=None)[0]
    circle_center = origin+coef[:2]
    radius = np.sqrt(coef[2]+np.dot(coef[:2], coef[:2]))
    metrics.update(info)
    metrics.update(equivalent_circle_diameter_px=float(2*radius), circle_center_px=circle_center.tolist(),
        circle_fit_residual_px=float(np.sqrt(np.mean((np.linalg.norm(p-circle_center, axis=1)-radius)**2))),
        fit_residual_px=float(np.sqrt(np.mean(ellipse_residual(p, ellipse)**2))),
        edge_points=int(valid.sum()), inlier_points=int(keep.sum()), inlier_fraction=float(keep.sum()/len(points)),
        circularity_deviation=float(1-selected['circularity']),
        edge_points_original_px=points.tolist(), rejected_edge_indices=np.flatnonzero(~keep).tolist())
    return {**scales(known_diameter_um/metrics['diameter_x_px'], known_diameter_um/metrics['diameter_y_px']),
            'rotation_deg': metrics['ellipse_angle_deg'], 'fit_metrics': metrics,
            'warnings': ['APPARENT_ANISOTROPY_INCLUDES_PATTERN_AND_OPTICS'], 'measurement_status': 'MEASURED'}
