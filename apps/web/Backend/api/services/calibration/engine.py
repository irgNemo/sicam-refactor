"""Pure Python orchestration: explicit physical manifest, original raster and hashes."""
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image
from .common import MeasurementError
from .circle import measure_circle
from .grid import measure_grid

ENGINE_VERSION = 'calibration-provisional-v1'


def validate_entry(entry):
    if entry.get('pattern_type') not in ('circle', 'graduated_grid'):
        raise ValueError('Unsupported pattern_type')
    key = 'known_diameter_um' if entry['pattern_type'] == 'circle' else 'division_um'
    for name in (key, 'objective_magnification'):
        value = entry.get(name)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not np.isfinite(value) or value <= 0:
            raise ValueError(f'{name} must be explicit, positive and finite')
    if entry.get('grid_reference') not in (None, 'uniform_lattice'):
        raise ValueError('Unsupported grid_reference')
    dimensions = entry.get('expected_dimensions_px', [4928, 4928])
    if len(dimensions) != 2 or any(isinstance(v, bool) or not isinstance(v, int) or v <= 0 for v in dimensions):
        raise ValueError('expected_dimensions_px must contain width and height')
    return key, dimensions


def measure_image(path, entry):
    key, expected = validate_entry(entry)
    path = Path(path)
    result = dict(source_file=path.name, sha256=None, file_size_bytes=None,
                  source_width_px=None, source_height_px=None,
                  objective_magnification=entry['objective_magnification'],
                  acquisition=entry.get('acquisition', {}), pattern_type=entry['pattern_type'],
                  known_dimension_um=entry[key], physical_dimension_source='EXPLICIT_MANIFEST',
                  expected_dimensions_px=expected, engine_version=ENGINE_VERSION,
                  scale_x_um_per_px=None, scale_y_um_per_px=None, mean_scale_um_per_px=None,
                  anisotropy_percent=None, rotation_deg=None, fit_metrics={}, warnings=[])
    if not path.is_file():
        return {**result, 'measurement_status': 'REAL_CALIBRATION_FILES_MISSING'}
    content = path.read_bytes()
    result.update(sha256=hashlib.sha256(content).hexdigest(), file_size_bytes=len(content))
    # Read the exact bytes that were hashed; no EXIF orientation or DPI transform.
    from io import BytesIO
    try:
        with Image.open(BytesIO(content)) as image:
            result.update(source_width_px=image.width, source_height_px=image.height,
                          source_mode=image.mode, source_channels=list(image.getbands()), source_format=image.format,
                          metadata={'dpi': image.info.get('dpi'), 'exif_orientation': image.getexif().get(274)})
            if list(image.size) != expected:
                return {**result, 'measurement_status': 'SOURCE_DIMENSION_MISMATCH'}
            gray = np.asarray(image.convert('L'))
    except (OSError, ValueError):
        return {**result, 'measurement_status': 'INVALID_SOURCE_IMAGE'}
    try:
        measured = (measure_circle(gray, entry[key]) if entry['pattern_type'] == 'circle'
                    else measure_grid(gray, entry[key], entry.get('grid_reference')))
        result.update(measured)
    except MeasurementError as error:
        result.update(measurement_status=error.status, fit_metrics=error.metrics,
                      rotation_deg=error.metrics.get('estimated_rotation_deg'))
    except (np.linalg.LinAlgError, FloatingPointError):
        result.update(measurement_status='DEGENERATE_GEOMETRY')
    # DPI is informational only, never an input to either measurement function.
    if result.get('metadata', {}).get('dpi'):
        result['warnings'].append('DPI_IGNORED_FOR_MICROSCOPIC_SCALE')
    return result


def percent_difference(a, b):
    return float(100*abs(a-b)/((a+b)/2))


def consensus(results):
    measured = [r for r in results if r['measurement_status'] == 'MEASURED']
    excluded = [{'source_file': r['source_file'], 'reason': r['measurement_status']} for r in results if r not in measured]
    signatures = {json.dumps([r['source_width_px'], r['source_height_px'], r['objective_magnification'], r['acquisition']], sort_keys=True) for r in measured}
    if len(signatures) > 1:
        return {'status': 'INCOMPATIBLE_ACQUISITION', 'n_methods': len(measured), 'excluded': excluded}
    pairs = []
    for i, a in enumerate(measured):
        for b in measured[i+1:]:
            pairs.append(dict(sources=[a['source_file'], b['source_file']],
                difference_x_percent=percent_difference(a['scale_x_um_per_px'], b['scale_x_um_per_px']),
                difference_y_percent=percent_difference(a['scale_y_um_per_px'], b['scale_y_um_per_px'])))
    stats = {}
    for axis in ('x', 'y'):
        values = np.asarray([r[f'scale_{axis}_um_per_px'] for r in measured], dtype=np.float64)
        if not len(values):
            stats[axis] = None
            continue
        std = float(np.std(values, ddof=1)) if len(values) >= 2 else None
        stats[axis] = dict(mean=float(values.mean()), median=float(np.median(values)), standard_deviation=std,
            cv_percent=100*std/float(values.mean()) if std is not None else None,
            mad=float(np.median(abs(values-np.median(values)))), min=float(values.min()), max=float(values.max()),
            max_percent_difference=max((p[f'difference_{axis}_percent'] for p in pairs), default=None))
    return dict(status='PROVISIONAL_ONLY' if len(measured) >= 2 else 'INSUFFICIENT_MEASURED_METHODS',
                n_methods=len(measured), included=[r['source_file'] for r in measured], excluded=excluded,
                statistics=stats, pairwise=pairs,
                provisional_median_scale_x=stats['x']['median'] if len(measured) >= 2 else None,
                provisional_median_scale_y=stats['y']['median'] if len(measured) >= 2 else None)
