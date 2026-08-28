"""First controlled V2.1 Horse Ability candidate.

The accepted ``form-first-v2.0`` run performances are immutable inputs.  This
module converts only prior runs into point-in-time Horse Ability states and
evaluates them chronologically.  It does not use market prices or race-day map,
barrier, weather, jockey or trainer inputs.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Callable

from .evaluation_protocol import load_protocol, period_for, protocol_hash, score_race
from .horse_identity import identity_key
from .promotion_evaluation import paired_interval
from .storage import RacingStore, utc_now
from .v2_ratings import MODEL_VERSION as RUN_MODEL_VERSION


ROOT = Path(__file__).resolve().parents[1]
ABILITY_VERSION = "horse-ability-v2.1-sustainable-recency-shadow"
REJECTED_V2_BASELINE = "form-first-v2.0-median-last-three-rejected"
V1_BASELINE = "performance-par-v1.0-median-last-three"
WINDOW_RUNS = 6
RECENCY_HALF_LIFE_DAYS = 180.0
SUSTAINABLE_PEAK_BLEND = 0.35
RELIABILITY_PRIOR_RUNS = 2.0
NEUTRAL = 100.0
TEMPERATURES = (3.0, 5.0, 8.0, 10.0, 12.0, 15.0, 20.0, 30.0, 40.0, 60.0)


@dataclass(frozen=True)
class AbilityState:
    ability_rating: float
    recency_rating: float
    sustainable_peak: float
    uncertainty: float
    rated_runs: int
    last_run_date: str | None


def _weighted_mean(values: list[float], weights: list[float]) -> float:
    return sum(value * weight for value, weight in zip(values, weights)) / sum(weights)


def ability_state(history: list[tuple[str, float]], as_of_date: str) -> AbilityState:
    """Build a state using only runs strictly before ``as_of_date``."""
    prior = [(day, rating) for day, rating in history if day < as_of_date]
    if not prior:
        return AbilityState(NEUTRAL, NEUTRAL, NEUTRAL, 12.0, 0, None)

    recent = prior[-WINDOW_RUNS:]
    cutoff = date.fromisoformat(as_of_date)
    values = [float(rating) for _, rating in recent]
    weights = [
        math.exp(
            -math.log(2.0)
            * max(0, (cutoff - date.fromisoformat(day)).days)
            / RECENCY_HALF_LIFE_DAYS
        )
        for day, _ in recent
    ]
    recency = _weighted_mean(values, weights)
    sustainable_peak = statistics.mean(sorted(values, reverse=True)[: min(2, len(values))])
    repeatability = min(1.0, len(values) / 3.0)
    raw = recency + SUSTAINABLE_PEAK_BLEND * repeatability * (sustainable_peak - recency)
    reliability = len(prior) / (len(prior) + RELIABILITY_PRIOR_RUNS)
    ability = NEUTRAL + reliability * (raw - NEUTRAL)
    median = statistics.median(values)
    mad = statistics.median(abs(value - median) for value in values)
    uncertainty = max(2.0, 10.0 / math.sqrt(len(prior)) + 0.50 * mad)
    return AbilityState(ability, recency, sustainable_peak, uncertainty, len(prior), prior[-1][0])


def rejected_v2_state(history: list[tuple[str, float]], as_of_date: str) -> float:
    values = [float(rating) for day, rating in history if day < as_of_date]
    return statistics.median(values[-3:]) if values else NEUTRAL


def probabilities(ratings: list[float], temperature: float) -> list[float]:
    scaled = [rating / temperature for rating in ratings]
    peak = max(scaled)
    exponentials = [math.exp(max(-40.0, min(40.0, value - peak))) for value in scaled]
    total = sum(exponentials)
    return [value / total for value in exponentials]


def schema(store: RacingStore) -> None:
    store.connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS v2_horse_ability_states (
          model_version TEXT NOT NULL,
          race_id TEXT NOT NULL,
          runner_number INTEGER NOT NULL,
          horse_key TEXT NOT NULL,
          horse_name TEXT NOT NULL,
          ability_rating REAL NOT NULL,
          recency_rating REAL NOT NULL,
          sustainable_peak REAL NOT NULL,
          uncertainty REAL NOT NULL,
          rated_runs INTEGER NOT NULL,
          last_run_date TEXT,
          information_cutoff TEXT NOT NULL,
          detail_json TEXT NOT NULL,
          created_at TEXT NOT NULL,
          PRIMARY KEY (model_version, race_id, runner_number)
        );
        """
    )


