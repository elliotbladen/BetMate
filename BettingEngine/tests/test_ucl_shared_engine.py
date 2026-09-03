import unittest
from ml.football.ucl_shared_engine import load_matches, fit_before

class UCLSharedEngineTests(unittest.TestCase):
    def test_contract_uses_goals_fallback_without_xg(self):
        rows=load_matches(); self.assertEqual(rows.xg_source.iloc[0], "goals_fallback")
        ratings=fit_before(rows, rows.Date.iloc[-1]); self.assertTrue(ratings)

if __name__=="__main__": unittest.main()
