#!/usr/bin/env python3
"""Flat-stake backtest of the AFL matrix net-confluence rule over a season.

Mirror of ``scripts/backtest_nrl_matrix_net7_2026.py`` so AFL and NRL numbers are
directly comparable. Same rule, same thresholds, same settlement, same reporting.

Rule under test
---------------
For every game in the test season, score each side with the same overlapping
base-rate cells that ``scripts/afl_matrix_confluence.py`` uses in production:

    net = (applicable cells pointing AT the side) - (cells pointing AGAINST it)

Cells come from BOTH teams' sheets. If a side reaches ``--net`` or better in a
market's matrix, back it. One unit per bet.

The shipped matrices are frozen on 2022-25, so 2026 is fully out of sample.

⚠️ AFL COLUMN LAYOUT IS NOT THE NRL LAYOUT. The AFL sheet carries Goals/Behinds
in I-L where NRL carries Over Time, so every market column sits +2 on the NRL
index from "Home Odds Open" onward. Indices below were read off the header row
of the AFL file, not derived from the NRL script.

Usage:
    python scripts/backtest_afl_matrix_2026.py --markets h2h,handicap,totals
    python scripts/backtest_afl_matrix_2026.py --markets totals --totals-version v2 --net 7
"""

from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

import ephem
import openpyxl

ROOT = Path(__file__).resolve().parents[1]
H2H_MATRIX = ROOT / "outputs" / "afl_h2h_matrix.xlsx"
HANDICAP_MATRIX = ROOT / "outputs" / "afl_handicap_matrix.csv"
TOTALS_MATRIX = ROOT / "outputs" / "afl_team_totals_matrix.xlsx"
TOTALS_MATRIX_V2 = ROOT / "outputs" / "afl_team_totals_matrix_v2.xlsx"
RESULTS_XLSX = ROOT / "outputs" / "afl_weekly_review" / "historical" / "latest.xlsx"

MONTH_LABELS = {3: "March", 4: "April", 5: "May", 6: "June",
                7: "July", 8: "August", 9: "September", 10: "October"}

# AFL results xlsx already uses the matrix sheet keys (short names).
TEAM_NAME_MAP: dict[str, str] = {}

# Sections afl_matrix_confluence.py does NOT consult. Included only under --extended.
TRIP_ROWS = ("Away — Local / Short Trip (same state)", "Away — Interstate",
             "Away — Long Haul (Perth / TAS / NT / OS)")

_AFL_TEAM_STATE = {
    "Adelaide": "SA", "Port Adelaide": "SA",
    "Brisbane": "QLD", "Gold Coast": "QLD",
    "Carlton": "VIC", "Collingwood": "VIC", "Essendon": "VIC", "Geelong": "VIC",
    "Hawthorn": "VIC", "Melbourne": "VIC", "North Melbourne": "VIC",
    "Richmond": "VIC", "St Kilda": "VIC", "Western Bulldogs": "VIC",
    "Fremantle": "WA", "West Coast": "WA",
    "GWS Giants": "NSW", "Sydney": "NSW",
}
_AFL_VENUE_STATE = {
    "MCG": "VIC", "Marvel Stadium": "VIC", "Marvl": "VIC",
    "GMHBA Stadium": "VIC", "Mars Stadium": "VIC",
    "Adelaide Oval": "SA", "AAMI Stadium": "SA", "Adelaide Hills": "SA",
    "Barossa Park": "SA", "Norwood Oval": "SA",
    "Optus Stadium": "WA", "Domain Stadium": "WA",
    "Gabba": "QLD", "People First Stadium": "QLD", "Cazaly's Stadium": "QLD",
    "Riverway Stadium": "QLD", "Ninja Stadium": "QLD",
    "SCG": "NSW", "ENGIE Stadium": "NSW", "Accor Stadium": "NSW",
    "Blacktown Park": "NSW", "Manuka Oval": "NSW",
    "UTAS Stadium": "LH", "TIO Stadium": "LH", "Traeger Park": "LH",
    "Jiangwan Sports Centre": "LH", "Westpac Stadium": "LH", "Hands Oval": "LH",
}


