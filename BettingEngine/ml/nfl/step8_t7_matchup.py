"""Step 8I: NFL scheme/matchup interaction audit."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .baselines import _metrics, fit_ridge, model_frame


ROOT = Path(__file__).resolve().parents[2]
FEATURES = ROOT / "data/nfl/features/weekly_epa.parquet"
PREDICTIONS = ROOT / "data/nfl/predictions/step8_t7_matchup_ablations.csv"
REPORT = ROOT / "ml/nfl/reports/step8_t7_matchup.json"
FAMILIES = ["pass_epa", "rush_epa", "success_rate", "early_down_epa", "explosive_rate", "sack_rate"]
MARGIN_MATCHUP = [f"matchup_diff_{name}" for name in FAMILIES]
TOTAL_MATCHUP = [f"matchup_sum_{name}" for name in FAMILIES]


def matchup_features(games: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame({"game_id": games.game_id}, index=games.index)
    for name in FAMILIES:
        home = games[f"home_off_{name}"].astype(float) * games[f"away_def_{name}"].astype(float)
        away = games[f"away_off_{name}"].astype(float) * games[f"home_def_{name}"].astype(float)
        out[f"matchup_diff_{name}"] = home - away
        out[f"matchup_sum_{name}"] = home + away
    return out


def _shuffle(frame: pd.DataFrame, columns: list[str], seed: int) -> pd.DataFrame:
    values = frame.groupby("season", group_keys=False)[columns].sample(frac=1.0, random_state=seed).reset_index(drop=True)
    values.index = frame.index
    return values


def run_audit() -> tuple[pd.DataFrame, dict]:
    games = pd.read_parquet(FEATURES)
    games = games.merge(matchup_features(games), on="game_id", validate="one_to_one")
    development = games[games.season.between(2014, 2024)].sort_values(["season", "week", "game_id"]).copy()
    core = model_frame(development)
    extras = development[MARGIN_MATCHUP + TOTAL_MATCHUP].astype(float).fillna(0.0)
    design = pd.concat([core, extras], axis=1)
    source = pd.concat([development[["season"]], extras], axis=1)
    shuffled_margin = _shuffle(source, MARGIN_MATCHUP, 20260871)
    shuffled_total = _shuffle(source, TOTAL_MATCHUP, 20260872)
    shuffled_margin_names, shuffled_total_names = [], []
    for column in MARGIN_MATCHUP:
        name = f"shuffled_{column}"; design[name] = shuffled_margin[column].to_numpy(); shuffled_margin_names.append(name)
    for column in TOTAL_MATCHUP:
        name = f"shuffled_{column}"; design[name] = shuffled_total[column].to_numpy(); shuffled_total_names.append(name)
    margin_base = [c for c in core if c.startswith("diff_")] + ["rest_diff", "div_game", "week"]
    total_base = [c for c in core if c.startswith("sum_")] + [
        "rest_sum", "div_game", "week", "dynamic_kickoff_rule", "onside_anytime_when_trailing",
        "kickoff_touchback_to_35", "regular_season_ot_both_possess", "onside_2026_alignment_rule",
    ]
    models = {
        "margin": {"t1_core": margin_base, "t1_plus_t7": margin_base + MARGIN_MATCHUP,
                   "t1_plus_shuffled_t7": margin_base + shuffled_margin_names},
        "total": {"t1_core": total_base, "t1_plus_t7": total_base + TOTAL_MATCHUP,
                  "t1_plus_shuffled_t7": total_base + shuffled_total_names},
    }
    folds = []
    for season in range(2019, 2025):
        train, test = development.season.lt(season), development.season.eq(season)
        fold = development.loc[test, ["game_id", "season", "week", "margin", "total", "spread_home_close", "total_line_close"]].copy()
        for target, families in models.items():
            for name, columns in families.items():
                model = fit_ridge(design[train], development.loc[train, target], columns, alpha=25.0)
                fold[f"{target}_{name}"] = model.predict(design[test])
        folds.append(fold)
    predictions = pd.concat(folds, ignore_index=True)
    metrics = {target: {name: _metrics(predictions[target], predictions[f"{target}_{name}"])
                        for name in families} for target, families in models.items()}
    to_close = {
        "margin": {name: _metrics(-predictions.spread_home_close, predictions[f"margin_{name}"])
                   for name in models["margin"]},
        "total": {name: _metrics(predictions.total_line_close, predictions[f"total_{name}"])
                  for name in models["total"]},
    }
    stability = {}
    for target, families in models.items():
        stability[target] = {}
        for name in families:
            gains = []
            for _, rows in predictions.groupby("season"):
                core_mae = _metrics(rows[target], rows[f"{target}_t1_core"])["mae"]
                candidate = _metrics(rows[target], rows[f"{target}_{name}"])["mae"]
                gains.append(core_mae - candidate)
            stability[target][name] = {"overall_mae_gain_vs_t1": metrics[target]["t1_core"]["mae"] - metrics[target][name]["mae"],
                                       "seasons_better_than_t1": sum(g > 0 for g in gains), "seasons_tested": len(gains),
                                       "worst_season_gain": min(gains), "best_season_gain": max(gains)}
    report = {"status": "t7_historical_shadow_audit_only", "games": len(predictions),
              "test_seasons": list(range(2019, 2025)), "vault_2025_predictions": 0,
              "features": {"margin": MARGIN_MATCHUP, "total": TOTAL_MATCHUP},
              "metrics": metrics, "to_closing_market": to_close, "stability": stability,
              "restrictions": ["interactions use only pregame rolling team state", "no coach labels or future play calls",
                               "shallow generic tree remains separately rejected", "shadow only"]}
    return predictions, report


def main() -> None:
    predictions, report = run_audit(); PREDICTIONS.parent.mkdir(parents=True, exist_ok=True); REPORT.parent.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(PREDICTIONS, index=False); REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "games": report["games"], "metrics": report["metrics"],
                      "to_closing_market": report["to_closing_market"], "stability": report["stability"]}, indent=2))


if __name__ == "__main__":
    main()
