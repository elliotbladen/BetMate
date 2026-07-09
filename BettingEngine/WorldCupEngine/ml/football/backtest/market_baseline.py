"""
Market baseline: the bookmaker's own RPS on a league's test seasons.

De-vigs Pinnacle closing 1X2 odds (PSCH/PSCD/PSCA; falls back to opening PSH/PSD/PSA,
then B365) into probabilities and scores them with RPS — the honest benchmark for
walk_forward results. A model within ~2% of this number is at market strength.

Usage:
    python ml/football/backtest/market_baseline.py --league championship
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(_ROOT))

from ml.football.league_config import load_league

ODDS_SETS = [
    ("Pinnacle closing", ("PSCH", "PSCD", "PSCA")),
    ("Pinnacle opening", ("PSH", "PSD", "PSA")),
    ("Bet365",           ("B365H", "B365D", "B365A")),
]


def rps(p_home: float, p_draw: float, p_away: float, result: str) -> float:
    o = [1, 0, 0] if result == "H" else [0, 1, 0] if result == "D" else [0, 0, 1]
    p = [p_home, p_draw, p_away]
    return float(np.mean((np.cumsum(p) - np.cumsum(o)) ** 2))


def devig(oh: float, od: float, oa: float) -> tuple[float, float, float] | None:
    if not all(isinstance(v, (int, float)) and v and v > 1.0 for v in (oh, od, oa)):
        return None
    ih, idr, ia = 1 / oh, 1 / od, 1 / oa
    s = ih + idr + ia
    return ih / s, idr / s, ia / s


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--league", default="epl")
    args = parser.parse_args()

    cfg = load_league(args.league)
    df = pd.read_csv(cfg.matches_csv, parse_dates=["Date"])

    print(f"Market baseline — {cfg.name}")
    all_scores = []
    for season in cfg.test_seasons:
        sdf = df[df["Season"] == season]
        scores, source_used = [], None
        for source, cols in ODDS_SETS:
            if not all(c in sdf.columns for c in cols):
                continue
            sub = sdf.dropna(subset=list(cols))
            if len(sub) < len(sdf) * 0.8:
                continue
            for _, r in sub.iterrows():
                p = devig(r[cols[0]], r[cols[1]], r[cols[2]])
                if p:
                    scores.append(rps(*p, r["FTR"]))
            source_used = source
            break
        if scores:
            print(f"  {season}: market RPS {np.mean(scores):.4f}  (n={len(scores)}, {source_used})")
            all_scores.extend(scores)
        else:
            print(f"  {season}: no odds coverage")

    if all_scores:
        print(f"  {'-'*46}")
        print(f"  AGGREGATE market RPS: {np.mean(all_scores):.4f}  (n={len(all_scores)})")


if __name__ == "__main__":
    main()
