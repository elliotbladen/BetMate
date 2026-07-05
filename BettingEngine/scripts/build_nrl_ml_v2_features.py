#!/usr/bin/env python3
"""
Build an additive NRL ML v2 feature matrix.

This preserves every v1 feature and appends the learned Elo/luck signals:
  - deserved-margin Elo fields
  - difference between deserved Elo and original Elo fields
  - rolling luck debt for each team

The added fields are pre-game only. After a match is played, the script uses
that match's post-game stats to update deserved Elo and luck debt for future
matches.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parent.parent
STARTING_ELO = 1500.0
K_FACTOR = 20.0
POINTS_PER_ELO = 0.04
HOME_ADVANTAGE = 3.5

TEAM_CANON = {
    "Brisbane": "Brisbane Broncos",
    "Canberra": "Canberra Raiders",
    "Canterbury": "Canterbury-Bankstown Bulldogs",
    "Cronulla": "Cronulla-Sutherland Sharks",
    "Gold Coast Titans": "Gold Coast Titans",
    "Manly": "Manly-Warringah Sea Eagles",
    "Melbourne": "Melbourne Storm",
    "Melbourne Storm": "Melbourne Storm",
    "Newcastle": "Newcastle Knights",
    "North Queensland": "North Queensland Cowboys",
    "Parramatta": "Parramatta Eels",
    "Penrith": "Penrith Panthers",
    "Penrith Panthers": "Penrith Panthers",
    "South Sydney": "South Sydney Rabbitohs",
    "St George Illawarra": "St. George Illawarra Dragons",
    "Sydney Roosters": "Sydney Roosters",
    "Warriors": "New Zealand Warriors",
    "Wests Tigers": "Wests Tigers",
    "Dolphins": "Dolphins",
}

PROCESS_STATS = [
    "run_metres",
    "post_contact_metres",
    "runs",
    "runs_8plus_meters",
    "tackle_busts",
    "off_loads",
    "effective_offloads",
    "line_breaks",
    "line_break_assists",
    "tackledOpp20",
    "tackle_opp_half",
    "forced_drop_outs",
    "possession_percentage",
    "territory",
    "complete_sets",
    "total_sets",
    "errors",
    "inCompleteSets",
    "penalties_conceded",
    "penaltiesAwarded",
    "set_restart_infringements_awarded",
    "set_restart_infringements_conceded",
    "sin_bins",
    "send_offs",
    "missed_tackles",
    "kick_metres",
    "long_kicks",
    "attacking_kicks",
    "kicks_dead",
    "drop_outs",
]

V2_FEATURE_COLS = [
    "dm_elo_diff",
    "dm_home_elo_win_prob",
    "dm_elo_predicted_margin",
    "dm_elo_diff_delta",
    "dm_home_prob_delta",
    "dm_pred_margin_delta",
    "home_luck_debt",
    "away_luck_debt",
    "luck_debt_diff",
]


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


def expected_score(r_home: float, r_away: float) -> float:
    return 1.0 / (1.0 + 10.0 ** ((r_away - r_home) / 400.0))


def margin_to_score(margin: float, scale: float) -> float:
    return 1.0 / (1.0 + math.exp(-margin / scale))


def actual_score_from_margin(margin: float) -> float:
    if margin > 0:
        return 1.0
    if margin < 0:
        return 0.0
    return 0.5


def load_csv(path: Path) -> list[dict]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def write_csv(rows: list[dict], path: Path, fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def stats_features(a_stats: dict, b_stats: dict) -> list[float]:
    return [num(a_stats.get(key)) - num(b_stats.get(key)) for key in PROCESS_STATS]


def stats_rows_for_season(season: int, stats_root: Path) -> list[dict]:
    rows = []
    season_dir = stats_root / str(season)
    for path in sorted(season_dir.glob(f"NRL{season}*.json")):
        data = json.loads(path.read_text())
        team_a = data["team_A"]
        team_b = data["team_B"]
        a_name = canon_team(team_a["name"])
        b_name = canon_team(team_b["name"])
        a_stats = team_a["stats"]
        b_stats = team_b["stats"]
        a_points = int(num(a_stats.get("points")))
        b_points = int(num(b_stats.get("points")))
        rows.append(
            {
                "season": season,
                "match_id": data["match_id"],
                "team_a": a_name,
                "team_b": b_name,
                "margin_a": float(a_points - b_points),
                "total": float(a_points + b_points),
                "features_a": stats_features(a_stats, b_stats),
            }
        )
    return rows


def train_deserved_model(train_seasons: list[int], stats_root: Path):
    train_rows = []
    for season in train_seasons:
        train_rows.extend(stats_rows_for_season(season, stats_root))
    if not train_rows:
        return None
    x = [row["features_a"] for row in train_rows]
    y = [row["margin_a"] for row in train_rows]
    model = make_pipeline(StandardScaler(), Ridge(alpha=10.0))
    model.fit(x, y)
    return model


def feature_key(home: str, away: str, margin: float, total: float) -> tuple[str, str, str]:
    return (home, away, f"{int(margin):+d}:{int(total):d}")


def score_key(row: dict) -> str:
    return f"{int(float(row['actual_margin'])):+d}:{int(float(row['actual_total'])):d}"


def build_deserved_maps(
    seasons: list[int],
    stats_root: Path,
    first_train_season: int,
) -> dict[int, dict[tuple[str, str, str], dict]]:
    maps = {}
    for season in seasons:
        train_seasons = [y for y in range(first_train_season, season) if (stats_root / str(y)).exists()]
        model = train_deserved_model(train_seasons, stats_root)
        if model is None:
            maps[season] = {}
            continue
        season_map = {}
        for row in stats_rows_for_season(season, stats_root):
            pred_a = float(model.predict([row["features_a"]])[0])
            a = row["team_a"]
            b = row["team_b"]
            margin_a = row["margin_a"]
            total = row["total"]
            season_map[feature_key(a, b, margin_a, total)] = {
                "match_id": row["match_id"],
                "deserved_home_margin": pred_a,
            }
            season_map[feature_key(b, a, -margin_a, total)] = {
                "match_id": row["match_id"],
                "deserved_home_margin": -pred_a,
            }
        maps[season] = season_map
    return maps


def initial_ratings(game_log_rows: list[dict], season: int) -> dict[str, float]:
    ratings: dict[str, float] = {}
    for row in game_log_rows:
        if int(row["season"]) != season:
            continue
        for side, elo_col in (("home_team", "home_elo"), ("away_team", "away_elo")):
            team = row[side]
            if team not in ratings and row.get(elo_col) not in ("", None):
                ratings[team] = float(row[elo_col])
    return ratings


def safe_float(row: dict, key: str) -> float:
    try:
        return float(row.get(key) or 0.0)
    except ValueError:
        return 0.0


def build_features(
    rows: list[dict],
    game_log_rows: list[dict],
    deserved_maps: dict[int, dict[tuple[str, str, str], dict]],
    blend_weight: float,
    margin_scale: float,
    luck_decay: float,
    luck_scale: float,
) -> tuple[list[dict], list[dict]]:
    out_rows = []
    audit = []
    ratings_by_season: dict[int, dict[str, float]] = {}
    luck_by_season: dict[int, dict[str, float]] = {}

    for row in rows:
        season = int(row["season"])
        ratings = ratings_by_season.setdefault(season, initial_ratings(game_log_rows, season))
        luck = luck_by_season.setdefault(season, {})

        home = row["home_team"]
        away = row["away_team"]
        ratings.setdefault(home, STARTING_ELO)
        ratings.setdefault(away, STARTING_ELO)
        luck.setdefault(home, 0.0)
        luck.setdefault(away, 0.0)

        home_elo = ratings[home]
        away_elo = ratings[away]
        dm_elo_diff = home_elo - away_elo
        dm_home_prob = expected_score(home_elo, away_elo)
        dm_pred_margin = dm_elo_diff * POINTS_PER_ELO + HOME_ADVANTAGE

        original_elo_diff = safe_float(row, "elo_diff")
        original_home_prob = safe_float(row, "home_elo_win_prob")
        original_pred_margin = safe_float(row, "elo_predicted_margin")
        home_luck = luck[home]
        away_luck = luck[away]

        out = dict(row)
        out.update(
            {
                "dm_elo_diff": f"{dm_elo_diff:.2f}",
                "dm_home_elo_win_prob": f"{dm_home_prob:.4f}",
                "dm_elo_predicted_margin": f"{dm_pred_margin:.2f}",
                "dm_elo_diff_delta": f"{dm_elo_diff - original_elo_diff:.2f}",
                "dm_home_prob_delta": f"{dm_home_prob - original_home_prob:.4f}",
                "dm_pred_margin_delta": f"{dm_pred_margin - original_pred_margin:.2f}",
                "home_luck_debt": f"{home_luck:.2f}",
                "away_luck_debt": f"{away_luck:.2f}",
                "luck_debt_diff": f"{home_luck - away_luck:.2f}",
            }
        )

        actual_margin = float(row["actual_margin"])
        actual_score = actual_score_from_margin(actual_margin)
        deserved = deserved_maps.get(season, {}).get((home, away, score_key(row)))
        deserved_margin = float(deserved["deserved_home_margin"]) if deserved else actual_margin
        deserved_score = margin_to_score(deserved_margin, margin_scale)
        blended_score = (1.0 - blend_weight) * actual_score + blend_weight * deserved_score
        delta = K_FACTOR * (blended_score - dm_home_prob)
        ratings[home] = home_elo + delta
        ratings[away] = away_elo - delta

        luck_gap = actual_margin - deserved_margin
        luck[home] = home_luck * luck_decay - luck_gap * luck_scale
        luck[away] = away_luck * luck_decay + luck_gap * luck_scale

        audit.append(
            {
                "season": season,
                "date": row["date"],
                "home_team": home,
                "away_team": away,
                "actual_margin": round(actual_margin, 2),
                "deserved_margin": round(deserved_margin, 2),
                "luck_gap": round(luck_gap, 2),
                "pregame_dm_elo_diff": round(dm_elo_diff, 2),
                "pregame_luck_debt_diff": round(home_luck - away_luck, 2),
                "postgame_home_luck_debt": round(luck[home], 2),
                "postgame_away_luck_debt": round(luck[away], 2),
                "match_id": deserved.get("match_id", "") if deserved else "",
            }
        )
        out_rows.append(out)

    return out_rows, audit


def main() -> None:
    parser = argparse.ArgumentParser(description="Build additive NRL ML v2 features")
    parser.add_argument("--features", default=str(ROOT / "ml/results/features.csv"))
    parser.add_argument("--game-log-features", default=str(ROOT / "ml/results/game_log_features.csv"))
    parser.add_argument("--stats-root", default=str(ROOT / "ml/data/match_stats"))
    parser.add_argument("--out", default=str(ROOT / "ml/results/features_ml_v2.csv"))
    parser.add_argument("--audit-out", default=str(ROOT / "outputs/nrl_deserved_margin/ml_v2_feature_audit.csv"))
    parser.add_argument("--first-train-season", type=int, default=2022)
    parser.add_argument("--blend-weight", type=float, default=0.50)
    parser.add_argument("--margin-scale", type=float, default=6.0)
    parser.add_argument("--luck-decay", type=float, default=0.75)
    parser.add_argument("--luck-scale", type=float, default=0.10)
    args = parser.parse_args()

    rows = load_csv(Path(args.features))
    game_log_rows = load_csv(Path(args.game_log_features))
    stats_root = Path(args.stats_root)
    seasons = sorted({int(row["season"]) for row in rows})
    deserved_maps = build_deserved_maps(seasons, stats_root, args.first_train_season)
    out_rows, audit = build_features(
        rows,
        game_log_rows,
        deserved_maps,
        args.blend_weight,
        args.margin_scale,
        args.luck_decay,
        args.luck_scale,
    )
    fieldnames = list(rows[0].keys()) + [col for col in V2_FEATURE_COLS if col not in rows[0]]
    write_csv(out_rows, Path(args.out), fieldnames)
    write_csv(audit, Path(args.audit_out), list(audit[0].keys()))
    matched = sum(1 for row in audit if row["match_id"])

    print(f"Wrote {args.out}")
    print(f"Wrote {args.audit_out}")
    print(f"Rows: {len(out_rows)}")
    print(f"Deserved-margin stat matches: {matched}/{len(audit)}")
    print(f"Added v2 columns: {', '.join(V2_FEATURE_COLS)}")


if __name__ == "__main__":
    main()
