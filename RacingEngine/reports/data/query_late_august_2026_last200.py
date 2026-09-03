"""Report the fastest final 200m sections in Sydney, 24-30 August 2026."""
import csv
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "data/racing_engine.sqlite"
OUT = Path(__file__).with_name("sydney_fastest_last200_2026-08-24_to_2026-08-30.csv")

db = sqlite3.connect(DB)
db.row_factory = sqlite3.Row
rows = db.execute("""
SELECT s.race_date,s.track_slug,s.race_number,s.runner_number,
       rr.runner_name,rr.finish_position,rr.beaten_lengths,
       s.section_seconds AS last_200_seconds
FROM runner_sectionals s
JOIN runner_results rr
  ON rr.source=s.source AND rr.race_date=s.race_date
 AND rr.track_slug=s.track_slug AND rr.race_number=s.race_number
 AND rr.runner_number=s.runner_number
WHERE s.source='racing-com-nsw-authorised-v2'
  AND s.race_date>='2026-08-24' AND s.race_date<'2026-08-31'
  AND s.track_slug IN ('randwick','rosehill')
  AND s.marker_metres=0 AND s.section_seconds BETWEEN 8 AND 20
  AND rr.finish_position IS NOT NULL
ORDER BY s.section_seconds, s.race_number, rr.finish_position
""").fetchall()

with OUT.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=rows[0].keys() if rows else [])
    if rows:
        writer.writeheader()
        writer.writerows(dict(row) for row in rows)

for row in rows[:10]:
    print(dict(row))
print(f"runners={len(rows)} output={OUT}")
