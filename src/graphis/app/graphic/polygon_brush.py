"""Local circular editing of polygon exterior boundaries."""

from shapely.geometry import Point, Polygon, box


def brush_polygon_boundary(coordinates, center, radius, mode, image_width, image_height):
    """Return a modified exterior, or None when contact or topology rules prevent an edit."""
    if mode not in {"expand", "shrink"}:
        raise ValueError("Polygon broom mode must be expand or shrink.")
    polygon = Polygon(coordinates)
    point = Point(center)
    if not polygon.is_valid or radius <= 0 or polygon.exterior.distance(point) >= radius:
        return None
    brush = point.buffer(radius, quad_segs=16)
    result = polygon.union(brush) if mode == "expand" else polygon.difference(brush)
    result = result.intersection(box(0, 0, image_width, image_height))
    # Overlapping brush circles otherwise accumulate hundreds of almost collinear
    # vertices. Metadata validation compares segment pairs, so retaining those
    # subpixel details makes saving a stroke progressively slower.
    result = result.simplify(0.15, preserve_topology=True)
    # A border brush must not split a region, create holes, or delete its geometry.
    if (
        result.geom_type != "Polygon" or result.is_empty or not result.is_valid
        or result.area < 1 or result.interiors or result.equals(polygon)
    ):
        return None
    return [list(point) for point in result.exterior.coords[:-1]]
