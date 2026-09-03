"""Audit Sydney runner-level sectional coverage for the trailing three years."""
from __future__ import annotations

import csv
import json
import re
import sqlite3
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent
DB = ROOT / "data" / "racing_engine.sqlite"
OUT = ROOT / "reports" / "data"
END = date(2026, 8, 31)
START = END - timedelta(days=3 * 365)
TRACKS = ("randwick", "rosehill")
DATE_RE = re.compile(
    r"\b(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|"
    r"September|October|November|December)\s+\d{4})\b",
    re.I,
)


def pdf_audit() -> list[dict]:
    findings = []
    raw_root = ROOT / "data" / "raw" / "rnsw"
    paths = list(raw_root.glob("????-??-??/*/sectionals.pdf")) + list(raw_root.glob("????-??-??/*/atc-sectionals.pdf"))
    for path in sorted(paths):
        expected = path.parts[-3]
        if not (START.isoformat() <= expected < END.isoformat()):
            continue
        try:
            reader = PdfReader(path)
            text = reader.pages[0].extract_text() or "" if reader.pages else ""
            match = DATE_RE.search(text)
            observed = (
                datetime.strptime(match.group(1).title(), "%d %B %Y").date().isoformat()
                if match else None
            )
            status = "valid_date" if observed == expected else ("wrong_date" if observed else "date_unreadable")
            findings.append({"expected_date": expected, "track": path.parent.name,
                             "observed_date": observed, "status": status,
                             "path": str(path.relative_to(ROOT))})
        except Exception as exc:
            findings.append({"expected_date": expected, "track": path.parent.name,
                             "observed_date": None, "status": "pdf_error",
                             "path": str(path.relative_to(ROOT)), "error": str(exc)})
    return findings


def main() -> None:
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    pdfs = pdf_audit()
    valid_pdf_meetings = {(row["expected_date"], row["track"])
                          for row in pdfs if row["status"] == "valid_date"}
    wrong_pdf_meetings = {(row["expected_date"], row["track"])
                          for row in pdfs if row["status"] == "wrong_date"} - valid_pdf_meetings
    rows = [dict(row) for row in db.execute("""
        SELECT r.race_date, r.track_slug, r.race_number, r.race_id,
               r.source, r.official_time_seconds, r.clock_status,
               rr.runner_number, rr.horse_name, rr.horse_key,
               rr.finish_position, rr.result_status,
               rr.source_finish_time_seconds, rr.runner_clock_status,
               COUNT(s.marker_metres) AS sectional_rows,
               COUNT(DISTINCT s.marker_metres) AS sectional_markers,
               MAX(CASE WHEN s.marker_metres=0 THEN 1 ELSE 0 END) AS has_finish_marker
          FROM v2_clean_races r
          JOIN v2_clean_runner_results rr USING(race_id)
          LEFT JOIN runner_sectionals s
            ON s.race_date=r.race_date AND s.track_slug=r.track_slug
           AND s.race_number=r.race_number AND s.runner_number=rr.runner_number
         WHERE r.race_date>=? AND r.race_date<?
           AND r.track_slug IN (?,?)
           AND rr.result_status='finished' AND rr.finish_position IS NOT NULL
         GROUP BY r.race_date,r.track_slug,r.race_number,r.race_id,r.source,
                  r.official_time_seconds,r.clock_status,rr.runner_number,
                  rr.horse_name,rr.horse_key,rr.finish_position,rr.result_status,
                  rr.source_finish_time_seconds,rr.runner_clock_status
         ORDER BY r.race_date,r.track_slug,r.race_number,rr.finish_position
    """, (START.isoformat(), END.isoformat(), *TRACKS))]
    for row in rows:
        if (row["race_date"], row["track_slug"]) in wrong_pdf_meetings:
            row["sectional_status"] = "invalid_wrong_date_source"
        elif row["sectional_rows"] == 0:
            row["sectional_status"] = "missing"
        elif not row["has_finish_marker"]:
            row["sectional_status"] = "partial_no_finish_marker"
        else:
            row["sectional_status"] = "present"

    missing = [row for row in rows if row["sectional_status"] in {"missing", "invalid_wrong_date_source"}]
    partial = [row for row in rows if row["sectional_status"] == "partial_no_finish_marker"]
    affected = {}
    for row in missing:
        item = affected.setdefault(row["horse_key"], {"horse_name": row["horse_name"], "missing_runs": 0,
                                                       "meetings": []})
        item["missing_runs"] += 1
        item["meetings"].append(f'{row["race_date"]}|{row["track_slug"]}|R{row["race_number"]}')

    meeting_keys = {(r["race_date"], r["track_slug"]) for r in rows}
    missing_meetings = {(r["race_date"], r["track_slug"]) for r in missing}
    meeting_summary = {}
    for row in rows:
        key = (row["race_date"], row["track_slug"])
        item = meeting_summary.setdefault(key, {"race_date": row["race_date"], "track": row["track_slug"],
                                                "finished_runs": 0, "present": 0, "partial": 0, "missing": 0})
        item["finished_runs"] += 1
        bucket = {"present": "present", "partial_no_finish_marker": "partial",
                  "missing": "missing", "invalid_wrong_date_source": "missing"}[row["sectional_status"]]
        item[bucket] += 1
    meeting_rows = sorted(meeting_summary.values(), key=lambda x: (x["race_date"], x["track"]))
    fully_missing_meetings = [m for m in meeting_rows if m["missing"] == m["finished_runs"]]
    summary = {
        "window": {"start_inclusive": START.isoformat(), "end_exclusive": END.isoformat()},
        "tracks": list(TRACKS),
        "meetings": len(meeting_keys),
        "finished_runner_runs": len(rows),
        "runner_runs_with_sectionals": sum(r["sectional_status"] == "present" for r in rows),
        "runner_runs_partial": len(partial),
        "runner_runs_missing": len(missing),
        "runner_runs_invalid_wrong_date_source": sum(
            r["sectional_status"] == "invalid_wrong_date_source" for r in rows),
        "unique_horses_missing_sectionals": len(affected),
        "meetings_with_at_least_one_missing_runner": len(missing_meetings),
        "meetings_fully_missing_sectionals": len(fully_missing_meetings),
        "races_with_valid_clock": len({r["race_id"] for r in rows if r["clock_status"] == "valid"}),
        "runner_finish_clocks_valid": sum(r["runner_clock_status"] == "valid" for r in rows),
        "pdf_status": dict(Counter(r["status"] for r in pdfs)),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    csv_path = OUT / "sydney_missing_sectionals_3y_2026-08-31.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(missing + partial)
    horse_path = OUT / "sydney_horses_missing_sectionals_3y_2026-08-31.csv"
    with horse_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=("horse_name", "missing_runs", "meetings"))
        writer.writeheader()
        for item in sorted(affected.values(), key=lambda x: (-x["missing_runs"], x["horse_name"])):
            writer.writerow({**item, "meetings": ";".join(item["meetings"])})
    report = {"summary": summary, "pdf_audit": pdfs,
              "meeting_coverage": meeting_rows,
              "worst_affected_horses": sorted(affected.values(), key=lambda x: (-x["missing_runs"], x["horse_name"]))[:100],
              "outputs": {"missing_runner_runs_csv": str(csv_path.relative_to(ROOT)),
                          "affected_horses_csv": str(horse_path.relative_to(ROOT))}}
    report_path = OUT / "sydney_sectional_audit_3y_2026-08-31.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
