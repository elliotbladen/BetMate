from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from racing_engine.readiness import build_report, render_markdown
from racing_engine.storage import RacingStore


class ReadinessReportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        self.store = RacingStore(Path(self.temporary_directory.name) / "test.sqlite")

    def tearDown(self) -> None:
        self.store.close()
        self.temporary_directory.cleanup()

    def add_race(self, *, official_time=70.0, runners=None) -> None:
        runners = runners if runners is not None else [
            {"runner_number": 1, "runner_name": "Winner", "finish_position": 1,
             "beaten_lengths": 0.0, "finish_time_seconds": 70.0, "barrier": 1,
             "weight_carried_kg": 58.0, "jockey": "A Rider", "trainer": "A Trainer",
             "official_handicap_rating": 80, "distance_travelled_vs_winner_metres": 0.0},
            {"runner_number": 2, "runner_name": "Second", "finish_position": 2,
             "beaten_lengths": 1.0, "finish_time_seconds": 70.17, "barrier": 2,
             "weight_carried_kg": 57.0, "jockey": "B Rider", "trainer": "B Trainer",
             "official_handicap_rating": 75, "distance_travelled_vs_winner_metres": 1.2},
        ]
        self.store.upsert_result(
            source="test-source", race_date="2026-08-01", state="NSW", track_slug="randwick",
            race_number=1, distance_metres=1200, official_time_seconds=official_time,
            track_condition="Good 4", rail_position="True", source_url=None, raw_race={}, runners=runners,
        )

    def add_supporting_data(self, *, steward_status="complete", add_card=True) -> None:
        self.store.upsert_race_classification({
            "source": "test-source", "race_date": "2026-08-01", "track_slug": "randwick",
            "race_number": 1, "class_family": "benchmark", "raw_class_text": "BM78", "parser_version": "test",
        })
        self.store.upsert_race_weather({
            "source": "test-source", "race_date": "2026-08-01", "track_slug": "randwick", "race_number": 1,
            "weather_source": "test", "station_id": "station", "observed_at": "2026-08-01T01:00:00Z",
            "quality": {}, "raw": {},
        })
        if steward_status:
            self.store.record_steward_report_check(
                report_source="test-stewards", race_date="2026-08-01", track_slug="randwick",
                status=steward_status, detail="test",
            )
        if add_card:
            self.store.upsert_card("2026-08-01", "NSW", {"track": "Randwick", "slug": "randwick"}, [{
                "raceNumber": 1, "runners": [
                    {"number": 1, "name": "Winner"}, {"number": 2, "name": "Second"},
                ],
            }])
        self.store.upsert_sectionals([
            {"source": "test-source", "race_date": "2026-08-01", "track_slug": "randwick",
             "race_number": 1, "runner_number": number, "marker_metres": 200, "section_seconds": seconds}
            for number, seconds in ((1, 11.0), (2, 11.2))
        ])

    def test_complete_fixture_is_ready(self) -> None:
        self.add_race()
        self.add_supporting_data()
        report = build_report(self.store.connection, generated_at="fixed")
        self.assertEqual(report["readiness"]["status"], "READY")
        self.assertEqual(report["totals"]["races"], 1)
        self.assertFalse(report["gaps"])

    def test_structural_gaps_are_blocking_and_traceable(self) -> None:
        self.add_race(official_time=None, runners=[])
        report = build_report(self.store.connection, generated_at="fixed")
        self.assertEqual(report["readiness"]["status"], "NOT_READY")
        self.assertTrue({"runner_results", "winner", "official_time", "class", "weather", "steward_check"}
                        <= set(report["readiness"]["blocking_reasons"]))
        official_gap = next(g for g in report["gaps"] if g["check"] == "official_time")
        self.assertEqual((official_gap["track_slug"], official_gap["race_number"]), ("randwick", 1))

    def test_non_finisher_does_not_require_time_or_margin(self) -> None:
        runners = [
            {"runner_number": 1, "runner_name": "Winner", "finish_position": 1, "beaten_lengths": 0.0,
             "finish_time_seconds": 70.0, "result_status": "finished"},
            {"runner_number": 2, "runner_name": "DNF", "finish_position": None, "beaten_lengths": None,
             "finish_time_seconds": None, "result_status": "did_not_finish"},
        ]
        self.add_race(runners=runners)
        report = build_report(self.store.connection, generated_at="fixed")
        self.assertEqual(report["checks"]["runner_time"]["eligible"], 1)
        self.assertEqual(report["checks"]["margins"]["eligible"], 1)

    def test_checked_absence_is_a_complete_steward_check(self) -> None:
        self.add_race()
        self.add_supporting_data(steward_status="no_report")
        report = build_report(self.store.connection, generated_at="fixed")
        self.assertEqual(report["checks"]["steward_check"]["complete"], 1)
        self.assertNotIn("steward_check", report["readiness"]["blocking_reasons"])

    def test_missing_optional_data_yields_warning_not_zero(self) -> None:
        self.add_race()
        self.add_supporting_data(add_card=False)
        self.store.connection.execute(
            "UPDATE runner_results SET distance_travelled_vs_winner_metres=NULL WHERE runner_number=2")
        report = build_report(self.store.connection, generated_at="fixed")
        self.assertEqual(report["readiness"]["status"], "READY_WITH_WARNINGS")
        self.assertEqual(report["checks"]["dtw"]["missing"], 1)
        self.assertEqual(report["checks"]["pre_race_card"]["missing"], 1)

    def test_filters_and_renderers_share_report(self) -> None:
        self.add_race()
        self.add_supporting_data()
        excluded = build_report(self.store.connection, states=["VIC"], generated_at="fixed")
        self.assertEqual(excluded["totals"]["races"], 0)
        self.assertEqual(excluded["readiness"]["status"], "NOT_READY")
        self.assertIn("no_data", excluded["readiness"]["blocking_reasons"])
        report = build_report(self.store.connection, states=["NSW"], generated_at="fixed")
        markdown = render_markdown(report)
        self.assertIn("Status: **READY**", markdown)
        self.assertIn("| official_time | 1 | 1 | 100.00% | blocking |", markdown)


if __name__ == "__main__":
    unittest.main()
