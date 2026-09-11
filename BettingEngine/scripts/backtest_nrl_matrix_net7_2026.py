#!/usr/bin/env python3
"""Flat-stake backtest of the NRL matrix net-confluence rule over the 2026 season.

Rule under test
---------------
For every 2026 NRL game, score each team side with the same overlapping
base-rate cells that ``scripts/matrix_confluence.py`` uses in production:

    net = (applicable cells pointing AT the side) - (cells pointing AGAINST it)

Cells come from BOTH teams' sheets (an "opposing" cell on the opponent's sheet
is a positive for this side, exactly as the production confluence buckets it).
If a side reaches ``--net`` or better in the H2H matrix, back it to win; if it
reaches it in the handicap matrix, back it on the line. One unit per bet.

The matrices are frozen on 2022-25, so 2026 is fully out of sample.

Usage:
    python scripts/backtest_nrl_matrix_net7_2026.py
    python scripts/backtest_nrl_matrix_net7_2026.py --net 7 --min-edge 5 --season 2026
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
H2H_MATRIX = ROOT / "outputs" / "nrl_h2h_matrix.xlsx"
HANDICAP_MATRIX = ROOT / "outputs" / "nrl_handicap_matrix.csv"
TOTALS_MATRIX = ROOT / "outputs" / "nrl_team_totals_matrix.xlsx"
TOTALS_MATRIX_V2 = ROOT / "outputs" / "nrl_team_totals_matrix_v2.xlsx"
RESULTS_XLSX = ROOT / "outputs" / "nrl_weekly_review" / "historical" / "latest.xlsx"

MONTH_LABELS = {3: "March", 4: "April", 5: "May", 6: "June",
                7: "July", 8: "August", 9: "September", 10: "October"}

TEAM_NAME_MAP = {  # results xlsx already uses matrix keys, kept for safety
    "Canterbury-Bankstown Bulldogs": "Canterbury Bulldogs",
    "Cronulla-Sutherland Sharks": "Cronulla Sharks",
    "Manly-Warringah Sea Eagles": "Manly Sea Eagles",
    "North Queensland Cowboys": "North QLD Cowboys",
    "St George Illawarra Dragons": "St George Dragons",
}

# Sections matrix_confluence.py does NOT consult. Included only under --extended.
TRIP_ROWS = ("Away — Local / Short Trip (same state)", "Away — Interstate",
             "Away — Long Haul (NZ / Perth / Darwin / Vegas)")

_NRL_TEAM_STATE = {
    "Brisbane Broncos": "QLD", "Gold Coast Titans": "QLD", "North QLD Cowboys": "QLD",
    "Dolphins": "QLD", "Canberra Raiders": "NSW", "Canterbury Bulldogs": "NSW",
    "Cronulla Sharks": "NSW", "Manly Sea Eagles": "NSW", "Newcastle Knights": "NSW",
    "Parramatta Eels": "NSW", "Penrith Panthers": "NSW", "South Sydney Rabbitohs": "NSW",
    "St George Dragons": "NSW", "Sydney Roosters": "NSW", "Wests Tigers": "NSW",
    "Melbourne Storm": "VIC", "New Zealand Warriors": "NZ",
}
_NRL_VENUE_STATE = {
    "Suncorp Stadium": "QLD", "Cbus Super Stadium": "QLD", "QCB Stadium": "QLD",
    "Sunshine Coast Stadium": "QLD", "Moreton Daily Stadium": "QLD", "Kayo Stadium": "QLD",
    "Clive Berghofer Stadium": "QLD", "Browne Park": "QLD", "BB Print Stadium": "QLD",
    "Barlow Park": "QLD", "McLean Park": "QLD", "McDonalds Park": "QLD",
    "Carrington Park": "QLD", "Polytec Stadium": "QLD", "Ocean Protect Stadium": "QLD",
    "Glen Willow Regional Sports Stadium": "QLD", "Scully Park": "QLD", "The Gabba": "QLD",
    "Accor Stadium": "NSW", "CommBank Stadium": "NSW", "Allianz Stadium": "NSW",
    "Jubilee Stadium": "NSW", "McDonald Jones Stadium": "NSW", "GIO Stadium": "NSW",
    "4 Pines Park (Brookvale Oval)": "NSW", "WIN Stadium": "NSW", "SCG": "NSW",
    "Campbelltown Stadium": "NSW", "BlueBet Stadium": "NSW", "Central Coast Stadium": "NSW",
    "Leichhardt Oval": "NSW", "Apex Oval": "NSW", "Belmore Sports Ground": "NSW",
    "AAMI Park": "VIC", "Marvel Stadium": "VIC",
    "Go Media Stadium": "NZ", "Apollo Projects Stadium": "NZ", "Hnry Stadium": "NZ",
    "Sky Stadium": "NZ", "FMG Stadium": "NZ",
    "Allegiant Stadium": "LH", "HBF Park": "LH", "Optus Stadium": "LH", "TIO Stadium": "LH",
}


# ---------------------------------------------------------------------------
# Matrix loading (mirrors matrix_confluence.py)
# ---------------------------------------------------------------------------

def _parse_edge(val):
    if not val:
        return None
    s = str(val).strip()
    if s in ("—", "-", ""):
        return None
    m = re.match(r"^([\d.]+)%\s+(.+)$", s)
    return (float(m.group(1)), m.group(2).strip().lower()) if m else None


def load_h2h_matrix(path: Path) -> dict:
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


def load_games(path: Path) -> list[Game]:
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
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
            dt = datetime(gdate.year, gdate.month, gdate.day, 19, 0)
        home = TEAM_NAME_MAP.get(r[2], r[2])
        away = TEAM_NAME_MAP.get(r[3], r[3])
        games.append(Game(
            dt=dt, gdate=gdate, home=home, away=away, venue=r[4] or "Unknown",
            home_score=int(r[5]), away_score=int(r[6]),
            home_odds_close=_f(r[16]), away_odds_close=_f(r[20]),
            home_odds_open=_f(r[13]), away_odds_open=_f(r[17]),
            home_line_close=_f(r[24]), away_line_close=_f(r[28]),
            home_line_open=_f(r[21]), away_line_open=_f(r[25]),
            home_line_odds_close=_f(r[32]), away_line_odds_close=_f(r[36]),
            home_line_odds_open=_f(r[29]), away_line_odds_open=_f(r[33]),
            total_close=_f(r[40]), total_open=_f(r[37]),
            over_odds_close=_f(r[44]), under_odds_close=_f(r[48]),
            over_odds_open=_f(r[41]), under_odds_open=_f(r[45]),
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
                if prev.home == team:
                    margin = prev.home_score - prev.away_score
                else:
                    margin = prev.away_score - prev.home_score
                g.ctx[team] = {
                    "rest_days": (g.gdate - prev.gdate).days,
                    "last_result": "win" if margin > 0 else ("loss" if margin < 0 else "draw"),
                }
        seen[g.home] = g
        seen[g.away] = g


# ---------------------------------------------------------------------------
# Applicable rows (mirrors matrix_confluence.applicable_row_names)
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
    if ctx["rest_days"] is not None:
        if ctx["rest_days"] <= 6:
            rows.append("Short Rest (≤ 6 days)")
        elif ctx["rest_days"] >= 10:
            rows.append("Long Rest (≥ 10 days)")
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
            vs = _NRL_VENUE_STATE.get(g.venue, "LH")
            ts = _NRL_TEAM_STATE.get(team, "NSW")
            if vs == "LH" or (vs == "NZ" and ts != "NZ"):
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
# totals are not team-relative: a cell points at OVER or UNDER for the game.
TOTALS_SIDES = ("over", "under")


def score_game(g: Game, matrix: dict, market: str, min_edge: float,
               min_n: int, extended: bool) -> dict:
    """Return {'home': net, 'away': net, 'cells': {...}} for one market."""
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
    return {
        a: len(tally[a]) - len(tally[b]),
        b: len(tally[b]) - len(tally[a]),
        "cells": tally,
    }


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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", type=int, default=2026)
    ap.add_argument("--net", type=int, default=7)
    ap.add_argument("--min-edge", type=float, default=5.0)
    ap.add_argument("--min-n", type=int, default=0, help="minimum sample behind a cell")
    ap.add_argument("--extended", action="store_true",
                    help="also use road-trip and line-bucket rows (production ignores these)")
    ap.add_argument("--price", choices=["close", "open"], default="close")
    ap.add_argument("--totals-matrix", type=Path, default=None,
                    help="explicit totals matrix xlsx (overrides --totals-version)")
    ap.add_argument("--totals-version", choices=["v1", "v2"], default="v1",
                    help="v1 = mean total vs line; v2 = over hit rate vs 50%%")
    ap.add_argument("--markets", default="h2h,handicap",
                    help="comma list of h2h,handicap,totals")
    ap.add_argument("--csv", type=Path, default=None)
    args = ap.parse_args()

    wanted = [m.strip() for m in args.markets.split(",") if m.strip()]
    available = {"h2h": load_h2h_matrix(H2H_MATRIX) if "h2h" in wanted else {},
                 "handicap": load_handicap_matrix(HANDICAP_MATRIX) if "handicap" in wanted else {},
                 "totals": load_h2h_matrix(args.totals_matrix or (TOTALS_MATRIX_V2 if args.totals_version == "v2" else TOTALS_MATRIX))}
    markets = [(m, available[m]) for m in wanted]
    games = load_games(RESULTS_XLSX)
    attach_context(games)
    season = [g for g in games if g.gdate.year == args.season]

    bets = []
    for g in season:
        for market, matrix in markets:
            s = score_game(g, matrix, market, args.min_edge, args.min_n, args.extended)
            sides = TOTALS_SIDES if market == "totals" else ("home", "away")
            for side in sides:
                if s[side] < args.net:
                    continue
                if market == "totals":
                    team = side.upper()
                    opp = f"{g.home} v {g.away}"
                    if args.price == "close":
                        line = g.total_close
                        price = g.over_odds_close if side == "over" else g.under_odds_close
                    else:
                        line = g.total_open
                        price = g.over_odds_open if side == "over" else g.under_odds_open
                    result = settle_total(g, side, line)
                elif market == "h2h":
                    team = g.home if side == "home" else g.away
                    opp = g.away if side == "home" else g.home
                    price = (g.home_odds_close if side == "home" else g.away_odds_close) \
                        if args.price == "close" else \
                        (g.home_odds_open if side == "home" else g.away_odds_open)
                    result = settle_h2h(g, side)
                    line = None
                else:
                    team = g.home if side == "home" else g.away
                    opp = g.away if side == "home" else g.home
                    if args.price == "close":
                        line = g.home_line_close if side == "home" else g.away_line_close
                        price = g.home_line_odds_close if side == "home" else g.away_line_odds_close
                    else:
                        line = g.home_line_open if side == "home" else g.away_line_open
                        price = g.home_line_odds_open if side == "home" else g.away_line_odds_open
                    result = settle_line(g, side, line)
                if price is None or result == "novoid":
                    result = "no_price"
                    pnl = 0.0
                elif result == "win":
                    pnl = price - 1.0
                elif result == "push":
                    pnl = 0.0
                else:
                    pnl = -1.0
                bets.append({
                    "date": g.gdate.isoformat(), "market": market, "team": team,
                    "opponent": opp, "side": side, "venue": g.venue,
                    "net": s[side], "line": line, "price": price,
                    "other_side_cells": len(s["cells"][
                        ({"home": "away", "away": "home",
                          "over": "under", "under": "over"})[side]]),
                    "score": f"{g.home_score}-{g.away_score}",
                    "result": result, "pnl": round(pnl, 4),
                    "for_cells": len(s["cells"][side]),
                })

    def summarise(rows, label):
        priced = [b for b in rows if b["result"] != "no_price"]
        if not priced:
            print(f"{label:<12} no bets")
            return
        staked = sum(1 for b in priced if b["result"] != "push")
        wins = sum(1 for b in priced if b["result"] == "win")
        pushes = sum(1 for b in priced if b["result"] == "push")
        draws = sum(1 for b in priced if b["result"] == "draw")
        pnl = sum(b["pnl"] for b in priced)
        turnover = len(priced)
        roi = pnl / turnover * 100 if turnover else 0.0
        avg_price = sum(b["price"] for b in priced) / len(priced)
        strike = wins / staked * 100 if staked else 0.0
        print(f"{label:<12} bets {len(priced):>3}  W-L {wins}-{len(priced)-wins-pushes}"
              f"{f' (push {pushes})' if pushes else ''}"
              f"{f' [draws {draws}]' if draws else ''}"
              f"  strike {strike:5.1f}%  avg ${avg_price:.2f}"
              f"  P/L ${pnl:+.2f}  ROI {roi:+.2f}%")

    print(f"\nNRL {args.season} — matrix net +{args.net} rule, $1 flat, "
          f"{args.price} price, cells ≥{args.min_edge:g}% edge"
          f"{', totals ' + args.totals_version if 'totals' in wanted else ''}"
          f"{', extended rows' if args.extended else ''}"
          f"{f', min N={args.min_n}' if args.min_n else ''}")
    print(f"games in season: {len(season)}\n")
    for m in wanted:
        summarise([b for b in bets if b["market"] == m], m.upper())
    if len(wanted) > 1:
        summarise(bets, "COMBINED")

    if bets:
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