# ---------------------------------------------------------------------------
# Matrix loading (mirrors afl_matrix_confluence.py)
# ---------------------------------------------------------------------------

def _parse_edge(val):
    if not val:
        return None
    s = str(val).strip()
    if s in ("—", "-", ""):
        return None
    m = re.match(r"^([\d.]+)%\s+(.+)$", s)
    return (float(m.group(1)), m.group(2).strip().lower()) if m else None


def load_sheet_matrix(path: Path) -> dict:
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    out = {}
    for sheet in wb.sheetnames:
        data = {}
        for row in wb[sheet].iter_rows(min_row=3, values_only=True):
            cat = row[0]
            if not cat:
                continue
            parsed = _parse_edge(row[4] if len(row) > 4 else None)
            if parsed:
                n = row[5] if len(row) > 5 else None
                data[str(cat).strip()] = (parsed[0], parsed[1], n if isinstance(n, int) else None)
        out[sheet] = data
    wb.close()
    return out


def load_handicap_matrix(path: Path) -> dict:
    out: dict[str, dict] = defaultdict(dict)
    with path.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            try:
                edge = float(row["edge_pct"])
                n = int(row["n"])
            except (TypeError, ValueError):
                continue
            direction = row["direction"].strip().lower()
            if direction:
                out[row["team"].strip()][row["category"].strip()] = (edge, direction, n)
    return dict(out)


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------

@dataclass
class Game:
    dt: datetime
    gdate: date
    home: str
    away: str
    venue: str
    home_score: int
    away_score: int
    home_odds_close: float | None
    away_odds_close: float | None
    home_odds_open: float | None
    away_odds_open: float | None
    home_line_close: float | None
    away_line_close: float | None
    home_line_open: float | None
    away_line_open: float | None
    home_line_odds_close: float | None
    away_line_odds_close: float | None
    home_line_odds_open: float | None
    away_line_odds_open: float | None
    total_close: float | None
    total_open: float | None
    over_odds_close: float | None
    under_odds_close: float | None
    over_odds_open: float | None
    under_odds_open: float | None
    ctx: dict = field(default_factory=dict)


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


# AFL header-verified 0-based column indices.
C_HOME_ODDS_OPEN, C_HOME_ODDS_CLOSE = 15, 18
C_AWAY_ODDS_OPEN, C_AWAY_ODDS_CLOSE = 19, 22
C_HOME_LINE_OPEN, C_HOME_LINE_CLOSE = 23, 26
C_AWAY_LINE_OPEN, C_AWAY_LINE_CLOSE = 27, 30
C_HOME_LINE_ODDS_OPEN, C_HOME_LINE_ODDS_CLOSE = 31, 34
C_AWAY_LINE_ODDS_OPEN, C_AWAY_LINE_ODDS_CLOSE = 35, 38
C_TOTAL_OPEN, C_TOTAL_CLOSE = 39, 42
C_OVER_OPEN, C_OVER_CLOSE = 43, 46
C_UNDER_OPEN, C_UNDER_CLOSE = 47, 50

EXPECTED_HEADERS = {
    0: "Date", 5: "Home Score", 6: "Away Score", 7: "Play Off Game?",
    C_HOME_ODDS_CLOSE: "Home Odds Close", C_AWAY_ODDS_CLOSE: "Away Odds Close",
    C_HOME_LINE_CLOSE: "Home Line Close", C_AWAY_LINE_CLOSE: "Away Line Close",
    C_HOME_LINE_ODDS_CLOSE: "Home Line Odds Close",
    C_AWAY_LINE_ODDS_CLOSE: "Away Line Odds Close",
    C_TOTAL_OPEN: "Total Score Open", C_TOTAL_CLOSE: "Total Score Close",
    C_OVER_CLOSE: "Total Score Over Close", C_UNDER_CLOSE: "Total Score Under Close",
}


