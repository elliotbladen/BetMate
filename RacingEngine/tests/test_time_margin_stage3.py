import unittest

from racing_engine.time_margin_stage3 import blend_ratings


class TimeMarginStage3Tests(unittest.TestCase):
    def test_blend_endpoints_and_halfway(self):
        identity=[100.0,90.0];margin=[104.0,88.0]
        self.assertEqual(blend_ratings(identity,margin,0),identity)
        self.assertEqual(blend_ratings(identity,margin,1),margin)
        self.assertEqual(blend_ratings(identity,margin,.5),[102.0,89.0])

    def test_mismatched_books_are_rejected(self):
        with self.assertRaises(ValueError):blend_ratings([100.0],[100.0,90.0],.5)

if __name__=="__main__":unittest.main()
