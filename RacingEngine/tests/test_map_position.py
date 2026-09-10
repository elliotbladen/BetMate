from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from racing_engine.map_position import (RunnerInput, blend_context, ensure_schema,
    _profile, distance_band, going_bucket, simulate_field, smoothed_probabilities,
    state_from_position, evaluate_history, VERSION)
from racing_engine.storage import RacingStore

class MapPositionTests(unittest.TestCase):
    def test_position_labels_scale_with_field(self):
        self.assertEqual(state_from_position(1,12),"leader")
        self.assertEqual(state_from_position(3,12),"on_pace")
        self.assertEqual(state_from_position(7,12),"midfield")
        self.assertEqual(state_from_position(11,12),"backmarker")

    def test_probabilities_are_smoothed(self):
        p=smoothed_probabilities({"leader":3})
        self.assertAlmostEqual(sum(p.values()),1.0)
        self.assertGreater(p["backmarker"],0)

    def test_inside_barrier_tilts_forward_without_forcing(self):
        base={state:.25 for state in ("leader","on_pace","midfield","backmarker")}
        inside=blend_context(base,1,12); outside=blend_context(base,12,12)
        self.assertGreater(inside["leader"],outside["leader"])
        self.assertGreater(outside["backmarker"],inside["backmarker"])

    def test_simulation_is_deterministic_and_constrained(self):
        p=[{"leader":.6,"on_pace":.2,"midfield":.1,"backmarker":.1},
           {"leader":.1,"on_pace":.2,"midfield":.3,"backmarker":.4}]
        a=simulate_field(p,[1,2],500,7); b=simulate_field(p,[1,2],500,7)
        self.assertEqual(a,b)
        self.assertLess(a[0]["expected_rank"],a[1]["expected_rank"])

    def test_schema_is_isolated_from_prices(self):
        with TemporaryDirectory() as folder:
            store=RacingStore(Path(folder)/"test.sqlite")
            try:
                ensure_schema(store)
                names={row[0] for row in store.connection.execute("select name from sqlite_master where type='table'")}
                self.assertIn("map_runner_predictions",names)
            finally: store.close()

    def test_context_buckets_are_stable(self):
        self.assertEqual(going_bucket("Soft 5"), "soft")
        self.assertEqual(distance_band(1200), "sprint")
        self.assertEqual(distance_band(1600), "mile")
        self.assertEqual(distance_band(2000), "middle")

    def test_profile_prefers_track_distance_going_history(self):
        with TemporaryDirectory() as folder:
            store = RacingStore(Path(folder) / "test.sqlite")
            try:
                ensure_schema(store)
                exact_detail = '{"distance_band":"sprint","going_bucket":"soft"}'
                fallback_detail = '{"distance_band":"staying","going_bucket":"good"}'
                for i in range(4):
                    store.connection.execute(
                        """INSERT INTO map_runner_history_features VALUES
                        (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (VERSION, "src", f"2024-01-{i + 1:02d}", "randwick", i + 1, i + 1,
                         "example", "Example", "leader", 1, 10, None, "unavailable", 1,
                         0, 0, 0, f"2024-01-{i + 1:02d}", exact_detail, "now"))
                    store.connection.execute(
                        """INSERT INTO map_runner_history_features VALUES
                        (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (VERSION, "src", f"2023-12-{i + 1:02d}", "randwick", i + 1, i + 1,
                         "example", "Example", "backmarker", 9, 10, None, "unavailable", 1,
                         0, 0, 0, f"2023-12-{i + 1:02d}", fallback_detail, "now"))
                probs, runs, _ = _profile(
                    store, RunnerInput(1, "Example", 1), "2025-01-01",
                    track_slug="randwick", distance_metres=1000, going="Soft 5")
                self.assertEqual(runs, 4)
                self.assertGreater(probs["leader"], probs["backmarker"])
            finally:
                store.close()

    def test_empty_history_is_a_blocked_evaluation(self):
        with TemporaryDirectory() as folder:
            store = RacingStore(Path(folder) / "test.sqlite")
            try:
                self.assertEqual(evaluate_history(store)["status"], "BLOCKED_NO_LABELLED_HISTORY")
            finally:
                store.close()

if __name__ == "__main__": unittest.main()
