"""Step 10 controlled promotion evaluation for Race Strength candidates."""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable

from .benchmark import (_calibration, _distance_segment, _field_segment, _history_segment,
                        _runner_summary, _summary)
from .evaluation_protocol import assess_eligibility, load_protocol, period_for, protocol_hash, score_race
from .performance import MODEL_VERSION, utc_now
from .race_strength_models import VARIANTS, build_variants
from .ratings import horse_key, softmax
from .storage import RacingStore


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PERIODS = ("validation", "historical_holdout")


def paired_interval(rows: list[dict[str, Any]], repetitions: int, confidence: float,
                    seed: int) -> dict[str, Any]:
    """Meeting-day block bootstrap for candidate-minus-baseline log loss."""
    blocks: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    for row in rows:
        blocks[(row["source"], row["race_date"], row["track_slug"])].append(
            row["candidate_log_loss"] - row["baseline_log_loss"])
    observed = sum(sum(values) for values in blocks.values()) / sum(map(len, blocks.values())) if blocks else None
    if not blocks:
        return {"delta": None, "lower": None, "upper": None, "blocks": 0, "repetitions": repetitions}
    values = list(blocks.values()); rng = random.Random(seed); samples = []
    for _ in range(repetitions):
        selected = [values[rng.randrange(len(values))] for _ in values]
        samples.append(sum(sum(block) for block in selected) / sum(len(block) for block in selected))
    samples.sort(); alpha = (1.0 - confidence) / 2.0
    lower_index = max(0, min(len(samples) - 1, int(alpha * len(samples))))
    upper_index = max(0, min(len(samples) - 1, int((1.0 - alpha) * len(samples)) - 1))
    return {"delta": observed, "lower": samples[lower_index], "upper": samples[upper_index],
            "blocks": len(values), "repetitions": repetitions,
            "interpretation": "candidate minus frozen V1; negative favours candidate"}


def _candidate_decision(validation: dict[str, Any], holdout: dict[str, Any],
                        validation_interval: dict[str, Any]) -> tuple[str, list[str]]:
    reasons = []
    if validation["mean_log_loss"] is None or holdout["mean_log_loss"] is None:
        return "INSUFFICIENT_EVIDENCE", ["required evaluation period has no eligible races"]
    if validation["mean_log_loss"] >= validation["baseline_mean_log_loss"]:
        reasons.append("validation primary metric did not improve")
    if validation_interval["upper"] is None or validation_interval["upper"] >= 0:
        reasons.append("paired validation interval includes no improvement")
    if holdout["mean_log_loss"] >= holdout["baseline_mean_log_loss"]:
        reasons.append("historical holdout direction does not agree")
    return ("PROMOTE", ["all frozen promotion rules passed"]) if not reasons else ("REVISE", reasons)


