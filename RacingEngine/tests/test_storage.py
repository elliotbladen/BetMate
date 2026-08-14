from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from racing_engine.storage import RacingStore


class RacingStoreTests(unittest.TestCase):
    def test_upsert_card_stores_runner_metadata(self) -> None:
        meeting = {"track": "Rosehill", "slug": "rosehill"}
        card = {
            "raceNumber": 1,
            "raceName": "Midway Handicap",
            "distance": "1500m",
            "condition": "Soft 5",
            "runners": [
                {"number": 1, "name": "Example Runner", "jockey": "J. Rider", "trainer": "T. Trainer", "barrier": 4, "weight": 58.5, "form": "1121", "scratched": False}
            ],
        }
        with TemporaryDirectory() as temporary_directory:
            store = RacingStore(Path(temporary_directory) / "racing.sqlite")
            try:
                self.assertEqual(store.upsert_card("2026-08-15", "NSW", meeting, [card]), 1)
                row = store.connection.execute("SELECT runner_name, jockey, trainer, barrier FROM runners").fetchone()
                self.assertEqual(tuple(row), ("Example Runner", "J. Rider", "T. Trainer", 4))
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()
