import unittest
import pandas as pd

from ml.nfl.step8_t5_schedule import schedule_features


class NFLStep8T5Tests(unittest.TestCase):
    def test_short_and_long_rest_are_side_consistent(self):
        row = pd.DataFrame([{"game_id": "g1", "home_rest": 4, "away_rest": 10, "weekday": "Thursday"}])
        result = schedule_features(row).iloc[0]
        self.assertEqual(result.short_rest_diff, 1)
        self.assertEqual(result.long_rest_diff, -1)
        self.assertEqual(result.rest_mismatch_away_advantage, 6)
        self.assertEqual(result.thursday_game, 1)


if __name__ == "__main__":
    unittest.main()
