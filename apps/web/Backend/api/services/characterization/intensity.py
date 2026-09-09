from PIL import Image, ImageDraw


def load_grayscale_image(image_path):
    with Image.open(image_path) as image:
        return image.convert('L')


def mean_gray_intensity(points, grayscale_image):
    if grayscale_image is None:
        return None

    mask = Image.new('L', grayscale_image.size, 0)
    ImageDraw.Draw(mask).polygon(
        [tuple(point) for point in points],
        outline=1,
        fill=1,
    )

    image_pixels = grayscale_image.load()
    mask_pixels = mask.load()
    width, height = grayscale_image.size
    values = []

    for y in range(height):
        for x in range(width):
            if mask_pixels[x, y]:
                values.append(image_pixels[x, y])

    if not values:
        return None

    return sum(values) / len(values) / 255


def points_fit_image(points, grayscale_image):
    if grayscale_image is None:
        return False

    width, height = grayscale_image.size
    for x, y in points:
        if x < 0 or y < 0 or x >= width or y >= height:
            return False
    return True
