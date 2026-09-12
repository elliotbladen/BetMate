"""Review-only, reconciled ingestion of one Racing NSW trial results meeting."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import uuid
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

from .fitness_identity import link_rows, persist_quarantine
from .fitness_quality import quality_gate
from .horse_identity import identity_key
from .storage import RacingStore, utc_now
from .trial_ingest import archive_payload, fetch

VERSION = "rnsw-trial-meeting-v1"
SOURCE = "racing_nsw"


class MeetingError(ValueError):
    """Source identity or completeness cannot be established."""


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def _text(html):
    parser = _Text()
    parser.feed(html)
    return " ".join(" ".join(parser.parts).split())


class _Table(HTMLParser):
    """Preserve cell text and links without scraping unrelated page tables."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self.row_classes = []
        self.row = None
        self.cell = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            if self.row is not None:
                raise MeetingError("nested_or_unclosed_result_row")
            self.row = []
            self.current_classes = dict(attrs).get("class", "").lower().split()
        elif tag in ("td", "th") and self.row is not None:
            if self.cell is not None:
                raise MeetingError("nested_or_unclosed_result_cell")
            self.cell = {"parts": [], "links": []}
        elif tag == "a" and self.cell is not None:
            href = dict(attrs).get("href")
            if href:
                self.cell["links"].append(href)

    def handle_data(self, data):
        if self.cell is not None:
            self.cell["parts"].append(data)

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None:
            self.cell["text"] = " ".join(" ".join(self.cell.pop("parts")).split())
            self.row.append(self.cell)
            self.cell = None
        elif tag == "tr" and self.row is not None:
            if self.cell is not None:
                raise MeetingError("unclosed_result_cell")
            if self.row:
                self.rows.append(self.row)
                self.row_classes.append(self.current_classes)
            self.row = None


def _one(pattern, html, label):
    matches = re.findall(pattern, html, re.I | re.S)
    if len(matches) != 1:
        raise MeetingError(f"expected_one_{label}: found {len(matches)}")
    return matches[0]


def _class_block(tag, name):
    return rf'<{tag}\b[^>]*class=[\'"]{name}[\'"][^>]*>(.*?)</{tag}>'


def _seconds(value):
    if not value:
        return None
    match = re.fullmatch(r"(\d+):(\d{2}(?:\.\d+)?)", value)
    if not match or float(match[2]) >= 60:
        raise MeetingError("invalid_heat_clock")
    return int(match[1]) * 60 + float(match[2])


def _label(info, label):
    match = re.search(rf"<b>\s*{re.escape(label)}:\s*</b>(.*?)(?=<b>|$)", info, re.I | re.S)
    return _text(match[1]) if match else None


