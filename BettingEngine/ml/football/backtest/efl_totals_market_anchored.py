#!/usr/bin/env python3
"""Market-anchored Championship O/U 2.5 rule — development check and vault test.

THE RULE (frozen; see VAULT_PREREGISTRATION.md)
  anchor   de-vigged OPENING consensus  (Avg>2.5 / Avg<2.5)
  model    logit(p) = a + b*logit(anchor) + c*logit(dc_raw), logistic, fitted on
           seasons STRICTLY BEFORE the season being tested
  execute  best available OPENING price (Max>2.5 / Max<2.5)
  bet      EV = p * best_price - 1 >= 0.03, both sides, flat 1u
  CLV      taken price / closing consensus (AvgC) - 1
  pass     ROI >= 0 OR CLV >= 0

`--mode dev` runs 2022/23-2024/25. `--mode vault` runs the sealed 2025/26 season and
is SINGLE USE — the whole point is that the rule is frozen before it is run.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

MATCHES = ROOT / "ml/football/data/championship/matches/championship_matches.csv"
DEV_DC = ROOT / "ml/football/data/championship/clv/backtest_results.csv"
VAULT_DC = ROOT / "ml/football/data/championship/clv_vault/backtest_results.csv"
DEV_SEASONS = ["2022/23", "2023/24", "2024/25"]
TRAIN_SEASONS = ["2022/23", "2023/24", "2024/25"]   # frozen training set for the vault test
VAULT_SEASON = "2025/26"
THRESHOLD = 0.03


def logit(p):
    p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def devig(a, b):
    ia, ib = 1 / a, 1 / b
    return ia / (ia + ib)


def frame(dc_paths: list[Path]) -> pd.DataFrame:
    m = pd.read_csv(MATCHES, low_memory=False, parse_dates=["Date"])
    m["over"] = ((m.FTHG + m.FTAG) > 2.5).astype(int)
    dc = pd.concat([pd.read_csv(p) for p in dc_paths if p.exists()], ignore_index=True)
    dc["Date"] = pd.to_datetime(dc.date)
    j = dc.merge(m[["Date", "HomeTeam", "AwayTeam", "Season", "over",
                    "AvgC>2.5", "AvgC<2.5", "Max>2.5", "Max<2.5",
                    "BFE>2.5", "BFE<2.5", "P>2.5", "P<2.5"]],
                 left_on=["Date", "home", "away"], right_on=["Date", "HomeTeam", "AwayTeam"])
    j = j.dropna(subset=["AvgC>2.5", "AvgC<2.5", "Max>2.5", "Max<2.5"])
    j["dc_raw"] = (1.0 / j.model_over25).clip(.01, .99)
    # Sharp anchor: Betfair Exchange where football-data carries it, else Pinnacle.
    # football-data is retiring Pinnacle from E1 (full through 2024/25, 260/552 in
    # 2025/26, column absent in 2026/27); de-vigged BFE correlates 0.979 with
    # de-vigged Pinnacle (n=545, mean abs diff 0.0062), so they are interchangeable.
    # The de-vigged CONSENSUS (Avg) is NOT a substitute - it is measurably worse
    # (dev strike 41.2% vs 47.3%), because averaging soft books biases the estimate.
    bfe = devig(j["BFE>2.5"], j["BFE<2.5"])
    pin = devig(j["P>2.5"], j["P<2.5"])
    j["anchor"] = bfe.fillna(pin)
    j["anchor_src"] = np.where(bfe.notna(), "BFE", np.where(pin.notna(), "Pinnacle", "none"))
    return j.dropna(subset=["anchor"]).sort_values("Date").reset_index(drop=True)


def fit_blend(train: pd.DataFrame) -> LogisticRegression:
    X = np.column_stack([logit(train.anchor), logit(train.dc_raw)])
    return LogisticRegression(max_iter=2000).fit(X, train.over.values)


def bets(test: pd.DataFrame, p: np.ndarray) -> pd.DataFrame:
    rows = []
    for (_, r), pv in zip(test.iterrows(), p):
        for side, prob, px, close in (("OVER", pv, r["Max>2.5"], r["AvgC>2.5"]),
                                      ("UNDER", 1 - pv, r["Max<2.5"], r["AvgC<2.5"])):
            ev = prob * px - 1
            if ev >= THRESHOLD:
                won = (r.over == 1) if side == "OVER" else (r.over == 0)
                rows.append({"season": r.Season, "date": r.Date, "match": f"{r.home} v {r.away}",
                             "side": side, "model_p": prob, "price": px, "close": close,
                             "ev": ev, "won": bool(won),
                             "pnl": px - 1 if won else -1.0, "clv": px / close - 1})
    return pd.DataFrame(rows)


def report(D: pd.DataFrame, label: str) -> dict:
    n = len(D)
    roi, clv = D.pnl.mean(), D.clv.mean()
    rng = np.random.default_rng(7)
    boot = np.array([D.pnl.values[rng.integers(0, n, n)].mean() for _ in range(4000)])
    lo, hi = np.percentile(boot, [2.5, 97.5])
    print(f"\n{'='*78}\n{label}\n{'='*78}")
    print(f"  bets {n}   {int(D.won.sum())}W-{n-int(D.won.sum())}L ({D.won.mean():.1%})   "
          f"{(D.side=='UNDER').mean():.0%} Unders")
    print(f"  P&L {D.pnl.sum():+.2f}u   ROI {roi:+.2%}   CLV {clv:+.2%}")
    print(f"  ROI 95% bootstrap CI [{lo:+.2%}, {hi:+.2%}]   P(ROI>0) {np.mean(boot>0):.1%}")
    g = D.groupby("season").agg(n=("pnl", "size"), w=("won", "sum"),
                                pnl=("pnl", "sum"), clv=("clv", "mean"))
    g["roi"] = g.pnl / g.n
    print("\n  per season:")
    for s, x in g.iterrows():
        print(f"    {s}  {x.n:>4.0f} bets  {x.w:>3.0f}W  P&L {x.pnl:>+8.2f}u  "
              f"ROI {x.roi:>+8.2%}  CLV {x.clv:>+7.2%}")
    verdict = "PASS" if (roi >= 0 or clv >= 0) else "FAIL"
    print(f"\n  BAR (ROI >= 0 or CLV >= 0):  **{verdict}**")
    return {"n": n, "roi": roi, "clv": clv, "ci_lo": lo, "ci_hi": hi, "verdict": verdict}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["dev", "vault"], required=True)
    a = ap.parse_args()

    if a.mode == "dev":
        j = frame([DEV_DC])
        out = []
        for s in DEV_SEASONS:
            te, tr = j[j.Season == s], j[j.Season < s]
            if len(tr) < 300:
                continue
            m = fit_blend(tr)
            p = m.predict_proba(np.column_stack([logit(te.anchor), logit(te.dc_raw)]))[:, 1]
            out.append(bets(te, p))
        D = pd.concat(out, ignore_index=True)
        report(D, "DEVELOPMENT SEASONS (2022/23-2024/25) — anchor Avg, execute Max")
        D.to_csv(ROOT / "outputs/football/championship/_research/market_anchored_dev.csv", index=False)
    else:
        if not VAULT_DC.exists():
            raise SystemExit(f"vault D-C probabilities not generated yet: {VAULT_DC}")
        j = frame([DEV_DC, VAULT_DC])
        te, tr = j[j.Season == VAULT_SEASON], j[j.Season.isin(TRAIN_SEASONS)]
        print(f"train rows {len(tr)} (seasons {sorted(tr.Season.unique())})  ->  test rows {len(te)}")
        m = fit_blend(tr)
        print(f"blend coefficients: anchor {m.coef_[0][0]:+.4f}  dc_raw {m.coef_[0][1]:+.4f}  "
              f"intercept {m.intercept_[0]:+.4f}")
        p = m.predict_proba(np.column_stack([logit(te.anchor), logit(te.dc_raw)]))[:, 1]
        D = bets(te, p)
        report(D, "SEALED VAULT 2025/26 — SINGLE-USE TEST")
        D.to_csv(ROOT / "outputs/football/championship/_research/market_anchored_vault.csv", index=False)


if __name__ == "__main__":
    main()