def _model_diagnostics(races: list[dict[str, Any]], runners: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    dimensions = {"period": "period", "season": "season", "state": "state", "source": "source",
                  "track": "track_slug", "distance": "distance", "going": "going",
                  "field_size": "field_size_segment", "class_family": "class_family"}
    segments = {label: {value: _summary([row for row in races if str(row[field]) == value])
                        for value in sorted({str(row[field]) for row in races})}
                for label, field in dimensions.items()}
    history_values = sorted({_history_segment(row["history_depth"]) for row in runners})
    uncertainty = lambda value: "low" if value <= 6 else ("medium" if value <= 12 else "high")
    uncertainty_values = sorted({uncertainty(row["uncertainty"]) for row in runners})
    runner_segments = {
        "history_depth": {value: _runner_summary([row for row in runners
            if _history_segment(row["history_depth"]) == value]) for value in history_values},
        "uncertainty": {value: _runner_summary([row for row in runners
            if uncertainty(row["uncertainty"]) == value]) for value in uncertainty_values},
    }
    return segments, runner_segments


def run_evaluation(store: RacingStore, *, protocol_path: Path,
                   periods: tuple[str, ...] = DEFAULT_PERIODS, min_par_sample: int = 5,
                   repetitions: int | None = None,
                   candidate_models: dict[str, str] | None = None,
                   candidate_builder: Callable[..., dict[str, Any]] = build_variants,
                   candidate_key_modes: dict[str, str] | None = None,
                   report_name: str = "race-strength-promotion-step10") -> dict[str, Any]:
    protocol = load_protocol(protocol_path); digest = protocol_hash(protocol)
    unknown = set(periods) - set(protocol["periods"])
    if unknown:
        raise ValueError(f"unknown evaluation periods: {sorted(unknown)}")
    dates = [row[0] for row in store.connection.execute(
        "SELECT DISTINCT race_date FROM race_results ORDER BY race_date").fetchall()
        if period_for(row[0], protocol) in periods]
    candidates_to_test = candidate_models or VARIANTS
    key_modes = candidate_key_modes or {name: "durable" for name in candidates_to_test}
    if set(key_modes) != set(candidates_to_test) or set(key_modes.values()) - {"raw", "durable"}:
        raise ValueError("candidate key modes must define every candidate as raw or durable")
    models = {"v1": MODEL_VERSION, **candidates_to_test}
    race_rows: dict[str, list[dict[str, Any]]] = {name: [] for name in models}
    runner_rows: dict[str, list[dict[str, Any]]] = {name: [] for name in models}
    paired: dict[str, list[dict[str, Any]]] = {name: [] for name in candidates_to_test}
    exclusions: Counter[str] = Counter(); now = utc_now()
    for race_date in dates:
        period = period_for(race_date, protocol)
        candidate_builder(store, race_date, min_par_sample=min_par_sample)
        state_maps = {name: {row["horse_key"]: row for row in store.connection.execute(
            "SELECT horse_key,overall_rating,rated_runs,uncertainty FROM horse_rating_states WHERE model_version=? AND as_of_date=?",
            (version, race_date))} for name, version in models.items()}
        races = store.connection.execute(
            """SELECT rr.source,rr.race_date,rr.track_slug,rr.race_number,rr.state,rr.distance_metres,
                      rr.track_condition,rc.class_family
                 FROM race_results rr LEFT JOIN race_classifications rc USING(source,race_date,track_slug,race_number)
                WHERE rr.race_date=? ORDER BY rr.track_slug,rr.race_number,rr.source""", (race_date,)).fetchall()
        for race in races:
            identity = (race["source"], race_date, race["track_slug"], race["race_number"])
            raw = [dict(row) for row in store.connection.execute(
                """SELECT rr.runner_number,rr.runner_name,rr.finish_position,rr.result_status,l.horse_id
                     FROM runner_results rr LEFT JOIN runner_horse_links l
                       USING(source,race_date,track_slug,race_number,runner_number)
                    WHERE rr.source=? AND rr.race_date=? AND rr.track_slug=? AND rr.race_number=?
                    ORDER BY rr.runner_number""", identity)]
            eligibility = assess_eligibility(raw, protocol)
            if not eligibility.eligible:
                exclusions[eligibility.reason or "unknown"] += 1; continue
            outcomes = [int(runner["finish_position"] == 1) for runner in eligibility.starters]
            scores = {}
            for name, version in models.items():
                ratings = []; histories = []; uncertainties = []
                for runner in eligibility.starters:
                    key = (horse_key(runner["runner_name"])
                           if name == "v1" or key_modes.get(name) == "raw" else runner["horse_id"])
                    state = state_maps[name].get(key) if key else None
                    ratings.append(float(state["overall_rating"]) if state else float(protocol["eligibility"]["population_prior_rating"]))
                    histories.append(int(state["rated_runs"]) if state else 0)
                    uncertainties.append(float(state["uncertainty"]) if state else 12.0)
                probabilities = softmax(ratings); score = score_race(probabilities, outcomes, protocol); scores[name] = score
                detail = {"period": period, "source": race["source"], "race_date": race_date,
                          "track_slug": race["track_slug"], "race_number": race["race_number"],
                          "season": race_date[:4], "state": race["state"],
                          "distance": _distance_segment(race["distance_metres"]),
                          "going": (race["track_condition"] or "unknown").lower().split()[0],
                          "field_size_segment": _field_segment(len(outcomes)),
                          "class_family": race["class_family"] or "unknown", "field_size": len(outcomes), **score}
                race_rows[name].append(detail)
                for runner, rating, history, uncertainty, probability, outcome in zip(
                        eligibility.starters, ratings, histories, uncertainties, probabilities, outcomes):
                    runner_rows[name].append({**{key: detail[key] for key in ("period", "source", "race_date", "track_slug", "race_number")},
                        "runner_number": runner["runner_number"], "runner_name": runner["runner_name"],
                        "rating": rating, "history_depth": history, "uncertainty": uncertainty,
                        "probability": probability, "outcome": outcome})
                    store.connection.execute(
                        """INSERT INTO benchmark_predictions
                           (protocol_version,protocol_hash,model_version,period,source,race_date,track_slug,race_number,
                            runner_number,runner_name,horse_key,raw_rating,win_probability,outcome,history_depth,unrated,
                            information_cutoff,detail_json,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                           ON CONFLICT(protocol_hash,model_version,source,race_date,track_slug,race_number,runner_number)
                           DO UPDATE SET raw_rating=excluded.raw_rating,win_probability=excluded.win_probability,
                             outcome=excluded.outcome,history_depth=excluded.history_depth,unrated=excluded.unrated,
                             information_cutoff=excluded.information_cutoff,detail_json=excluded.detail_json,created_at=excluded.created_at""",
                        (protocol["protocol_version"], digest, version, period, race["source"], race_date,
                         race["track_slug"], race["race_number"], runner["runner_number"], runner["runner_name"],
                         horse_key(runner["runner_name"]) if name == "v1" or key_modes.get(name) == "raw"
                         else runner["horse_id"], rating, probability,
                         outcome, history, int(history == 0), race_date,
                         json.dumps({"state_cutoff_exclusive": race_date, "uncertainty": uncertainty}, sort_keys=True), now))
            for name in candidates_to_test:
                paired[name].append({"period": period, "source": race["source"], "race_date": race_date,
                                     "track_slug": race["track_slug"], "race_number": race["race_number"],
                                     "baseline_log_loss": scores["v1"]["log_loss"],
                                     "candidate_log_loss": scores[name]["log_loss"]})
        store.connection.commit()
    sampling = protocol["resampling"]; reps = repetitions or int(sampling["repetitions"])
    summaries = {}
    for name in models:
        metrics = _summary(race_rows[name])
        by_period = {period: _summary([row for row in race_rows[name] if row["period"] == period]) for period in periods}
        segments, runner_segments = _model_diagnostics(race_rows[name], runner_rows[name])
        summaries[name] = {"model_version": models[name], "metrics": metrics, "by_period": by_period,
                           "coverage": {"eligible_races": len(race_rows[name]), "runners": len(runner_rows[name]),
                                        "unrated_runners": sum(row["history_depth"] == 0 for row in runner_rows[name])},
                           "segments": segments, "runner_segments": runner_segments,
                           "calibration": _calibration(runner_rows[name], protocol["metrics"]["calibration_edges"])}
    candidates = {}
    for offset, name in enumerate(candidates_to_test):
        intervals = {period: paired_interval([row for row in paired[name] if row["period"] == period], reps,
            float(sampling["confidence_level"]), int(sampling["seed"]) + offset) for period in periods}
        period_comparison = {}
        for period in periods:
            candidate = summaries[name]["by_period"][period]; baseline = summaries["v1"]["by_period"][period]
            period_comparison[period] = {**candidate, "baseline_mean_log_loss": baseline["mean_log_loss"],
                "log_loss_delta": (candidate["mean_log_loss"] - baseline["mean_log_loss"])
                if candidate["mean_log_loss"] is not None and baseline["mean_log_loss"] is not None else None}
        decision, reasons = _candidate_decision(period_comparison.get("validation", {}),
            period_comparison.get("historical_holdout", {}), intervals.get("validation", {}))
        candidates[name] = {**summaries[name], "period_comparison": period_comparison,
                            "paired_log_loss_intervals": intervals, "decision": decision, "reasons": reasons}
    report = {"report_name": report_name, "protocol_version": protocol["protocol_version"],
              "protocol_hash": digest, "periods": list(periods), "database_cutoff": max(dates) if dates else None,
              "baseline": summaries["v1"], "candidates": candidates,
              "common_sample": {"same_runner_sets": True, "eligible_races": len(race_rows["v1"]),
                                "excluded_races": sum(exclusions.values()), "exclusion_reasons": dict(sorted(exclusions.items()))},
              "resampling": {**sampling, "repetitions": reps},
              "no_lookahead": {"state_cutoff": "race_date exclusive", "same_day_results_used": False},
              "candidate_key_modes": key_modes, "generated_at": now}
    store.connection.execute(
        """INSERT INTO benchmark_reports (protocol_hash,model_version,report_name,database_cutoff,report_json,created_at)
           VALUES (?,?,?,?,?,?) ON CONFLICT(protocol_hash,model_version,report_name) DO UPDATE SET
             database_cutoff=excluded.database_cutoff,report_json=excluded.report_json,created_at=excluded.created_at""",
        (digest, "+".join(candidates_to_test), report["report_name"], report["database_cutoff"] or "",
         json.dumps(report, sort_keys=True), now))
    store.connection.commit(); return report


def render_markdown(report: dict[str, Any]) -> str:
    lines = [f"# {report['report_name']}", "",
             f"Protocol: `{report['protocol_version']}` (`{report['protocol_hash']}`)", "",
             "| Candidate | Validation log-loss delta | Holdout delta | 95% validation interval | Decision |",
             "| --- | ---: | ---: | ---: | --- |"]
    for name, candidate in report["candidates"].items():
        validation = candidate["period_comparison"]["validation"]; holdout = candidate["period_comparison"]["historical_holdout"]
        interval = candidate["paired_log_loss_intervals"]["validation"]
        lines.append(f"| {name} | {validation['log_loss_delta']:.6f} | {holdout['log_loss_delta']:.6f} | "
                     f"[{interval['lower']:.6f}, {interval['upper']:.6f}] | {candidate['decision']} |")
    lines += ["", "Negative log-loss differences favour the candidate. No candidate is automatically made official by this report.", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=ROOT / "data" / "racing_engine.sqlite")
    parser.add_argument("--protocol", type=Path, default=ROOT / "config" / "evaluation_protocol_v1.json")
    parser.add_argument("--period", action="append", choices=("train", "validation", "historical_holdout", "prospective_holdout"))
    parser.add_argument("--min-par-sample", type=int, default=5); parser.add_argument("--repetitions", type=int)
    parser.add_argument("--suite", choices=("race_strength", "step11", "winning_margin", "wfa", "weight_response"), default="race_strength")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(); store = RacingStore(args.database)
    try:
        if args.suite == "step11":
            from .step11_models import VARIANTS as STEP11_VARIANTS, build_step11_variants
            report = run_evaluation(store, protocol_path=args.protocol, periods=tuple(args.period or DEFAULT_PERIODS),
                min_par_sample=args.min_par_sample, repetitions=args.repetitions,
                candidate_models=STEP11_VARIANTS, candidate_builder=build_step11_variants,
                candidate_key_modes={name: "raw" for name in STEP11_VARIANTS},
                report_name="daily-variant-weight-promotion-step11")
        elif args.suite == "winning_margin":
            from .winning_margin import MODEL as MARGIN_MODEL, build_candidate
            report = run_evaluation(store, protocol_path=args.protocol, periods=tuple(args.period or DEFAULT_PERIODS),
                min_par_sample=args.min_par_sample, repetitions=args.repetitions,
                candidate_models={"form_anchored_margin": MARGIN_MODEL}, candidate_builder=build_candidate,
                candidate_key_modes={"form_anchored_margin": "durable"},
                report_name="winning-margin-retrospective-diagnostic")
            report["promotion_eligible"] = False
            report["promotion_blocker"] = "candidate designed after historical holdout inspection; prospective evidence required"
        elif args.suite == "wfa":
            from .wfa_research import MODEL as WFA_MODEL, build_candidate
            report = run_evaluation(store, protocol_path=args.protocol, periods=tuple(args.period or DEFAULT_PERIODS),
                min_par_sample=args.min_par_sample, repetitions=args.repetitions,
                candidate_models={"wfa_relative_weight": WFA_MODEL}, candidate_builder=build_candidate,
                candidate_key_modes={"wfa_relative_weight": "durable"},
                report_name="wfa-relative-weight-retrospective-diagnostic")
            report["promotion_eligible"] = False
            report["promotion_blocker"] = "incomplete profiles and retrospective candidate design; prospective evidence required"
        elif args.suite == "weight_response":
            from .weight_response_research import VARIANTS as WEIGHT_VARIANTS, build_candidates
            report = run_evaluation(store, protocol_path=args.protocol, periods=tuple(args.period or DEFAULT_PERIODS),
                min_par_sample=args.min_par_sample, repetitions=args.repetitions,
                candidate_models=WEIGHT_VARIANTS, candidate_builder=build_candidates,
                candidate_key_modes={name:"durable" for name in WEIGHT_VARIANTS},
                report_name="weight-response-retrospective-diagnostic")
            report["promotion_eligible"] = False
            report["promotion_blocker"] = "research candidates developed after historical result inspection; prospective evidence required"
        else:
            report = run_evaluation(store, protocol_path=args.protocol, periods=tuple(args.period or DEFAULT_PERIODS),
                                    min_par_sample=args.min_par_sample, repetitions=args.repetitions)
    finally:
        store.close()
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(rendered)
        args.output.with_suffix(".md").write_text(render_markdown(report))
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
