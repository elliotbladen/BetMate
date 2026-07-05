#!/usr/bin/env python3
"""
Build a richer AFL Tier 2 snapshot table from public data.

This script combines:
  - AFL Tables game-level team stats for rolling form
  - Footywire season snapshots for advanced style fields

Output:
  data/afl_public_snapshots.csv

The output keeps the same field names the AFL T2 engine already knows how to
read, but refreshes them from rolling match data instead of relying only on the
older static Footywire season averages.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
GAME_STATS_CSV = ROOT / "outputs" / "afl_game_stats" / "afl_game_team_stats_2024_2025.csv"
FOOTYWIRE_SNAPSHOT_CSV = ROOT / "data" / "footywire_snapshots.csv"
FOOTYWIRE_HIST_CSV = ROOT / "data" / "footywire_team_stats.csv"
OUT_CSV = ROOT / "data" / "afl_public_snapshots.csv"

OUTPUT_FIELDS = [
    "season",
    "round_number",
    "team_name",
    "games",
    "kicks_pg",
    "handballs_pg",
    "disposals_pg",
    "marks_pg",
    "goals_pg",
    "behinds_pg",
    "goal_assists_pg",
    "inside_50s_pg",
    "rebound_50s_pg",
    "tackles_pg",
    "hitouts_pg",
    "frees_for_pg",
    "frees_ag_pg",
    "clearances_pg",
    "clangers_pg",
    "cp_pg",
    "up_pg",
    "eff_disposals_pg",
    "disposal_eff_pct",
    "cont_marks_pg",
    "marks_i50_pg",
    "one_pct_pg",
    "bounces_pg",
    "centre_cl_pg",
    "stoppage_cl_pg",
    "metres_gained_total",
    "turnovers_pg",
    "intercepts_pg",
    "tackles_i50_pg",
    "goal_conv_pct",
    "kicking_ratio",
    "mg_pg",
    "source_game_rows",
    "source_mix",
]


ROUND_FINALS = {
    "qualifying final": 101,
    "elimination final": 102,
    "semi final": 103,
    "preliminary final": 104,
    "grand final": 105,
}


def parse_round_number(label: str) -> int | None:
    text = (label or "").strip().lower()
    if text.isdigit():
        return int(text)
    m = re.search(r"round\s+(\d+)", text)
    if m:
        return int(m.group(1))
    for key, value in ROUND_FINALS.items():
        if key in text:
            return value
    return None


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, low_memory=False)


def safe_mean(series: pd.Series) -> float | None:
    if series.empty:
        return None
    return float(series.mean())


def safe_ratio(num: float | None, den: float | None) -> float | None:
    if num is None or den in (None, 0):
        return None
    return float(num / den)


def first_value(*values):
    for value in values:
        if value is not None and pd.notna(value):
            return value
    return None


def latest_row(df: pd.DataFrame, season: int, team: str, round_number: int | None) -> dict:
    if df.empty:
        return {}
    subset = df[(df["season"] == season) & (df["team_name"] == team)]
    if round_number is not None and "round_number" in subset.columns:
        subset = subset[pd.to_numeric(subset["round_number"], errors="coerce") <= round_number]
    if subset.empty:
        return {}
    row = subset.sort_values([c for c in ("round_number", "games") if c in subset.columns]).iloc[-1]
    return row.to_dict()


def team_game_rollup(team_games: pd.DataFrame) -> dict:
    if team_games.empty:
        return {}

    games = len(team_games)
    shots = team_games["goals"].sum() + team_games["behinds"].sum()
    kicks = team_games["kicks"].sum()
    handballs = team_games["handballs"].sum()

    rollup = {
        "games": float(games),
        "kicks_pg": safe_mean(team_games["kicks"]),
        "handballs_pg": safe_mean(team_games["handballs"]),
        "disposals_pg": safe_mean(team_games["disposals"]),
        "marks_pg": safe_mean(team_games["marks"]),
        "goals_pg": safe_mean(team_games["goals"]),
        "behinds_pg": safe_mean(team_games["behinds"]),
        "goal_assists_pg": safe_mean(team_games["goal_assists"]),
        "inside_50s_pg": safe_mean(team_games["inside_50s"]),
        "rebound_50s_pg": safe_mean(team_games["rebound_50s"]),
        "tackles_pg": safe_mean(team_games["tackles"]),
        "hitouts_pg": safe_mean(team_games["hitouts"]),
        "frees_for_pg": safe_mean(team_games["frees_for"]),
        "frees_ag_pg": safe_mean(team_games["frees_against"]),
        "clearances_pg": safe_mean(team_games["clearances"]),
        "clangers_pg": safe_mean(team_games["clangers"]),
        "cp_pg": safe_mean(team_games["contested_possessions"]),
        "up_pg": safe_mean(team_games["uncontested_possessions"]),
        "cont_marks_pg": safe_mean(team_games["contested_marks"]),
        "marks_i50_pg": safe_mean(team_games["marks_inside_50"]),
        "one_pct_pg": safe_mean(team_games["one_percenters"]),
        "bounces_pg": safe_mean(team_games["bounces"]),
        "goal_conv_pct": safe_ratio(team_games["goals"].sum(), shots),
        "kicking_ratio": safe_ratio(kicks, kicks + handballs),
        "source_game_rows": float(games),
        "source_mix": "afl_tables",
    }
    return rollup


def build_snapshots(game_df: pd.DataFrame, fw_snap: pd.DataFrame, fw_hist: pd.DataFrame) -> pd.DataFrame:
    if game_df.empty and fw_snap.empty and fw_hist.empty:
        return pd.DataFrame(columns=OUTPUT_FIELDS)

    frames = []
    if not game_df.empty:
        game_df = game_df.copy()
        game_df["round_number"] = game_df["round_label"].map(parse_round_number)
        game_df["season"] = pd.to_numeric(game_df["season"], errors="coerce")
        game_df["game_number"] = pd.to_numeric(game_df["game_number"], errors="coerce")
        game_df = game_df.dropna(subset=["season", "round_number", "team"])
        game_df["season"] = game_df["season"].astype(int)
        game_df["round_number"] = game_df["round_number"].astype(int)
        game_df["game_number"] = game_df["game_number"].astype(int)
        frames.append(game_df)

    if not fw_snap.empty:
        fw_snap = fw_snap.copy()
        fw_snap["season"] = pd.to_numeric(fw_snap["season"], errors="coerce")
        fw_snap["round_number"] = pd.to_numeric(fw_snap["round_number"], errors="coerce")
        fw_snap = fw_snap.dropna(subset=["season", "round_number", "team_name"])
        fw_snap["season"] = fw_snap["season"].astype(int)
        fw_snap["round_number"] = fw_snap["round_number"].astype(int)
        frames.append(fw_snap)

    if not fw_hist.empty:
        fw_hist = fw_hist.copy()
        fw_hist["season"] = pd.to_numeric(fw_hist["season"], errors="coerce")
        fw_hist = fw_hist.dropna(subset=["season", "team_name"])
        fw_hist["season"] = fw_hist["season"].astype(int)

    seasons = sorted({int(s) for f in frames for s in f["season"].dropna().unique()})
    if not seasons and not fw_hist.empty:
        seasons = sorted(fw_hist["season"].dropna().astype(int).unique().tolist())

    out_rows: list[dict] = []
    for season in seasons:
        season_games = game_df[game_df["season"] == season] if not game_df.empty else pd.DataFrame()
        season_teams = set()
        if not season_games.empty:
            season_teams.update(season_games["team"].dropna().astype(str).unique().tolist())
        if not fw_snap.empty:
            season_teams.update(fw_snap[fw_snap["season"] == season]["team_name"].dropna().astype(str).unique().tolist())
        if not fw_hist.empty:
            season_teams.update(fw_hist[fw_hist["season"] == season]["team_name"].dropna().astype(str).unique().tolist())
        if not season_teams:
            continue

        round_sources = []
        if not season_games.empty:
            round_sources.extend(season_games["round_number"].dropna().astype(int).unique().tolist())
        if not fw_snap.empty:
            round_sources.extend(fw_snap[fw_snap["season"] == season]["round_number"].dropna().astype(int).unique().tolist())
        round_numbers = sorted(set(round_sources))
        if not round_numbers and not season_games.empty:
            round_numbers = sorted(season_games["round_number"].dropna().astype(int).unique().tolist())

        for round_number in round_numbers:
            for team in sorted(season_teams):
                team_games = pd.DataFrame()
                if not season_games.empty:
                    team_games = season_games[
                        (season_games["team"] == team) & (season_games["round_number"] <= round_number)
                    ].sort_values(["round_number", "game_number"])

                rollup = team_game_rollup(team_games)

                fw_row = latest_row(fw_snap, season, team, round_number)
                if not fw_row:
                    fw_row = latest_row(fw_hist, season, team, None)
                if not fw_row and not fw_hist.empty and season > fw_hist["season"].min():
                    fw_row = latest_row(fw_hist, season - 1, team, None)

                row = {
                    "season": season,
                    "round_number": round_number,
                    "team_name": team,
                    "games": first_value(rollup.get("games"), fw_row.get("games")),
                    "kicks_pg": first_value(rollup.get("kicks_pg"), fw_row.get("kicks_pg")),
                    "handballs_pg": first_value(rollup.get("handballs_pg"), fw_row.get("handballs_pg")),
                    "disposals_pg": first_value(rollup.get("disposals_pg"), fw_row.get("disposals_pg")),
                    "marks_pg": first_value(rollup.get("marks_pg"), fw_row.get("marks_pg")),
                    "goals_pg": first_value(rollup.get("goals_pg"), fw_row.get("goals_pg")),
                    "behinds_pg": first_value(rollup.get("behinds_pg"), fw_row.get("behinds_pg")),
                    "goal_assists_pg": first_value(rollup.get("goal_assists_pg"), fw_row.get("goal_assists_pg")),
                    "inside_50s_pg": first_value(rollup.get("inside_50s_pg"), fw_row.get("inside_50s_pg")),
                    "rebound_50s_pg": first_value(rollup.get("rebound_50s_pg"), fw_row.get("rebound_50s_pg")),
                    "tackles_pg": first_value(rollup.get("tackles_pg"), fw_row.get("tackles_pg")),
                    "hitouts_pg": first_value(rollup.get("hitouts_pg"), fw_row.get("hitouts_pg")),
                    "frees_for_pg": first_value(rollup.get("frees_for_pg"), fw_row.get("frees_for_pg")),
                    "frees_ag_pg": first_value(rollup.get("frees_ag_pg"), fw_row.get("frees_ag_pg")),
                    "clearances_pg": first_value(rollup.get("clearances_pg"), fw_row.get("clearances_pg")),
                    "clangers_pg": first_value(rollup.get("clangers_pg"), fw_row.get("clangers_pg")),
                    "cp_pg": first_value(rollup.get("cp_pg"), fw_row.get("cp_pg")),
                    "up_pg": first_value(rollup.get("up_pg"), fw_row.get("up_pg")),
                    "eff_disposals_pg": fw_row.get("eff_disposals_pg"),
                    "disposal_eff_pct": fw_row.get("disposal_eff_pct"),
                    "cont_marks_pg": first_value(rollup.get("cont_marks_pg"), fw_row.get("cont_marks_pg")),
                    "marks_i50_pg": first_value(rollup.get("marks_i50_pg"), fw_row.get("marks_i50_pg")),
                    "one_pct_pg": first_value(rollup.get("one_pct_pg"), fw_row.get("one_pct_pg")),
                    "bounces_pg": first_value(rollup.get("bounces_pg"), fw_row.get("bounces_pg")),
                    "centre_cl_pg": fw_row.get("centre_cl_pg"),
                    "stoppage_cl_pg": fw_row.get("stoppage_cl_pg"),
                    "metres_gained_total": fw_row.get("metres_gained_total"),
                    "turnovers_pg": fw_row.get("turnovers_pg"),
                    "intercepts_pg": fw_row.get("intercepts_pg"),
                    "tackles_i50_pg": fw_row.get("tackles_i50_pg"),
                    "goal_conv_pct": first_value(rollup.get("goal_conv_pct"), fw_row.get("goal_conv_pct")),
                    "kicking_ratio": first_value(rollup.get("kicking_ratio"), fw_row.get("kicking_ratio")),
                    "mg_pg": fw_row.get("mg_pg"),
                    "source_game_rows": first_value(rollup.get("source_game_rows"), 0.0),
                    "source_mix": "afl_tables+footywire" if fw_row else "afl_tables",
                }
                out_rows.append(row)

    out_df = pd.DataFrame(out_rows)
    if out_df.empty:
        return pd.DataFrame(columns=OUTPUT_FIELDS)

    for field in OUTPUT_FIELDS:
        if field not in out_df.columns:
            out_df[field] = None
    out_df = out_df[OUTPUT_FIELDS].sort_values(["season", "round_number", "team_name"]).reset_index(drop=True)
    return out_df


def main() -> int:
    parser = argparse.ArgumentParser(description="Build richer AFL public T2 snapshot rows.")
    parser.add_argument("--game-stats", default=str(GAME_STATS_CSV))
    parser.add_argument("--footywire-snapshots", default=str(FOOTYWIRE_SNAPSHOT_CSV))
    parser.add_argument("--footywire-history", default=str(FOOTYWIRE_HIST_CSV))
    parser.add_argument("--out", default=str(OUT_CSV))
    args = parser.parse_args()

    game_df = load_csv(Path(args.game_stats))
    fw_snap = load_csv(Path(args.footywire_snapshots))
    fw_hist = load_csv(Path(args.footywire_history))

    out_df = build_snapshots(game_df, fw_snap, fw_hist)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(out_path, index=False)
    print(f"Wrote {out_path} ({len(out_df)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
