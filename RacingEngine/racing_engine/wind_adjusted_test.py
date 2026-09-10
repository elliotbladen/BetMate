"""Randwick-only wind sensitivity test.

This is a shadow experiment, not a production weather model.  Randwick's
published orientation is clockwise; for this first test we use a conservative
eastbound home-straight bearing and expose only 25% of the race to the wind.
The result is deliberately easy to audit before adding track geometry and
runner-level in-running position data.
"""
from __future__ import annotations

import argparse
import json
import math
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL = "dan-aligned-wind-test-randwick-v0.2"
WEATHER_SOURCE = "wunderground-observed-halfhour-v1"
POINTS_PER_KMH = 0.10
EXPOSURE = 0.25
HOME_STRAIGHT_BEARING = 90.0


def wind_component(speed_kmh: float, from_deg: float, heading_deg: float = HOME_STRAIGHT_BEARING) -> float:
    """Positive = tailwind, negative = headwind along the test heading."""
    toward = (from_deg + 180.0) % 360.0
    delta = math.radians(toward - heading_deg)
    return speed_kmh * math.cos(delta)


def build(database: Path) -> dict:
    c = sqlite3.connect(database)
    c.row_factory = sqlite3.Row
    c.execute("DROP TABLE IF EXISTS wind_adjusted_run_test")
    c.execute("""CREATE TABLE IF NOT EXISTS wind_adjusted_run_test (
      model_version TEXT NOT NULL, race_id TEXT NOT NULL, runner_number INTEGER NOT NULL,
      race_number INTEGER NOT NULL, horse_name TEXT NOT NULL, base_rating REAL NOT NULL, wind_adjustment REAL NOT NULL,
      adjusted_rating REAL NOT NULL, wind_component_kmh REAL NOT NULL,
      wind_speed_kmh REAL NOT NULL, wind_direction_deg REAL NOT NULL,
      exposure_factor REAL NOT NULL, detail_json TEXT NOT NULL, PRIMARY KEY(model_version,race_id,runner_number))""")
    c.execute("DELETE FROM wind_adjusted_run_test WHERE model_version=?", (MODEL,))
    rows = c.execute("""SELECT d.race_id,d.runner_number,d.horse_name,d.performance_rating,
                              r.race_number,r.distance_metres,
                              w.wind_speed_kmh,w.wind_direction_deg,
                              cr.finish_position
                         FROM dan_aligned_run_performances d
                         JOIN v2_clean_races r ON r.race_id=d.race_id
                         JOIN v2_clean_runner_results cr ON cr.race_id=d.race_id
                            AND cr.runner_number=d.runner_number
                         JOIN race_weather w ON w.source=r.source AND w.race_date=r.race_date
                            AND w.track_slug=r.track_slug AND w.race_number=r.race_number
                            AND w.weather_source=?
                        WHERE d.model_version='dan-aligned-wfa-v0.1'
                          AND r.race_date='2026-09-05' AND r.track_slug='randwick'""",
                   (WEATHER_SOURCE,)).fetchall()
    # Use the last available sectional position as a simple exposure proxy:
    # leaders are more exposed to a head/tail wind, while rearward runners are
    # partly sheltered. This is still a test proxy, not full tracking data.
    pos = {}
    for s in c.execute("""SELECT runner_number,MAX(marker_metres) max_marker,
                                 position_at_marker
                            FROM runner_sectionals
                           WHERE source='racing-com-nsw-authorised-v2'
                             AND race_date='2026-09-05' AND track_slug='randwick'
                           GROUP BY race_number,runner_number"""):
        pos[(s["runner_number"],)] = s["position_at_marker"]
    field_sizes = {}
    for r in rows:
        field_sizes[r["race_number"]] = max(field_sizes.get(r["race_number"], 0), int(r["runner_number"]))
    for row in rows:
        comp = wind_component(float(row["wind_speed_kmh"]), float(row["wind_direction_deg"]))
        # Tailwind makes the achieved clock look faster, so reduce the rating;
        # headwind does the opposite.  Same race-level correction for now:
        # runner-specific exposure needs tracking/in-running position data.
        # The table has no race number in the sectional key, so retrieve the
        # final position directly for this race/runner.
        s = c.execute("""SELECT position_at_marker FROM runner_sectionals
                          WHERE source='racing-com-nsw-authorised-v2'
                            AND race_date='2026-09-05' AND track_slug='randwick'
                            AND race_number=? AND runner_number=?
                          ORDER BY marker_metres DESC LIMIT 1""",
                      (row["race_number"], row["runner_number"])).fetchone()
        field = c.execute("""SELECT COUNT(*) FROM v2_clean_runner_results cr
                              JOIN v2_clean_races r ON r.race_id=cr.race_id
                             WHERE r.race_date='2026-09-05' AND r.track_slug='randwick'
                               AND r.race_number=? AND cr.result_status='finished'""",
                         (row["race_number"],)).fetchone()[0]
        final_pos = int(s[0]) if s and s[0] is not None else max(1, field // 2)
        exposure_factor = 1.0 if field <= 1 else 1.0 - 0.5 * ((final_pos - 1) / max(1, field - 1))
        adj = -comp * POINTS_PER_KMH * EXPOSURE * exposure_factor
        detail = {"method": MODEL, "wind_source": WEATHER_SOURCE,
                  "home_straight_bearing_deg": HOME_STRAIGHT_BEARING,
                  "wind_component_kmh": comp, "points_per_kmh": POINTS_PER_KMH,
                  "race_exposure": EXPOSURE,
                  "runner_specific_exposure": True, "final_section_position": final_pos,
                  "exposure_factor": exposure_factor}
        c.execute("INSERT INTO wind_adjusted_run_test VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                  (MODEL,row["race_id"],row["runner_number"],row["race_number"],row["horse_name"],
                   row["performance_rating"],adj,row["performance_rating"]+adj,comp,
                   row["wind_speed_kmh"],row["wind_direction_deg"],exposure_factor,json.dumps(detail,sort_keys=True)))
    c.commit()
    race = c.execute("""SELECT race_number,wind_speed_kmh,wind_direction_deg,
                              wind_component_kmh,wind_adjustment
                         FROM wind_adjusted_run_test WHERE model_version=?
                        GROUP BY race_number ORDER BY race_number""", (MODEL,)).fetchall()
    top = c.execute("""SELECT horse_name,adjusted_rating,base_rating,race_id,runner_number
                         FROM wind_adjusted_run_test WHERE model_version=?
                        ORDER BY adjusted_rating DESC LIMIT 20""", (MODEL,)).fetchall()
    c.close()
    return {"model_version": MODEL, "runners": len(rows), "races": [dict(x) for x in race],
            "top": [dict(x) for x in top], "status": "shadow_test_only"}


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--database", type=Path, default=ROOT / "data/racing_engine.sqlite")
    print(json.dumps(build(ap.parse_args().database), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
