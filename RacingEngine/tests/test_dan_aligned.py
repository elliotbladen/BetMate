import unittest

from racing_engine.dan_aligned import calibrate_upper_tail


class DanAlignedTests(unittest.TestCase):
    def test_calibration_leaves_normal_ratings_unchanged(self):
        self.assertEqual(calibrate_upper_tail(100.0), 100.0)
        self.assertEqual(calibrate_upper_tail(106.0), 106.0)

    def test_calibration_flattens_only_the_elite_tail(self):
        self.assertAlmostEqual(calibrate_upper_tail(116.0), 111.5)
        self.assertLess(calibrate_upper_tail(122.0), 122.0)


if __name__ == "__main__":
    unittest.main()
