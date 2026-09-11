#!/usr/bin/env python3
"""Apply the frozen EFL +6 net-matrix rule to GW7 10%+ EV 1X2 candidates.

Same rule as the GW5 audit, but the fixture context (last result, rest days,
current de-vigged prices) is derived from the matches CSV and the live market
file rather than hand-entered, and candidates are read from the EV screen.
"""
from __future__ import annotations

import csv
import json
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.efl_championship_confluence_matrix import load_rows, odds_band, stats_1x2, team_rows

SOURCE = ROOT / "ml/football/data/championship/matches/championship_matches.csv"
GW = ROOT / "outputs/football/championship/2026-27/gw07"
SEASONS = ("2020/21", "2021/22", "2022/23", "2023/24", "2024/25")
EDGE_PP = 7.5
NET_REQUIRED = 6
MARKET = json.loads((Path(__file__).resolve().parent / "_efl_gw7_market_2026.json").read_text())
SIDE = {"home": 0, "draw": 1, "away": 2}


def fixture_context():
    """Last result and rest days per club from the 2026/27 rows of the matches CSV."""
    rows = []
    with open(SOURCE, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["Season"] == "2026/27" and r["FTR"] in ("H", "D", "A"):
                rows.append((datetime.fromisoformat(r["Date"]).date(),
                             r["HomeTeam"], r["AwayTeam"], r["FTR"]))
    rows.sort()
    last: dict[str, tuple[date, str]] = {}
    for d, h, a, ftr in rows:
        last[h] = (d, {"H": "W", "D": "D", "A": "L"}[ftr])
        last[a] = (d, {"A": "W", "D": "D", "H": "L"}[ftr])
    return last


LAST = fixture_context()


def devig(odds):
    raw = [1 / v for v in odds]
    return [v / sum(raw) for v in raw]


def applicable(team, home, away, played, previous, rest_days, price_probs):
    games = team_rows(ROWS, team)
    fake = {"market_1x2": (price_probs, "current"), "home": home, "away": away}
    band = odds_band(fake, team)
    if rest_days <= 3:
        rest_label = "Short rest (<=3 days)"
        rest_games = [g for g in games if g.get(f"rest__{team}") is not None and g[f"rest__{team}"] <= 3]
    elif rest_days <= 8:
        rest_label = "Normal rest (4-8 days)"
        rest_games = [g for g in games if g.get(f"rest__{team}") is not None and 4 <= g[f"rest__{team}"] <= 8]
    else:
        rest_label = "Long rest (>=9 days)"
        rest_games = [g for g in games if g.get(f"rest__{team}") is not None and g[f"rest__{team}"] >= 9]
    venue_key = "home" if team == home else "away"
    opponent = away if team == home else home
    return [
        ("All games", games),
        ("Home games" if venue_key == "home" else "Away games", [g for g in games if g[venue_key] == team]),
        (played.strftime("%A"), [g for g in games if g["weekday"] == played.weekday()]),
        (played.strftime("%B"), [g for g in games if g["month"] == played.month]),
        ({"W": "After a win", "D": "After a draw", "L": "After a loss"}[previous],
         [g for g in games if g.get(f"previous__{team}") == previous]),
        (rest_label, rest_games),
        (band or "No price band", [g for g in games if odds_band(g, team) == band] if band else []),
        (f"vs {opponent}", [g for g in games if opponent in (g["home"], g["away"])]),
    ]


def audit(home, away, pick_team):
    mkt = MARKET[f"{home} v {away}"]
    played = datetime.fromisoformat(mkt["kickoff"]).date()
    probs = devig([mkt["avg_home"], mkt["avg_draw"], mkt["avg_away"]])
    aligned, opposed = [], []
    opponent = away if pick_team == home else home
    for team in (pick_team, opponent):
        played_last, prev = LAST[team]
        rest = (played - played_last).days
        for label, games in applicable(team, home, away, played, prev, rest, probs):
            stat = stats_1x2(games, team)
            if stat is None:
                continue
            edge, n = stat[2], stat[6]
            direction = 1 if team == pick_team else -1
            signal = {"team": team, "category": label, "edge_pp": round(edge, 1), "n": n}
            if edge * direction >= EDGE_PP:
                aligned.append(signal)
            elif edge * direction <= -EDGE_PP:
                opposed.append(signal)
    return aligned, opposed


def main():
    import pandas as pd
    screen = pd.read_csv(GW / "_supporting" / "ev_screen.csv")
    cands = screen[(screen.market == "1X2") & (screen.selection != "draw")
                   & (screen.ev_best_t5on >= 0.10)]
    results = []
    for _, c in cands.iterrows():
        home, away = c["match"].split(" v ")
        pick = home if c.selection == "home" else away
        aligned, opposed = audit(home, away, pick)
        net = len(aligned) - len(opposed)
        results.append({"home": home, "away": away, "selection": pick,
                        "ev": float(c.ev_best_t5on) * 100, "aligned": aligned,
                        "opposed": opposed, "net": net,
                        "stake_units": 1.5 if net >= NET_REQUIRED else 1.0})
    (GW / "2_bets_matrix.json").write_text(json.dumps(
        {"edge_threshold_pp": EDGE_PP, "net_required": NET_REQUIRED,
         "seasons": SEASONS, "note": "Draws are excluded - the matrix scores team sides only.",
         "results": results}, indent=2), encoding="utf-8")
    lines = ["# EFL Championship GW7 — 10%+ EV candidate matrix audit", "",
             "Rule: normal-engine EV >=10% at the best price and net matrix score >=+6 for the",
             "1.5u stake. Matrix cells require |edge| >=7.5pp over 2020/21-2024/25. Live 2026/27",
             "results are excluded from the matrix. Draw selections are not scored by this matrix.", "",
             "| Selection | EV (best) | Aligned | Opposed | Net | Matrix stake |", "|---|---:|---:|---:|---:|---:|"]
    for r in results:
        lines.append(f"| {r['selection']} — {r['home']} v {r['away']} | {r['ev']:+.1f}% | "
                     f"{len(r['aligned'])} | {len(r['opposed'])} | {r['net']:+d} | {r['stake_units']:.1f}u |")
    for r in results:
        lines += ["", f"## {r['selection']} — {r['home']} v {r['away']}", "",
                  "Aligned: " + ("; ".join(f"{x['team']} {x['category']} {x['edge_pp']:+.1f}pp (n={x['n']})"
                                           for x in r["aligned"]) or "None"), "",
                  "Opposed: " + ("; ".join(f"{x['team']} {x['category']} {x['edge_pp']:+.1f}pp (n={x['n']})"
                                           for x in r["opposed"]) or "None"), ""]
    lines += ["", "Signals overlap heavily and are descriptive, not independent evidence. The matrix",
              "stake column is what the frozen rule *would* say; it is not a recommendation here.", ""]
    (GW / "2_bets_matrix.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines[:12]))


ROWS = load_rows(SOURCE, SEASONS)

if __name__ == "__main__":
    main()
