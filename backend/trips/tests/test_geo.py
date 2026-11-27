from django.test import SimpleTestCase

from trips.services import geo


class GeoTests(SimpleTestCase):
    def test_haversine_chicago_atlanta(self):
        miles = geo.haversine_miles((41.8781, -87.6298), (33.749, -84.388))
        self.assertAlmostEqual(miles, 587, delta=5)

    def test_checkpoint_distances_include_start_and_end(self):
        self.assertEqual(geo.checkpoint_distances(60, 25), [0, 25, 50, 60])
        self.assertEqual(geo.checkpoint_distances(50, 25), [0, 25, 50])
        self.assertEqual(geo.checkpoint_distances(5, 25), [0, 5])

    def test_segment_ownership_sums_to_route_length(self):
        distances = geo.checkpoint_distances(137.0, 25)
        self.assertAlmostEqual(sum(geo.segment_ownership(distances)), 137.0)

    def test_point_at_interpolates(self):
        coords = [(0.0, 0.0), (0.0, 1.0), (0.0, 2.0)]
        cum = geo.cumulative_miles(coords)
        lat, lon = geo.point_at(coords, cum, cum[-1] / 4)
        self.assertAlmostEqual(lat, 0.0)
        self.assertAlmostEqual(lon, 0.5, places=3)

    def test_interpolate_clamps(self):
        self.assertEqual(geo.interpolate_along([0, 10], [0, 5], 99), 10)
        self.assertEqual(geo.interpolate_along([0, 10], [0, 5], -1), 0)

    def test_simplify_keeps_corners_and_drops_collinear(self):
        line = [(0, 0), (0, 0.1), (0, 0.2), (0.2, 0.2)]
        self.assertEqual(geo.simplify(line, 0.01), [(0, 0), (0, 0.2), (0.2, 0.2)])

    def test_overlap_ratio(self):
        a = [(0.0, i / 100) for i in range(100)]
        self.assertEqual(geo.overlap_ratio(a, a), 1.0)
        far = [(1.0, i / 100) for i in range(100)]
        self.assertEqual(geo.overlap_ratio(a, far), 0.0)
