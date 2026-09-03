import unittest

from ml.football.ucl_player_shadow import run_status


class UCLPlayerShadowTests(unittest.TestCase):
    def test_fails_closed_without_events(self):
        result = run_status()
        self.assertEqual(result["mode"], "shadow")
        self.assertFalse(result["production_price_influence"])


if __name__ == "__main__":
    unittest.main()
