import unittest

from racing_engine.achieved_run_corroborated import quantile


class CorroboratedAchievedRunTests(unittest.TestCase):
    def test_training_quantile_is_deterministic(self):
        self.assertEqual(quantile([4, 1, 3, 2], .75), 4)
        self.assertIsNone(quantile([], .75))


if __name__ == "__main__":
    unittest.main()
