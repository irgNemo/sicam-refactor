"""SALIVA 2.1 raster moments and masked GLCM, using only Python stdlib."""

import math


TEXTURE_GRAY_LEVELS = 32
TEXTURE_OFFSETS = ((1, 0), (1, -1), (0, -1), (-1, -1))
NUMERICAL_EPSILON = 1e-12
TEXTURE_FEATURES = ('contrast', 'homogeneity', 'energy', 'correlation', 'entropy')


def texture_methodology():
    return {
        'method': 'GLCM', 'gray_levels': TEXTURE_GRAY_LEVELS,
        'distance_px': 1, 'angles_deg': [0, 45, 90, 135],
        'symmetric': True, 'normalized': True,
        'aggregation': 'mean_over_valid_angles',
    }


def empty_texture():
    return {**dict.fromkeys(TEXTURE_FEATURES), 'valid_angles': 0, 'valid_pairs': 0}


def measure_raster(raster):
    """Reuse one mask and one gray crop for all four object measurements."""
    count = sx = sy = sxx = syy = sxy = 0
    histogram = [0] * 256
    for index, inside in enumerate(raster.mask):
        if not inside:
            continue
        y, x = divmod(index, raster.width)
        count += 1
        sx += x
        sy += y
        sxx += x * x
        syy += y * y
        sxy += x * y
        if raster.gray is not None:
            histogram[raster.gray[index]] += 1

    eccentricity = None
    if count >= 2:
        mu20 = max(0.0, sxx / count - (sx / count) ** 2)
        mu02 = max(0.0, syy / count - (sy / count) ** 2)
        mu11 = sxy / count - sx * sy / count ** 2
        delta = math.hypot(mu20 - mu02, 2 * mu11)
        major = (mu20 + mu02 + delta) / 2
        minor = max(0.0, (mu20 + mu02 - delta) / 2)
        if major > NUMERICAL_EPSILON:
            eccentricity = math.sqrt(max(0.0, min(1.0, 1 - minor / major)))

    mean = std = None
    if count and raster.gray is not None:
        # Preserve the exact 2.0 arithmetic: integer sum / count / 255.
        mean = sum(value * n for value, n in enumerate(histogram)) / count / 255
        variance = math.fsum(
            n * (value / 255.0 - mean) ** 2
            for value, n in enumerate(histogram) if n
        ) / count
        std = math.sqrt(max(0.0, variance))
    texture = measure_texture(raster) if raster.gray is not None else empty_texture()
    return {
        'eccentricity': eccentricity, 'mean_gray_intensity': mean,
        'std_gray_intensity': std, 'texture': texture,
    }


def measure_texture(raster):
    result = empty_texture()
    if raster.gray is None:
        return result
    quantized = bytes(value * TEXTURE_GRAY_LEVELS // 256 for value in raster.gray)
    features = []
    width, height, mask = raster.width, raster.height, raster.mask
    for dx, dy in TEXTURE_OFFSETS:
        counts = [0] * (TEXTURE_GRAY_LEVELS ** 2)
        pairs = 0
        for y in range(max(0, -dy), min(height, height - dy)):
            for x in range(max(0, -dx), min(width, width - dx)):
                origin = y * width + x
                neighbor = (y + dy) * width + x + dx
                if mask[origin] and mask[neighbor]:
                    i, j = quantized[origin], quantized[neighbor]
                    counts[i * TEXTURE_GRAY_LEVELS + j] += 1
                    counts[j * TEXTURE_GRAY_LEVELS + i] += 1
                    pairs += 1
        if pairs:
            features.append(_glcm_features(counts, 2 * pairs))
            result['valid_pairs'] += pairs
    result['valid_angles'] = len(features)
    for name in TEXTURE_FEATURES:
        values = [angle[name] for angle in features if angle[name] is not None]
        if values:
            result[name] = math.fsum(values) / len(values)
    return result


def _glcm_features(counts, total):
    entries = [
        (*divmod(index, TEXTURE_GRAY_LEVELS), count / total)
        for index, count in enumerate(counts) if count
    ]
    mean_i = math.fsum(i * p for i, _, p in entries)
    mean_j = math.fsum(j * p for _, j, p in entries)
    variance_i = math.fsum(p * (i - mean_i) ** 2 for i, _, p in entries)
    variance_j = math.fsum(p * (j - mean_j) ** 2 for _, j, p in entries)
    denominator = math.sqrt(variance_i * variance_j)
    correlation = None
    if denominator > NUMERICAL_EPSILON:
        correlation = math.fsum(
            p * (i - mean_i) * (j - mean_j) for i, j, p in entries
        ) / denominator
    return {
        'contrast': math.fsum(p * (i - j) ** 2 for i, j, p in entries),
        'homogeneity': math.fsum(p / (1 + (i - j) ** 2) for i, j, p in entries),
        'energy': math.sqrt(math.fsum(p * p for _, _, p in entries)),
        'entropy': -math.fsum(p * math.log2(p) for _, _, p in entries),
        'correlation': correlation,
    }
