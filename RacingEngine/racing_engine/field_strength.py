"""Freeze identity-aware, prior-only strength for each historical field."""

from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

from .performance import MODEL_VERSION, NEUTRAL, RECENCY_HALF_LIFE_DAYS, run_pipeline
from .storage import RacingStore, utc_now


ROOT = Path(__file__).resolve().parents[1]
FIELD_MODEL_VERSION = "pre-race-field-v1.0"
UNRATED_UNCERTAINTY = 12.0


def identity_states(store: RacingStore, as_of_date: str, *, performance_model: str = MODEL_VERSION) -> dict[str, dict[str, Any]]:
    """Aggregate exact-cutoff performances through durable horse links."""
    rows = store.connection.execute(
        """SELECT l.horse_id,h.canonical_name,p.race_date,p.performance_rating,p.confidence
             FROM run_performances p
             JOIN runner_horse_links l USING(source,race_date,track_slug,race_number,runner_number)
             JOIN horses h ON h.horse_id=l.horse_id
            WHERE p.model_version=? AND p.as_of_date=? AND p.race_date<?
            ORDER BY l.horse_id,p.race_date""", (performance_model, as_of_date, as_of_date)).fetchall()
    grouped: dict[str, list[Any]] = defaultdict(list)
    for row in rows:
        grouped[row["horse_id"]].append(row)
    cutoff = date.fromisoformat(as_of_date)
    result = {}
    for horse_id, runs in grouped.items():
        values, weights = [], []
        for run in runs:
            age = max(0, (cutoff - date.fromisoformat(run["race_date"])).days)
            weight = math.exp(-math.log(2) * age / RECENCY_HALF_LIFE_DAYS) * float(run["confidence"])
            values.append(float(run["performance_rating"])); weights.append(weight)
        mean = sum(value * weight for value, weight in zip(values, weights)) / sum(weights)
        reliability = 1.0 - math.exp(-len(values) / 4.0)
        rating = NEUTRAL + reliability * (mean - NEUTRAL)
        consistency = statistics.pstdev(values) if len(values) > 1 else 0.0
        uncertainty = max(2.0, UNRATED_UNCERTAINTY * (1 - reliability) + consistency * 0.5)
        result[horse_id] = {"horse_name": runs[-1]["canonical_name"], "rating": rating,
                            "prior_runs": len(values), "uncertainty": uncertainty}
    return result


def summarize_field(runners: list[dict[str, Any]]) -> dict[str, Any]:
    if len(runners) < 2:
        raise ValueError("field strength requires at least two starters")
    ratings = [float(row["prior_rating"]) for row in runners]
    rated_ratings = [float(row["prior_rating"]) for row in runners if row["rated"]]
    ordered = sorted(ratings, reverse=True)
    top = ordered[0]
    rated_top = max(rated_ratings) if rated_ratings else None
    return {"starters": len(runners), "rated_runners": len(rated_ratings),
            "rated_coverage": len(rated_ratings) / len(runners),
            "field_median_rating": statistics.median(ratings),
            "rated_only_median_rating": statistics.median(rated_ratings) if rated_ratings else None,
            "top_four_mean_rating": statistics.mean(ordered[:4]), "top_rating": top,
            "depth_within_five": (sum(value >= rated_top - 5.0 for value in rated_ratings)
                                  if rated_top is not None else 0),
            "field_uncertainty": math.sqrt(statistics.mean(float(row["prior_uncertainty"]) ** 2 for row in runners))}


