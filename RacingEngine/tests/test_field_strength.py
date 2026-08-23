from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from racing_engine.field_strength import build_field_strengths, summarize_field
from racing_engine.horse_identity import build_registry
from racing_engine.storage import RacingStore


class FieldStrengthTests(unittest.TestCase):
    def test_summary_reports_median_top_depth_coverage_and_uncertainty(self) -> None:
        result = summarize_field([
            {"prior_rating": 110, "prior_uncertainty": 3, "rated": 1},
            {"prior_rating": 107, "prior_uncertainty": 4, "rated": 1},
            {"prior_rating": 100, "prior_uncertainty": 12, "rated": 0},
            {"prior_rating": 99, "prior_uncertainty": 5, "rated": 1},
        ])
        self.assertEqual(result["field_median_rating"], 103.5)
        self.assertEqual(result["top_four_mean_rating"], 104)
        self.assertEqual(result["depth_within_five"], 2)
        self.assertEqual(result["rated_coverage"], 0.75)
        self.assertGreater(result["field_uncertainty"], 6)

    def test_identity_variant_supplies_prior_state_without_future_leakage(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            store = RacingStore(Path(temporary_directory) / "test.sqlite")
            try:
                self._race(store, "rnsw-authorised", "2024-01-01", "randwick", "PALMETTO 1 70.0", 70.0)
                self._race(store, "racing-com-rv-authorised", "2024-02-01", "flemington", "Palmetto (NZ)", 71.0)
                build_registry(store)
                first = build_field_strengths(store, from_date="2024-02-01", to_date="2024-02-01", min_par_sample=1)
                state = store.connection.execute(
                    """SELECT rated,prior_runs,prior_rating,information_cutoff FROM pre_race_runner_states
                       WHERE race_date='2024-02-01' AND runner_number=1""").fetchone()
                self.assertEqual((state["rated"], state["prior_runs"], state["information_cutoff"]), (1, 1, "2024-02-01"))
                rating_before = state["prior_rating"]
                self._race(store, "racing-com-rv-authorised", "2025-01-01", "flemington", "Palmetto (NZ)", 20.0)
                build_registry(store)
                second = build_field_strengths(store, from_date="2024-02-01", to_date="2024-02-01", min_par_sample=1)
                rating_after = store.connection.execute(
                    "SELECT prior_rating FROM pre_race_runner_states WHERE race_date='2024-02-01' AND runner_number=1").fetchone()[0]
                self.assertEqual(first["races"], second["races"])
                self.assertEqual(rating_before, rating_after)
                self.assertEqual(store.connection.execute(
                    "SELECT count(*) FROM pre_race_field_strengths WHERE race_date='2024-02-01'").fetchone()[0], 1)
            finally:
                store.close()

    @staticmethod
    def _race(store: RacingStore, source: str, race_date: str, track: str, horse: str, seconds: float) -> None:
        store.upsert_result(source=source, race_date=race_date, state="NSW", track_slug=track, race_number=1,
            distance_metres=1200, official_time_seconds=seconds, track_condition="Good 4", rail_position="True",
            source_url=None, raw_race={}, runners=[
                {"runner_number": 1, "runner_name": horse, "finish_position": 1,
                 "finish_time_seconds": seconds, "beaten_lengths": 0.0},
                {"runner_number": 2, "runner_name": f"Other {race_date}", "finish_position": 2,
                 "finish_time_seconds": seconds + 0.2, "beaten_lengths": 1.0},
            ])


if __name__ == "__main__":
    unittest.main()
