"""Convert segmentation masks to valid exterior polygon boundaries."""

import cv2
import numpy as np
from shapely.geometry import Polygon, box


def _smooth_exterior(polygon, smoothing_pixels=5.0):
    """Smooth an evenly sampled closed boundary without introducing invalid geometry."""
    points = np.asarray(polygon.exterior.coords)
    distances = np.concatenate(([0.0], np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))))
    count = max(400, min(8000, int(np.ceil(distances[-1]))))
    samples = np.linspace(0, distances[-1], count, endpoint=False)
    points = np.column_stack([np.interp(samples, distances, points[:, axis]) for axis in range(2)])
    if smoothing_pixels > 0:
        sigma = smoothing_pixels * count / distances[-1]
        radius = min(count // 4, max(1, int(np.ceil(3 * sigma))))
        offsets = np.arange(-radius, radius + 1)
        weights = np.exp(-0.5 * (offsets / sigma) ** 2)
        weights /= weights.sum()
        wrapped = np.pad(points, ((radius, radius), (0, 0)), mode="wrap")
        points = np.column_stack([np.convolve(wrapped[:, axis], weights, mode="valid") for axis in range(2)])
    smoothed = Polygon(points)
    return smoothed if smoothed.is_valid and smoothed.area > 0 else polygon


def mask_to_polygons(
    mask, minimum_pixels=300, maximum_points=400, buffer_pixels=20.0, smoothing_pixels=5.0, largest_only=False
):
    """Smooth and expand qualifying exterior rings, clipping the buffer to the image.

    With ``largest_only``, only the resulting polygon with the largest area is returned.
    """
    mask = np.asarray(mask, dtype=np.uint8)
    if mask.ndim != 2:
        raise ValueError("The AI mask must be two-dimensional.")
    if buffer_pixels < 0 or smoothing_pixels < 0:
        raise ValueError("Polygon buffer and smoothing must be nonnegative.")
    image_height, image_width = mask.shape
    image_bounds = box(0, 0, image_width - 1, image_height - 1)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    polygons = []
    for label in range(1, count):
        if stats[label, cv2.CC_STAT_AREA] <= minimum_pixels:
            continue
        x, y, width, height = stats[label, :4]
        component = (labels[y:y + height, x:x + width] == label).astype(np.uint8)
        contours, _ = cv2.findContours(component, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            points = contour.reshape(-1, 2) + [x, y]
            if len(points) < 3:
                continue
            # Pixel contours can touch themselves at diagonal connections.
            geometry = Polygon(points).buffer(0)
            parts = list(geometry.geoms) if geometry.geom_type == "MultiPolygon" else [geometry]
            for part in parts:
                if part.is_empty or part.area <= 0:
                    continue
                exterior = _smooth_exterior(Polygon(part.exterior), smoothing_pixels)
                exterior = exterior.buffer(buffer_pixels).intersection(image_bounds)
                if exterior.is_empty or exterior.area <= 0:
                    continue
                exterior = Polygon(exterior.exterior)
                simplified = exterior
                if len(exterior.exterior.coords) - 1 > maximum_points:
                    low, high = 0.0, float(max(width, height))
                    for _ in range(32):
                        tolerance = (low + high) / 2
                        candidate = exterior.simplify(tolerance, preserve_topology=True)
                        if len(candidate.exterior.coords) - 1 > maximum_points:
                            low = tolerance
                        else:
                            high = tolerance
                            simplified = candidate
                polygons.append((simplified.area, [list(point) for point in simplified.exterior.coords[:-1]]))
    if largest_only and polygons:
        return [max(polygons, key=lambda item: item[0])[1]]
    return [coordinates for _area, coordinates in polygons]
