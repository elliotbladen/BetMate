"""Step 8F: nonlinear NFL rest/schedule walk-forward audit."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .baselines import _metrics, fit_ridge, model_frame


ROOT = Path(__file__).resolve().parents[2]
FEATURES = ROOT / "data/nfl/features/weekly_epa.parquet"
SCHEDULES = ROOT / "data/nfl/schedules/games.csv"
PREDICTIONS = ROOT / "data/nfl/predictions/step8_t5_schedule_ablations.csv"
REPORT = ROOT / "ml/nfl/reports/step8_t5_schedule.json"

MARGIN_SCHEDULE = [
    "short_rest_diff", "very_short_rest_diff", "long_rest_diff",
    "rest_mismatch_home_advantage", "rest_mismatch_away_advantage",
]
TOTAL_SCHEDULE = [
    "both_short_rest", "any_short_rest", "both_long_rest", "thursday_game",
    "monday_game", "saturday_game", "rest_mismatch_absolute",
]


def schedule_features(frame: pd.DataFrame) -> pd.DataFrame:
    home = frame.home_rest.astype(float); away = frame.away_rest.astype(float)
    weekday = frame.weekday.astype(str).str.lower()
    return pd.DataFrame({
        "game_id": frame.game_id,
        "short_rest_diff": home.le(6).astype(int) - away.le(6).astype(int),
        "very_short_rest_diff": home.le(4).astype(int) - away.le(4).astype(int),
        "long_rest_diff": home.ge(10).astype(int) - away.ge(10).astype(int),
        "rest_mismatch_home_advantage": (home - away).clip(lower=0),
        "rest_mismatch_away_advantage": (away - home).clip(lower=0),
        "both_short_rest": (home.le(6) & away.le(6)).astype(int),
        "any_short_rest": (home.le(6) | away.le(6)).astype(int),
        "both_long_rest": (home.ge(10) & away.ge(10)).astype(int),
        "thursday_game": weekday.eq("thursday").astype(int),
        "monday_game": weekday.eq("monday").astype(int),
        "saturday_game": weekday.eq("saturday").astype(int),
        "rest_mismatch_absolute": (home - away).abs(),
    }, index=frame.index)


def _shuffle(frame: pd.DataFrame, columns: list[str], seed: int) -> pd.DataFrame:
    values = frame.groupby("season", group_keys=False)[columns].sample(frac=1.0, random_state=seed).reset_index(drop=True)
    values.index = frame.index
    return values


def run_audit() -> tuple[pd.DataFrame, dict]:
    games = pd.read_parquet(FEATURES)
    schedule = pd.read_csv(SCHEDULES)
    schedule = schedule[schedule.game_type.eq("REG")]
    context = schedule_features(schedule)
    games = games.merge(context, on="game_id", how="left", validate="one_to_one")
    development = games[games.season.between(2014, 2024)].sort_values(["season", "week", "game_id"]).copy()
    core = model_frame(development)
    extras = development[MARGIN_SCHEDULE + TOTAL_SCHEDULE].astype(float).fillna(0.0)
    design = pd.concat([core, extras], axis=1)
    source = pd.concat([development[["season"]], extras], axis=1)
    shuffled_margin = _shuffle(source, MARGIN_SCHEDULE, 20260851)
    shuffled_total = _shuffle(source, TOTAL_SCHEDULE, 20260852)
    shuffled_margin_names, shuffled_total_names = [], []
    for column in MARGIN_SCHEDULE:
        name = f"shuffled_margin_{column}"; design[name] = shuffled_margin[column].to_numpy(); shuffled_margin_names.append(name)
    for column in TOTAL_SCHEDULE:
        name = f"shuffled_total_{column}"; design[name] = shuffled_total[column].to_numpy(); shuffled_total_names.append(name)
    margin_base = [c for c in core if c.startswith("diff_")] + ["rest_diff", "div_game", "week"]
    total_base = [c for c in core if c.startswith("sum_")] + [
        "rest_sum", "div_game", "week", "dynamic_kickoff_rule", "onside_anytime_when_trailing",
        "kickoff_touchback_to_35", "regular_season_ot_both_possess", "onside_2026_alignment_rule",
    ]
    families = {
        "margin": {"t1_core": margin_base, "t1_plus_t5": margin_base + MARGIN_SCHEDULE,
                   "t1_plus_shuffled_t5": margin_base + shuffled_margin_names},
        "total": {"t1_core": total_base, "t1_plus_t5": total_base + TOTAL_SCHEDULE,
                  "t1_plus_shuffled_t5": total_base + shuffled_total_names},
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
    metrics = {target: {name: _metrics(predictions[target], predictions[f"{target}_{name}"])
                        for name in target_families} for target, target_families in families.items()}
    to_close = {
        "margin": {name: _metrics(-predictions.spread_home_close, predictions[f"margin_{name}"])
                   for name in families["margin"]},
        "total": {name: _metrics(predictions.total_line_close, predictions[f"total_{name}"])
                  for name in families["total"]},
    }
    stability = {}
    for target, target_families in families.items():
        stability[target] = {}
        for name in target_families:
            gains = []
            for _, rows in predictions.groupby("season"):
                core_mae = _metrics(rows[target], rows[f"{target}_t1_core"])["mae"]
                candidate = _metrics(rows[target], rows[f"{target}_{name}"])["mae"]
                gains.append(core_mae - candidate)
            stability[target][name] = {
                "overall_mae_gain_vs_t1": metrics[target]["t1_core"]["mae"] - metrics[target][name]["mae"],
                "seasons_better_than_t1": sum(g > 0 for g in gains), "seasons_tested": len(gains),
                "worst_season_gain": min(gains), "best_season_gain": max(gains),
            }
    report = {
        "status": "t5_historical_shadow_audit_only", "games": len(predictions),
        "test_seasons": list(range(2019, 2025)), "vault_2025_predictions": 0,
        "features": {"margin": MARGIN_SCHEDULE, "total": TOTAL_SCHEDULE},
        "metrics": metrics, "to_closing_market": to_close, "stability": stability,
        "restrictions": ["T1 already contains linear rest difference/sum", "T5 tests nonlinear incremental effects",
                         "no manual bye or short-week points", "travel excluded", "shadow only"],
    }
    return predictions, report


def main() -> None:
    predictions, report = run_audit()
    PREDICTIONS.parent.mkdir(parents=True, exist_ok=True); REPORT.parent.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(PREDICTIONS, index=False); REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "games": report["games"], "metrics": report["metrics"],
                      "to_closing_market": report["to_closing_market"], "stability": report["stability"]}, indent=2))


if __name__ == "__main__":
    main()
