from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from racing_engine.step11_models import VARIANTS, build_step11_variants
from racing_engine.storage import RacingStore


class Step11ModelTests(unittest.TestCase):
    def test_daily_variant_and_weight_are_isolated_and_wfa_is_gated(self):
        with TemporaryDirectory() as temporary_directory:
            store = RacingStore(Path(temporary_directory) / "test.sqlite")
            try:
                for number, seconds in enumerate((70.0, 71.0, 72.0), 1):
                    self._race(store, "2024-01-01", number, seconds, 60.0, 56.0)
                report = build_step11_variants(store, "2024-01-02", min_par_sample=1)
                self.assertEqual(report["wfa_status"], "GATED_MISSING_DATA")
                base = self._run(store, "performance-par-v1.0", 1, 1)
                daily = self._run(store, VARIANTS["daily_variant"], 1, 1)
                weight = self._run(store, VARIANTS["carried_weight"], 1, 1)
                combined = self._run(store, VARIANTS["daily_weight"], 1, 1)
                self.assertAlmostEqual(weight["performance_rating"], base["performance_rating"] + 2.0)
                self.assertAlmostEqual(combined["performance_rating"], daily["performance_rating"] + 2.0)
                self.assertEqual(weight["time_component"], base["time_component"])
                self.assertIsNone(json.loads(weight["detail_json"])["wfa_component"])
                variant = store.connection.execute("SELECT * FROM daily_track_variants").fetchone()
                self.assertEqual(variant["races_used"], 3)
                self.assertAlmostEqual(variant["shrinkage_factor"], 1 / 3)
                again = build_step11_variants(store, "2024-01-02", min_par_sample=1)
                self.assertEqual(report["variants"], again["variants"])
            finally:
                store.close()

    @staticmethod
    def _run(store, model, race_number, runner_number):
        return store.connection.execute(
            """SELECT * FROM run_performances WHERE model_version=? AND as_of_date='2024-01-02'
               AND race_number=? AND runner_number=?""", (model, race_number, runner_number)).fetchone()

    @staticmethod
    def _race(store, date, number, seconds, first_weight, second_weight):
        store.upsert_result(source="test", race_date=date, state="NSW", track_slug="test-track",
            race_number=number, distance_metres=1200, official_time_seconds=seconds,
            track_condition="Good 4", rail_position="True", source_url=None, raw_race={}, runners=[
                {"runner_number": 1, "runner_name": f"Alpha {number}", "finish_position": 1,
                 "finish_time_seconds": seconds, "beaten_lengths": 0, "weight_carried_kg": first_weight},
                {"runner_number": 2, "runner_name": f"Beta {number}", "finish_position": 2,
                 "finish_time_seconds": seconds + .2, "beaten_lengths": 1, "weight_carried_kg": second_weight}])


if __name__ == "__main__": unittest.main()
