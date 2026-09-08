import unittest

from racing_engine.franked_form import (
    FRANK_BOUND,
    WEIGHT_MERIT_PTS_PER_KG_HCP,
    WEIGHT_MERIT_PTS_PER_KG_WFA,
    _adj_margin,
    _weight_factor,
    franking_revision,
)


class AdjMarginTests(unittest.TestCase):
    def test_linear_to_the_knee(self):
        self.assertEqual(_adj_margin(3.0), 3.0)
        self.assertEqual(_adj_margin(4.0), 4.0)

    def test_tapered_past_the_knee(self):
        self.assertAlmostEqual(_adj_margin(10.0), 4.0 + 6.0 * 0.45)


class WeightFactorTests(unittest.TestCase):
    def test_handicap_full(self):
        self.assertEqual(_weight_factor("Handicap. BenchMark 78."), WEIGHT_MERIT_PTS_PER_KG_HCP)

    def test_wfa_small(self):
        self.assertEqual(_weight_factor("Weight for Age. Group 1."), WEIGHT_MERIT_PTS_PER_KG_WFA)


class FrankingRevisionTests(unittest.TestCase):
    def test_no_revision_without_enough_contributors(self):
        self.assertEqual(franking_revision(100.0, [108.0], contributors=1), 0.0)

    def test_positive_when_beaten_field_proves_strong(self):
        # winner rated 100; beaten field's later form + margins medians to 106
        rev = franking_revision(100.0, [105.0, 106.0, 107.0], contributors=3)
        self.assertGreater(rev, 0.0)
        self.assertAlmostEqual(rev, (106.0 - 100.0) * 0.55)

    def test_negative_when_beaten_field_flops(self):
        rev = franking_revision(105.0, [98.0, 99.0, 100.0], contributors=3)
        self.assertLess(rev, 0.0)

    def test_bounded(self):
        self.assertEqual(franking_revision(80.0, [140.0, 141.0], contributors=2), FRANK_BOUND)
        self.assertEqual(franking_revision(140.0, [80.0, 81.0], contributors=2), -FRANK_BOUND)


if __name__ == "__main__":
    unittest.main()
