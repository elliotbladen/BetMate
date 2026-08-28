import unittest

from racing_engine.collateral_revision_v2 import INITIAL_WEIGHT_COEFFICIENT


class CollateralRevisionV2Tests(unittest.TestCase):
    def test_initial_coefficient_is_rematch_selected(self):
        self.assertEqual(INITIAL_WEIGHT_COEFFICIENT,.25)


if __name__=="__main__":unittest.main()
