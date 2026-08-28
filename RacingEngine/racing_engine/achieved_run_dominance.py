"""V2.5 achieved-run candidate using point-in-time dominance reliability."""
from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

from .achieved_run_collateral import MODEL_VERSION as V24_VERSION, ROOT, build as build_v24
from .achieved_run_recovery import MODEL_VERSION as V21_VERSION, audits
from .storage import RacingStore

MODEL_VERSION = "achieved-run-v2.5-dominance-pit-shadow"
TRAINING_CUTOFF = "2025-01-01"
HORIZON_DAYS = 90
MIN_PRIOR_RACES = 20
GRID = tuple(value / 20 for value in range(21))
NAMED_AUDITS = {"naturalfling", "ninja", "gringotts", "shezaalibi"}


def distance_band(distance: int) -> str:
    if distance < 1300: return "sprint"
    if distance < 1800: return "mile"
    if distance < 2400: return "middle"
    return "staying"


def empirical_dominance(margin: float, prior_margins: list[float]) -> dict[str, Any]:
    """Score positive-margin rarity without looking beyond the race date."""
    if len(prior_margins) < MIN_PRIOR_RACES:
        return {"available": False, "reliability": 0.0, "prior_races": len(prior_margins)}
    ordered = sorted(prior_margins)
    percentile = sum(value < margin for value in ordered) / len(ordered)
    # No authority below the prior 75th percentile; smoothly reaches full
    # authority at the top of the historical distribution.
    reliability = max(0.0, min(1.0, (percentile - 0.75) / 0.25))
    return {"available": True, "reliability": reliability, "prior_races": len(ordered),
            "margin_lengths": margin, "prior_median": statistics.median(ordered),
            "percentile": percentile}


def dominance_evidence(store: RacingStore) -> dict[str, dict[str, Any]]:
    histories: dict[tuple[str, str], list[float]] = defaultdict(list)
    output: dict[str, dict[str, Any]] = {}
    races = store.connection.execute("SELECT * FROM v2_clean_races ORDER BY race_date,race_id").fetchall()
    for race in races:
        winner = store.connection.execute(
            """SELECT beaten_lengths FROM v2_clean_runner_results WHERE race_id=?
                AND result_status='finished' AND finish_position=1""", (race["race_id"],)).fetchone()
        if winner is None:
            continue
        key = (race["class_family"], distance_band(int(race["distance_metres"] or 1600)))
        margin = float(winner["beaten_lengths"] or 0.0)
        output[race["race_id"]] = {"class_family": key[0], "distance_band": key[1],
                                   **empirical_dominance(margin, histories[key])}
        histories[key].append(margin)
    return output


def fit_coefficient(store: RacingStore, evidence: dict[str, dict[str, Any]]) -> dict[str, Any]:
    samples = []
    rows = store.connection.execute(
        """SELECT p.race_id,p.horse_key,p.achieved_rating parent_rating,
                  p.collateral_revision_component,
                  f.achieved_rating full_rating,r.race_date,c.finish_position
             FROM v2_achieved_run_candidates p JOIN v2_achieved_run_candidates f USING(race_id,runner_number)
             JOIN v2_clean_races r USING(race_id)
             JOIN v2_clean_runner_results c USING(race_id,runner_number)
            WHERE p.model_version=? AND f.model_version=? AND r.race_date<?
              AND c.finish_position=1""", (V24_VERSION, V21_VERSION, TRAINING_CUTOFF)).fetchall()
    for row in rows:
        signal = evidence.get(row["race_id"], {})
        reliability = float(signal.get("reliability") or 0.0)
        if reliability <= 0 or row["horse_key"] in NAMED_AUDITS:
            continue
        start = date.fromisoformat(row["race_date"])
        end = date.fromordinal(start.toordinal() + HORIZON_DAYS).isoformat()
        future = [float(x[0]) for x in store.connection.execute(
            """SELECT p.performance_rating FROM v2_run_performances p JOIN v2_clean_races r USING(race_id)
                WHERE p.model_version='form-first-v2.0' AND p.horse_key=?
                  AND r.race_date>? AND r.race_date<=?""", (row["horse_key"], row["race_date"], end))]
        if future:
            parent_before_opposition = (float(row["parent_rating"])
                                        - float(row["collateral_revision_component"]))
            delta = reliability * (float(row["full_rating"]) - parent_before_opposition)
            samples.append((float(row["parent_rating"]), delta, max(future)))
    trials = []
    for coefficient in GRID:
        mae = statistics.mean(abs(base + coefficient * delta - target) for base,delta,target in samples)
        trials.append({"coefficient": coefficient, "training_future_peak_mae": mae})
    selected = min(trials, key=lambda row: (row["training_future_peak_mae"], row["coefficient"]))
    return {"training_cutoff_exclusive": TRAINING_CUTOFF, "horizon_days": HORIZON_DAYS,
            "samples": len(samples), "selected_coefficient": selected["coefficient"],
            "named_audit_horses_excluded": sorted(NAMED_AUDITS), "trials": trials}


