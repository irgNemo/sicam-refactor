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
