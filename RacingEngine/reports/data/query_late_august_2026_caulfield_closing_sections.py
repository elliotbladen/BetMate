"""Rank Caulfield closing 200m and 400m sections for 24-30 August 2026."""
import csv
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
db = sqlite3.connect(ROOT / "data/racing_engine.sqlite")
db.row_factory = sqlite3.Row

print("meetings", [dict(row) for row in db.execute("""
SELECT race_date,track_slug,source,COUNT(*) AS races
FROM race_results
WHERE race_date>='2026-08-24' AND race_date<'2026-08-31'
  AND (track_slug LIKE '%caulfield%' OR track_slug LIKE '%sandown%' OR track_slug LIKE '%flemington%')
GROUP BY race_date,track_slug,source ORDER BY race_date,track_slug,source
""")])
print("sectional meetings", [dict(row) for row in db.execute("""
SELECT race_date,track_slug,source,COUNT(*) AS rows
FROM runner_sectionals
WHERE race_date>='2026-08-24' AND race_date<'2026-08-31'
  AND (track_slug LIKE '%caulfield%' OR track_slug LIKE '%sandown%' OR track_slug LIKE '%flemington%')
GROUP BY race_date,track_slug,source ORDER BY race_date,track_slug,source
""")])
print("markers", [dict(row) for row in db.execute("""
SELECT marker_metres,COUNT(*) AS rows,MIN(section_seconds) AS fastest,MAX(section_seconds) AS slowest
FROM runner_sectionals WHERE race_date='2026-08-29' AND track_slug='caulfield'
GROUP BY marker_metres ORDER BY marker_metres
""")])


def query(markers: tuple[int, ...], label: str):
    placeholders = ",".join("?" for _ in markers)
    rows = db.execute(f"""
    SELECT s.race_date,s.track_slug,s.race_number,s.runner_number,
           rr.runner_name,rr.finish_position,rr.beaten_lengths,
           ROUND(SUM(s.section_seconds),3) AS {label}_seconds
    FROM runner_sectionals s
    JOIN runner_results rr
      ON rr.source=s.source AND rr.race_date=s.race_date
     AND rr.track_slug=s.track_slug AND rr.race_number=s.race_number
     AND rr.runner_number=s.runner_number
    WHERE s.race_date>='2026-08-24' AND s.race_date<'2026-08-31'
      AND s.track_slug IN ('caulfield','caulfield-heath')
      AND s.marker_metres IN ({placeholders})
      AND s.section_seconds BETWEEN 18 AND 35
      AND rr.finish_position IS NOT NULL
    GROUP BY s.source,s.race_date,s.track_slug,s.race_number,s.runner_number,
             rr.runner_name,rr.finish_position,rr.beaten_lengths
    HAVING COUNT(DISTINCT s.marker_metres)=?
    ORDER BY {label}_seconds,s.race_number,rr.finish_position
    """, (*markers, len(markers))).fetchall()
    output = Path(__file__).with_name(
        f"caulfield_fastest_{label}_2026-08-24_to_2026-08-30.csv")
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys() if rows else [])
        if rows:
            writer.writeheader()
            writer.writerows(dict(row) for row in rows)
    print(label, "runners", len(rows), "output", output)
    for row in rows[:10]:
        print(dict(row))


# Racing Victoria's stored feed is supplied in 400m blocks: marker 0 is the
# final 400m. It does not support an honest final-200 ranking for this meeting.
query((0,), "last400")