def parse_meeting(payload: bytes, source_url: str, *, expected_date: str,
                  expected_track: str, collected_at: str) -> dict:
    """Refuse wrong meetings, interim results, missing heats and silent row loss."""
    event_date = date.fromisoformat(expected_date)
    observed = datetime.fromisoformat(collected_at.replace("Z", "+00:00"))
    if observed.tzinfo is None or observed.astimezone(ZoneInfo("Australia/Sydney")).date() < event_date:
        raise MeetingError("invalid_collection_timestamp")
    url = urlparse(source_url)
    if url.scheme != "https" or url.hostname != "mdata.racingnsw.com.au" or url.path != "/FreeFields/Results.aspx":
        raise MeetingError("expected_official_results_url")
    keys = parse_qs(url.query).get("Key", [])
    if len(keys) != 1:
        raise MeetingError("missing_meeting_key")
    key = keys[0].split(",")
    if len(key) != 4 or key[1] != "NSW" or key[3] != "Trial":
        raise MeetingError("not_a_nsw_trial_meeting")
    if datetime.strptime(key[0], "%Y%b%d").date() != event_date or identity_key(key[2]) != identity_key(expected_track):
        raise MeetingError("url_meeting_identity_mismatch")
    html = payload.decode("utf-8-sig")
    header = _one(_class_block("header", "race-venue"), html, "meeting_header")
    displayed_date = _text(_one(_class_block("span", "race-venue-date"), header, "meeting_date"))
    if datetime.strptime(displayed_date, "%A %d, %B %Y").date() != event_date:
        raise MeetingError("page_date_mismatch")
    venue = _text(_one(r"<span\s+notranslate[^>]*>(.*?)</span>", header, "venue")).split(":")[0]
    if identity_key(venue) != identity_key(expected_track):
        raise MeetingError("page_venue_mismatch")
    if re.search(r"\bMeeting Abandoned\.", _text(html)):
        if re.search(_class_block("table", "race-strip-fields"), html, re.I | re.S):
            raise MeetingError("abandoned_meeting_has_result_rows")
        return {"source": SOURCE, "source_url": source_url, "event_date": expected_date,
                "track": expected_track, "advertised_starters": 0, "heats": [], "rows": [],
                "meeting_status": "abandoned"}
    total = int(_one(r"Total Number of starters for this meeting \(including emergencies\)\s*(\d+)", html, "starter_total"))
    index = [int(n) for n in re.findall(r'href=[\'"]#Race(\d+)[\'"]', html)]
    headings = list(re.finditer(_class_block("div", "race-title"), html, re.I | re.S))
    if not index or len(index) != len(set(index)) or len(headings) != len(index):
        raise MeetingError("heat_index_count_mismatch")
    published = _one(r"Results Last Published:</b>\s*([^<]+)", html, "results_publication_marker").strip()
    rows, heats = [], []
    for i, heading in enumerate(headings):
        title = _text(heading[1])
        match = re.fullmatch(r"Race (\d+)\s*-\s*(\d+:\d+[AP]M)\s+(.+?)\s+\((\d+) METRES\)", title)
        if not match or "TRIAL" not in match[3]:
            raise MeetingError("unrecognised_trial_heading")
        heat, scheduled, trial_type, distance = int(match[1]), match[2], match[3], int(match[4])
        if heat != index[i] or not 100 <= distance <= 4000:
            raise MeetingError("heat_identity_or_distance_mismatch")
        chunk = html[heading.end():headings[i + 1].start() if i + 1 < len(headings) else len(html)]
        info = _one(_class_block("div", "race-info"), chunk, "heat_info")
        if re.search(r"INTERIM|ABANDONED|CANCELLED", _text(info), re.I):
            raise MeetingError(f"heat_{heat}_not_final")
        clock = _seconds(_label(info, "Time"))
        last600 = _seconds(_label(info, "Last 600m"))
        table = _Table()
        table.feed(_one(_class_block("table", "race-strip-fields"), chunk, "result_table"))
        if len(table.rows) < 2:
            raise MeetingError("empty_results")
        headers = [cell["text"].lower() for cell in table.rows[0]]
        required = ("finish", "no.", "horse", "trainer", "jockey", "marg(l)", "bar")
        if any(headers.count(name) != 1 for name in required):
            raise MeetingError("result_columns_changed")
        positions = {name: headers.index(name) for name in required}
        seen = set()
        seen_horses = set()
        heat_rows = []
        for cells, classes in zip(table.rows[1:], table.row_classes[1:]):
            if len(cells) != len(headers):
                raise MeetingError("result_row_width_mismatch")
            values = {name: cells[pos]["text"] for name, pos in positions.items()}
            runner_label = re.fullmatch(r"(\d+)(e)?", values["no."], re.I)
            if not values["horse"] or not runner_label:
                raise MeetingError("missing_runner_identity")
            number = int(runner_label[1])
            if number in seen:
                raise MeetingError("duplicate_heat_runner")
            seen.add(number)
            horse_links = cells[positions["horse"]]["links"]
            provider_ids = {v for link in horse_links for v in parse_qs(urlparse(link).query).get("horsecode", [])}
            if len(provider_ids) != 1:
                raise MeetingError("missing_or_ambiguous_source_horse_id")
            source_horse_id = next(iter(provider_ids))
            if source_horse_id in seen_horses:
                raise MeetingError("duplicate_source_horse_in_heat")
            seen_horses.add(source_horse_id)
            for link in horse_links:
                link_keys = parse_qs(urlparse(link).query).get("Key", [])
                if link_keys and link_keys != keys:
                    raise MeetingError("runner_link_meeting_mismatch")
            finish_text = values["finish"]
            if "scratched" in classes:
                if finish_text.isdigit():
                    raise MeetingError("scratched_runner_has_finish_position")
                finish_text = "SCR"
            finish = int(finish_text) if finish_text.isdigit() else None
            if finish is None and finish_text.upper() not in {"SCR", "SCRATCHED", "DNS", "DNF", "FF", "LR", "UR", "DQ", "DSQ", "LP"}:
                raise MeetingError("unrecognised_finish_status")
            barrier_text = values["bar"]
            if barrier_text and not barrier_text.isdigit():
                raise MeetingError("invalid_barrier")
            barrier = int(barrier_text) if barrier_text and int(barrier_text) > 0 else None
            margin_text = values["marg(l)"]
            if margin_text and not re.fullmatch(r"\d+(?:\.\d+)?", margin_text):
                raise MeetingError("invalid_margin")
            missing = []
            for field, value in (("barrier", barrier), ("jockey_name", values["jockey"]),
                                 ("trainer_name", values["trainer"]), ("heat_time_seconds", clock)):
                if not value:
                    missing.append(field + "_not_reported")
            row = {
                "source": SOURCE, "source_event_id": f"{expected_date}:{identity_key(expected_track)}:trial:{heat}",
                "source_horse_id": source_horse_id, "provider": SOURCE,
                "horse_name": values["horse"], "runner_number": number,
                "event_type": "official_trial", "event_date": expected_date,
                # Today's observation must never masquerade as historically available evidence.
                "effective_at": observed.astimezone(timezone.utc).isoformat(),
                "collected_at": observed.astimezone(timezone.utc).isoformat(),
                "source_url": source_url, "parser_version": VERSION,
                "track_slug": {"royalrandwick": "randwick", "rosehillgardens": "rosehill"}.get(identity_key(expected_track), re.sub(r"\s+", "-", expected_track.lower())),
                "heat_number": heat, "distance_metres": distance, "trial_type": trial_type,
                "finish_position": finish, "result_status": "finished" if finish else finish_text.lower(),
                "barrier": barrier, "beaten_margin": float(margin_text) if margin_text else (0.0 if finish == 1 else None),
                # Only the winner has an observed individual official time.
                "official_time_seconds": clock if finish == 1 else None,
                "jockey_name": values["jockey"] or None, "trainer_name": values["trainer"] or None,
                "surface": _label(info, "Track Type"), "going": _label(info, "Track Condition"),
                "detail": {"scheduled_local_time": scheduled, "heat_time_seconds": clock,
                           "heat_last_600m_seconds": last600, "time_scope": "heat_winner",
                           "source_published_text": published,
                           "missing_reasons": missing, "retrospective_collection": True},
            }
            if runner_label[2]:
                row["detail"]["source_runner_label"] = values["no."]
                row["detail"]["emergency"] = True
            heat_rows.append(row)
        starters = sum(row["result_status"] not in {"scr", "scratched", "dns"} for row in heat_rows)
        finishes = [row["finish_position"] for row in heat_rows if row["finish_position"] is not None]
        if not finishes or min(finishes) != 1 or any(n < 1 or n > starters for n in finishes):
            raise MeetingError("invalid_finish_positions")
        for row in heat_rows:
            row["field_size"] = starters
        heats.append({"heat_number": heat, "distance_metres": distance, "source_rows": len(heat_rows), "starters": starters})
        rows.extend(heat_rows)
    # Racing NSW lists scratched rows in results tables but excludes them from
    # its advertised starter total. Keep both denominators visible.
    starters = sum(h["starters"] for h in heats)
    if starters != total:
        raise MeetingError(f"advertised_starter_count_mismatch: {total} != {starters}")
    return {"source": SOURCE, "source_url": source_url, "event_date": expected_date,
            "track": expected_track, "advertised_starters": total, "heats": heats, "rows": rows}


