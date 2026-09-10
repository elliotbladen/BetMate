import unittest

from racing_engine.wind_adjusted_test import wind_component


class WindAdjustedTest(unittest.TestCase):
    def test_tailwind_is_positive_component(self):
        # Wind from west travels east; eastbound travel receives a tailwind.
        self.assertAlmostEqual(wind_component(40.0, 270.0, 90.0), 40.0)

    def test_headwind_is_negative_component(self):
        self.assertAlmostEqual(wind_component(40.0, 90.0, 90.0), -40.0)

    def test_crosswind_is_neutral(self):
        self.assertAlmostEqual(wind_component(40.0, 0.0, 90.0), 0.0, places=8)


if __name__ == "__main__":
    unittest.main()
