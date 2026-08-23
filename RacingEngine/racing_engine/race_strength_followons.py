"""Research-only Race Strength follow-ons after the Step 10 non-promotion."""

from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

from .performance import MODEL_VERSION, NEUTRAL, RECENCY_HALF_LIFE_DAYS, build_horse_states, run_pipeline, utc_now
from .race_strength import RACE_STRENGTH_VERSION
from .storage import RacingStore


ROOT = Path(__file__).resolve().parents[1]
RESEARCH_MODELS = {
    "reduced_10": "performance-par-v1.0+race-strength-10pct-research-v1.0",
    "reduced_25": "performance-par-v1.0+race-strength-25pct-research-v1.0",
    "reduced_50": "performance-par-v1.0+race-strength-50pct-research-v1.0",
    "confidence_only": "performance-par-v1.0+race-strength-confidence-research-v1.0",
    "conditional": "performance-par-v1.0+race-strength-conditional-research-v1.0",
}
COEFFICIENTS = {"reduced_10": .10, "reduced_25": .25, "reduced_50": .50}


def robust_weighted_state(values: list[tuple[float, float, int]], cutoff: date) -> tuple[float, float]:
    """Recency/confidence mean with per-horse median +/- 20 point winsorisation."""
    raw = [value for value, _, _ in values]; centre = statistics.median(raw)
    clipped = [max(centre - 20.0, min(centre + 20.0, value)) for value in raw]
    weights = [math.exp(-math.log(2) * age / RECENCY_HALF_LIFE_DAYS) * confidence
               for _, confidence, age in values]
    mean = sum(value * weight for value, weight in zip(clipped, weights)) / sum(weights)
    reliability = 1.0 - math.exp(-len(values) / 4.0)
    return NEUTRAL + reliability * (mean - NEUTRAL), statistics.pstdev(clipped) if len(clipped) > 1 else 0.0


def _conditional_coefficient(class_family: str | None, reliability: float) -> float:
    base = .25 if class_family in ("group", "listed") else (.10 if class_family == "benchmark" else .05)
    return base * max(0.0, min(1.0, reliability))


def build_research_candidates(store: RacingStore, as_of_date: str, *, min_par_sample: int = 5) -> dict[str, Any]:
    run_pipeline(store, as_of_date, min_par_sample=min_par_sample, model_version=MODEL_VERSION)
    rows = store.connection.execute(
        """SELECT p.*,l.horse_id,h.canonical_name,rs.combined_rating,
                  ((rs.class_reliability+rs.field_reliability)/2.0) strength_reliability,rc.class_family
             FROM run_performances p JOIN runner_horse_links l USING(source,race_date,track_slug,race_number,runner_number)
             JOIN horses h ON h.horse_id=l.horse_id
             LEFT JOIN race_strength_ratings rs ON rs.race_strength_version=? AND rs.source=p.source
               AND rs.race_date=p.race_date AND rs.track_slug=p.track_slug AND rs.race_number=p.race_number
             LEFT JOIN race_classifications rc USING(source,race_date,track_slug,race_number)
            WHERE p.model_version=? AND p.as_of_date=? AND p.race_date<?""",
        (RACE_STRENGTH_VERSION, MODEL_VERSION, as_of_date, as_of_date)).fetchall()
    now = utc_now(); summaries = {}
    for name, model in RESEARCH_MODELS.items():
        for row in rows:
            reliability = float(row["strength_reliability"] or 0.0)
            if name in COEFFICIENTS:
                coefficient = COEFFICIENTS[name]; delta = coefficient * (float(row["combined_rating"] or 100) - 100)
                confidence = float(row["confidence"])
            elif name == "conditional":
                coefficient = _conditional_coefficient(row["class_family"], reliability)
                delta = coefficient * (float(row["combined_rating"] or 100) - 100)
                confidence = float(row["confidence"])
            else:
                coefficient = 0.0; delta = 0.0
                confidence = float(row["confidence"]) * (.75 + .25 * reliability)
            detail = {**json.loads(row["detail_json"]), "research_only": True,
                      "prospective_promotion_required": True, "race_strength_coefficient": coefficient,
                      "race_strength_adjustment": delta, "race_strength_reliability": reliability,
                      "confidence_multiplier": confidence / float(row["confidence"])}
            store.connection.execute(
                """INSERT INTO run_performances
                   (model_version,as_of_date,source,race_date,track_slug,race_number,runner_number,horse_key,horse_name,
                    performance_rating,time_component,margin_component,sectional_component,pace_component,confidence,
                    detail_json,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(model_version,as_of_date,source,race_date,track_slug,race_number,runner_number) DO UPDATE SET
                    horse_key=excluded.horse_key,horse_name=excluded.horse_name,
                    performance_rating=excluded.performance_rating,confidence=excluded.confidence,
                    detail_json=excluded.detail_json,created_at=excluded.created_at""",
                (model, as_of_date, row["source"], row["race_date"], row["track_slug"], row["race_number"],
                 row["runner_number"], row["horse_id"], row["canonical_name"], row["performance_rating"] + delta,
                 row["time_component"], row["margin_component"], row["sectional_component"], row["pace_component"],
                 confidence, json.dumps(detail, sort_keys=True), now))
        store.connection.commit(); summaries[name] = {"model_version": model,
            "performances": len(rows), "horse_states": build_horse_states(store, as_of_date, model_version=model)}
    robust_model = "performance-par-v1.0+robust-identity-state-research-v1.0"
    grouped: dict[str, list] = defaultdict(list)
    cutoff = date.fromisoformat(as_of_date)
    for row in rows:
        grouped[row["horse_id"]].append(row)
    for horse_id, runs in grouped.items():
        values = [(float(run["performance_rating"]), float(run["confidence"]),
                   max(0, (cutoff - date.fromisoformat(run["race_date"])).days)) for run in runs]
        rating, consistency = robust_weighted_state(values, cutoff); latest = max(runs, key=lambda run: run["race_date"])
        store.connection.execute(
            """INSERT INTO horse_rating_states
               (model_version,as_of_date,horse_key,horse_name,overall_rating,peak_rating,consistency,rated_runs,
                uncertainty,detail_json,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(model_version,as_of_date,horse_key) DO UPDATE SET overall_rating=excluded.overall_rating,
                peak_rating=excluded.peak_rating,consistency=excluded.consistency,rated_runs=excluded.rated_runs,
                uncertainty=excluded.uncertainty,detail_json=excluded.detail_json,created_at=excluded.created_at""",
            (robust_model, as_of_date, horse_id, latest["canonical_name"], rating,
             max(value[0] for value in values), consistency, len(values), max(2, consistency * .5),
             json.dumps({"method": "recency-confidence-winsorised-state-v1", "winsor_band": 20,
                         "research_only": True, "prospective_promotion_required": True}, sort_keys=True), now))
    store.connection.commit(); summaries["robust_identity"] = {"model_version": robust_model, "horse_states": len(grouped)}
    return {"as_of_date": as_of_date, "status": "RESEARCH_ONLY_NOT_PROMOTED", "models": summaries,
            "holdout_policy": "Step 10 holdout has been observed; promotion requires prospective results"}


