"""Step 8A: leakage-safe historical audit for NFL T2 and T3.

T2 contains quarterback and reported-availability information. T3 contains
roster/unit continuity. This script evaluates each family separately, together,
and against within-season shuffled controls. The 2025 vault is never fitted or
scored here.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .baselines import _metrics, fit_ridge, model_frame
from .phase3 import CONTINUITY_COLUMNS, INJURY_COLUMNS, QB_COLUMNS


ROOT = Path(__file__).resolve().parents[2]
FEATURES = ROOT / "data/nfl/features/weekly_epa.parquet"
PERSONNEL = ROOT / "data/nfl/features/personnel_context.parquet"
PREDICTIONS = ROOT / "data/nfl/predictions/step8_tier_ablations.csv"
REPORT = ROOT / "ml/nfl/reports/step8_tier_audit.json"


def _shuffle_within_season(
    frame: pd.DataFrame, columns: list[str], *, seed: int
) -> pd.DataFrame:
    shuffled = frame.groupby("season", group_keys=False)[columns].sample(
        frac=1.0, random_state=seed
    ).reset_index(drop=True)
    shuffled.index = frame.index
    return shuffled


def run_audit() -> tuple[pd.DataFrame, dict]:
    personnel = pd.read_parquet(PERSONNEL).drop(
        columns=["season", "week", "home_team", "away_team", "roof", "surface"]
    )
    games = pd.read_parquet(FEATURES).merge(
        personnel, on="game_id", how="left", validate="one_to_one"
    )
    development = games[games.season.between(2014, 2024)].sort_values(
        ["season", "week", "game_id"]
    ).copy()
    core = model_frame(development)
    extras = development[QB_COLUMNS + INJURY_COLUMNS + CONTINUITY_COLUMNS].astype(float).fillna(0.0)
    design = pd.concat([core, extras], axis=1)
    base = [column for column in core if column.startswith("diff_")] + ["rest_diff", "div_game", "week"]

    shuffled_families = {
        "shuffled_t2": (QB_COLUMNS + INJURY_COLUMNS, 20260831),
        "shuffled_t3": (CONTINUITY_COLUMNS, 20260832),
    }
    shuffled_names: dict[str, list[str]] = {}
    shuffle_source = pd.concat([development[["season"]], extras], axis=1)
    for family, (columns, seed) in shuffled_families.items():
        values = _shuffle_within_season(shuffle_source, columns, seed=seed)
        names = []
        for column in columns:
            name = f"{family}_{column}"
            design[name] = values[column].to_numpy()
            names.append(name)
        shuffled_names[family] = names

    families = {
        "t1_core": base,
        "t1_plus_t2_qb": base + QB_COLUMNS,
        "t1_plus_t2_injuries": base + INJURY_COLUMNS,
        "t1_plus_t2": base + QB_COLUMNS + INJURY_COLUMNS,
        "t1_plus_t3": base + CONTINUITY_COLUMNS,
        "t1_plus_t2_t3": base + QB_COLUMNS + INJURY_COLUMNS + CONTINUITY_COLUMNS,
        "t1_plus_shuffled_t2": base + shuffled_names["shuffled_t2"],
        "t1_plus_shuffled_t3": base + shuffled_names["shuffled_t3"],
    }

    folds = []
    for season in range(2019, 2025):
        train, test = development.season < season, development.season.eq(season)
        fold = development.loc[test, ["game_id", "season", "week", "margin", "spread_home_close"]].copy()
        for name, columns in families.items():
            model = fit_ridge(design[train], development.loc[train, "margin"], columns, alpha=25.0)
            fold[name] = model.predict(design[test])
        folds.append(fold)
    predictions = pd.concat(folds, ignore_index=True)

    overall = {name: _metrics(predictions.margin, predictions[name]) for name in families}
    to_close = {
        name: _metrics(-predictions.spread_home_close, predictions[name]) for name in families
    }
    by_season: dict[str, dict] = {}
    for season, rows in predictions.groupby("season"):
        season_metrics = {name: _metrics(rows.margin, rows[name]) for name in families}
        core_mae = season_metrics["t1_core"]["mae"]
        by_season[str(int(season))] = {
            name: {**metrics, "mae_gain_vs_t1": core_mae - metrics["mae"]}
            for name, metrics in season_metrics.items()
        }

    core_mae = overall["t1_core"]["mae"]
    stability = {}
    for name in families:
        gains = [by_season[str(season)][name]["mae_gain_vs_t1"] for season in range(2019, 2025)]
        stability[name] = {
            "overall_mae_gain_vs_t1": core_mae - overall[name]["mae"],
            "seasons_better_than_t1": sum(gain > 0 for gain in gains),
            "seasons_tested": len(gains),
            "worst_season_gain": min(gains),
            "best_season_gain": max(gains),
        }

    report = {
        "status": "historical_shadow_audit_only",
        "development_seasons": [2014, 2024],
        "test_seasons": list(range(2019, 2025)),
        "vault_2025_predictions": 0,
        "games": len(predictions),
        "tier_definition": {
            "t2": "quarterback posterior plus position-weighted reported availability",
            "t3": "weekly and prior-season roster, offensive-line and receiver continuity",
        },
        "margin": overall,
        "to_closing_spread": to_close,
        "stability": stability,
        "by_season": by_season,
        "restrictions": [
            "historical actual starter is an oracle and cannot be used as a live starter forecast",
            "injuries are final-report and position weighted, not snap-value weighted",
            "2025 injury feed lacks date_modified and is excluded from this development audit",
            "no tier point adjustment or betting promotion is authorised by this audit",
        ],
    }
    return predictions, report


def main() -> None:
    predictions, report = run_audit()
    PREDICTIONS.parent.mkdir(parents=True, exist_ok=True)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(PREDICTIONS, index=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"], "games": report["games"],
        "margin": report["margin"], "stability": report["stability"],
    }, indent=2))


if __name__ == "__main__":
    main()