def build(store: RacingStore) -> dict[str, Any]:
    parent = build_v24(store)
    evidence = dominance_evidence(store)
    fit = fit_coefficient(store, evidence)
    coefficient = float(fit["selected_coefficient"])
    store.connection.execute("DELETE FROM v2_achieved_run_candidates WHERE model_version=?", (MODEL_VERSION,))
    rows = store.connection.execute(
        """SELECT p.*,f.achieved_rating full_rating,f.race_strength full_strength,
                  f.winner_margin_component full_margin
             FROM v2_achieved_run_candidates p JOIN v2_achieved_run_candidates f USING(race_id,runner_number)
            WHERE p.model_version=? AND f.model_version=?""", (V24_VERSION,V21_VERSION)).fetchall()
    changed = 0
    for row in rows:
        signal = evidence.get(row["race_id"], {})
        reliability = float(signal.get("reliability") or 0.0)
        # Dominance belongs only to the winner. Other runners retain the V2.4
        # opposition revision and their existing beaten-margin interpretation.
        full_delta = float(row["full_rating"]) - (float(row["achieved_rating"])
                     - float(row["collateral_revision_component"]))
        delta = coefficient * reliability * full_delta if float(row["winner_margin_component"]) > 0 else 0.0
        detail = {**json.loads(row["detail_json"]), "candidate_version": MODEL_VERSION,
                  "dominance_evidence": signal, "dominance_coefficient": coefficient,
                  "dominance_update_component": delta,
                  "dominance_fit": {k:v for k,v in fit.items() if k != "trials"},
                  "named_audits_excluded_from_fit": True}
        store.connection.execute(
            """INSERT INTO v2_achieved_run_candidates VALUES
               (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (MODEL_VERSION,row["race_id"],row["runner_number"],row["horse_key"],row["horse_name"],
             float(row["achieved_rating"])+delta,row["base_rating"],float(row["race_strength"])+delta,
             row["base_race_strength"],float(row["winner_margin_component"])+delta,
             row["beaten_margin_component"],row["weight_component"],row["time_variant_component"],
             row["sectional_component"],row["collateral_revision_component"],row["confidence"],
             json.dumps(detail,sort_keys=True)))
        changed += int(abs(delta) > 1e-9)
    store.connection.commit()
    return {"model_version": MODEL_VERSION, "parent": parent, "fit": fit,
            "performances": len(rows), "dominance_updated_winners": changed}


def named_audit(store: RacingStore) -> dict[str, Any]:
    rows = store.connection.execute(
        """SELECT a.horse_name,r.race_date,a.achieved_rating,a.winner_margin_component,
                  a.collateral_revision_component,a.detail_json FROM v2_achieved_run_candidates a
             JOIN v2_clean_races r USING(race_id) WHERE a.model_version=?
              AND ((a.horse_key='naturalfling' AND r.race_date='2026-08-15')
                OR (a.horse_key='ninja' AND r.race_date='2026-08-08'))""", (MODEL_VERSION,)).fetchall()
    return {row["horse_name"]: {**{k:row[k] for k in row.keys() if k != "detail_json"},
            "dominance_evidence": json.loads(row["detail_json"])["dominance_evidence"]} for row in rows}


def run(store: RacingStore) -> dict[str, Any]:
    built = build(store); checked = audits(store, MODEL_VERSION); named = named_audit(store)
    return {"build": built, "audits": checked, "named_winner_audit": named,
            "decision": "SHADOW_CONTINUE" if checked["partial_gate_passed"] else "REJECT_OR_REVISE",
            "accepted_ratings_changed": False}


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database",type=Path,default=ROOT/"data"/"racing_engine.sqlite")
    parser.add_argument("--output",type=Path,default=ROOT/"reports"/"v2_ratings"/"achieved_run_v2_5_dominance.json")
    args=parser.parse_args();store=RacingStore(args.database)
    try: report=run(store)
    finally: store.close()
    rendered=json.dumps(report,indent=2,sort_keys=True)+"\n";args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(rendered,encoding="utf-8");print(rendered,end="")


if __name__ == "__main__": main()
