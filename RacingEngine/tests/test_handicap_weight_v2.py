import unittest

from racing_engine.handicap_weight_v2 import COEFFICIENTS


class HandicapWeightV2Tests(unittest.TestCase):
    def test_grid_is_bounded_and_includes_full_parent(self):
        self.assertEqual(COEFFICIENTS[0],0.0);self.assertEqual(COEFFICIENTS[-1],1.0)
        self.assertTrue(all(0<=value<=1 for value in COEFFICIENTS))


if __name__=="__main__":unittest.main()