def assert_layout(ws) -> None:
    """Fail loudly if the sheet is not the layout these indices were read from.

    A silently shifted column would still produce plausible ROI, which is the
    failure mode this repo keeps hitting.
    """
    header = next(ws.iter_rows(min_row=2, max_row=2, values_only=True))
    bad = []
    for idx, want in EXPECTED_HEADERS.items():
        got = str(header[idx]).strip() if idx < len(header) and header[idx] else None
        if got != want:
            bad.append(f"col {idx}: expected {want!r}, found {got!r}")
    if bad:
        raise SystemExit("AFL results layout changed:\n  " + "\n  ".join(bad))


def load_games(path: Path) -> list[Game]:
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    assert_layout(ws)
    games = []
    for r in ws.iter_rows(min_row=3, values_only=True):
        d = r[0]
        if not d or not hasattr(d, "year") or r[5] is None or r[6] is None:
            continue
        gdate = d.date() if hasattr(d, "date") else d
        ko = r[1]
        if ko is not None and hasattr(ko, "hour") and not hasattr(ko, "date"):
            dt = datetime.combine(gdate, ko)
        elif ko is not None and hasattr(ko, "date"):
            dt = datetime.combine(gdate, ko.time())
        else:
            dt = datetime(gdate.year, gdate.month, gdate.day, 14, 30)
        home = TEAM_NAME_MAP.get(r[2], r[2])
        away = TEAM_NAME_MAP.get(r[3], r[3])
        games.append(Game(
            dt=dt, gdate=gdate, home=home, away=away, venue=r[4] or "Unknown",
            home_score=int(r[5]), away_score=int(r[6]),
            home_odds_close=_f(r[C_HOME_ODDS_CLOSE]), away_odds_close=_f(r[C_AWAY_ODDS_CLOSE]),
            home_odds_open=_f(r[C_HOME_ODDS_OPEN]), away_odds_open=_f(r[C_AWAY_ODDS_OPEN]),
            home_line_close=_f(r[C_HOME_LINE_CLOSE]), away_line_close=_f(r[C_AWAY_LINE_CLOSE]),
            home_line_open=_f(r[C_HOME_LINE_OPEN]), away_line_open=_f(r[C_AWAY_LINE_OPEN]),
            home_line_odds_close=_f(r[C_HOME_LINE_ODDS_CLOSE]),
            away_line_odds_close=_f(r[C_AWAY_LINE_ODDS_CLOSE]),
            home_line_odds_open=_f(r[C_HOME_LINE_ODDS_OPEN]),
            away_line_odds_open=_f(r[C_AWAY_LINE_ODDS_OPEN]),
            total_close=_f(r[C_TOTAL_CLOSE]), total_open=_f(r[C_TOTAL_OPEN]),
            over_odds_close=_f(r[C_OVER_CLOSE]), under_odds_close=_f(r[C_UNDER_CLOSE]),
            over_odds_open=_f(r[C_OVER_OPEN]), under_odds_open=_f(r[C_UNDER_OPEN]),
        ))
    wb.close()
    games.sort(key=lambda g: g.dt)
    return games


def attach_context(games: list[Game]) -> None:
    """Rest days + last result per team, from the full multi-season history."""
    seen: dict[str, Game] = {}
    for g in games:
        for team in (g.home, g.away):
            prev = seen.get(team)
            if prev is None:
                g.ctx[team] = {"rest_days": None, "last_result": None}
            else:
                margin = (prev.home_score - prev.away_score) if prev.home == team \
                    else (prev.away_score - prev.home_score)
                g.ctx[team] = {
                    "rest_days": (g.gdate - prev.gdate).days,
                    "last_result": "win" if margin > 0 else ("loss" if margin < 0 else "draw"),
                }
        seen[g.home] = g
        seen[g.away] = g


