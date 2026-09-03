import unittest

from ml.nfl.step8_t9_confluence import confluence_status


class NFLStep8T9Tests(unittest.TestCase):
    def test_same_family_is_only_one_vote(self):
        signals = [{"family": "team", "direction": 1, "confidence": .8, "fresh": True},
                   {"family": "team", "direction": 1, "confidence": .7, "fresh": True},
                   {"family": "ml", "direction": 1, "confidence": .6, "fresh": True}]
        result = confluence_status(signals)
        self.assertEqual(result["distinct_families"], 2)
        self.assertEqual(result["status"], "insufficient_distinct_families")

    def test_three_distinct_agreeing_families_create_watch_not_bet(self):
        signals = [{"family": family, "direction": -1, "confidence": .7, "fresh": True}
                   for family in ("team", "personnel", "ml")]
        result = confluence_status(signals)
        self.assertEqual(result["status"], "watch_confluence")
        self.assertEqual(result["direction"], -1)
        self.assertEqual(result["betting_action"], "none")

    def test_conflict_forces_abstain(self):
        signals = [{"family": "team", "direction": 1, "confidence": .8, "fresh": True},
                   {"family": "personnel", "direction": -1, "confidence": .8, "fresh": True},
                   {"family": "ml", "direction": 1, "confidence": .8, "fresh": True}]
        self.assertEqual(confluence_status(signals)["status"], "conflict_abstain")


if __name__ == "__main__":
    unittest.main()
