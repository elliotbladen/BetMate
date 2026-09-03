import unittest

import pandas as pd

from ml.nfl.step8_tier_audit import _shuffle_within_season


class NFLStep8Tests(unittest.TestCase):
    def test_negative_control_preserves_each_seasons_values(self):
        frame = pd.DataFrame({
            "season": [2023, 2023, 2023, 2024, 2024, 2024],
            "value": [1, 2, 3, 10, 20, 30],
        })
        shuffled = _shuffle_within_season(frame, ["value"], seed=7)
        for season in (2023, 2024):
            original = sorted(frame.loc[frame.season.eq(season), "value"])
            result = sorted(shuffled.loc[frame.season.eq(season), "value"])
            self.assertEqual(original, result)


if __name__ == "__main__":
    unittest.main()
