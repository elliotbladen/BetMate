"""Step 8G: observed-weather oracle for NFL totals.

Schedule temperature and wind are observed conditions without forecast capture
timestamps. They measure an upper bound only and can never populate live prices.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .baselines import _metrics, fit_ridge, model_frame


ROOT = Path(__file__).resolve().parents[2]
FEATURES = ROOT / "data/nfl/features/weekly_epa.parquet"
SCHEDULES = ROOT / "data/nfl/schedules/games.csv"
PREDICTIONS = ROOT / "data/nfl/predictions/step8_t6_weather_oracle.csv"
REPORT = ROOT / "ml/nfl/reports/step8_t6_weather.json"
WEATHER_COLUMNS = [
    "open_air", "weather_available", "wind_mph_open_air", "wind_squared_scaled",
    "wind_15_plus", "wind_20_plus", "temperature_deviation_60",
    "freezing_or_below", "hot_80_plus",
]


def weather_features(frame: pd.DataFrame) -> pd.DataFrame:
    open_air = frame.roof.astype(str).str.strip().str.lower().isin(["outdoors", "open"])
    available = open_air & frame.temp.notna() & frame.wind.notna()
    wind = frame.wind.astype(float).where(available, 0.0)
    temp = frame.temp.astype(float).where(available, 60.0)
    return pd.DataFrame({
        "game_id": frame.game_id,
        "open_air": open_air.astype(int), "weather_available": available.astype(int),
        "wind_mph_open_air": wind, "wind_squared_scaled": wind.pow(2) / 100.0,
        "wind_15_plus": (available & wind.ge(15)).astype(int),
        "wind_20_plus": (available & wind.ge(20)).astype(int),
        "temperature_deviation_60": (temp - 60.0).abs().where(available, 0.0),
        "freezing_or_below": (available & temp.le(32)).astype(int),
        "hot_80_plus": (available & temp.ge(80)).astype(int),
    }, index=frame.index)


def _shuffle(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    values = frame.groupby("season", group_keys=False)[columns].sample(frac=1.0, random_state=20260861)
    values = values.reset_index(drop=True); values.index = frame.index
    return values


def run_audit() -> tuple[pd.DataFrame, dict]:
    games = pd.read_parquet(FEATURES)
    schedule = pd.read_csv(SCHEDULES)
    regular = schedule[schedule.game_type.eq("REG")].copy()
    weather = weather_features(regular)
    games = games.merge(weather, on="game_id", how="left", validate="one_to_one")
    development = games[games.season.between(2014, 2024)].sort_values(["season", "week", "game_id"]).copy()
    core = model_frame(development)
    extras = development[WEATHER_COLUMNS].astype(float).fillna(0.0)
    design = pd.concat([core, extras], axis=1)
    shuffled = _shuffle(pd.concat([development[["season"]], extras], axis=1), WEATHER_COLUMNS)
    shuffled_names = []
    for column in WEATHER_COLUMNS:
        name = f"shuffled_{column}"; design[name] = shuffled[column].to_numpy(); shuffled_names.append(name)
    base = [c for c in core if c.startswith("sum_")] + [
        "rest_sum", "div_game", "week", "dynamic_kickoff_rule", "onside_anytime_when_trailing",
        "kickoff_touchback_to_35", "regular_season_ot_both_possess", "onside_2026_alignment_rule",
    ]
    families = {"t1_core": base, "t1_plus_t6_oracle": base + WEATHER_COLUMNS,
                "t1_plus_shuffled_t6": base + shuffled_names}
    folds = []
    for season in range(2019, 2025):
        train, test = development.season.lt(season), development.season.eq(season)
        fold = development.loc[test, ["game_id", "season", "week", "total", "total_line_close"]].copy()
        for name, columns in families.items():
            model = fit_ridge(design[train], development.loc[train, "total"], columns, alpha=25.0)
            fold[name] = model.predict(design[test])
        folds.append(fold)
    predictions = pd.concat(folds, ignore_index=True)
    metrics = {name: _metrics(predictions.total, predictions[name]) for name in families}
    to_close = {name: _metrics(predictions.total_line_close, predictions[name]) for name in families}
    stability = {}
    for name in families:
        gains = []
        for _, rows in predictions.groupby("season"):
            core_mae = _metrics(rows.total, rows.t1_core)["mae"]
            candidate = _metrics(rows.total, rows[name])["mae"]
            gains.append(core_mae - candidate)
        stability[name] = {
            "overall_mae_gain_vs_t1": metrics["t1_core"]["mae"] - metrics[name]["mae"],
            "seasons_better_than_t1": sum(g > 0 for g in gains), "seasons_tested": len(gains),
            "worst_season_gain": min(gains), "best_season_gain": max(gains),
        }
    test_schedule = regular[regular.season.between(2019, 2024)]
    test_open = test_schedule.roof.isin(["outdoors", "open"])
    report = {
        "status": "t6_observed_weather_oracle_only", "games": len(predictions),
        "test_seasons": list(range(2019, 2025)), "vault_2025_predictions": 0,
        "features": WEATHER_COLUMNS, "metrics": metrics, "to_closing_total": to_close,
        "stability": stability,
        "coverage": {"open_air_games": int(test_open.sum()),
                     "open_air_weather": float(test_schedule.loc[test_open, "wind"].notna().mean())},
        "restrictions": ["observed weather is not a timestamped forecast", "oracle cannot price live games",
                         "missing weather has a separate availability flag", "totals only", "staking disabled"],
    }
    return predictions, report


def main() -> None:
    predictions, report = run_audit()
    PREDICTIONS.parent.mkdir(parents=True, exist_ok=True); REPORT.parent.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(PREDICTIONS, index=False); REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "games": report["games"], "metrics": report["metrics"],
                      "to_closing_total": report["to_closing_total"], "stability": report["stability"],
                      "coverage": report["coverage"]}, indent=2))


if __name__ == "__main__":
    main()
