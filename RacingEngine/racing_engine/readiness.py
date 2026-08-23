"""Deterministic, read-only completeness audit for historical racing data."""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
REPORT_VERSION = "data-readiness-v1"
TERMINAL_STEWARD_STATUSES = {"complete", "completed", "no_report", "not_published", "absent"}
BLOCKING_CHECKS = {
    "runner_results", "winner", "official_time", "margins", "class", "weather", "steward_check"
}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _key(row: sqlite3.Row) -> tuple[str, str, str, int]:
    return row["source"], row["race_date"], row["track_slug"], int(row["race_number"])


def _gap(check: str, row: sqlite3.Row, reason: str, *, runner_number: int | None = None,
         severity: str | None = None) -> dict[str, Any]:
    return {
        "check": check,
        "severity": severity or ("blocking" if check in BLOCKING_CHECKS else "warning"),
        "source": row["source"],
        "race_date": row["race_date"],
        "track_slug": row["track_slug"],
        "race_number": int(row["race_number"]),
        "runner_number": runner_number,
        "reason": reason,
    }


def _where(from_date: str | None, to_date: str | None, states: Iterable[str] | None,
           sources: Iterable[str] | None) -> tuple[str, list[Any]]:
    clauses: list[str] = []
    parameters: list[Any] = []
    if from_date:
        clauses.append("race_date >= ?")
        parameters.append(from_date)
    if to_date:
        clauses.append("race_date <= ?")
        parameters.append(to_date)
    for column, values in (("state", states), ("source", sources)):
        selected = list(values or [])
        if selected:
            clauses.append(f"{column} IN ({','.join('?' for _ in selected)})")
            parameters.extend(selected)
    return (" WHERE " + " AND ".join(clauses)) if clauses else "", parameters


