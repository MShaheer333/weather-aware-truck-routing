from datetime import datetime, timedelta, timezone
from unittest import mock

from django.core.cache import cache
from rest_framework.test import APISimpleTestCase

from trips.domain import Route
from trips.services import geo, weather


def make_route(index, lat_offset=0.0, minutes=600):
    coords = [(40.0 + lat_offset, -90.0 + i * 0.1) for i in range(0, 101)]  # ~530 mi west->east line
    cum = geo.cumulative_miles(coords)
    secs = [minutes * 60 * m / cum[-1] for m in cum]
    return Route(index, coords, cum, secs, summary=f"I-{index}")


def fake_forecasts(points, start_date, end_date, wind=10.0):
    start = datetime(start_date.year, start_date.month, start_date.day, tzinfo=timezone.utc)
    hours = (end_date - start_date).days * 24 + 24
    series = weather.ForecastSeries(start, [wind] * hours, [0.0] * hours, [0.0] * hours)
    return {weather.grid_key(p): series for p in points}


PAYLOAD = {
    "origin": {"lat": 40.0, "lon": -90.0, "label": "A"},
    "destination": {"lat": 40.0, "lon": -80.0, "label": "B"},
    "load_weight_lb": 35000,
    "checkpoint_interval_miles": 50,
}


def payload(**overrides):
    departure = (datetime.now(timezone.utc) + timedelta(hours=3)).isoformat()
    return {**PAYLOAD, "departure_time": departure, **overrides}


def _routes(origin, destination):
    return [make_route(0), make_route(1, 0.5, 650), make_route(2, 1.0, 700)]


@mock.patch("trips.services.analysis.routing.fetch_routes", _routes)
class AnalyzeApiTests(APISimpleTestCase):
    def setUp(self):
        cache.clear()

    def post(self, body, wind=10.0):
        patched = lambda p, s, e: fake_forecasts(p, s, e, wind)  # noqa: E731
        with mock.patch("trips.services.analysis.weather.fetch_forecasts", patched):
            return self.client.post("/api/analyze/", body, format="json")

    def test_happy_path_shape(self):
        res = self.post(payload())
        self.assertEqual(res.status_code, 200, res.content)
        data = res.json()
        self.assertEqual(len(data["routes"]), 3)
        self.assertEqual(data["recommended_route_id"], 0)  # equal risk -> fastest
        route = data["routes"][0]
        self.assertEqual(route["checkpoints"][0]["mile"], 0.0)
        self.assertAlmostEqual(route["checkpoints"][-1]["mile"], route["distance_miles"], delta=0.1)
        self.assertAlmostEqual(route["metrics"]["miles_by_level"]["low"], route["distance_miles"], delta=0.2)
        self.assertEqual(data["heatmap"]["hours"], 49)
        self.assertTrue(all(len(p["levels"]) == 49 for p in data["heatmap"]["points"]))

    def test_checkpoint_etas_increase(self):
        etas = [c["eta"] for c in self.post(payload()).json()["routes"][0]["checkpoints"]]
        self.assertEqual(etas, sorted(etas))

    def test_heavy_load_in_wind_marks_route_no_travel(self):
        data = self.post(payload(load_weight_lb=45000), wind=50).json()
        self.assertEqual(data["routes"][0]["metrics"]["max_level"], 4)
        self.assertTrue(data["warnings"])

    def test_light_load_same_wind_is_only_severe(self):
        data = self.post(payload(load_weight_lb=20000), wind=50).json()
        self.assertEqual(data["routes"][0]["metrics"]["max_level"], 3)

    def test_validation_errors(self):
        self.assertEqual(self.post(payload(load_weight_lb=-1)).status_code, 400)
        self.assertEqual(self.post(payload(checkpoint_interval_miles=30)).status_code, 400)
        past = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        res = self.post(payload(departure_time=past))
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["error"]["code"], "invalid_request")


class GeocodeApiTests(APISimpleTestCase):
    def test_short_query_returns_empty(self):
        res = self.client.get("/api/geocode/?q=ab")
        self.assertEqual(res.json(), {"results": []})
