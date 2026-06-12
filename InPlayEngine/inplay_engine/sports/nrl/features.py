"""
InPlayEngine/sports/nrl/features.py

Feature engineering for NRL halftime pricing model.
Input: a row from the halftime dataset (HT scores + HT exchange price + context).
Output: feature vector for the model.
"""
from __future__ import annotations

import pandas as pd


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build features from the halftime dataset.

    Expected input columns:
        season, round, date, home_team, away_team,
        ht_home_score, ht_away_score,
        ht_home_price, ht_away_price,   ← from Betfair
        ft_home_score, ft_away_score    ← ground truth (for training)

    Returns df with feature columns appended.
    """
    out = df.copy()

    # Score state
    out["ht_score_diff"] = out["ht_home_score"] - out["ht_away_score"]
    out["ht_total_score"] = out["ht_home_score"] + out["ht_away_score"]

    # Which team is leading at HT
    out["ht_leader"] = out["ht_score_diff"].apply(
        lambda d: "home" if d > 0 else ("away" if d < 0 else "level")
    )

    # Trailing team deficit (absolute)
    out["ht_deficit"] = out["ht_score_diff"].abs()

    # Deficit bands (matches our comeback analysis)
    out["deficit_band"] = pd.cut(
        out["ht_deficit"],
        bins=[0, 4, 6, 8, 10, 99],
        labels=["1-4", "5-6", "7-8", "9-10", "10+"],
        right=True,
    )

    # Market-implied probabilities at halftime
    # Exchange price is decimal odds → implied prob = 1/price
    out["ht_home_impl_prob"] = 1 / out["ht_home_price"].clip(lower=1.01)
    out["ht_away_impl_prob"] = 1 / out["ht_away_price"].clip(lower=1.01)

    # Ground truth labels for training
    if "ft_home_score" in df.columns and "ft_away_score" in df.columns:
        out["ft_score_diff"] = out["ft_home_score"] - out["ft_away_score"]
        out["home_won"] = (out["ft_home_score"] > out["ft_away_score"]).astype(int)
        out["away_won"] = (out["ft_away_score"] > out["ft_home_score"]).astype(int)

    return out


FEATURE_COLS = [
    "ht_score_diff",
    "ht_total_score",
    "ht_deficit",
    "ht_home_impl_prob",
    "ht_away_impl_prob",
]
