from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from racing_engine.horse_identity import build_registry
from racing_engine.race_strength_models import VARIANTS, adjustment, build_variants
from racing_engine.storage import RacingStore


class RaceStrengthModelTests(unittest.TestCase):
    def test_adjustment_is_neutral_and_transparent(self) -> None:
        self.assertEqual(adjustment(None), 0)
        self.assertEqual(adjustment(100), 0)
        self.assertEqual(adjustment(108.5), 8.5)

    def test_variants_change_only_race_strength_component_and_use_horse_id(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            store = RacingStore(Path(temporary_directory) / "test.sqlite")
            try:
                self._race(store, "2024-01-01", 1, "PALMETTO 1 70.0", 70.0)
                self._race(store, "2024-02-01", 2, "Palmetto (NZ)", 71.0)
                build_registry(store)
                self._strength(store, "2024-01-01", 1, 110, 103, 108)
                self._strength(store, "2024-02-01", 2, 90, 98, 94)
                first = build_variants(store, "2024-03-01", min_par_sample=1)
                base = store.connection.execute(
                    """SELECT * FROM run_performances WHERE model_version='performance-par-v1.0'
                       AND as_of_date='2024-03-01' AND race_date='2024-01-01' AND runner_number=1""").fetchone()
                class_row = store.connection.execute(
                    """SELECT * FROM run_performances WHERE model_version=? AND as_of_date='2024-03-01'
                       AND race_date='2024-01-01' AND runner_number=1""", (VARIANTS["class_only"],)).fetchone()
                self.assertAlmostEqual(class_row["performance_rating"], base["performance_rating"] + 10)
                self.assertEqual(class_row["time_component"], base["time_component"])
                self.assertEqual(class_row["margin_component"], base["margin_component"])
                self.assertTrue(class_row["horse_key"].startswith("hrs_"))
                horse_id = class_row["horse_key"]
                state = store.connection.execute(
                    "SELECT rated_runs FROM horse_rating_states WHERE model_version=? AND as_of_date='2024-03-01' AND horse_key=?",
                    (VARIANTS["class_only"], horse_id)).fetchone()
                self.assertEqual(state[0], 2)
                second = build_variants(store, "2024-03-01", min_par_sample=1)
                self.assertEqual(first["variants"], second["variants"])
                self.assertEqual(store.connection.execute(
                    "SELECT count(*) FROM run_performances WHERE model_version IN (?,?,?,?)",
                    tuple(VARIANTS.values())).fetchone()[0], 16)
            finally:
                store.close()

    @staticmethod
    def _race(store: RacingStore, race_date: str, number: int, horse: str, seconds: float) -> None:
        store.upsert_result(source="rnsw-authorised", race_date=race_date, state="NSW", track_slug="randwick",
            race_number=number, distance_metres=1200, official_time_seconds=seconds, track_condition="Good 4",
            rail_position="True", source_url=None, raw_race={}, runners=[
                {"runner_number": 1, "runner_name": horse, "finish_position": 1,
                 "finish_time_seconds": seconds, "beaten_lengths": 0.0},
                {"runner_number": 2, "runner_name": f"Other {number}", "finish_position": 2,
                 "finish_time_seconds": seconds + .2, "beaten_lengths": 1.0}])

    @staticmethod
    def _strength(store: RacingStore, race_date: str, number: int, class_rating: float,
                  field_rating: float, combined: float) -> None:
        store.connection.execute(
            """INSERT INTO race_strength_ratings
               (race_strength_version,source,race_date,track_slug,race_number,class_prior_level,class_prior_key,
                class_prior_official_scale,class_global_official_scale,class_only_rating,class_reliability,
                field_only_rating,field_reliability,combined_rating,rated_coverage,field_uncertainty,
                information_cutoff,component_json,created_at)
               VALUES ('race-strength-v1.0','rnsw-authorised',?,'randwick',?,'class_family','NSW|group',90,80,?,.8,?,.5,?,.7,6,?,'{}','now')""",
            (race_date, number, class_rating, field_rating, combined, race_date))
        store.connection.commit()


if __name__ == "__main__":
    unittest.main()
