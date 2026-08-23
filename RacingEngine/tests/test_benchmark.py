from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from racing_engine.benchmark import run_benchmark
from racing_engine.evaluation_protocol import DEFAULT_PROTOCOL
from racing_engine.storage import RacingStore


class BenchmarkTests(unittest.TestCase):
    def test_prediction_ledger_is_complete_and_reproducible(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            store = RacingStore(Path(temporary_directory) / "test.sqlite")
            try:
                self._race(store, "2024-08-01", "Known", "Other", 70.0)
                self._race(store, "2024-09-07", "Known", "Debutant", 71.0)
                first = run_benchmark(store, protocol_path=DEFAULT_PROTOCOL,
                                      periods=("validation",), min_par_sample=1)
                rows = store.connection.execute(
                    "SELECT runner_name,win_probability,outcome,unrated,information_cutoff FROM benchmark_predictions ORDER BY runner_number"
                ).fetchall()
                self.assertEqual(first["coverage"]["eligible_races"], 1)
                self.assertEqual(first["segments"]["state"]["NSW"]["races"], 1)
                self.assertEqual(first["runner_segments"]["history_depth"]["debutant"]["runners"], 1)
                self.assertEqual(len(rows), 2)
                self.assertAlmostEqual(sum(row["win_probability"] for row in rows), 1.0)
                self.assertEqual(sum(row["outcome"] for row in rows), 1)
                self.assertEqual(next(row["unrated"] for row in rows if row["runner_name"] == "Debutant"), 1)
                self.assertTrue(all(row["information_cutoff"] == "2024-09-07" for row in rows))
                second = run_benchmark(store, protocol_path=DEFAULT_PROTOCOL,
                                       periods=("validation",), min_par_sample=1)
                self.assertEqual(first["metrics"], second["metrics"])
                self.assertEqual(store.connection.execute("SELECT count(*) FROM benchmark_predictions").fetchone()[0], 2)
            finally:
                store.close()

    @staticmethod
    def _race(store: RacingStore, race_date: str, winner: str, second: str, seconds: float) -> None:
        store.upsert_result(
            source="test", race_date=race_date, state="NSW", track_slug="randwick", race_number=1,
            distance_metres=1200, official_time_seconds=seconds, track_condition="Good 4", rail_position="True",
            source_url=None, raw_race={}, runners=[
                {"runner_number": 1, "runner_name": winner, "finish_position": 1,
                 "finish_time_seconds": seconds, "beaten_lengths": 0.0},
                {"runner_number": 2, "runner_name": second, "finish_position": 2,
                 "finish_time_seconds": seconds + 0.2, "beaten_lengths": 1.0},
            ])


if __name__ == "__main__":
    unittest.main()
