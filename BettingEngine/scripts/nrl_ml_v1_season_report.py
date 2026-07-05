#!/usr/bin/env python3
"""
Generate an NRL ML v1 season prediction report.

This trains the existing v1 feature set on seasons before the target season,
then predicts every game in the target season. It is intended for baseline
comparison against Elo v2 experiments.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np
import xgboost as xgb
import joblib
from sklearn.metrics import accuracy_score, mean_absolute_error


ROOT = Path(__file__).resolve().parent.parent

FEATURE_COLS = [
    "elo_diff",
    "home_elo_win_prob",
    "elo_predicted_margin",
    "home_rest_days",
    "away_rest_days",
    "rest_diff",
    "home_rest_class",
    "away_rest_class",
    "home_had_bye",
    "away_had_bye",
    "home_prev_margin",
    "away_prev_margin",
    "home_off_big_win",
    "home_off_big_loss",
    "away_off_big_win",
    "away_off_big_loss",
    "home_win_streak",
    "away_win_streak",
    "home_loss_streak",
    "away_loss_streak",
    "home_travel_km",
    "away_travel_km",
    "travel_diff",
    "is_neutral_venue",
    "venue_avg_total",
    "venue_home_win_pct",
    "ref_total_diff",
    "ref_penalty_rate",
    "ref_home_bias",
    "ref_home_win_pct",
    "rain_mm",
    "wind_kmh",
    "wind_gusts_kmh",
    "temp_c",
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


def load_rows(path: Path) -> list[dict]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def load_feature_names(path: Path) -> list[str]:
    with path.open(newline="") as f:
        reader = csv.reader(f)
        try:
            return next(reader)
        except StopIteration:
            return []


def to_arrays(rows: list[dict], feature_cols: list[str]) -> tuple[np.ndarray, np.ndarray]:
    x = []
    weights = []
    for row in rows:
        feats = []
        for col in feature_cols:
            value = row.get(col)
            try:
                feats.append(float(value) if value not in (None, "", "None") else float("nan"))
            except ValueError:
                feats.append(float("nan"))
        x.append(feats)
        weights.append(float(row.get("season_weight", 1.0) or 1.0))
    return np.array(x, dtype=np.float32), np.array(weights, dtype=np.float32)


def train_models(train_rows: list[dict], feature_cols: list[str]):
    x_train, weights = to_arrays(train_rows, feature_cols)
    y_margin = np.array([float(row["actual_margin"]) for row in train_rows])
    y_total = np.array([float(row["actual_total"]) for row in train_rows])
    y_h2h = np.array([int(row["home_win"]) for row in train_rows])

    reg_params = dict(
        n_estimators=400,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=10,
        reg_alpha=0.1,
        reg_lambda=1.0,
        random_state=42,
        verbosity=0,
    )
    cls_params = dict(
        **reg_params,
        eval_metric="logloss",
    )

    margin_model = xgb.XGBRegressor(**reg_params)
    total_model = xgb.XGBRegressor(**reg_params)
    h2h_model = xgb.XGBClassifier(**cls_params)

    margin_model.fit(x_train, y_margin, sample_weight=weights)
    total_model.fit(x_train, y_total, sample_weight=weights)
    h2h_model.fit(x_train, y_h2h, sample_weight=weights)
    return margin_model, total_model, h2h_model


def load_saved_models(models_dir: Path):
    def latest(prefix: str) -> Path:
        files = sorted(models_dir.glob(f"{prefix}_v*.joblib"))
        if not files:
            raise FileNotFoundError(f"No saved {prefix} model found in {models_dir}")
        return files[-1]

    return (
        joblib.load(latest("margin_model")),
        joblib.load(latest("total_model")),
        joblib.load(latest("h2h_model")),
    )


def prediction_rows(target_rows: list[dict], margin_model, total_model, h2h_model, feature_cols: list[str]) -> list[dict]:
    x_target, _ = to_arrays(target_rows, feature_cols)
    margin_pred = margin_model.predict(x_target)
    total_pred = total_model.predict(x_target)
    home_prob = h2h_model.predict_proba(x_target)[:, 1]

    out = []
    for row, ml_margin, ml_total, prob in zip(target_rows, margin_pred, total_pred, home_prob):
        actual_margin = float(row["actual_margin"])
        actual_total = float(row["actual_total"])
        home_team = row["home_team"]
        away_team = row["away_team"]
        ml_pick = home_team if prob >= 0.5 else away_team
        ml_pick_prob = prob if prob >= 0.5 else 1.0 - prob

        if actual_margin > 0:
            actual_winner = home_team
            h2h_correct = int(ml_pick == home_team)
        elif actual_margin < 0:
            actual_winner = away_team
            h2h_correct = int(ml_pick == away_team)
        else:
            actual_winner = "Draw"
            h2h_correct = ""

        out.append(
            {
                "season": row["season"],
                "date": row["date"],
                "home_team": home_team,
                "away_team": away_team,
                "ml_home_prob": round(float(prob), 4),
                "ml_pick_prob": round(float(ml_pick_prob), 4),
                "ml_pick": ml_pick,
                "actual_winner": actual_winner,
                "h2h_correct": h2h_correct,
                "ml_margin": round(float(ml_margin), 2),
                "actual_margin": round(actual_margin, 2),
                "margin_error": round(abs(actual_margin - float(ml_margin)), 2),
                "ml_total": round(float(ml_total), 2),
                "actual_total": round(actual_total, 2),
                "total_error": round(abs(actual_total - float(ml_total)), 2),
                "over_under_ml_line": "OVER" if actual_total > float(ml_total) else ("UNDER" if actual_total < float(ml_total) else "PUSH"),
            }
        )
    return out


def write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_txt(rows: list[dict], path: Path, target_season: int, train_from: int, train_to: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    decided = [row for row in rows if row["h2h_correct"] != ""]
    correct = sum(int(row["h2h_correct"]) for row in decided)
    draws = len(rows) - len(decided)
    acc = correct / len(decided) * 100 if decided else 0.0
    high_conf = [row for row in decided if row["ml_pick_prob"] >= 0.65]
    high_correct = sum(int(row["h2h_correct"]) for row in high_conf)
    med_conf = [row for row in decided if 0.55 < row["ml_pick_prob"] < 0.65]
    med_correct = sum(int(row["h2h_correct"]) for row in med_conf)
    tossups = [row for row in decided if row["ml_pick_prob"] <= 0.55]
    toss_correct = sum(int(row["h2h_correct"]) for row in tossups)

    margin_mae = mean_absolute_error(
        [float(row["actual_margin"]) for row in rows],
        [float(row["ml_margin"]) for row in rows],
    )
    total_mae = mean_absolute_error(
        [float(row["actual_total"]) for row in rows],
        [float(row["ml_total"]) for row in rows],
    )

    lines = [
        "",
        "=" * 155,
        f"  NRL {target_season} - ML v1 Shadow Predictions vs Actual Results  ({len(rows)} games)",
        f"  Train: {train_from}-{train_to}",
        f"  H2H Accuracy: {correct}/{len(decided)} = {acc:.1f}%" + (f"  ({draws} draw excluded)" if draws else ""),
        "=" * 155,
        "",
        "  Date         Home                             Away                              ML%  ML Pick                         Actual Winner                    H2H   ML Mgn  Act Mgn   ML Tot  Act Tot    O/U",
        "  " + "-" * 151,
    ]

    for row in rows:
        mark = "-" if row["h2h_correct"] == "" else ("Y" if int(row["h2h_correct"]) else "N")
        lines.append(
            f"  {row['date']:<10}   {row['home_team']:<32} {row['away_team']:<32} "
            f"{row['ml_pick_prob'] * 100:>5.1f}% {row['ml_pick']:<31} {row['actual_winner']:<31} "
            f"{mark:>3} {float(row['ml_margin']):>8.1f} {float(row['actual_margin']):>8.1f} "
            f"{float(row['ml_total']):>8.1f} {float(row['actual_total']):>8.1f} {row['over_under_ml_line']:>6}"
        )

    def band_line(label: str, band: list[dict], band_correct: int) -> str:
        pct = band_correct / len(band) * 100 if band else 0.0
        return f"  {label:<34} {band_correct:>3}/{len(band):<3} = {pct:>5.1f}%"

    over_count = sum(1 for row in rows if row["over_under_ml_line"] == "OVER")
    under_count = sum(1 for row in rows if row["over_under_ml_line"] == "UNDER")
    lines.extend(
        [
            "",
            "  " + "-" * 151,
            "  SUMMARY",
            f"  H2H overall:     {correct}/{len(decided)} = {acc:.1f}%" + (f"  ({draws} draw excluded)" if draws else ""),
            band_line("High conf (>=65%)", high_conf, high_correct),
            band_line("Medium conf (55-65%)", med_conf, med_correct),
            band_line("Toss-up (<=55%)", tossups, toss_correct),
            f"  Margin MAE:      {margin_mae:.2f} pts",
            f"  Total MAE:       {total_mae:.2f} pts",
            f"  Totals - actual OVER ml line:  {over_count}/{len(rows)} = {over_count / len(rows) * 100:.1f}%",
            f"  Totals - actual UNDER ml line: {under_count}/{len(rows)} = {under_count / len(rows) * 100:.1f}%",
            "",
            "=" * 155,
        ]
    )
    path.write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate an NRL ML v1 season shadow report")
    parser.add_argument("--features", default=str(ROOT / "ml/results/features.csv"))
    parser.add_argument("--target-season", type=int, default=2024)
    parser.add_argument("--train-from", type=int, default=2009)
    parser.add_argument("--train-to", type=int, default=2023)
    parser.add_argument("--out-csv", default=str(ROOT / "results/2024_ml_backtest.csv"))
    parser.add_argument("--out-txt", default=str(ROOT / "results/2024_ml_backtest.txt"))
    parser.add_argument("--use-saved-models", action="store_true",
                        help="Use latest ml/models/*.joblib instead of retraining")
    parser.add_argument("--models-dir", default=str(ROOT / "ml/models"))
    parser.add_argument("--extra-feature-cols", default="",
                        help="Comma-separated extra feature columns to append to the v1 feature set")
    parser.add_argument("--extra-feature-file", default="",
                        help="CSV file whose extra columns should be appended automatically")
    parser.add_argument("--use-v2-features", action="store_true",
                        help="Append the standard additive ML v2 Elo/luck feature columns")
    args = parser.parse_args()

    extra_feature_cols = []
    if args.use_v2_features:
        extra_feature_cols.extend(V2_FEATURE_COLS)
    if args.extra_feature_file:
        extra_cols_from_file = [
            c for c in load_feature_names(Path(args.extra_feature_file))
            if c not in FEATURE_COLS and c not in {"season", "date", "home_team", "away_team",
                                                   "venue", "actual_margin", "actual_total",
                                                   "home_win", "season_weight"}
        ]
        extra_feature_cols.extend(extra_cols_from_file)
    if args.extra_feature_cols:
        extra_feature_cols.extend(col.strip() for col in args.extra_feature_cols.split(",") if col.strip())
    feature_cols = FEATURE_COLS + [col for col in extra_feature_cols if col not in FEATURE_COLS]

    rows = load_rows(Path(args.features))
    train_rows = [
        row for row in rows
        if args.train_from <= int(row["season"]) <= args.train_to
    ]
    target_rows = [
        row for row in rows
        if int(row["season"]) == args.target_season
    ]
    if not args.use_saved_models and not train_rows:
        raise SystemExit("No training rows found")
    if not target_rows:
        raise SystemExit("No target rows found")

    if args.use_saved_models:
        print(f"Loading saved ML v1 models from {args.models_dir}")
    else:
        print(f"Training ML v1 on {len(train_rows)} games ({args.train_from}-{args.train_to})")
    print(f"Predicting {len(target_rows)} games from {args.target_season}")
    if args.use_saved_models and extra_feature_cols:
        raise SystemExit("Saved v1 models cannot use extra feature columns; retrain instead")
    models = load_saved_models(Path(args.models_dir)) if args.use_saved_models else train_models(train_rows, feature_cols)
    preds = prediction_rows(target_rows, *models, feature_cols)
    write_csv(preds, Path(args.out_csv))
    write_txt(preds, Path(args.out_txt), args.target_season, args.train_from, args.train_to)

    decided = [row for row in preds if row["h2h_correct"] != ""]
    correct = sum(int(row["h2h_correct"]) for row in decided)
    print(f"H2H Accuracy: {correct}/{len(decided)} = {correct / len(decided) * 100:.1f}%")
    print(f"Wrote {args.out_csv}")
    print(f"Wrote {args.out_txt}")


if __name__ == "__main__":
    main()
