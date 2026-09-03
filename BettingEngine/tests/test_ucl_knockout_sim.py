import unittest

from ml.football.ucl_knockout_sim import simulate_final, simulate_two_leg_tie


class UCLKnockoutSimTests(unittest.TestCase):
    def legs(self):
        return ({"home_club_id": "a", "away_club_id": "b", "home_goals": 2, "away_goals": 0,
                 "home_xg": 1.5, "away_xg": 1.0},
                {"home_club_id": "b", "away_club_id": "a", "home_goals": 0, "away_goals": 0,
                 "home_xg": 1.2, "away_xg": 1.0})

    def test_first_leg_lead_is_carried_without_away_goals(self):
        result = simulate_two_leg_tie(*self.legs(), simulations=500, seed=1)
        self.assertGreater(result["home_qualification_probability"], .7)
        self.assertFalse(result["away_goals_rule"])

    def test_reversed_legs_are_required(self):
        first, second = self.legs(); second["away_club_id"] = "c"
        with self.assertRaisesRegex(ValueError, "reverse"):
            simulate_two_leg_tie(first, second, simulations=10)

    def test_final_is_neutral(self):
        result = simulate_final(1.4, 1.0, simulations=100, seed=1)
        self.assertTrue(result["neutral_final"])


if __name__ == "__main__":
    unittest.main()