def future_form_confirmation(store: RacingStore, as_of_date: str) -> dict[str, Any]:
    rows = store.connection.execute(
        """SELECT l.horse_id,p.race_date,p.performance_rating,rs.combined_rating,rc.class_family
             FROM run_performances p JOIN runner_horse_links l USING(source,race_date,track_slug,race_number,runner_number)
             JOIN race_strength_ratings rs ON rs.race_strength_version=? AND rs.source=p.source
               AND rs.race_date=p.race_date AND rs.track_slug=p.track_slug AND rs.race_number=p.race_number
             LEFT JOIN race_classifications rc USING(source,race_date,track_slug,race_number)
            WHERE p.model_version=? AND p.as_of_date=? ORDER BY l.horse_id,p.race_date""",
        (RACE_STRENGTH_VERSION, MODEL_VERSION, as_of_date)).fetchall()
    grouped: dict[str, list] = defaultdict(list)
    for row in rows: grouped[row["horse_id"]].append(row)
    pairs = []
    for runs in grouped.values():
        for current, nxt in zip(runs, runs[1:]):
            pairs.append((float(current["combined_rating"]), float(nxt["performance_rating"]) - float(current["performance_rating"])))
    if len(pairs) < 3: return {"pairs": len(pairs), "status": "INSUFFICIENT_EVIDENCE"}
    strengths, changes = zip(*pairs); mean_x = statistics.mean(strengths); mean_y = statistics.mean(changes)
    numerator = sum((x-mean_x)*(y-mean_y) for x,y in pairs)
    denominator = math.sqrt(sum((x-mean_x)**2 for x in strengths)*sum((y-mean_y)**2 for y in changes))
    return {"pairs": len(pairs), "correlation_strength_to_next_run_change": numerator/denominator if denominator else None,
            "mean_next_run_change": mean_y,
            "interpretation": "descriptive confirmation only; not a causal or promotion test"}


def descriptive_report(store: RacingStore) -> dict[str, Any]:
    by_class = [dict(row) for row in store.connection.execute(
        """SELECT coalesce(rc.class_family,'unknown') class_family,count(*) races,
                  round(avg(rs.combined_rating),2) mean_strength,round(min(rs.combined_rating),2) minimum,
                  round(max(rs.combined_rating),2) maximum
             FROM race_strength_ratings rs LEFT JOIN race_classifications rc
               USING(source,race_date,track_slug,race_number)
            WHERE rs.race_strength_version=? GROUP BY coalesce(rc.class_family,'unknown') ORDER BY mean_strength DESC""",
        (RACE_STRENGTH_VERSION,))]
    by_state = [dict(row) for row in store.connection.execute(
        """SELECT rr.state,count(*) races,round(avg(rs.combined_rating),2) mean_strength
             FROM race_strength_ratings rs JOIN race_results rr USING(source,race_date,track_slug,race_number)
            WHERE rs.race_strength_version=? GROUP BY rr.state""", (RACE_STRENGTH_VERSION,))]
    return {"race_strength_version": RACE_STRENGTH_VERSION, "by_class": by_class, "by_state": by_state,
            "usage": "descriptive comparison; not an accepted Horse Ability adjustment"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=ROOT / "data" / "racing_engine.sqlite")
    parser.add_argument("--as-of", required=True); parser.add_argument("--output", type=Path)
    args = parser.parse_args(); store = RacingStore(args.database)
    try:
        report = {"candidates": build_research_candidates(store, args.as_of),
                  "future_form": future_form_confirmation(store, args.as_of),
                  "descriptive": descriptive_report(store)}
    finally: store.close()
    rendered = json.dumps(report, indent=2, sort_keys=True)+"\n"
    if args.output: args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(rendered)
    else: print(rendered,end="")


if __name__ == "__main__": main()
