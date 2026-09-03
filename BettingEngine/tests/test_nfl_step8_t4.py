import unittest
import pandas as pd

from ml.nfl.step8_t4_venue import venue_features


class NFLStep8T4Tests(unittest.TestCase):
    def test_current_game_does_not_enter_its_own_familiarity(self):
        games = pd.DataFrame([
            {"game_id": "g1", "gameday": "2024-01-01", "gametime": "13:00", "stadium_id": "s1", "stadium": "A",
             "home_team": "H", "away_team": "A", "location": "Home", "roof": "outdoors", "surface": "grass"},
            {"game_id": "g2", "gameday": "2024-01-08", "gametime": "13:00", "stadium_id": "s1", "stadium": "A",
             "home_team": "H", "away_team": "B", "location": "Home", "roof": "outdoors", "surface": "grass"},
        ])
        result = venue_features(games).set_index("game_id")
        self.assertEqual(result.loc["g1", "home_stadium_prior_games_log"], 0.0)
        self.assertGreater(result.loc["g2", "home_stadium_prior_games_log"], 0.0)


if __name__ == "__main__":
    unittest.main()
