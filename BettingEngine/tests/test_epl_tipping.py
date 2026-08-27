import unittest

from ml.football.tipping import PoolRules, tip_match


class EplTippingTests(unittest.TestCase):
    def row(self):
        return {"date": "2026-08-28", "home": "Home", "away": "Away",
                "normal_p_home": .50, "normal_p_draw": .30, "normal_p_away": .20,
                "shadow_p_home": .45, "shadow_p_draw": .32, "shadow_p_away": .23}

    def test_accuracy_mode_chooses_highest_probability(self):
        result = tip_match(self.row(), rules=PoolRules())
        self.assertEqual(result["accuracy_pick"], "H")
        self.assertEqual(result["strategy_pick"], "H")
        self.assertAlmostEqual(sum(result["probabilities"].values()), 1.0, places=5)

    def test_draw_bonus_is_part_of_expected_points(self):
        result = tip_match(self.row(), rules=PoolRules(draw_points=2.0))
        self.assertEqual(result["strategy_pick"], "D")

    def test_model_disagreement_is_exposed(self):
        row = self.row()
        row.update(shadow_p_home=.20, shadow_p_draw=.25, shadow_p_away=.55)
        result = tip_match(row)
        self.assertFalse(result["normal_shadow_agree"])
        self.assertIsNotNone(result["warning"])


if __name__ == "__main__":
    unittest.main()
