import copy
import math
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from racing_engine.evaluation_protocol import (
    assess_eligibility, load_protocol, period_for, protocol_hash, score_race,
    validate_probability_book, validate_protocol,
)
from racing_engine.performance import run_pipeline
from racing_engine.storage import RacingStore


class EvaluationProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.protocol = load_protocol()

    def test_period_boundaries_are_fixed_and_non_overlapping(self) -> None:
        self.assertEqual(period_for("2024-08-31", self.protocol), "train")
        self.assertEqual(period_for("2024-09-01", self.protocol), "validation")
        self.assertEqual(period_for("2025-09-01", self.protocol), "historical_holdout")
        self.assertEqual(period_for("2026-08-16", self.protocol), "prospective_holdout")

    def test_invalid_or_changed_protocol_is_detectable(self) -> None:
        changed = copy.deepcopy(self.protocol)
        changed["periods"]["validation"]["from"] = "2024-08-31"
        with self.assertRaisesRegex(ValueError, "overlaps"):
            validate_protocol(changed)
        changed = copy.deepcopy(self.protocol)
        changed["resampling"]["seed"] += 1
        self.assertNotEqual(protocol_hash(changed), protocol_hash(self.protocol))

    def test_starters_include_dnf_but_not_scratches(self) -> None:
        result = assess_eligibility([
            {"runner_number": 1, "runner_name": "Winner", "finish_position": 1, "result_status": "finished"},
            {"runner_number": 2, "runner_name": "DNF", "finish_position": None, "result_status": "did_not_finish"},
            {"runner_number": 3, "runner_name": "Scratched", "finish_position": None, "result_status": "scratched"},
        ], self.protocol)
        self.assertTrue(result.eligible)
        self.assertEqual([row["runner_name"] for row in result.starters], ["Winner", "DNF"])

    def test_exclusion_reasons_are_mutually_specific(self) -> None:
        missing = assess_eligibility([
            {"runner_number": 1, "runner_name": "One", "finish_position": 2},
            {"runner_number": 2, "runner_name": "Two", "finish_position": 3},
        ], self.protocol)
        dead_heat = assess_eligibility([
            {"runner_number": 1, "runner_name": "One", "finish_position": 1},
            {"runner_number": 2, "runner_name": "Two", "finish_position": 1},
        ], self.protocol)
        self.assertEqual(missing.reason, "missing_winner")
        self.assertEqual(dead_heat.reason, "multiple_winners")

    def test_metrics_match_hand_calculation(self) -> None:
        result = score_race([0.7, 0.2, 0.1], [1, 0, 0], self.protocol)
        self.assertAlmostEqual(result["log_loss"], -math.log(0.7))
        self.assertAlmostEqual(result["race_brier"], 0.14)
        self.assertAlmostEqual(result["runner_brier"], 0.14 / 3)
        self.assertEqual(result["winner_rank"], 1)
        with self.assertRaisesRegex(ValueError, "sum"):
            validate_probability_book([0.4, 0.4], 2)

    def test_future_result_cannot_change_earlier_state(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            store = RacingStore(Path(temporary_directory) / "test.sqlite")
            try:
                self._add_race(store, "2024-01-01", 70.0, "Past Horse")
                first = run_pipeline(store, "2024-02-01", min_par_sample=1)
                state_before = store.connection.execute(
                    "SELECT overall_rating FROM horse_rating_states WHERE as_of_date='2024-02-01' AND horse_key='pasthorse'"
                ).fetchone()[0]
                self._add_race(store, "2025-01-01", 20.0, "Past Horse")
                second = run_pipeline(store, "2024-02-01", min_par_sample=1)
                state_after = store.connection.execute(
                    "SELECT overall_rating FROM horse_rating_states WHERE as_of_date='2024-02-01' AND horse_key='pasthorse'"
                ).fetchone()[0]
                self.assertEqual(first, second)
                self.assertEqual(state_before, state_after)
            finally:
                store.close()

    @staticmethod
    def _add_race(store: RacingStore, race_date: str, time: float, horse: str) -> None:
        store.upsert_result(
            source="test", race_date=race_date, state="NSW", track_slug="randwick", race_number=1,
            distance_metres=1200, official_time_seconds=time, track_condition="Good 4", rail_position="True",
            source_url=None, raw_race={}, runners=[
                {"runner_number": 1, "runner_name": horse, "finish_position": 1,
                 "finish_time_seconds": time, "beaten_lengths": 0.0},
                {"runner_number": 2, "runner_name": "Other", "finish_position": 2,
                 "finish_time_seconds": time + 0.2, "beaten_lengths": 1.0},
            ],
        )


if __name__ == "__main__":
    unittest.main()
