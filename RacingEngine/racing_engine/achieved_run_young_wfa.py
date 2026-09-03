"""Research-only young-horse/WFA achieved-run candidate.

The accepted form-first model remains frozen.  This candidate fixes the
semantic failure where complete but immature collateral receives maximum
authority, and makes winner-margin credit conditional on independent clock and
sectional evidence.  WFA profile data is audited explicitly; set-weight and WFA
allowances are never mistaken for superior performance.
"""
from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .achieved_run_collateral import opposition_evidence
from .achieved_run_recovery import BASE_VERSION, ROOT, race_weight_policy, schema, weight_component
from .achieved_run_separated import achieved_margin
from .horse_profiles import DERIVATION_VERSION
from .race_time_evidence import VERSION as TIME_VERSION
from .energy_sectionals import HIER_VERSION as ENERGY_VERSION
from .storage import RacingStore
from .v2_ratings import pounds_per_length
from .wfa import standard_weight

MODEL_VERSION = "achieved-run-v2.10-young-wfa-shadow"
YOUNG_MAX_OPPOSITION_RELIABILITY = 0.50
GENERAL_MAX_OPPOSITION_RELIABILITY = 0.80
TIME_SUPPORT_THRESHOLD = 0.50
SECTIONAL_SUPPORT_THRESHOLD = 1.00


def age_cohort(race_class: str | None) -> str:
    text = (race_class or "").lower()
    if "two-years-old" in text and "upwards" not in text:
        return "2yo_only"
    if "three-years-old" in text and "upwards" not in text:
        return "3yo_only"
    return "open_age"


def evidence_margin_fraction(clock_signal: float | None, sectional_signal: float | None) -> float:
    """Retain half the observed margin, plus a quarter per independent support."""
    clock = clock_signal is not None and clock_signal >= TIME_SUPPORT_THRESHOLD
    sectionals = sectional_signal is not None and sectional_signal >= SECTIONAL_SUPPORT_THRESHOLD
    return 0.50 + 0.25 * int(clock) + 0.25 * int(sectionals)


def reliability_weight(reliabilities: list[float], coverage: float, cohort: str) -> float:
    if not reliabilities:
        return 0.0
    cap = YOUNG_MAX_OPPOSITION_RELIABILITY if cohort in {"2yo_only", "3yo_only"} else GENERAL_MAX_OPPOSITION_RELIABILITY
    raw = statistics.mean(reliabilities) * max(0.0, min(1.0, coverage))
    return max(0.0, min(cap, raw))


def _winner_evidence(store: RacingStore, race_id: str, runner_number: int) -> dict[str, Any]:
    clock = store.connection.execute(
        "SELECT fast_mad_signal,confidence FROM v2_race_time_evidence WHERE version=? AND race_id=?",
        (TIME_VERSION, race_id),
    ).fetchone()
    energy = store.connection.execute(
        """SELECT achievement_signal,compensation_signal,confidence
             FROM v2_runner_energy_sectionals
            WHERE version=? AND race_id=? AND runner_number=?""",
        (ENERGY_VERSION, race_id, runner_number),
    ).fetchone()
    return {
        "clock_signal": float(clock["fast_mad_signal"]) if clock else None,
        "clock_confidence": float(clock["confidence"]) if clock else None,
        "sectional_signal": float(energy["achievement_signal"]) if energy else None,
        "sectional_compensation": float(energy["compensation_signal"]) if energy else None,
        "sectional_confidence": float(energy["confidence"]) if energy else None,
    }


def _profile(store: RacingStore, race: Any, runner_number: int) -> dict[str, Any]:
    row = store.connection.execute(
        """SELECT racing_age,sex,age_method,profile_source,detail_json
             FROM runner_derived_profiles
            WHERE derivation_version=? AND source=? AND race_date=? AND track_slug=?
              AND race_number=? AND runner_number=?""",
        (DERIVATION_VERSION, race["source"], race["race_date"], race["track_slug"],
         race["race_number"], runner_number),
    ).fetchone()
    if row is None:
        return {"available": False, "wfa_standard_kg": None}
    detail = json.loads(row["detail_json"] or "{}")
    reference = None
    if row["racing_age"] is not None and row["sex"] and race["distance_metres"]:
        reference = standard_weight(
            race["race_date"], int(race["distance_metres"]), int(row["racing_age"]), row["sex"],
            northern_sired_jan_jul_foal=bool(detail.get("ar170_eligible")),
        )
    return {"available": True, "racing_age": row["racing_age"], "sex": row["sex"],
            "age_method": row["age_method"], "profile_source": row["profile_source"],
            "wfa_standard_kg": reference, "wfa_status": "audited_allowance_neutral"}


