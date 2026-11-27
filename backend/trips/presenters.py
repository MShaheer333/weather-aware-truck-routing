"""Turn analysis results into the JSON the frontend consumes."""
from __future__ import annotations

from bisect import bisect_left, bisect_right

from .domain import AnalyzedRoute, RiskLevel
from .services import geo
from .services.analysis import AnalysisResult, route_name

LEVEL_KEYS = {level: level.name.lower() for level in RiskLevel}


def present(result: AnalysisResult, request_echo: dict) -> dict:
    best = result.routes[0]
    return {
        "request": request_echo,
        "recommended_route_id": best.route.index,
        "recommendation": result.recommendation,
        "routes": [_route(a) for a in sorted(result.routes, key=lambda a: a.route.index)],
        "heatmap": {
            "hours": result.heatmap_hours,
            "start": result.departure.isoformat(),
            "points": [
                {"lat": p.lat, "lon": p.lon, "levels": p.levels, "wind": p.wind, "rain": p.rain, "snow": p.snow}
                for p in result.heatmap_points
            ],
        },
        "warnings": result.warnings,
    }


def _route(a: AnalyzedRoute) -> dict:
    r = a.route
    miles = {LEVEL_KEYS[level]: round(a.metrics.miles_by_level.get(level, 0.0), 1) for level in RiskLevel}
    return {
        "id": r.index,
        "name": route_name(r.index),
        "summary": r.summary,
        "rank": a.rank,
        "is_recommended": a.rank == 1,
        "distance_miles": round(r.distance_miles, 1),
        "duration_seconds": round(r.duration_seconds),
        "departure": a.checkpoints[0].eta.isoformat(),
        "arrival": a.checkpoints[-1].eta.isoformat(),
        "metrics": {
            "miles_by_level": miles,
            "avg_risk": round(a.metrics.avg_risk, 2),
            "max_level": int(a.metrics.max_level),
            "max_level_label": a.metrics.max_level.label,
        },
        "segments": _segments(a),
        "checkpoints": [
            {
                "mile": round(c.mile, 1),
                "lat": round(c.lat, 5),
                "lon": round(c.lon, 5),
                "eta": c.eta.isoformat(),
                "weather": {
                    "wind_mph": round(c.weather.wind_mph, 1),
                    "rain_in_hr": round(c.weather.rain_in_hr, 3),
                    "snow_in_hr": round(c.weather.snow_in_hr, 2),
                },
                "risk": {
                    "level": int(c.risk.level),
                    "label": c.risk.level.label,
                    "wind": int(c.risk.wind_level),
                    "rain": int(c.risk.rain_level),
                    "snow": int(c.risk.snow_level),
                    "load_rule": c.risk.load_rule,
                },
            }
            for c in a.checkpoints
        ],
    }


def _segments(a: AnalyzedRoute) -> list[dict]:
    """The route line split into runs of equal risk, so the map can colour it without extra logic."""
    r = a.route
    distances = [c.mile for c in a.checkpoints]
    owned = geo.segment_ownership(distances)
    runs: list[list] = []  # [level, start_mile, end_mile]
    cursor = 0.0
    for cp, length in zip(a.checkpoints, owned):
        start = cursor
        end = cursor + length
        cursor = end
        if length <= 0:
            continue
        level = int(cp.risk.level)
        if runs and runs[-1][0] == level:
            runs[-1][2] = end
        else:
            runs.append([level, start, end])
    if not runs:
        runs = [[int(a.checkpoints[0].risk.level), 0.0, r.distance_miles]]
    runs[-1][2] = r.distance_miles

    out = []
    for level, start, end in runs:
        lo = bisect_right(r.cum_miles, start)
        hi = bisect_left(r.cum_miles, end)
        first = geo.point_at(r.coordinates, r.cum_miles, start)
        last = geo.point_at(r.coordinates, r.cum_miles, end)
        path = [first, *r.coordinates[lo:hi], last]
        path = geo.simplify(path)
        out.append({"level": level, "path": [[round(lat, 5), round(lon, 5)] for lat, lon in path]})
    return out
