"""
NFL weekly EPA feature store.

Reads nflverse play-by-play parquet files and computes per-team-per-week
features suitable for margin/total prediction. All features are shifted
(week N uses only data through week N-1) to prevent leakage.

Key features per team per week:
  - pass/rush offense/defense EPA per play
  - success rate (pass/rush, off/def)
  - early-down EPA (1st/2nd down, non-garbage-time)
  - explosives rate, pressure/sack rate
  - special teams EPA
  - EWMA-smoothed versions with configurable half-life

Usage:
    python -m ml.nfl.features --seasons 2014 2025 --output data/nfl/features/weekly_epa.parquet
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


# --- config from config.yaml ---
HALF_LIFE_GAMES = 6
PRIOR_SEASON_RETENTION = 0.35
GARBAGE_WP_LOW = 0.05
GARBAGE_WP_HIGH = 0.95

EWMA_ALPHA = 1 - 0.5 ** (1 / HALF_LIFE_GAMES)


def load_pbp_season(year: int, pbp_dir: str = "data/nfl/pbp") -> pd.DataFrame:
    """Load a single season's PBP parquet, keeping only the columns we need."""
    cols = [
        "game_id", "play_type", "posteam", "defteam", "epa",
        "wp", "down", "yards_gained", "success",
        "home_team", "away_team", "week", "season",
        "pass_attempt", "rush_attempt", "sack",
    ]
    path = Path(pbp_dir) / f"play_by_play_{year}.parquet"
    df = pd.read_parquet(path)
    available = [c for c in cols if c in df.columns]
    return df[available].copy()


def _agg_stats(g: pd.DataFrame, prefix: str) -> dict:
    """Compute EPA stats for a group of plays (offense or defense perspective)."""
    n = len(g)
    if n == 0:
        return {}
    pass_plays = g[g.play_type == "pass"]
    run_plays = g[g.play_type == "run"]
    early = g[(g.down.isin([1, 2])) & ~((g.wp < GARBAGE_WP_LOW) | (g.wp > GARBAGE_WP_HIGH))]

    has_sack = "sack" in g.columns
    return {
        f"{prefix}_epa": g.epa.mean(),
        f"{prefix}_pass_epa": pass_plays.epa.mean() if len(pass_plays) > 0 else 0,
        f"{prefix}_rush_epa": run_plays.epa.mean() if len(run_plays) > 0 else 0,
        f"{prefix}_success_rate": g.success.mean() if "success" in g.columns else 0,
        f"{prefix}_pass_success": pass_plays.success.mean() if len(pass_plays) > 0 and "success" in g.columns else 0,
        f"{prefix}_rush_success": run_plays.success.mean() if len(run_plays) > 0 and "success" in g.columns else 0,
        f"{prefix}_early_down_epa": early.epa.mean() if len(early) > 0 else 0,
        f"{prefix}_explosive_rate": (g.yards_gained >= 20).mean() if "yards_gained" in g.columns else 0,
        f"{prefix}_sack_rate": g.sack.mean() if has_sack else 0,
        f"{prefix}_plays": n,
    }


def compute_game_stats(pbp: pd.DataFrame) -> pd.DataFrame:
    """
    From play-by-play, compute per-team-per-game aggregate stats.
    Returns one row per (game_id, team) with both off_ and def_ columns.
    """
    plays = pbp[pbp.play_type.isin(["pass", "run"])].copy()
    if "success" not in plays.columns:
        plays["success"] = (plays.epa > 0).astype(int)

    rows = []
    for (game_id, season, week), game_plays in plays.groupby(["game_id", "season", "week"]):
        teams_in_game = game_plays.posteam.dropna().unique()
        for team in teams_in_game:
            off_plays = game_plays[game_plays.posteam == team]
            def_plays = game_plays[game_plays.defteam == team]
            opponents = off_plays.defteam.dropna().unique()
            opponent = opponents[0] if len(opponents) > 0 else ""

            row = {
                "game_id": game_id,
                "season": int(season),
                "week": int(week),
                "team": team,
                "opponent": opponent,
            }
            row.update(_agg_stats(off_plays, "off"))
            row.update(_agg_stats(def_plays, "def"))
            rows.append(row)

    return pd.DataFrame(rows)


def ewma_features(game_stats: pd.DataFrame) -> pd.DataFrame:
    """
    Compute EWMA-smoothed features per team, shifted so week N uses
    only data through week N-1. Returns one row per (season, week, team).
    """
    epa_cols = [c for c in game_stats.columns
                if any(c.startswith(p) for p in ["off_", "def_"])
                and not c.endswith("_plays")]

    rows = []
    for team in sorted(game_stats.team.unique()):
        team_games = game_stats[game_stats.team == team].sort_values(["season", "week"])

        ewma_state = {c: 0.0 for c in epa_cols}
        ewma_count = 0
        prev_season = None

        for _, g in team_games.iterrows():
            season, week = g.season, g.week

            # Season boundary: decay prior season
            if prev_season is not None and season != prev_season:
                for c in epa_cols:
                    ewma_state[c] *= PRIOR_SEASON_RETENTION
                ewma_count = max(1, int(ewma_count * PRIOR_SEASON_RETENTION))

            # EMIT the shifted feature row BEFORE updating with this game
            row = {"season": int(season), "week": int(week), "team": team,
                   "games_in_ewma": ewma_count}
            for c in epa_cols:
                row[c] = ewma_state[c]
            rows.append(row)

            # UPDATE ewma with this game's result
            for c in epa_cols:
                val = g.get(c, 0)
                if pd.isna(val):
                    val = 0
                ewma_state[c] = EWMA_ALPHA * val + (1 - EWMA_ALPHA) * ewma_state[c]
            ewma_count += 1
            prev_season = season

    return pd.DataFrame(rows)


def build_matchup_features(
    schedules_path: str,
    ewma_df: pd.DataFrame,
    odds_path: str | None = None,
) -> pd.DataFrame:
    """
    Build the final matchup-level feature table: one row per game with
    home/away team features, schedule context, and odds.
    """
    sched = pd.read_csv(schedules_path)
    sched = sched[sched.game_type == "REG"].copy()

    # Split EWMA into offense and defense column groups for renaming
    off_cols = [c for c in ewma_df.columns if c.startswith("off_")]
    def_cols = [c for c in ewma_df.columns if c.startswith("def_")]
    meta_cols = ["season", "week", "team", "games_in_ewma"]

    # --- Home team features ---
    home_rename = {"team": "home_team", "games_in_ewma": "home_games_in_ewma"}
    for c in off_cols:
        home_rename[c] = f"home_{c}"
    for c in def_cols:
        home_rename[c] = f"home_{c}"

    home_feats = ewma_df[meta_cols + off_cols + def_cols].rename(columns=home_rename)

    # --- Away team features ---
    away_rename = {"team": "away_team", "games_in_ewma": "away_games_in_ewma"}
    for c in off_cols:
        away_rename[c] = f"away_{c}"
    for c in def_cols:
        away_rename[c] = f"away_{c}"

    away_feats = ewma_df[meta_cols + off_cols + def_cols].rename(columns=away_rename)

    # Start with schedule
    result = sched[["game_id", "season", "week", "home_team", "away_team",
                     "home_score", "away_score", "spread_line", "total_line",
                     "home_rest", "away_rest", "roof", "surface", "div_game"]].copy()

    # Merge home features
    result = result.merge(home_feats, on=["season", "week", "home_team"], how="left")
    # Merge away features
    result = result.merge(away_feats, on=["season", "week", "away_team"], how="left")

    # Derived labels
    result["margin"] = result.home_score - result.away_score
    result["total"] = result.home_score + result.away_score

    # Differential features (home perspective)
    for stat in off_cols:
        base = stat  # e.g. "off_epa"
        home_col = f"home_{base}"
        away_col = f"away_{base}"
        if home_col in result.columns and away_col in result.columns:
            result[f"diff_{base}"] = result[home_col] - result[away_col]

    for stat in def_cols:
        base = stat
        home_col = f"home_{base}"
        away_col = f"away_{base}"
        if home_col in result.columns and away_col in result.columns:
            # For defense, LOWER EPA allowed is better, so home - away
            result[f"diff_{base}"] = result[home_col] - result[away_col]

    # Merge odds if available
    if odds_path and Path(odds_path).exists():
        odds = pd.read_csv(odds_path)
        odds["date"] = pd.to_datetime(odds["date"])
        result = result.merge(
            odds[["season", "home_team", "away_team",
                  "h2h_home_close", "h2h_away_close",
                  "spread_home_close", "total_line_close",
                  "spread_home_open", "total_line_open",
                  "h2h_home_open", "h2h_away_open"]],
            on=["season", "home_team", "away_team"],
            how="left"
        )

    return result


def build_feature_store(
    seasons: tuple[int, int] = (2014, 2025),
    pbp_dir: str = "data/nfl/pbp",
    schedules_path: str = "data/nfl/schedules/games.csv",
    odds_path: str = "data/nfl/historical_odds/nfl_odds_2014_2025.csv",
    output_path: str = "data/nfl/features/weekly_epa.parquet",
) -> pd.DataFrame:
    """Main entry point: build the complete feature store."""
    print(f"Building NFL feature store for {seasons[0]}-{seasons[1]}...")

    # Step 1: Load and aggregate PBP into per-game stats
    all_game_stats = []
    for year in range(seasons[0], seasons[1] + 1):
        print(f"  Processing PBP {year}...", end=" ")
        pbp = load_pbp_season(year, pbp_dir)
        gs = compute_game_stats(pbp)
        all_game_stats.append(gs)
        print(f"{len(gs)} team-games")

    game_stats = pd.concat(all_game_stats, ignore_index=True)
    print(f"\n  Total game-stats rows: {len(game_stats)}")

    # Step 2: EWMA features (shifted: week N uses data through N-1)
    print("  Computing EWMA features...")
    ewma = ewma_features(game_stats)
    print(f"  EWMA rows: {len(ewma)}")

    # Step 3: Build matchup-level features
    print("  Building matchup features...")
    features = build_matchup_features(schedules_path, ewma, odds_path)
    print(f"  Matchup rows: {len(features)}")

    # Step 4: Save
    out_dir = Path(output_path).parent
    out_dir.mkdir(parents=True, exist_ok=True)
    features.to_parquet(output_path, index=False)
    print(f"\n  Saved to {output_path}")

    csv_path = output_path.replace(".parquet", ".csv")
    features.to_csv(csv_path, index=False)
    print(f"  CSV copy: {csv_path}")

    # Summary
    feat_cols = [c for c in features.columns if c.startswith("home_off") or c.startswith("away_off")]
    non_null = features[feat_cols[0]].notna().sum() if feat_cols else 0
    complete = features.dropna(subset=["margin"])
    print(f"\n  Games with results: {len(complete)}")
    print(f"  Games with EWMA features: {non_null}")
    if "spread_home_close" in features.columns:
        with_odds = features.spread_home_close.notna().sum()
        print(f"  Games with closing odds: {with_odds}")

    return features


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build NFL weekly EPA feature store")
    parser.add_argument("--seasons", nargs=2, type=int, default=[2014, 2025],
                        help="Start and end season (inclusive)")
    parser.add_argument("--output", default="data/nfl/features/weekly_epa.parquet")
    args = parser.parse_args()

    build_feature_store(
        seasons=tuple(args.seasons),
        output_path=args.output,
    )
