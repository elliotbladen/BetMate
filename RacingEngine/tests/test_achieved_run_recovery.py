import unittest

from racing_engine.achieved_run_recovery import (
    breakout_collateral_weight, race_weight_policy, weight_component,
    winner_margin_component,
)


class AchievedRunRecoveryTests(unittest.TestCase):
    def test_wfa_and_set_weight_allowances_are_not_merit_bonuses(self):
        for label in ("Standard Weight for Age. Group 1", "Set Weights plus Penalties. Group 3"):
            policy = race_weight_policy(label)
            self.assertNotEqual(policy, "handicap_relative_burden")
            self.assertEqual(weight_component(policy, 59.0, 56.5), 0.0)

    def test_handicap_burden_remains_explicit(self):
        policy = race_weight_policy("Handicap. Group 1")
        self.assertEqual(policy, "handicap_relative_burden")
        self.assertGreater(weight_component(policy, 59.0, 56.5), 5.0)

    def test_dominant_winner_gets_bounded_positive_evidence(self):
        self.assertGreater(winner_margin_component(4.0, 2.8), 0.0)
        self.assertEqual(winner_margin_component(20.0, 2.8), 12.0)

    def test_breakout_relief_requires_multiple_predeclared_flags(self):
        changed, flagged = breakout_collateral_weight(
            .8, winning_margin=4, winner_prior=71, class_standard=105, prior_starts=1)
        self.assertTrue(flagged)
        self.assertEqual(changed, .35)
        unchanged, flagged = breakout_collateral_weight(
            .8, winning_margin=1, winner_prior=71, class_standard=105, prior_starts=1)
        self.assertFalse(flagged)
        self.assertEqual(unchanged, .8)


if __name__ == "__main__":
    unittest.main()