def _v1_history(store: RacingStore) -> dict[str, list[tuple[str, float]]]:
    histories: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for row in store.connection.execute(
        """SELECT race_date,horse_name,performance_rating
             FROM run_performances
            WHERE model_version='performance-par-v1.0'
            ORDER BY race_date"""
    ):
        histories[identity_key(row["horse_name"])].append(
            (row["race_date"], float(row["performance_rating"]))
        )
    return histories


def _performance_rows(store: RacingStore, model_version: str) -> list[Any]:
    if model_version == RUN_MODEL_VERSION:
        return store.connection.execute(
            """SELECT p.*,r.race_date FROM v2_run_performances p
                 JOIN v2_clean_races r ON r.race_id=p.race_id
                WHERE p.model_version=? ORDER BY r.race_date,p.race_id,p.runner_number""",
            (model_version,),).fetchall()
    return store.connection.execute(
        """SELECT p.*,p.achieved_rating performance_rating,r.race_date
             FROM v2_achieved_run_candidates p JOIN v2_clean_races r ON r.race_id=p.race_id
            WHERE p.model_version=? ORDER BY r.race_date,p.race_id,p.runner_number""",
        (model_version,),).fetchall()


def build_point_in_time_examples(store: RacingStore, protocol: dict[str, Any], *,
                                 run_model_version: str = RUN_MODEL_VERSION,
                                 ability_version: str = ABILITY_VERSION,
                                 state_builder: Callable[[list[tuple[str, float]], str], AbilityState] = ability_state) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Materialise pre-race states without same-day or future leakage."""
    schema(store)
    store.connection.execute(
        "DELETE FROM v2_horse_ability_states WHERE model_version=?", (ability_version,)
    )
    v1_histories = _v1_history(store)
    v2_histories: dict[str, list[tuple[str, float]]] = defaultdict(list)
    rejected_histories: dict[str, list[tuple[str, float]]] = defaultdict(list)
    performance_by_race: dict[str, list[Any]] = defaultdict(list)
    for row in _performance_rows(store, run_model_version):
        performance_by_race[row["race_id"]].append(row)
    rejected_by_race: dict[str, list[Any]] = defaultdict(list)
    for row in _performance_rows(store, RUN_MODEL_VERSION):
        rejected_by_race[row["race_id"]].append(row)

    races_by_date: dict[str, list[Any]] = defaultdict(list)
    for race in store.connection.execute(
        "SELECT * FROM v2_clean_races ORDER BY race_date,track_slug,race_number"
    ):
        races_by_date[race["race_date"]].append(race)

    examples: list[dict[str, Any]] = []
    exclusions = Counter()
    created_at = utc_now()
    for race_date in sorted(races_by_date):
        # Score the entire meeting day before adding any performances from that
        # date. This prevents later races from seeing same-day results.
        for race in races_by_date[race_date]:
            runners = store.connection.execute(
                """SELECT * FROM v2_clean_runner_results
                    WHERE race_id=? AND result_status='finished'
                      AND finish_position IS NOT NULL
                    ORDER BY runner_number""",
                (race["race_id"],),
            ).fetchall()
            state_rows = []
            for runner in runners:
                key = runner["horse_key"]
                state = state_builder(v2_histories[key], race_date)
                v1_values = [rating for day, rating in v1_histories[key] if day < race_date]
                state_rows.append(
                    {
                        "runner_number": int(runner["runner_number"]),
                        "horse_key": key,
                        "horse_name": runner["horse_name"],
                        "finish_position": int(runner["finish_position"]),
                        "ability": state.ability_rating,
                        "rejected_v2": rejected_v2_state(rejected_histories[key], race_date),
                        "v1": statistics.median(v1_values[-3:]) if v1_values else NEUTRAL,
                        "state": state,
                    }
                )
                store.connection.execute(
                    """INSERT INTO v2_horse_ability_states VALUES
                       (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        ability_version,
                        race["race_id"],
                        runner["runner_number"],
                        key,
                        runner["horse_name"],
                        state.ability_rating,
                        state.recency_rating,
                        state.sustainable_peak,
                        state.uncertainty,
                        state.rated_runs,
                        state.last_run_date,
                        race_date,
                        json.dumps(
                            {
                                "window_runs": WINDOW_RUNS,
                                "recency_half_life_days": RECENCY_HALF_LIFE_DAYS,
                                "sustainable_peak_blend": SUSTAINABLE_PEAK_BLEND,
                                "reliability_prior_runs": RELIABILITY_PRIOR_RUNS,
                                "same_day_results_used": False,
                            },
                            sort_keys=True,
                        ),
                        created_at,
                    ),
                )

            if len(state_rows) < 4:
                exclusions["insufficient_starters"] += 1
                continue
            winners = [index for index, row in enumerate(state_rows) if row["finish_position"] == 1]
            if len(winners) != 1:
                exclusions["invalid_winner_count"] += 1
                continue
            period = period_for(race_date, protocol)
            if period is None:
                exclusions["outside_protocol"] += 1
                continue
            examples.append(
                {
                    "race_id": race["race_id"],
                    "race_date": race_date,
                    "period": period,
                    "source": race["source"],
                    "state": race["state"],
                    "track_slug": race["track_slug"],
                    "race_number": int(race["race_number"]),
                    "distance_metres": race["distance_metres"],
                    "class_family": race["class_family"],
                    "winner": winners[0],
                    "runners": state_rows,
                }
            )

        for race in races_by_date[race_date]:
            for performance in performance_by_race.get(race["race_id"], []):
                v2_histories[performance["horse_key"]].append(
                    (race_date, float(performance["performance_rating"]))
                )
            for performance in rejected_by_race.get(race["race_id"], []):
                rejected_histories[performance["horse_key"]].append(
                    (race_date, float(performance["performance_rating"]))
                )
    store.connection.commit()
    return examples, dict(exclusions)


