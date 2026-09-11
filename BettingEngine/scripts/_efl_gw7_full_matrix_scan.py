#!/usr/bin/env python3
"""Score EVERY team side in every GW7 fixture on the frozen EFL confluence matrix.

The GW7 candidate audit only scored the four 1X2 team sides that cleared 10% EV.
This scans all 24 sides so net-confluence can be read independently of EV.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.efl_gw7_candidate_confluence import audit, MARKET  # noqa: E402

GW = ROOT / "outputs/football/championship/2026-27/gw07"
MODEL = json.loads((GW / "1_model.json").read_text())["games"]

rows = []
for g in MODEL:
    home, away = g["home"], g["away"]
    mkt = MARKET[f"{home} v {away}"]
    for side, team in (("home", home), ("away", away)):
        aligned, opposed = audit(home, away, team)
        rows.append({
            "date": g["date"], "match": f"{home} v {away}", "team": team, "side": side,
            "aligned": len(aligned), "opposed": len(opposed),
            "net": len(aligned) - len(opposed),
            "best_price": mkt[f"best_{side}"],
            "model_p": g["normal"][f"p_{side}"],
            "ev_best": g["normal"][f"p_{side}"] * mkt[f"best_{side}"] - 1,
            "dc_reset": ", ".join(g["dc_reset_teams"]),
            "aligned_detail": "; ".join(f"{x['team']} {x['category']} {x['edge_pp']:+.1f}pp (n={x['n']})"
                                        for x in aligned) or "None",
            "opposed_detail": "; ".join(f"{x['team']} {x['category']} {x['edge_pp']:+.1f}pp (n={x['n']})"
                                        for x in opposed) or "None",
        })

import pandas as pd
df = pd.DataFrame(rows).sort_values("net", ascending=False)
df.to_csv(GW / "_supporting" / "matrix_full_scan.csv", index=False)

print(f"{'Match':<28}{'Team':<18}{'V':<4}{'Al':>3}{'Op':>4}{'Net':>5}{'Price':>7}{'Model p':>9}{'EV':>9}  reset")
print("-" * 108)
for _, r in df.iterrows():
    print(f"{r['match']:<28}{r.team:<18}{'H' if r.side=='home' else 'A':<4}"
          f"{r.aligned:>3}{r.opposed:>4}{r.net:>+5d}{r.best_price:>7.2f}{r.model_p:>9.3f}"
          f"{r.ev_best:>+9.1%}  {r.dc_reset}")

print("\n\n############ NET >= +3 ############")
for _, r in df[df.net >= 3].iterrows():
    print(f"\n{r.team} — {r['match']}  ({'home' if r.side=='home' else 'away'})   "
          f"net {r.net:+d}  ({r.aligned} aligned / {r.opposed} opposed)")
    print(f"  best price {r.best_price:.2f} | model {1/r.model_p:.2f} | EV {r.ev_best:+.1%}"
          + (f" | RESET: {r.dc_reset}" if r.dc_reset else ""))
    print(f"  Aligned: {r.aligned_detail}")
    print(f"  Opposed: {r.opposed_detail}")
print(f"\nwrote {GW/'_supporting'/'matrix_full_scan.csv'}")
