from django.test import SimpleTestCase

from trips.domain import RiskLevel as L
from trips.domain import WeatherSample
from trips.services import risk


def sample(wind=0.0, rain=0.0, snow=0.0):
    return WeatherSample(wind, rain, snow)


class ThresholdTests(SimpleTestCase):
    def test_wind_bands(self):
        cases = [(0, L.LOW), (24.9, L.LOW), (25, L.MODERATE), (34.9, L.MODERATE), (35, L.HIGH),
                 (44.9, L.HIGH), (45, L.SEVERE), (54.9, L.SEVERE), (55, L.NO_TRAVEL), (80, L.NO_TRAVEL)]
        for value, expected in cases:
            with self.subTest(wind=value):
                self.assertEqual(risk.WIND.classify(value), expected)

    def test_rain_bands(self):
        cases = [(0.09, L.LOW), (0.10, L.MODERATE), (0.24, L.MODERATE), (0.25, L.HIGH), (0.49, L.HIGH),
                 (0.50, L.SEVERE), (1.00, L.SEVERE), (1.01, L.NO_TRAVEL)]
        for value, expected in cases:
            with self.subTest(rain=value):
                self.assertEqual(risk.RAIN.classify(value), expected)

    def test_snow_bands(self):
        cases = [(0.4, L.LOW), (0.5, L.MODERATE), (1.0, L.HIGH), (2.0, L.SEVERE), (3.0, L.SEVERE), (3.01, L.NO_TRAVEL)]
        for value, expected in cases:
            with self.subTest(snow=value):
                self.assertEqual(risk.SNOW.classify(value), expected)


class LoadRuleTests(SimpleTestCase):
    def test_wind_55_is_no_travel_for_any_load(self):
        self.assertEqual(risk.assess(sample(wind=55), 0).level, L.NO_TRAVEL)

    def test_45_to_54_with_heavy_load_is_no_travel(self):
        self.assertEqual(risk.assess(sample(wind=50), 30_001).level, L.NO_TRAVEL)

    def test_45_to_54_at_or_below_30k_stays_severe(self):
        self.assertEqual(risk.assess(sample(wind=50), 30_000).level, L.SEVERE)

    def test_35_to_44_over_40k_is_severe(self):
        result = risk.assess(sample(wind=40), 40_001)
        self.assertEqual(result.level, L.SEVERE)
        self.assertIsNotNone(result.load_rule)

    def test_35_to_44_at_40k_stays_high(self):
        result = risk.assess(sample(wind=40), 40_000)
        self.assertEqual(result.level, L.HIGH)
        self.assertIsNone(result.load_rule)

    def test_light_wind_unaffected_by_load(self):
        self.assertEqual(risk.assess(sample(wind=20), 80_000).level, L.LOW)

    def test_overall_level_is_worst_condition(self):
        result = risk.assess(sample(wind=26, rain=0.6, snow=0.1), 10_000)
        self.assertEqual((result.wind_level, result.rain_level, result.snow_level), (L.MODERATE, L.SEVERE, L.LOW))
        self.assertEqual(result.level, L.SEVERE)
