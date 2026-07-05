#!/usr/bin/env python3
"""
Build a feature matrix with 2024 Elo fields replayed through Elo v2 labels.

Only the target season's Elo-derived columns are changed:
  - elo_diff
  - home_elo_win_prob
  - elo_predicted_margin

All other rows and columns are preserved. This lets us test whether the v1
ML model improves when fed adjusted live Elo features.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
STARTING_ELO = 1500.0
K_FACTOR = 20.0
POINTS_PER_ELO = 0.04
HOME_ADVANTAGE = 3.5

DEFAULT_MULTIPLIERS = {
    "stat_reversal": 0.50,
    "margin_exaggeration": 0.70,
    "close_game_tension": 0.80,
    "report_context_tension": 0.80,
}


def expected_score(r_home: float, r_away: float) -> float:
    return 1.0 / (1.0 + 10.0 ** ((r_away - r_home) / 400.0))


def load_csv(path: Path) -> list[dict]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def write_csv(rows: list[dict], path: Path, fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def score_key(row: dict) -> str:
    return f"{int(float(row['actual_margin'])):+d}:{int(float(row['actual_total'])):d}"


def matchup_key(row: dict) -> tuple[str, str, str]:
    return (row["home_team"], row["away_team"], score_key(row))


def label_key(row: dict) -> tuple[str, str, str]:
    a_score, b_score = row["score"].split("-")
    margin = int(a_score) - int(b_score)
    total = int(a_score) + int(b_score)
    return (row["team_a"], row["team_b"], f"{margin:+d}:{total:d}")


def build_label_map(labels: list[dict]) -> dict[tuple[str, str, str], dict]:
    return {label_key(row): row for row in labels}


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


def overlay_target_season(
    rows: list[dict],
    game_log_rows: list[dict],
    labels: list[dict],
    target_season: int,
    multipliers: dict[str, float],
) -> tuple[list[dict], list[dict]]:
    label_map = build_label_map(labels)
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

        label = label_map.get(matchup_key(row), {})
        adjustment_type = label.get("adjustment_type", "normal")
        is_flagged = label.get("stat_mismatch") == "yes"
        multiplier = multipliers.get(adjustment_type, 1.0) if is_flagged else 1.0

        actual_margin = float(row["actual_margin"])
        if actual_margin > 0:
            actual_home = 1.0
        elif actual_margin < 0:
            actual_home = 0.0
        else:
            actual_home = 0.5

        standard_delta = K_FACTOR * (actual_home - home_prob)
        adjusted_delta = standard_delta * multiplier
        ratings[home] = home_elo + adjusted_delta
        ratings[away] = away_elo - adjusted_delta

        audit.append(
            {
                "date": row["date"],
                "home_team": home,
                "away_team": away,
                "actual_margin": row["actual_margin"],
                "standard_home_delta": round(standard_delta, 3),
                "adjusted_home_delta": round(adjusted_delta, 3),
                "multiplier": multiplier,
                "adjustment_type": adjustment_type if is_flagged else "normal",
                "hard_done_by": label.get("hard_done_by", "") if is_flagged else "",
                "lucky_winner": label.get("lucky_winner", "") if is_flagged else "",
                "pregame_home_elo_v2": round(home_elo, 2),
                "pregame_away_elo_v2": round(away_elo, 2),
                "postgame_home_elo_v2": round(ratings[home], 2),
                "postgame_away_elo_v2": round(ratings[away], 2),
            }
        )
        out_rows.append(out)

    return out_rows, audit


def main() -> None:
    parser = argparse.ArgumentParser(description="Build NRL Elo v2 feature overlay")
    parser.add_argument("--features", default=str(ROOT / "ml/results/features.csv"))
    parser.add_argument("--game-log-features", default=str(ROOT / "ml/results/game_log_features.csv"))
    parser.add_argument("--labels", default=str(ROOT / "outputs/nrl_elo_v2/season_2024_labels.csv"))
    parser.add_argument("--target-season", type=int, default=2024)
    parser.add_argument("--out", default=str(ROOT / "ml/results/features_elo_v2_overlay_2024.csv"))
    parser.add_argument("--audit-out", default=str(ROOT / "outputs/nrl_elo_v2/season_2024_elo_v2_audit.csv"))
    parser.add_argument("--stat-reversal-multiplier", type=float, default=DEFAULT_MULTIPLIERS["stat_reversal"])
    parser.add_argument("--margin-exaggeration-multiplier", type=float, default=DEFAULT_MULTIPLIERS["margin_exaggeration"])
    parser.add_argument("--close-game-multiplier", type=float, default=DEFAULT_MULTIPLIERS["close_game_tension"])
    parser.add_argument("--report-context-multiplier", type=float, default=DEFAULT_MULTIPLIERS["report_context_tension"])
    args = parser.parse_args()

    feature_path = Path(args.features)
    rows = load_csv(feature_path)
    game_log_rows = load_csv(Path(args.game_log_features))
    labels = load_csv(Path(args.labels))

    multipliers = {
        "stat_reversal": args.stat_reversal_multiplier,
        "margin_exaggeration": args.margin_exaggeration_multiplier,
        "close_game_tension": args.close_game_multiplier,
        "report_context_tension": args.report_context_multiplier,
    }
    out_rows, audit = overlay_target_season(rows, game_log_rows, labels, args.target_season, multipliers)
    write_csv(out_rows, Path(args.out), list(rows[0].keys()))
    write_csv(audit, Path(args.audit_out), list(audit[0].keys()))

    changed = sum(1 for row in audit if row["multiplier"] != 1.0)
    print(f"Wrote {args.out}")
    print(f"Wrote {args.audit_out}")
    print(f"Target season games replayed: {len(audit)}")
    print(f"Adjusted Elo updates: {changed}")


if __name__ == "__main__":
    main()