# ---------------------------------------------------------------------------
# Applicable rows (mirrors afl_matrix_confluence.applicable_row_names)
# ---------------------------------------------------------------------------

_moon_cache: dict[date, str | None] = {}


def moon_row(d: date) -> str | None:
    if d in _moon_cache:
        return _moon_cache[d]
    e = ephem.Date(d.strftime("%Y/%m/%d 12:00:00"))
    near_new = min(abs(float(e) - float(ephem.previous_new_moon(e))),
                   abs(float(ephem.next_new_moon(e)) - float(e)))
    near_full = min(abs(float(e) - float(ephem.previous_full_moon(e))),
                    abs(float(ephem.next_full_moon(e)) - float(e)))
    out = "New Moon (±1 day)" if near_new <= 1.0 else ("Full Moon (±1 day)" if near_full <= 1.0 else None)
    _moon_cache[d] = out
    return out


def line_bucket(line: float | None) -> list[str]:
    if line is None:
        return []
    rows = ["As Favourite (line < 0)" if line < 0 else "As Underdog  (line > 0)"]
    if line <= -9.5:
        rows.append("Heavy Fav (line ≤ -9.5)")
    elif -9.5 < line < 0:
        rows.append("Slight Fav (line -1 to -9)")
    elif 0 < line < 9.5:
        rows.append("Slight Dog (line +1 to +9)")
    elif line >= 9.5:
        rows.append("Big Dog    (line ≥ +9.5)")
    return rows


def applicable_rows(g: Game, team: str, role: str, generic: str, market: str,
                    extended: bool, line: float | None) -> list[str]:
    rows = [generic]
    rows.append("Night Games (kick-off ≥ 18:00)" if g.dt.hour >= 18 else "Day Games (kick-off < 18:00)")
    wd = g.dt.weekday()
    if wd in (3, 4):
        rows.append("Thursday / Friday Games")
    elif wd == 5:
        rows.append("Saturday Games")
    elif wd == 6:
        rows.append("Sunday Games")
    ctx = g.ctx[team]
    # AFL production consults only the short and long bands, never "Normal Rest".
    if ctx["rest_days"] is not None:
        if ctx["rest_days"] <= 6:
            rows.append("Short Rest (≤ 6 days)")
        elif ctx["rest_days"] >= 10:
            rows.append("Long Rest / Bye (≥ 10 days)")
    if ctx["last_result"] == "win":
        rows.append("After a Win")
    elif ctx["last_result"] == "loss":
        rows.append("After a Loss")
    month = MONTH_LABELS.get(g.gdate.month)
    if month:
        rows.append(month)
    mr = moon_row(g.gdate)
    if mr:
        rows.append(mr)
    rows.append(f"vs {g.away if role == 'home' else g.home}")
    rows.append(g.venue)
    if extended:
        if role == "away":
            vs = _AFL_VENUE_STATE.get(g.venue, "LH")
            ts = _AFL_TEAM_STATE.get(team, "VIC")
            if vs == "LH" or (vs == "WA" and ts != "WA"):
                rows.append(TRIP_ROWS[2])
            elif vs == ts:
                rows.append(TRIP_ROWS[0])
            else:
                rows.append(TRIP_ROWS[1])
        if market == "handicap":
            rows.extend(line_bucket(line))
    return rows


GENERIC = {"h2h": ("Win % — Home", "Win % — Away"),
           "handicap": ("Cover Rate — Home", "Cover Rate — Away"),
           "totals": ("Total Points — Home", "Total Points — Away")}
FAVOURS = {"h2h": {"backing": True, "opposing": False},
           "handicap": {"covers": True, "fades": False}}
TOTALS_SIDES = ("over", "under")


