"""Frozen identifiers and validation rules for the NFL data spine.

The model uses nflverse schedule identifiers as its canonical historical keys.
Relocated franchises therefore retain the abbreviation in use for that season
(``STL``, ``SD`` and ``OAK``).  Provider aliases are converted back to those
season-specific identifiers before a date-aware join is attempted.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd


CONTRACT_VERSION = "nfl-data-contract-v1.0"
SPREAD_CONVENTION = "home_team_handicap_negative_home_favourite"
HISTORICAL_FEATURE_TIMING = "week_n_uses_completed_games_through_week_n_minus_1"
LIVE_PREDICTION_CUTOFF_HOURS_BEFORE_OPEN = 1

TEAM_CODES = frozenset({
    "ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE", "DAL",
    "DEN", "DET", "GB", "HOU", "IND", "JAX", "KC", "LA", "LAC",
    "LV", "MIA", "MIN", "NE", "NO", "NYG", "NYJ", "OAK", "PHI",
    "PIT", "SD", "SEA", "SF", "STL", "TB", "TEN", "WAS",
})

GAME_ID = re.compile(
    r"^(?P<season>\d{4})_(?P<week>\d{2})_(?P<away>[A-Z0-9]+)_(?P<home>[A-Z0-9]+)$"
)

REQUIRED_FEATURE_COLUMNS = frozenset({
    "game_id", "season", "week", "gameday", "home_team", "away_team",
    "home_score", "away_score", "margin", "total", "schedule_away_spread", "spread_line",
    "total_line", "home_rest", "away_rest", "roof", "surface", "div_game",
    "home_games_in_ewma", "away_games_in_ewma", "stats_through_week",
    "feature_timing_rule",
})

LABEL_AND_MARKET_COLUMNS = frozenset({
    "home_score", "away_score", "margin", "total", "spread_line", "total_line",
    "h2h_home_close", "h2h_away_close", "spread_home_close", "total_line_close",
    "spread_home_open", "total_line_open", "h2h_home_open", "h2h_away_open",
})


def schedule_team_code(team: str, season: int) -> str:
    """Return the nflverse historical abbreviation for a provider team code."""
    team = str(team).strip().upper()
    if team == "LA" and season <= 2015:
        return "STL"
    if team == "LAC" and season <= 2016:
        return "SD"
    if team == "LV" and season <= 2019:
        return "OAK"
    return team


def validate_game_identity(
    game_id: str, season: int, week: int, home_team: str, away_team: str
) -> None:
    match = GAME_ID.fullmatch(str(game_id))
    if not match:
        raise ValueError(f"invalid nflverse game_id: {game_id}")
    if home_team == away_team:
        raise ValueError("home_team and away_team must differ")
    unknown = {home_team, away_team} - TEAM_CODES
    if unknown:
        raise ValueError(f"unknown NFL team code(s): {', '.join(sorted(unknown))}")
    expected = (int(match["season"]), int(match["week"]), match["home"], match["away"])
    actual = (int(season), int(week), home_team, away_team)
    if expected != actual:
        raise ValueError(f"game_id components {expected} do not match row {actual}")


def prepare_odds_for_schedule_join(odds: pd.DataFrame) -> pd.DataFrame:
    """Normalise provider aliases and enforce one quote row per dated matchup."""
    required = {"date", "season", "home_team", "away_team"}
    missing = required - set(odds.columns)
    if missing:
        raise ValueError(f"odds missing join columns: {', '.join(sorted(missing))}")
    result = odds.copy()
    result["gameday"] = pd.to_datetime(result["date"], errors="raise").dt.date.astype(str)
    result["home_team"] = [schedule_team_code(t, int(s)) for t, s in zip(result.home_team, result.season)]
    result["away_team"] = [schedule_team_code(t, int(s)) for t, s in zip(result.away_team, result.season)]
    keys = ["season", "gameday", "home_team", "away_team"]
    duplicates = result.duplicated(keys, keep=False)
    if duplicates.any():
        examples = result.loc[duplicates, keys].head(5).to_dict("records")
        raise ValueError(f"odds join key is not unique: {examples}")
    return result


def validate_feature_store(frame: pd.DataFrame, *, season_from: int, season_to: int) -> dict[str, Any]:
    errors: list[str] = []
    metrics: dict[str, Any] = {}
    missing = REQUIRED_FEATURE_COLUMNS - set(frame.columns)
    if missing:
        errors.append(f"missing required columns: {', '.join(sorted(missing))}")
    if frame.game_id.duplicated().any():
        errors.append(f"duplicate game_id rows: {int(frame.game_id.duplicated(False).sum())}")
    outside = frame[~frame.season.between(season_from, season_to)]
    if len(outside):
        errors.append(f"rows outside {season_from}-{season_to}: {len(outside)}")
    identity_errors = []
    for row in frame[["game_id", "season", "week", "home_team", "away_team"]].itertuples(index=False):
        try:
            validate_game_identity(*row)
        except ValueError as exc:
            identity_errors.append(str(exc))
            if len(identity_errors) == 5:
                break
    errors.extend(identity_errors)
    if "stats_through_week" in frame:
        bad_shift = frame.stats_through_week != frame.week - 1
        if bad_shift.any():
            errors.append(f"unshifted weekly feature rows: {int(bad_shift.sum())}")
    if "feature_timing_rule" in frame:
        bad_rule = frame.feature_timing_rule != HISTORICAL_FEATURE_TIMING
        if bad_rule.any():
            errors.append(f"unexpected feature timing rule rows: {int(bad_rule.sum())}")
    if {"schedule_away_spread", "spread_line"} <= set(frame.columns):
        quoted = frame[["schedule_away_spread", "spread_line"]].dropna()
        bad_sign = (quoted.schedule_away_spread + quoted.spread_line).abs() > 1e-9
        if bad_sign.any():
            errors.append(f"schedule spreads not converted to home convention: {int(bad_sign.sum())}")
    if {"spread_line", "spread_home_close"} <= set(frame.columns):
        quoted = frame[["spread_line", "spread_home_close"]].dropna()
        direction_conflicts = (
            (quoted.spread_line != 0)
            & (quoted.spread_home_close != 0)
            & ((quoted.spread_line > 0) != (quoted.spread_home_close > 0))
        )
        conflict_rate = float(direction_conflicts.mean()) if len(quoted) else 0.0
        metrics["schedule_vs_odds_spread_direction_conflict_rate"] = conflict_rate
        # Different closing feeds can legitimately cross pick'em. A larger rate
        # indicates a likely sign or mapping failure rather than market movement.
        if conflict_rate > 0.02:
            errors.append(f"schedule/odds home-spread direction conflict rate: {conflict_rate:.3%}")
    feature_columns = [column for column in ("home_off_epa", "away_off_epa") if column in frame]
    if feature_columns:
        metrics["complete_core_feature_rows"] = int(frame[feature_columns].notna().all(axis=1).sum())
    if "spread_home_close" in frame:
        metrics["rows_with_historical_closing_spread"] = int(frame.spread_home_close.notna().sum())
    report = {
        "contract_version": CONTRACT_VERSION,
        "spread_convention": SPREAD_CONVENTION,
        "historical_feature_timing": HISTORICAL_FEATURE_TIMING,
        "season_from": season_from,
        "season_to": season_to,
        "rows": len(frame),
        "unique_games": int(frame.game_id.nunique()),
        "metrics": metrics,
        "errors": errors,
        "passed": not errors,
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", type=Path, default=Path("data/nfl/features/weekly_epa.parquet"))
    parser.add_argument("--season-from", type=int, default=2014)
    parser.add_argument("--season-to", type=int, default=2025)
    parser.add_argument("--output", type=Path, default=Path("ml/nfl/reports/step1_data_contract.json"))
    args = parser.parse_args()
    frame = pd.read_parquet(args.features) if args.features.suffix == ".parquet" else pd.read_csv(args.features)
    report = validate_feature_store(frame, season_from=args.season_from, season_to=args.season_to)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
