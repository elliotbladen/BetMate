"""Parse historic race-condition text into an auditable class taxonomy."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from .storage import RacingStore


ROOT = Path(__file__).resolve().parents[1]
PARSER_VERSION = "race-class-taxonomy-v1"


def first_match(pattern: str, text: str) -> int | None:
    match = re.search(pattern, text, re.I)
    return int(match.group(1)) if match else None


def classify(text: str | None) -> dict:
    raw = text or ""
    group = first_match(r"\bGroup\s*(\d)\b|\bG(\d)\b", raw)
    # `first_match` intentionally handles the common Group form; G1 aliases
    # are caught below because they place the number in capture group two.
    if group is None:
        alias = re.search(r"\bG([1-3])\b", raw, re.I)
        group = int(alias.group(1)) if alias else None
    benchmark = first_match(r"\b(?:BenchMark|Benchmark|BM)\s*(\d+)\b", raw)
    class_number = first_match(r"\bClass\s*(\d+)\b", raw)
    if group:
        family = "group"
    elif re.search(r"\bListed\b", raw, re.I):
        family = "listed"
    elif benchmark is not None:
        family = "benchmark"
    elif class_number is not None:
        family = "class"
    elif re.search(r"\bMaiden\b", raw, re.I):
        family = "maiden"
    elif re.search(r"\b(?:Quality|Open)\b", raw, re.I):
        family = "open_or_quality"
    elif re.search(r"\bHandicap\b", raw, re.I):
        family = "handicap_unspecified"
    else:
        family = "unclassified"
    race_type = next((value for value in ("Handicap", "Set Weights plus Penalties", "Set Weights", "Quality", "Plate")
                      if re.search(r"\b" + re.escape(value) + r"\b", raw, re.I)), None)
    age = next((value for value in ("Two-Years-Old", "Three-Years-Old", "Four-Years-Old and Upwards", "Three-Years-Old and Upwards")
                if value.lower() in raw.lower()), None)
    sex = next((value for value in ("Fillies and Mares", "Fillies", "Mares", "Colts and Geldings")
                if value.lower() in raw.lower()), None)
    return {"race_type": race_type, "class_family": family, "group_grade": group,
            "benchmark": benchmark, "class_number": class_number, "age_condition": age,
            "sex_condition": sex, "raw_class_text": raw, "parser_version": PARSER_VERSION}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", choices=("VIC", "NSW", "ALL"), default="ALL")
    args = parser.parse_args()
    store = RacingStore(ROOT / "data" / "racing_engine.sqlite")
    try:
        states = ("VIC", "NSW") if args.state == "ALL" else (args.state,)
        rows = store.connection.execute(
            "SELECT source,race_date,track_slug,race_number,race_class FROM race_results WHERE state IN ({})".format(
                ",".join("?" for _ in states)), states).fetchall()
        counts: dict[str, int] = {}
        for row in rows:
            parsed = classify(row["race_class"])
            store.upsert_race_classification({**dict(row), **parsed})
            counts[parsed["class_family"]] = counts.get(parsed["class_family"], 0) + 1
        print(json.dumps({"races_classified": len(rows), "families": counts}, sort_keys=True))
    finally:
        store.close()


if __name__ == "__main__":
    main()