def build_field_strengths(store: RacingStore, *, from_date: str | None = None, to_date: str | None = None,
                          min_par_sample: int = 5, field_model_version: str = FIELD_MODEL_VERSION,
                          performance_model: str = MODEL_VERSION) -> dict[str, Any]:
    clauses = []
    parameters: list[Any] = []
    if from_date:
        clauses.append("race_date>=?"); parameters.append(from_date)
    if to_date:
        clauses.append("race_date<=?"); parameters.append(to_date)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    dates = [row[0] for row in store.connection.execute(
        "SELECT DISTINCT race_date FROM race_results" + where + " ORDER BY race_date", parameters).fetchall()]
    now = utc_now(); races_stored = runners_stored = excluded = 0
    coverage_values = []
    for race_date in dates:
        run_pipeline(store, race_date, min_par_sample=min_par_sample, model_version=performance_model)
        states = identity_states(store, race_date, performance_model=performance_model)
        races = store.connection.execute(
            "SELECT source,track_slug,race_number FROM race_results WHERE race_date=? ORDER BY track_slug,race_number,source",
            (race_date,)).fetchall()
        for race in races:
            identity = (race["source"], race_date, race["track_slug"], race["race_number"])
            starters = store.connection.execute(
                """SELECT rr.runner_number,rr.runner_name,l.horse_id,h.canonical_name
                     FROM runner_results rr
                     JOIN runner_horse_links l USING(source,race_date,track_slug,race_number,runner_number)
                     JOIN horses h ON h.horse_id=l.horse_id
                    WHERE rr.source=? AND rr.race_date=? AND rr.track_slug=? AND rr.race_number=?
                      AND rr.result_status NOT IN ('scratched','non_starter','abandoned')
                    ORDER BY rr.runner_number""", identity).fetchall()
            if len(starters) < 2:
                excluded += 1; continue
            runner_states = []
            for runner in starters:
                prior = states.get(runner["horse_id"])
                state = {"runner_number": runner["runner_number"], "horse_id": runner["horse_id"],
                         "horse_name": runner["canonical_name"], "prior_rating": prior["rating"] if prior else NEUTRAL,
                         "prior_runs": prior["prior_runs"] if prior else 0,
                         "prior_uncertainty": prior["uncertainty"] if prior else UNRATED_UNCERTAINTY,
                         "rated": int(prior is not None)}
                runner_states.append(state)
                store.connection.execute(
                    """INSERT INTO pre_race_runner_states
                       (field_model_version,source,race_date,track_slug,race_number,runner_number,horse_id,horse_name,
                        prior_rating,prior_runs,prior_uncertainty,rated,information_cutoff,detail_json,created_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                       ON CONFLICT(field_model_version,source,race_date,track_slug,race_number,runner_number) DO UPDATE SET
                        horse_id=excluded.horse_id,horse_name=excluded.horse_name,prior_rating=excluded.prior_rating,
                        prior_runs=excluded.prior_runs,prior_uncertainty=excluded.prior_uncertainty,rated=excluded.rated,
                        information_cutoff=excluded.information_cutoff,detail_json=excluded.detail_json,created_at=excluded.created_at""",
                    (field_model_version, *identity, runner["runner_number"], runner["horse_id"], runner["canonical_name"],
                     state["prior_rating"], state["prior_runs"], state["prior_uncertainty"], state["rated"], race_date,
                     json.dumps({"cutoff_exclusive": race_date, "performance_model": performance_model,
                                 "unrated_policy": "neutral_100"}, sort_keys=True), now))
                runners_stored += 1
            summary = summarize_field(runner_states); coverage_values.append(summary["rated_coverage"])
            store.connection.execute(
                """INSERT INTO pre_race_field_strengths
                   (field_model_version,source,race_date,track_slug,race_number,starters,rated_runners,rated_coverage,
                    field_median_rating,rated_only_median_rating,top_four_mean_rating,top_rating,depth_within_five,
                    field_uncertainty,information_cutoff,detail_json,created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(field_model_version,source,race_date,track_slug,race_number) DO UPDATE SET
                    starters=excluded.starters,rated_runners=excluded.rated_runners,rated_coverage=excluded.rated_coverage,
                    field_median_rating=excluded.field_median_rating,rated_only_median_rating=excluded.rated_only_median_rating,
                    top_four_mean_rating=excluded.top_four_mean_rating,top_rating=excluded.top_rating,
                    depth_within_five=excluded.depth_within_five,field_uncertainty=excluded.field_uncertainty,
                    information_cutoff=excluded.information_cutoff,detail_json=excluded.detail_json,created_at=excluded.created_at""",
                (field_model_version, *identity, summary["starters"], summary["rated_runners"], summary["rated_coverage"],
                 summary["field_median_rating"], summary["rated_only_median_rating"], summary["top_four_mean_rating"],
                 summary["top_rating"], summary["depth_within_five"], summary["field_uncertainty"], race_date,
                 json.dumps({"cutoff_exclusive": race_date, "depth_definition": "rated runners within five points of top rated runner",
                             "median_includes_unrated_neutral_prior": True}, sort_keys=True), now))
            races_stored += 1
        store.connection.commit()
    return {"field_model_version": field_model_version, "performance_model": performance_model,
            "from_date": from_date, "to_date": to_date, "dates": len(dates), "races": races_stored,
            "runners": runners_stored, "excluded_races": excluded,
            "mean_rated_coverage": statistics.mean(coverage_values) if coverage_values else None,
            "no_lookahead": "all performance evidence race_date < target race_date"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=ROOT / "data" / "racing_engine.sqlite")
    parser.add_argument("--from-date"); parser.add_argument("--to-date")
    parser.add_argument("--min-par-sample", type=int, default=5)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(); store = RacingStore(args.database)
    try:
        report = build_field_strengths(store, from_date=args.from_date, to_date=args.to_date,
                                       min_par_sample=args.min_par_sample)
    finally:
        store.close()
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(rendered)
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
