#!/usr/bin/env python3
"""
scripts/score_football_saved_bets.py

Grade the saved EPL / EFL Championship selections against football-data.co.uk
results and CLOSING odds.

Conventions (match the 2026-09-02 football CLV work):
  - closing odds  = average closing (AvgCH/AvgCD/AvgCA, AvgC>2.5)
  - stake         = the stake_units on the saved row (1.0u, or 1.5u on a +6 matrix)
  - losing bet returns zero
  - CLV %         = saved_price / closing_odds - 1

Run: python3 scripts/score_football_saved_bets.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
EPL = ROOT / "ml/football/data/epl/matches/epl_matches.csv"
EFL = ROOT / "ml/football/data/championship/matches/championship_matches.csv"
OUT = ROOT / "outputs/results"

# (league, home, away, market, side, saved_price, stake_u, source)
BETS = [
    # EPL GW3 — outputs/football/epl/gw3_10pct_ev_candidates_2026-09-03.csv
    ("EPL", "Ipswich",   "Liverpool",   "1X2",     "H",    5.50, 1.0, "Ipswich win"),
    ("EPL", "Brentford", "Sunderland",  "1X2",     "A",    5.50, 1.0, "Sunderland win"),
    ("EPL", "Hull",      "Aston Villa", "1X2",     "H",    4.10, 1.0, "Hull win"),
    ("EPL", "Everton",   "Man United",  "1X2",     "H",    3.10, 1.0, "Everton win"),
    ("EPL", "Newcastle", "Bournemouth", "O/U 2.5", "OVER", 1.57, 1.0, "Over 2.5"),
    ("EPL", "Everton",   "Man United",  "O/U 2.5", "OVER", 1.70, 1.0, "Over 2.5"),
    ("EPL", "Arsenal",   "Chelsea",     "O/U 2.5", "OVER", 2.00, 1.0, "Over 2.5"),
    # EFL GW5 — outputs/football/championship/gw5_bets_injury_adjusted_2026-09-03.csv
    ("EFL", "Stoke",            "Charlton", "1X2", "A", 3.48, 1.0, "Charlton win"),
    ("EFL", "Millwall",         "Bolton",   "1X2", "A", 6.00, 1.0, "Bolton win"),
    ("EFL", "Sheffield United", "Norwich",  "1X2", "H", 2.50, 1.5, "Sheffield United win (+6 matrix)"),
    ("EFL", "Swansea",          "Wrexham",  "1X2", "H", 2.50, 1.0, "Swansea win"),
    ("EFL", "Birmingham",       "Wolves",   "1X2", "H", 2.99, 1.0, "Birmingham win"),
]


def load(p: Path) -> pd.DataFrame:
    df = pd.read_csv(p, low_memory=False)
    df["D"] = pd.to_datetime(df["Date"], errors="coerce")
    return df[df.D >= "2026-09-01"]


def grade(bet, books):
    league, home, away, market, side, price, stake, label = bet
    df = books[league]
    m = df[(df.HomeTeam == home) & (df.AwayTeam == away)]
    if m.empty:
        raise SystemExit(f"no match row for {home} v {away}")
    r = m.iloc[0]
    hg, ag = int(r.FTHG), int(r.FTAG)
    total = hg + ag

    if market == "1X2":
        won = (side == "H" and hg > ag) or (side == "A" and ag > hg)
        close = float(r["AvgCH"] if side == "H" else r["AvgCA"])
    else:
        won = total > 2.5
        close = float(r["AvgC>2.5"])

    pnl = stake * (price - 1) if won else -stake
    return {
        "league": league, "match": f"{home} v {away}", "market": market,
        "selection": label, "saved_price": price, "closing_odds": round(close, 2),
        "clv_pct": round((price / close - 1) * 100, 2),
        "score": f"{hg}-{ag}", "total_goals": total,
        "result": "win" if won else "loss",
        "stake_u": stake, "pnl_u": round(pnl, 3),
    }


def summarise(rows):
    n = len(rows)
    w = sum(1 for r in rows if r["result"] == "win")
    staked = sum(r["stake_u"] for r in rows)
    pnl = sum(r["pnl_u"] for r in rows)
    clvs = [r["clv_pct"] for r in rows]
    return {"bets": n, "wins": w, "losses": n - w,
            "strike": round(w / n * 100, 1), "staked": round(staked, 2),
            "pnl": round(pnl, 3), "roi": round(pnl / staked * 100, 2),
            "avg_clv": round(sum(clvs) / n, 2),
            "pos_clv": sum(1 for c in clvs if c > 0),
            "beat_close_pct": round(sum(1 for c in clvs if c > 0) / n * 100, 1)}


def main():
    books = {"EPL": load(EPL), "EFL": load(EFL)}
    rows = [grade(b, books) for b in BETS]

    OUT.mkdir(parents=True, exist_ok=True)
    csv_path = OUT / "epl_efl_saved_bets_clv_roi_2026-09-08.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)

    for lg in ("EPL", "EFL"):
        sub = [r for r in rows if r["league"] == lg]
        s = summarise(sub)
        print(f"\n{'='*100}")
        print(f"{lg} — saved selections vs closing line")
        print(f"{'='*100}")
        print(f"{'Match':<32}{'Selection':<26}{'Took':>7}{'Close':>7}{'CLV':>9}{'Score':>8}{'Res':>6}{'P&L':>8}")
        for r in sub:
            print(f"{r['match']:<32}{r['selection']:<26}{r['saved_price']:>7.2f}{r['closing_odds']:>7.2f}"
                  f"{r['clv_pct']:>+8.2f}%{r['score']:>8}{r['result'][:1].upper():>6}{r['pnl_u']:>+8.2f}")
        print("-" * 100)
        print(f"  {s['bets']} bets | {s['wins']}W-{s['losses']}L ({s['strike']}%) | staked {s['staked']}u | "
              f"P&L {s['pnl']:+.2f}u | ROI {s['roi']:+.2f}% | avg CLV {s['avg_clv']:+.2f}% | "
              f"beat close {s['pos_clv']}/{s['bets']} ({s['beat_close_pct']}%)")

    s = summarise(rows)
    print(f"\n{'='*100}")
    print(f"COMBINED: {s['bets']} bets | {s['wins']}W-{s['losses']}L ({s['strike']}%) | staked {s['staked']}u | "
          f"P&L {s['pnl']:+.2f}u | ROI {s['roi']:+.2f}% | avg CLV {s['avg_clv']:+.2f}% | "
          f"beat close {s['pos_clv']}/{s['bets']} ({s['beat_close_pct']}%)")
    print(f"\nwritten: {csv_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
