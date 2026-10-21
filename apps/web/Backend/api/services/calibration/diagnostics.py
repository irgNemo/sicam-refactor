"""Scientific overlays, rendered at original coordinates before preview reduction."""
import cv2
import numpy as np
from PIL import Image, ImageDraw


def save_diagnostic(source, result, destination):
    with Image.open(source) as original:
        image = original.convert('RGB')
    draw = ImageDraw.Draw(image)
    metrics = result['fit_metrics']
    width = max(1, image.width//1000)
    for segment in metrics.get('detected_segments_original_px', []):
        draw.line(tuple(segment), fill='cyan', width=width)
    if 'original_to_aligned' in metrics:
        inverse = cv2.invertAffineTransform(np.array(metrics['original_to_aligned'], dtype=np.float64))
        for axis, color in [('x', 'red'), ('y', 'yellow')]:
            for position in metrics[f'detected_centers_{axis}_px']:
                aligned = np.array([position, image.height/2, 1.] if axis == 'x' else [image.width/2, position, 1.])
                x, y = inverse @ aligned
                draw.ellipse((x-3*width, y-3*width, x+3*width, y+3*width), fill=color)
            for position in metrics.get(f'rejected_marks_{axis}_px', []):
                aligned = np.array([position, image.height/2, 1.] if axis == 'x' else [image.width/2, position, 1.])
                x, y = inverse @ aligned
                draw.line((x-5*width, y-5*width, x+5*width, y+5*width), fill='magenta', width=width)
    rejected = set(metrics.get('rejected_edge_indices', []))
    for i, (x, y) in enumerate(metrics.get('edge_points_original_px', [])):
        draw.ellipse((x-width, y-width, x+width, y+width), fill='magenta' if i in rejected else 'cyan')
    if 'ellipse_major_px' in metrics:
        theta = np.radians(metrics['ellipse_angle_deg'])
        matrix = np.array([[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]])
        t = np.linspace(0, 2*np.pi, 721)
        center = np.array([metrics['center_x_px'], metrics['center_y_px']])
        ellipse = np.column_stack((np.cos(t)*metrics['ellipse_major_px']/2, np.sin(t)*metrics['ellipse_minor_px']/2)) @ matrix.T + center
        draw.line([tuple(p) for p in ellipse], fill='red', width=width)
        cx, cy = metrics['circle_center_px']; r = metrics['equivalent_circle_diameter_px']/2
        draw.ellipse((cx-r, cy-r, cx+r, cy+r), outline='yellow', width=width)
        x, y = center
        draw.line((x-10*width, y, x+10*width, y), fill='red', width=width)
        draw.line((x, y-10*width, x, y+10*width), fill='red', width=width)
    else:
        for candidate in metrics.get('candidates', []):
            x, y, w, h = candidate['bbox']
            draw.rectangle((x, y, x+w, y+h), outline='orange', width=width)
    # This is a diagnostic only. The measurements above never consume this image.
    image.thumbnail((1400, 1400))
    image.save(destination)
