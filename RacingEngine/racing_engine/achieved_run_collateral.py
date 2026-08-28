"""V2.4 point-in-time opposition-strength achieved-run candidate.

This shadow family replaces the base model's unconditional use of current-day
official ratings for the first four finishers with a reliability-weighted
pre-race anchor.  Official ratings and strictly prior V2 performances are
combined according to history depth and dispersion.  The resulting opposition
level is applied only at a coefficient selected on pre-2025 dominant winners;
the three named audit horses are excluded from fitting.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

from .achieved_run_calibrated import MODEL_VERSION as V23_VERSION, ROOT, build as build_v23
from .achieved_run_recovery import BASE_VERSION, audits
from .storage import RacingStore
from .v2_ratings import pounds_per_length

MODEL_VERSION = "achieved-run-v2.4-opposition-pit-shadow"
TRAINING_CUTOFF = "2025-01-01"
HORIZON_DAYS = 90
GRID = tuple(value / 20 for value in range(21))
NAMED_AUDITS = {"naturalfling", "gringotts", "shezaalibi"}


def prior_form_anchor(values: list[float], official: float | None) -> dict[str, Any]:
    """Return a bounded pre-race anchor and explicit evidence reliability."""
    recent = values[-3:]
    if not recent:
        return {"anchor": official, "reliability": 0.0, "runs": 0,
                "prior_median": None, "dispersion": None}
    centre = statistics.median(recent)
    dispersion = statistics.median(abs(value - centre) for value in recent)
    depth = 1.0 - math.exp(-len(recent) / 2.0)
    consistency = max(0.0, 1.0 - dispersion / 15.0)
    reliability = depth * consistency
    anchor = centre if official is None else official + reliability * (centre - official)
    return {"anchor": anchor, "reliability": reliability, "runs": len(recent),
            "prior_median": centre, "dispersion": dispersion}


def opposition_evidence(store: RacingStore) -> dict[str, dict[str, Any]]:
    histories: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for row in store.connection.execute(
        """SELECT p.horse_key,r.race_date,p.performance_rating FROM v2_run_performances p
             JOIN v2_clean_races r USING(race_id) WHERE p.model_version=?
             ORDER BY r.race_date,r.race_id""", (BASE_VERSION,)
    ):
        histories[row["horse_key"]].append((row["race_date"], float(row["performance_rating"])))
    evidence: dict[str, dict[str, Any]] = {}
    for race in store.connection.execute("SELECT * FROM v2_clean_races ORDER BY race_date,race_id"):
        principals = store.connection.execute(
            """SELECT * FROM v2_clean_runner_results WHERE race_id=? AND result_status='finished'
                 AND finish_position BETWEEN 1 AND 4 ORDER BY finish_position""", (race["race_id"],)
        ).fetchall()
        if not principals:
            continue
        ppl = pounds_per_length(int(race["distance_metres"] or 1600))
        winner_weight = float(principals[0]["weight_carried_kg"] or 58.0)
        anchors = []
        detail = []
        for runner in principals:
            prior = [rating for day, rating in histories[runner["horse_key"]] if day < race["race_date"]]
            official = (float(runner["official_handicap_rating"])
                        if runner["official_handicap_rating"] is not None else None)
            item = prior_form_anchor(prior, official)
            if item["anchor"] is None:
                continue
            margin = 0.0 if int(runner["finish_position"]) == 1 else float(runner["beaten_lengths"] or 0.0)
            weight_delta = (winner_weight - float(runner["weight_carried_kg"] or winner_weight)) * 2.20462262
            adjusted = float(item["anchor"]) + margin * ppl + weight_delta
            anchors.append(adjusted)
            detail.append({"horse_key": runner["horse_key"], "finish_position": runner["finish_position"],
                           "official": official, "adjusted_anchor": adjusted, **item})
        evidence[race["race_id"]] = {
            "opposition_anchor": statistics.median(anchors) if anchors else None,
            "principal_coverage": len(anchors) / len(principals), "principals": detail,
        }
    return evidence


def fit_coefficient(store: RacingStore, evidence: dict[str, dict[str, Any]]) -> dict[str, Any]:
    samples = []
    for row in store.connection.execute(
        """SELECT a.*,r.race_date,c.finish_position,c.beaten_lengths FROM v2_achieved_run_candidates a
             JOIN v2_clean_races r USING(race_id)
             JOIN v2_clean_runner_results c USING(race_id,runner_number)
            WHERE a.model_version=? AND r.race_date<? AND c.finish_position=1
              AND c.beaten_lengths>=3 ORDER BY r.race_date""", (V23_VERSION, TRAINING_CUTOFF)
    ):
        if row["horse_key"] in NAMED_AUDITS:
            continue
        item = evidence.get(row["race_id"], {})
        anchor = item.get("opposition_anchor")
        if anchor is None:
            continue
        start = date.fromisoformat(row["race_date"])
        end = date.fromordinal(start.toordinal() + HORIZON_DAYS).isoformat()
        future = [float(x[0]) for x in store.connection.execute(
            """SELECT p.performance_rating FROM v2_run_performances p JOIN v2_clean_races r USING(race_id)
                WHERE p.model_version=? AND p.horse_key=? AND r.race_date>? AND r.race_date<=?""",
            (BASE_VERSION, row["horse_key"], row["race_date"], end))]
        if future:
            samples.append((float(row["achieved_rating"]), float(anchor) - float(row["race_strength"]), max(future)))
    trials = []
    for coefficient in GRID:
        mae = statistics.mean(abs(base + coefficient * delta - target) for base, delta, target in samples)
        trials.append({"coefficient": coefficient, "training_future_peak_mae": mae})
    selected = min(trials, key=lambda x: (x["training_future_peak_mae"], x["coefficient"]))
    return {"training_cutoff_exclusive": TRAINING_CUTOFF, "horizon_days": HORIZON_DAYS,
            "samples": len(samples), "named_audit_horses_excluded": True,
            "selected_coefficient": selected["coefficient"], "trials": trials}


def build(store: RacingStore) -> dict[str, Any]:
    parent = build_v23(store)
    evidence = opposition_evidence(store)
    fit = fit_coefficient(store, evidence)
    coefficient = float(fit["selected_coefficient"])
    store.connection.execute("DELETE FROM v2_achieved_run_candidates WHERE model_version=?", (MODEL_VERSION,))
    changed = 0
    rows = store.connection.execute(
        "SELECT * FROM v2_achieved_run_candidates WHERE model_version=?", (V23_VERSION,)).fetchall()
    for row in rows:
        item = evidence.get(row["race_id"], {})
        anchor = item.get("opposition_anchor")
        delta = coefficient * (float(anchor) - float(row["race_strength"])) if anchor is not None else 0.0
        detail = {**json.loads(row["detail_json"]), "candidate_version": MODEL_VERSION,
                  "opposition_evidence": item, "opposition_fit": {k: v for k, v in fit.items() if k != "trials"},
                  "opposition_revision_coefficient": coefficient,
                  "opposition_revision_component": delta, "strictly_prior_evidence": True}
        store.connection.execute(
            """INSERT INTO v2_achieved_run_candidates VALUES
               (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (MODEL_VERSION,row["race_id"],row["runner_number"],row["horse_key"],row["horse_name"],
             float(row["achieved_rating"])+delta,row["base_rating"],float(row["race_strength"])+delta,
             row["base_race_strength"],row["winner_margin_component"],row["beaten_margin_component"],
             row["weight_component"],row["time_variant_component"],row["sectional_component"],delta,
             row["confidence"],json.dumps(detail,sort_keys=True)))
        changed += int(abs(delta) > 1e-9)
    store.connection.commit()
    return {"model_version": MODEL_VERSION, "parent": parent, "fit": fit,
            "performances": len(rows), "revised_rows": changed}


def run(store: RacingStore) -> dict[str, Any]:
    built = build(store)
    checked = audits(store, MODEL_VERSION)
    return {"build": built, "audits": checked,
            "decision": "SHADOW_CONTINUE" if checked["partial_gate_passed"] else "REJECT_OR_REVISE",
            "accepted_ratings_changed": False}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=ROOT / "data" / "racing_engine.sqlite")
    parser.add_argument("--output", type=Path, default=ROOT / "reports" / "v2_ratings" / "achieved_run_v2_4_opposition.json")
    args = parser.parse_args(); store = RacingStore(args.database)
    try: report = run(store)
    finally: store.close()
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__": main()
