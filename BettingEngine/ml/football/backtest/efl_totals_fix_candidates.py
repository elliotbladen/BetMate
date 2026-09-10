#!/usr/bin/env python3
"""Which fixes actually get Championship O/U 2.5 to break even vs the line?

Bar: ROI >= 0 or CLV >= 0 at the OPENING price. Everything is walk-forward and the
model may only see the OPENING price at bet time; CLV is then measured to the close.
Anchoring on the closing line would be lookahead.

Variants
  A  production      D-C raw -> isotonic fitted on prior seasons (today's engine)
  B  platt           D-C raw -> logistic calibration (smooth, no plateau, no ceiling)
  C  platt+drift     B plus a rolling league base-rate offset, so a hot season tracks
  D  market-anchored logit(p) = a + b*logit(mkt_open) + c*logit(raw), fitted walk-forward
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

SEASONS = ["2022/23", "2023/24", "2024/25"]      # 2021/22 has no prior season to fit on
ROLL_BASE = 60                                    # matches in the rolling base-rate window


def logit(p):
    p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def load():
    m = pd.read_csv(ROOT / "ml/football/data/championship/matches/championship_matches.csv",
                    low_memory=False, parse_dates=["Date"])
    m["over"] = ((m.FTHG + m.FTAG) > 2.5).astype(int)
    b = pd.read_csv(ROOT / "ml/football/data/championship/clv/backtest_results.csv")
    b["Date"] = pd.to_datetime(b.date)
    j = b.merge(m[["Date", "HomeTeam", "AwayTeam", "Season", "over",
                   "P>2.5", "P<2.5", "PC>2.5", "PC<2.5", "Max>2.5", "Max<2.5"]],
                left_on=["Date", "home", "away"], right_on=["Date", "HomeTeam", "AwayTeam"])
    j = j.dropna(subset=["P>2.5", "P<2.5", "PC>2.5", "PC<2.5"]).sort_values("Date")
    j["raw"] = (1.0 / j.model_over25).clip(.01, .99)
    io, iu = 1 / j["P>2.5"], 1 / j["P<2.5"]
    j["mkt_open"] = io / (io + iu)
    co, cu = 1 / j["PC>2.5"], 1 / j["PC<2.5"]
    j["mkt_close"] = co / (co + cu)
    # rolling league over-rate from STRICTLY prior matches
    j["base_roll"] = j.over.shift(1).rolling(ROLL_BASE, min_periods=30).mean()
    return j.reset_index(drop=True)


def predictions(j):
    out = {k: pd.Series(np.nan, index=j.index) for k in ("A", "B", "C", "D")}
    for s in SEASONS:
        te, tr = j[j.Season == s], j[j.Season < s]
        if len(tr) < 200:
            continue
        # A - isotonic, prior seasons only
        iso = IsotonicRegression(out_of_bounds="clip").fit(tr.raw, tr.over)
        out["A"].loc[te.index] = np.clip(iso.predict(te.raw), .01, .99)
        # B - Platt
        pl = LogisticRegression(max_iter=2000).fit(logit(tr.raw).reshape(-1, 1), tr.over)
        out["B"].loc[te.index] = pl.predict_proba(logit(te.raw).reshape(-1, 1))[:, 1]
        # C - Platt + rolling base-rate drift
        trc = tr.dropna(subset=["base_roll"])
        X = np.column_stack([logit(trc.raw), logit(trc.base_roll)])
        pc = LogisticRegression(max_iter=2000).fit(X, trc.over)
        Xt = np.column_stack([logit(te.raw), logit(te.base_roll.fillna(tr.over.mean()))])
        out["C"].loc[te.index] = pc.predict_proba(Xt)[:, 1]
        # D - market-anchored (OPENING price only - no lookahead)
        Xd = np.column_stack([logit(tr.mkt_open), logit(tr.raw)])
        pd_ = LogisticRegression(max_iter=2000).fit(Xd, tr.over)
        out["D"].loc[te.index] = pd_.predict_proba(
            np.column_stack([logit(te.mkt_open), logit(te.raw)]))[:, 1]
        if s == SEASONS[-1]:
            print(f"    variant D coefficients (fit to {s}): "
                  f"market {pd_.coef_[0][0]:+.3f}, model {pd_.coef_[0][1]:+.3f}")
    return out


def simulate(te, p, thr):
    rows = []
    for (_, r), pv in zip(te.iterrows(), p):
        for side, prob, px, clo in (("OVER", pv, r["P>2.5"], r["PC>2.5"]),
                                    ("UNDER", 1 - pv, r["P<2.5"], r["PC<2.5"])):
            if prob * px - 1 >= thr:
                won = (r.over == 1) if side == "OVER" else (r.over == 0)
                rows.append({"side": side, "pnl": px - 1 if won else -1,
                             "won": won, "clv": px / clo - 1})
    return pd.DataFrame(rows)


def main():
    j = load()
    print(f"rows: {len(j)}  seasons tested: {', '.join(SEASONS)}")
    preds = predictions(j)
    mask = j.Season.isin(SEASONS)
    te = j[mask]
    names = {"A": "production (isotonic)", "B": "platt", "C": "platt + drift",
             "D": "market-anchored"}
    print(f"\n{'variant':<24}{'thr':>6}{'bets':>6}{'%Und':>6}{'strike':>8}{'ROI':>9}{'CLV':>9}  bar")
    print("-" * 82)
    for k in ("A", "B", "C", "D"):
        p = preds[k][mask].values
        if np.isnan(p).all():
            continue
        for thr in (0.05, 0.10, 0.20):
            D = simulate(te, p, thr)
            if D.empty:
                print(f"{names[k]:<24}{thr:>6.0%}{0:>6}{'-':>6}{'-':>8}{'-':>9}{'-':>9}  no bets")
                continue
            roi, clv = D.pnl.mean(), D.clv.mean()
            ok = "PASS" if (roi >= 0 or clv >= 0) else ""
            print(f"{names[k]:<24}{thr:>6.0%}{len(D):>6}{(D.side=='UNDER').mean():>6.0%}"
                  f"{D.won.mean():>8.1%}{roi:>+9.2%}{clv:>+9.2%}  {ok}")
    # distribution sanity: does each variant actually vary per game?
    print("\ndistinct probabilities emitted (out of %d fixtures):" % mask.sum())
    for k in ("A", "B", "C", "D"):
        v = preds[k][mask].round(4)
        print(f"  {names[k]:<24}{v.nunique():>5}   range {v.min():.3f}-{v.max():.3f}")


if __name__ == "__main__":
    main()
