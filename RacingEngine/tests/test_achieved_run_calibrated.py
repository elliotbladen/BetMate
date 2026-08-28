import unittest

from racing_engine.achieved_run_calibrated import GRID


class AchievedRunCalibratedTests(unittest.TestCase):
    def test_grid_is_bounded_and_contains_no_extrapolation(self):
        self.assertEqual(GRID[0], 0.0)
        self.assertEqual(GRID[-1], 1.0)
        self.assertEqual(len(GRID), 21)


if __name__ == "__main__":
    unittest.main()
