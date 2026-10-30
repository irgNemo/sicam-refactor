import math


CIRCULARITY_EPSILON = 1e-9
POINT_BOUNDARY_EPSILON = 1e-9

POINT_INSIDE = 'INSIDE'
POINT_ON_BOUNDARY = 'ON_BOUNDARY'
POINT_OUTSIDE = 'OUTSIDE'


def polygon_area(points):
    valid_points = _validate_polygon_points(points)
    return abs(polygon_signed_area(valid_points))


def polygon_signed_area(points):
    valid_points = _validate_polygon_points(points)
    area = 0
    for index, current in enumerate(valid_points):
        next_point = valid_points[(index + 1) % len(valid_points)]
        area += current[0] * next_point[1]
        area -= next_point[0] * current[1]
    return area / 2


def polygon_perimeter(points):
    valid_points = _validate_polygon_points(points)
    perimeter = 0
    for index, current in enumerate(valid_points):
        next_point = valid_points[(index + 1) % len(valid_points)]
        perimeter += math.dist(current, next_point)
    return perimeter


def polygon_centroid(points):
    valid_points = _validate_polygon_points(points)
    signed_area = polygon_signed_area(valid_points)
    if signed_area == 0:
        return None

    factor = 1 / (6 * signed_area)
    centroid_x = 0
    centroid_y = 0
    for index, current in enumerate(valid_points):
        next_point = valid_points[(index + 1) % len(valid_points)]
        cross = current[0] * next_point[1] - next_point[0] * current[1]
        centroid_x += (current[0] + next_point[0]) * cross
        centroid_y += (current[1] + next_point[1]) * cross

    return [centroid_x * factor, centroid_y * factor]


def polygon_circularity(area, perimeter):
    if area is None or perimeter is None or perimeter == 0:
        return None, None

    circularity = 4 * math.pi * area / (perimeter ** 2)
    if 0 <= circularity <= 1:
        return circularity, None
    if 1 < circularity <= 1 + CIRCULARITY_EPSILON:
        return 1.0, None
    return None, 'INVALID_CIRCULARITY'


def is_self_intersecting_polygon(points):
    valid_points = _validate_polygon_points(points)
    segments = _polygon_segments(valid_points)

    for first_index, first_segment in enumerate(segments):
        for second_index in range(first_index + 1, len(segments)):
            if _segments_are_adjacent(
                first_index,
                second_index,
                len(segments),
            ):
                continue
            if _segments_intersect(first_segment, segments[second_index]):
                return True
    return False


def classify_point_in_polygon(point, polygon, epsilon=POINT_BOUNDARY_EPSILON):
    valid_polygon = _validate_polygon_points(polygon)
    valid_point = _validate_point(point)

    inside = False
    x, y = valid_point

    for start, end in _polygon_segments(valid_polygon):
        if _point_on_segment(valid_point, start, end, epsilon):
            return POINT_ON_BOUNDARY

        yi = start[1]
        yj = end[1]
        if (yi > y) != (yj > y):
            x_intersection = (
                (end[0] - start[0]) * (y - yi) / (yj - yi) + start[0]
            )
            if x < x_intersection:
                inside = not inside

    return POINT_INSIDE if inside else POINT_OUTSIDE


def _validate_polygon_points(points):
    if not isinstance(points, list) or len(points) < 3:
        raise ValueError('points debe ser una lista de al menos 3 puntos')

    valid_points = []
    for point in points:
        valid_points.append(_validate_point(point))

    return valid_points


def _validate_point(point):
    if not isinstance(point, list) or len(point) != 2:
        raise ValueError('cada punto debe tener dos coordenadas')
    if not all(_is_finite_number(coordinate) for coordinate in point):
        raise ValueError('las coordenadas deben ser numeros finitos')
    return [float(point[0]), float(point[1])]


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _polygon_segments(points):
    return [
        (current, points[(index + 1) % len(points)])
        for index, current in enumerate(points)
    ]


def _segments_are_adjacent(first_index, second_index, total_segments):
    if abs(first_index - second_index) == 1:
        return True
    return {first_index, second_index} == {0, total_segments - 1}


def _segments_intersect(first, second):
    p1, q1 = first
    p2, q2 = second

    o1 = _orientation(p1, q1, p2)
    o2 = _orientation(p1, q1, q2)
    o3 = _orientation(p2, q2, p1)
    o4 = _orientation(p2, q2, q1)

    if o1 != o2 and o3 != o4:
        return True

    if o1 == 0 and _point_on_segment(p2, p1, q1):
        return True
    if o2 == 0 and _point_on_segment(q2, p1, q1):
        return True
    if o3 == 0 and _point_on_segment(p1, p2, q2):
        return True
    if o4 == 0 and _point_on_segment(q1, p2, q2):
        return True

    return False


def _orientation(start, end, point):
    value = (
        (end[1] - start[1]) * (point[0] - end[0]) -
        (end[0] - start[0]) * (point[1] - end[1])
    )
    if abs(value) <= POINT_BOUNDARY_EPSILON:
        return 0
    return 1 if value > 0 else 2


