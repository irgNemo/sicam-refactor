"""Lossless-to-raster polygon conversion; no scientific segmentation."""
import cv2
import numpy as np
from PIL import Image, ImageDraw

from api.services.characterization.geometry import is_self_intersecting_polygon
from api.services.segmentation.normalizers import normalize_segmentation_result, validate_normalized_segmentation_result
from .contracts import ImportProblem, LABELS


def topology(reason):
    raise ImportProblem('UNSUPPORTED_POLYGON_TOPOLOGY', reason)


def validate_contour(points, width, height):
    if len(points) < 3 or len(set(map(tuple, points))) < 3:
        topology('DEGENERATE_CONTOUR')
    if len(set(map(tuple, points))) != len(points):
        topology('SELF_INTERSECTION')
    if any(not (0 <= x < width and 0 <= y < height) for x, y in points):
        topology('OUT_OF_BOUNDS')
    if is_self_intersecting_polygon(points):
        topology('SELF_INTERSECTION')
    if cv2.contourArea(np.asarray(points, dtype=np.int32)) <= 0:
        topology('DEGENERATE_CONTOUR')


def component_polygon(binary, original, value):
    height, width = binary.shape
    contours, hierarchy = cv2.findContours(binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
    externals = [] if hierarchy is None else [i for i, h in enumerate(hierarchy[0]) if h[3] == -1]
    if len(externals) != 1:
        topology('MULTIPLE_EXTERIORS')
    if cv2.connectedComponents(binary, connectivity=4)[0] - 1 != 1:
        topology('DIAGONAL_BRIDGE')
    points = contours[externals[0]].reshape(-1, 2).tolist()
    if len(points) > 1 and points[0] == points[-1]:
        points.pop()
    validate_contour(points, width, height)
    rendered = Image.new('1', (width, height))
    ImageDraw.Draw(rendered).polygon([tuple(p) for p in points], fill=1)
    filled = np.asarray(rendered, dtype=bool)
    support = binary.astype(bool)
    interior = filled & ~support
    if value == 170:
        # Only nuclear/MN occlusions may occupy the cell's interior. Never fill
        # actual background or another cell region; never change source pixels.
        if np.any(interior & ~np.isin(original, (85, 255))):
            topology('REAL_HOLE')
        expected = support | (interior & np.isin(original, (85, 255)))
    else:
        if len(contours) > 1 or np.any(interior):
            topology('REAL_HOLE')
        expected = support
    if not np.array_equal(filled, expected):
        topology('RASTER_MISMATCH')
    return points


def convert_pair(image_path, mask_path):
    try:
        with Image.open(image_path) as image:
            if image.format not in ('JPEG', 'PNG') or getattr(image, 'n_frames', 1) != 1 or image.getexif().get(274, 1) != 1:
                raise ImportProblem('UNSUPPORTED_IMAGE_FORMAT')
            image.load()
            width, height = image.size
        with Image.open(mask_path) as mask:
            if mask.format != 'TIFF' or mask.mode != 'L' or getattr(mask, 'n_frames', 1) != 1 or mask.getexif().get(274, 1) != 1:
                raise ImportProblem('UNSUPPORTED_MASK_FORMAT')
            if mask.size != (width, height):
                raise ImportProblem('DIMENSION_MISMATCH')
            pixels = np.asarray(mask).copy()
    except ImportProblem:
        raise
    except (OSError, ValueError, Image.DecompressionBombError):
        raise ImportProblem('INVALID_IMAGE_FILE') from None
    if set(np.unique(pixels).tolist()) - {0, 85, 170, 255}:
        raise ImportProblem('UNEXPECTED_MASK_VALUE')
    raw = {'objetos': []}
    for value, label in LABELS:
        count, labels, stats, _ = cv2.connectedComponentsWithStats((pixels == value).astype('uint8'), connectivity=8)
        # Stable raster-order IDs, independent of OpenCV's component numbering.
        components = sorted(range(1, count), key=lambda i: (stats[i, 1], stats[i, 0], i))
        for raw_id, component in enumerate(components, 1):
            x, y, w, h, _ = stats[component]
            binary = (labels[y:y+h, x:x+w] == component).astype('uint8')
            local = component_polygon(binary, pixels[y:y+h, x:x+w], value)
            points = [[px + int(x), py + int(y)] for px, py in local]
            raw['objetos'].append({'id': raw_id, 'tipo': label, 'puntos': points})
    normalized = normalize_segmentation_result(raw, sample_type='SALIVA')
    validate_normalized_segmentation_result(normalized, 'SALIVA')
    for obj in normalized['objects']:
        obj['provenance'] = {'origin': 'manual', 'base_object_id': None}
    normalized['summary']['counts_by_label'] = {label: normalized['summary']['counts_by_label'].get(label, 0) for _, label in LABELS}
    return raw, normalized, {'width': width, 'height': height, 'raster_tolerance_px': 0}
