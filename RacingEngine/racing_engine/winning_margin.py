"""Research candidate that anchors winning margins to known pre-race form."""

from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

from .field_strength import FIELD_MODEL_VERSION
from .performance import MODEL_VERSION, SECONDS_PER_LENGTH, build_horse_states, run_pipeline, utc_now
from .storage import RacingStore


ROOT = Path(__file__).resolve().parents[1]
MODEL = "performance-par-v1.0+form-anchored-margin-research-v1.0"


def margin_multiplier(distance_metres: int) -> float:
    """IFHA-inspired relative scale: 1 internal point/length at 1600m."""
    if distance_metres <= 1000: return 1.5
    if distance_metres <= 1600: return 1.5 - .5 * (distance_metres - 1000) / 600
    if distance_metres <= 2800: return 1.0 - .5 * (distance_metres - 1600) / 1200
    return .5


def anchored_level(prior_and_margin: list[tuple[float, float]], field_size: int) -> tuple[float | None, float]:
    if len(prior_and_margin) < 2: return None, 0.0
    implied = [prior + margin for prior, margin in prior_and_margin]
    centre = statistics.median(implied)
    mad = statistics.median(abs(value - centre) for value in implied)
    coverage = len(prior_and_margin) / field_size
    reliability = min(.50, coverage * len(implied) / (len(implied) + 4.0) * 10.0 / (10.0 + mad))
    return centre, reliability


def build_candidate(store: RacingStore, as_of_date: str, *, min_par_sample: int = 5) -> dict[str, Any]:
    run_pipeline(store, as_of_date, min_par_sample=min_par_sample, model_version=MODEL_VERSION)
    rows = store.connection.execute(
        """SELECT p.*,rr.finish_position,rr.beaten_lengths,rr.finish_time_seconds,race.official_time_seconds,
                  race.distance_metres,l.horse_id,h.canonical_name,pre.prior_rating,pre.rated
             FROM run_performances p JOIN runner_results rr
               USING(source,race_date,track_slug,race_number,runner_number)
             JOIN race_results race USING(source,race_date,track_slug,race_number)
             JOIN runner_horse_links l USING(source,race_date,track_slug,race_number,runner_number)
             JOIN horses h ON h.horse_id=l.horse_id
             LEFT JOIN pre_race_runner_states pre ON pre.field_model_version=? AND pre.source=p.source
               AND pre.race_date=p.race_date AND pre.track_slug=p.track_slug AND pre.race_number=p.race_number
               AND pre.runner_number=p.runner_number
            WHERE p.model_version=? AND p.as_of_date=? AND p.race_date<?
            ORDER BY p.source,p.race_date,p.track_slug,p.race_number,p.runner_number""",
        (FIELD_MODEL_VERSION, MODEL_VERSION, as_of_date, as_of_date)).fetchall()
    grouped: dict[tuple, list] = defaultdict(list)
    for row in rows: grouped[(row["source"],row["race_date"],row["track_slug"],row["race_number"])].append(row)
    now = utc_now(); anchored_races = winner_raised = winner_lowered = 0; adjustments = []
    for race_rows in grouped.values():
        multiplier = margin_multiplier(int(race_rows[0]["distance_metres"]))
        evidence = []
        margins = {}
        for row in race_rows:
            margin = row["beaten_lengths"]
            if margin is None and row["finish_time_seconds"] is not None and row["official_time_seconds"] is not None:
                margin = max(0.0, (float(row["finish_time_seconds"])-float(row["official_time_seconds"])) / SECONDS_PER_LENGTH)
            margins[row["runner_number"]] = float(margin) if margin is not None else None
            if row["rated"] and row["prior_rating"] is not None and margin is not None:
                evidence.append((float(row["prior_rating"]), min(float(margin), 12.0) * multiplier))
        level, reliability = anchored_level(evidence, len(race_rows)); anchored_races += int(level is not None)
        for row in race_rows:
            margin = margins[row["runner_number"]]
            form_rating = level - min(margin, 12.0)*multiplier if level is not None and margin is not None else None
            adjustment = reliability * (form_rating-float(row["performance_rating"])) if form_rating is not None else 0.0
            adjustments.append(abs(adjustment))
            if row["finish_position"] == 1:
                winner_raised += int(adjustment > 1e-12); winner_lowered += int(adjustment < -1e-12)
            detail = {**json.loads(row["detail_json"]), "form_anchored_margin": {
                "model": MODEL, "margin_lengths": margin, "distance_multiplier": multiplier,
                "implied_winner_level": level, "anchor_reliability": reliability,
                "form_rating": form_rating, "adjustment": adjustment, "margin_cap_lengths": 12.0,
                "weight_wfa_adjustment": "not available", "research_only": True,
                "prospective_promotion_required": True}}
            store.connection.execute(
                """INSERT INTO run_performances
                   (model_version,as_of_date,source,race_date,track_slug,race_number,runner_number,horse_key,horse_name,
                    performance_rating,time_component,margin_component,sectional_component,pace_component,confidence,
                    detail_json,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(model_version,as_of_date,source,race_date,track_slug,race_number,runner_number) DO UPDATE SET
                    horse_key=excluded.horse_key,horse_name=excluded.horse_name,
                    performance_rating=excluded.performance_rating,detail_json=excluded.detail_json,created_at=excluded.created_at""",
                (MODEL, as_of_date, row["source"], row["race_date"], row["track_slug"], row["race_number"],
                 row["runner_number"], row["horse_id"], row["canonical_name"], row["performance_rating"]+adjustment,
                 row["time_component"], row["margin_component"], row["sectional_component"], row["pace_component"],
                 row["confidence"], json.dumps(detail, sort_keys=True), now))
    store.connection.commit(); states = build_horse_states(store, as_of_date, model_version=MODEL)
    return {"model_version": MODEL, "as_of_date": as_of_date, "performances": len(rows), "horse_states": states,
            "races": len(grouped), "anchored_races": anchored_races, "winner_raised": winner_raised,
            "winner_lowered": winner_lowered, "mean_absolute_adjustment": statistics.mean(adjustments) if adjustments else 0,
            "status": "RESEARCH_ONLY_AWAITING_PROSPECTIVE_RESULTS",
            "important": "not a flat winner bonus; whole-race margins are anchored to prior known form"}


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database",type=Path,default=ROOT/"data"/"racing_engine.sqlite")
    parser.add_argument("--as-of",required=True); parser.add_argument("--output",type=Path)
    args=parser.parse_args(); store=RacingStore(args.database)
    try: report=build_candidate(store,args.as_of)
    finally: store.close()
    rendered=json.dumps(report,indent=2,sort_keys=True)+"\n"
    if args.output: args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(rendered)
    else: print(rendered,end="")


if __name__=="__main__": main()
