"""Create internal shadow fair prices for an imported racecard."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .ratings import MODEL_VERSION, NEUTRAL_RATING, Rating, build_ratings, horse_key, softmax
from .storage import RacingStore, utc_now


ROOT = Path(__file__).resolve().parents[1]


def price_card(store: RacingStore, race_date: str, state: str, model_version: str = MODEL_VERSION) -> list[dict[str, Any]]:
    """Price an already-imported card using ratings strictly before race_date."""
    ratings = build_ratings(store, race_date, model_version)
    races = store.connection.execute(
        """SELECT r.race_date, r.track_slug, r.race_number, r.race_name, r.distance, r.condition, r.race_class
             FROM races r
             JOIN meetings m ON m.source = r.source AND m.race_date = r.race_date AND m.track_slug = r.track_slug
            WHERE r.race_date = ? AND m.state = ?
            ORDER BY r.track_slug, r.race_number""",
        (race_date, state),
    ).fetchall()
    output: list[dict[str, Any]] = []
    now = utc_now()
    for race in races:
        runners = store.connection.execute(
            """SELECT runner_number, runner_name, barrier, weight, form FROM runners
                 WHERE race_date = ? AND track_slug = ? AND race_number = ? AND scratched = 0
                 ORDER BY runner_number""",
            (race["race_date"], race["track_slug"], race["race_number"]),
        ).fetchall()
        if len(runners) < 2:
            continue
        rated = [ratings.get(horse_key(str(runner["runner_name"])), Rating(str(runner["runner_name"]), NEUTRAL_RATING, 0)) for runner in runners]
        probabilities = softmax([rating.effective_rating for rating in rated])
        race_confidence = sum(rating.reliability for rating in rated) / len(rated)
        priced_runners: list[dict[str, Any]] = []
        for runner, rating, probability in zip(runners, rated, probabilities):
            detail = {
                "rating": round(rating.rating, 4), "effective_rating": round(rating.effective_rating, 4),
                "races_rated": rating.races_rated, "reliability": round(rating.reliability, 4),
                "warning": "Shadow only: no track-par, class, weight, barrier or sectional adjustment yet.",
            }
            fair_odds = 1.0 / probability
            store.connection.execute(
                """INSERT INTO fair_prices (model_version, race_date, track_slug, race_number, runner_number, horse_name, win_probability, fair_odds, confidence, detail_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(model_version, race_date, track_slug, race_number, runner_number) DO UPDATE SET
                     horse_name=excluded.horse_name, win_probability=excluded.win_probability, fair_odds=excluded.fair_odds,
                     confidence=excluded.confidence, detail_json=excluded.detail_json, created_at=excluded.created_at""",
                (model_version, race_date, race["track_slug"], race["race_number"], runner["runner_number"], runner["runner_name"], probability, fair_odds, race_confidence, json.dumps(detail, sort_keys=True), now),
            )
            priced_runners.append({
                "number": runner["runner_number"], "name": runner["runner_name"],
                "win_probability": round(probability, 5), "fair_odds": round(fair_odds, 2),
                "rating": round(rating.rating, 2), "reliability": round(rating.reliability, 3),
            })
        output.append({
            "track": race["track_slug"], "race_number": race["race_number"], "race_name": race["race_name"],
            "condition": race["condition"], "race_class": race["race_class"], "confidence": round(race_confidence, 3),
            "runners": priced_runners,
        })
    store.connection.commit()
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", required=True, help="Card date YYYY-MM-DD")
    parser.add_argument("--state", choices=("NSW", "VIC"), required=True)
    parser.add_argument("--output", type=Path, help="Optional JSON output path")
    args = parser.parse_args()
    store = RacingStore(ROOT / "data" / "racing_engine.sqlite")
    try:
        prices = price_card(store, args.date, args.state)
    finally:
        store.close()
    payload = json.dumps({"model_version": MODEL_VERSION, "date": args.date, "state": args.state, "races": prices}, indent=2)
    if args.output:
        args.output.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)


if __name__ == "__main__":
    main()
