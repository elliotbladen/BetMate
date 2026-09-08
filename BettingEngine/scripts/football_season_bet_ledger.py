#!/usr/bin/env python3
"""
scripts/football_season_bet_ledger.py

Season-to-date CLV and ROI for saved football selections, split EPL vs EFL.

NOTE: these are PAPER selections. User confirmed 2026-09-08 that none were
staked. Model/paper performance only — not a betting record.

Sources (the only two graded saved-bet records that carry both a taken price and
a result):
  1. outputs/results/epl_efl_saved_20pct_ev_results_2026-09-02.csv
     EPL week 2 (29-31 Aug) x6, EFL week 3 (28-29 Aug) x3
  2. outputs/results/epl_efl_saved_bets_clv_roi_2026-09-08.csv
     EPL GW3 (4-6 Sep) x7, EFL GW5 (5-6 Sep) x5

NOT included: outputs/results/all model results/* and the gw1 clv backtests.
Those are full model portfolios (every side of every game), not placed bets.
The 23-bet "previous weekend" in epl_efl_combined_performance_through_2026-08-31
has no underlying graded bet file and that report labels itself mixed-rule
preliminary, so it is excluded rather than merged on faith.

Odds: football-data consensus averages. open = AvgH/AvgD/AvgA, Avg>2.5;
close = AvgCH/AvgCD/AvgCA, AvgC>2.5. Flat 1u unless a stake is recorded.

Run: python3 scripts/football_season_bet_ledger.py
"""
from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
BOOKS = {
    "EPL": pd.read_csv(ROOT / "ml/football/data/epl/matches/epl_matches.csv", low_memory=False),
    "EFL": pd.read_csv(ROOT / "ml/football/data/championship/matches/championship_matches.csv", low_memory=False),
}


def odds(league, home, away, market, side):
    df = BOOKS[league]
    m = df[(df.HomeTeam == home) & (df.AwayTeam == away) & (df.Date >= "2026-08-01")]
    if m.empty:
        return None, None
    r = m.iloc[0]
    if market == "1X2":
        col = {"H": ("AvgH", "AvgCH"), "D": ("AvgD", "AvgCD"), "A": ("AvgA", "AvgCA")}[side]
    else:
        col = ("Avg>2.5", "AvgC>2.5") if side == "OVER" else ("Avg<2.5", "AvgC<2.5")
    return float(r[col[0]]), float(r[col[1]])


rows = []

# --- source 1: the 2026-09-02 graded 20% EV list -----------------------------
for r in csv.DictReader(open(ROOT / "outputs/results/epl_efl_saved_20pct_ev_results_2026-09-02.csv", encoding="utf-8-sig")):
    lg = "EPL" if r["league"] == "EPL" else "EFL"
    sel = r["selection"]
    if "Over" in sel:
        market, side = "O/U 2.5", "OVER"
    elif "Under" in sel:
        market, side = "O/U 2.5", "UNDER"
    else:
        market = "1X2"
        side = "H" if sel.replace(" win", "") == r["home"] else "A"
    o, c = odds(lg, r["home"], r["away"], market, side)
    price = float(r["saved_price"]); won = r["outcome"] == "WIN"
    rows.append(dict(league=lg, week=f"{lg} W{r['week']}", date=r["match_date"],
                     match=f"{r['home']} v {r['away']}", market=market, selection=sel,
                     opening_odds=o, saved_price=price, closing_odds=c,
                     stake_u=1.0, result="win" if won else "loss",
                     pnl_u=round(price - 1 if won else -1.0, 3),
                     flag=r["status"] if "verification" in r["status"] else ""))

# --- source 2: this weekend's graded card ------------------------------------
for r in csv.DictReader(open(ROOT / "outputs/results/epl_efl_saved_bets_clv_roi_2026-09-08.csv", encoding="utf-8-sig")):
    rows.append(dict(league=r["league"], week=f"{r['league']} {'GW3' if r['league']=='EPL' else 'GW5'}",
                     date="2026-09-05", match=r["match"], market=r["market"], selection=r["selection"],
                     opening_odds=float(r["opening_odds"]), saved_price=float(r["saved_price"]),
                     closing_odds=float(r["closing_odds"]), stake_u=float(r["stake_u"]),
                     result=r["result"], pnl_u=float(r["pnl_u"]), flag=""))

for r in rows:
    r["vs_open_pct"] = round((r["saved_price"] / r["opening_odds"] - 1) * 100, 2) if r["opening_odds"] else None
    r["clv_pct"] = round((r["saved_price"] / r["closing_odds"] - 1) * 100, 2) if r["closing_odds"] else None

out = ROOT / "outputs/results/football_season_bet_ledger_2026-09-08.csv"
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)


def block(rs, label):
    n = len(rs); wn = sum(1 for r in rs if r["result"] == "win")
    st = sum(r["stake_u"] for r in rs); pnl = sum(r["pnl_u"] for r in rs)
    cl = [r["clv_pct"] for r in rs if r["clv_pct"] is not None]
    op = [r["vs_open_pct"] for r in rs if r["vs_open_pct"] is not None]
    print(f"\n{label}")
    print(f"  Bets        {n}   ({wn}W-{n-wn}L, {wn/n*100:.1f}% strike)")
    print(f"  Staked      {st:.2f}u      P&L {pnl:+.2f}u")
    print(f"  ROI         {pnl/st*100:+.2f}%")
    print(f"  CLV         {sum(cl)/len(cl):+.2f}%   beat close {sum(1 for c in cl if c>0)}/{len(cl)}")
    print(f"  vs open     {sum(op)/len(op):+.2f}%   beat open  {sum(1 for c in op if c>0)}/{len(op)}")
    return dict(n=n, w=wn, staked=st, pnl=pnl, roi=pnl/st*100,
                clv=sum(cl)/len(cl), open=sum(op)/len(op))


print("=" * 78)
print("FOOTBALL — SEASON-TO-DATE PAPER SELECTIONS, NOT STAKED (through 2026-09-06)")
print("=" * 78)
for lg in ("EPL", "EFL"):
    rs = [r for r in rows if r["league"] == lg]
    block(rs, f"### {lg} — COMBINED ({len(rs)} bets)")
    for wk in sorted({r["week"] for r in rs}):
        sub = [r for r in rs if r["week"] == wk]
        wn = sum(1 for r in sub if r["result"] == "win")
        st = sum(r["stake_u"] for r in sub); pnl = sum(r["pnl_u"] for r in sub)
        cl = [r["clv_pct"] for r in sub if r["clv_pct"] is not None]
        print(f"      {wk:<10} {len(sub)} bets  {wn}W-{len(sub)-wn}L  "
              f"P&L {pnl:+6.2f}u  ROI {pnl/st*100:+7.2f}%  CLV {sum(cl)/len(cl):+6.2f}%")

print("\n" + "=" * 78)
block(rows, f"### BOTH LEAGUES ({len(rows)} bets)")
flagged = [r for r in rows if r["flag"]]
if flagged:
    clean = [r for r in rows if not r["flag"]]
    st = sum(r["stake_u"] for r in clean); pnl = sum(r["pnl_u"] for r in clean)
    print(f"\n  {len(flagged)} rows carry verification warnings from the 2026-09-02 report.")
    print(f"  Excluding them: {len(clean)} bets, P&L {pnl:+.2f}u, ROI {pnl/st*100:+.2f}%")
print(f"\nwritten: {out.relative_to(ROOT)}")
