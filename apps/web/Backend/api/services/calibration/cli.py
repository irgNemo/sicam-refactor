"""Run with python -m api.services.calibration.cli --manifest ... --output /tmp/..."""
import argparse
import json
from pathlib import Path
from .engine import measure_image, consensus, ENGINE_VERSION
from .diagnostics import save_diagnostic


def run(manifest, output):
    manifest, output = Path(manifest).resolve(), Path(output).resolve()
    entries = json.loads(manifest.read_text())
    if not isinstance(entries, list) or not entries:
        raise ValueError('Manifest must be a nonempty array')
    sources = [(manifest.parent / entry['file']).resolve() for entry in entries]
    if len(set(sources)) != len(sources):
        raise ValueError('Duplicate sources cannot supply independent methods')
    if any(source.is_relative_to(output) for source in sources):
        raise ValueError('Output must be separate from source files')
    results = []
    for index, (source, entry) in enumerate(zip(sources, entries), 1):
        result = measure_image(source, entry)
        output.mkdir(parents=True, exist_ok=True)
        if result['source_width_px'] is not None and result['measurement_status'] != 'INVALID_SOURCE_IMAGE':
            diagnostic = output / f'{index:02d}-diagnostic.png'
            save_diagnostic(source, result, diagnostic)
            result['diagnostic_file'] = str(diagnostic)
        results.append(result)
    summary = {'engine_version': ENGINE_VERSION, 'results': results, 'consensus': consensus(results)}
    (output/'results.json').write_text(json.dumps(summary, indent=2, allow_nan=False)+'\n')
    lines = ['Provisional calibration estimate — NOT scientifically validated',
             'Original-resolution measurements; DPI ignored. Overlays are reduced diagnostics.',
             'Cyan: detected/inlier edges or segments; red: ellipse/X centers; yellow: circle/Y centers; magenta: rejected.', '']
    for result in results:
        lines.append(f"{result['source_file']}: {result['measurement_status']}")
        for key in ('sha256', 'source_width_px', 'source_height_px', 'known_dimension_um',
                    'scale_x_um_per_px', 'scale_y_um_per_px', 'mean_scale_um_per_px',
                    'anisotropy_percent', 'rotation_deg', 'warnings'):
            lines.append(f'  {key}: {result[key]}')
        metrics = result['fit_metrics']
        if result['pattern_type'] == 'graduated_grid':
            lines.append('  selected family: ' + (str(metrics.get('reference_family'))
                         if result['measurement_status'] == 'MEASURED' else 'NONE; no physical assignment'))
            for axis in ('x', 'y'):
                lines.append(f"  detected centers {axis}: {metrics.get('n_detected_centers_'+axis)}")
                for candidate in metrics.get('periodicity_candidates_'+axis, []):
                    lines.append(f"  {axis} candidate: " + json.dumps(candidate))
        else:
            for key in ('center_x_px', 'center_y_px', 'diameter_x_px', 'diameter_y_px',
                        'equivalent_circle_diameter_px', 'ellipse_major_px', 'ellipse_minor_px',
                        'ellipse_angle_deg', 'axis_ratio', 'fit_residual_px', 'circle_fit_residual_px',
                        'edge_points', 'inlier_points', 'inlier_fraction', 'circularity_deviation'):
                lines.append(f'  {key}: {metrics.get(key)}')
    lines.extend(['', json.dumps(summary['consensus'], indent=2, allow_nan=False)])
    (output/'report.txt').write_text('\n'.join(lines)+'\n')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    summary = run(args.manifest, args.output)
    print(json.dumps({'statuses': [r['measurement_status'] for r in summary['results']], 'consensus': summary['consensus']}, indent=2))


if __name__ == '__main__':
    main()
