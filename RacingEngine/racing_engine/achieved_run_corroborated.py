"""V2.2 achieved-run candidate requiring independent breakout corroboration."""
from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter
from pathlib import Path
from typing import Any

from .achieved_run_recovery import (
    BASE_VERSION, MODEL_VERSION as V21_VERSION, ROOT, audits, build as build_v21,
)
from .storage import RacingStore

MODEL_VERSION = "achieved-run-v2.2-corroborated-shadow"
ENERGY_VERSION = "energy-sectionals-v2.5-hierarchical-shadow"
TRAINING_CUTOFF = "2025-01-01"
ENERGY_QUANTILE = 0.75
CLOCK_MAD_THRESHOLD = 0.50


def quantile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(len(ordered) * fraction))]


def fit_training_thresholds(store: RacingStore) -> dict[str, Any]:
    energy = [float(row[0]) for row in store.connection.execute(
        """SELECT e.compensation_signal FROM v2_runner_energy_sectionals e
             JOIN v2_clean_runner_results c USING(race_id,runner_number)
             JOIN v2_clean_races r USING(race_id)
            WHERE e.version=? AND c.finish_position=1 AND r.race_date<?
              AND e.horse_key NOT IN ('naturalfling','gringotts','shezaalibi')""",
        (ENERGY_VERSION, TRAINING_CUTOFF),
    )]
    return {"training_cutoff_exclusive": TRAINING_CUTOFF,
            "named_audit_horses_excluded": True,
            "energy_winner_rows": len(energy),
            "energy_compensation_threshold": quantile(energy, ENERGY_QUANTILE),
            "energy_quantile": ENERGY_QUANTILE,
            "clock_fast_threshold_mad": CLOCK_MAD_THRESHOLD}


def _clock_support(store: RacingStore, race: Any) -> dict[str, Any]:
    if race["clock_status"] != "valid" or race["official_time_seconds"] is None:
        return {"available": False, "supported": False, "reason": "no_valid_clock"}
    history = [float(row[0]) for row in store.connection.execute(
        """SELECT official_time_seconds FROM v2_clean_races
            WHERE source=? AND track_slug=? AND distance_metres=? AND race_date<?
              AND clock_status='valid' AND official_time_seconds IS NOT NULL""",
        (race["source"], race["track_slug"], race["distance_metres"], race["race_date"]),
    )]
    if len(history) < 20:
        return {"available": False, "supported": False, "reason": "fewer_than_20_prior_track_distance_clocks"}
    centre = statistics.median(history)
    mad = statistics.median(abs(value - centre) for value in history)
    meeting_residuals = []
    for other in store.connection.execute(
        """SELECT * FROM v2_clean_races WHERE source=? AND track_slug=? AND race_date=?
              AND race_id<>? AND clock_status='valid' AND official_time_seconds IS NOT NULL""",
        (race["source"], race["track_slug"], race["race_date"], race["race_id"]),
    ):
        prior = [float(row[0]) for row in store.connection.execute(
            """SELECT official_time_seconds FROM v2_clean_races
                WHERE source=? AND track_slug=? AND distance_metres=? AND race_date<?
                  AND clock_status='valid' AND official_time_seconds IS NOT NULL""",
            (other["source"], other["track_slug"], other["distance_metres"], other["race_date"]),
        )]
        if len(prior) >= 20:
            meeting_residuals.append(float(other["official_time_seconds"]) - statistics.median(prior))
    meeting_variant = statistics.median(meeting_residuals) if len(meeting_residuals) >= 3 else 0.0
    adjusted_residual = float(race["official_time_seconds"]) - centre - meeting_variant
    standardised = -adjusted_residual / max(0.10, mad)
    return {"available": True, "supported": standardised >= CLOCK_MAD_THRESHOLD,
            "prior_clocks": len(history), "track_distance_median_seconds": centre,
            "track_distance_mad_seconds": mad, "other_meeting_races": len(meeting_residuals),
            "meeting_variant_seconds": meeting_variant,
            "adjusted_fast_mad": standardised}


