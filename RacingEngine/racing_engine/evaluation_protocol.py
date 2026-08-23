"""Versioned evaluation policy shared by every model comparison."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL = ROOT / "config" / "evaluation_protocol_v1.json"
REQUIRED_SECTIONS = {"protocol_version", "periods", "eligibility", "metrics", "segments", "resampling", "promotion_rules"}
PERIOD_ORDER = ("train", "validation", "historical_holdout", "prospective_holdout")


@dataclass(frozen=True)
class Eligibility:
    eligible: bool
    reason: str | None
    starters: tuple[dict[str, Any], ...]


def canonical_json(value: dict[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def protocol_hash(value: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def validate_protocol(value: dict[str, Any]) -> None:
    missing = REQUIRED_SECTIONS - set(value)
    if missing:
        raise ValueError(f"protocol missing required sections: {sorted(missing)}")
    if value["protocol_version"] != "evaluation-v1":
        raise ValueError(f"unsupported protocol version: {value['protocol_version']}")
    periods = value["periods"]
    if tuple(periods) != PERIOD_ORDER:
        raise ValueError(f"periods must appear in chronological order: {PERIOD_ORDER}")
    prior_end: date | None = None
    for name in PERIOD_ORDER:
        start = date.fromisoformat(periods[name]["from"])
        end_text = periods[name]["to"]
        end = date.fromisoformat(end_text) if end_text else None
        if end and end < start:
            raise ValueError(f"{name} ends before it starts")
        if prior_end and start <= prior_end:
            raise ValueError(f"{name} overlaps the preceding period")
        prior_end = end
    metrics = value["metrics"]
    edges = metrics["calibration_edges"]
    if edges[0] != 0 or edges[-1] != 1 or edges != sorted(set(edges)):
        raise ValueError("calibration edges must be unique, ascending, and cover zero to one")
    if not 0 < metrics["probability_floor"] < 1:
        raise ValueError("probability floor must lie between zero and one")
    sampling = value["resampling"]
    if sampling["unit"] != "meeting_day" or sampling["repetitions"] <= 0:
        raise ValueError("V1 requires positive meeting-day block resampling")


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    value = json.loads(path.read_text())
    validate_protocol(value)
    return value


def period_for(race_date: str, protocol: dict[str, Any]) -> str | None:
    target = date.fromisoformat(race_date)
    matches = []
    for name, bounds in protocol["periods"].items():
        start = date.fromisoformat(bounds["from"])
        end = date.fromisoformat(bounds["to"]) if bounds["to"] else None
        if target >= start and (end is None or target <= end):
            matches.append(name)
    if len(matches) > 1:
        raise ValueError(f"race date {race_date} belongs to multiple periods")
    return matches[0] if matches else None


def assess_eligibility(rows: Iterable[dict[str, Any]], protocol: dict[str, Any]) -> Eligibility:
    policy = protocol["eligibility"]
    excluded = set(policy["starter_excluded_statuses"])
    starters = tuple(row for row in rows if str(row.get("result_status", "finished")).lower() not in excluded)
    if len(starters) < policy["minimum_starters"]:
        return Eligibility(False, "insufficient_starters", starters)
    if len({(row.get("runner_number"), row.get("runner_name")) for row in starters}) != len(starters):
        return Eligibility(False, "duplicate_runner", starters)
    winner_count = sum(row.get("finish_position") == 1 for row in starters)
    if winner_count == 0:
        return Eligibility(False, "missing_winner", starters)
    if winner_count > policy["required_winners"]:
        return Eligibility(False, "multiple_winners", starters)
    return Eligibility(True, None, starters)


def validate_probability_book(probabilities: Iterable[float], expected_size: int, *, tolerance: float = 1e-9) -> list[float]:
    values = list(probabilities)
    if len(values) != expected_size:
        raise ValueError("probability book does not match starter count")
    if any(not math.isfinite(value) or value <= 0 or value > 1 for value in values):
        raise ValueError("probabilities must be finite and in (0, 1]")
    if not math.isclose(sum(values), 1.0, abs_tol=tolerance):
        raise ValueError("probabilities do not sum to one")
    return values


def score_race(probabilities: Iterable[float], outcomes: Iterable[float], protocol: dict[str, Any]) -> dict[str, float | int]:
    outcomes_list = list(outcomes)
    probabilities_list = validate_probability_book(probabilities, len(outcomes_list))
    if sum(outcomes_list) != 1 or any(value not in (0, 1) for value in outcomes_list):
        raise ValueError("outcomes must contain exactly one winner")
    winner_index = outcomes_list.index(1)
    floor = protocol["metrics"]["probability_floor"]
    brier_sum = sum((probability - outcome) ** 2 for probability, outcome in zip(probabilities_list, outcomes_list))
    winner_probability = probabilities_list[winner_index]
    ordered = sorted(enumerate(probabilities_list), key=lambda item: (-item[1], item[0]))
    winner_rank = next(rank for rank, (index, _) in enumerate(ordered, start=1) if index == winner_index)
    return {
        "log_loss": -math.log(max(winner_probability, floor)),
        "race_brier": brier_sum,
        "runner_brier": brier_sum / len(outcomes_list),
        "winner_rank": winner_rank,
    }