def score_game(g: Game, matrix: dict, market: str, min_edge: float,
               min_n: int, extended: bool) -> dict:
    is_totals = market == "totals"
    tally = {"over": [], "under": []} if is_totals else {"home": [], "away": []}
    home_generic, away_generic = GENERIC[market]
    for team, role, generic, line in (
        (g.home, "home", home_generic, g.home_line_close),
        (g.away, "away", away_generic, g.away_line_close),
    ):
        data = matrix.get(team, {})
        for row in applicable_rows(g, team, role, generic, market, extended, line):
            cell = data.get(row)
            if not cell:
                continue
            edge, direction, n = cell
            if edge < min_edge:
                continue
            if min_n and (n is None or n < min_n):
                continue
            if is_totals:
                if "overs" in direction:
                    side = "over"
                elif "unders" in direction:
                    side = "under"
                else:
                    continue
            else:
                favours = FAVOURS[market].get(direction)
                if favours is None:
                    continue
                side = role if favours else ("away" if role == "home" else "home")
            tally[side].append((edge, row, team))
    a, b = ("over", "under") if is_totals else ("home", "away")
    return {a: len(tally[a]) - len(tally[b]),
            b: len(tally[b]) - len(tally[a]),
            "cells": tally}


# ---------------------------------------------------------------------------
# Settlement
# ---------------------------------------------------------------------------

def settle_h2h(g: Game, side: str) -> str:
    m = g.home_score - g.away_score
    if m == 0:
        return "draw"
    won = (m > 0) if side == "home" else (m < 0)
    return "win" if won else "loss"


def settle_line(g: Game, side: str, line: float | None) -> str:
    if line is None:
        return "novoid"
    m = (g.home_score - g.away_score) if side == "home" else (g.away_score - g.home_score)
    adj = m + line
    if adj == 0:
        return "push"
    return "win" if adj > 0 else "loss"


def settle_total(g: Game, side: str, line: float | None) -> str:
    if line is None:
        return "novoid"
    total = g.home_score + g.away_score
    if total == line:
        return "push"
    hit = (total > line) if side == "over" else (total < line)
    return "win" if hit else "loss"


def run(games, season, markets, net, min_edge, min_n, extended, price):
    bets = []
    for g in [x for x in games if x.gdate.year == season]:
        for market, matrix in markets:
            s = score_game(g, matrix, market, min_edge, min_n, extended)
            sides = TOTALS_SIDES if market == "totals" else ("home", "away")
            for side in sides:
                if s[side] < net:
                    continue
                if market == "totals":
                    team, opp = side.upper(), f"{g.home} v {g.away}"
                    if price == "close":
                        line = g.total_close
                        pr = g.over_odds_close if side == "over" else g.under_odds_close
                    else:
                        line = g.total_open
                        pr = g.over_odds_open if side == "over" else g.under_odds_open
                    result = settle_total(g, side, line)
                elif market == "h2h":
                    team = g.home if side == "home" else g.away
                    opp = g.away if side == "home" else g.home
                    pr = (g.home_odds_close if side == "home" else g.away_odds_close) \
                        if price == "close" else \
                        (g.home_odds_open if side == "home" else g.away_odds_open)
                    result, line = settle_h2h(g, side), None
                else:
                    team = g.home if side == "home" else g.away
                    opp = g.away if side == "home" else g.home
                    if price == "close":
                        line = g.home_line_close if side == "home" else g.away_line_close
                        pr = g.home_line_odds_close if side == "home" else g.away_line_odds_close
                    else:
                        line = g.home_line_open if side == "home" else g.away_line_open
                        pr = g.home_line_odds_open if side == "home" else g.away_line_odds_open
                    result = settle_line(g, side, line)
                if pr is None or result == "novoid":
                    result, pnl = "no_price", 0.0
                elif result == "win":
                    pnl = pr - 1.0
                elif result in ("push", "draw"):
                    pnl = 0.0 if result == "push" else -1.0
                else:
                    pnl = -1.0
                bets.append({
                    "date": g.gdate.isoformat(), "market": market, "team": team,
                    "opponent": opp, "side": side, "venue": g.venue,
                    "net": s[side], "line": line, "price": pr,
                    "score": f"{g.home_score}-{g.away_score}",
                    "result": result, "pnl": round(pnl, 4),
                    "for_cells": len(s["cells"][side]),
                })
    return bets


