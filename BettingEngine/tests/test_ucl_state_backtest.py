import unittest

from ml.football.ucl_state_backtest import run


class UCLStateBacktestTests(unittest.TestCase):
    def test_modern_buckets(self):
        rows, report = run()
        self.assertEqual(len(rows), 72)
        self.assertTrue(all(report["checks"].values()))


if __name__ == "__main__":
    unittest.main()
