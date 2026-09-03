import unittest
import pandas as pd

from ml.nfl.step8_t7_matchup import matchup_features


class NFLStep8T7Tests(unittest.TestCase):
    def test_matchup_interaction_is_home_minus_away_for_margin(self):
        row = {"game_id": "g1"}
        for name in ("pass_epa", "rush_epa", "success_rate", "early_down_epa", "explosive_rate", "sack_rate"):
            row.update({f"home_off_{name}": 2.0, f"away_def_{name}": 3.0,
                        f"away_off_{name}": 1.0, f"home_def_{name}": 4.0})
        result = matchup_features(pd.DataFrame([row])).iloc[0]
        self.assertEqual(result.matchup_diff_pass_epa, 2.0)
        self.assertEqual(result.matchup_sum_pass_epa, 10.0)


if __name__ == "__main__":
    unittest.main()