def build_report(connection: sqlite3.Connection, *, from_date: str | None = None,
                 to_date: str | None = None, states: Iterable[str] | None = None,
                 sources: Iterable[str] | None = None,
                 generated_at: str | None = None, database_path: str | None = None) -> dict[str, Any]:
    """Audit the selected result races without modifying the database."""
    connection.row_factory = sqlite3.Row
    where, parameters = _where(from_date, to_date, states, sources)
    races = connection.execute(
        "SELECT * FROM race_results" + where + " ORDER BY race_date, track_slug, race_number, source",
        parameters,
    ).fetchall()
    gaps: list[dict[str, Any]] = []
    check_counts: dict[str, Counter] = defaultdict(Counter)
    meeting_data: dict[tuple[str, str, str], dict[str, Any]] = {}
    source_data: dict[str, Counter] = defaultdict(Counter)

    runner_sql = """SELECT * FROM runner_results WHERE source=? AND race_date=? AND track_slug=? AND race_number=?
                    ORDER BY runner_number"""
    for race in races:
        key = _key(race)
        source, race_date, track_slug, race_number = key
        meeting = meeting_data.setdefault((source, race_date, track_slug), {
            "source": source, "race_date": race_date, "track_slug": track_slug,
            "race_numbers": [], "races": 0, "runners": 0, "blocking_gaps": 0, "warnings": 0,
        })
        meeting["race_numbers"].append(race_number)
        meeting["races"] += 1
        source_data[source]["races"] += 1
        runners = connection.execute(runner_sql, key).fetchall()
        meeting["runners"] += len(runners)
        source_data[source]["runners"] += len(runners)

        def record(check: str, complete: bool, reason: str, runner_number: int | None = None,
                   severity: str | None = None) -> None:
            check_counts[check]["eligible"] += 1
            if complete:
                check_counts[check]["complete"] += 1
                return
            item = _gap(check, race, reason, runner_number=runner_number, severity=severity)
            gaps.append(item)
            label = "blocking_gaps" if item["severity"] == "blocking" else "warnings"
            meeting[label] += 1
            source_data[source][label] += 1

        record("runner_results", bool(runners), "race has no runner-result rows")
        winners = [r for r in runners if r["result_status"] == "finished" and r["finish_position"] == 1]
        record("winner", len(winners) == 1, f"expected exactly one finished winner; found {len(winners)}")
        record("official_time", race["official_time_seconds"] is not None and race["official_time_seconds"] > 0,
               "official_time_seconds is null or non-positive")

        classification = connection.execute(
            """SELECT class_family FROM race_classifications
               WHERE source=? AND race_date=? AND track_slug=? AND race_number=?""", key).fetchone()
        record("class", bool(classification and str(classification["class_family"] or "").strip()),
               "usable race classification is missing")
        weather = connection.execute(
            """SELECT 1 FROM race_weather WHERE source=? AND race_date=? AND track_slug=? AND race_number=? LIMIT 1""",
            key).fetchone()
        record("weather", weather is not None, "matched race weather is missing")

        card = connection.execute(
            """SELECT 1 FROM races WHERE race_date=? AND track_slug=? AND race_number=? LIMIT 1""",
            (race_date, track_slug, race_number)).fetchone()
        record("pre_race_card", card is not None, "pre-race card is missing")

        for runner in runners:
            number = int(runner["runner_number"])
            finished = runner["result_status"] == "finished"
            if finished:
                record("runner_time", runner["finish_time_seconds"] is not None and runner["finish_time_seconds"] > 0,
                       "finished runner time is null or non-positive", number)
                margin_ok = runner["beaten_lengths"] is not None and runner["beaten_lengths"] >= 0
                if runner["finish_position"] == 1:
                    margin_ok = margin_ok and runner["beaten_lengths"] == 0
                record("margins", margin_ok, "finished runner margin is missing, negative, or winner is not zero", number)
                sectional = connection.execute(
                    """SELECT group_concat(marker_metres) AS markers FROM runner_sectionals
                       WHERE source=? AND race_date=? AND track_slug=? AND race_number=? AND runner_number=?""",
                    (*key, number)).fetchone()
                markers = sectional["markers"] if sectional else None
                record("sectionals", bool(markers), "finished runner has no sectional markers", number)
            for field in ("barrier", "weight_carried_kg", "jockey", "trainer", "official_handicap_rating"):
                value = runner[field]
                present = value is not None and (not isinstance(value, str) or bool(value.strip()))
                record(f"metadata_{field}", present, f"runner {field} is missing", number)
            record("dtw", runner["distance_travelled_vs_winner_metres"] is not None,
                   "explicit DT-W value is unavailable", number)

    # Steward checks are meeting-level: a checked absence is complete evidence.
    for (source, race_date, track_slug), meeting in meeting_data.items():
        rows = connection.execute(
            "SELECT status, detail FROM steward_report_ingestions WHERE race_date=? AND track_slug=?",
            (race_date, track_slug)).fetchall()
        complete = any(str(row["status"]).lower() in TERMINAL_STEWARD_STATUSES for row in rows)
        check_counts["steward_check"]["eligible"] += 1
        if complete:
            check_counts["steward_check"]["complete"] += 1
        else:
            representative = next(r for r in races if _key(r)[:3] == (source, race_date, track_slug))
            item = _gap("steward_check", representative, "meeting has no completed steward-source check")
            item["race_number"] = None
            gaps.append(item)
            meeting["blocking_gaps"] += 1
            source_data[source]["blocking_gaps"] += 1

        report_count = connection.execute(
            "SELECT count(*) FROM steward_reports WHERE race_date=? AND track_slug=?", (race_date, track_slug)
        ).fetchone()[0]
        event_count = connection.execute(
            "SELECT count(*) FROM steward_events WHERE race_date=? AND track_slug=?", (race_date, track_slug)
        ).fetchone()[0]
        meeting["steward_reports"] = report_count
        meeting["steward_events"] = event_count

        numbers = sorted(meeting["race_numbers"])
        missing_numbers = sorted(set(range(1, max(numbers) + 1)) - set(numbers)) if numbers else []
        check_counts["race_sequence"]["eligible"] += 1
        if not missing_numbers:
            check_counts["race_sequence"]["complete"] += 1
        else:
            representative = next(r for r in races if _key(r)[:3] == (source, race_date, track_slug))
            item = _gap("race_sequence", representative,
                        f"missing race numbers in imported meeting: {missing_numbers}")
            item["race_number"] = None
            gaps.append(item)
            meeting["warnings"] += 1
            source_data[source]["warnings"] += 1

    checks = {}
    for name, counts in sorted(check_counts.items()):
        eligible = counts["eligible"]
        complete = counts["complete"]
        checks[name] = {
            "eligible": eligible,
            "complete": complete,
            "missing": eligible - complete,
            "coverage_pct": round(100 * complete / eligible, 2) if eligible else None,
            "severity": "blocking" if name in BLOCKING_CHECKS else "warning",
        }

    blocking = [gap for gap in gaps if gap["severity"] == "blocking"]
    warnings = [gap for gap in gaps if gap["severity"] == "warning"]
    if not races:
        gaps.append({
            "check": "no_data", "severity": "blocking", "source": None, "race_date": None,
            "track_slug": None, "race_number": None, "runner_number": None,
            "reason": "no result races matched the requested scope",
        })
        blocking = [gap for gap in gaps if gap["severity"] == "blocking"]
    status = "NOT_READY" if blocking else ("READY_WITH_WARNINGS" if warnings else "READY")
    meetings = sorted(meeting_data.values(), key=lambda x: (x["race_date"], x["track_slug"], x["source"]))
    for meeting in meetings:
        numbers = sorted(meeting.pop("race_numbers"))
        meeting["race_numbers"] = numbers
        meeting["missing_race_numbers"] = sorted(set(range(1, max(numbers) + 1)) - set(numbers)) if numbers else []
    source_rows = []
    for source, counts in sorted(source_data.items()):
        source_rows.append({"source": source, **dict(counts)})

    return {
        "report_version": REPORT_VERSION,
        "generated_at": generated_at or _now(),
        "database_path": database_path,
        "scope": {
            "from_date": from_date, "to_date": to_date,
            "states": sorted(states or []), "sources": sorted(sources or []),
        },
        "totals": {
            "sources": len(source_data), "meetings": len(meetings), "races": len(races),
            "runners": sum(row["runners"] for row in source_rows),
            "blocking_gaps": len(blocking), "warnings": len(warnings),
        },
        "checks": checks,
        "sources": source_rows,
        "meetings": meetings,
        "gaps": gaps,
        "readiness": {
            "status": status,
            "blocking_reasons": sorted({gap["check"] for gap in blocking}),
            "warning_reasons": sorted({gap["check"] for gap in warnings}),
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    totals = report["totals"]
    lines = [
        "# Data readiness report", "", f"Status: **{report['readiness']['status']}**", "",
        f"Generated: {report['generated_at']}", "",
        f"Scope: {totals['sources']} sources, {totals['meetings']} meetings, "
        f"{totals['races']} races and {totals['runners']} runners.", "",
        "## Completeness", "", "| Check | Complete | Eligible | Coverage | Severity |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for name, check in report["checks"].items():
        coverage = "n/a" if check["coverage_pct"] is None else f"{check['coverage_pct']:.2f}%"
        lines.append(f"| {name} | {check['complete']} | {check['eligible']} | {coverage} | {check['severity']} |")
    lines += ["", "## Sources", "", "| Source | Races | Runners | Blocking gaps | Warnings |",
              "| --- | ---: | ---: | ---: | ---: |"]
    for source in report["sources"]:
        lines.append(f"| {source['source']} | {source.get('races', 0)} | {source.get('runners', 0)} | "
                     f"{source.get('blocking_gaps', 0)} | {source.get('warnings', 0)} |")
    lines += ["", "## Gaps", ""]
    if not report["gaps"]:
        lines.append("No gaps found.")
    else:
        lines += ["| Severity | Check | Race | Runner | Reason |", "| --- | --- | --- | ---: | --- |"]
        for gap in report["gaps"]:
            race = f"{gap['race_date']} {gap['track_slug']} R{gap['race_number'] or '-'} ({gap['source']})"
            lines.append(f"| {gap['severity']} | {gap['check']} | {race} | {gap['runner_number'] or '-'} | {gap['reason']} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=ROOT / "data" / "racing_engine.sqlite")
    parser.add_argument("--from-date")
    parser.add_argument("--to-date")
    parser.add_argument("--state", action="append", choices=("NSW", "VIC"), dest="states")
    parser.add_argument("--source", action="append", dest="sources")
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--fail-on-not-ready", action="store_true")
    args = parser.parse_args()
    uri = f"file:{args.database.resolve()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    try:
        report = build_report(connection, from_date=args.from_date, to_date=args.to_date,
                              states=args.states, sources=args.sources, database_path=str(args.database.resolve()))
    finally:
        connection.close()
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n" if args.format == "json" else render_markdown(report)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)
    else:
        print(rendered, end="")
    if args.fail_on_not_ready and report["readiness"]["status"] == "NOT_READY":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
