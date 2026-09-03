import unittest

from ml.football.ucl_walk_forward import run


class UCLWalkForwardTests(unittest.TestCase):
    def test_real_source_produces_expanding_predictions(self):
        rows, report = run()
        self.assertEqual(len(rows), 1997)
        self.assertEqual(report["status"], "ucl_expanding_window_backtest_complete")
        self.assertFalse(report["market_fields_used"])

    def test_modern_and_legacy_are_separate(self):
        _, report = run()
        self.assertEqual(report["modern_format_seasons"], ["2024-25", "2025-26"])
        self.assertIn("legacy", report["by_format"])


if __name__ == "__main__":
    unittest.main()
