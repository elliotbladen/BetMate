"""Chronological, no-look-ahead evaluation for the internal rating spine."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from .performance import MODEL_VERSION, run_pipeline, utc_now
from .ratings import horse_key, softmax
from .storage import RacingStore


def walk_forward(store: RacingStore, end_date: str, *, min_par_sample: int = 5,
                 model_version: str = MODEL_VERSION) -> dict[str, float | int]:
    """Score each date using only the rating state available before that date."""
    dates = [row[0] for row in store.connection.execute(
        "SELECT DISTINCT race_date FROM race_results WHERE race_date < ? ORDER BY race_date", (end_date,)
    )]
    total_brier = total_log_loss = 0.0
    races_scored = runners_scored = 0
    for race_date in dates:
        # This rebuilds pars and states using < race_date only.  It is slower
        # than an in-sample report by design: future information is forbidden.
        run_pipeline(store, race_date, min_par_sample=min_par_sample, model_version=model_version)
        states = {
            row["horse_key"]: float(row["overall_rating"])
            for row in store.connection.execute(
                "SELECT horse_key, overall_rating FROM horse_rating_states WHERE model_version = ? AND as_of_date = ?",
                (model_version, race_date),
            )
        }
        races = store.connection.execute(
            "SELECT source, track_slug, race_number FROM race_results WHERE race_date = ?", (race_date,)
        ).fetchall()
        for race in races:
            runners = store.connection.execute(
                """SELECT runner_name, finish_position FROM runner_results
                     WHERE source = ? AND race_date = ? AND track_slug = ? AND race_number = ?
                       AND result_status = 'finished' AND finish_position IS NOT NULL
                     ORDER BY runner_number""",
                (race["source"], race_date, race["track_slug"], race["race_number"]),
            ).fetchall()
            winner_count = sum(1 for runner in runners if runner["finish_position"] == 1)
            if len(runners) < 2 or winner_count != 1:
                continue
            probabilities = softmax([states.get(horse_key(row["runner_name"]), 100.0) for row in runners])
            for runner, probability in zip(runners, probabilities):
                outcome = 1.0 if runner["finish_position"] == 1 else 0.0
                total_brier += (probability - outcome) ** 2
                if outcome:
                    total_log_loss += -math.log(max(probability, 1e-12))
            races_scored += 1
            runners_scored += len(runners)
    result = {
        "races_scored": races_scored,
        "runners_scored": runners_scored,
        "mean_brier": total_brier / runners_scored if runners_scored else None,
        "mean_log_loss": total_log_loss / races_scored if races_scored else None,
    }
    store.connection.execute(
        """INSERT INTO evaluation_runs (model_version, as_of_date, evaluation_name, races_scored, runners_scored, mean_brier, mean_log_loss, detail_json, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(model_version, as_of_date, evaluation_name) DO UPDATE SET
             races_scored=excluded.races_scored, runners_scored=excluded.runners_scored,
             mean_brier=excluded.mean_brier, mean_log_loss=excluded.mean_log_loss,
             detail_json=excluded.detail_json, created_at=excluded.created_at""",
        (model_version, end_date, "walk-forward-v1", races_scored, runners_scored,
         result["mean_brier"], result["mean_log_loss"],
         json.dumps({"cutoff": end_date, "min_par_sample": min_par_sample, "no_lookahead": True}, sort_keys=True), utc_now()),
    )
    store.connection.commit()
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--end-date", required=True, help="Exclusive YYYY-MM-DD cutoff")
    parser.add_argument("--min-par-sample", type=int, default=5)
    args = parser.parse_args()
    store = RacingStore(Path(__file__).resolve().parents[1] / "data" / "racing_engine.sqlite")
    try:
        print(json.dumps(walk_forward(store, args.end_date, min_par_sample=args.min_par_sample), sort_keys=True))
    finally:
        store.close()


if __name__ == "__main__":
    main()
