"""V2.6 separated achieved-run figure.

Completed-race achievement is built from a reliability-weighted opposition
anchor, the registered historical class standard, and observed margins. It is
not fitted to future peaks; repeatability and mean reversion belong to the
downstream Horse Ability layer.
"""
from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter
from pathlib import Path
from typing import Any

from .achieved_run_collateral import ROOT, opposition_evidence
from .achieved_run_recovery import BASE_VERSION, audits, race_weight_policy, weight_component
from .storage import RacingStore
from .v2_ratings import pounds_per_length

MODEL_VERSION = "achieved-run-v2.6-separated-shadow"
MAX_WIN_MARGIN_POINTS = 12.0


def reliable_race_level(class_standard: float, opposition_anchor: float | None,
                        principal_reliabilities: list[float], coverage: float) -> tuple[float, float]:
    """Blend opposition with class prior by evidence quality, not row presence."""
    if opposition_anchor is None or not principal_reliabilities:
        return class_standard, 0.0
    reliability = statistics.mean(principal_reliabilities) * max(0.0, min(1.0, coverage))
    reliability = max(0.0, min(0.80, reliability))
    return (reliability * opposition_anchor + (1.0 - reliability) * class_standard,
            reliability)


def achieved_margin(finish_position: int, margin: float, ppl: float) -> float:
    if finish_position == 1:
        return min(MAX_WIN_MARGIN_POINTS, max(0.0, margin * ppl))
    return -max(0.0, margin) * ppl


def build(store: RacingStore) -> dict[str, Any]:
    # V2.4's evidence builder is independent of V2.4 candidate rows.
    evidence = opposition_evidence(store)
    store.connection.execute("DELETE FROM v2_achieved_run_candidates WHERE model_version=?", (MODEL_VERSION,))
    counts = Counter()
    for race in store.connection.execute("SELECT * FROM v2_clean_races ORDER BY race_date,race_id").fetchall():
        runners = store.connection.execute(
            """SELECT c.*,p.performance_rating,p.race_strength base_strength,p.class_standard,
                      p.confidence FROM v2_clean_runner_results c JOIN v2_run_performances p
                      USING(race_id,runner_number) WHERE c.race_id=? AND c.result_status='finished'
                      AND c.finish_position IS NOT NULL AND p.model_version=?
                 ORDER BY c.finish_position,c.runner_number""", (race["race_id"],BASE_VERSION)).fetchall()
        winner = next((row for row in runners if int(row["finish_position"]) == 1), None)
        if winner is None: continue
        winner_prior_starts = int(store.connection.execute(
            """SELECT count(*) FROM v2_run_performances p JOIN v2_clean_races r USING(race_id)
                WHERE p.model_version=? AND p.horse_key=? AND r.race_date<?""",
            (BASE_VERSION,winner["horse_key"],race["race_date"])).fetchone()[0])
        item = evidence.get(race["race_id"], {})
        reliabilities = [float(x["reliability"]) for x in item.get("principals", [])]
        standard = float(winner["class_standard"])
        strength, strength_reliability = reliable_race_level(
            standard, item.get("opposition_anchor"), reliabilities,
            float(item.get("principal_coverage") or 0.0))
        ppl = pounds_per_length(int(race["distance_metres"] or 1600))
        policy = race_weight_policy(race["race_class"])
        for row in runners:
            position = int(row["finish_position"])
            margin = float(row["beaten_lengths"] or 0.0)
            margin_component = achieved_margin(position, margin, ppl)
            weight = weight_component(policy, row["weight_carried_kg"], winner["weight_carried_kg"])
            achieved = strength + margin_component + weight
            detail = {"candidate_version": MODEL_VERSION, "base_model_version": BASE_VERSION,
                      "layer": "completed_run_achievement", "class_standard": standard,
                      "opposition_evidence": item, "opposition_reliability": strength_reliability,
                      "race_weight_policy": policy, "pounds_per_length": ppl,
                      "winner_margin_cap_points": MAX_WIN_MARGIN_POINTS,
                      "breakout_flags": {"winning_margin": float(winner["beaten_lengths"] or 0.0),
                                          "winner_prior": winner["official_handicap_rating"],
                                          "winner_prior_starts": winner_prior_starts},
                      "future_peak_not_a_fit_target": True,
                      "repeatability_deferred_to_horse_ability": True,
                      "time_variant_status": "not_promoted_zero",
                      "sectional_status": "not_promoted_zero", "research_only": True}
            store.connection.execute(
                """INSERT INTO v2_achieved_run_candidates VALUES
                   (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (MODEL_VERSION,race["race_id"],row["runner_number"],row["horse_key"],row["horse_name"],
                 achieved,row["performance_rating"],strength,row["base_strength"],
                 margin_component if position == 1 else 0.0,
                 margin_component if position != 1 else 0.0,weight,0.0,0.0,0.0,row["confidence"],
                 json.dumps(detail,sort_keys=True)))
            counts["performances"] += 1
        counts["races"] += 1
    store.connection.commit()
    return {"model_version": MODEL_VERSION, **dict(counts)}


def layer_audits(store: RacingStore) -> dict[str, Any]:
    rows = store.connection.execute(
        """SELECT a.horse_name,r.race_date,a.achieved_rating,a.race_strength,
                  a.winner_margin_component,a.beaten_margin_component,a.weight_component,a.detail_json
             FROM v2_achieved_run_candidates a JOIN v2_clean_races r USING(race_id)
            WHERE a.model_version=? AND ((a.horse_key='naturalfling' AND r.race_date='2026-08-15')
              OR (a.horse_key='ninja' AND r.race_date='2026-08-08')
              OR (a.horse_key IN ('shezaalibi','gringotts') AND r.race_date='2026-08-22'))
            ORDER BY r.race_date,a.achieved_rating DESC""", (MODEL_VERSION,)).fetchall()
    output = []
    for row in rows:
        detail=json.loads(row["detail_json"])
        output.append({k:row[k] for k in row.keys() if k != "detail_json"} |
                      {"opposition_reliability":detail["opposition_reliability"],
                       "class_standard":detail["class_standard"]})
    return {"named": output,
            "target_boundary": "Achieved-run gates describe the completed race; future-peak MAE is diagnostic only until Horse Ability."}


def run(store: RacingStore) -> dict[str, Any]:
    built=build(store);checked=audits(store,MODEL_VERSION);layers=layer_audits(store)
    achieved_gates={key:value for key,value in checked["gates"].items()
                    if key != "frozen_breakout_cohort_90d_mae"}
    return {"build":built,"audits":checked,"layer_audits":layers,
            "achieved_run_gates":achieved_gates,
            "achieved_run_gate_passed":all(achieved_gates.values()),
            "horse_ability_future_peak_gate_passed":checked["gates"]["frozen_breakout_cohort_90d_mae"],
            "decision":"SHADOW_READY_FOR_LAYER_REVIEW" if all(achieved_gates.values()) else "REVISE",
            "accepted_ratings_changed":False}


def main()->None:
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--database",type=Path,default=ROOT/"data"/"racing_engine.sqlite")
    p.add_argument("--output",type=Path,default=ROOT/"reports"/"v2_ratings"/"achieved_run_v2_6_separated.json")
    a=p.parse_args();s=RacingStore(a.database)
    try:r=run(s)
    finally:s.close()
    rendered=json.dumps(r,indent=2,sort_keys=True)+"\n";a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(rendered,encoding="utf-8");print(rendered,end="")


if __name__=="__main__":main()
