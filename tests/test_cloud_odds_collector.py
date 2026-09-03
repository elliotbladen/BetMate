import importlib.util
import json
import sys
import types
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if "requests" not in sys.modules:
    sys.modules["requests"] = types.SimpleNamespace()
SPEC = importlib.util.spec_from_file_location("odds_collector", ROOT / "cloud" / "odds_collector.py")
collector = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(collector)
NEWS_SPEC = importlib.util.spec_from_file_location("news_event_ingest", ROOT / "cloud" / "news_event_ingest.py")
news = importlib.util.module_from_spec(NEWS_SPEC)
NEWS_SPEC.loader.exec_module(news)


class OddsCollectorTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((ROOT / "cloud" / "odds_collection_config.json").read_text())
        self.now = datetime(2026, 9, 3, 0, 0, tzinfo=timezone.utc)

    def test_soccer_draw_is_preserved(self):
        self.assertEqual(collector.selection_key("Draw", "Arsenal", "Chelsea"), "draw")

    def test_flatten_supports_three_way_h2h_and_line_markets(self):
        event = {"id": "game-1", "commence_time": "2026-09-05T14:00:00Z",
                 "home_team": "Arsenal", "away_team": "Chelsea", "bookmakers": [{
                     "key": "book", "title": "Book", "last_update": "2026-09-03T00:00:00Z",
                     "markets": [
                         {"key": "h2h", "outcomes": [{"name": "Arsenal", "price": 2.0},
                                                        {"name": "Draw", "price": 3.4},
                                                        {"name": "Chelsea", "price": 3.8}]},
                         {"key": "totals", "outcomes": [{"name": "Over", "price": 1.9, "point": 2.5},
                                                           {"name": "Under", "price": 1.9, "point": 2.5}]},
                     ]
                 }]}
        rows = collector.flatten([event], "EPL", "soccer_epl", self.now, "au,uk")
        self.assertEqual(len(rows), 5)
        self.assertEqual({r["selection_key"] for r in rows}, {"home", "draw", "away", "over", "under"})
        self.assertEqual(len({r["quote_key"] for r in rows}), 5)

    def test_fingerprint_changes_for_price_or_line(self):
        base = collector.fingerprint(2.5, 1.90)
        self.assertNotEqual(base, collector.fingerprint(2.5, 1.91))
        self.assertNotEqual(base, collector.fingerprint(3.0, 1.90))

    def test_cadence_tightens_near_kickoff(self):
        self.assertEqual(collector.cadence_minutes(self.config, self.now + timedelta(minutes=60), self.now), 5)
        self.assertEqual(collector.cadence_minutes(self.config, self.now + timedelta(hours=5), self.now), 15)
        self.assertEqual(collector.cadence_minutes(self.config, self.now + timedelta(days=2), self.now), 60)

    def test_checkpoint_uses_current_horizon_bucket(self):
        self.assertEqual(collector.checkpoint_for(50, self.config), ("t_minus_60m", 60))
        self.assertEqual(collector.checkpoint_for(4, self.config), ("close", 0))
        self.assertIsNone(collector.checkpoint_for(20000, self.config))

    def test_news_event_requires_timezone_and_deduplicates_stably(self):
        event = {"published_at": "2026-09-03T01:00:00Z", "sport": "nfl",
                 "event_type": "practice_status", "source_level": "A",
                 "source_name": "Club", "source_url": "https://example.test/report",
                 "team_name": "Example", "player_name": "Player", "status_after": "limited"}
        first = news.normalize(event)
        second = news.normalize(event)
        self.assertEqual(first["sport"], "NFL")
        self.assertTrue(first["confirmed"])
        self.assertEqual(first["content_hash"], second["content_hash"])


if __name__ == "__main__":
    unittest.main()
