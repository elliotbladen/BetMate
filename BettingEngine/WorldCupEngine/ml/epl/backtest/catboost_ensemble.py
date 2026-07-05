"""
CatBoost ensemble layer (T8) for EPL model.

Architecture:
  Input:  Base model probs (D-C + Elo blend) + T2/T3/T6 features
  Output: Refined H2H probabilities + over25 probability

Two models:
  1. H2H classifier  — CatBoostClassifier (3 classes: H/D/A)
  2. Totals regressor — CatBoostClassifier (binary: over25 or not)

Walk-forward validation:
  Train: 2017/18 – 2020/21  (4 seasons, ~1,520 rows)
  Test:  2021/22 – 2023/24  (3 seasons, ~1,140 rows)

  Then re-train on 2017/18–2022/23, evaluate 2023/24 as the final out-of-sample.

Usage:
    python ml/epl/backtest/catboost_ensemble.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from catboost import CatBoostClassifier, Pool
from sklearn.isotonic import IsotonicRegression

DATA_DIR   = Path(__file__).parent.parent / "data" / "clv"
FEATURES_CSV = DATA_DIR / "features_all_seasons.csv"
RESULTS_CSV  = DATA_DIR / "backtest_results.csv"

TRAIN_SEASONS = ["2017/18", "2018/19", "2019/20", "2020/21"]
TEST_SEASONS  = ["2021/22", "2022/23", "2023/24"]

# Features fed to CatBoost (base model probabilities + T2/T3/T6)
H2H_FEATURES = [
    # Base model signal
    "p_home", "p_draw", "p_away",
    "elo_diff",
    "lambda", "mu",
    # T2 pressing
    "ppda_home", "ppda_away", "ppda_diff",
    # T3 momentum
    "rest_days_home", "rest_days_away", "rest_diff",
    "form5_home", "form5_away", "form5_diff",
    # T6 referee
    "ref_home_win_rate", "ref_goals_pg", "ref_cards_pg",
]

TOTALS_FEATURES = [
    # Base model signal
    "lambda", "mu",
    "ppda_home", "ppda_away", "ppda_sum",
    "rest_days_home", "rest_days_away",
    "form5_home", "form5_away",
    "ref_goals_pg", "ref_cards_pg",
]


def rps(p_home: float, p_draw: float, p_away: float, result: str) -> float:
    o = [1,0,0] if result == "H" else ([0,1,0] if result == "D" else [0,0,1])
    p = [p_home, p_draw, p_away]
    return float(np.mean((np.cumsum(p) - np.cumsum(o)) ** 2))


def load_data() -> pd.DataFrame:
    if not FEATURES_CSV.exists():
        raise FileNotFoundError(f"Run walk_forward.py first to generate {FEATURES_CSV}")
    df = pd.read_csv(FEATURES_CSV)
    print(f"Loaded {len(df)} rows across seasons: {sorted(df['season'].unique())}")
    return df


def prepare(df: pd.DataFrame, features: list[str]) -> tuple[np.ndarray, np.ndarray]:
    """Return (X, valid_mask) with NaN rows filled with column median."""
    X = df[features].copy()
    for col in features:
        X[col] = X[col].fillna(X[col].median())
    return X.values


def train_h2h(train_df: pd.DataFrame) -> CatBoostClassifier:
    X = prepare(train_df, H2H_FEATURES)
    y = train_df["result"].map({"H": 0, "D": 1, "A": 2}).values

    model = CatBoostClassifier(
        iterations=400,
        depth=4,
        learning_rate=0.05,
        loss_function="MultiClass",
        eval_metric="MultiClass",
        l2_leaf_reg=5,
        random_seed=42,
        verbose=False,
    )
    model.fit(X, y)
    return model


def train_totals(train_df: pd.DataFrame) -> CatBoostClassifier:
    X = prepare(train_df, TOTALS_FEATURES)
    y = train_df["actual_over25"].values.astype(int)

    model = CatBoostClassifier(
        iterations=400,
        depth=4,
        learning_rate=0.05,
        loss_function="Logloss",
        eval_metric="Logloss",
        l2_leaf_reg=5,
        random_seed=42,
        verbose=False,
    )
    model.fit(X, y)
    return model


def evaluate(
    h2h_model: CatBoostClassifier,
    tot_model: CatBoostClassifier,
    test_df: pd.DataFrame,
) -> dict:
    X_h2h = prepare(test_df, H2H_FEATURES)
    X_tot = prepare(test_df, TOTALS_FEATURES)

    h2h_probs  = h2h_model.predict_proba(X_h2h)   # (n, 3) — H/D/A
    tot_probs  = tot_model.predict_proba(X_tot)[:, 1]  # P(over25)

    # Metrics
    rps_scores = [
        rps(h2h_probs[i,0], h2h_probs[i,1], h2h_probs[i,2], row["result"])
        for i, (_, row) in enumerate(test_df.iterrows())
    ]
    avg_rps = float(np.mean(rps_scores))

    # Baseline RPS (using raw D-C + Elo blend)
    base_rps = [
        rps(row["p_home"], row["p_draw"], row["p_away"], row["result"])
        for _, row in test_df.iterrows()
    ]
    avg_base_rps = float(np.mean(base_rps))

    # H2H accuracy
    preds = h2h_probs.argmax(axis=1)
    actual_idx = test_df["result"].map({"H":0,"D":1,"A":2}).values
    acc = float((preds == actual_idx).mean())

    # Brier for over25
    brier_tot = float(np.mean((tot_probs - test_df["actual_over25"].values) ** 2))

    print(f"  RPS:        base={avg_base_rps:.4f}  catboost={avg_rps:.4f}  "
          f"delta={avg_rps-avg_base_rps:+.4f}")
    print(f"  H2H Acc:    {acc:.1%}")
    print(f"  Brier(tot): {brier_tot:.4f}")

    return {
        "rps_base":     round(avg_base_rps, 4),
        "rps_catboost": round(avg_rps, 4),
        "rps_delta":    round(avg_rps - avg_base_rps, 4),
        "h2h_acc":      round(acc, 4),
        "brier_totals": round(brier_tot, 4),
        "n":            len(test_df),
    }


def feature_importance(model: CatBoostClassifier, features: list[str], label: str):
    imp = model.get_feature_importance()
    ranked = sorted(zip(features, imp), key=lambda x: -x[1])
    print(f"\n  {label} feature importance:")
    for feat, score in ranked[:10]:
        print(f"    {feat:<25} {score:.1f}")


def main():
    df = load_data()

    train_df = df[df["season"].isin(TRAIN_SEASONS)].copy()
    test_df  = df[df["season"].isin(TEST_SEASONS)].copy()

    print(f"\nTrain: {len(train_df)} rows ({', '.join(TRAIN_SEASONS)})")
    print(f"Test:  {len(test_df)} rows ({', '.join(TEST_SEASONS)})")

    # ── Train ──────────────────────────────────────────────────────────────────
    print("\nTraining H2H CatBoost...")
    h2h_model = train_h2h(train_df)

    print("Training Totals CatBoost...")
    tot_model = train_totals(train_df)

    # ── Evaluate on 3 test seasons ────────────────────────────────────────────
    print(f"\n{'='*58}")
    print("  Evaluation: 2021/22 – 2023/24")
    print(f"{'='*58}")
    overall = evaluate(h2h_model, tot_model, test_df)

    print("\n  Per-season breakdown:")
    season_results = []
    for season in TEST_SEASONS:
        s_df = test_df[test_df["season"] == season]
        if s_df.empty:
            continue
        print(f"\n  {season} (n={len(s_df)}):")
        r = evaluate(h2h_model, tot_model, s_df)
        r["season"] = season
        season_results.append(r)

    # ── Feature importance ────────────────────────────────────────────────────
    feature_importance(h2h_model, H2H_FEATURES, "H2H")
    feature_importance(tot_model, TOTALS_FEATURES, "Totals")

    # ── Save results ──────────────────────────────────────────────────────────
    out = {
        "train_seasons": TRAIN_SEASONS,
        "test_seasons": TEST_SEASONS,
        "overall": overall,
        "per_season": season_results,
    }
    out_path = DATA_DIR / "catboost_eval.json"
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
