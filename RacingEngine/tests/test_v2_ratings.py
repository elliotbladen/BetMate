import tempfile
import unittest
from pathlib import Path

from racing_engine.storage import RacingStore
from racing_engine.v2_ratings import (
    MODEL_VERSION, build_form_first, load_audit_set, plausible_race_clock,
    plausible_runner_clock, pounds_per_length, rebuild_clean_history,
)


class V2RatingsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = RacingStore(Path(self.temp.name) / "test.sqlite")

    def tearDown(self):
        self.store.close(); self.temp.cleanup()

    def add_race(self, source, day, runners, official=70.0, race_class="Group 1"):
        self.store.upsert_result(source=source,race_date=day,state="NSW",track_slug="randwick",
            race_number=1,distance_metres=1200,race_class=race_class,race_class_code=None,
            scheduled_start_at=None,official_time_seconds=official,track_condition="Good 4",
            rail_position=None,source_url="https://example.test",raw_race={},runners=runners)

    def test_distance_scale_follows_ifha_anchors(self):
        self.assertEqual(pounds_per_length(1000),3.0)
        self.assertEqual(pounds_per_length(1600),2.0)
        self.assertEqual(pounds_per_length(2800),1.0)
        self.assertGreater(pounds_per_length(1200),pounds_per_length(2400))

    def test_impossible_clocks_are_rejected(self):
        self.assertFalse(plausible_race_clock(2000,77.81)[0])
        self.assertTrue(plausible_race_clock(1200,70.0)[0])
        self.assertFalse(plausible_runner_clock(70.0,60.0,1200)[0])

    def test_pdf_identity_source_is_excluded_and_structured_source_wins(self):
        bad=[{"runner_number":1,"runner_name":"SIRE NAME 3 70.4","finish_position":1,"result_status":"finished"}]
        clean=[{"runner_number":1,"runner_name":"Autumn Glow","finish_position":1,"beaten_lengths":0,
                "official_handicap_rating":110,"weight_carried_kg":56.5,"result_status":"finished"},
               {"runner_number":2,"runner_name":"Good Horse","finish_position":2,"beaten_lengths":2,
                "official_handicap_rating":105,"weight_carried_kg":58,"result_status":"finished"},
               {"runner_number":3,"runner_name":"Third Horse","finish_position":3,"beaten_lengths":3,
                "official_handicap_rating":102,"weight_carried_kg":58,"result_status":"finished"}]
        self.add_race("rnsw-authorised","2025-03-01",bad)
        self.add_race("racing-com-nsw-results-fallback","2025-03-01",clean)
        report=rebuild_clean_history(self.store,"2026-01-01")
        names=[row[0] for row in self.store.connection.execute("SELECT horse_name FROM v2_clean_runner_results")]
        self.assertEqual(report["races"],1); self.assertIn("Autumn Glow",names); self.assertNotIn("SIRE NAME 3 70.4",names)

    def test_form_and_margin_anchor_group_one_winner(self):
        runners=[{"runner_number":1,"runner_name":"Elite Winner","finish_position":1,"beaten_lengths":0,
                  "official_handicap_rating":112,"weight_carried_kg":58,"result_status":"finished"},
                 {"runner_number":2,"runner_name":"Elite Second","finish_position":2,"beaten_lengths":5,
                  "official_handicap_rating":112,"weight_carried_kg":58,"result_status":"finished"},
                 {"runner_number":3,"runner_name":"Elite Third","finish_position":3,"beaten_lengths":6,
                  "official_handicap_rating":110,"weight_carried_kg":58,"result_status":"finished"}]
        self.add_race("racing-com-nsw-results-fallback","2025-03-01",runners)
        rebuild_clean_history(self.store,"2026-01-01"); build_form_first(self.store)
        winner=self.store.connection.execute("SELECT performance_rating FROM v2_run_performances WHERE model_version=? AND runner_number=1",(MODEL_VERSION,)).fetchone()[0]
        second=self.store.connection.execute("SELECT performance_rating FROM v2_run_performances WHERE model_version=? AND runner_number=2",(MODEL_VERSION,)).fetchone()[0]
        self.assertGreater(winner,115); self.assertGreater(winner,second)

    def test_missing_audit_csv_preserves_restored_reference_rows(self):
        missing = Path(self.temp.name) / "missing-audit.csv"
        self.assertEqual(load_audit_set(self.store, missing), 0)
        self.store.connection.execute(
            "INSERT INTO v2_audit_classifications VALUES (?,?,?,?,?,?,?,?)",
            ("2024/25", "Audit Horse", "AUDIT HORSE", 115.0,
             "2025-01-01", "Audit Race", 1, "https://example.test/audit"),
        )
        self.store.connection.commit()

        self.assertEqual(load_audit_set(self.store, missing), 1)
        count = self.store.connection.execute(
            "SELECT count(*) FROM v2_audit_classifications"
        ).fetchone()[0]
        self.assertEqual(count, 1)


if __name__ == "__main__": unittest.main()
