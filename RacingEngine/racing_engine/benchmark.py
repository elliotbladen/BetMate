"""Generate the frozen prediction-level V1 benchmark."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .evaluation_protocol import assess_eligibility, load_protocol, period_for, protocol_hash, score_race
from .performance import MODEL_VERSION, NEUTRAL, run_pipeline, utc_now
from .ratings import horse_key, softmax
from .storage import RacingStore


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PERIODS = ("validation", "historical_holdout")


def _distance_segment(value: int | None) -> str:
    if value is None:
        return "unknown"
    if value <= 1200:
        return "sprint"
    if value <= 1600:
        return "short_mile"
    if value <= 2000:
        return "middle"
    return "staying"


def _field_segment(value: int) -> str:
    return "small" if value <= 8 else ("medium" if value <= 12 else "large")


def _history_segment(value: int) -> str:
    return "debutant" if value == 0 else ("light" if value <= 2 else ("developing" if value <= 5 else "established"))


def _runner_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "runners": len(rows),
        "mean_probability": sum(row["probability"] for row in rows) / len(rows) if rows else None,
        "strike_rate": sum(row["outcome"] for row in rows) / len(rows) if rows else None,
        "mean_brier": sum((row["probability"] - row["outcome"]) ** 2 for row in rows) / len(rows) if rows else None,
    }


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"races": 0, "runners": 0, "mean_log_loss": None, "mean_race_brier": None,
                "mean_runner_brier": None, "top_1": None, "top_2": None, "top_3": None,
                "mean_winner_rank": None}
    return {
        "races": len(rows),
        "runners": sum(row["field_size"] for row in rows),
        "mean_log_loss": sum(row["log_loss"] for row in rows) / len(rows),
        "mean_race_brier": sum(row["race_brier"] for row in rows) / len(rows),
        "mean_runner_brier": sum(row["race_brier"] for row in rows) / sum(row["field_size"] for row in rows),
        "top_1": sum(row["winner_rank"] <= 1 for row in rows) / len(rows),
        "top_2": sum(row["winner_rank"] <= 2 for row in rows) / len(rows),
        "top_3": sum(row["winner_rank"] <= 3 for row in rows) / len(rows),
        "mean_winner_rank": sum(row["winner_rank"] for row in rows) / len(rows),
    }


def _calibration(predictions: list[dict[str, Any]], edges: list[float]) -> list[dict[str, Any]]:
    result = []
    for lower, upper in zip(edges, edges[1:]):
        selected = [row for row in predictions if lower <= row["probability"] <= upper
                    and (row["probability"] < upper or upper == 1.0)]
        result.append({
            "lower": lower, "upper": upper, "runners": len(selected),
            "mean_probability": sum(row["probability"] for row in selected) / len(selected) if selected else None,
            "strike_rate": sum(row["outcome"] for row in selected) / len(selected) if selected else None,
        })
    return result


def run_benchmark(store: RacingStore, *, protocol_path: Path, periods: tuple[str, ...] = DEFAULT_PERIODS,
                  min_par_sample: int = 5, model_version: str = MODEL_VERSION) -> dict[str, Any]:
    protocol = load_protocol(protocol_path)
    digest = protocol_hash(protocol)
    unknown = set(periods) - set(protocol["periods"])
    if unknown:
        raise ValueError(f"unknown evaluation periods: {sorted(unknown)}")
    dates = [row[0] for row in store.connection.execute(
        "SELECT DISTINCT race_date FROM race_results ORDER BY race_date").fetchall()
        if period_for(row[0], protocol) in periods]
    exclusions: Counter[str] = Counter()
    race_scores: list[dict[str, Any]] = []
    equal_scores: list[dict[str, Any]] = []
    prediction_rows: list[dict[str, Any]] = []
    now = utc_now()
    for race_date in dates:
        period = period_for(race_date, protocol)
        run_pipeline(store, race_date, min_par_sample=min_par_sample, model_version=model_version)
        states = {row["horse_key"]: row for row in store.connection.execute(
            """SELECT horse_key, overall_rating, rated_runs FROM horse_rating_states
               WHERE model_version=? AND as_of_date=?""", (model_version, race_date))}
        races = store.connection.execute(
            """SELECT rr.source,rr.race_date,rr.track_slug,rr.race_number,rr.state,rr.distance_metres,
                      rr.track_condition,rc.class_family
                 FROM race_results rr LEFT JOIN race_classifications rc USING(source,race_date,track_slug,race_number)
                WHERE rr.race_date=? ORDER BY rr.track_slug,rr.race_number,rr.source""", (race_date,)).fetchall()
        for race in races:
            identity = (race["source"], race_date, race["track_slug"], race["race_number"])
            raw = [dict(row) for row in store.connection.execute(
                """SELECT runner_number, runner_name, finish_position, result_status FROM runner_results
                   WHERE source=? AND race_date=? AND track_slug=? AND race_number=? ORDER BY runner_number""", identity)]
            eligibility = assess_eligibility(raw, protocol)
            if not eligibility.eligible:
                exclusions[eligibility.reason or "unknown"] += 1
                continue
            ratings = []
            histories = []
            for runner in eligibility.starters:
                state = states.get(horse_key(runner["runner_name"]))
                ratings.append(float(state["overall_rating"]) if state else float(protocol["eligibility"]["population_prior_rating"]))
                histories.append(int(state["rated_runs"]) if state else 0)
            probabilities = softmax(ratings)
            outcomes = [1 if runner["finish_position"] == 1 else 0 for runner in eligibility.starters]
            score = score_race(probabilities, outcomes, protocol)
            equal = score_race([1 / len(outcomes)] * len(outcomes), outcomes, protocol)
            race_detail = {"period": period, "source": race["source"], "race_date": race_date,
                           "track_slug": race["track_slug"], "race_number": race["race_number"],
                           "season": race_date[:4], "state": race["state"],
                           "distance": _distance_segment(race["distance_metres"]),
                           "going": (race["track_condition"] or "unknown").lower().split()[0],
                           "field_size_segment": _field_segment(len(outcomes)),
                           "class_family": race["class_family"] or "unknown",
                           "field_size": len(outcomes), **score}
            race_scores.append(race_detail)
            equal_scores.append({**race_detail, **equal})
            for runner, rating, history, probability, outcome in zip(
                    eligibility.starters, ratings, histories, probabilities, outcomes):
                item = {"period": period, "source": race["source"], "race_date": race_date,
                        "track_slug": race["track_slug"], "race_number": race["race_number"],
                        "runner_number": runner["runner_number"], "runner_name": runner["runner_name"],
                        "rating": rating, "history_depth": history, "probability": probability,
                        "outcome": outcome}
                prediction_rows.append(item)
                store.connection.execute(
                    """INSERT INTO benchmark_predictions
                       (protocol_version,protocol_hash,model_version,period,source,race_date,track_slug,race_number,
                        runner_number,runner_name,horse_key,raw_rating,win_probability,outcome,history_depth,unrated,
                        information_cutoff,detail_json,created_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                       ON CONFLICT(protocol_hash,model_version,source,race_date,track_slug,race_number,runner_number)
                       DO UPDATE SET raw_rating=excluded.raw_rating,win_probability=excluded.win_probability,
                         outcome=excluded.outcome,history_depth=excluded.history_depth,unrated=excluded.unrated,
                         information_cutoff=excluded.information_cutoff,detail_json=excluded.detail_json,
                         created_at=excluded.created_at""",
                    (protocol["protocol_version"], digest, model_version, period, race["source"], race_date,
                     race["track_slug"], race["race_number"], runner["runner_number"], runner["runner_name"],
                     horse_key(runner["runner_name"]), rating, probability, outcome, history, int(history == 0),
                     race_date, json.dumps({"state_cutoff_exclusive": race_date}, sort_keys=True), now))
        store.connection.commit()
    by_period = {period: _summary([row for row in race_scores if row["period"] == period]) for period in periods}
    dimensions = {
        "period": "period", "season": "season", "state": "state", "source": "source",
        "track": "track_slug", "distance": "distance", "going": "going",
        "field_size": "field_size_segment", "class_family": "class_family",
    }
    segments = {}
    for label, field in dimensions.items():
        values = sorted({str(row[field]) for row in race_scores})
        segments[label] = {value: _summary([row for row in race_scores if str(row[field]) == value]) for value in values}
    history_values = sorted({_history_segment(row["history_depth"]) for row in prediction_rows})
    runner_segments = {"history_depth": {
        value: _runner_summary([row for row in prediction_rows if _history_segment(row["history_depth"]) == value])
        for value in history_values
    }}
    report = {
        "report_name": "definitive-v1-benchmark",
        "model_version": model_version,
        "protocol_version": protocol["protocol_version"],
        "protocol_hash": digest,
        "periods": list(periods),
        "database_cutoff": max(dates) if dates else None,
        "metrics": _summary(race_scores),
        "equal_probability": _summary(equal_scores),
        "by_period": by_period,
        "segments": segments,
        "runner_segments": runner_segments,
        "coverage": {"eligible_races": len(race_scores), "runners": len(prediction_rows),
                     "unrated_runners": sum(row["history_depth"] == 0 for row in prediction_rows),
                     "excluded_races": sum(exclusions.values()), "exclusion_reasons": dict(sorted(exclusions.items()))},
        "calibration": _calibration(prediction_rows, protocol["metrics"]["calibration_edges"]),
        "no_lookahead": {"state_cutoff": "race_date exclusive", "same_day_results_used": False},
        "generated_at": now,
    }
    store.connection.execute(
        """INSERT INTO benchmark_reports (protocol_hash,model_version,report_name,database_cutoff,report_json,created_at)
           VALUES (?,?,?,?,?,?) ON CONFLICT(protocol_hash,model_version,report_name) DO UPDATE SET
             database_cutoff=excluded.database_cutoff,report_json=excluded.report_json,created_at=excluded.created_at""",
        (digest, model_version, report["report_name"], report["database_cutoff"] or "", json.dumps(report, sort_keys=True), now))
    store.connection.commit()
    return report


def render_markdown(report: dict[str, Any]) -> str:
    metric = report["metrics"]
    equal = report["equal_probability"]
    lines = ["# Definitive V1 benchmark", "", f"Model: `{report['model_version']}`", "",
             f"Protocol: `{report['protocol_version']}` (`{report['protocol_hash']}`)", "",
             "## Overall", "", "| Measure | V1 | Equal probability |", "| --- | ---: | ---: |"]
    for key in ("races", "runners", "mean_log_loss", "mean_race_brier", "mean_runner_brier", "top_1", "top_2", "top_3", "mean_winner_rank"):
        lines.append(f"| {key} | {metric[key]} | {equal[key]} |")
    lines += ["", "## Coverage", "", "```json", json.dumps(report["coverage"], indent=2, sort_keys=True), "```", "",
              "## Periods", ""]
    for period, values in report["by_period"].items():
        lines.append(f"- {period}: {values['races']} races, log loss {values['mean_log_loss']}, race Brier {values['mean_race_brier']}")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=ROOT / "data" / "racing_engine.sqlite")
    parser.add_argument("--protocol", type=Path, default=ROOT / "config" / "evaluation_protocol_v1.json")
    parser.add_argument("--period", action="append", choices=("train", "validation", "historical_holdout", "prospective_holdout"))
    parser.add_argument("--min-par-sample", type=int, default=5)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    store = RacingStore(args.database)
    try:
        report = run_benchmark(store, protocol_path=args.protocol, periods=tuple(args.period or DEFAULT_PERIODS),
                               min_par_sample=args.min_par_sample)
    finally:
        store.close()
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)
        args.output.with_suffix(".md").write_text(render_markdown(report))
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
