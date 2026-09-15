import sqlite3
import tempfile
import unittest
from pathlib import Path

from racing_engine.storage import RacingStore


class FitnessEventsSchemaTests(unittest.TestCase):
    def test_event_contract_is_append_only_and_provenance_complete(self):
        with tempfile.TemporaryDirectory() as directory:
            store = RacingStore(Path(directory) / "fitness.sqlite")
            store.connection.execute(
                """INSERT INTO horses
                   (horse_id, canonical_name, identity_key, identity_status,
                    detail_json, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                ("h1", "Test Horse", "test horse", "test", "{}", "2026-01-01", "2026-01-01"),
            )
            store.connection.execute(
                """INSERT INTO fitness_events
                   (event_id, horse_id, event_type, event_date, effective_at,
                    source, source_event_id, track_slug, distance_metres, surface,
                    going, rail_position, trial_type, heat_number, field_size,
                    barrier, finish_position, beaten_margin, official_time_seconds,
                    sectionals_json, jockey_name, trainer_name, source_url,
                    collected_at, parser_version, payload_hash, raw_json,
                    detail_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                           ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    "e1", "h1", "official_trial", "2026-01-01", "2026-01-01T00:00:00Z",
                    "racing-nsw", "trial-1", "randwick", 1000, "turf", "Good4", "true",
                    "OPEN", 1, 8, 3, 1, 0.2, 60.0, "{}", "J.Doe", "T.Trainer",
                    "https://example.test", "2026-01-01T01:00:00Z", "parser-v1", "hash-1",
                    "{}", "{}", "2026-01-01T01:00:00Z",
                ),
            )
            with self.assertRaises(sqlite3.IntegrityError):
                store.connection.execute("UPDATE fitness_events SET going='Soft5' WHERE event_id='e1'")
            with self.assertRaises(sqlite3.IntegrityError):
                store.connection.execute("DELETE FROM fitness_events WHERE event_id='e1'")
            columns = {row[1] for row in store.connection.execute("PRAGMA table_info(fitness_events)")}
            self.assertTrue({"horse_id", "event_type", "effective_at", "source_url", "parser_version", "payload_hash"} <= columns)
            store.close()


if __name__ == "__main__":
    unittest.main()
