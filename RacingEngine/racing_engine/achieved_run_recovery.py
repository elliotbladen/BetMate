"""Frozen achieved-run recovery candidate for the V2 ratings foundation.

This candidate fixes two known semantic defects without overwriting accepted
``form-first-v2.0`` figures:

* a dominant winner receives bounded positive margin evidence; and
* weight is interpreted by race conditions rather than as a universal carried-
  weight bonus (standard/WFA sex and age allowances are not treated as merit).

Pace, sectional, clock/variant and retrospective collateral adjustments remain
zero until their independently frozen promotion gates pass.  Their coverage is
recorded so absence cannot be mistaken for a fitted zero.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .storage import RacingStore
from .v2_ratings import CLASS_STANDARDS, MODEL_VERSION as BASE_VERSION, correlation, pounds_per_length

ROOT = Path(__file__).resolve().parents[1]
MODEL_VERSION = "achieved-run-v2.1-margin-weight-shadow"
MAX_WIN_MARGIN_POINTS = 12.0
BREAKOUT_MARGIN_LENGTHS = 3.0
BREAKOUT_MAX_COLLATERAL_WEIGHT = 0.35


def race_weight_policy(race_class: str | None) -> str:
    text = (race_class or "").lower()
    if "handicap" in text or text.startswith("quality"):
        return "handicap_relative_burden"
    if "weight for age" in text or "standard weight for age" in text:
        return "wfa_allowance_neutral"
    if "set weight" in text:
        return "set_weight_allowance_neutral"
    return "unknown_neutral"


def weight_component(policy: str, carried: float | None, winner_carried: float | None) -> float:
    if policy != "handicap_relative_burden" or carried is None or winner_carried is None:
        return 0.0
    return (float(carried) - float(winner_carried)) * 2.20462262


def winner_margin_component(winning_margin: float | None, ppl: float) -> float:
    return min(MAX_WIN_MARGIN_POINTS, max(0.0, float(winning_margin or 0.0)) * ppl)


def breakout_collateral_weight(
    original: float,
    *,
    winning_margin: float,
    winner_prior: float | None,
    class_standard: float,
    prior_starts: int,
) -> tuple[float, bool]:
    """Reduce stale-anchor authority only when independent breakout flags agree."""
    flagged = (
        winning_margin >= BREAKOUT_MARGIN_LENGTHS
        and prior_starts <= 8
        and winner_prior is not None
        and winner_prior <= class_standard - 10.0
    )
    return (min(original, BREAKOUT_MAX_COLLATERAL_WEIGHT), True) if flagged else (original, False)


def schema(store: RacingStore) -> None:
    store.connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS v2_achieved_run_candidates (
          model_version TEXT NOT NULL, race_id TEXT NOT NULL,
          runner_number INTEGER NOT NULL, horse_key TEXT NOT NULL,
          horse_name TEXT NOT NULL, achieved_rating REAL NOT NULL,
          base_rating REAL NOT NULL, race_strength REAL NOT NULL,
          base_race_strength REAL NOT NULL, winner_margin_component REAL NOT NULL,
          beaten_margin_component REAL NOT NULL, weight_component REAL NOT NULL,
          time_variant_component REAL NOT NULL, sectional_component REAL NOT NULL,
          collateral_revision_component REAL NOT NULL, confidence REAL NOT NULL,
          detail_json TEXT NOT NULL,
          PRIMARY KEY(model_version,race_id,runner_number)
        );
        """
    )


def _prior_starts(store: RacingStore, horse_key: str, day: str) -> int:
    return int(store.connection.execute(
        """SELECT count(*) FROM v2_run_performances p JOIN v2_clean_races r USING(race_id)
             WHERE p.model_version=? AND p.horse_key=? AND r.race_date<?""",
        (BASE_VERSION, horse_key, day),
    ).fetchone()[0])


