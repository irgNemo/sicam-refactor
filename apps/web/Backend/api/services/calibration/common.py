"""Image-only operations and float64 geometry. No DPI-to-length conversion."""
import cv2
import numpy as np


class MeasurementError(ValueError):
    def __init__(self, status, metrics=None):
        super().__init__(status)
        self.status = status
        self.metrics = metrics or {}


def normalized_gray(gray):
    """Robust bright-background plane, estimated from tiles, on the original raster.

    Float32 raster buffers limit memory; plane estimation and all fits use float64.
    Only illumination is normalized; there is no spatial resampling here.
    """
    h, w = gray.shape
    samples = []
    tile = max(16, min(h, w) // 16)
    for y in range(0, h, tile):
        for x in range(0, w, tile):
            block = gray[y:y+tile, x:x+tile]
            samples.append([(x + (block.shape[1]-1)/2)/w, (y + (block.shape[0]-1)/2)/h, np.percentile(block, 90)])
    values = np.asarray(samples, dtype=np.float64)
    design = np.column_stack((values[:, :2], np.ones(len(values))))
    keep = values[:, 2] >= np.percentile(values[:, 2], 40)
    for _ in range(5):
        coef = np.linalg.lstsq(design[keep], values[keep, 2], rcond=None)[0]
        residual = values[:, 2] - design @ coef
        center = np.median(residual[keep])
        mad = max(1.0, 1.4826 * np.median(np.abs(residual[keep] - center)))
        keep = np.abs(residual - center) <= 3 * mad
        if keep.sum() < 3:
            raise MeasurementError('INVALID_BACKGROUND')
    plane = (coef[0] * np.arange(w, dtype=np.float32)[None, :]/w
             + coef[1] * np.arange(h, dtype=np.float32)[:, None]/h + coef[2])
    normalized = np.clip(gray.astype(np.float32) * 200.0 / np.maximum(plane, 1), 0, 255).astype(np.uint8)
    if np.ptp(normalized) < 5:
        raise MeasurementError('NO_REFERENCE_DETECTED')
    return cv2.GaussianBlur(normalized, (0, 0), 1.0), coef.tolist()


def dark_mask(gray):
    threshold, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    return mask, float(threshold)


def scales(sx, sy):
    sx, sy = float(sx), float(sy)
    mean = (sx + sy)/2
    return dict(scale_x_um_per_px=sx, scale_y_um_per_px=sy,
                mean_scale_um_per_px=mean, anisotropy_percent=100*abs(sx-sy)/mean)


def fit_ellipse(points):
    """Constrained direct least squares in centered/scaled float64 coordinates."""
    points = np.asarray(points, dtype=np.float64)
    if len(points) < 6:
        raise MeasurementError('INSUFFICIENT_EDGE_POINTS')
    origin = points.mean(axis=0)
    factor = np.std(points)
    if factor <= 0:
        raise MeasurementError('DEGENERATE_REFERENCE_OBJECT')
    x, y = ((points-origin)/factor).T
    d1 = np.column_stack((x*x, x*y, y*y))
    d2 = np.column_stack((x, y, np.ones(len(x))))
    transform = -np.linalg.solve(d2.T @ d2, d2.T @ d1)
    c1 = np.array([[0., 0., 2.], [0., -1., 0.], [2., 0., 0.]])
    matrix = np.linalg.solve(c1, d1.T @ d1 + d1.T @ d2 @ transform)
    _, vectors = np.linalg.eig(matrix)
    candidates = [v.real for v in vectors.T if np.max(abs(v.imag)) < 1e-8 and 4*v.real[0]*v.real[2]-v.real[1]**2 > 0]
    if len(candidates) != 1:
        raise MeasurementError('DEGENERATE_ELLIPSE_FIT')
    a, b, c = candidates[0]
    d, e, f = transform @ candidates[0]
    q = np.array([[a, b/2], [b/2, c]])
    center = -.5 * np.linalg.solve(q, [d, e])
    level = -(center @ q @ center + np.dot([d, e], center) + f)
    eig, axes = np.linalg.eigh(q)
    radii_squared = level/eig
    if np.any(radii_squared <= 0):
        raise MeasurementError('DEGENERATE_ELLIPSE_FIT')
    radii = np.sqrt(radii_squared)*factor
    order = np.argsort(radii)[::-1]
    return origin+center*factor, radii[order], axes[:, order]


def ellipse_residual(points, ellipse):
    center, radii, axes = ellipse
    local = (points-center) @ axes
    value = np.sum((local/radii)**2, axis=1)-1
    gradient = 2*np.sqrt(np.sum((local/(radii*radii))**2, axis=1))
    return value/np.maximum(gradient, 1e-12)


def ellipse_metrics(ellipse):
    center, radii, axes = ellipse
    extents = np.sqrt((axes**2) @ (radii**2))
    return dict(center_x_px=float(center[0]), center_y_px=float(center[1]),
                diameter_x_px=float(2*extents[0]), diameter_y_px=float(2*extents[1]),
                ellipse_major_px=float(2*radii[0]), ellipse_minor_px=float(2*radii[1]),
                ellipse_angle_deg=float(np.degrees(np.arctan2(axes[1, 0], axes[0, 0])) % 180),
                axis_ratio=float(radii[0]/radii[1]),
                area_equivalent_diameter_px=float(2*np.sqrt(np.prod(radii))))