def summarise(rows, label):
    priced = [b for b in rows if b["result"] != "no_price"]
    if not priced:
        print(f"{label:<12} no bets")
        return None
    staked = sum(1 for b in priced if b["result"] != "push")
    wins = sum(1 for b in priced if b["result"] == "win")
    pushes = sum(1 for b in priced if b["result"] == "push")
    pnl = sum(b["pnl"] for b in priced)
    roi = pnl / len(priced) * 100
    avg_price = sum(b["price"] for b in priced) / len(priced)
    strike = wins / staked * 100 if staked else 0.0
    print(f"{label:<12} bets {len(priced):>3}  W-L {wins}-{len(priced)-wins-pushes}"
          f"{f' (push {pushes})' if pushes else ''}"
          f"  strike {strike:5.1f}%  avg ${avg_price:.2f}"
          f"  P/L ${pnl:+.2f}  ROI {roi:+.2f}%")
    return roi


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", type=int, default=2026)
    ap.add_argument("--net", type=int, default=7)
    ap.add_argument("--min-edge", type=float, default=5.0)
    ap.add_argument("--min-n", type=int, default=0)
    ap.add_argument("--extended", action="store_true")
    ap.add_argument("--price", choices=["close", "open"], default="close")
    ap.add_argument("--totals-matrix", type=Path, default=None)
    ap.add_argument("--totals-version", choices=["v1", "v2"], default="v1")
    ap.add_argument("--markets", default="h2h,handicap")
    ap.add_argument("--csv", type=Path, default=None)
    ap.add_argument("--quiet", action="store_true", help="summary only, no bet list")
    args = ap.parse_args()

    wanted = [m.strip() for m in args.markets.split(",") if m.strip()]
    available = {
        "h2h": load_sheet_matrix(H2H_MATRIX) if "h2h" in wanted else {},
        "handicap": load_handicap_matrix(HANDICAP_MATRIX) if "handicap" in wanted else {},
        "totals": load_sheet_matrix(args.totals_matrix or
                                    (TOTALS_MATRIX_V2 if args.totals_version == "v2" else TOTALS_MATRIX))
        if "totals" in wanted else {},
    }
    markets = [(m, available[m]) for m in wanted]
    games = load_games(RESULTS_XLSX)
    attach_context(games)
    season_games = [g for g in games if g.gdate.year == args.season]

    bets = run(games, args.season, markets, args.net, args.min_edge,
               args.min_n, args.extended, args.price)

    print(f"\nAFL {args.season} — matrix net +{args.net} rule, $1 flat, "
          f"{args.price} price, cells ≥{args.min_edge:g}% edge"
          f"{', totals ' + args.totals_version if 'totals' in wanted else ''}"
          f"{', extended rows' if args.extended else ''}"
          f"{f', min N={args.min_n}' if args.min_n else ''}")
    print(f"games in season: {len(season_games)}\n")
    for m in wanted:
        summarise([b for b in bets if b["market"] == m], m.upper())
    if len(wanted) > 1:
        summarise(bets, "COMBINED")

    if bets and not args.quiet:
        print("\n  date        market    team                      net  line   price  score    result   pnl")
        for b in sorted(bets, key=lambda x: (x["date"], x["market"])):
            ln = f"{b['line']:+.1f}" if b["line"] is not None else "   — "
            pr = f"{b['price']:.2f}" if b["price"] else "  — "
            print(f"  {b['date']}  {b['market']:<9} {b['team']:<24} {b['net']:+3d} {ln:>6} {pr:>7}"
                  f"  {b['score']:<8} {b['result']:<7} {b['pnl']:+.2f}")

    if args.csv:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        with args.csv.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(bets[0].keys()))
            w.writeheader()
            w.writerows(bets)
        print(f"\nwrote {args.csv}")


if __name__ == "__main__":
    main()