def _mean_loss(examples: list[dict[str, Any]], field: str, temperature: float) -> float:
    losses = []
    for race in examples:
        probs = probabilities([runner[field] for runner in race["runners"]], temperature)
        losses.append(-math.log(max(probs[race["winner"]], 1e-12)))
    return statistics.mean(losses)


def fit_temperature(examples: list[dict[str, Any]], field: str) -> dict[str, Any]:
    trials = [
        {"temperature": temperature, "training_log_loss": _mean_loss(examples, field, temperature)}
        for temperature in TEMPERATURES
    ]
    selected = min(trials, key=lambda row: row["training_log_loss"])
    return {"selected": selected["temperature"], "trials": trials}


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"races": 0}
    return {
        "races": len(rows),
        "mean_log_loss": statistics.mean(row["log_loss"] for row in rows),
        "mean_race_brier": statistics.mean(row["race_brier"] for row in rows),
        "mean_winner_rank": statistics.mean(row["winner_rank"] for row in rows),
        "top_1": statistics.mean(row["winner_rank"] == 1 for row in rows),
        "top_3": statistics.mean(row["winner_rank"] <= 3 for row in rows),
    }


def evaluate(
    examples: list[dict[str, Any]],
    protocol: dict[str, Any],
    temperatures: dict[str, float],
) -> dict[str, Any]:
    model_fields = {
        "candidate": "ability",
        "rejected_v2": "rejected_v2",
        "v1": "v1",
    }
    scored: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for race in examples:
        outcomes = [int(index == race["winner"]) for index in range(len(race["runners"]))]
        common = {
            key: race[key]
            for key in ("race_id", "race_date", "period", "source", "state", "track_slug", "race_number")
        }
        for name, field in model_fields.items():
            probs = probabilities(
                [runner[field] for runner in race["runners"]], temperatures[name]
            )
            scored[name].append({**common, **score_race(probs, outcomes, protocol)})
        uniform = [1.0 / len(outcomes)] * len(outcomes)
        scored["uniform"].append({**common, **score_race(uniform, outcomes, protocol)})

    results: dict[str, Any] = {}
    seed = int(protocol["resampling"]["seed"])
    for period in protocol["periods"]:
        results[period] = {}
        candidate_rows = [row for row in scored["candidate"] if row["period"] == period]
        results[period]["candidate"] = _summary(candidate_rows)
        for offset, baseline in enumerate(("rejected_v2", "v1", "uniform")):
            baseline_rows = [row for row in scored[baseline] if row["period"] == period]
            results[period][baseline] = _summary(baseline_rows)
            paired = []
            for candidate, comparator in zip(candidate_rows, baseline_rows):
                paired.append(
                    {
                        "race_date": candidate["race_date"],
                        "source": candidate["source"],
                        "track_slug": candidate["track_slug"],
                        "state": candidate["state"],
                        "baseline_log_loss": comparator["log_loss"],
                        "candidate_log_loss": candidate["log_loss"],
                    }
                )
            if paired:
                repetitions = int(protocol["resampling"]["repetitions"])
                interval = paired_interval(
                    paired,
                    repetitions,
                    float(protocol["resampling"]["confidence_level"]),
                    seed + offset,
                )
                interval["interpretation"] = (
                    f"candidate minus {baseline}; negative favours candidate"
                )
                candidate_summary = results[period]["candidate"]
                baseline_summary = results[period][baseline]
                results[period][f"candidate_vs_{baseline}"] = {
                    "log_loss_delta": candidate_summary["mean_log_loss"]
                    - baseline_summary["mean_log_loss"],
                    "race_brier_delta": candidate_summary["mean_race_brier"]
                    - baseline_summary["mean_race_brier"],
                    "top_1_delta": candidate_summary["top_1"] - baseline_summary["top_1"],
                    "paired_log_loss_interval": interval,
                }
    return results