def copy_registry(source_path: Path, store: RacingStore) -> dict:
    """Copy identity tables only from a read-only connection; never copy race data."""
    counts = {}
    with sqlite3.connect(source_path.resolve().as_uri() + "?mode=ro", uri=True) as source:
        for table in ("horses", "horse_aliases"):
            rows = source.execute(f"SELECT * FROM {table}").fetchall()
            columns = [r[1] for r in source.execute(f"PRAGMA table_info({table})")]
            placeholders = ",".join("?" for _ in columns)
            store.connection.executemany(f"INSERT OR IGNORE INTO {table} ({','.join(columns)}) VALUES ({placeholders})", rows)
            counts[table] = len(rows)
    store.connection.commit()
    return counts


def _digest(row):
    # Transport timestamps, profile revisions and rotating replay links are not
    # event changes. Keep the original observation intact on an identical rerun.
    stable = {k: v for k, v in row.items() if k not in {"effective_at", "collected_at", "raw_payload_hash"}}
    stable["detail"] = {k: v for k, v in row["detail"].items() if k != "source_published_text"}
    return hashlib.sha256(json.dumps(stable, sort_keys=True).encode()).hexdigest()


def ingest_meeting(store: RacingStore, meeting: dict, *, raw_payload_hash: str) -> dict:
    """Atomically save accepted events and every excluded/unmatched observation."""
    rows = [{**row, "raw_payload_hash": raw_payload_hash} for row in meeting["rows"]]
    counters = dict(inserted=0, unchanged=0, identity_quarantined=0, quality_quarantined=0)
    per_heat = {h["heat_number"]: {**h, **counters} for h in meeting["heats"]}
    with store.connection:
        held_statuses = {"scr", "scratched", "dns", "lp"}
        nonstarters = [row for row in rows if row["result_status"] in held_statuses]
        starters = [row for row in rows if row["result_status"] not in held_statuses]
        identity = link_rows(store, starters)
        for row in identity["quarantined_rows"]:
            persist_quarantine(store, [row], commit=False)
            counters["identity_quarantined"] += 1
            per_heat[row["heat_number"]]["identity_quarantined"] += 1
        # Preserve scratches even when they have no horse-registry match.
        for row in identity["linked_rows"] + nonstarters:
            reason = None
            if row["result_status"] in {"scr", "scratched", "dns"}:
                reason = "not_a_completed_preparation_event"
            elif row["result_status"] == "lp":
                reason = "unresolved_result_code_lp"
            row_hash = _digest({k: v for k, v in row.items() if k not in {
                "horse_id", "cleaned_horse_name", "identity_method", "identity_confidence",
                "review_status", "identity_version", "transformations"}})
            prior = store.connection.execute(
                "SELECT payload_hash FROM fitness_events WHERE source=? AND source_event_id=? AND horse_id=?",
                (SOURCE, row["source_event_id"], row.get("horse_id"))).fetchone()
            if not reason and quality_gate([row])["quarantined"]:
                reason = "invalid_event_contract"
            if prior and prior[0] != row_hash:
                reason = "conflicting_existing_event"
            if reason:
                review_key = hashlib.sha256(f"{row['source_event_id']}:{row['source_horse_id']}:{row_hash}:{reason}".encode()).hexdigest()
                store.connection.execute("""INSERT OR IGNORE INTO fitness_quality_quarantine
                    (review_key,source,source_event_id,horse_id,event_date,reason_json,payload_hash,raw_json,parser_version,created_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?)""", (review_key, SOURCE, row["source_event_id"], row.get("horse_id"),
                    row["event_date"], json.dumps([reason]), row_hash, json.dumps(row, sort_keys=True), VERSION, utc_now()))
                outcome = "quality_quarantined"
            elif prior:
                outcome = "unchanged"
            else:
                detail = {**row["detail"], "source_horse_id": row["source_horse_id"],
                          "runner_number": row["runner_number"], "result_status": row["result_status"],
                          "identity_method": row["identity_method"], "identity_confidence": row["identity_confidence"],
                          "raw_payload_hash": raw_payload_hash}
                event = {key: row.get(key) for key in (
                    "horse_id", "event_type", "event_date", "effective_at", "source", "source_event_id",
                    "track_slug", "distance_metres", "surface", "going", "trial_type", "heat_number", "field_size",
                    "barrier", "finish_position", "beaten_margin", "official_time_seconds", "jockey_name",
                    "trainer_name", "source_url", "collected_at", "parser_version")}
                event.update(event_id="trial_" + hashlib.sha256(f"{SOURCE}:{row['source_event_id']}:{row['horse_id']}".encode()).hexdigest(),
                             payload_hash=row_hash, raw_json=json.dumps(row, sort_keys=True),
                             detail_json=json.dumps(detail, sort_keys=True), created_at=utc_now())
                store.connection.execute(f"INSERT INTO fitness_events ({','.join(event)}) VALUES ({','.join('?' for _ in event)})", tuple(event.values()))
                outcome = "inserted"
            counters[outcome] += 1
            per_heat[row["heat_number"]][outcome] += 1
        if sum(counters.values()) != len(rows):
            raise MeetingError("persistence_accounting_mismatch")
    return {"parser_version": VERSION, "event_date": meeting["event_date"], "track": meeting["track"],
            "source_url": meeting["source_url"], "raw_payload_hash": raw_payload_hash,
            "advertised_starters": meeting["advertised_starters"], "parsed_rows": len(rows),
            "non_starters": len(rows) - meeting["advertised_starters"],
            "meeting_status": meeting.get("meeting_status", "results"),
            **counters, "reconciled": True, "heats": list(per_heat.values())}


