"""Step 8E: point-in-time NFL venue context and walk-forward ablations."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

from .baselines import _metrics, fit_ridge, model_frame


ROOT = Path(__file__).resolve().parents[2]
FEATURES = ROOT / "data/nfl/features/weekly_epa.parquet"
SCHEDULES = ROOT / "data/nfl/schedules/games.csv"
PREDICTIONS = ROOT / "data/nfl/predictions/step8_t4_venue_ablations.csv"
REPORT = ROOT / "ml/nfl/reports/step8_t4_venue.json"

MARGIN_VENUE = ["neutral_site", "stadium_familiarity_diff"]
TOTAL_VENUE = [
    "neutral_site", "roof_dome", "roof_closed", "roof_open", "surface_grass",
    "stadium_familiarity_sum",
]


def venue_features(schedule: pd.DataFrame) -> pd.DataFrame:
    """Create familiarity counts before updating with the current game."""
    ordered = schedule.sort_values(["gameday", "gametime", "game_id"]).copy()
    experience: defaultdict[tuple[str, str], int] = defaultdict(int)
    rows = []
    for game in ordered.itertuples(index=False):
        stadium = str(game.stadium_id) if pd.notna(game.stadium_id) else str(game.stadium)
        home_prior = experience[(str(game.home_team), stadium)]
        away_prior = experience[(str(game.away_team), stadium)]
        home_log, away_log = np.log1p(home_prior), np.log1p(away_prior)
        roof = str(game.roof).strip().lower()
        surface = str(game.surface).strip().lower()
        rows.append({
            "game_id": game.game_id,
            "neutral_site": int(str(game.location).lower() == "neutral"),
            "roof_dome": int(roof == "dome"), "roof_closed": int(roof == "closed"),
            "roof_open": int(roof == "open"), "surface_grass": int(surface == "grass"),
            "home_stadium_prior_games_log": home_log,
            "away_stadium_prior_games_log": away_log,
            "stadium_familiarity_diff": home_log - away_log,
            "stadium_familiarity_sum": home_log + away_log,
        })
        experience[(str(game.home_team), stadium)] += 1
        experience[(str(game.away_team), stadium)] += 1
    return pd.DataFrame(rows)


def _shuffle(frame: pd.DataFrame, columns: list[str], seed: int) -> pd.DataFrame:
    values = frame.groupby("season", group_keys=False)[columns].sample(frac=1.0, random_state=seed)
    values = values.reset_index(drop=True)
    values.index = frame.index
    return values


def run_audit() -> tuple[pd.DataFrame, dict]:
    games = pd.read_parquet(FEATURES)
    schedule = pd.read_csv(SCHEDULES)
    regular = schedule[schedule.game_type.eq("REG")].copy()
    venues = venue_features(regular)
    games = games.merge(venues, on="game_id", how="left", validate="one_to_one")
    development = games[games.season.between(2014, 2024)].sort_values(["season", "week", "game_id"]).copy()
    design = pd.concat([model_frame(development), development[MARGIN_VENUE + [c for c in TOTAL_VENUE if c not in MARGIN_VENUE]].fillna(0.0)], axis=1)
    shuffled_margin = _shuffle(development.assign(**{c: development[c].fillna(0.0) for c in MARGIN_VENUE}), MARGIN_VENUE, 20260841)
    shuffled_total = _shuffle(development.assign(**{c: development[c].fillna(0.0) for c in TOTAL_VENUE}), TOTAL_VENUE, 20260842)
    shuffled_margin_names, shuffled_total_names = [], []
    for column in MARGIN_VENUE:
        name = f"shuffled_margin_{column}"; design[name] = shuffled_margin[column].to_numpy(); shuffled_margin_names.append(name)
    for column in TOTAL_VENUE:
        name = f"shuffled_total_{column}"; design[name] = shuffled_total[column].to_numpy(); shuffled_total_names.append(name)
    margin_base = [c for c in design if c.startswith("diff_")] + ["rest_diff", "div_game", "week"]
    total_base = [c for c in design if c.startswith("sum_")] + [
        "rest_sum", "div_game", "week", "dynamic_kickoff_rule", "onside_anytime_when_trailing",
        "kickoff_touchback_to_35", "regular_season_ot_both_possess", "onside_2026_alignment_rule",
    ]
    families = {
        "margin": {"t1_core": margin_base, "t1_plus_t4a": margin_base + MARGIN_VENUE,
                   "t1_plus_shuffled_t4a": margin_base + shuffled_margin_names},
        "total": {"t1_core": total_base, "t1_plus_t4a": total_base + TOTAL_VENUE,
                  "t1_plus_shuffled_t4a": total_base + shuffled_total_names},
    }
    folds = []
    for season in range(2019, 2025):
        train, test = development.season.lt(season), development.season.eq(season)
        fold = development.loc[test, ["game_id", "season", "week", "margin", "total", "spread_home_close", "total_line_close"]].copy()
        for target, target_families in families.items():
            for name, columns in target_families.items():
                model = fit_ridge(design[train], development.loc[train, target], columns, alpha=25.0)
                fold[f"{target}_{name}"] = model.predict(design[test])
        folds.append(fold)
    predictions = pd.concat(folds, ignore_index=True)
    metrics = {target: {
        name: _metrics(predictions[target], predictions[f"{target}_{name}"])
        for name in target_families
    } for target, target_families in families.items()}
    to_closing_market = {
        "margin": {
            name: _metrics(-predictions.spread_home_close, predictions[f"margin_{name}"])
            for name in families["margin"]
        },
        "total": {
            name: _metrics(predictions.total_line_close, predictions[f"total_{name}"])
            for name in families["total"]
        },
    }
    stability = {}
    for target, target_families in families.items():
        stability[target] = {}
        for name in target_families:
            gains = []
            for _, rows in predictions.groupby("season"):
                core = _metrics(rows[target], rows[f"{target}_t1_core"])["mae"]
                candidate = _metrics(rows[target], rows[f"{target}_{name}"])["mae"]
                gains.append(core - candidate)
            stability[target][name] = {
                "overall_mae_gain_vs_t1": metrics[target]["t1_core"]["mae"] - metrics[target][name]["mae"],
                "seasons_better_than_t1": sum(gain > 0 for gain in gains), "seasons_tested": len(gains),
                "worst_season_gain": min(gains), "best_season_gain": max(gains),
            }
    report = {
        "status": "t4a_historical_shadow_audit_only", "games": len(predictions),
        "test_seasons": list(range(2019, 2025)), "vault_2025_predictions": 0,
        "coverage": {"stadium": 1.0, "location": 1.0, "roof": 1.0,
                     "surface": float(regular[regular.season.between(2014, 2025)].surface.notna().mean())},
        "features": {"margin": MARGIN_VENUE, "total": TOTAL_VENUE},
        "metrics": metrics, "to_closing_market": to_closing_market, "stability": stability,
        "travel": "not_tested_no_historical_coordinates_or_distance_in_current_store",
        "restrictions": ["venue familiarity uses only prior games", "weather observations excluded",
                         "T4A remains shadow", "no manual venue points authorised"],
    }
    return predictions, report


def main() -> None:
    predictions, report = run_audit()
    PREDICTIONS.parent.mkdir(parents=True, exist_ok=True); REPORT.parent.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(PREDICTIONS, index=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "games": report["games"],
                      "metrics": report["metrics"], "stability": report["stability"]}, indent=2))


if __name__ == "__main__":
    main()
