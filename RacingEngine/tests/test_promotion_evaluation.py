import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from racing_engine.horse_identity import build_registry
from racing_engine.promotion_evaluation import paired_interval, run_evaluation
from racing_engine.step11_models import VARIANTS as STEP11_VARIANTS, build_step11_variants
from racing_engine.storage import RacingStore


class PromotionEvaluationTests(unittest.TestCase):
    def test_paired_interval_is_deterministic_and_preserves_meeting_blocks(self) -> None:
        rows = [
            {"source": "a", "race_date": "2024-01-01", "track_slug": "x",
             "candidate_log_loss": 1.0, "baseline_log_loss": 2.0},
            {"source": "a", "race_date": "2024-01-01", "track_slug": "x",
             "candidate_log_loss": 2.0, "baseline_log_loss": 3.0},
            {"source": "a", "race_date": "2024-01-02", "track_slug": "y",
             "candidate_log_loss": 1.5, "baseline_log_loss": 2.0},
        ]
        first = paired_interval(rows, 200, .95, 7)
        self.assertEqual(first, paired_interval(rows, 200, .95, 7))
        self.assertEqual(first["blocks"], 2)
        self.assertAlmostEqual(first["delta"], -2.5 / 3)
        self.assertLess(first["upper"], 0)

    def test_all_models_use_the_same_races_runners_and_exclusive_cutoff(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory); store = RacingStore(root / "test.sqlite")
            try:
                self._race(store, "2024-01-01", 1, "Alpha 1 70.0", "Beta", 70.0)
                self._race(store, "2024-01-02", 2, "Alpha", "Gamma", 71.0)
                self._race(store, "2024-01-03", 3, "Alpha", "Delta", 72.0)
                build_registry(store)
                for date, number in (("2024-01-01", 1), ("2024-01-02", 2)):
                    self._strength(store, date, number)
                protocol_path = root / "protocol.json"; protocol_path.write_text(json.dumps(self._protocol()))
                report = run_evaluation(store, protocol_path=protocol_path, min_par_sample=1, repetitions=100)
                self.assertEqual(report["common_sample"]["eligible_races"], 2)
                for candidate in report["candidates"].values():
                    self.assertEqual(candidate["coverage"]["eligible_races"], 2)
                    self.assertEqual(candidate["coverage"]["runners"], 4)
                row = store.connection.execute(
                    """SELECT history_depth,detail_json FROM benchmark_predictions
                       WHERE model_version='performance-par-v1.0+identity-v1.0' AND race_date='2024-01-02'
                         AND runner_number=1""").fetchone()
                self.assertEqual(row["history_depth"], 1)
                self.assertEqual(json.loads(row["detail_json"])["state_cutoff_exclusive"], "2024-01-02")
                step11 = run_evaluation(store, protocol_path=protocol_path, min_par_sample=1, repetitions=20,
                    candidate_models=STEP11_VARIANTS, candidate_builder=build_step11_variants,
                    candidate_key_modes={name: "raw" for name in STEP11_VARIANTS}, report_name="step11-test")
                self.assertLess(step11["candidates"]["daily_variant"]["coverage"]["unrated_runners"], 4)
            finally:
                store.close()

    @staticmethod
    def _protocol():
        return {
            "protocol_version": "evaluation-v1",
            "periods": {"train": {"from": "2024-01-01", "to": "2024-01-01"},
                        "validation": {"from": "2024-01-02", "to": "2024-01-02"},
                        "historical_holdout": {"from": "2024-01-03", "to": "2024-01-03"},
                        "prospective_holdout": {"from": "2024-01-04", "to": None}},
            "eligibility": {"minimum_starters": 2, "required_winners": 1,
                            "starter_excluded_statuses": ["scratched", "non_starter", "abandoned"],
                            "dead_heat_policy": "exclude", "unrated_runner_policy": "population_prior",
                            "population_prior_rating": 100.0, "same_runner_set_required": True},
            "metrics": {"primary": "race_weighted_log_loss", "secondary": [],
                        "probability_floor": 1e-12, "calibration_edges": [0, .5, 1]},
            "segments": {"distance_metres": [1200, 1600, 2000], "field_size": [8, 12],
                         "history_depth": [0, 2, 5], "dimensions": []},
            "resampling": {"unit": "meeting_day", "repetitions": 100,
                           "confidence_level": .95, "seed": 7},
            "promotion_rules": {"validation_primary_must_improve": True,
                                "paired_interval_must_exclude_no_improvement": True,
                                "holdout_direction_must_agree": True,
                                "maximum_coverage_drop_percentage_points": 1.0,
                                "decisions": ["PROMOTE", "REVISE", "REJECT", "INSUFFICIENT_EVIDENCE"]}}

    @staticmethod
    def _race(store, date, number, first, second, seconds):
        store.upsert_result(source="rnsw-authorised", race_date=date, state="NSW", track_slug="randwick",
            race_number=number, distance_metres=1200, official_time_seconds=seconds, track_condition="Good 4",
            rail_position="True", source_url=None, raw_race={}, runners=[
                {"runner_number": 1, "runner_name": first, "finish_position": 1,
                 "finish_time_seconds": seconds, "beaten_lengths": 0.0},
                {"runner_number": 2, "runner_name": second, "finish_position": 2,
                 "finish_time_seconds": seconds + .2, "beaten_lengths": 1.0}])

    @staticmethod
    def _strength(store, date, number):
        store.connection.execute(
            """INSERT INTO race_strength_ratings
               (race_strength_version,source,race_date,track_slug,race_number,class_prior_level,class_prior_key,
                class_prior_official_scale,class_global_official_scale,class_only_rating,class_reliability,
                field_only_rating,field_reliability,combined_rating,rated_coverage,field_uncertainty,
                information_cutoff,component_json,created_at)
               VALUES ('race-strength-v1.0','rnsw-authorised',?,'randwick',?,'class_family','NSW|group',90,80,
                       110,.8,103,.5,108,.7,6,?,'{}','now')""", (date, number, date))
        store.connection.commit()


if __name__ == "__main__":
    unittest.main()
