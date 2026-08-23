from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from racing_engine.sectional_features import build_features, derive
from racing_engine.storage import RacingStore


def rows(values):
    return [{"marker_metres": marker, "section_seconds": seconds, "position_at_marker": position}
            for marker, seconds, position in values]


class SectionalFeatureTests(unittest.TestCase):
    def test_nsw_final_intervals_are_summed_from_adjacent_200s(self) -> None:
        result = derive("rnsw-authorised", rows([
            (600, 12.0, 4), (400, 11.8, 3), (200, 11.5, 2), (0, 11.2, 1),
        ]))
        self.assertAlmostEqual(result["final_200_seconds"], 11.2)
        self.assertAlmostEqual(result["final_400_seconds"], 22.7)
        self.assertAlmostEqual(result["final_600_seconds"], 34.5)
        self.assertEqual(result["position_400m"], 3)
        self.assertEqual(result["quality_status"], "ok")

    def test_nsw_does_not_invent_interval_when_adjacent_marker_is_missing(self) -> None:
        result = derive("rnsw-authorised", rows([(400, 23.0, 3), (0, 23.5, 1)]))
        self.assertIsNone(result["final_200_seconds"])
        self.assertIsNone(result["final_400_seconds"])
        self.assertIn("final_200_requires_markers_200_0", result["missing_reasons"])

    def test_victorian_last_400_is_not_called_final_200(self) -> None:
        result = derive("racing-com-rv-authorised", rows([
            (800, 35.95, 7), (400, 23.17, 7), (0, 23.67, None),
        ]))
        self.assertEqual(result["final_400_seconds"], 23.67)
        self.assertIsNone(result["final_200_seconds"])
        self.assertIsNone(result["final_600_seconds"])
        self.assertEqual(result["eight_to_four_seconds"], 23.17)

    def test_unknown_source_and_outlying_values_are_flagged(self) -> None:
        self.assertEqual(derive("unknown", [])["quality_status"], "unsupported_source")
        result = derive("rnsw-authorised", rows([
            (600, 12.0, 1), (400, 11.0, 1), (200, 11.0, 1), (0, 30.0, 1),
        ]))
        self.assertEqual(result["quality_status"], "outlier")
        self.assertTrue(any(reason.startswith("final_200_seconds_outside") for reason in result["missing_reasons"]))

    def test_build_is_idempotent_and_preserves_provenance(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            store = RacingStore(Path(temporary_directory) / "test.sqlite")
            try:
                store.upsert_result(source="rnsw-authorised", race_date="2026-08-01", state="NSW",
                    track_slug="randwick", race_number=1, official_time_seconds=70.0,
                    track_condition="Good 4", rail_position="True", source_url=None, raw_race={}, runners=[
                        {"runner_number": 1, "runner_name": "Runner", "finish_position": 1,
                         "finish_time_seconds": 70.0, "beaten_lengths": 0.0}])
                store.upsert_sectionals([
                    {"source": "rnsw-authorised", "race_date": "2026-08-01", "track_slug": "randwick",
                     "race_number": 1, "runner_number": 1, "marker_metres": marker,
                     "section_seconds": seconds, "position_at_marker": 1}
                    for marker, seconds in ((600, 12.0), (400, 11.8), (200, 11.5), (0, 11.2))])
                first = build_features(store)
                second = build_features(store)
                self.assertEqual(first["coverage_by_source"], second["coverage_by_source"])
                row = store.connection.execute(
                    "SELECT final_600_seconds,derivation_json FROM canonical_sectionals").fetchone()
                self.assertAlmostEqual(row["final_600_seconds"], 34.5)
                self.assertIn('"required_markers": [600, 400, 200, 0]', row["derivation_json"])
                self.assertEqual(store.connection.execute("SELECT count(*) FROM canonical_sectionals").fetchone()[0], 1)
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()