def current_states(store: RacingStore, as_of_date: str, *,
                   run_model_version: str = RUN_MODEL_VERSION,
                   state_builder: Callable[[list[tuple[str, float]], str], AbilityState] = ability_state) -> list[dict[str, Any]]:
    histories: dict[str, list[tuple[str, float]]] = defaultdict(list)
    names: dict[str, str] = {}
    for row in _performance_rows(store, run_model_version):
        if row["race_date"] >= as_of_date:
            continue
        histories[row["horse_key"]].append((row["race_date"], float(row["performance_rating"])))
        names[row["horse_key"]] = row["horse_name"]
    rows = []
    for key, history in histories.items():
        state = state_builder(history, as_of_date)
        rows.append(
            {
                "horse_key": key,
                "horse_name": names[key],
                "ability_rating": state.ability_rating,
                "recency_rating": state.recency_rating,
                "sustainable_peak": state.sustainable_peak,
                "uncertainty": state.uncertainty,
                "rated_runs": state.rated_runs,
                "last_run_date": state.last_run_date,
            }
        )
    return sorted(rows, key=lambda row: row["ability_rating"], reverse=True)


def named_run_audits(store: RacingStore, *, run_model_version: str = RUN_MODEL_VERSION) -> dict[str, Any]:
    if run_model_version == RUN_MODEL_VERSION:
        natural_fling = store.connection.execute(
            """SELECT r.race_date,r.track_slug,r.race_number,p.performance_rating,
                      p.race_strength,p.class_standard,p.anchor_coverage,p.detail_json
                 FROM v2_run_performances p JOIN v2_clean_races r ON r.race_id=p.race_id
                WHERE p.model_version=? AND p.horse_key='naturalfling'
                ORDER BY r.race_date DESC LIMIT 1""", (run_model_version,)).fetchone()
    else:
        natural_fling = store.connection.execute(
            """SELECT r.race_date,r.track_slug,r.race_number,p.achieved_rating performance_rating,
                      p.race_strength,json_extract(p.detail_json,'$.class_standard') class_standard,
                      json_extract(p.detail_json,'$.opposition_evidence.principal_coverage') anchor_coverage,
                      p.detail_json FROM v2_achieved_run_candidates p JOIN v2_clean_races r USING(race_id)
                WHERE p.model_version=? AND p.horse_key='naturalfling'
                ORDER BY r.race_date DESC LIMIT 1""", (run_model_version,)).fetchone()
    latest = dict(natural_fling) if natural_fling else None
    natural_fling_passed = bool(
        latest and 100.0 <= float(latest["performance_rating"]) <= 110.0
    )
    return {
        "natural_fling_group3": {
            "required_range": [100.0, 110.0],
            "latest_run": latest,
            "passed": natural_fling_passed,
            "interpretation": (
                "Hard upstream achieved-performance gate; it is not fitted by this "
                "Horse Ability candidate."
            ),
        }
    }


