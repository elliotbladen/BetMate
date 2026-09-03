"""Immutable 2026 NFL paper prediction and market-snapshot workflow."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from .baselines import fit_ridge, model_frame
from .challenger import _normal_win_probability, _regressor, challenger_frame
from .features import (
    EWMA_ALPHA,
    PRIOR_SEASON_RETENTION,
    compute_game_stats,
    load_pbp_season,
)
from .rule_eras import rule_era_features


ROOT = Path(__file__).resolve().parents[2]
PAPER_CONFIG = ROOT / "ml/nfl/step5_paper_2026.yaml"
SCHEDULES = ROOT / "data/nfl/schedules/games.csv"
HISTORICAL = ROOT / "data/nfl/features/weekly_epa.parquet"
STATE = ROOT / "data/nfl/features/2026_week1_preseason_team_state.parquet"
PREDICTIONS = ROOT / "data/nfl/predictions/2026_week01_paper_frozen.csv"
MANIFEST = ROOT / "ml/nfl/reports/step6_week01_prediction_manifest.json"
MARKET = ROOT / "data/nfl/markets/2026_week01_schedule_reference.csv"
MARKET_MANIFEST = ROOT / "ml/nfl/reports/step6_week01_market_manifest.json"

LABEL_COLUMNS = {
    "home_score", "away_score", "margin", "total", "result",
    "spread_line", "total_line", "spread_home_open", "spread_home_close",
    "total_line_open", "total_line_close", "h2h_home_close", "h2h_away_close",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_json_once(path: Path, payload: dict) -> None:
    if path.exists():
        raise RuntimeError(f"refusing to overwrite frozen artefact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def final_team_state() -> pd.DataFrame:
    """Recreate final 2025 EWMA state, then apply fixed offseason regression."""
    all_stats = []
    for season in range(2014, 2026):
        all_stats.append(compute_game_stats(load_pbp_season(season, str(ROOT / "data/nfl/pbp"))))
    stats = pd.concat(all_stats, ignore_index=True)
    value_columns = [
        column for column in stats.columns
        if column.startswith(("off_", "def_")) and not column.endswith("_plays")
    ]
    rows = []
    current_teams = sorted(stats.loc[stats.season.eq(2025), "team"].unique())
    for team in current_teams:
        games = stats[stats.team.eq(team)].sort_values(["season", "week", "game_id"])
        state = {column: 0.0 for column in value_columns}
        count = 0
        prior_season = None
        for game in games.itertuples(index=False):
            season = int(game.season)
            if prior_season is not None and season != prior_season:
                for column in value_columns:
                    state[column] *= PRIOR_SEASON_RETENTION
                count = max(1, int(count * PRIOR_SEASON_RETENTION))
            for column in value_columns:
                value = getattr(game, column)
                value = 0.0 if pd.isna(value) else float(value)
                state[column] = EWMA_ALPHA * value + (1.0 - EWMA_ALPHA) * state[column]
            count += 1
            prior_season = season
        if prior_season != 2025:
            raise RuntimeError(f"{team} has no final 2025 state")
        for column in value_columns:
            state[column] *= PRIOR_SEASON_RETENTION
        rows.append({"team": team, "games_in_ewma": max(1, int(count * PRIOR_SEASON_RETENTION)), **state})
    result = pd.DataFrame(rows)
    if len(result) != 32:
        raise RuntimeError(f"expected 32 team states, found {len(result)}")
    return result


def week_one_features(state: pd.DataFrame) -> pd.DataFrame:
    schedule = pd.read_csv(SCHEDULES)
    games = schedule[
        schedule.season.eq(2026) & schedule.game_type.eq("REG") & schedule.week.eq(1)
    ].copy()
    if len(games) != 16 or games.home_score.notna().any():
        raise RuntimeError("Week 1 schedule is not an unplayed 16-game card")
    feature_columns = [c for c in state.columns if c not in {"team", "games_in_ewma"}]
    home = state.rename(columns={
        "team": "home_team", "games_in_ewma": "home_games_in_ewma",
        **{column: f"home_{column}" for column in feature_columns},
    })
    away = state.rename(columns={
        "team": "away_team", "games_in_ewma": "away_games_in_ewma",
        **{column: f"away_{column}" for column in feature_columns},
    })
    output = games[[
        "game_id", "season", "week", "gameday", "gametime", "home_team", "away_team",
        "home_rest", "away_rest", "roof", "surface", "div_game",
    ]].merge(home, on="home_team", validate="many_to_one").merge(
        away, on="away_team", validate="many_to_one"
    )
    output["home_rest"] = output.home_rest.fillna(7)
    output["away_rest"] = output.away_rest.fillna(7)
    for name, value in rule_era_features(2026).items():
        output[name] = value
    output["stats_through_week"] = 0
    output["feature_timing_rule"] = "2026_week_1_uses_regressed_final_2025_state"
    return output


def _margin_columns(frame: pd.DataFrame) -> list[str]:
    return [c for c in frame if c.startswith("diff_")] + ["rest_diff", "div_game", "week"]


def _total_columns(frame: pd.DataFrame) -> list[str]:
    return [c for c in frame if c.startswith("sum_")] + [
        "rest_sum", "div_game", "week", "dynamic_kickoff_rule",
        "onside_anytime_when_trailing", "kickoff_touchback_to_35",
        "regular_season_ot_both_possess", "onside_2026_alignment_rule",
    ]


def prepare_week_one() -> dict:
    if any(path.exists() for path in (STATE, PREDICTIONS, MANIFEST)):
        raise RuntimeError("2026 Week 1 paper card has already been prepared")
    generated_at = datetime.now(timezone.utc).isoformat()
    state = final_team_state()
    features = week_one_features(state)
    historical = pd.read_parquet(HISTORICAL).sort_values(["season", "week", "game_id"])
    development = historical[historical.season <= 2025].copy()
    calibration_train = historical[historical.season <= 2024].copy()
    calibration_test = historical[historical.season.eq(2025)].copy()

    train_frame = model_frame(development)
    paper_frame = model_frame(features)
    margin_model = fit_ridge(
        train_frame, development.margin, _margin_columns(train_frame), alpha=25.0
    )
    total_model = fit_ridge(
        train_frame, development.total, _total_columns(train_frame), alpha=25.0
    )
    calibration_train_frame = model_frame(calibration_train)
    calibration_test_frame = model_frame(calibration_test)
    calibration_model = fit_ridge(
        calibration_train_frame,
        calibration_train.margin,
        _margin_columns(calibration_train_frame),
        alpha=25.0,
    )
    calibration_error = calibration_test.margin.to_numpy() - calibration_model.predict(calibration_test_frame)
    residual_sd = float(np.std(calibration_error, ddof=1))

    tree_train = challenger_frame(development)
    tree_paper = challenger_frame(features)
    tree_margin_model = _regressor().fit(tree_train, development.margin)
    tree_total_model = _regressor().fit(tree_train, development.total)

    predictions = features[[
        "game_id", "season", "week", "gameday", "gametime", "home_team", "away_team",
        "stats_through_week", "feature_timing_rule",
    ]].copy()
    predictions["ridge_margin"] = margin_model.predict(paper_frame)
    predictions["ridge_fair_home_spread"] = -predictions.ridge_margin
    predictions["ridge_total"] = total_model.predict(paper_frame)
    predictions["ridge_home_win_probability"] = _normal_win_probability(
        predictions.ridge_margin.to_numpy(), residual_sd
    )
    predictions["ridge_expected_home_points"] = (predictions.ridge_total + predictions.ridge_margin) / 2.0
    predictions["ridge_expected_away_points"] = (predictions.ridge_total - predictions.ridge_margin) / 2.0
    predictions["tree_shadow_margin"] = tree_margin_model.predict(tree_paper)
    predictions["tree_shadow_fair_home_spread"] = -predictions.tree_shadow_margin
    predictions["tree_shadow_total"] = tree_total_model.predict(tree_paper)
    predictions["generated_at_utc"] = generated_at
    predictions["feature_cutoff_utc"] = generated_at
    predictions["training_through"] = 2025
    predictions["staking_enabled"] = False
    if LABEL_COLUMNS.intersection(predictions.columns):
        raise RuntimeError("paper prediction contains a market field or label")

    STATE.parent.mkdir(parents=True, exist_ok=True)
    PREDICTIONS.parent.mkdir(parents=True, exist_ok=True)
    state.to_parquet(STATE, index=False)
    predictions.to_csv(PREDICTIONS, index=False)
    manifest = {
        "status": "2026_week01_paper_predictions_frozen_before_market_capture",
        "generated_at_utc": generated_at,
        "games": len(predictions),
        "training_through": 2025,
        "hyperparameters_retuned_after_vault": False,
        "market_fields_in_prediction": False,
        "staking_enabled": False,
        "sha256": {
            "prediction": _sha256(PREDICTIONS),
            "team_state": _sha256(STATE),
            "historical_features": _sha256(HISTORICAL),
            "paper_config": _sha256(PAPER_CONFIG),
            "step6_code": _sha256(Path(__file__)),
        },
    }
    _write_json_once(MANIFEST, manifest)
    return manifest


def capture_schedule_reference() -> dict:
    if not PREDICTIONS.exists() or not MANIFEST.exists():
        raise RuntimeError("predictions must be frozen before any market capture")
    if MARKET.exists() or MARKET_MANIFEST.exists():
        raise RuntimeError("Week 1 schedule market reference has already been captured")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if _sha256(PREDICTIONS) != manifest["sha256"]["prediction"]:
        raise RuntimeError("paper predictions changed before market capture")
    captured_at = datetime.now(timezone.utc).isoformat()
    schedule = pd.read_csv(SCHEDULES)
    rows = schedule[
        schedule.season.eq(2026) & schedule.game_type.eq("REG") & schedule.week.eq(1)
    ][["game_id", "spread_line", "total_line"]].copy()
    # nflverse schedule spread_line is the away handicap; convert to locked
    # home-team handicap convention.
    rows["home_spread"] = -rows.spread_line
    rows = rows.drop(columns="spread_line")
    rows["captured_at_utc"] = captured_at
    rows["source"] = "nflverse_schedule_embedded"
    rows["bookmaker"] = "unknown"
    rows["valid_obtainable_quote"] = False
    rows["qualification_reason"] = "missing_bookmaker_and_original_quote_timestamp"
    MARKET.parent.mkdir(parents=True, exist_ok=True)
    rows.to_csv(MARKET, index=False)
    market_manifest = {
        "status": "reference_only_not_valid_for_clv_or_roi",
        "captured_after_prediction": True,
        "captured_at_utc": captured_at,
        "games": len(rows),
        "valid_obtainable_quotes": 0,
        "prediction_sha256": _sha256(PREDICTIONS),
        "market_reference_sha256": _sha256(MARKET),
    }
    _write_json_once(MARKET_MANIFEST, market_manifest)
    return market_manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare-week-one", "capture-schedule-reference"))
    args = parser.parse_args()
    action = {
        "prepare-week-one": prepare_week_one,
        "capture-schedule-reference": capture_schedule_reference,
    }[args.action]
    print(json.dumps(action(), indent=2))


if __name__ == "__main__":
    main()