def build(store: RacingStore) -> dict[str, Any]:
    schema(store)
    evidence = opposition_evidence(store)
    store.connection.execute("DELETE FROM v2_achieved_run_candidates WHERE model_version=?", (MODEL_VERSION,))
    counts = Counter()
    for race in store.connection.execute("SELECT * FROM v2_clean_races ORDER BY race_date,race_id"):
        runners = store.connection.execute(
            """SELECT c.*,p.performance_rating,p.race_strength base_strength,p.class_standard,p.confidence
                 FROM v2_clean_runner_results c JOIN v2_run_performances p USING(race_id,runner_number)
                WHERE c.race_id=? AND c.result_status='finished' AND c.finish_position IS NOT NULL
                  AND p.model_version=? ORDER BY c.finish_position,c.runner_number""",
            (race["race_id"], BASE_VERSION),
        ).fetchall()
        winner = next((row for row in runners if int(row["finish_position"]) == 1), None)
        if winner is None:
            continue
        cohort = age_cohort(race["race_class"])
        item = evidence.get(race["race_id"], {})
        reliabilities = [float(value["reliability"]) for value in item.get("principals", [])]
        reliability = reliability_weight(reliabilities, float(item.get("principal_coverage") or 0.0), cohort)
        standard = float(winner["class_standard"])
        anchor = item.get("opposition_anchor")
        strength = standard if anchor is None else reliability * float(anchor) + (1.0 - reliability) * standard
        signals = _winner_evidence(store, race["race_id"], int(winner["runner_number"]))
        margin_fraction = evidence_margin_fraction(signals["clock_signal"], signals["sectional_signal"])
        ppl = pounds_per_length(int(race["distance_metres"] or 1600))
        policy = race_weight_policy(race["race_class"])
        for row in runners:
            position = int(row["finish_position"])
            margin = float(row["beaten_lengths"] or 0.0)
            raw_margin = achieved_margin(position, margin, ppl)
            margin_component = raw_margin * margin_fraction if position == 1 else raw_margin
            weight = weight_component(policy, row["weight_carried_kg"], winner["weight_carried_kg"])
            achieved = strength + margin_component + weight
            profile = _profile(store, race, int(row["runner_number"]))
            detail = {"candidate_version": MODEL_VERSION, "base_model_version": BASE_VERSION,
                      "research_only": True, "age_cohort": cohort, "class_standard": standard,
                      "opposition_anchor": anchor, "opposition_reliability": reliability,
                      "opposition_reliability_cap": YOUNG_MAX_OPPOSITION_RELIABILITY if cohort != "open_age" else GENERAL_MAX_OPPOSITION_RELIABILITY,
                      "margin_evidence_fraction": margin_fraction, "independent_evidence": signals,
                      "race_weight_policy": policy, "wfa_profile": profile,
                      "wfa_interpretation": "allowances neutralised; not added as merit",
                      "accepted_model_changed": False}
            store.connection.execute(
                """INSERT INTO v2_achieved_run_candidates VALUES
                   (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (MODEL_VERSION, race["race_id"], row["runner_number"], row["horse_key"], row["horse_name"],
                 achieved, row["performance_rating"], strength, row["base_strength"],
                 margin_component if position == 1 else 0.0,
                 margin_component if position != 1 else 0.0, weight, 0.0, 0.0, 0.0,
                 row["confidence"], json.dumps(detail, sort_keys=True)),
            )
            counts["performances"] += 1
            counts[f"profile_{'available' if profile['available'] else 'missing'}"] += 1
        counts["races"] += 1
        counts[f"cohort_{cohort}"] += 1
    store.connection.commit()
    return {"model_version": MODEL_VERSION, **dict(counts), "accepted_ratings_changed": False}


def evaluate(store: RacingStore) -> dict[str, Any]:
    rows = store.connection.execute(
        """SELECT a.*,r.race_date,r.race_class,r.class_family,c.finish_position
             FROM v2_achieved_run_candidates a JOIN v2_clean_races r USING(race_id)
             JOIN v2_clean_runner_results c USING(race_id,runner_number)
            WHERE a.model_version=? AND c.finish_position=1 ORDER BY r.race_date""",
        (MODEL_VERSION,),
    ).fetchall()
    cohorts = defaultdict(list)
    for row in rows:
        cohorts[age_cohort(row["race_class"])].append(row)
    histories = defaultdict(list)
    for point in store.connection.execute(
        """SELECT p.horse_key,r.race_date,p.performance_rating FROM v2_run_performances p
             JOIN v2_clean_races r USING(race_id) WHERE p.model_version=?
             ORDER BY p.horse_key,r.race_date,r.race_id""", (BASE_VERSION,)):
        histories[point["horse_key"]].append((point["race_date"], float(point["performance_rating"])))
    next_targets = {}
    for horse_key, points in histories.items():
        for current, nxt in zip(points, points[1:]):
            next_targets[(horse_key, current[0])] = nxt[1]

    def predictive(sample: list[Any]) -> dict[str, Any]:
        pairs = [(row, next_targets[(row["horse_key"], row["race_date"])]) for row in sample
                 if (row["horse_key"], row["race_date"]) in next_targets]
        train = [(row, target) for row, target in pairs if row["race_date"] < "2025-01-01"]
        test = [(row, target) for row, target in pairs if row["race_date"] >= "2025-01-01"]
        trials = []
        for alpha in (value / 20 for value in range(21)):
            error = statistics.mean(abs(target - (float(row["base_rating"]) + alpha *
                (float(row["achieved_rating"]) - float(row["base_rating"])))) for row, target in train) if train else None
            trials.append((alpha, error))
        selected = min(trials, key=lambda value: (value[1], value[0]))[0] if train else 0.0
        def mae(sample_pairs: list[tuple[Any, float]], alpha: float) -> float | None:
            return statistics.mean(abs(target - (float(row["base_rating"]) + alpha *
                (float(row["achieved_rating"]) - float(row["base_rating"])))) for row, target in sample_pairs) if sample_pairs else None
        return {"training_pairs": len(train), "test_pairs": len(test), "selected_shrinkage": selected,
                "test_mae_base": mae(test, 0.0), "test_mae_raw_candidate": mae(test, 1.0),
                "test_mae_shrunk_candidate": mae(test, selected)}

    summary = {}
    for name, sample in cohorts.items():
        group = [row for row in sample if row["class_family"] in {"listed", "group_3", "group_2", "group_1"}]
        summary[name] = {"winner_runs": len(sample), "group_listed_winners": len(group),
            "mean_candidate_minus_standard": statistics.mean(float(x["achieved_rating"])-float(json.loads(x["detail_json"])["class_standard"]) for x in group) if group else None,
            "mean_base_minus_standard": statistics.mean(float(x["base_rating"])-float(json.loads(x["detail_json"])["class_standard"]) for x in group) if group else None,
            "all_races_next_start": predictive(sample), "group_listed_next_start": predictive(group)}
    guest = store.connection.execute(
        """SELECT * FROM v2_achieved_run_candidates WHERE model_version=?
              AND race_id='2026-08-29|rosehill|8' AND horse_key='guesthouse'""",
        (MODEL_VERSION,),
    ).fetchone()
    return {"cohorts": summary, "guest_house": dict(guest) if guest else None,
            "promotion_decision": "RESEARCH_SHADOW_ONLY",
            "promotion_blockers": ["time signal failed its existing promotion gate",
              "sectional signal has not passed all existing cross-cohort gates",
              "requires untouched prospective validation"]}


def run(store: RacingStore) -> dict[str, Any]:
    return {"build": build(store), "evaluation": evaluate(store)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=ROOT / "data" / "racing_engine.sqlite")
    parser.add_argument("--output", type=Path, default=ROOT / "reports" / "v2_ratings" / "achieved_run_v2_10_young_wfa.json")
    parser.add_argument("--evaluate-only", action="store_true")
    args = parser.parse_args(); store = RacingStore(args.database)
    try:
        report = {"build": {"skipped": True}, "evaluation": evaluate(store)} if args.evaluate_only else run(store)
    finally:
        store.close()
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
