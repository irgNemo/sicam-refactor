import math


def polygon_area(points):
    valid_points = _validate_polygon_points(points)
    area = 0
    for index, current in enumerate(valid_points):
        next_point = valid_points[(index + 1) % len(valid_points)]
        area += current[0] * next_point[1]
        area -= next_point[0] * current[1]
    return abs(area) / 2


def polygon_perimeter(points):
    valid_points = _validate_polygon_points(points)
    perimeter = 0
    for index, current in enumerate(valid_points):
        next_point = valid_points[(index + 1) % len(valid_points)]
        perimeter += math.dist(current, next_point)
    return perimeter


def _validate_polygon_points(points):
    if not isinstance(points, list) or len(points) < 3:
        raise ValueError('points debe ser una lista de al menos 3 puntos')

    valid_points = []
    for point in points:
        if not isinstance(point, list) or len(point) != 2:
            raise ValueError('cada punto debe tener dos coordenadas')
        if not all(_is_finite_number(coordinate) for coordinate in point):
            raise ValueError('las coordenadas deben ser numeros finitos')
        valid_points.append([float(point[0]), float(point[1])])

    return valid_points


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )
