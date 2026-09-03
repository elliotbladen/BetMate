#!/usr/bin/env python3
"""Apply the saved EPL +6 net-matrix rule to GW3 10%+ EV candidates."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from scripts.efl_championship_confluence_matrix import (
    build_workbook, load_rows, odds_band, stats_1x2, stats_goals, team_rows,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "ml/football/data/epl/matches/epl_matches.csv"
OUT_DIR = ROOT / "outputs/football/epl"
OUT_JSON = OUT_DIR / "gw3_10pct_ev_matrix_confluence_2026-09-03.json"
OUT_MD = OUT_DIR / "gw3_10pct_ev_matrix_confluence_2026-09-03.md"
SEASONS = ("2022/23", "2023/24", "2024/25", "2025/26")
EDGE_PP = 7.5
NET_REQUIRED = 6

FIXTURE = {
    ("Ipswich", "Liverpool"): (date(2026, 9, 4), {"Ipswich": "L", "Liverpool": "D"}, [5.5, 4.4, 1.5]),
    ("Brentford", "Sunderland"): (date(2026, 9, 5), {"Brentford": "D", "Sunderland": "W"}, [1.55, 4.0, 5.5]),
    ("Hull", "Aston Villa"): (date(2026, 9, 5), {"Hull": "W", "Aston Villa": "L"}, [4.1, 3.6, 1.8]),
    ("Everton", "Man United"): (date(2026, 9, 6), {"Everton": "D", "Man United": "W"}, [3.1, 3.5, 2.15]),
    ("Newcastle", "Bournemouth"): (date(2026, 9, 5), {"Newcastle": "D", "Bournemouth": "D"}, [2.15, 3.7, 3.0]),
    ("Arsenal", "Chelsea"): (date(2026, 9, 6), {"Arsenal": "W", "Chelsea": "W"}, [1.6667, 3.8, 4.75]),
}

CANDIDATES = [
    {"market": "1X2", "home": "Ipswich", "away": "Liverpool", "selection": "Ipswich", "ev": 23.32},
    {"market": "1X2", "home": "Brentford", "away": "Sunderland", "selection": "Sunderland", "ev": 35.71},
    {"market": "1X2", "home": "Hull", "away": "Aston Villa", "selection": "Hull", "ev": 30.10},
    {"market": "1X2", "home": "Everton", "away": "Man United", "selection": "Everton", "ev": 34.82},
    {"market": "O/U 2.5", "home": "Newcastle", "away": "Bournemouth", "selection": "Over", "ev": 22.11},
    {"market": "O/U 2.5", "home": "Everton", "away": "Man United", "selection": "Over", "ev": 14.49},
    {"market": "O/U 2.5", "home": "Arsenal", "away": "Chelsea", "selection": "Over", "ev": 34.69},
]


def devig(odds: list[float]) -> list[float]:
    raw = [1 / x for x in odds]
    return [x / sum(raw) for x in raw]


def applicable(team: str, home: str, away: str, played: date, previous: str,
               price_probs: list[float]) -> list[tuple[str, list[dict]]]:
    games = team_rows(ROWS, team)
    fake = {"market_1x2": (price_probs, "current"), "home": home, "away": away}
    band = odds_band(fake, team)
    return [
        ("All games", games),
        ("Home games" if team == home else "Away games", [g for g in games if g["home" if team == home else "away"] == team]),
        (played.strftime("%A"), [g for g in games if g["weekday"] == played.weekday()]),
        (played.strftime("%B"), [g for g in games if g["month"] == played.month]),
        ({"W": "After a win", "D": "After a draw", "L": "After a loss"}[previous],
         [g for g in games if g.get(f"previous__{team}") == previous]),
        ("Normal rest (4-8 days)", [g for g in games if g.get(f"rest__{team}") is not None and 4 <= g[f"rest__{team}"] <= 8]),
        (band or "No price band", [g for g in games if odds_band(g, team) == band] if band else []),
        (f"vs {away if team == home else home}", [g for g in games if (away if team == home else home) in (g["home"], g["away"])]),
    ]


def one_x_two(candidate: dict) -> tuple[list[dict], list[dict]]:
    home, away, pick = candidate["home"], candidate["away"], candidate["selection"]
    played, previous, odds = FIXTURE[(home, away)]
    probs = devig(odds)
    aligned, opposed = [], []
    opponent = away if pick == home else home
    for team in (pick, opponent):
        for label, games in applicable(team, home, away, played, previous[team], probs):
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


def totals(candidate: dict) -> tuple[list[dict], list[dict]]:
    home, away = candidate["home"], candidate["away"]
    played, previous, odds = FIXTURE[(home, away)]
    probs = devig(odds)
    aligned, opposed = [], []
    for team in (home, away):
        for label, games in applicable(team, home, away, played, previous[team], probs):
            stat = stats_goals(games, LEAGUE_BTTS)
            if stat is None:
                continue
            over_edge, n = stat[2], stat[10]
            signal = {"team": team, "category": label, "edge_pp": round(over_edge, 1), "n": n}
            direction = 1 if candidate["selection"] == "Over" else -1
            if over_edge * direction >= EDGE_PP:
                aligned.append(signal)
            elif over_edge * direction <= -EDGE_PP:
                opposed.append(signal)
    return aligned, opposed


def main() -> None:
    teams = sorted(set(r["home"] for r in ROWS) | set(r["away"] for r in ROWS))
    build_workbook(ROWS, teams, SEASONS, "1x2", OUT_DIR / "epl_1x2_confluence_matrix.xlsx",
                   league_name="English Premier League", holdout_note="Live 2026/27 excluded.")
    build_workbook(ROWS, teams, SEASONS, "goals", OUT_DIR / "epl_goals_confluence_matrix.xlsx",
                   league_name="English Premier League", holdout_note="Live 2026/27 excluded.")
    results = []
    for candidate in CANDIDATES:
        aligned, opposed = one_x_two(candidate) if candidate["market"] == "1X2" else totals(candidate)
        net = len(aligned) - len(opposed)
        results.append({**candidate, "aligned": aligned, "opposed": opposed, "net": net,
                        "passes_10pct_ev": candidate["ev"] >= 10,
                        "passes_matrix": net >= NET_REQUIRED,
                        "stake_units": 1.5 if candidate["ev"] >= 10 and net >= NET_REQUIRED else 1.0})
    OUT_JSON.write_text(json.dumps({"edge_threshold_pp": EDGE_PP, "net_required": NET_REQUIRED,
                                    "seasons": SEASONS, "results": results}, indent=2), encoding="utf-8")
    lines = ["# EPL GW3 10%+ EV candidate matrix audit", "",
             f"Rule: normal-engine EV >=10% and net matrix score >=+{NET_REQUIRED}. Matrix cells require |edge| >={EDGE_PP}pp. Live 2026/27 results are excluded.", "",
             "| Market | Selection | EV | Aligned | Opposed | Net | Stake |", "|---|---|---:|---:|---:|---:|---:|"]
    for r in results:
        lines.append(f"| {r['market']} | {r['selection']} — {r['home']} v {r['away']} | {r['ev']:+.1f}% | {len(r['aligned'])} | {len(r['opposed'])} | {r['net']:+d} | **{r['stake_units']:.1f}u** |")
    for r in results:
        lines += ["", f"## {r['selection']} — {r['home']} v {r['away']}", "",
                  "Aligned: " + ("; ".join(f"{x['team']} {x['category']} {x['edge_pp']:+.1f}pp (n={x['n']})" for x in r["aligned"]) or "None"), "",
                  "Opposed: " + ("; ".join(f"{x['team']} {x['category']} {x['edge_pp']:+.1f}pp (n={x['n']})" for x in r["opposed"]) or "None"), ""]
    lines += ["", "Signals overlap and are descriptive, not independent. Promoted clubs can have insufficient recent EPL samples; missing evidence is not positive evidence.", ""]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(OUT_MD.read_text(encoding="utf-8"))


ROWS = load_rows(SOURCE, SEASONS)
LEAGUE_BTTS = sum(int(r["home_goals"] > 0 and r["away_goals"] > 0) for r in ROWS) / len(ROWS)

if __name__ == "__main__":
    main()
