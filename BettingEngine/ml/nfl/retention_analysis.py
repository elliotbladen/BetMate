"""Walk-forward comparison of offseason state-retention settings.

This is read-only research.  It rebuilds the shifted EWMA feature table for
each candidate retention value and never changes the frozen prediction card.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .baselines import _metrics, fit_ridge, model_frame
from .features import build_matchup_features, compute_game_stats, load_pbp_season, ewma_features


ROOT = Path(__file__).resolve().parents[2]


def evaluate(retention: float, first_test: int = 2019, last_test: int = 2024) -> dict:
    stats = pd.concat(
        [compute_game_stats(load_pbp_season(year, str(ROOT / "data/nfl/pbp")))
         for year in range(2014, last_test + 1)],
        ignore_index=True,
    )
    ewma = ewma_features(stats, prior_season_retention=retention)
    games = build_matchup_features(
        str(ROOT / "data/nfl/schedules/games.csv"), ewma,
        str(ROOT / "data/nfl/historical_odds/nfl_odds_2014_2025.csv"),
    )
    games = games[games.season.between(2014, last_test)].sort_values(
        ["season", "week", "gameday", "game_id"]
    ).copy()
    rows = []
    for season in range(first_test, last_test + 1):
        seasons = games["season"].astype(int).to_numpy()
        train = seasons < season
        test = seasons == season
        if not test.any():
            continue
        if int(train.sum()) == 0:
            raise RuntimeError(f"no training games before season {season}; feature rebuild is incomplete")
        train = train & games.margin.notna().to_numpy() & games.total.notna().to_numpy()
        x = model_frame(games)
        margin_cols = [c for c in x if c.startswith("diff_")] + ["rest_diff", "div_game", "week"]
        total_cols = [c for c in x if c.startswith("sum_")] + ["rest_sum", "div_game", "week",
            "dynamic_kickoff_rule", "onside_anytime_when_trailing", "kickoff_touchback_to_35",
            "regular_season_ot_both_possess", "onside_2026_alignment_rule"]
        margin_model = fit_ridge(x[train], games.loc[train, "margin"], margin_cols)
        total_model = fit_ridge(x[train], games.loc[train, "total"], total_cols)
        fold = games.loc[test, ["margin", "total", "spread_home_open", "spread_home_close",
                                "total_line_open", "total_line_close"]].copy()
        fold["margin_model"] = margin_model.predict(x[test])
        fold["total_model"] = total_model.predict(x[test])
        rows.append(fold)
    scored = pd.concat(rows, ignore_index=True)
    return {
        "retention": retention,
        "games": len(scored),
        "margin": {
            "model": _metrics(scored.margin, scored.margin_model),
            "opening_market": _metrics(scored.margin, -scored.spread_home_open),
            "closing_market": _metrics(scored.margin, -scored.spread_home_close),
        },
        "total": {
            "model": _metrics(scored.total, scored.total_model),
            "opening_market": _metrics(scored.total, scored.total_line_open),
            "closing_market": _metrics(scored.total, scored.total_line_close),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--retentions", nargs="+", type=float, default=[0.35, 0.5, 0.75, 1.0])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    results = [evaluate(value) for value in args.retentions]
    payload = {"status": "retention_walk_forward_complete", "results": results,
               "selection_rule": "choose only using training-fold results; no 2026 Week 1 outcomes"}
    text = json.dumps(payload, indent=2) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    main()
