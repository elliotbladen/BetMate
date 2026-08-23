import unittest

from racing_engine.race_strength_followons import _conditional_coefficient, robust_weighted_state


class RaceStrengthFollowonTests(unittest.TestCase):
    def test_robust_state_limits_one_extreme_run(self):
        from datetime import date
        normal = robust_weighted_state([(100, 1, 1), (102, 1, 2), (300, 1, 3)], date(2026, 1, 1))[0]
        self.assertLess(normal, 115)

    def test_conditional_strength_is_small_and_reliability_gated(self):
        self.assertEqual(_conditional_coefficient("group", 0), 0)
        self.assertAlmostEqual(_conditional_coefficient("group", .8), .2)
        self.assertAlmostEqual(_conditional_coefficient("benchmark", .8), .08)
        self.assertAlmostEqual(_conditional_coefficient("unknown", .8), .04)


if __name__ == "__main__": unittest.main()
