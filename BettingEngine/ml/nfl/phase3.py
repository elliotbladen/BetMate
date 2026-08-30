"""Walk-forward ablations for NFL personnel and context shadow tiers."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .baselines import MARGIN_STATS, _metrics, fit_ridge, model_frame


QB_COLUMNS = [
    "diff_qb_epa_posterior", "diff_qb_success_posterior",
    "diff_qb_sack_rate_posterior", "diff_qb_turnover_rate_posterior",
    "diff_qb_scramble_rate_posterior", "diff_qb_prior_dropbacks", "diff_qb_change",
]
CONTINUITY_COLUMNS = [
    "diff_weekly_roster_continuity", "diff_returning_roster_share",
    "diff_returning_ol_share", "diff_returning_receiver_share",
]
INJURY_COLUMNS = [
    "diff_injury_burden", "diff_players_out", "diff_players_questionable",
    "diff_injury_report_rows",
]


def run_phase3(
    feature_path: str = "data/nfl/features/weekly_epa.parquet",
    personnel_path: str = "data/nfl/features/personnel_context.parquet",
) -> tuple[pd.DataFrame, dict]:
    games = pd.read_parquet(feature_path).merge(
        pd.read_parquet(personnel_path).drop(columns=["season", "week", "home_team", "away_team", "roof", "surface"]),
        on="game_id", how="left", validate="one_to_one",
    )
    development = games[games.season <= 2024].sort_values(["season", "week", "game_id"]).copy()
    core = model_frame(development)
    extras = development[QB_COLUMNS + CONTINUITY_COLUMNS + INJURY_COLUMNS].astype(float).fillna(0.0)
    design = pd.concat([core, extras], axis=1)
    # Deterministic within-season negative control: it preserves each feature's
    # distribution while destroying its connection to the correct game.
    shuffled_qb = development.groupby("season", group_keys=False)[QB_COLUMNS].sample(
        frac=1.0, random_state=202603
    ).reset_index(drop=True)
    shuffled_qb.index = design.index
    shuffled_columns = []
    for column in QB_COLUMNS:
        shuffled = f"shuffled_{column}"
        design[shuffled] = shuffled_qb[column].to_numpy()
        shuffled_columns.append(shuffled)
    base_columns = [c for c in core if c.startswith("diff_")] + ["rest_diff", "div_game", "week"]
    families = {
        "core": base_columns,
        "core_plus_qb": base_columns + QB_COLUMNS,
        "core_plus_shuffled_qb": base_columns + shuffled_columns,
        "core_plus_continuity": base_columns + CONTINUITY_COLUMNS,
        "core_plus_injuries": base_columns + INJURY_COLUMNS,
        "core_plus_qb_continuity": base_columns + QB_COLUMNS + CONTINUITY_COLUMNS,
        "core_plus_all_personnel": base_columns + QB_COLUMNS + CONTINUITY_COLUMNS + INJURY_COLUMNS,
    }
    outputs = []
    for season in range(2019, 2025):
        train = development.season < season
        test = development.season == season
        fold = development.loc[test, ["game_id", "season", "margin", "spread_home_close"]].copy()
        for name, columns in families.items():
            model = fit_ridge(design[train], development.loc[train, "margin"], columns)
            fold[name] = model.predict(design[test])
        outputs.append(fold)
    predictions = pd.concat(outputs, ignore_index=True)
    report = {
        "status": "shadow_only",
        "vault_2025_predictions": int((predictions.season == 2025).sum()),
        "games": len(predictions),
        "margin": {name: _metrics(predictions.margin, predictions[name]) for name in families},
        "to_closing_spread": {
            name: _metrics(-predictions.spread_home_close, predictions[name]) for name in families
        },
        "coverage": {
            "qb_starter_id": float(games.home_qb_id.ne("").mean()),
            "weekly_roster_continuity": float(games.home_weekly_roster_continuity.notna().mean()),
            "returning_roster_share": float(games.home_returning_roster_share.notna().mean()),
            "injury_report": float(games.home_injury_report_rows.notna().mean()),
        },
        "weather": "diagnostic_only_no_historical_forecast_capture_timestamp",
        "injuries": "shadow_position_weighted_final_report; snap_weighting_not_available",
    }
    return predictions, report


if __name__ == "__main__":
    predictions, report = run_phase3()
    Path("data/nfl/predictions").mkdir(parents=True, exist_ok=True)
    predictions.to_csv("data/nfl/predictions/step3_ablations.csv", index=False)
    Path("ml/nfl/reports/step3_personnel_context.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))
