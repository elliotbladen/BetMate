"""
CLV backtest: simulate betting the model against Pinnacle OPENING odds and measure
Closing Line Value + flat-stake P/L over the walk-forward test seasons.

Logic per match/outcome:
  edge = p_model × opening_odds − 1        (EV vs the opening line)
  bet when edge ≥ threshold
  CLV% = opening_odds / closing_odds − 1   (positive = beat the close)
  P/L  = flat 1u stake, settled on the actual result

Reads: data/{league}/clv/backtest_results.csv  (model probs, from walk_forward)
Joins: data/{league}/matches/*.csv             (PSH/PSD/PSA opening, PSCH/PSCD/PSCA closing)

Usage:
    python ml/football/backtest/clv_backtest.py --league championship
    python ml/football/backtest/clv_backtest.py --league championship --thresholds 0.03,0.05,0.08
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

OUTCOMES = [
    # (label, model prob col, open col, close col, wins_when)
    ("home", "p_home", "PSH", "PSCH", "H"),
    ("draw", "p_draw", "PSD", "PSCD", "D"),
    ("away", "p_away", "PSA", "PSCA", "A"),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--league", default="epl")
    parser.add_argument("--thresholds", default="0.02,0.05,0.08,0.12")
    args = parser.parse_args()
    thresholds = [float(t) for t in args.thresholds.split(",")]

    cfg = load_league(args.league)
    res = pd.read_csv(cfg.results_csv, parse_dates=["date"])
    matches = pd.read_csv(cfg.matches_csv, parse_dates=["Date"])

    odds_cols = ["PSH", "PSD", "PSA", "PSCH", "PSCD", "PSCA"]
    have = [c for c in odds_cols if c in matches.columns]
    if len(have) < 6:
        raise SystemExit(f"Missing Pinnacle columns in matches CSV — have {have}")

    m = matches[["Date", "HomeTeam", "AwayTeam"] + odds_cols].rename(
        columns={"Date": "date", "HomeTeam": "home", "AwayTeam": "away"})
    df = res.merge(m, on=["date", "home", "away"], how="left")
    n_odds = df["PSH"].notna() & df["PSCH"].notna()
    print(f"{cfg.name}: {len(df)} test rows, {n_odds.sum()} with Pinnacle open+close\n")

    for thr in thresholds:
        bets = []
        for label, pcol, ocol, ccol, wins in OUTCOMES:
            sub = df.dropna(subset=[pcol, ocol, ccol])
            edge = sub[pcol] * sub[ocol] - 1.0
            sel = sub[edge >= thr].copy()
            sel["outcome"] = label
            sel["edge"] = edge[edge >= thr]
            sel["clv"] = sel[ocol] / sel[ccol] - 1.0
            sel["won"] = (sel["result"] == wins)
            sel["pl"] = np.where(sel["won"], sel[ocol] - 1.0, -1.0)
            bets.append(sel[["season", "outcome", "edge", "clv", "won", "pl"]])

        allb = pd.concat(bets, ignore_index=True) if bets else pd.DataFrame()
        if allb.empty:
            print(f"edge ≥ {thr:.0%}: no bets")
            continue

        print(f"═══ edge ≥ {thr:.0%} vs OPENING ═══════════════════════════════")
        print(f"  {'':10} {'bets':>5} {'CLV avg':>8} {'CLV>0':>6} {'strike':>7} {'ROI':>7}")
        for grp_name, grp in [("ALL", allb)] + list(allb.groupby("outcome")):
            print(f"  {grp_name:<10} {len(grp):>5} {grp['clv'].mean():>+7.2%} "
                  f"{(grp['clv'] > 0).mean():>5.0%} {grp['won'].mean():>6.1%} "
                  f"{grp['pl'].sum() / len(grp):>+6.1%}")
        by_season = allb.groupby("season").agg(
            bets=("pl", "size"), clv=("clv", "mean"), roi=("pl", "mean"))
        for s, r in by_season.iterrows():
            print(f"    {s}: {int(r.bets)} bets, CLV {r.clv:+.2%}, ROI {r.roi:+.1%}")
        print()


if __name__ == "__main__":
    main()
