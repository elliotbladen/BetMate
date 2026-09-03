import unittest

import pandas as pd

from ml.football.ucl_backtest import multiclass_metrics, qualification_metrics, run_status


class UCLBacktestTests(unittest.TestCase):
    def test_match_metrics_are_valid(self):
        rows = pd.DataFrame([{ "home_goals": 2, "away_goals": 0, "p_home": .6, "p_draw": .2, "p_away": .2 }])
        result = multiclass_metrics(rows)
        self.assertEqual(result["games"], 1)
        self.assertGreater(result["accuracy"], 0)

    def test_qualification_metrics_are_bounded(self):
        rows = pd.DataFrame([{ "top8_probability": .8, "top8_actual": 1, "top24_probability": .9, "top24_actual": 1 }])
        result = qualification_metrics(rows)
        self.assertEqual(result["clubs"], 1)
        self.assertGreaterEqual(result["top8_brier"], 0)

    def test_loaded_source_still_blocks_without_predictions(self):
        result = run_status()
        self.assertEqual(result["status"], "ucl_backtest_input_loaded_metrics_pending")
        self.assertEqual(result["games"], 1997)
        self.assertFalse(result["promotion_allowed"])


if __name__ == "__main__":
    unittest.main()
