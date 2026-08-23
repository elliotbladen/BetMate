"""Source-aware canonical sectional features; no environmental adjustments."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .storage import RacingStore, utc_now


ROOT = Path(__file__).resolve().parents[1]
FEATURE_VERSION = "canonical-sectionals-v1.0"
NSW_SOURCES = {"rnsw-authorised", "racing-com-nsw-authorised-v2"}
SUPPORTED = NSW_SOURCES | {"racing-com-rv-authorised"}
PLAUSIBLE = {"final_200_seconds": (8.0, 20.0), "final_400_seconds": (18.0, 36.0),
             "final_600_seconds": (27.0, 54.0)}


def derive(source: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Derive only intervals proven by the registered source semantics."""
    by_marker = {int(row["marker_metres"]): row for row in rows}
    values = {name: None for name in ("final_200_seconds", "final_400_seconds", "final_600_seconds",
                                      "early_to_800_seconds", "eight_to_four_seconds")}
    positions = {f"position_{marker}m": (by_marker.get(marker) or {}).get("position_at_marker")
                 for marker in (800, 600, 400, 200)}
    derivation: dict[str, Any] = {"source_semantics": None, "features": {}}
    missing: list[str] = []
    if source in NSW_SOURCES:
        derivation["source_semantics"] = "200m interval durations ending at metres-remaining markers"
        if all(marker in by_marker for marker in (200, 0)):
            values["final_200_seconds"] = float(by_marker[0]["section_seconds"])
            derivation["features"]["final_200_seconds"] = {"sum_markers": [0], "required_markers": [200, 0]}
        else:
            missing.append("final_200_requires_markers_200_0")
        if all(marker in by_marker for marker in (400, 200, 0)):
            values["final_400_seconds"] = sum(float(by_marker[m]["section_seconds"]) for m in (200, 0))
            derivation["features"]["final_400_seconds"] = {"sum_markers": [200, 0], "required_markers": [400, 200, 0]}
        else:
            missing.append("final_400_requires_markers_400_200_0")
        if all(marker in by_marker for marker in (600, 400, 200, 0)):
            values["final_600_seconds"] = sum(float(by_marker[m]["section_seconds"]) for m in (400, 200, 0))
            derivation["features"]["final_600_seconds"] = {"sum_markers": [400, 200, 0], "required_markers": [600, 400, 200, 0]}
        else:
            missing.append("final_600_requires_markers_600_400_200_0")
    elif source == "racing-com-rv-authorised":
        derivation["source_semantics"] = "to-800, 800-to-400, and 400-to-finish durations"
        if 0 in by_marker:
            values["final_400_seconds"] = float(by_marker[0]["section_seconds"])
            derivation["features"]["final_400_seconds"] = {"source_marker": 0, "meaning": "400_to_finish"}
        else:
            missing.append("final_400_requires_marker_0")
        if 800 in by_marker:
            values["early_to_800_seconds"] = float(by_marker[800]["section_seconds"])
        else:
            missing.append("early_to_800_requires_marker_800")
        if 400 in by_marker:
            values["eight_to_four_seconds"] = float(by_marker[400]["section_seconds"])
        else:
            missing.append("eight_to_four_requires_marker_400")
        missing += ["final_200_not_supplied_by_source", "final_600_not_supplied_by_source"]
    else:
        derivation["source_semantics"] = "unsupported"
        missing.append("unsupported_source")
    outliers = []
    for name, bounds in PLAUSIBLE.items():
        value = values[name]
        if value is not None and not bounds[0] <= value <= bounds[1]:
            outliers.append(f"{name}_outside_{bounds[0]}_{bounds[1]}")
    if "unsupported_source" in missing:
        quality = "unsupported_source"
    elif outliers:
        # A very slow split can be real (eased, injured, or tailed off). Flag
        # it for review without claiming that the source observation is false.
        quality = "outlier"
    elif not rows or all(values[name] is None for name in PLAUSIBLE):
        quality = "incomplete"
    else:
        quality = "ok"
    return {**values, **positions, "quality_status": quality,
            "missing_reasons": missing + outliers, "derivation": derivation}


def build_features(store: RacingStore, *, feature_version: str = FEATURE_VERSION,
                   from_date: str | None = None, to_date: str | None = None) -> dict[str, Any]:
    clauses = ["rr.result_status='finished'"]
    parameters: list[Any] = []
    if from_date:
        clauses.append("rr.race_date>=?"); parameters.append(from_date)
    if to_date:
        clauses.append("rr.race_date<=?"); parameters.append(to_date)
    runners = store.connection.execute(
        """SELECT rr.source,rr.race_date,rr.track_slug,rr.race_number,rr.runner_number
             FROM runner_results rr WHERE """ + " AND ".join(clauses) +
        " ORDER BY rr.race_date,rr.track_slug,rr.race_number,rr.runner_number", parameters).fetchall()
    now = utc_now()
    status_counts: Counter[str] = Counter()
    coverage: dict[str, Counter] = defaultdict(Counter)
    for runner in runners:
        key = tuple(runner[column] for column in ("source", "race_date", "track_slug", "race_number", "runner_number"))
        raw = [dict(row) for row in store.connection.execute(
            """SELECT marker_metres,section_seconds,position_at_marker FROM runner_sectionals
               WHERE source=? AND race_date=? AND track_slug=? AND race_number=? AND runner_number=?
               ORDER BY marker_metres DESC""", key)]
        result = derive(runner["source"], raw)
        status_counts[result["quality_status"]] += 1
        coverage[runner["source"]]["runners"] += 1
        for field in PLAUSIBLE:
            coverage[runner["source"]][field] += int(result[field] is not None)
        store.connection.execute(
            """INSERT INTO canonical_sectionals
               (feature_version,source,race_date,track_slug,race_number,runner_number,final_200_seconds,
                final_400_seconds,final_600_seconds,early_to_800_seconds,eight_to_four_seconds,
                position_800m,position_600m,position_400m,position_200m,quality_status,
                missing_reasons_json,derivation_json,created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(feature_version,source,race_date,track_slug,race_number,runner_number) DO UPDATE SET
                 final_200_seconds=excluded.final_200_seconds,final_400_seconds=excluded.final_400_seconds,
                 final_600_seconds=excluded.final_600_seconds,early_to_800_seconds=excluded.early_to_800_seconds,
                 eight_to_four_seconds=excluded.eight_to_four_seconds,position_800m=excluded.position_800m,
                 position_600m=excluded.position_600m,position_400m=excluded.position_400m,
                 position_200m=excluded.position_200m,quality_status=excluded.quality_status,
                 missing_reasons_json=excluded.missing_reasons_json,derivation_json=excluded.derivation_json,
                 created_at=excluded.created_at""",
            (feature_version, *key, result["final_200_seconds"], result["final_400_seconds"],
             result["final_600_seconds"], result["early_to_800_seconds"], result["eight_to_four_seconds"],
             result["position_800m"], result["position_600m"], result["position_400m"], result["position_200m"],
             result["quality_status"], json.dumps(result["missing_reasons"], sort_keys=True),
             json.dumps(result["derivation"], sort_keys=True), now))
    store.connection.commit()
    return {"feature_version": feature_version, "runners": len(runners),
            "quality": dict(sorted(status_counts.items())),
            "coverage_by_source": {source: dict(counts) for source, counts in sorted(coverage.items())}}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=ROOT / "data" / "racing_engine.sqlite")
    parser.add_argument("--from-date"); parser.add_argument("--to-date")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    store = RacingStore(args.database)
    try:
        report = build_features(store, from_date=args.from_date, to_date=args.to_date)
    finally:
        store.close()
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(rendered)
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
