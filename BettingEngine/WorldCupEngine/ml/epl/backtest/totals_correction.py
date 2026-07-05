"""
Simple logistic correction for over25 probability using referee and PPDA signals.

Why not CatBoost: with ~1,500 training rows and 18 features, CatBoost overfits.
A 3-feature logistic model (base_logit + ref_goals_deviation + ppda_sum_deviation)
is interpretable and avoids overfitting.

Improvement path: as more seasons accumulate, graduate to CatBoost.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

DATA_DIR     = Path(__file__).parent.parent / "data" / "clv"
FEATURES_CSV = DATA_DIR / "features_all_seasons.csv"

TRAIN_SEASONS = ["2017/18", "2018/19", "2019/20", "2020/21"]
TEST_SEASONS  = ["2021/22", "2022/23", "2023/24"]


def brier(p: np.ndarray, y: np.ndarray) -> float:
    return float(np.mean((p - y) ** 2))


def main():
    df = pd.read_csv(FEATURES_CSV)

    train = df[df["season"].isin(TRAIN_SEASONS)].copy()
    test  = df[df["season"].isin(TEST_SEASONS)].copy()

    # Base model over25 probability (calibrated odds → prob)
    train["p_over_base"] = 1.0 / train["model_over25"]
    test["p_over_base"]  = 1.0 / test["model_over25"]

    # Deviation features: how different is this match from average
    ref_goals_mean = train["ref_goals_pg"].mean()
    ppda_sum_mean  = train["ppda_sum"].mean()

    train["ref_goals_dev"] = train["ref_goals_pg"] - ref_goals_mean
    train["ppda_sum_dev"]  = train["ppda_sum"]     - ppda_sum_mean
    test["ref_goals_dev"]  = test["ref_goals_pg"]  - ref_goals_mean
    test["ppda_sum_dev"]   = test["ppda_sum"]      - ppda_sum_mean

    # Features: base logit + 2 deviation terms
    def make_X(d):
        logit_base = np.log(d["p_over_base"].clip(0.01, 0.99) /
                            (1 - d["p_over_base"].clip(0.01, 0.99)))
        return np.column_stack([
            logit_base,
            d["ref_goals_dev"].fillna(0),
            d["ppda_sum_dev"].fillna(0),
        ])

    X_train = make_X(train)
    X_test  = make_X(test)
    y_train = train["actual_over25"].values.astype(int)
    y_test  = test["actual_over25"].values.astype(int)

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s  = scaler.transform(X_test)

    model = LogisticRegression(C=1.0, max_iter=1000)
    model.fit(X_train_s, y_train)

    p_corrected = model.predict_proba(X_test_s)[:, 1]
    p_base      = test["p_over_base"].values

    brier_base  = brier(p_base, y_test)
    brier_corr  = brier(p_corrected, y_test)

    actual_rate = y_test.mean()
    print(f"Test seasons: {', '.join(TEST_SEASONS)}")
    print(f"Actual over25 rate:  {actual_rate:.3f}")
    print(f"Base P(over25) avg:  {p_base.mean():.3f}")
    print(f"Corrected avg:       {p_corrected.mean():.3f}")
    print(f"\nBrier base:       {brier_base:.4f}")
    print(f"Brier corrected:  {brier_corr:.4f}  (delta: {brier_corr-brier_base:+.4f})")

    print(f"\nLogistic coefficients:")
    for name, coef in zip(["logit_base", "ref_goals_dev", "ppda_sum_dev"], model.coef_[0]):
        print(f"  {name:<20} {coef:+.4f}")


if __name__ == "__main__":
    main()
