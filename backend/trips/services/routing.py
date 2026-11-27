"""Route generation using OSRM.

OSRM's `alternatives` option often returns fewer than the 3 routes we need, so when it does we
create additional candidates by routing through a via-point pushed sideways from the middle of
the fastest route, then keep only candidates that are genuinely different and not absurdly long.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import requests
from django.conf import settings

from ..domain import Route
from ..exceptions import NoRouteFound, UpstreamError
from . import geo, http

DUPLICATE_OVERLAP = 0.90  # candidate sharing >= 90% of its length with a kept route is a duplicate
MAX_DETOUR_FACTOR = 1.75  # discard via-routes slower than 1.75x the fastest route


def fetch_routes(origin: geo.LatLon, destination: geo.LatLon, count: int | None = None) -> list[Route]:
    count = count or settings.ROUTE_OPTIONS
    if geo.haversine_miles(origin, destination) < 0.5:
        raise NoRouteFound("Origin and destination are too close together.")

    raw = _osrm([origin, destination], alternatives=count)
    kept = _dedupe([_build_route(r) for r in raw], [])

    if len(kept) < count:
        kept = _dedupe(_via_candidates(origin, destination, kept[0]), kept)

    kept = kept[:count]
    kept.sort(key=lambda r: r.duration_seconds)
    for i, route in enumerate(kept):
        route.index = i
    return kept


# --------------------------------------------------------------------------------------------------
def _osrm(waypoints: list[geo.LatLon], alternatives: int | bool) -> list[dict]:
    coords = ";".join(f"{lon:.6f},{lat:.6f}" for lat, lon in waypoints)
    params = {
        "alternatives": str(alternatives).lower() if isinstance(alternatives, bool) else alternatives,
        "overview": "full",
        "geometries": "geojson",
        "steps": "true",
        "annotations": "distance,duration",
    }
    try:
        data = http.get_json(f"{settings.OSRM_BASE_URL}/route/v1/driving/{coords}", params)
    except requests.HTTPError as exc:
        # OSRM answers 400 with a JSON body for unroutable input (e.g. across an ocean).
        if exc.response is not None and exc.response.status_code == 400:
            raise NoRouteFound("No drivable route exists between those locations.") from exc
        raise UpstreamError("Routing service is unavailable. Please try again.") from exc
    except requests.RequestException as exc:
        raise UpstreamError("Routing service is unavailable. Please try again.") from exc
    if data.get("code") != "Ok" or not data.get("routes"):
        raise NoRouteFound("No drivable route exists between those locations.")
    return data["routes"]


def _build_route(raw: dict) -> Route:
    coords = [(lat, lon) for lon, lat in raw["geometry"]["coordinates"]]
    cum_miles = geo.cumulative_miles(coords)
    osrm_miles = raw["distance"] / geo.METERS_PER_MILE
    if cum_miles[-1] > 0:  # align polyline length with the routing engine's own distance
        scale = osrm_miles / cum_miles[-1]
        cum_miles = [m * scale for m in cum_miles]

    durations: list[float] = []
    for leg in raw["legs"]:
        durations.extend(leg.get("annotation", {}).get("duration", []))
    if len(durations) == len(coords) - 1:
        cum_seconds = [0.0]
        for d in durations:
            cum_seconds.append(cum_seconds[-1] + d)
    else:  # annotation unavailable: assume constant speed
        total = raw["duration"]
        cum_seconds = [total * (m / cum_miles[-1]) if cum_miles[-1] else 0.0 for m in cum_miles]

    factor = settings.TRUCK_SPEED_FACTOR
    cum_seconds = [s / factor for s in cum_seconds]

    names: list[str] = []
    for leg in raw["legs"]:
        for part in filter(None, (p.strip() for p in leg.get("summary", "").split(","))):
            if part not in names:
                names.append(part)
    return Route(index=0, coordinates=coords, cum_miles=cum_miles, cum_seconds=cum_seconds, summary=", ".join(names[:3]))


def _dedupe(candidates: list[Route], existing: list[Route]) -> list[Route]:
    kept = list(existing)
    for cand in candidates:
        if any(geo.overlap_ratio(cand.coordinates, k.coordinates) >= DUPLICATE_OVERLAP for k in kept):
            continue
        kept.append(cand)
    return kept


def _via_candidates(origin: geo.LatLon, destination: geo.LatLon, base: Route) -> list[Route]:
    mid = geo.point_at(base.coordinates, base.cum_miles, base.distance_miles / 2)
    bearing = geo.bearing_degrees(origin, destination)
    plans = []
    for fraction in (0.12, 0.25):
        offset = max(10.0, base.distance_miles * fraction)
        for side in (90, -90):
            plans.append(geo.offset_point(mid, bearing + side, offset))

    def run(via: geo.LatLon) -> Route | None:
        try:
            raw = _osrm([origin, via, destination], alternatives=False)
        except (UpstreamError, NoRouteFound):
            return None
        route = _build_route(raw[0])
        return route if route.duration_seconds <= base.duration_seconds * MAX_DETOUR_FACTOR else None

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(run, plans))
    # Smallest detours first so near-duplicates of larger ones are dropped, not the reverse.
    return sorted((r for r in results if r), key=lambda r: r.duration_seconds)
