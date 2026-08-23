import json
import tempfile
import unittest
from pathlib import Path

from racing_engine.context_features import _number, build_all, weight_condition
from racing_engine.storage import RacingStore


class ContextFeatureTests(unittest.TestCase):
    def test_weight_condition_precedence(self):
        self.assertEqual(weight_condition("Set Weights plus Penalties", None), "set_weights_plus_penalties")
        self.assertEqual(weight_condition("Handicap", "BM78 Handicap"), "handicap")
        self.assertEqual(weight_condition(None, None), "unknown")
        self.assertEqual(_number({"raw_entry":{"weight":"59.5kg"}},("raw_entry","weight")),59.5)

    def test_point_in_time_row_uses_only_previous_race(self):
        with tempfile.TemporaryDirectory() as folder:
            store=RacingStore(Path(folder)/"test.sqlite")
            for day,number,weight,rating in (("2024-01-01",1,55.0,70),("2024-02-01",2,57.0,74)):
                store.upsert_result(source="x",race_date=day,track_slug="track",race_number=number,state="NSW",distance_metres=1200,race_class="Handicap",race_class_code=None,scheduled_start_at=None,official_time_seconds=70,track_condition="Good",rail_position=None,source_url=None,raw_race={},runners=[{"runner_number":1,"runner_name":"HORSE","finish_position":1,"weight_carried_kg":weight,"official_handicap_rating":rating}])
                store.connection.execute("INSERT INTO horses VALUES (?,?,?,?,?,?,?)",("h1","HORSE","horse","automatic","{}","now","now")) if number==1 else None
                store.connection.execute("INSERT INTO runner_horse_links VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",("x",day,"track",number,1,"h1","HORSE","horse","exact",1.0,"automatic","{}","now"))
                store.connection.execute("INSERT INTO race_classifications VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",("x",day,"track",number,"Handicap","benchmark",None,70,None,None,None,"Handicap","v","now"))
            store.connection.commit(); report=build_all(store)
            row=store.connection.execute("SELECT * FROM point_in_time_features WHERE target_race_date='2024-02-01'").fetchone()
            self.assertEqual(row["history_runs"],1); self.assertEqual(row["prior_weight_kg"],55.0)
            self.assertTrue(json.loads(row["availability_json"])["current_result_weight_excluded"])
            self.assertEqual(report["baseline"]["status"],"frozen")
            store.close()

if __name__ == "__main__": unittest.main()
