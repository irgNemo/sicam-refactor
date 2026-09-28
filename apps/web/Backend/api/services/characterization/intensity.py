from PIL import Image

from .raster import rasterize_object


def load_grayscale_image(image_path):
    with Image.open(image_path) as image:
        return image.convert('L')


def mean_gray_intensity(points, grayscale_image):
    if grayscale_image is None:
        return None

    raster = rasterize_object(points, grayscale_image)
    values = [value for value, inside in zip(raster.gray, raster.mask) if inside]
    return sum(values) / len(values) / 255 if values else None


def points_fit_image(points, grayscale_image):
    if grayscale_image is None:
        return False

    width, height = grayscale_image.size
    for x, y in points:
        if x < 0 or y < 0 or x >= width or y >= height:
            return False
    return True
