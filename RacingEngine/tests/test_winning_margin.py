import unittest

from racing_engine.winning_margin import anchored_level, margin_multiplier


class WinningMarginTests(unittest.TestCase):
    def test_distance_multiplier_declines_without_becoming_zero(self):
        self.assertEqual(margin_multiplier(1000), 1.5)
        self.assertEqual(margin_multiplier(1600), 1.0)
        self.assertEqual(margin_multiplier(2800), .5)
        self.assertEqual(margin_multiplier(4000), .5)

    def test_wider_margin_raises_form_anchored_winner_level(self):
        narrow, narrow_reliability = anchored_level([(100, 0), (100, 1)], 2)
        wide, wide_reliability = anchored_level([(100, 0), (100, 5)], 2)
        self.assertGreater(wide, narrow)
        self.assertGreater(narrow_reliability, 0)
        self.assertGreater(wide_reliability, 0)

    def test_anchor_requires_more_than_one_known_horse(self):
        self.assertEqual(anchored_level([(100, 0)], 10), (None, 0.0))


if __name__ == "__main__": unittest.main()
