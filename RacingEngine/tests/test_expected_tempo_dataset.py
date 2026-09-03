import json
import tempfile
import unittest
from pathlib import Path

from racing_engine.expected_tempo_dataset import _as_utc, _going_bucket, write_artifacts


class ExpectedTempoDatasetTests(unittest.TestCase):
    def test_going_bucket_keeps_conditions_separate(self):
        self.assertEqual(_going_bucket("Good 4"), "good")
        self.assertEqual(_going_bucket("Soft 7"), "soft")
        self.assertEqual(_going_bucket("Heavy 10"), "heavy")
        self.assertIsNone(_going_bucket(None))

    def test_timestamp_parser_normalises_utc(self):
        self.assertLess(
            _as_utc("2026-08-15T01:00:00Z"),
            _as_utc("2026-08-15T02:00:00+00:00"),
        )

    def test_artifact_contract_separates_features_and_targets(self):
        row = {
            "dataset_version": "test", "race_date": "2026-01-01", "state": "NSW",
            "feature_going_bucket": "soft", "feature_rail_position": None,
            "feature_group_grade": 1, "feature_profiled_runner_coverage": 0.5,
            "feature_temperature_c": 20.0, "feature_wind_speed_kmh": 10.0,
            "feature_weather_point_in_time_safe": 1,
            "target_early_score": 1.0, "target_middle_score": 0.0,
            "target_late_score": -1.0, "target_pace_label": "pace_collapse",
        }
        with tempfile.TemporaryDirectory() as folder:
            report = write_artifacts([row], Path(folder))
            schema = json.loads(Path(report["schema"]).read_text(encoding="utf-8"))
            self.assertIn("feature_prefix", schema)
            self.assertIn("target_prefix", schema)
            self.assertEqual(report["rows"], 1)


if __name__ == "__main__":
    unittest.main()