def _energy_support(store: RacingStore, race_id: str, runner_number: int, threshold: float | None) -> dict[str, Any]:
    row = store.connection.execute(
        """SELECT compensation_signal,achievement_signal,confidence FROM v2_runner_energy_sectionals
            WHERE version=? AND race_id=? AND runner_number=?""",
        (ENERGY_VERSION, race_id, runner_number),
    ).fetchone()
    if row is None or threshold is None:
        return {"available": False, "supported": False}
    value = float(row["compensation_signal"])
    return {"available": True, "supported": value >= threshold,
            "compensation_signal": value, "achievement_signal": float(row["achievement_signal"]),
            "confidence": float(row["confidence"]), "training_threshold": threshold}


def build(store: RacingStore) -> dict[str, Any]:
    build_v21(store)
    thresholds = fit_training_thresholds(store)
    store.connection.execute("DELETE FROM v2_achieved_run_candidates WHERE model_version=?", (MODEL_VERSION,))
    counts = Counter()
    for race in store.connection.execute("SELECT * FROM v2_clean_races ORDER BY race_date,race_id").fetchall():
        rows = store.connection.execute(
            """SELECT a.*,c.finish_position,c.beaten_lengths FROM v2_achieved_run_candidates a
                 JOIN v2_clean_runner_results c USING(race_id,runner_number)
                WHERE a.model_version=? AND a.race_id=? ORDER BY c.finish_position""",
            (V21_VERSION, race["race_id"]),
        ).fetchall()
        if not rows:
            continue
        winner = next(row for row in rows if int(row["finish_position"]) == 1)
        prior_detail = json.loads(winner["detail_json"])
        clock = _clock_support(store, race)
        energy = _energy_support(store, race["race_id"], int(winner["runner_number"]),
                                 thresholds["energy_compensation_threshold"])
        corroborated = bool(clock["supported"] or energy["supported"])
        breakout = bool(prior_detail["breakout_anchor_relief"] and corroborated)
        collateral = prior_detail["collateral_anchor"]
        original_weight = float(prior_detail["original_collateral_weight"])
        standard = float(prior_detail["class_standard"])
        candidate_weight = float(prior_detail["candidate_collateral_weight"]) if breakout else original_weight
        strength = (candidate_weight * float(collateral) + (1-candidate_weight)*standard
                    if collateral is not None else standard)
        dominant = float(winner["beaten_lengths"] or 0.0) >= 3.0
        for row in rows:
            margin = float(row["winner_margin_component"]) if corroborated and dominant else 0.0
            achieved = strength + margin + float(row["beaten_margin_component"]) + float(row["weight_component"])
            detail = {**json.loads(row["detail_json"]),
                      "candidate_version": MODEL_VERSION,
                      "breakout_anchor_relief": breakout,
                      "candidate_collateral_weight": candidate_weight,
                      "independent_corroboration": {"clock": clock, "energy": energy,
                                                     "supported": corroborated},
                      "training_thresholds": thresholds,
                      "winner_margin_requires_corroboration": True}
            store.connection.execute(
                """INSERT INTO v2_achieved_run_candidates VALUES
                   (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (MODEL_VERSION,row["race_id"],row["runner_number"],row["horse_key"],row["horse_name"],
                 achieved,row["base_rating"],strength,row["base_race_strength"],margin,
                 row["beaten_margin_component"],row["weight_component"],0.0,0.0,0.0,
                 row["confidence"],json.dumps(detail,sort_keys=True)))
            counts["performances"] += 1
        counts["races"] += 1
        counts["corroborated_dominant_winners"] += int(corroborated and dominant)
        counts["breakout_anchor_relief_races"] += int(breakout)
    store.connection.commit()
    return {"model_version": MODEL_VERSION, "thresholds": thresholds, **dict(counts)}


def run(store: RacingStore) -> dict[str, Any]:
    built = build(store)
    checked = audits(store, MODEL_VERSION)
    return {"build": built, "audits": checked,
            "decision": "SHADOW_CONTINUE" if checked["partial_gate_passed"] else "REVISE_OR_REJECT",
            "accepted_ratings_changed": False}


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database",type=Path,default=ROOT/"data"/"racing_engine.sqlite")
    parser.add_argument("--output",type=Path,default=ROOT/"reports"/"v2_ratings"/"achieved_run_v2_2_corroborated.json")
    args=parser.parse_args();store=RacingStore(args.database)
    try: report=run(store)
    finally: store.close()
    rendered=json.dumps(report,indent=2,sort_keys=True)+"\n";args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(rendered,encoding="utf-8");print(rendered,end="")


if __name__=="__main__": main()
