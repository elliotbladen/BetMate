import unittest

from ml.football.ucl_context import MatchContext, context_signal, validate_player_event


class UCLContextTests(unittest.TestCase):
    def event(self):
        return {"event_id": "e1", "club_id": "arsenal", "player_id": "p1", "role": "forward",
                "status": "injured", "expected_minutes_share": 0.8,
                "announced_at_utc": "2026-09-01T10:00:00Z", "source": "club",
                "source_published_at_utc": "2026-09-01T10:00:00Z"}

    def test_post_cutoff_player_event_is_rejected(self):
        event = self.event()
        with self.assertRaisesRegex(ValueError, "not public"):
            validate_player_event(event, "2026-09-01T09:00:00Z", "2026-09-08T19:00:00Z")

    def test_player_event_has_no_direct_points(self):
        event = self.event()
        result = validate_player_event(event, "2026-09-01T12:00:00Z", "2026-09-08T19:00:00Z")
        self.assertEqual(result["model_points"], 0.0)

    def test_context_is_diagnostic(self):
        context = MatchContext("m1", "arsenal", 3, 1200, 1, 4, "2026-09-01T00:00:00Z")
        self.assertEqual(context_signal(context)["signal_mode"], "shadow_no_points")


if __name__ == "__main__":
    unittest.main()
