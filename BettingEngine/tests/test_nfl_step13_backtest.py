import unittest

from ml.nfl.step13_end_to_end_backtest import run


class NFLStep13BacktestTests(unittest.TestCase):
    def test_backtest_contains_development_and_vault(self):
        rows, report = run()
        self.assertEqual(report["walk_forward_games"], 1599)
        self.assertEqual(report["sealed_vault_games"], 272)
        self.assertIn("spread_model_margin", report["markets"])
        self.assertIn("totals", report["thresholds"]["3.0"])

    def test_backtest_never_claims_real_roi(self):
        _, report = run()
        self.assertTrue(any(item.startswith("ROI is synthetic") for item in report["restrictions"]))
        self.assertEqual(report["decision"], "price_paper_markets_now_collect_prospective_evidence_before_betting")


if __name__ == "__main__":
    unittest.main()
