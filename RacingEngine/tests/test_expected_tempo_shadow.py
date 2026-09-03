import unittest

import numpy as np

from racing_engine.expected_tempo_shadow import bounded_score, cap_probability_update


class ExpectedTempoShadowTests(unittest.TestCase):
    def test_probability_cap_preserves_sum_and_bounds_each_move(self):
        v0 = np.array([0.4, 0.2, 0.3, 0.1])
        candidate = np.array([0.1, 0.2, 0.3, 0.4])
        result = cap_probability_update(v0, candidate, 0.05)
        self.assertAlmostEqual(float(result.sum()), 1.0)
        self.assertLessEqual(float(np.max(np.abs(result - v0))), 0.05 + 1e-12)

    def test_score_threshold_and_cap(self):
        self.assertEqual(bounded_score(0.0, 0.02, 0.05, 0.5), (0.0, "below_minimum_change"))
        self.assertEqual(bounded_score(0.0, 0.8, 0.05, 0.5), (0.5, "capped"))
        self.assertEqual(bounded_score(0.0, -0.3, 0.05, 0.5), (-0.3, "updated"))


if __name__ == "__main__":
    unittest.main()
