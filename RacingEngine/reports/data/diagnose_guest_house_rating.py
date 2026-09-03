"""Trace Guest House's accepted rating and age/cohort diagnostics."""
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
db = sqlite3.connect(ROOT / "data/racing_engine.sqlite")
db.row_factory = sqlite3.Row

race = db.execute("""
SELECT * FROM v2_clean_races WHERE race_date='2026-08-29' AND track_slug='rosehill' AND race_number=8
""").fetchone()
print("RACE", dict(race))
rows = db.execute("""
SELECT c.*,p.performance_rating,p.race_strength,p.class_standard,p.anchor_coverage,
       p.confidence,p.detail_json
FROM v2_clean_runner_results c JOIN v2_run_performances p USING(race_id,runner_number)
WHERE c.race_id=? AND p.model_version='form-first-v2.0'
ORDER BY c.finish_position
""", (race["race_id"],)).fetchall()
for row in rows:
    item = dict(row)
    item["detail_json"] = json.loads(item["detail_json"])
    priors = db.execute("""
    SELECT r.race_date,p.performance_rating,c.official_handicap_rating,c.finish_position
    FROM v2_run_performances p JOIN v2_clean_races r USING(race_id)
    JOIN v2_clean_runner_results c USING(race_id,runner_number)
    WHERE p.model_version='form-first-v2.0' AND p.horse_key=? AND r.race_date<?
    ORDER BY r.race_date DESC LIMIT 3
    """, (row["horse_key"], race["race_date"])).fetchall()
    item["three_prior_runs"] = [dict(value) for value in priors]
    print("RUNNER", json.dumps(item, default=str))

cohort = [dict(row) for row in db.execute("""
SELECT r.race_date,r.race_id,r.race_class,r.class_family,
       c.horse_name,c.official_handicap_rating,p.performance_rating,
       p.race_strength,p.class_standard,p.anchor_coverage
FROM v2_clean_races r JOIN v2_clean_runner_results c USING(race_id)
JOIN v2_run_performances p USING(race_id,runner_number)
WHERE p.model_version='form-first-v2.0' AND c.finish_position=1
  AND r.race_date>='2023-09-01' AND r.class_family IN ('listed','group_3','group_2','group_1')
""")]
for item in cohort:
    text = item["race_class"].lower()
    item["cohort"] = ("3yo_only" if "three-years-old" in text and "upwards" not in text
                      else "2yo_only" if "two-years-old" in text and "upwards" not in text
                      else "open_age")
for cohort_name in ("2yo_only", "3yo_only", "open_age"):
    sample = [item for item in cohort if item["cohort"] == cohort_name]
    with_official = [item for item in sample if item["official_handicap_rating"] is not None]
    def avg(values):
        return sum(values) / len(values) if values else None
    print("COHORT", json.dumps({
        "cohort": cohort_name, "winner_runs": len(sample),
        "mean_rating_minus_class_standard": avg([item["performance_rating"] - item["class_standard"] for item in sample]),
        "official_coverage": len(with_official),
        "mean_rating_minus_official": avg([item["performance_rating"] - item["official_handicap_rating"] for item in with_official]),
        "rated_below_official_rate": avg([item["performance_rating"] < item["official_handicap_rating"] for item in with_official]),
    }))

for family in ("group_1", "group_2", "group_3", "listed"):
    for cohort_name in ("2yo_only", "3yo_only", "open_age"):
        sample = [item for item in cohort if item["cohort"] == cohort_name and item["class_family"] == family]
        with_official = [item for item in sample if item["official_handicap_rating"] is not None]
        if not sample:
            continue
        print("GRADE_COHORT", json.dumps({
            "class_family": family, "cohort": cohort_name, "winner_runs": len(sample),
            "mean_rating_minus_class_standard": avg([item["performance_rating"] - item["class_standard"] for item in sample]),
            "official_coverage": len(with_official),
            "mean_rating_minus_official": avg([item["performance_rating"] - item["official_handicap_rating"] for item in with_official]),
            "rated_below_official_rate": avg([item["performance_rating"] < item["official_handicap_rating"] for item in with_official]),
        }))

print("LOWEST_AGE_GROUP_WINNERS")
for item in sorted(
    [value for value in cohort if value["cohort"] in ("2yo_only", "3yo_only")],
    key=lambda value: value["performance_rating"] - value["class_standard"],
)[:20]:
    print(json.dumps(item, default=str))

for table in ("v2_race_time_evidence", "v2_race_pace_shapes", "v2_runner_energy_sectionals",
              "v2_runner_pace_ratings", "v2_achieved_run_candidates"):
    exists = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
    if not exists:
        continue
    columns = [row[1] for row in db.execute(f"PRAGMA table_info({table})")]
    where = []
    args = []
    if "race_id" in columns:
        where.append("race_id=?"); args.append(race["race_id"])
    if "horse_key" in columns:
        where.append("horse_key='guesthouse'")
    found = [dict(row) for row in db.execute(
        f"SELECT * FROM {table}" + (" WHERE " + " AND ".join(where) if where else " LIMIT 0"), args
    ).fetchall()]
    print("SHADOW", table, json.dumps(found, default=str))
