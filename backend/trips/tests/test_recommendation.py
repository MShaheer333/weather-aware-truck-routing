from django.test import SimpleTestCase

from trips.domain import AnalyzedRoute, RiskLevel, Route, RouteMetrics
from trips.services import recommendation


def analyzed(index, minutes, no_travel=0.0, severe=0.0, high=0.0, avg=0.0):
    route = Route(index, [(0, 0), (0, 1)], [0, 100], [0, minutes * 60])
    metrics = RouteMetrics({RiskLevel.NO_TRAVEL: no_travel, RiskLevel.SEVERE: severe, RiskLevel.HIGH: high}, avg)
    return AnalyzedRoute(route, [], metrics)


def name(a):
    return f"Route {a.route.index}"


class RankingTests(SimpleTestCase):
    def test_fewest_severe_miles_beats_speed_and_everything_else(self):
        fast_but_severe = analyzed(0, 100, severe=10, high=0, avg=0.1)
        slow_but_clear = analyzed(1, 300, severe=0, high=90, avg=1.5)
        self.assertEqual(recommendation.rank_routes([fast_but_severe, slow_but_clear])[0], slow_but_clear)

    def test_high_miles_break_severe_ties(self):
        a, b = analyzed(0, 100, severe=5, high=40), analyzed(1, 200, severe=5, high=10)
        self.assertEqual(recommendation.rank_routes([a, b])[0], b)

    def test_avg_risk_then_time(self):
        a, b = analyzed(0, 100, avg=0.8), analyzed(1, 200, avg=0.4)
        self.assertEqual(recommendation.rank_routes([a, b])[0], b)
        c, d = analyzed(0, 200, avg=0.5), analyzed(1, 100, avg=0.5)
        self.assertEqual(recommendation.rank_routes([c, d])[0], d)

    def test_no_travel_is_worse_than_any_severe(self):
        blocked = analyzed(0, 100, no_travel=1, severe=0)
        severe = analyzed(1, 100, severe=80)
        self.assertEqual(recommendation.rank_routes([blocked, severe])[0], severe)

    def test_ranks_assigned(self):
        routes = recommendation.rank_routes([analyzed(0, 200), analyzed(1, 100)])
        self.assertEqual([r.rank for r in routes], [1, 2])

    def test_explanation_cites_first_deciding_criterion(self):
        best, other = analyzed(0, 100, severe=0, high=5), analyzed(1, 90, severe=12, high=0)
        self.assertIn("fewest Severe miles", recommendation.explain(best, [other], name))