def build(store: RacingStore) -> dict[str, Any]:
    schema(store)
    store.connection.execute(
        "DELETE FROM v2_achieved_run_candidates WHERE model_version=?", (MODEL_VERSION,)
    )
    races = store.connection.execute(
        "SELECT * FROM v2_clean_races ORDER BY race_date,race_id"
    ).fetchall()
    counts = Counter()
    named: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for race in races:
        runners = store.connection.execute(
            """SELECT c.*,p.performance_rating,p.race_strength,p.class_standard,
                      p.anchor_coverage,p.confidence,p.detail_json
                 FROM v2_clean_runner_results c JOIN v2_run_performances p
                   USING(race_id,runner_number)
                WHERE c.race_id=? AND c.result_status='finished'
                  AND c.finish_position IS NOT NULL AND p.model_version=?
                ORDER BY c.finish_position,c.runner_number""",
            (race["race_id"], BASE_VERSION),
        ).fetchall()
        winner = next((row for row in runners if int(row["finish_position"]) == 1), None)
        if winner is None:
            continue
        detail = json.loads(winner["detail_json"])
        original_weight = float(detail.get("collateral_weight") or 0.0)
        standard = float(winner["class_standard"])
        winning_margin = float(winner["beaten_lengths"] or 0.0)
        prior_starts = _prior_starts(store, winner["horse_key"], race["race_date"])
        prior = float(winner["official_handicap_rating"]) if winner["official_handicap_rating"] is not None else None
        adjusted_weight, breakout = breakout_collateral_weight(
            original_weight, winning_margin=winning_margin, winner_prior=prior,
            class_standard=standard, prior_starts=prior_starts,
        )
        collateral = detail.get("collateral_anchor")
        strength = (
            adjusted_weight * float(collateral) + (1.0 - adjusted_weight) * standard
            if collateral is not None else standard
        )
        ppl = pounds_per_length(int(race["distance_metres"] or 1600))
        policy = race_weight_policy(race["race_class"])
        positive = winner_margin_component(winning_margin, ppl)
        for row in runners:
            beaten = 0.0 if int(row["finish_position"]) == 1 else float(row["beaten_lengths"] or 0.0)
            beaten_component = -beaten * ppl
            weight = weight_component(policy, row["weight_carried_kg"], winner["weight_carried_kg"])
            winner_component = positive if int(row["finish_position"]) == 1 else 0.0
            achieved = strength + winner_component + beaten_component + weight
            component_detail = {
                "base_model_version": BASE_VERSION,
                "race_weight_policy": policy,
                "original_collateral_weight": original_weight,
                "candidate_collateral_weight": adjusted_weight,
                "collateral_anchor": collateral,
                "class_standard": standard,
                "breakout_anchor_relief": breakout,
                "breakout_flags": {"winning_margin": winning_margin, "winner_prior": prior,
                                   "winner_prior_starts": prior_starts},
                "winner_margin_cap_points": MAX_WIN_MARGIN_POINTS,
                "time_variant_status": "not_promoted_zero",
                "sectional_status": "not_promoted_zero",
                "collateral_revision_status": "not_yet_applied_zero",
                "research_only": True,
            }
            store.connection.execute(
                """INSERT INTO v2_achieved_run_candidates VALUES
                   (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (MODEL_VERSION, race["race_id"], row["runner_number"], row["horse_key"],
                 row["horse_name"], achieved, row["performance_rating"], strength,
                 row["race_strength"], winner_component, beaten_component, weight,
                 0.0, 0.0, 0.0, row["confidence"], json.dumps(component_detail, sort_keys=True)),
            )
            counts["performances"] += 1
            if row["horse_key"] in {"naturalfling", "gringotts", "shezaalibi"}:
                named[row["horse_key"]].append({"race_date": race["race_date"],
                    "race_id": race["race_id"], "finish_position": row["finish_position"],
                    "base_rating": float(row["performance_rating"]), "candidate_rating": achieved,
                    "winner_margin_component": winner_component, "weight_component": weight,
                    "policy": policy})
        counts["races"] += 1
        counts["breakout_anchor_relief_races"] += int(breakout)
    store.connection.commit()
    return {"model_version": MODEL_VERSION, **dict(counts), "named": dict(named)}


def audits(store: RacingStore) -> dict[str, Any]:
    natural = store.connection.execute(
        """SELECT a.*,r.race_date FROM v2_achieved_run_candidates a
             JOIN v2_clean_races r USING(race_id)
            WHERE a.model_version=? AND a.horse_key='naturalfling'
              AND r.race_date='2026-08-15'""", (MODEL_VERSION,)
    ).fetchone()
    pair = [dict(row) for row in store.connection.execute(
        """SELECT a.horse_name,a.achieved_rating,a.base_rating,a.weight_component,
                  a.beaten_margin_component FROM v2_achieved_run_candidates a
            WHERE a.model_version=? AND a.race_id='2026-08-22|randwick|9'
              AND a.horse_key IN ('gringotts','shezaalibi') ORDER BY a.horse_key""",
        (MODEL_VERSION,),
    )]
    # Preserve the already reviewed official-classification gate on the same
    # historical season, comparing peak candidate figures rather than fitting.
    matches = store.connection.execute(
        """SELECT a.official_rating,MAX(c.achieved_rating) candidate_rating
             FROM v2_audit_classifications a JOIN v2_achieved_run_candidates c USING(horse_key)
             JOIN v2_clean_races r USING(race_id)
            WHERE c.model_version=? AND a.season='2024/25'
              AND r.race_date>='2024-08-01' AND r.race_date<'2025-08-01'
            GROUP BY a.horse_key""", (MODEL_VERSION,)
    ).fetchall()
    rho = correlation([float(x[0]) for x in matches], [float(x[1]) for x in matches])
    natural_rating = float(natural["achieved_rating"]) if natural else None
    pair_by_name = {row["horse_name"]: row for row in pair}
    pair_pass = (
        "Sheza Alibi" in pair_by_name and "Gringotts" in pair_by_name
        and pair_by_name["Sheza Alibi"]["achieved_rating"] > pair_by_name["Gringotts"]["achieved_rating"]
        and pair_by_name["Sheza Alibi"]["weight_component"] == 0.0
        and pair_by_name["Gringotts"]["weight_component"] == 0.0
    )
    cohort = breakout_cohort(store)
    gates = {
        "natural_fling_100_to_110": natural_rating is not None and 100.0 <= natural_rating <= 110.0,
        "gringotts_sheza_wfa_semantics": pair_pass,
        "elite_spearman_at_least_0_50": rho is not None and rho >= 0.50,
        "frozen_breakout_cohort_90d_mae": cohort["horizons"]["90"]["candidate_beats_both_baselines"],
    }
    return {"natural_fling": dict(natural) if natural else None,
            "gringotts_sheza_alibi": pair, "official_audit_matches": len(matches),
            "official_audit_spearman": rho, "frozen_breakout_cohort": cohort, "gates": gates,
            "partial_gate_passed": all(gates.values()),
            "promotion_warning": "Partial only: frozen breakout cohort, time/variant, sectional and collateral gates remain required."}


def breakout_cohort(store: RacingStore) -> dict[str, Any]:
    """Evaluate pre-race flagged improvers without selecting on future success.

    The database currently ends on 22 August 2026, so censoring is explicit and
    no horizon is treated as passed without enough subsequent calendar time.
    """
    last_day = store.connection.execute("SELECT max(race_date) FROM v2_clean_races").fetchone()[0]
    raw = store.connection.execute(
        """SELECT c.*,r.race_date,r.class_family,rr.official_handicap_rating,
                  rr.beaten_lengths,rr.finish_position
             FROM v2_achieved_run_candidates c JOIN v2_clean_races r USING(race_id)
             JOIN v2_clean_runner_results rr USING(race_id,runner_number)
            WHERE c.model_version=? AND rr.finish_position=1
              AND rr.beaten_lengths>=3 AND rr.official_handicap_rating IS NOT NULL
              AND rr.official_handicap_rating < c.race_strength
            ORDER BY r.race_date,c.race_id""", (MODEL_VERSION,)
    ).fetchall()
    selected = []
    for row in raw:
        detail = json.loads(row["detail_json"])
        if int(detail["breakout_flags"]["winner_prior_starts"]) > 8:
            continue
        selected.append(row)
    horizons: dict[str, Any] = {}
    from datetime import date
    final_date = date.fromisoformat(last_day)
    for days in (90, 180, 365):
        eligible = []
        for row in selected:
            start = date.fromisoformat(row["race_date"])
            if (final_date - start).days < days:
                continue
            end = start.fromordinal(start.toordinal() + days).isoformat()
            future = store.connection.execute(
                """SELECT p.performance_rating,r.class_family,c.finish_position
                     FROM v2_run_performances p JOIN v2_clean_races r USING(race_id)
                     JOIN v2_clean_runner_results c USING(race_id,runner_number)
                    WHERE p.model_version=? AND p.horse_key=? AND r.race_date>?
                      AND r.race_date<=? ORDER BY r.race_date""",
                (BASE_VERSION, row["horse_key"], row["race_date"], end),
            ).fetchall()
            if not future:
                continue
            target = max(float(x["performance_rating"]) for x in future)
            group_outcome = any(x["class_family"] in ("group_1", "group_2", "group_3", "listed")
                                and int(x["finish_position"] or 99) <= 3 for x in future)
            eligible.append({"target": target, "candidate": float(row["achieved_rating"]),
                             "official": float(row["official_handicap_rating"]),
                             "class_only": float(json.loads(row["detail_json"])["class_standard"]),
                             "predicted_breakout": float(row["achieved_rating"]) >= 100,
                             "group_outcome": group_outcome})
        def mae(field: str) -> float | None:
            return statistics.mean(abs(x[field] - x["target"]) for x in eligible) if eligible else None
        candidate_mae, official_mae, class_mae = mae("candidate"), mae("official"), mae("class_only")
        tp = sum(x["predicted_breakout"] and x["group_outcome"] for x in eligible)
        fp = sum(x["predicted_breakout"] and not x["group_outcome"] for x in eligible)
        fn = sum(not x["predicted_breakout"] and x["group_outcome"] for x in eligible)
        horizons[str(days)] = {"eligible": len(eligible), "censored_or_no_followup": len(selected)-len(eligible),
            "future_peak_mae": {"candidate": candidate_mae, "official": official_mae, "class_only": class_mae},
            "precision": tp/(tp+fp) if tp+fp else None, "recall": tp/(tp+fn) if tp+fn else None,
            "false_discovery_rate": fp/(tp+fp) if tp+fp else None,
            "candidate_beats_both_baselines": bool(len(eligible) >= 20 and candidate_mae is not None
                and candidate_mae < official_mae and candidate_mae < class_mae)}
    return {"selection": "winner margin >=3L; <=8 prior starts; official below candidate race strength; no future outcome used",
            "database_last_date": last_day, "selected": len(selected), "horizons": horizons,
            "limitations": "Age/sex stratification and 2026 untouched test remain mandatory before promotion."}


def run(store: RacingStore) -> dict[str, Any]:
    built = build(store)
    checked = audits(store)
    return {"build": built, "audits": checked,
            "decision": "SHADOW_CONTINUE" if checked["partial_gate_passed"] else "REVISE",
            "accepted_ratings_changed": False}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=ROOT / "data" / "racing_engine.sqlite")
    parser.add_argument("--output", type=Path, default=ROOT / "reports" / "v2_ratings" / "achieved_run_v2_1_recovery.json")
    args = parser.parse_args()
    store = RacingStore(args.database)
    try:
        report = run(store)
    finally:
        store.close()
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
