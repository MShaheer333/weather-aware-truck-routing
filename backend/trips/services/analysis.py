"""Orchestrates one trip analysis: routes -> checkpoints -> weather -> risk -> ranking -> heatmap."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from django.conf import settings

from ..domain import AnalyzedRoute, Checkpoint, RiskLevel, Route, RouteMetrics
from ..exceptions import InvalidRequest
from . import geo, recommendation, risk, routing, weather

HEATMAP_MIN_SPACING_MILES = 25.0
ALLOWED_INTERVALS = (10, 25, 50)


@dataclass
class HeatmapPoint:
    lat: float
    lon: float
    wind: list[float]
    rain: list[float]
    snow: list[float]
    levels: list[int]


@dataclass
class AnalysisResult:
    departure: datetime
    load_lb: float
    interval_miles: int
    routes: list[AnalyzedRoute]  # best-first
    recommendation: str
    heatmap_points: list[HeatmapPoint]
    heatmap_hours: int
    warnings: list[str] = field(default_factory=list)


def analyze(
    origin: geo.LatLon,
    destination: geo.LatLon,
    departure: datetime,
    load_lb: float,
    interval_miles: int,
) -> AnalysisResult:
    departure = _validate_departure(departure)
    if interval_miles not in ALLOWED_INTERVALS:
        raise InvalidRequest(f"Checkpoint interval must be one of {ALLOWED_INTERVALS} miles.")

    routes = routing.fetch_routes(origin, destination)

    checkpoint_plans = {r.index: geo.checkpoint_distances(r.distance_miles, interval_miles) for r in routes}
    heatmap_plans = {r.index: _heatmap_distances(r) for r in routes}

    all_points = [
        geo.point_at(r.coordinates, r.cum_miles, d)
        for r in routes
        for d in (*checkpoint_plans[r.index], *heatmap_plans[r.index])
    ]
    horizon = settings.FORECAST_HORIZON_HOURS
    longest = max(r.duration_seconds for r in routes)
    window_end = departure + timedelta(seconds=max(longest, horizon * 3600)) + timedelta(hours=1)
    forecasts = weather.fetch_forecasts(all_points, departure.date(), window_end.date())

    warnings: list[str] = []
    if any(f.end < window_end - timedelta(hours=1) for f in forecasts.values()):
        warnings.append("Forecast data ends before the end of the trip window; the last available value is held.")

    analyzed = [
        _analyze_route(r, checkpoint_plans[r.index], departure, load_lb, forecasts) for r in routes
    ]
    ranked = recommendation.rank_routes(analyzed)
    best = ranked[0]
    explanation = recommendation.explain(best, ranked[1:], _route_name)
    if best.metrics.miles_by_level.get(RiskLevel.NO_TRAVEL, 0) > 0:
        warnings.append(
            "Every route has stretches where travel is prohibited at the forecast times. "
            "Consider delaying departure or reducing the load."
        )
    if len(routes) < settings.ROUTE_OPTIONS:
        warnings.append(f"Only {len(routes)} distinct route(s) could be generated for this trip.")

    return AnalysisResult(
        departure=departure,
        load_lb=load_lb,
        interval_miles=interval_miles,
        routes=ranked,
        recommendation=explanation,
        heatmap_points=_build_heatmap(routes, heatmap_plans, forecasts, departure, load_lb, horizon),
        heatmap_hours=horizon + 1,
        warnings=warnings,
    )


def route_name(index: int) -> str:
    return f"Route {chr(ord('A') + index)}"


def _route_name(a: AnalyzedRoute) -> str:
    return route_name(a.route.index)


# --------------------------------------------------------------------------------------------------
def _validate_departure(departure: datetime) -> datetime:
    if departure.tzinfo is None:
        departure = departure.replace(tzinfo=timezone.utc)
    departure = departure.astimezone(timezone.utc)
    now = datetime.now(timezone.utc)
    if departure < now - timedelta(days=1):
        raise InvalidRequest("Departure time cannot be more than a day in the past.")
    if departure > now + timedelta(days=settings.MAX_DEPARTURE_DAYS_AHEAD):
        raise InvalidRequest(
            f"Departure must be within the next {settings.MAX_DEPARTURE_DAYS_AHEAD} days (forecast range)."
        )
    return departure


def _heatmap_distances(route: Route) -> list[float]:
    spacing = max(HEATMAP_MIN_SPACING_MILES, route.distance_miles / settings.HEATMAP_MAX_POINTS_PER_ROUTE)
    return geo.checkpoint_distances(route.distance_miles, spacing)


def _analyze_route(
    route: Route,
    distances: list[float],
    departure: datetime,
    load_lb: float,
    forecasts: dict[geo.LatLon, weather.ForecastSeries],
) -> AnalyzedRoute:
    owned = geo.segment_ownership(distances)
    checkpoints: list[Checkpoint] = []
    for mile, miles_owned in zip(distances, owned):
        lat, lon = geo.point_at(route.coordinates, route.cum_miles, mile)
        seconds = geo.interpolate_along(route.cum_seconds, route.cum_miles, mile)
        eta = departure + timedelta(seconds=seconds)
        sample = forecasts[weather.grid_key((lat, lon))].at(eta)
        checkpoints.append(Checkpoint(mile, lat, lon, eta, sample, risk.assess(sample, load_lb), miles_owned))
    return AnalyzedRoute(route=route, checkpoints=checkpoints, metrics=_metrics(checkpoints))


def _metrics(checkpoints: list[Checkpoint]) -> RouteMetrics:
    miles = {level: 0.0 for level in RiskLevel}
    for cp in checkpoints:
        miles[cp.risk.level] += cp.owned_miles
    total = sum(miles.values())
    if total > 0:
        avg = sum(int(level) * m for level, m in miles.items()) / total
    else:  # degenerate zero-length route: fall back to the plain mean
        avg = sum(int(cp.risk.level) for cp in checkpoints) / len(checkpoints)
    return RouteMetrics(miles, avg, max(cp.risk.level for cp in checkpoints))


def _build_heatmap(
    routes: list[Route],
    plans: dict[int, list[float]],
    forecasts: dict[geo.LatLon, weather.ForecastSeries],
    departure: datetime,
    load_lb: float,
    horizon: int,
) -> list[HeatmapPoint]:
    """Risk at every corridor point for every hour 0..horizon after departure (one fixed time per hour)."""
    seen: dict[geo.LatLon, HeatmapPoint] = {}
    for route in routes:
        for mile in plans[route.index]:
            lat, lon = geo.point_at(route.coordinates, route.cum_miles, mile)
            key = weather.grid_key((lat, lon))
            if key in seen:
                continue
            wind, rain, snow, levels = [], [], [], []
            for hour in range(horizon + 1):
                sample = forecasts[key].at(departure + timedelta(hours=hour))
                wind.append(round(sample.wind_mph, 1))
                rain.append(round(sample.rain_in_hr, 3))
                snow.append(round(sample.snow_in_hr, 2))
                levels.append(int(risk.assess(sample, load_lb).level))
            seen[key] = HeatmapPoint(round(lat, 4), round(lon, 4), wind, rain, snow, levels)
    return list(seen.values())
