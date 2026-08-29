#!/usr/bin/env python3
"""Train a bounded player-layer correction on pre-match base lambdas.

v1 (failed): sparse player-ID features — no signal, -0.0005 improvement.
v2: position-grouped rolling stats — aggregates per-player rolling averages
    by position group (GK/DEF/MID/ATT) for each team, giving the model
    learnable signal about team strength changes from lineup composition.
"""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "championship" / "player_layer"
# Use tier-adjusted lambdas so shadow learns residuals AFTER T3/T6/T7/T8,
# preventing double-counting when shadow delta is added to price_match() output.
# Falls back to base (no tiers) if tier backtest hasn't been run.
_TIERS_PATH = ROOT / "data" / "championship" / "clv" / "backtest_results_tiers.csv"
_BASE_PATH = ROOT / "data" / "championship" / "clv" / "backtest_results.csv"
BASE = _TIERS_PATH if _TIERS_PATH.exists() else _BASE_PATH

ALIASES = {
    "Blackburn Rovers": "Blackburn", "Bristol City": "Bristol City",
    "Cardiff City": "Cardiff", "Coventry City": "Coventry",
    "Hull City": "Hull", "Ipswich Town": "Ipswich",
    "Leeds United": "Leeds", "Leicester City": "Leicester",
    "Norwich City": "Norwich", "Preston North End": "Preston",
    "Queens Park Rangers": "QPR", "Sheffield United": "Sheffield United",
    "Sheffield Wednesday": "Sheffield Weds", "Stoke City": "Stoke",
    "Swansea City": "Swansea", "West Bromwich Albion": "West Brom",
    "Plymouth Argyle": "Plymouth", "Oxford United": "Oxford",
    "Derby County": "Derby", "Luton Town": "Luton",
    "Birmingham City": "Birmingham", "Huddersfield Town": "Huddersfield",
    "Rotherham United": "Rotherham", "Southampton": "Southampton",
    "Burnley": "Burnley", "Sunderland": "Sunderland",
    "Middlesbrough": "Middlesbrough", "Millwall": "Millwall",
    "Watford": "Watford", "Portsmouth": "Portsmouth",
    "Charlton Athletic": "Charlton", "Wrexham": "Wrexham",
    "Wolverhampton Wanderers": "Wolves", "West Ham United": "West Ham",
    "Bolton Wanderers": "Bolton", "Lincoln City": "Lincoln",
}

# Rolling stats window
ROLLING_WINDOW = 8

# Stats to compute rolling per-90 averages for
ROLLING_STATS = ["goals", "assists", "shots", "shots_on_target", "saves"]

# Position groups for aggregation
POSITION_GROUPS = ["GK", "DEF", "MID", "ATT"]


def _load_all_player_stats(years: list[int]) -> pd.DataFrame:
    """Load player match stats from Championship + cross-league (EPL, League One).

    Cross-league data ensures players promoted/relegated into the Championship
    have rolling history from their prior league.
    """
    frames = []
    for year in years:
        for pattern in [
            f"player_match_stats_espn_{year}.csv",
            f"player_match_stats_espn_epl_{year}.csv",
            f"player_match_stats_espn_league1_{year}.csv",
        ]:
            path = DATA / pattern
            if path.exists():
                frames.append(pd.read_csv(path))
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def build_rolling_features(stats_path: Path,
                           cross_league_years: list[int] | None = None,
                           ) -> pd.DataFrame:
    """Build per-player rolling per-90 stats from match-level data.

    Returns a DataFrame with one row per player per match, with rolling
    averages computed from PRIOR matches only (no look-ahead).

    If cross_league_years is provided, EPL and League One stats for those
    years are included so promoted/relegated players have rolling history.
    """
    champ_df = pd.read_csv(stats_path)

    if cross_league_years:
        # Load cross-league data for the same years
        extra_frames = []
        for year in cross_league_years:
            for league in ["epl", "league1"]:
                path = DATA / f"player_match_stats_espn_{league}_{year}.csv"
                if path.exists():
                    extra_frames.append(pd.read_csv(path))
        if extra_frames:
            # Mark source so we can filter back to Championship matches later
            champ_df["_source"] = "championship"
            for ef in extra_frames:
                ef["_source"] = "cross_league"
            df = pd.concat([champ_df] + extra_frames, ignore_index=True)
        else:
            df = champ_df
            df["_source"] = "championship"
    else:
        df = champ_df
        df["_source"] = "championship"

    df["date"] = pd.to_datetime(df.kickoff, utc=True).dt.strftime("%Y-%m-%d")
    df["team_alias"] = df.team.map(lambda x: ALIASES.get(x, x))
    df = df.sort_values(["player_id", "date"])

    # Compute per-90 stats
    for stat in ROLLING_STATS:
        df[f"{stat}_p90"] = np.where(df.minutes > 0, df[stat] / df.minutes * 90, 0.0)

    # Rolling averages per player (shifted by 1 to avoid look-ahead)
    # Computed across ALL leagues so cross-league history feeds in
    rolling_cols = [f"{s}_p90" for s in ROLLING_STATS]
    for col in rolling_cols:
        df[f"roll_{col}"] = (
            df.groupby("player_id")[col]
            .transform(lambda x: x.shift(1).rolling(ROLLING_WINDOW, min_periods=1).mean())
        )
    # Rolling minutes (not per-90)
    df["roll_minutes"] = (
        df.groupby("player_id")["minutes"]
        .transform(lambda x: x.shift(1).rolling(ROLLING_WINDOW, min_periods=1).mean())
    )

    # Only return Championship matches for training/aggregation
    # (cross-league rows were only needed to seed rolling history)
    return df[df._source == "championship"].drop(columns=["_source"])


