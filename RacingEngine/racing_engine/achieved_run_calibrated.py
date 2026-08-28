"""V2.3 training-calibrated partial update for uncorroborated breakouts."""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

from .achieved_run_corroborated import MODEL_VERSION as V22_VERSION, ROOT, build as build_v22
from .achieved_run_recovery import BASE_VERSION, MODEL_VERSION as V21_VERSION, audits
from .storage import RacingStore

MODEL_VERSION = "achieved-run-v2.3-calibrated-shadow"
TRAINING_CUTOFF = "2025-01-01"
HORIZON_DAYS = 90
GRID = tuple(value / 20 for value in range(21))


def fit_partial_update(store: RacingStore) -> dict[str, Any]:
    histories: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for row in store.connection.execute(
        """SELECT p.horse_key,r.race_date,p.performance_rating FROM v2_run_performances p
             JOIN v2_clean_races r USING(race_id) WHERE p.model_version=? ORDER BY r.race_date""",
        (BASE_VERSION,),
    ):
        histories[row["horse_key"]].append((row["race_date"], float(row["performance_rating"])))
    candidates = store.connection.execute(
        """SELECT a.horse_key,r.race_date,a.achieved_rating v21,b.achieved_rating v22
             FROM v2_achieved_run_candidates a JOIN v2_achieved_run_candidates b USING(race_id,runner_number)
             JOIN v2_clean_races r USING(race_id)
            WHERE a.model_version=? AND b.model_version=? AND r.race_date<?
              AND abs(a.achieved_rating-b.achieved_rating)>1e-9
              AND a.horse_key NOT IN ('naturalfling','gringotts','shezaalibi')""",
        (V21_VERSION, V22_VERSION, TRAINING_CUTOFF),
    ).fetchall()
    samples = []
    for row in candidates:
        start = date.fromisoformat(row["race_date"])
        future = [rating for day, rating in histories[row["horse_key"]]
                  if 0 < (date.fromisoformat(day)-start).days <= HORIZON_DAYS]
        if future:
            samples.append((float(row["v22"]), float(row["v21"]), max(future)))
    trials = []
    for coefficient in GRID:
        mae = sum(abs(base + coefficient*(full-base) - target)
                  for base,full,target in samples) / len(samples) if samples else None
        trials.append({"coefficient": coefficient, "training_future_peak_mae": mae})
    selected = min(trials, key=lambda row: (row["training_future_peak_mae"], row["coefficient"])) if samples else None
    return {"training_cutoff_exclusive": TRAINING_CUTOFF, "horizon_days": HORIZON_DAYS,
            "named_audit_horses_excluded": True, "samples": len(samples),
            "selected_coefficient": selected["coefficient"] if selected else 0.0,
            "trials": trials}


def build(store: RacingStore) -> dict[str, Any]:
    parent = build_v22(store)
    fit = fit_partial_update(store)
    coefficient = float(fit["selected_coefficient"])
    store.connection.execute("DELETE FROM v2_achieved_run_candidates WHERE model_version=?", (MODEL_VERSION,))
    rows = store.connection.execute(
        """SELECT b.*,a.achieved_rating full_rating,a.race_strength full_strength,
                  a.winner_margin_component full_margin
             FROM v2_achieved_run_candidates b JOIN v2_achieved_run_candidates a USING(race_id,runner_number)
            WHERE b.model_version=? AND a.model_version=?""", (V22_VERSION,V21_VERSION)
    ).fetchall()
    changed = 0
    for row in rows:
        delta = float(row["full_rating"])-float(row["achieved_rating"])
        partial = coefficient*delta
        fit_summary = {"training_cutoff_exclusive": fit["training_cutoff_exclusive"],
                       "horizon_days": fit["horizon_days"], "samples": fit["samples"],
                       "selected_coefficient": coefficient,
                       "named_audit_horses_excluded": True}
        detail = {**json.loads(row["detail_json"]), "candidate_version": MODEL_VERSION,
                  "uncorroborated_partial_update": partial,
                  "partial_update_coefficient": coefficient,
                  "partial_update_fit": fit_summary,
                  "named_audits_excluded_from_fit": True}
        strength_delta = coefficient*(float(row["full_strength"])-float(row["race_strength"]))
        margin_delta = coefficient*(float(row["full_margin"])-float(row["winner_margin_component"]))
        store.connection.execute(
            """INSERT INTO v2_achieved_run_candidates VALUES
               (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (MODEL_VERSION,row["race_id"],row["runner_number"],row["horse_key"],row["horse_name"],
             float(row["achieved_rating"])+partial,row["base_rating"],float(row["race_strength"])+strength_delta,
             row["base_race_strength"],float(row["winner_margin_component"])+margin_delta,
             row["beaten_margin_component"],row["weight_component"],row["time_variant_component"],
             row["sectional_component"],row["collateral_revision_component"],row["confidence"],
             json.dumps(detail,sort_keys=True)))
        changed += int(abs(partial)>1e-9)
    store.connection.commit()
    return {"model_version":MODEL_VERSION,"parent":parent,"fit":fit,
            "performances":len(rows),"partially_updated_rows":changed}


def run(store:RacingStore)->dict[str,Any]:
    built=build(store);checked=audits(store,MODEL_VERSION)
    return {"build":built,"audits":checked,
            "decision":"SHADOW_CONTINUE" if checked["partial_gate_passed"] else "REJECT_OR_REVISE",
            "accepted_ratings_changed":False}


def main()->None:
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--database",type=Path,default=ROOT/"data"/"racing_engine.sqlite")
    p.add_argument("--output",type=Path,default=ROOT/"reports"/"v2_ratings"/"achieved_run_v2_3_calibrated.json");a=p.parse_args();s=RacingStore(a.database)
    try:r=run(s)
    finally:s.close()
    rendered=json.dumps(r,indent=2,sort_keys=True)+"\n";a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(rendered);print(rendered,end="")


if __name__=="__main__":main()
