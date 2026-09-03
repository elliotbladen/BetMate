import unittest

from racing_engine.achieved_run_young_wfa import (
    age_cohort, evidence_margin_fraction, reliability_weight,
)


class YoungWfaAchievedRunTests(unittest.TestCase):
    def test_age_restricted_cohorts_are_parsed_without_upwards_races(self):
        self.assertEqual(age_cohort("Three-Years-Old Set Weight With Penalties"), "3yo_only")
        self.assertEqual(age_cohort("Three-Years-Old and Upwards Handicap"), "open_age")
        self.assertEqual(age_cohort("Two-Years-Old Group 1"), "2yo_only")

    def test_young_collateral_authority_is_capped(self):
        self.assertEqual(reliability_weight([1, 1, 1, 1], 1, "3yo_only"), 0.5)
        self.assertEqual(reliability_weight([1, 1, 1, 1], 1, "open_age"), 0.8)

    def test_margin_credit_requires_independent_support_for_full_value(self):
        self.assertEqual(evidence_margin_fraction(None, None), 0.5)
        self.assertEqual(evidence_margin_fraction(0.6, None), 0.75)
        self.assertEqual(evidence_margin_fraction(None, 1.2), 0.75)
        self.assertEqual(evidence_margin_fraction(0.6, 1.2), 1.0)


if __name__ == "__main__":
    unittest.main()
