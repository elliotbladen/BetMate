import unittest

from ml.football.ucl_league_sim import rank_table, simulate_league_phase


class UCLLeagueSimTests(unittest.TestCase):
    def test_rank_table_uses_points_then_goal_difference(self):
        clubs = [{"club_id": "a"}, {"club_id": "b"}]
        records = [{"home_club_id": "a", "away_club_id": "b", "home_goals": 2, "away_goals": 0}]
        self.assertEqual(rank_table(records, clubs), ["a", "b"])

    def test_simulation_rejects_incomplete_draw(self):
        clubs = [{"club_id": "a", "coefficient_pot": 1, "association": "x"}]
        with self.assertRaisesRegex(ValueError, "36"):
            simulate_league_phase(clubs, [], {"a": (1, 1)}, simulations=2)


if __name__ == "__main__":
    unittest.main()