def aggregate_match_features(rolling_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate per-player rolling stats into per-team position-group features.

    For each match, for each side (home/away), sum the rolling stats of
    starters by position group. This creates features like:
        home_ATT_roll_goals_p90 = sum of rolling goals/90 for home attackers
    """
    # Only starters contribute
    starters = rolling_df[rolling_df.starter == 1].copy()
    starters["date"] = pd.to_datetime(starters.kickoff, utc=True).dt.strftime("%Y-%m-%d")
    starters["home_alias"] = starters.home_team.map(lambda x: ALIASES.get(x, x))
    starters["away_alias"] = starters.away_team.map(lambda x: ALIASES.get(x, x))

    roll_cols = [f"roll_{s}_p90" for s in ROLLING_STATS] + ["roll_minutes"]
    games = []

    for (event_id, date, home_alias, away_alias), match in starters.groupby(
        ["event_id", "date", "home_alias", "away_alias"]
    ):
        row = {"event_id": event_id, "date": date, "home": home_alias, "away": away_alias}
        for side in ["home", "away"]:
            side_df = match[match.side == side]
            for pg in POSITION_GROUPS:
                pg_df = side_df[side_df.position_group == pg]
                for col in roll_cols:
                    key = f"{side}_{pg}_{col}"
                    row[key] = pg_df[col].sum() if len(pg_df) else 0.0
                row[f"{side}_{pg}_count"] = len(pg_df)
        games.append(row)

    return pd.DataFrame(games)


def joined(year: int, season: str, base: pd.DataFrame,
           cross_league_years: list[int] | None = None) -> pd.DataFrame:
    """Join position-grouped features with backtest base lambdas."""
    stats_path = DATA / f"player_match_stats_espn_{year}.csv"
    if not stats_path.exists():
        raise FileNotFoundError(f"Run backfill_espn_player_stats.py --season {year} first")

    rolling = build_rolling_features(stats_path, cross_league_years=cross_league_years)
    match_features = aggregate_match_features(rolling)

    subset = base[base.season.eq(season)].copy()
    subset["date"] = pd.to_datetime(subset.date).dt.strftime("%Y-%m-%d")

    merged = match_features.merge(
        subset[["date", "home", "away", "lambda", "mu", "fthg", "ftag"]],
        on=["date", "home", "away"],
        how="inner",
    )
    return merged


def feature_columns(df: pd.DataFrame) -> list[str]:
    """Get the feature column names from a joined DataFrame."""
    return [c for c in df.columns if c.startswith(("home_", "away_"))
            and c not in {"home", "away"}]


def main() -> None:
    base = pd.read_csv(BASE)
    # Cross-league years: include EPL + League One data so promoted/relegated
    # players have rolling history when they appear in Championship matches
    xl = [2023, 2024, 2025]
    train = joined(2023, "2023/24", base, cross_league_years=xl)
    test = joined(2024, "2024/25", base, cross_league_years=xl)

    feat_cols = feature_columns(train)
    # Ensure test has same columns (new players in test season get 0)
    for col in feat_cols:
        if col not in test.columns:
            test[col] = 0.0
    test_feat_cols = [c for c in feat_cols if c in test.columns]

    x_train = train[feat_cols].fillna(0).values
    x_test = test[test_feat_cols].fillna(0).values

    y_train = np.c_[train.fthg - train["lambda"], train.ftag - train.mu]
    y_test = np.c_[test.fthg - test["lambda"], test.ftag - test.mu]

    model = Ridge(alpha=50.0, solver="lsqr").fit(x_train, y_train)
    pred = np.clip(model.predict(x_test), -0.12, 0.12)

    base_mae = float(np.mean(np.abs(y_test)))
    adjusted_mae = float(np.mean(np.abs(y_test - pred)))

    report = {
        "model": "ridge_position_rolling_v2",
        "train_season": "2023/24",
        "test_season": "2024/25",
        "train_matches": len(train),
        "test_matches": len(test),
        "features": len(feat_cols),
        "base_goal_mae": round(base_mae, 6),
        "adjusted_goal_mae": round(adjusted_mae, 6),
        "improvement": round(base_mae - adjusted_mae, 6),
        "cap_goals": 0.12,
        "approved": adjusted_mae < base_mae,
    }
    (DATA / "starter_shadow_eval.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    if report["approved"]:
        both = pd.concat([train, test], ignore_index=True)
        x_all = both[feat_cols].fillna(0).values
        y_all = np.c_[both.fthg - both["lambda"], both.ftag - both.mu]
        final_model = Ridge(alpha=50.0, solver="lsqr").fit(x_all, y_all)
        joblib.dump(
            {"feature_cols": feat_cols, "model": final_model,
             "cap": 0.12, "report": report},
            DATA / "player_shadow.joblib",
        )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
