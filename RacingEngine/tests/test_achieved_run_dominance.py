import unittest

from racing_engine.achieved_run_dominance import MIN_PRIOR_RACES, empirical_dominance


class AchievedRunDominanceTests(unittest.TestCase):
    def test_sparse_history_has_no_authority(self):
        result = empirical_dominance(4.0, [0.5] * (MIN_PRIOR_RACES - 1))
        self.assertFalse(result["available"])
        self.assertEqual(result["reliability"], 0.0)

    def test_ordinary_margin_has_no_dominance_authority(self):
        result = empirical_dominance(0.5, [x / 20 for x in range(20)])
        self.assertEqual(result["reliability"], 0.0)

    def test_exceptional_margin_has_high_authority(self):
        result = empirical_dominance(4.0, [x / 20 for x in range(20)])
        self.assertGreaterEqual(result["reliability"], 0.95)


if __name__ == "__main__": unittest.main()
