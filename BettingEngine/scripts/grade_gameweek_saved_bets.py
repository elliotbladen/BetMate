#!/usr/bin/env python3
"""Grade a saved gameweek slate: result, P&L, and CLV vs open/close.

Reads any `2_bets.csv` written in the gameweek schema (match_date, home, away,
market, selection, saved_price, stake_units) and grades it against the league's
matches CSV.

Handles all three 1X2 sides and both O/U 2.5 sides. `score_football_saved_bets.py`
could not grade a Draw or an Under before 2026-09-10 (draws scored as losses
against the away odds column; unders graded backwards against the over column) --
that is fixed there too, but this script is the reusable entry point.

Usage:
    python scripts/grade_gameweek_saved_bets.py \
        --bets outputs/football/championship/2026-27/gw07/2_bets.csv \
        --league championship
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

MATCHES = {
    "championship": ROOT / "ml/football/data/championship/matches/championship_matches.csv",
    "epl": ROOT / "ml/football/data/epl/matches/epl_matches.csv",
}
ODDS = {                      # side -> (open col, close col)
    "H": ("AvgH", "AvgCH"), "D": ("AvgD", "AvgCD"), "A": ("AvgA", "AvgCA"),
    "OVER": ("Avg>2.5", "AvgC>2.5"), "UNDER": ("Avg<2.5", "AvgC<2.5"),
}


def side_of(row) -> str:
    text = str(row.selection).strip().lower()
    if row.market == "1X2":
        if "draw" in text:
            return "D"
        if text.startswith(str(row.home).lower()):
            return "H"
        if text.startswith(str(row.away).lower()):
            return "A"
        raise SystemExit(f"cannot map 1X2 selection {row.selection!r} to {row.home} v {row.away}")
    if row.market == "O/U 2.5":
        return "OVER" if text.startswith("over") else "UNDER"
    raise SystemExit(f"unsupported market {row.market!r}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bets", required=True, type=Path)
    ap.add_argument("--league", default="championship", choices=list(MATCHES))
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    bets = pd.read_csv(args.bets)
    res = pd.read_csv(MATCHES[args.league], low_memory=False)
    res["match_date"] = pd.to_datetime(res["Date"], errors="coerce").dt.strftime("%Y-%m-%d")

    rows, missing = [], []
    for b in bets.itertuples():
        m = res[(res.HomeTeam == b.home) & (res.AwayTeam == b.away)
                & (res.match_date >= str(b.match_date))]
        if m.empty:
            missing.append(f"{b.home} v {b.away} ({b.market} {b.selection})")
            continue
        r = m.iloc[0]
        hg, ag = int(r.FTHG), int(r.FTAG)
        total = hg + ag
        side = side_of(b)
        won = {"H": hg > ag, "D": hg == ag, "A": ag > hg,
               "OVER": total > 2.5, "UNDER": total < 2.5}[side]
        ocol, ccol = ODDS[side]
        open_ = float(r[ocol]) if pd.notna(r.get(ocol)) else float("nan")
        close = float(r[ccol]) if pd.notna(r.get(ccol)) else float("nan")
        stake = float(b.stake_units)
        rows.append({
            "week": b.week, "match": f"{b.home} v {b.away}", "market": b.market,
            "selection": b.selection, "score": f"{hg}-{ag}", "total_goals": total,
            "saved_price": b.saved_price, "opening_odds": round(open_, 2),
            "closing_odds": round(close, 2),
            "vs_open_pct": round((b.saved_price / open_ - 1) * 100, 2),
            "clv_pct": round((b.saved_price / close - 1) * 100, 2),
            "market_drift_pct": round((close / open_ - 1) * 100, 2),
            "result": "win" if won else "loss", "stake_u": stake,
            "pnl_u": round(stake * (b.saved_price - 1) if won else -stake, 3),
        })

    if missing:
        print("NOT YET PLAYED / NO RESULT ROW:")
        for x in missing:
            print("  ", x)
        print("  (re-run fetch_results.py --live-merge, then grade again)\n")
    if not rows:
        print("Nothing gradeable yet.")
        return

    out = pd.DataFrame(rows)
    dest = args.out or args.bets.parent / "4_review_bets.csv"
    out.to_csv(dest, index=False)
    print(out[["match", "market", "selection", "score", "saved_price", "closing_odds",
               "clv_pct", "result", "pnl_u"]].to_string(index=False))
    n, w = len(out), int((out.result == "win").sum())
    staked, pnl = out.stake_u.sum(), out.pnl_u.sum()
    print(f"\n{n} selections | {w}W-{n-w}L ({w/n*100:.1f}%) | staked {staked:.2f}u | "
          f"P&L {pnl:+.2f}u | ROI {pnl/staked*100:+.2f}%")
    clv = out.clv_pct.dropna()
    if len(clv):
        print(f"CLV {clv.mean():+.2f}% | beat the close {int((clv>0).sum())}/{len(clv)}")
    print(f"\nwrote {dest}")


if __name__ == "__main__":
    main()
