"""Import authorised official results and runner sectionals from CSV files.

This module deliberately has no scraper. The data owner/source is captured on
every row and the importer accepts a stable, documented interchange format.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from .storage import RacingStore


ROOT = Path(__file__).resolve().parents[1]
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class ImportError(ValueError):
    """Raised for a CSV that cannot safely become canonical model data."""


def required(row: dict[str, str], field: str, line: int) -> str:
    value = (row.get(field) or "").strip()
    if not value:
        raise ImportError(f"Line {line}: {field} is required.")
    return value


def optional_float(value: str | None, field: str, line: int) -> float | None:
    value = (value or "").strip()
    if not value:
        return None
    try:
        parsed = float(value)
    except ValueError as error:
        raise ImportError(f"Line {line}: {field} must be numeric, got {value!r}.") from error
    if parsed < 0:
        raise ImportError(f"Line {line}: {field} cannot be negative.")
    return parsed


def optional_int(value: str | None, field: str, line: int) -> int | None:
    value = (value or "").strip()
    if not value:
        return None
    try:
        parsed = int(value)
    except ValueError as error:
        raise ImportError(f"Line {line}: {field} must be a whole number, got {value!r}.") from error
    if parsed < 0:
        raise ImportError(f"Line {line}: {field} cannot be negative.")
    return parsed


def validate_common(row: dict[str, str], line: int) -> dict[str, Any]:
    race_date = required(row, "race_date", line)
    if not DATE_RE.match(race_date):
        raise ImportError(f"Line {line}: race_date must be YYYY-MM-DD.")
    state = required(row, "state", line).upper()
    if state not in {"NSW", "VIC"}:
        raise ImportError(f"Line {line}: state must be NSW or VIC.")
    return {
        "race_date": race_date,
        "state": state,
        "track_slug": required(row, "track_slug", line).lower(),
        "race_number": optional_int(required(row, "race_number", line), "race_number", line),
        "runner_number": optional_int(required(row, "runner_number", line), "runner_number", line),
    }


def import_results(store: RacingStore, path: Path, source: str) -> int:
    grouped: dict[tuple[str, str, str, int], dict[str, Any]] = defaultdict(lambda: {"runners": []})
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for line, row in enumerate(csv.DictReader(handle), start=2):
            common = validate_common(row, line)
            runner_name = required(row, "runner_name", line)
            finish_position = optional_int(row.get("finish_position"), "finish_position", line)
            beaten_lengths = optional_float(row.get("beaten_lengths"), "beaten_lengths", line)
            if finish_position is not None and finish_position == 0:
                raise ImportError(f"Line {line}: finish_position must start at 1.")
            key = (common["race_date"], common["state"], common["track_slug"], common["race_number"])
            race = grouped[key]
            race.update({
                **{key: value for key, value in common.items() if key != "runner_number"},
                "official_time_seconds": optional_float(row.get("official_time_seconds"), "official_time_seconds", line),
                "track_condition": (row.get("track_condition") or "").strip() or None,
                "rail_position": (row.get("rail_position") or "").strip() or None,
                "source_url": (row.get("source_url") or "").strip() or None,
            })
            race["runners"].append({
                "runner_number": common["runner_number"], "runner_name": runner_name,
                "finish_position": finish_position, "beaten_lengths": beaten_lengths,
                "finish_time_seconds": optional_float(row.get("finish_time_seconds"), "finish_time_seconds", line),
                "result_status": (row.get("result_status") or "finished").strip().lower(),
                "source_url": race["source_url"],
            })

    for race in grouped.values():
        raw_race = {key: value for key, value in race.items() if key != "runners"}
        store.upsert_result(source=source, raw_race=raw_race, **race)
    return len(grouped)


def import_sectionals(store: RacingStore, path: Path, source: str) -> int:
    rows: list[dict[str, Any]] = []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for line, row in enumerate(csv.DictReader(handle), start=2):
            common = validate_common(row, line)
            marker = optional_int(required(row, "marker_metres", line), "marker_metres", line)
            if marker is None:
                raise ImportError(f"Line {line}: marker_metres is required.")
            rows.append({
                "source": source, **common, "marker_metres": marker,
                "section_seconds": optional_float(row.get("section_seconds"), "section_seconds", line),
                "position_at_marker": optional_int(row.get("position_at_marker"), "position_at_marker", line),
                "distance_travelled_metres": optional_float(row.get("distance_travelled_metres"), "distance_travelled_metres", line),
                "speed_kmh": optional_float(row.get("speed_kmh"), "speed_kmh", line),
                "source_url": (row.get("source_url") or "").strip() or None,
            })
    store.upsert_sectionals(rows)
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, help="Canonical results CSV")
    parser.add_argument("--sectionals", type=Path, help="Canonical runner-sectionals CSV")
    parser.add_argument("--source", required=True, help="Authorised source identifier, e.g. racing-com-manual")
    args = parser.parse_args()
    if not args.results and not args.sectionals:
        parser.error("Provide --results and/or --sectionals.")

    store = RacingStore(ROOT / "data" / "racing_engine.sqlite")
    try:
        if args.results:
            print(f"Imported {import_results(store, args.results, args.source)} result races.")
        if args.sectionals:
            print(f"Imported {import_sectionals(store, args.sectionals, args.source)} sectional rows.")
    finally:
        store.close()


if __name__ == "__main__":
    main()
