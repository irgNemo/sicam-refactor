export const ZOOM_MIN = 1;
export const ZOOM_MAX = 8;
export const ZOOM_STEP = 0.25;

export function calculateImagePanLimits(renderedSize, imageZoom, imageRotation) {
  const width = renderedSize.width;
  const height = renderedSize.height;

  if (!width || !height || imageZoom <= 1) {
    return { maxX: 0, maxY: 0 };
  }

  const rotation = ((imageRotation % 360) + 360) % 360;
  const rotatedSideways = rotation === 90 || rotation === 270;
  const transformedWidth = (rotatedSideways ? height : width) * imageZoom;
  const transformedHeight = (rotatedSideways ? width : height) * imageZoom;

  return {
    maxX: Math.max(0, Math.round((transformedWidth - width) / 2)),
    maxY: Math.max(0, Math.round((transformedHeight - height) / 2)),
  };
}

export function calculateOverlayContainment(naturalSize, renderedSize) {
  const naturalWidth = naturalSize.width;
  const naturalHeight = naturalSize.height;
  const containerWidth = renderedSize.width;
  const containerHeight = renderedSize.height;

  if (
    !naturalWidth ||
    !naturalHeight ||
    !containerWidth ||
    !containerHeight
  ) {
    return {
      canProject: false,
      displayedSize: { width: 0, height: 0 },
      offsetX: 0,
      offsetY: 0,
      scaleX: null,
      scaleY: null,
    };
  }

  const imageAspect = naturalWidth / naturalHeight;
  const containerAspect = containerWidth / containerHeight;
  let displayedImageWidth;
  let displayedImageHeight;
  let offsetX;
  let offsetY;

  if (containerAspect > imageAspect) {
    displayedImageHeight = containerHeight;
    displayedImageWidth = containerHeight * imageAspect;
    offsetX = (containerWidth - displayedImageWidth) / 2;
    offsetY = 0;
  } else {
    displayedImageWidth = containerWidth;
    displayedImageHeight = containerWidth / imageAspect;
    offsetX = 0;
    offsetY = (containerHeight - displayedImageHeight) / 2;
  }

  return {
    canProject: true,
    displayedSize: {
      width: Math.round(displayedImageWidth),
      height: Math.round(displayedImageHeight),
    },
    offsetX,
    offsetY,
    scaleX: displayedImageWidth / naturalWidth,
    scaleY: displayedImageHeight / naturalHeight,
  };
}

export function getValidPolygonPoints(points) {
  if (!Array.isArray(points)) return [];

  return points.filter(point => (
    Array.isArray(point) &&
    point.length >= 2 &&
    Number.isFinite(Number(point[0])) &&
    Number.isFinite(Number(point[1]))
  ));
}

export function scalePointToOverlay(point, containment) {
  if (!containment.canProject) return null;
  if (!getValidPolygonPoints([point]).length) return null;

  return [
    Math.round(containment.offsetX + Number(point[0]) * containment.scaleX),
    Math.round(containment.offsetY + Number(point[1]) * containment.scaleY),
  ];
}

export function scalePolygonPointsToOverlay(points, containment) {
  return getValidPolygonPoints(points)
    .map(point => scalePointToOverlay(point, containment))
    .filter(Boolean);
}
