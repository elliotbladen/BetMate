import unittest

from ml.nfl.context_events import validate_context_event


class NFLContextEventTests(unittest.TestCase):
    def test_valid_event_is_diagnostic_and_zero_points(self):
        event = {"event_id": "e1", "game_id": "g1", "team": "BUF", "event_type": "head_coach_change",
                 "announced_at": "2026-09-01T12:00:00Z", "source_url": "https://example.com/official",
                 "source_kind": "team"}
        result = validate_context_event(event, "2026-09-06T17:00:00Z", "2026-09-05T17:00:00Z")
        self.assertEqual(result["model_points"], 0.0)
        self.assertEqual(result["routing"], "context_diagnostic")

    def test_post_cutoff_news_is_rejected(self):
        event = {"event_id": "e1", "game_id": "g1", "team": "BUF", "event_type": "bereavement",
                 "announced_at": "2026-09-06T12:00:00Z", "source_url": "https://example.com/official",
                 "source_kind": "team"}
        with self.assertRaisesRegex(ValueError, "not public"):
            validate_context_event(event, "2026-09-06T17:00:00Z", "2026-09-05T17:00:00Z")

    def test_returns_are_routed_to_personnel(self):
        event = {"event_id": "e2", "game_id": "g1", "team": "BUF", "event_type": "player_return",
                 "announced_at": "2026-09-01T12:00:00Z", "source_url": "https://example.com/official",
                 "source_kind": "league_transaction"}
        result = validate_context_event(event, "2026-09-06T17:00:00Z", "2026-09-05T17:00:00Z")
        self.assertEqual(result["routing"], "t2_availability")


if __name__ == "__main__":
    unittest.main()
