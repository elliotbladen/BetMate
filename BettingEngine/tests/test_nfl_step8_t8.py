import unittest

import pandas as pd

from ml.nfl.step8_t8_market import add_market_disagreement


class NFLStep8T8Tests(unittest.TestCase):
    def test_spread_signs_are_home_strength_consistent(self):
        frame = pd.DataFrame([{"spread_home_open": -3.0, "spread_home_close": -5.0,
                               "ridge_margin": 6.0, "tree_margin": 4.0,
                               "total_line_open": 45.0, "total_line_close": 47.0, "tree_total": 48.0}])
        row = add_market_disagreement(frame).iloc[0]
        self.assertEqual(row.open_implied_margin, 3.0)
        self.assertEqual(row.spread_move_home_strength, 2.0)
        self.assertEqual(row.ridge_spread_disagreement, 3.0)
        self.assertEqual(row.total_market_move, 2.0)


if __name__ == "__main__":
    unittest.main()
