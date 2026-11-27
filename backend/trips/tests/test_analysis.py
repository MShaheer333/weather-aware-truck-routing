"""Core requirement checks: weather is sampled at each checkpoint's *arrival* time, and 3 routes are produced."""
from datetime import datetime, timedelta, timezone
from unittest import mock

from django.core.cache import cache
from django.test import SimpleTestCase

from trips.domain import RiskLevel
from trips.services import analysis, geo, routing, weather

from .test_api import make_route


def hour_floor(dt):
    return dt.replace(minute=0, second=0, microsecond=0)


class ArrivalTimeWeatherTests(SimpleTestCase):
    """A storm that exists only 4-6 h after departure must hit only checkpoints reached in that window."""

    def setUp(self):
        cache.clear()
        self.departure = hour_floor(datetime.now(timezone.utc)) + timedelta(hours=3)
        self.storm = (self.departure + timedelta(hours=4), self.departure + timedelta(hours=6))

    def forecasts(self, points, start_date, end_date):
        start = datetime(start_date.year, start_date.month, start_date.day, tzinfo=timezone.utc)
        hours = (end_date - start_date).days * 24 + 24
        wind = [60.0 if self.storm[0] <= start + timedelta(hours=i) <= self.storm[1] else 5.0 for i in range(hours)]
        series = weather.ForecastSeries(start, wind, [0.0] * hours, [0.0] * hours)
        return {weather.grid_key(p): series for p in points}

    def test_only_checkpoints_reached_during_storm_are_no_travel(self):
        route = make_route(0, minutes=600)  # 10 h drive; ETA after truck-speed factor is checked via cp.eta
        with mock.patch.object(analysis.routing, "fetch_routes", lambda o, d: [route]), \
                mock.patch.object(analysis.weather, "fetch_forecasts", self.forecasts):
            result = analysis.analyze((40, -90), (40, -80), self.departure, 20_000, 10)

        checkpoints = result.routes[0].checkpoints
        inside = [c for c in checkpoints if self.storm[0] + timedelta(minutes=5) < c.eta < self.storm[1] - timedelta(minutes=5)]
        before, after = self.storm[0] - timedelta(hours=1), self.storm[1] + timedelta(hours=1)
        outside = [c for c in checkpoints if c.eta < before or c.eta > after]
        self.assertTrue(inside and outside, "test route should have checkpoints both inside and outside the storm")
        self.assertTrue(all(c.risk.level == RiskLevel.NO_TRAVEL for c in inside))
        self.assertTrue(all(c.risk.level == RiskLevel.LOW for c in outside))

    def test_heatmap_hours_follow_the_forecast(self):
        route = make_route(0, minutes=600)
        with mock.patch.object(analysis.routing, "fetch_routes", lambda o, d: [route]), \
                mock.patch.object(analysis.weather, "fetch_forecasts", self.forecasts):
            result = analysis.analyze((40, -90), (40, -80), self.departure, 20_000, 25)
        levels = result.heatmap_points[0].levels
        self.assertEqual(levels[0], RiskLevel.LOW)
        self.assertEqual(levels[5], RiskLevel.NO_TRAVEL)  # +5 h is mid-storm
        self.assertEqual(levels[8], RiskLevel.LOW)


def raw_route(coords_lonlat, miles):
    meters = miles * geo.METERS_PER_MILE
    n = len(coords_lonlat) - 1
    return {
        "geometry": {"coordinates": coords_lonlat},
        "distance": meters,
        "duration": meters / 25,  # ~56 mph
        "legs": [{"summary": "I-80", "annotation": {"duration": [meters / 25 / n] * n}}],
    }


def line(points, per_leg=60):
    out = []
    for (la1, lo1), (la2, lo2) in zip(points, points[1:]):
        out += [[lo1 + (lo2 - lo1) * i / per_leg, la1 + (la2 - la1) * i / per_leg] for i in range(per_leg)]
    out.append([points[-1][1], points[-1][0]])
    return out


class RouteGenerationTests(SimpleTestCase):
    ORIGIN, DEST = (40.0, -90.0), (40.0, -80.0)

    def fake_osrm(self, waypoints, alternatives):
        if len(waypoints) == 2:  # OSRM only offers one route
            return [raw_route(line(waypoints), 530)]
        pts = [*waypoints]
        miles = sum(geo.haversine_miles(a, b) for a, b in zip(pts, pts[1:]))
        return [raw_route(line(pts), miles)]

    def test_fills_up_to_three_distinct_routes_when_osrm_returns_one(self):
        with mock.patch.object(routing, "_osrm", self.fake_osrm):
            routes = routing.fetch_routes(self.ORIGIN, self.DEST)
        self.assertEqual(len(routes), 3)
        self.assertEqual([r.index for r in routes], [0, 1, 2])
        durations = [r.duration_seconds for r in routes]
        self.assertEqual(durations, sorted(durations))
        for a in routes:
            for b in routes:
                if a is not b:
                    self.assertLess(geo.overlap_ratio(a.coordinates, b.coordinates), routing.DUPLICATE_OVERLAP)

    def test_truck_speed_factor_slows_eta(self):
        with mock.patch.object(routing, "_osrm", lambda w, alternatives: [raw_route(line(w), 530)]), \
                self.settings(TRUCK_SPEED_FACTOR=0.5, ROUTE_OPTIONS=1):
            route = routing.fetch_routes(self.ORIGIN, self.DEST)[0]
        self.assertAlmostEqual(route.duration_seconds, 530 * geo.METERS_PER_MILE / 25 / 0.5, delta=1)

    def test_rejects_origin_equal_destination(self):
        with self.assertRaises(routing.NoRouteFound):
            routing.fetch_routes(self.ORIGIN, self.ORIGIN)
