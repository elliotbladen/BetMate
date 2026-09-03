from datetime import datetime, timezone
import unittest

from ml.nfl.step7_market_shadow import classify_market_disagreement, normalize_payload


class NFLStep7Tests(unittest.TestCase):
    def payload(self):
        return [{
            "id": "event-1", "commence_time": "2026-09-10T03:20:00Z",
            "home_team": "Seattle Seahawks", "away_team": "New England Patriots",
            "bookmakers": [{
                "key": "testbook", "last_update": "2026-09-01T00:00:00Z",
                "markets": [
                    {"key": "spreads", "outcomes": [
                        {"name": "Seattle Seahawks", "price": 1.91, "point": -3.0},
                        {"name": "New England Patriots", "price": 1.91, "point": 3.0},
                    ]},
                    {"key": "totals", "outcomes": [
                        {"name": "Over", "price": 1.91, "point": 47.5},
                        {"name": "Under", "price": 1.91, "point": 47.5},
                    ]},
                ],
            }],
        }]

    def test_valid_quote_maps_to_frozen_game_and_home_spread_convention(self):
        rows = normalize_payload(self.payload(), datetime(2026, 9, 1, tzinfo=timezone.utc))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["game_id"], "2026_01_NE_SEA")
        self.assertEqual(rows[0]["home_spread"], -3.0)
        self.assertTrue(rows[0]["valid_obtainable_quote"])

    def test_mismatched_spread_sign_is_rejected(self):
        payload = self.payload()
        payload[0]["bookmakers"][0]["markets"][0]["outcomes"][1]["point"] = 2.5
        row = normalize_payload(payload, datetime(2026, 9, 1, tzinfo=timezone.utc))[0]
        self.assertFalse(row["valid_obtainable_quote"])
        self.assertIn("spread_sign_mismatch", row["qualification_reason"])

    def test_post_kickoff_quote_is_rejected(self):
        payload = self.payload()
        payload[0]["bookmakers"][0]["last_update"] = "2026-09-10T04:00:00Z"
        row = normalize_payload(payload, datetime(2026, 9, 10, 4, tzinfo=timezone.utc))[0]
        self.assertFalse(row["valid_obtainable_quote"])
        self.assertIn("quote_not_before_kickoff", row["qualification_reason"])

    def test_t8_large_disagreement_remains_watch_only(self):
        result = classify_market_disagreement(3.2, 4.0, -3.1, 0.5, 1.0)
        self.assertEqual(result["spread_status"], "watch_large")
        self.assertTrue(result["spread_model_agreement"])
        self.assertEqual(result["betting_action"], "none")

    def test_t8_high_book_dispersion_marks_unstable_market(self):
        result = classify_market_disagreement(4.0, 3.5, None, 2.5, None)
        self.assertEqual(result["spread_status"], "watch_unstable_market")


if __name__ == "__main__":
    unittest.main()
