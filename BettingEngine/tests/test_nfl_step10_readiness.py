import unittest

from ml.nfl.step10_readiness import TIER_REGISTRY, assess_readiness


class NFLStep10ReadinessTests(unittest.TestCase):
    def test_rejected_tiers_cannot_silently_become_active(self):
        self.assertTrue(TIER_REGISTRY["T5 rest/schedule"][0].startswith("rejected"))
        self.assertTrue(TIER_REGISTRY["T7 scheme/matchup"][0].startswith("rejected"))

    def test_current_card_fails_closed(self):
        card, report = assess_readiness()
        self.assertEqual(len(card), 16)
        self.assertFalse(report["ready_to_bet"])
        self.assertFalse(card.staking_enabled.any())
        self.assertTrue(card.betting_decision.eq("ABSTAIN").all())

    def test_t2_t3_historical_gain_is_preserved(self):
        _, report = assess_readiness()
        result = report["historical_consolidation"]
        self.assertGreater(result["t2_t3_gain"], 0)
        self.assertEqual(result["t2_t3_better_seasons"], 6)


if __name__ == "__main__":
    unittest.main()
