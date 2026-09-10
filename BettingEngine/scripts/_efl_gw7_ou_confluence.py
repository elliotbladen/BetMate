#!/usr/bin/env python3
"""Score the GW7 Over/Under 2.5 candidates on the confluence matrix.

The frozen EFL matrix rule scores 1X2 team sides only. This applies the same
category slices and the same |edge| >= 7.5pp cell test to the goals matrix
(`stats_goals`), so O/U selections can be read on the same scale.

For a totals selection BOTH clubs' splits point the same way -- a low-scoring
tendency for either side supports Under -- unlike 1X2, where the opponent's
cells flip sign.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.efl_championship_confluence_matrix import (  # noqa: E402
    load_rows, odds_band, stats_goals, team_rows)
from scripts.efl_gw7_candidate_confluence import LAST, devig  # noqa: E402

GW = ROOT / "outputs/football/championship/2026-27/gw07"
SOURCE = ROOT / "ml/football/data/championship/matches/championship_matches.csv"
SEASONS = ("2020/21", "2021/22", "2022/23", "2023/24", "2024/25")
EDGE_PP = 7.5
MARKET = json.loads((Path(__file__).resolve().parent / "_efl_gw7_market_2026.json").read_text())
ROWS = load_rows(SOURCE, SEASONS)
LEAGUE_BTTS = sum(int(g["home_goals"] > 0 and g["away_goals"] > 0) for g in ROWS
                  if g["home_goals"] is not None) / max(1, sum(
                      1 for g in ROWS if g["home_goals"] is not None))


def slices(team, home, away, played, previous, rest_days, probs):
    games = team_rows(ROWS, team)
    fake = {"market_1x2": (probs, "current"), "home": home, "away": away}
    band = odds_band(fake, team)
    if rest_days <= 3:
        lbl, sel = "Short rest (<=3 days)", lambda g: g.get(f"rest__{team}") is not None and g[f"rest__{team}"] <= 3
    elif rest_days <= 8:
        lbl, sel = "Normal rest (4-8 days)", lambda g: g.get(f"rest__{team}") is not None and 4 <= g[f"rest__{team}"] <= 8
    else:
        lbl, sel = "Long rest (>=9 days)", lambda g: g.get(f"rest__{team}") is not None and g[f"rest__{team}"] >= 9
    venue = "home" if team == home else "away"
    opponent = away if team == home else home
    return [
        ("All games", games),
        ("Home games" if venue == "home" else "Away games", [g for g in games if g[venue] == team]),
        (played.strftime("%A"), [g for g in games if g["weekday"] == played.weekday()]),
        (played.strftime("%B"), [g for g in games if g["month"] == played.month]),
        ({"W": "After a win", "D": "After a draw", "L": "After a loss"}[previous],
         [g for g in games if g.get(f"previous__{team}") == previous]),
        (lbl, [g for g in games if sel(g)]),
        (band or "No price band", [g for g in games if odds_band(g, team) == band] if band else []),
        (f"vs {opponent}", [g for g in games if opponent in (g["home"], g["away"])]),
    ]


def audit_ou(home, away, pick):
    """pick = 'under25' or 'over25'."""
    mkt = MARKET[f"{home} v {away}"]
    played = datetime.fromisoformat(mkt["kickoff"]).date()
    probs = devig([mkt["avg_home"], mkt["avg_draw"], mkt["avg_away"]])
    idx = 5 if pick == "under25" else 2          # under edge / over edge
    aligned, opposed = [], []
    for team in (home, away):
        played_last, prev = LAST[team]
        rest = (played - played_last).days
        for label, games in slices(team, home, away, played, prev, rest, probs):
            stat = stats_goals(games, LEAGUE_BTTS)
            if stat is None:
                continue
            edge, n = stat[idx], stat[10]
            cell = {"team": team, "category": label, "edge_pp": round(edge, 1), "n": n}
            if edge >= EDGE_PP:
                aligned.append(cell)
            elif edge <= -EDGE_PP:
                opposed.append(cell)
    return aligned, opposed


def main():
    import pandas as pd
    screen = pd.read_csv(GW / "_supporting" / "ev_screen.csv")
    cands = screen[(screen.market == "OU25") & (screen.ev_best_t5on >= 0.20)]
    out = []
    for _, c in cands.iterrows():
        home, away = c["match"].split(" v ")
        aligned, opposed = audit_ou(home, away, c.selection)
        out.append({"match": c["match"], "selection": c.selection,
                    "best_price": c.market_best, "ev": float(c.ev_best_t5on),
                    "aligned": len(aligned), "opposed": len(opposed),
                    "net": len(aligned) - len(opposed),
                    "dc_reset": c.dc_reset if isinstance(c.dc_reset, str) else "",
                    "aligned_detail": aligned, "opposed_detail": opposed})
    (GW / "_supporting" / "matrix_ou_scan.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    for r in sorted(out, key=lambda x: -x["net"]):
        print(f"\n{r['selection'].upper()} — {r['match']}   net {r['net']:+d}  "
              f"({r['aligned']} aligned / {r['opposed']} opposed)   "
              f"price {r['best_price']:.2f}  EV {r['ev']:+.1%}"
              + (f"   RESET: {r['dc_reset']}" if r["dc_reset"] else ""))
        for tag in ("aligned", "opposed"):
            cells = r[f"{tag}_detail"]
            print(f"   {tag.capitalize()}: " + ("; ".join(
                f"{c['team']} {c['category']} {c['edge_pp']:+.1f}pp (n={c['n']})" for c in cells) or "None"))


if __name__ == "__main__":
    main()
