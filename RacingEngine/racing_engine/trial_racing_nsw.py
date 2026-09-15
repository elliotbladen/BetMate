"""Parser and collector for Racing NSW trial result pages.

Racing NSW publishes the same runner-level fields needed by the fitness
pipeline (finish, horse, trainer, jockey, margin and barrier) together with
the heat distance and winner clock.  This adapter keeps those observations
in the existing append-only official-evidence table.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import time
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode

from bs4 import BeautifulSoup

from .trial_ingest import archive_payload, fetch
from .trial_official_archive import install
from .trial_calendar_expansion import digest
from .trial_meeting import MeetingError, _seconds, validate_review_target
from .storage import utc_now


def source_url(item: dict) -> str:
    if not item.get("isTrial") or item.get("isJumpOut"):
        raise MeetingError("not_an_official_trial")
    key = ",".join([datetime.fromisoformat(item["date"]).strftime("%Y%b%d"), "NSW", item["venue"], "Trial"])
    return "https://mdata.racingnsw.com.au/FreeFields/Results.aspx?" + urlencode({"Key": key})


def _text(node) -> str:
    return " ".join(node.get_text(" ", strip=True).split())


def parse(payload: bytes, item: dict, url: str, observed_at: str) -> dict:
    if url != source_url(item):
        raise MeetingError("nsw_url_identity_mismatch")
    soup = BeautifulSoup(payload, "html.parser")
    venue = soup.select_one("header.race-venue")
    if not venue:
        raise MeetingError("nsw_missing_venue")
    date_text = _text(venue.select_one(".race-venue-date"))
    parsed_date = re.search(r"\b\d{1,2},?\s+\w+\s+\d{4}", date_text)
    if not parsed_date or datetime.strptime(parsed_date.group(0).replace(",", ""), "%d %B %Y").date().isoformat() != item["date"]:
        raise MeetingError("nsw_date_mismatch")
    title = _text(venue.select_one("h2 span"))
    if item["venue"].lower() not in title.lower():
        raise MeetingError("nsw_venue_mismatch")
    rows = []
    for heading in soup.select("div.race-title"):
        label = _text(heading)
        match = re.search(r"Race\s+(\d+).*?\((\d+)\s+METRES\)", label, re.I)
        if not match:
            continue
        heat, distance = int(match.group(1)), int(match.group(2))
        info = heading.find_next_sibling("div", class_="race-info")
        info_text = _text(info) if info else ""
        clock_match = re.search(r"Time:\s*([0-9:.]+)", info_text, re.I)
        winner_clock = _seconds(clock_match.group(1)) if clock_match else None
        table = heading.find_next("table", class_="race-strip-fields")
        if not table:
            continue
        headers = [_text(x).lower() for x in table.select("thead th")]
        aliases = {"finish": "finish", "horse": "horse", "trainer": "trainer", "jockey": "jockey", "marg(l)": "margin", "bar": "barrier"}
        index = {aliases[h]: i for i, h in enumerate(headers) if h in aliases}
        required = {"finish", "horse", "trainer", "jockey", "margin", "barrier"}
        if not required <= set(index):
            raise MeetingError("nsw_columns_changed")
        heat_rows = []
        for tr in table.select("tbody tr"):
            cells = tr.find_all("td", recursive=False)
            if len(cells) < len(headers):
                continue
            horse = _text(cells[index["horse"]])
            if not horse:
                continue
            finish = _text(cells[index["finish"]]).upper()
            finish_position = int(finish) if finish.isdigit() else None
            margin_text = _text(cells[index["margin"]]).rstrip("L ")
            link = cells[index["horse"]].find("a", href=True)
            horse_id = re.search(r"horsecode=([^&]+)", link["href"], re.I).group(1) if link and re.search(r"horsecode=([^&]+)", link["href"], re.I) else horse
            heat_rows.append({"source": "racing_nsw", "source_horse_id": horse_id,
                "source_entry_id": digest([item["date"], item["venue"], heat, horse_id]),
                "horse_name": horse, "event_date": item["date"], "state": "NSW", "track": item["venue"],
                "heat_number": heat, "distance_metres": distance, "finish_position": finish_position,
                "result_status": "finished" if finish_position else finish.lower(),
                "beaten_margin": float(margin_text) if re.fullmatch(r"\d+(?:\.\d+)?", margin_text) else None,
                "heat_time_seconds": winner_clock, "official_time_seconds": winner_clock if finish_position == 1 else None,
                "source_url": url, "observed_at": observed_at, "time_scope": "heat_winner",
                "jockey": _text(cells[index["jockey"]]) or None, "trainer": _text(cells[index["trainer"]]) or None,
                "barrier": _text(cells[index["barrier"]]) or None})
        rows.extend(heat_rows)
    if not rows:
        raise MeetingError("nsw_no_trial_rows")
    return {"status": "verified", "rows": rows, "heats": sorted({r["heat_number"] for r in rows}), "advertised_starters": len(rows)}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--database", type=Path, required=True); p.add_argument("--registry-database", type=Path, required=True)
    p.add_argument("--archive", type=Path, required=True); p.add_argument("--url")
    p.add_argument("--date"); p.add_argument("--venue"); p.add_argument("--report", type=Path, required=True)
    p.add_argument("--plan", type=Path); p.add_argument("--run-directory", type=Path); p.add_argument("--from-date", default="0001-01-01")
    a = p.parse_args(); validate_review_target(a.database, a.registry_database)
    if a.plan:
        if not a.run_directory: p.error("--run-directory is required with --plan")
        a.run_directory.mkdir(parents=True, exist_ok=True)
        meetings = [x for x in json.loads(a.plan.read_text())["meetings"] if x.get("state") == "NSW" and x.get("isTrial") and not x.get("isJumpOut") and x["date"] >= a.from_date]
        c = sqlite3.connect(a.database); total = inserted = failed = 0
        for item in sorted(meetings, key=lambda x: x["date"], reverse=True):
            url = source_url(item); path = a.run_directory / (digest(url) + ".json")
            if path.exists() and json.loads(path.read_text()).get("status") == "verified":
                continue
            try:
                time.sleep(0.75); raw = fetch(url); archive = archive_payload(a.archive, source_id="racing_nsw_trials", source_url=url, payload=raw, collected_at=utc_now())
                result = parse(raw, item, url, archive["collected_at"]); n = install(c, result["rows"], archive)
                path.write_text(json.dumps({"meeting": item, "source_url": url, "status": result["status"], "rows": len(result["rows"]), "inserted": n}, indent=2) + "\n")
                inserted += n
            except Exception as exc:
                failed += 1; path.write_text(json.dumps({"meeting": item, "source_url": url, "status": "failed", "error": str(exc)}, indent=2) + "\n")
                if "source_access_challenge" in str(exc): break
            total += 1
            if total % 25 == 0: print(json.dumps({"processed": total, "expected": len(meetings), "inserted": inserted, "failed": failed}), flush=True)
        c.close(); a.report.write_text(json.dumps({"source": "racing_nsw", "expected": len(meetings), "processed": total, "inserted": inserted, "failed": failed}, indent=2) + "\n"); print(a.report.read_text()); return
    if not a.url or not a.date or not a.venue: p.error("--url, --date and --venue are required without --plan")
    item = {"date": a.date, "venue": a.venue, "isTrial": True, "isJumpOut": False}; url = source_url(item)
    raw = fetch(a.url); archive = archive_payload(a.archive, source_id="racing_nsw_trials", source_url=a.url, payload=raw, collected_at=utc_now())
    c = sqlite3.connect(a.database); result = parse(raw, item, url, archive["collected_at"]); inserted = install(c, result["rows"], archive); c.close()
    a.report.write_text(json.dumps({"source": "racing_nsw", "url": a.url, "rows": len(result["rows"]), "inserted": inserted}, indent=2) + "\n")
    print(json.dumps({"rows": len(result["rows"]), "inserted": inserted}))


if __name__ == "__main__":
    main()
