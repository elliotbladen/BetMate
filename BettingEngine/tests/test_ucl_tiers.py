import unittest
from ml.football.ucl_tiers import status
class UCLTierTests(unittest.TestCase):
    def test_player_and_phase_tiers_are_shadowed(self):
        result=status("knockout")
        self.assertEqual(result["player_shadow"], "T2")
        self.assertEqual(result["tiers"]["T5"]["mode"], "shadow")
        self.assertEqual(result["production_price_influence"], ["T0", "T1"])
if __name__=="__main__": unittest.main()
