import unittest

from racing_engine.achieved_run_collateral import GRID, prior_form_anchor


class AchievedRunCollateralTests(unittest.TestCase):
    def test_no_history_preserves_official_with_zero_reliability(self):
        result = prior_form_anchor([], 72.0)
        self.assertEqual(result["anchor"], 72.0)
        self.assertEqual(result["reliability"], 0.0)

    def test_consistent_prior_form_can_move_stale_official_anchor(self):
        result = prior_form_anchor([84.0, 85.0, 83.0], 72.0)
        self.assertGreater(result["anchor"], 78.0)
        self.assertLess(result["anchor"], 85.0)

    def test_volatile_form_has_less_authority(self):
        consistent = prior_form_anchor([84.0, 85.0, 83.0], 72.0)
        volatile = prior_form_anchor([60.0, 84.0, 105.0], 72.0)
        self.assertGreater(consistent["reliability"], volatile["reliability"])

    def test_fit_grid_is_bounded(self):
        self.assertEqual((GRID[0], GRID[-1]), (0.0, 1.0))


if __name__ == "__main__": unittest.main()
