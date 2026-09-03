import unittest

from racing_engine.expected_tempo_targets import (
    _blend_par, four_way_label, rail_bucket, robust_location_scale,
)


class ExpectedTempoTargetTests(unittest.TestCase):
    def test_rail_bucket(self):
        self.assertEqual(rail_bucket("True Entire Circuit"), "true")
        self.assertEqual(rail_bucket("+3m Entire"), "out_1_3m")
        self.assertEqual(rail_bucket("Out 6m Entire Circuit"), "out_4_6m")
        self.assertEqual(rail_bucket("+9m 1000m-W/Post, +6m Remainder"), "out_7m_plus")

    def test_robust_scale_resists_outlier(self):
        location, scale = robust_location_scale([22.0] * 9 + [40.0])
        self.assertEqual(location, 22.0)
        self.assertEqual(scale, 0.10)

    def test_hierarchical_par_requires_prior_depth_and_shrinks(self):
        broad = [24.0] * 20
        local = [22.0] * 5
        result = _blend_par([("broad", broad), ("local", local)])
        self.assertIsNotNone(result)
        location, _, level, sample, _ = result
        self.assertEqual(level, "local")
        self.assertEqual(sample, 5)
        self.assertGreater(location, 22.0)
        self.assertLess(location, 24.0)

    def test_four_way_labels(self):
        self.assertEqual(four_way_label(-0.8, 0.0, 1.0), "slow")
        self.assertEqual(four_way_label(0.1, 0.0, 0.0), "even")
        self.assertEqual(four_way_label(0.7, 0.0, 0.0), "fast")
        self.assertEqual(four_way_label(0.9, 0.1, -0.9), "very_fast_or_collapse")


if __name__ == "__main__":
    unittest.main()
