#!/usr/bin/env python3
"""
Build NRL Elo features using post-match deserved margin updates.

The target season is still predicted fairly:
  - pre-game Elo features are written before the match is updated
  - after the match, a deserved-margin model estimates how much the
    underlying stats supported each side
  - Elo is updated with a blend of the actual result and deserved result

This script only replaces the target season's Elo-derived feature columns:
  - elo_diff
  - home_elo_win_prob
  - elo_predicted_margin
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, r2_score
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
    for path in sorted((stats_root / str(season)).glob(f"NRL{season}*.json")):
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
        raise SystemExit(f"No training stat rows found for seasons {train_seasons}")

    x = [row["features_a"] for row in train_rows]
    y = [row["margin_a"] for row in train_rows]
    model = make_pipeline(StandardScaler(), Ridge(alpha=10.0))
    model.fit(x, y)
    pred = model.predict(x)
    metrics = {
        "train_rows": len(train_rows),
        "train_mae": mean_absolute_error(y, pred),
        "train_r2": r2_score(y, pred),
    }
    return model, metrics


def score_key(row: dict) -> str:
    return f"{int(float(row['actual_margin'])):+d}:{int(float(row['actual_total'])):d}"


def feature_key(home: str, away: str, margin: float, total: float) -> tuple[str, str, str]:
    return (home, away, f"{int(margin):+d}:{int(total):d}")


def build_deserved_map(model, target_season: int, stats_root: Path) -> dict[tuple[str, str, str], dict]:
    out = {}
    for row in stats_rows_for_season(target_season, stats_root):
        pred_a = float(model.predict([row["features_a"]])[0])
        a = row["team_a"]
        b = row["team_b"]
        margin_a = row["margin_a"]
        total = row["total"]
        out[feature_key(a, b, margin_a, total)] = {
            "match_id": row["match_id"],
            "deserved_home_margin": pred_a,
            "stats_team_order": "normal",
        }
        out[feature_key(b, a, -margin_a, total)] = {
            "match_id": row["match_id"],
            "deserved_home_margin": -pred_a,
            "stats_team_order": "reversed",
        }
    return out


def initial_ratings(game_log_rows: list[dict], target_season: int) -> dict[str, float]:
    ratings: dict[str, float] = {}
    for row in game_log_rows:
        if int(row["season"]) != target_season:
            continue
        for side, elo_col in (("home_team", "home_elo"), ("away_team", "away_elo")):
            team = row[side]
            if team not in ratings and row.get(elo_col) not in ("", None):
                ratings[team] = float(row[elo_col])
    return ratings


def actual_score_from_margin(margin: float) -> float:
    if margin > 0:
        return 1.0
    if margin < 0:
        return 0.0
    return 0.5


def overlay_target_season(
    rows: list[dict],
    game_log_rows: list[dict],
    deserved_map: dict[tuple[str, str, str], dict],
    target_season: int,
    blend_weight: float,
    margin_scale: float,
) -> tuple[list[dict], list[dict]]:
    ratings = initial_ratings(game_log_rows, target_season)
    audit = []
    out_rows = []

    for row in rows:
        out = dict(row)
        if int(row["season"]) != target_season:
            out_rows.append(out)
            continue

        home = row["home_team"]
        away = row["away_team"]
        ratings.setdefault(home, STARTING_ELO)
        ratings.setdefault(away, STARTING_ELO)

        home_elo = ratings[home]
        away_elo = ratings[away]
        elo_diff = home_elo - away_elo
        home_prob = expected_score(home_elo, away_elo)
        pred_margin = elo_diff * POINTS_PER_ELO + HOME_ADVANTAGE

        out["elo_diff"] = f"{elo_diff:.2f}"
        out["home_elo_win_prob"] = f"{home_prob:.4f}"
        out["elo_predicted_margin"] = f"{pred_margin:.2f}"

        actual_margin = float(row["actual_margin"])
        actual_score = actual_score_from_margin(actual_margin)
        deserved = deserved_map.get((home, away, score_key(row)))
        deserved_margin = float(deserved["deserved_home_margin"]) if deserved else actual_margin
        deserved_score = margin_to_score(deserved_margin, margin_scale)
        blended_score = (1.0 - blend_weight) * actual_score + blend_weight * deserved_score

        standard_delta = K_FACTOR * (actual_score - home_prob)
        deserved_delta = K_FACTOR * (blended_score - home_prob)
        ratings[home] = home_elo + deserved_delta
        ratings[away] = away_elo - deserved_delta

        audit.append(
            {
                "date": row["date"],
                "home_team": home,
                "away_team": away,
                "actual_margin": round(actual_margin, 2),
                "deserved_margin": round(deserved_margin, 2),
                "luck_gap": round(actual_margin - deserved_margin, 2),
                "actual_score": round(actual_score, 4),
                "deserved_score": round(deserved_score, 4),
                "blended_score": round(blended_score, 4),
                "standard_home_delta": round(standard_delta, 3),
                "deserved_home_delta": round(deserved_delta, 3),
                "blend_weight": blend_weight,
                "margin_scale": margin_scale,
                "match_id": deserved.get("match_id", "") if deserved else "",
                "pregame_home_elo": round(home_elo, 2),
                "pregame_away_elo": round(away_elo, 2),
                "postgame_home_elo": round(ratings[home], 2),
                "postgame_away_elo": round(ratings[away], 2),
            }
        )
        out_rows.append(out)

    return out_rows, audit


def parse_train_seasons(value: str, target_season: int) -> list[int]:
    if value:
        return [int(part.strip()) for part in value.split(",") if part.strip()]
    return [season for season in range(2022, target_season) if (ROOT / f"ml/data/match_stats/{season}").exists()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build NRL deserved-margin Elo overlay")
    parser.add_argument("--features", default=str(ROOT / "ml/results/features.csv"))
    parser.add_argument("--game-log-features", default=str(ROOT / "ml/results/game_log_features.csv"))
    parser.add_argument("--stats-root", default=str(ROOT / "ml/data/match_stats"))
    parser.add_argument("--target-season", type=int, default=2024)
    parser.add_argument("--train-seasons", default="")
    parser.add_argument("--blend-weight", type=float, default=0.30)
    parser.add_argument("--margin-scale", type=float, default=10.0)
    parser.add_argument("--out", default=str(ROOT / "ml/results/features_deserved_margin_overlay_2024.csv"))
    parser.add_argument("--audit-out", default=str(ROOT / "outputs/nrl_deserved_margin/season_2024_audit.csv"))
    args = parser.parse_args()

    stats_root = Path(args.stats_root)
    train_seasons = parse_train_seasons(args.train_seasons, args.target_season)
    model, metrics = train_deserved_model(train_seasons, stats_root)
    deserved_map = build_deserved_map(model, args.target_season, stats_root)

    rows = load_csv(Path(args.features))
    game_log_rows = load_csv(Path(args.game_log_features))
    out_rows, audit = overlay_target_season(
        rows,
        game_log_rows,
        deserved_map,
        args.target_season,
        args.blend_weight,
        args.margin_scale,
    )

    write_csv(out_rows, Path(args.out), list(rows[0].keys()))
    write_csv(audit, Path(args.audit_out), list(audit[0].keys()))

    matched = sum(1 for row in audit if row["match_id"])
    print(f"Trained deserved-margin model on seasons {train_seasons}")
    print(f"Training rows: {metrics['train_rows']}")
    print(f"Training MAE: {metrics['train_mae']:.2f}")
    print(f"Training R2: {metrics['train_r2']:.3f}")
    print(f"Wrote {args.out}")
    print(f"Wrote {args.audit_out}")
    print(f"Target season games replayed: {len(audit)}")
    print(f"Matched deserved margins: {matched}/{len(audit)}")


if __name__ == "__main__":
    main()