def validate_review_target(database: Path, registry_database: Path):
    if (database.resolve() == registry_database.resolve() or database.name == "racing_engine.sqlite"
            or (database.exists() and registry_database.exists() and database.samefile(registry_database))):
        raise MeetingError("Use a separate review database; the rating database is read-only")
    if database.exists():
        with sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True) as check:
            tables = {r[0] for r in check.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if "race_results" in tables and check.execute("SELECT 1 FROM race_results LIMIT 1").fetchone():
                raise MeetingError("Refusing a database containing race results; use a dedicated review database")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--date", required=True)
    parser.add_argument("--track", required=True)
    parser.add_argument("--database", type=Path, required=True, help="Dedicated review database, never the production database")
    parser.add_argument("--registry-database", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--html", type=Path, help="Replay a locally archived results page")
    parser.add_argument("--collected-at", help="Required with --html; original UTC collection timestamp")
    args = parser.parse_args()
    validate_review_target(args.database, args.registry_database)
    if args.html and not args.collected_at:
        parser.error("--html requires its original --collected-at timestamp")
    if args.report.exists():
        parser.error("Choose a new report path; previous reports are immutable")
    report = {"run_id": uuid.uuid4().hex, "parser_version": VERSION, "status": "failed", "source_url": args.url}
    try:
        payload = args.html.read_bytes() if args.html else fetch(args.url)
        collected = args.collected_at or utc_now()
        archive = archive_payload(args.archive, source_id=SOURCE, source_url=args.url, payload=payload, collected_at=collected)
        report["archive"] = archive
        meeting = parse_meeting(payload, args.url, expected_date=args.date, expected_track=args.track, collected_at=collected)
        store = RacingStore(args.database)
        try:
            report["registry_rows"] = copy_registry(args.registry_database, store)
            report.update(ingest_meeting(store, meeting, raw_payload_hash=archive["payload_hash"]))
            report["status"] = "reconciled_with_quarantine" if report["identity_quarantined"] or report["quality_quarantined"] else "reconciled"
        finally:
            store.close()
    except (ValueError, sqlite3.Error, OSError) as exc:
        report["error_type"] = type(exc).__name__
        # Do not log arbitrary source payloads or signed URLs from exceptions.
        if isinstance(exc, MeetingError):
            report["error"] = str(exc)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("x") as output:
        output.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: report[k] for k in ("status", "advertised_starters", "parsed_rows", "non_starters", "inserted", "unchanged", "identity_quarantined", "quality_quarantined", "error") if k in report}, sort_keys=True))
    if report["status"] == "failed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
