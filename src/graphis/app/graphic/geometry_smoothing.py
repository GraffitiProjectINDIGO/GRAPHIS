"""Corner rounding and vertex reduction for polygon rings and open lines."""

import heapq
import math

from shapely.geometry import LineString, Polygon


def reduce_vertices(coordinates, closed):
    """Remove up to 10% of vertices, preferring the least significant corners."""
    points = [list(point) for point in coordinates]
    if closed and len(points) > 1 and points[0] == points[-1]:
        points.pop()
    count = len(points)
    minimum = 3 if closed else 2
    if count < minimum:
        raise ValueError("Too few vertices to reduce this geometry.")
    target = max(minimum, math.ceil(count * 0.9))
    previous = [(i - 1) % count for i in range(count)]
    following = [(i + 1) % count for i in range(count)]
    alive = [True] * count
    versions = [0] * count
    heap = []

    def queue(index):
        if not alive[index] or (not closed and index in {0, count - 1}):
            return
        a, b, c = points[previous[index]], points[index], points[following[index]]
        area = abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))
        versions[index] += 1
        heapq.heappush(heap, (area, index, versions[index]))

    for index in range(count):
        queue(index)
    remaining = count
    original = Polygon(points) if closed else LineString(points)
    if not original.is_valid:
        raise ValueError("Cannot reduce invalid geometry.")
    while remaining > target and heap:
        _, index, version = heapq.heappop(heap)
        if not alive[index] or version != versions[index]:
            continue
        candidate = [point for i, point in enumerate(points) if alive[i] and i != index]
        geometry = Polygon(candidate) if closed else LineString(candidate)
        if not geometry.is_valid or geometry.is_empty or (original.is_simple and not geometry.is_simple):
            continue
        alive[index] = False
        remaining -= 1
        left, right = previous[index], following[index]
        following[left], previous[right] = right, left
        queue(left)
        queue(right)
    return [point for index, point in enumerate(points) if alive[index]]


def smooth_vertices(coordinates, closed):
    """Apply two Chaikin passes, preserving open endpoints and removing subpixel detail."""
    points = [list(point) for point in coordinates]
    if closed and len(points) > 1 and points[0] == points[-1]:
        points.pop()
    if len(points) < (3 if closed else 2):
        raise ValueError("Too few vertices to smooth this geometry.")
    for _ in range(2):
        rounded = [] if closed else [points[0]]
        for index in range(len(points) if closed else len(points) - 1):
            start, end = points[index], points[(index + 1) % len(points)]
            rounded.extend([
                [0.75 * start[axis] + 0.25 * end[axis] for axis in range(2)],
                [0.25 * start[axis] + 0.75 * end[axis] for axis in range(2)],
            ])
        if not closed:
            rounded.append(points[-1])
        points = rounded
    geometry = Polygon(points) if closed else LineString(points)
    if not geometry.is_valid or geometry.is_empty:
        raise ValueError("Smoothing would create invalid geometry.")
    geometry = geometry.simplify(0.15, preserve_topology=True)
    return [list(point) for point in (geometry.exterior.coords[:-1] if closed else geometry.coords)]
