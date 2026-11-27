"""Pure geometry helpers. Coordinates are (lat, lon) tuples; distances are statute miles."""
from __future__ import annotations

import math
from bisect import bisect_right
from collections.abc import Sequence

EARTH_RADIUS_MILES = 3958.8
METERS_PER_MILE = 1609.344

LatLon = tuple[float, float]


def haversine_miles(a: LatLon, b: LatLon) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH_RADIUS_MILES * math.asin(math.sqrt(h))


def cumulative_miles(coords: Sequence[LatLon]) -> list[float]:
    """Running distance along the polyline; element i is the distance from coords[0] to coords[i]."""
    out = [0.0]
    for prev, cur in zip(coords, coords[1:]):
        out.append(out[-1] + haversine_miles(prev, cur))
    return out


def _locate(cum: Sequence[float], distance: float) -> tuple[int, float]:
    """Index i and fraction f such that `distance` lies at cum[i] + f * (cum[i+1] - cum[i])."""
    if distance <= cum[0]:
        return 0, 0.0
    if distance >= cum[-1]:
        return len(cum) - 2, 1.0
    i = bisect_right(cum, distance) - 1
    span = cum[i + 1] - cum[i]
    return i, 0.0 if span == 0 else (distance - cum[i]) / span


def interpolate_along(values: Sequence[float], cum: Sequence[float], distance: float) -> float:
    """Linearly interpolate `values` (aligned with `cum`) at `distance` along the line."""
    if len(cum) == 1:
        return values[0]
    i, f = _locate(cum, distance)
    return values[i] + (values[i + 1] - values[i]) * f


def point_at(coords: Sequence[LatLon], cum: Sequence[float], distance: float) -> LatLon:
    if len(coords) == 1:
        return coords[0]
    i, f = _locate(cum, distance)
    a, b = coords[i], coords[i + 1]
    return (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)


def checkpoint_distances(total_miles: float, interval_miles: float) -> list[float]:
    """0, interval, 2*interval ... and always the final point (destination)."""
    if total_miles <= 0:
        return [0.0]
    n = int(total_miles // interval_miles)
    points = [i * interval_miles for i in range(n + 1)]
    if total_miles - points[-1] > 1e-6:
        points.append(total_miles)
    else:
        points[-1] = total_miles
    return points


def segment_ownership(distances: Sequence[float]) -> list[float]:
    """Miles of road each checkpoint is responsible for.

    A checkpoint represents the stretch of road halfway back to the previous checkpoint and halfway
    forward to the next one, so the owned miles always sum to the full route length.
    """
    n = len(distances)
    if n == 1:
        return [0.0]
    owned = []
    for i, d in enumerate(distances):
        start = d if i == 0 else (distances[i - 1] + d) / 2
        end = d if i == n - 1 else (d + distances[i + 1]) / 2
        owned.append(end - start)
    return owned


def simplify(coords: Sequence[LatLon], tolerance_miles: float = 0.03) -> list[LatLon]:
    """Iterative Ramer-Douglas-Peucker. Keeps map payloads small without visibly changing the line."""
    n = len(coords)
    if n < 3:
        return list(coords)
    lat0 = math.radians(coords[0][0])
    kx = math.cos(lat0) * 69.172  # miles per degree of longitude near the route
    ky = 69.0
    pts = [(c[1] * kx, c[0] * ky) for c in coords]
    keep = [False] * n
    keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        lo, hi = stack.pop()
        (x1, y1), (x2, y2) = pts[lo], pts[hi]
        dx, dy = x2 - x1, y2 - y1
        norm = math.hypot(dx, dy)
        worst, idx = -1.0, -1
        for i in range(lo + 1, hi):
            px, py = pts[i]
            if norm == 0:
                dist = math.hypot(px - x1, py - y1)
            else:
                dist = abs(dy * (px - x1) - dx * (py - y1)) / norm
            if dist > worst:
                worst, idx = dist, i
        if worst > tolerance_miles:
            keep[idx] = True
            stack.append((lo, idx))
            stack.append((idx, hi))
    return [c for c, k in zip(coords, keep) if k]


def overlap_ratio(candidate: Sequence[LatLon], other: Sequence[LatLon], threshold_miles: float = 1.0, samples: int = 40) -> float:
    """Fraction of sampled candidate points that lie within `threshold_miles` of `other` (vertex-based)."""
    if not candidate or not other:
        return 0.0
    step = max(1, len(candidate) // samples)
    probe = candidate[::step]
    # Grid-bucket the other line so each probe only checks nearby vertices.
    cell = 0.05  # degrees (~3.5 mi)
    grid: dict[tuple[int, int], list[LatLon]] = {}
    for p in other:
        grid.setdefault((int(p[0] / cell), int(p[1] / cell)), []).append(p)
    near = 0
    for p in probe:
        ci, cj = int(p[0] / cell), int(p[1] / cell)
        found = False
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                for q in grid.get((ci + di, cj + dj), ()):
                    if haversine_miles(p, q) <= threshold_miles:
                        found = True
                        break
                if found:
                    break
            if found:
                break
        near += found
    return near / len(probe)


def offset_point(origin: LatLon, bearing_deg: float, miles: float) -> LatLon:
    """Destination point given a start, a bearing and a distance (spherical earth)."""
    lat1, lon1 = math.radians(origin[0]), math.radians(origin[1])
    brg = math.radians(bearing_deg)
    ang = miles / EARTH_RADIUS_MILES
    lat2 = math.asin(math.sin(lat1) * math.cos(ang) + math.cos(lat1) * math.sin(ang) * math.cos(brg))
    lon2 = lon1 + math.atan2(math.sin(brg) * math.sin(ang) * math.cos(lat1), math.cos(ang) - math.sin(lat1) * math.sin(lat2))
    return (math.degrees(lat2), (math.degrees(lon2) + 540) % 360 - 180)


def bearing_degrees(a: LatLon, b: LatLon) -> float:
    lat1, lat2 = math.radians(a[0]), math.radians(b[0])
    dlon = math.radians(b[1] - a[1])
    y = math.sin(dlon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    return (math.degrees(math.atan2(y, x)) + 360) % 360
