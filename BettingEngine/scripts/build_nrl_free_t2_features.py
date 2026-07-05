#!/usr/bin/env python3
"""
Build an NRL free-data T2 feature matrix.

This script augments the existing NRL ML feature table with rolling team-style
stats derived from the public Fox Sports match-stat JSONs in:

    ml/data/match_stats/{season}/NRL{season}{round}{match}.json

The added fields are pre-game only:
  - rolling team attack/defence style stats over the last 5 matches
  - season-to-date rolling stats
  - games played so far this season

The output is a new CSV with the original baseline features plus the added T2
columns. It is intended for walk-forward training on 2022-2024 and testing on
2025.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

BASE_FEATURES = ROOT / "ml" / "results" / "features.csv"
MATCH_STATS_ROOT = ROOT / "ml" / "data" / "match_stats"
DEFAULT_OUT = ROOT / "ml" / "results" / "features_nrl_free_t2.csv"
DEFAULT_AUDIT = ROOT / "outputs" / "nrl_free_t2" / "feature_audit.csv"


TEAM_CANON = {
    "Brisbane": "Brisbane Broncos",
    "Canberra": "Canberra Raiders",
    "Canterbury": "Canterbury-Bankstown Bulldogs",
    "Cronulla": "Cronulla-Sutherland Sharks",
    "Gold Coast Titans": "Gold Coast Titans",
    "Manly": "Manly-Warringah Sea Eagles",
    "Melbourne": "Melbourne Storm",
    "Newcastle": "Newcastle Knights",
    "North Queensland": "North Queensland Cowboys",
    "Parramatta": "Parramatta Eels",
    "Penrith": "Penrith Panthers",
    "South Sydney": "South Sydney Rabbitohs",
    "St George Illawarra": "St. George Illawarra Dragons",
    "Wests Tigers": "Wests Tigers",
    "Sydney Roosters": "Sydney Roosters",
    "Warriors": "New Zealand Warriors",
    "Dolphins": "Dolphins",
}


RAW_STAT_MAP = {
    "run_metres": "run_metres",
    "post_contact_metres": "post_contact_metres",
    "line_breaks": "line_breaks",
    "line_break_assists": "line_break_assists",
    "tackle_busts": "tackle_busts",
    "off_loads": "off_loads",
    "effective_offloads": "effective_offloads",
    "tackles": "tackles",
    "missed_tackles": "missed_tackles",
    "tackle_opp20": "tackledOpp20",
    "tackle_opp_half": "tackle_opp_half",
    "forced_drop_outs": "forced_drop_outs",
    "possession_percentage": "possession_percentage",
    "territory": "territory",
    "complete_sets": "complete_sets",
    "total_sets": "total_sets",
    "errors": "errors",
    "in_complete_sets": "inCompleteSets",
    "penalties_conceded": "penalties_conceded",
    "kick_metres": "kick_metres",
    "play_the_balls": "play_the_balls",
    "general_play_pass": "general_play_pass",
    "supports": "supports",
    "options": "options",
    "line_engagements": "line_engagements",
}

WINDOWS = (5, "season")


def canon_team(name: str) -> str:
    return TEAM_CANON.get(str(name).strip(), str(name).strip())


def num(value) -> float:
    if value in (None, ""):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if "/" in text:
        left, right = text.split("/", 1)
        try:
            return float(left) / float(right)
        except (TypeError, ValueError, ZeroDivisionError):
            return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def pct_from_sets(stats: dict) -> float:
    complete = num(stats.get("complete_sets"))
    total = num(stats.get("total_sets"))
    if total <= 0:
        return 0.0
    return (complete / total) * 100.0


def stat_value(stats: dict, feature_name: str) -> float:
    if feature_name == "completion_rate_pct":
        return pct_from_sets(stats)
    raw_key = RAW_STAT_MAP[feature_name]
    return num(stats.get(raw_key))


def feature_names() -> list[str]:
    cols = []
    for side in ("home", "away"):
        for window in WINDOWS:
            suffix = "season" if window == "season" else f"last{window}"
            for feat in RAW_STAT_MAP:
                cols.append(f"{side}_nrl_t2_{feat}_{suffix}")
            cols.append(f"{side}_nrl_t2_games_played_{suffix}")
    return cols


def load_rows(path: Path) -> list[dict]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def load_raw_match_stats(season: int, stats_root: Path) -> list[dict]:
    rows = []
    season_dir = stats_root / str(season)
    if not season_dir.exists():
        return rows

    for path in sorted(season_dir.glob(f"NRL{season}*.json")):
        data = json.loads(path.read_text())
        team_a = data["team_A"]
        team_b = data["team_B"]
        rows.append(
            {
                "match_id": data["match_id"],
                "home_team": canon_team(team_a["name"]),
                "away_team": canon_team(team_b["name"]),
                "home_stats": team_a["stats"],
                "away_stats": team_b["stats"],
            }
        )
    return rows


def canonical_pair(home: str, away: str) -> tuple[str, str]:
    return canon_team(home), canon_team(away)


def align_season_rows(base_rows: list[dict], raw_rows: list[dict], season: int) -> tuple[list[dict], list[dict], list[dict]]:
    """Align one season's base rows to raw match-stat rows.

    We pair matches by (home_team, away_team) occurrence order. This is
    necessary because some team pairs meet multiple times per season.
    """
    base_grouped: dict[tuple[str, str], list[tuple[int, dict]]] = defaultdict(list)
    raw_grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)

    for idx, row in enumerate(base_rows):
        if int(row["season"]) != season:
            continue
        pair = canonical_pair(row["home_team"], row["away_team"])
        base_grouped[pair].append((idx, row))

    for raw in raw_rows:
        pair = canonical_pair(raw["home_team"], raw["away_team"])
        raw_grouped[pair].append(raw)

    aligned = []
    audit = []

    all_pairs = sorted(set(base_grouped) | set(raw_grouped))
    for pair in all_pairs:
        base_list = sorted(base_grouped.get(pair, []), key=lambda x: (x[1]["date"], x[1]["home_team"], x[1]["away_team"]))
        raw_list = sorted(raw_grouped.get(pair, []), key=lambda x: x["match_id"])

        if len(base_list) != len(raw_list):
            audit.append(
                {
                    "season": season,
                    "pair": f"{pair[0]} vs {pair[1]}",
                    "base_rows": len(base_list),
                    "raw_rows": len(raw_list),
                    "status": "count_mismatch",
                }
            )

        for (base_idx, base_row), raw_row in zip(base_list, raw_list):
            aligned.append(
                {
                    "base_idx": base_idx,
                    "base_row": base_row,
                    "raw_row": raw_row,
                }
            )

    # Return in date order so rolling stats are built in chronological order.
    aligned.sort(key=lambda x: (x["base_row"]["date"], x["base_row"]["home_team"], x["base_row"]["away_team"]))
    return aligned, audit, raw_rows


def rolling_mean(history: list[dict], feature_name: str, window: int | None = None) -> float:
    if not history:
        return 0.0
    items = history[-window:] if window else history
    vals = [stat_value(h, feature_name) for h in items]
    return sum(vals) / len(vals) if vals else 0.0


def build_features(base_rows: list[dict], stats_root: Path) -> tuple[list[dict], list[dict]]:
    out_rows: list[dict] = []
    audit_rows: list[dict] = []

    # Keep history across seasons so each row only sees prior matches.
    team_history: dict[str, list[dict]] = defaultdict(list)

    seasons = sorted({int(r["season"]) for r in base_rows if int(r["season"]) >= 2022})
    base_by_season: dict[int, list[dict]] = {
        season: [r for r in base_rows if int(r["season"]) == season] for season in seasons
    }

    for season in seasons:
        raw_rows = load_raw_match_stats(season, stats_root)
        aligned, season_audit, _ = align_season_rows(base_rows, raw_rows, season)
        audit_rows.extend(season_audit)

        for item in aligned:
            row = dict(item["base_row"])
            raw = item["raw_row"]
            home = row["home_team"]
            away = row["away_team"]
            home_hist = team_history[home]
            away_hist = team_history[away]

            row["home_nrl_t2_games_played_season"] = str(len(home_hist))
            row["away_nrl_t2_games_played_season"] = str(len(away_hist))
            row["home_nrl_t2_games_played_last5"] = str(min(len(home_hist), 5))
            row["away_nrl_t2_games_played_last5"] = str(min(len(away_hist), 5))

            for feat in RAW_STAT_MAP:
                row[f"home_nrl_t2_{feat}_season"] = f"{rolling_mean(home_hist, feat):.4f}"
                row[f"away_nrl_t2_{feat}_season"] = f"{rolling_mean(away_hist, feat):.4f}"
                row[f"home_nrl_t2_{feat}_last5"] = f"{rolling_mean(home_hist, feat, 5):.4f}"
                row[f"away_nrl_t2_{feat}_last5"] = f"{rolling_mean(away_hist, feat, 5):.4f}"

            out_rows.append(row)

            # Update histories after the match is processed.
            home_record = dict(raw["home_stats"])
            away_record = dict(raw["away_stats"])
            team_history[home].append(home_record)
            team_history[away].append(away_record)

    # Fill rows before 2022 with zeros so the output remains compatible with
    # the original feature table.
    extra_cols = feature_names()
    for row in out_rows:
        if int(row["season"]) < 2022:
            for col in extra_cols:
                row[col] = "0"
        else:
            for col in extra_cols:
                row.setdefault(col, "0")

    return out_rows, audit_rows


def write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build NRL free-data T2 features")
    parser.add_argument("--features", default=str(BASE_FEATURES))
    parser.add_argument("--stats-root", default=str(MATCH_STATS_ROOT))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--audit-out", default=str(DEFAULT_AUDIT))
    args = parser.parse_args()

    base_rows = load_rows(Path(args.features))
    out_rows, audit = build_features(base_rows, Path(args.stats_root))
    write_csv(out_rows, Path(args.out))

    if audit:
        Path(args.audit_out).parent.mkdir(parents=True, exist_ok=True)
        with Path(args.audit_out).open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(audit[0].keys()))
            writer.writeheader()
            writer.writerows(audit)

    print(f"Wrote {args.out}")
    print(f"Rows: {len(out_rows)}")
    print(f"Added {len(feature_names())} free T2 columns")
    if audit:
        print(f"Audit rows: {len(audit)}")


if __name__ == "__main__":
    main()
