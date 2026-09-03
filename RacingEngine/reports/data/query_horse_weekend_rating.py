"""Print accepted and shadow evidence for a named horse on a race date."""
import argparse
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument("horse")
parser.add_argument("race_date")
args = parser.parse_args()

db = sqlite3.connect(ROOT / "data" / "racing_engine.sqlite")
db.row_factory = sqlite3.Row
key = "".join(ch for ch in args.horse.lower() if ch.isalnum())
rows = db.execute(
    """SELECT r.race_date,r.track_slug,r.race_number,r.race_class,r.class_family,
              r.distance_metres,r.official_time_seconds,c.horse_name,c.finish_position,
              c.beaten_lengths,c.weight_carried_kg,c.official_handicap_rating,
              p.performance_rating accepted_rating,p.race_strength accepted_strength,
              a.achieved_rating shadow_rating,a.race_strength shadow_strength,
              a.winner_margin_component,a.detail_json shadow_detail
         FROM v2_clean_runner_results c JOIN v2_clean_races r USING(race_id)
         JOIN v2_run_performances p USING(race_id,runner_number)
         LEFT JOIN v2_achieved_run_candidates a USING(race_id,runner_number)
        WHERE (c.horse_key=? OR lower(replace(c.horse_name,' ',''))=?)
          AND r.race_date=? AND p.model_version='form-first-v2.0'
          AND (a.model_version='achieved-run-v2.10-young-wfa-shadow' OR a.model_version IS NULL)""",
    (key, key, args.race_date),
).fetchall()
for row in rows:
    item = dict(row)
    item["shadow_detail"] = json.loads(item["shadow_detail"]) if item["shadow_detail"] else None
    race_id = f"{row['race_date']}|{row['track_slug']}|{row['race_number']}"
    item["time_evidence"] = [dict(value) for value in db.execute(
        "SELECT * FROM v2_race_time_evidence WHERE race_id=?", (race_id,))]
    item["sectional_evidence"] = [dict(value) for value in db.execute(
        "SELECT * FROM v2_runner_energy_sectionals WHERE race_id=? AND horse_key=?", (race_id, key))]
    print(json.dumps(item, indent=2, default=str))
