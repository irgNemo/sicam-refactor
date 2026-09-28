"""Object-local Pillow masks; coordinates and edge inclusion match SALIVA 2.0."""

from dataclasses import dataclass

from PIL import Image, ImageDraw


@dataclass(frozen=True)
class ObjectRaster:
    width: int
    height: int
    mask: bytes
    gray: bytes | None


def rasterize_object(points, grayscale_image=None):
    # Pillow truncates polygon vertices to integers before rasterization. Do
    # that in original coordinates, then translate: fractional vertices must
    # not change their rounding when the bounding box is cropped.
    vertices = [(int(x), int(y)) for x, y in points]
    left = min(x for x, _ in vertices)
    top = min(y for _, y in vertices)
    right = max(x for x, _ in vertices) + 1
    bottom = max(y for _, y in vertices) + 1
    if grayscale_image is not None:
        left, top = max(0, left), max(0, top)
        right = min(grayscale_image.width, right)
        bottom = min(grayscale_image.height, bottom)
    width, height = max(0, right - left), max(0, bottom - top)
    if not width or not height:
        return ObjectRaster(0, 0, b'', b'' if grayscale_image else None)
    mask = Image.new('L', (width, height), 0)
    ImageDraw.Draw(mask).polygon(
        [(x - left, y - top) for x, y in vertices], outline=1, fill=1,
    )
    gray = (
        grayscale_image.crop((left, top, right, bottom)).tobytes()
        if grayscale_image is not None else None
    )
    return ObjectRaster(width, height, mask.tobytes(), gray)
