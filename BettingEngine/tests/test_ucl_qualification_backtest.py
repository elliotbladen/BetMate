import unittest

from ml.football.ucl_qualification_backtest import run


class UCLQualificationBacktestTests(unittest.TestCase):
    def test_probabilities_are_bounded(self):
        rows, report = run(simulations=25)
        self.assertEqual(len(rows), 72)
        self.assertTrue(((rows.top8_probability >= 0) & (rows.top8_probability <= 1)).all())
        self.assertEqual(report["overall"]["clubs"], 72)


if __name__ == "__main__":
    unittest.main()