def run(store: RacingStore, protocol_path: Path, as_of_date: str, *,
        run_model_version: str = RUN_MODEL_VERSION,
        ability_version: str = ABILITY_VERSION,
        report_name: str = "horse-ability-v2.1-first-candidate",
        state_builder: Callable[[list[tuple[str, float]], str], AbilityState] = ability_state) -> dict[str, Any]:
    protocol = load_protocol(protocol_path)
    examples, exclusions = build_point_in_time_examples(store, protocol,
        run_model_version=run_model_version, ability_version=ability_version,
        state_builder=state_builder)
    training = [race for race in examples if race["period"] == "train"]
    fits = {
        "candidate": fit_temperature(training, "ability"),
        "rejected_v2": fit_temperature(training, "rejected_v2"),
        "v1": fit_temperature(training, "v1"),
    }
    temperatures = {name: fit["selected"] for name, fit in fits.items()}
    evaluation = evaluate(examples, protocol, temperatures)
    validation = evaluation["validation"]
    holdout = evaluation["historical_holdout"]
    reasons = []
    for baseline in ("rejected_v2", "v1", "uniform"):
        validation_comparison = validation[f"candidate_vs_{baseline}"]
        holdout_comparison = holdout[f"candidate_vs_{baseline}"]
        if validation_comparison["log_loss_delta"] >= 0:
            reasons.append(f"validation did not beat {baseline}")
        if validation_comparison["paired_log_loss_interval"]["upper"] >= 0:
            reasons.append(f"validation uncertainty includes no improvement vs {baseline}")
        if holdout_comparison["log_loss_delta"] >= 0:
            reasons.append(f"historical holdout did not beat {baseline}")

    current = current_states(store, as_of_date, run_model_version=run_model_version,
                             state_builder=state_builder)
    run_audits = named_run_audits(store, run_model_version=run_model_version)
    upstream_failures = [
        name for name, audit in run_audits.items() if not audit["passed"]
    ]
    named = {
        name: next((row for row in current if row["horse_name"].lower() == name.lower()), None)
        for name in ("Sheza Alibi", "Gringotts", "Autumn Glow", "Natural Fling")
    }
    return {
        "report_name": report_name,
        "model_version": ability_version,
        "run_model_version": run_model_version,
        "as_of_date": as_of_date,
        "protocol_hash": protocol_hash(protocol),
        "specification": {
            "window_runs": WINDOW_RUNS,
            "recency_half_life_days": RECENCY_HALF_LIFE_DAYS,
            "sustainable_peak_blend": SUSTAINABLE_PEAK_BLEND,
            "reliability_prior_runs": RELIABILITY_PRIOR_RUNS,
            "uncertainty": "max(2, 10/sqrt(all_prior_runs) + 0.5*recent_MAD)",
            "fitted_parameters": "probability temperature only; training period only",
            "weight_wfa_policy": "accepted V2 run figures frozen; WFA semantics registered separately",
        },
        "race_counts": dict(Counter(race["period"] for race in examples)),
        "exclusions": exclusions,
        "temperature_fits": fits,
        "evaluation": evaluation,
        "decision": (
            "BLOCKED_UPSTREAM"
            if upstream_failures
            else ("PROMOTION_ELIGIBLE" if not reasons else "REVISE_OR_FREEZE")
        ),
        "reasons": (
            [f"failed mandatory upstream run-rating audit: {name}" for name in upstream_failures]
            + reasons
        ),
        "prospective_warning": (
            "The 2026-08-16 onward period has been observed before this candidate was specified; "
            "it is diagnostic only and not an untouched promotion holdout."
        ),
        "current_top_50": current[:50],
        "named_horses": named,
        "named_run_audits": run_audits,
        "generated_at": utc_now(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=ROOT / "data" / "racing_engine.sqlite")
    parser.add_argument("--protocol", type=Path, default=ROOT / "config" / "evaluation_protocol_v1.json")
    parser.add_argument("--as-of", default="2026-08-23")
    parser.add_argument("--output", type=Path, default=ROOT / "reports" / "v2_ratings" / "horse_ability_v2_1_first_candidate.json")
    args = parser.parse_args()
    store = RacingStore(args.database)
    try:
        report = run(store, args.protocol, args.as_of)
    finally:
        store.close()
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