def _point_on_segment(point, start, end, epsilon=POINT_BOUNDARY_EPSILON):
    cross = (
        (point[1] - start[1]) * (end[0] - start[0]) -
        (point[0] - start[0]) * (end[1] - start[1])
    )
    if abs(cross) > epsilon:
        return False

    return (
        min(start[0], end[0]) - epsilon <= point[0] <=
        max(start[0], end[0]) + epsilon and
        min(start[1], end[1]) - epsilon <= point[1] <=
        max(start[1], end[1]) + epsilon
    )


# ---------------------------------------------------------------------------
# Sprint 18U-C1 — Characterization 2.3 geometry helpers
# ---------------------------------------------------------------------------

NUMERICAL_EPSILON = 1e-12


def polygon_convex_hull(points):
    """Return the convex hull of *points* using Andrew's Monotonic Chain.

    Parameters
    ----------
    points : list[list[float]]
        Input points in the same ``[x, y]`` format used throughout geometry.py.
        May contain duplicates.

    Returns
    -------
    list[list[float]] | None
        Counter-clockwise hull vertices, or ``None`` when the hull has fewer
        than 3 distinct non-collinear points (degenerate line / single point).
    """
    if not isinstance(points, list) or len(points) < 3:
        return None

    # Validate and deduplicate
    seen = set()
    valid = []
    for p in points:
        try:
            vp = _validate_point(p)
        except ValueError:
            continue
        key = (vp[0], vp[1])
        if key not in seen:
            seen.add(key)
            valid.append(vp)

    if len(valid) < 3:
        return None

    # Sort lexicographically (x primary, y secondary)
    valid.sort(key=lambda p: (p[0], p[1]))

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    # Build lower hull
    lower = []
    for p in valid:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)

    # Build upper hull
    upper = []
    for p in reversed(valid):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)

    # Concatenate without duplicating first/last shared points
    hull = lower[:-1] + upper[:-1]

    if len(hull) < 3:
        return None

    return hull


def polygon_convex_hull_area(points):
    """Return the area of the convex hull of *points*, or ``None`` if degenerate."""
    hull = polygon_convex_hull(points)
    if hull is None:
        return None
    return polygon_area(hull)


def minimum_polygon_distance(points_a, points_b):
    """Return the minimum Euclidean distance between two closed polygonal sets.

    A polygonal *set* is the filled region bounded by the polygon.  The distance
    between two sets is zero whenever they touch, overlap, intersect, or one is
    contained in the other.

    Parameters
    ----------
    points_a, points_b : list[list[float]]
        Polygon vertices as ``[x, y]`` lists.  Each polygon must have at least
        3 valid points.

    Returns
    -------
    float
        Minimum distance >= 0.  Returns 0.0 for touching/overlapping/contained.

    Raises
    ------
    ValueError
        If either polygon has fewer than 3 valid points.
    """
    va = _validate_polygon_points(points_a)
    vb = _validate_polygon_points(points_b)

    segs_a = _polygon_segments(va)
    segs_b = _polygon_segments(vb)

    # --- Short-circuit: segment intersection check ---
    for sa in segs_a:
        for sb in segs_b:
            if _segments_intersect(sa, sb):
                return 0.0

    # --- Short-circuit: point containment check ---
    # If any vertex of A is inside-or-on B, the regions overlap/touch.
    for p in va:
        if classify_point_in_polygon(p, vb) in (POINT_INSIDE, POINT_ON_BOUNDARY):
            return 0.0
    # If any vertex of B is inside-or-on A, the regions overlap/touch.
    for p in vb:
        if classify_point_in_polygon(p, va) in (POINT_INSIDE, POINT_ON_BOUNDARY):
            return 0.0

    # --- Minimum segment-to-segment distance ---
    min_dist = math.inf
    for sa in segs_a:
        for sb in segs_b:
            d = _segment_to_segment_distance(sa[0], sa[1], sb[0], sb[1])
            if d < min_dist:
                min_dist = d

    return max(0.0, min_dist)


def _point_to_segment_distance(p, a, b):
    """Minimum Euclidean distance from point *p* to segment *ab*."""
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    seg_len_sq = dx * dx + dy * dy
    if seg_len_sq < NUMERICAL_EPSILON:
        # Degenerate segment — treat as a point
        return math.dist(p, a)
    t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / seg_len_sq))
    proj = [ax + t * dx, ay + t * dy]
    return math.dist(p, proj)


def _segment_to_segment_distance(p1, p2, p3, p4):
    """Minimum distance between segment *p1-p2* and segment *p3-p4*."""
    return min(
        _point_to_segment_distance(p1, p3, p4),
        _point_to_segment_distance(p2, p3, p4),
        _point_to_segment_distance(p3, p1, p2),
        _point_to_segment_distance(p4, p1, p2),
    )
