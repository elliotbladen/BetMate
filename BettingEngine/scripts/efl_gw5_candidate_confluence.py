#!/usr/bin/env python3
"""Apply the frozen EFL +6 net-matrix rule to GW5 10%+ EV candidates."""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.efl_championship_confluence_matrix import load_rows, odds_band, stats_1x2, team_rows

SOURCE = ROOT / "ml/football/data/championship/matches/championship_matches.csv"
OUT_DIR = ROOT / "outputs/football/championship"
OUT_JSON = OUT_DIR / "gw5_10pct_ev_matrix_confluence_2026-09-03.json"
OUT_MD = OUT_DIR / "gw5_10pct_ev_matrix_confluence_2026-09-03.md"
SEASONS = ("2020/21", "2021/22", "2022/23", "2023/24", "2024/25")
EDGE_PP = 7.5
NET_REQUIRED = 6

# (date, last result, days since last match, current 1X2 market odds)
FIXTURE = {
    ("Lincoln", "Southampton"): (date(2026, 9, 5), {"Lincoln": "D", "Southampton": "D"}, {"Lincoln": 4, "Southampton": 4}, [3.88, 3.85, 1.81]),
    ("Stoke", "Charlton"): (date(2026, 9, 5), {"Stoke": "W", "Charlton": "D"}, {"Stoke": 4, "Charlton": 3}, [2.15, 3.18, 3.48]),
    ("Millwall", "Bolton"): (date(2026, 9, 5), {"Millwall": "L", "Bolton": "L"}, {"Millwall": 3, "Bolton": 4}, [1.55, 3.90, 6.00]),
    ("Sheffield United", "Norwich"): (date(2026, 9, 5), {"Sheffield United": "W", "Norwich": "L"}, {"Sheffield United": 4, "Norwich": 4}, [2.50, 3.50, 2.60]),
    ("Swansea", "Wrexham"): (date(2026, 9, 5), {"Swansea": "W", "Wrexham": "W"}, {"Swansea": 4, "Wrexham": 3}, [2.50, 3.40, 2.70]),
    ("Birmingham", "Wolves"): (date(2026, 9, 6), {"Birmingham": "D", "Wolves": "L"}, {"Birmingham": 5, "Wolves": 5}, [2.99, 3.12, 2.40]),
}

CANDIDATES = [
    ("Lincoln", "Southampton", "Lincoln", 13.6),
    ("Stoke", "Charlton", "Charlton", 11.1),
    ("Millwall", "Bolton", "Bolton", 24.9),
    ("Sheffield United", "Norwich", "Sheffield United", 17.1),
    ("Swansea", "Wrexham", "Swansea", 14.0),
    ("Birmingham", "Wolves", "Birmingham", 25.0),
]


def devig(odds: list[float]) -> list[float]:
    raw = [1 / value for value in odds]
    return [value / sum(raw) for value in raw]


def applicable(team: str, home: str, away: str, played: date, previous: str,
               rest_days: int, price_probs: list[float]):
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


def audit(home: str, away: str, pick: str):
    played, previous, rest_days, odds = FIXTURE[(home, away)]
    probs = devig(odds)
    aligned, opposed = [], []
    opponent = away if pick == home else home
    for team in (pick, opponent):
        for label, games in applicable(team, home, away, played, previous[team], rest_days[team], probs):
            stat = stats_1x2(games, team)
            if stat is None:
                continue
            edge, n = stat[2], stat[6]
            direction = 1 if team == pick else -1
            signal = {"team": team, "category": label, "edge_pp": round(edge, 1), "n": n}
            if edge * direction >= EDGE_PP:
                aligned.append(signal)
            elif edge * direction <= -EDGE_PP:
                opposed.append(signal)
    return aligned, opposed


def main():
    results = []
    for home, away, selection, ev in CANDIDATES:
        aligned, opposed = audit(home, away, selection)
        net = len(aligned) - len(opposed)
        results.append({"home": home, "away": away, "selection": selection, "ev": ev,
                        "aligned": aligned, "opposed": opposed, "net": net,
                        "stake_units": 1.5 if net >= NET_REQUIRED else 1.0})
    OUT_JSON.write_text(json.dumps({"edge_threshold_pp": EDGE_PP, "net_required": NET_REQUIRED,
                                    "seasons": SEASONS, "results": results}, indent=2), encoding="utf-8")
    lines = ["# EFL GW5 10%+ EV candidate matrix audit", "",
             "Rule: normal-engine EV >=10% and net matrix score >=+6. Matrix cells require |edge| >=7.5pp. Live 2026/27 results are excluded.", "",
             "| Selection | EV | Aligned | Opposed | Net | Stake |", "|---|---:|---:|---:|---:|---:|"]
    for row in results:
        lines.append(f"| {row['selection']} — {row['home']} v {row['away']} | {row['ev']:+.1f}% | {len(row['aligned'])} | {len(row['opposed'])} | {row['net']:+d} | **{row['stake_units']:.1f}u** |")
    for row in results:
        lines += ["", f"## {row['selection']} — {row['home']} v {row['away']}", "",
                  "Aligned: " + ("; ".join(f"{x['team']} {x['category']} {x['edge_pp']:+.1f}pp (n={x['n']})" for x in row["aligned"]) or "None"), "",
                  "Opposed: " + ("; ".join(f"{x['team']} {x['category']} {x['edge_pp']:+.1f}pp (n={x['n']})" for x in row["opposed"]) or "None"), ""]
    lines += ["", "Signals overlap and are descriptive rather than independent evidence.", ""]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(OUT_MD.read_text(encoding="utf-8"))


ROWS = load_rows(SOURCE, SEASONS)

if __name__ == "__main__":
    main()
