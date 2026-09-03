import unittest

from ml.nfl.step11_shadow_run import run_checkpoint


class NFLStep11ShadowRunTests(unittest.TestCase):
    def test_checkpoint_is_fail_closed(self):
        result = run_checkpoint()
        self.assertEqual(result["status"], "shadow_checkpoint_blocked")
        self.assertEqual(result["betting_decision"], "ABSTAIN")
        self.assertFalse(result["staking_enabled"])
        self.assertFalse(result["thresholds_retuned"])


if __name__ == "__main__":
    unittest.main()
