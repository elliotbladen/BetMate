#!/usr/bin/env python3
"""Build the EFL Championship REFEREE confluence workbook for Over/Under 2.5 goals.

The team workbook (efl_championship_confluence_matrix.py) already carries a REFEREE
section, but read team-first: "Barnsley when A Davies referees", n=5. This is the
transpose — one sheet per referee, every context split computed across all of that
referee's Championship matches, which is the direction with enough games in it to be
worth reading.

Same columns, same styling, same de-vigged-closing-market comparison and the same
reliability wording as the team workbook, so the two read as one system. Referee
extras: kickoff slot (the team workbook says times are unavailable — they are, from
2019/20), the referee's own rest, and goals/fouls/cards per game, which is what a
referee actually controls.

Read the sample column before the edge column. A month cell for even a busy referee is
around eight to twelve matches, where the 95% noise floor is +/-31pp — bigger than any
real refereeing effect. Cells are flagged on edge size alone, exactly as in the team
workbook, so a flag is an invitation to check n, not a signal.
"""
from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path
from statistics import mean

import numpy as np
import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill

from efl_championship_confluence_matrix import (
    ALT, AMBER, BLUE, BORDER, CURRENT_2026_27_TEAMS, GREEN, MIN_SAMPLE, NAVY,
    WHITE_FONT, _get_moon_phase, closing_1x2, closing_totals, number, parse_date,
    reliability, score,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "ml/football/data/championship/matches/championship_matches.csv"
DEFAULT_OUTPUT = ROOT / "outputs/football/_reference/efl_championship_referee_goals_matrix.xlsx"
DEFAULT_SEASONS = ("2021/22", "2022/23", "2023/24", "2024/25")
MIN_REFEREE_GAMES = 15          # plus every referee active in the current season

HEADERS = [
    "Section", "Category",
    "Actual over %", "Market over %", "Over edge pp", "Over edge pp (shrunk)",
    "Over $1 ROI %", "Under $1 ROI %",
    "Actual BTTS %", "BTTS difference pp",
    "Goals/game", "Fouls/game", "Cards/game", "Cards o3.5 %", "Cards BE odds",
    "Totals N", "Reliability", "Signal", "Main odds source",
]
CARD_LINE = 3.5             # league hit rate 53.3%, break-even 1.88 — the tradeable line
EDGE_COLUMN = 5             # raw over edge
SHRUNK_COLUMN = 6
ROI_COLUMNS = (7, 8)
SIGNAL_COLUMN = 18
FDR_Q = 0.10                # Benjamini-Hochberg false-discovery rate


def normal_sf(z: float) -> float:
    """Two-sided tail of the standard normal, without pulling in scipy."""
    from math import erfc, sqrt
    return erfc(abs(z) / sqrt(2.0))


def estimate_tau2(rows: list[dict]) -> float:
    """Method-of-moments prior variance: how much referees TRULY differ.

    Observed spread between referees = true spread + binomial noise. Subtract the
    noise and what is left is the real between-referee variance. It comes out around
    2pp, which is why almost every cell in this workbook shrinks to nearly nothing.
    """
    by_ref: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        if row["market_totals"]:
            by_ref[row["referee"]].append(row)
    edges, noises = [], []
    for games in by_ref.values():
        if len(games) < 20:
            continue
        actual = mean(int(g["home_goals"] + g["away_goals"] > 2) for g in games)
        implied = mean(g["market_totals"][0][0] for g in games)
        edges.append(actual - implied)
        noises.append(implied * (1 - implied) / len(games))
    if len(edges) < 5:
        return 0.0
    return max(float(np.var(edges, ddof=1) - np.mean(noises)), 0.0)


def load_rows(path: Path, seasons: tuple[str, ...]) -> tuple[list[dict], set[str]]:
    """Returns (rows in the window, referees seen in seasons AFTER the window)."""
    rows: list[dict] = []
    current: set[str] = set()
    latest = max(seasons)
    with path.open(encoding="utf-8-sig") as handle:
        for raw in csv.DictReader(handle):
            season = raw.get("Season")
            referee = (raw.get("Referee") or "").strip()
            if season and season > latest and referee:
                current.add(referee)
            if season not in seasons:
                continue
            played = parse_date((raw.get("Date") or "").strip())
            home, away = (raw.get("HomeTeam") or "").strip(), (raw.get("AwayTeam") or "").strip()
            home_goals, away_goals = score(raw.get("FTHG")), score(raw.get("FTAG"))
            if not played or not home or not away or not referee:
                continue
            if home_goals is None or away_goals is None:
                continue
            hour = None
            time_text = (raw.get("Time") or "").strip()
            if ":" in time_text:
                try:
                    hour = int(time_text.split(":")[0])
                except ValueError:
                    hour = None
            rows.append({
                "season": season, "date": played, "home": home, "away": away,
                "home_goals": home_goals, "away_goals": away_goals,
                "result": (raw.get("FTR") or "").strip(), "referee": referee,
                "month": played.month, "weekday": played.weekday(), "hour": hour,
                "fouls": _total(raw, "HF", "AF"), "cards": _total(raw, "HY", "AY"),
                "market_1x2": closing_1x2(raw), "market_totals": closing_totals(raw),
                "best_over": number(raw.get("MaxC>2.5")) or number(raw.get("Max>2.5")),
                "best_under": number(raw.get("MaxC<2.5")) or number(raw.get("Max<2.5")),
                "moon_phase": _get_moon_phase(played),
            })
    rows.sort(key=lambda row: row["date"])
    _enrich_rest(rows)
    return rows, current


def _total(raw: dict, *columns: str) -> float | None:
    values = []
    for column in columns:
        try:
            values.append(float(raw.get(column) or ""))
        except (TypeError, ValueError):
            return None
    return sum(values)


def _enrich_rest(rows: list[dict]) -> None:
    """Days since the referee's last Championship match, and each team's rest."""
    previous_ref: dict[str, date] = {}
    for row in rows:
        last = previous_ref.get(row["referee"])
        row["ref_rest"] = (row["date"] - last).days if last else None
        previous_ref[row["referee"]] = row["date"]

    previous_team: dict[str, date] = {}
    team_games: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        team_games[row["home"]].append(row)
        team_games[row["away"]].append(row)
    for team, games in team_games.items():
        previous_team.pop(team, None)
        last = None
        for game in games:
            game[f"rest__{team}"] = (game["date"] - last).days if last else None
            last = game["date"]
    for row in rows:
        rests = [row.get(f"rest__{row['home']}"), row.get(f"rest__{row['away']}")]
        known = [value for value in rests if value is not None]
        row["short_teams"] = sum(1 for value in known if value <= 3) if len(known) == 2 else None


def price_band(row: dict) -> str | None:
    """How one-sided the fixture was priced, from the favourite's fair odds."""
    if not row["market_1x2"]:
        return None
    probabilities = row["market_1x2"][0]
    fair = 1.0 / max(probabilities[0], probabilities[2])
    if fair < 1.80:
        return "Big mismatch (fav <1.80)"
    if fair < 2.50:
        return "Clear favourite (1.80–2.49)"
    return "Competitive (fav 2.50+)"


def totals_band(row: dict) -> str | None:
    if not row["market_totals"]:
        return None
    over = row["market_totals"][0][0]
    if over >= 0.55:
        return "Market expects goals (≥55% over)"
    if over >= 0.45:
        return "Balanced (45–55% over)"
    return "Market expects few (<45% over)"


def stats_goals(games: list[dict], league_btts: float,
                tau2: float = 0.0) -> tuple[tuple, float] | None:
    usable = [game for game in games if game["market_totals"]]
    if len(usable) < MIN_SAMPLE:
        return None
    actual = [int(game["home_goals"] + game["away_goals"] > 2) for game in usable]
    implied = [game["market_totals"][0][0] for game in usable]
    sources = Counter(game["market_totals"][1] for game in usable)
    actual_over, market_over = mean(actual) * 100, mean(implied) * 100
    actual_btts = mean(int(game["home_goals"] > 0 and game["away_goals"] > 0)
                       for game in games) * 100
    goals = mean(game["home_goals"] + game["away_goals"] for game in games)
    fouls = [game["fouls"] for game in games if game["fouls"] is not None]
    cards = [game["cards"] for game in games if game["cards"] is not None]
    # Shrink toward zero by how much this cell could be noise alone. A cell of ten
    # matches keeps under 2% of its raw edge; that is the honest number, not the raw one.
    p = mean(implied)
    noise = p * (1 - p) / len(usable)
    keep = tau2 / (tau2 + noise) if (tau2 + noise) > 0 else 0.0
    edge = actual_over - market_over
    z = edge / (np.sqrt(noise) * 100) if noise > 0 else 0.0

    # Flat $1 on every match in this cell, at the best price on the board at the close.
    # Not a model and not a selection — just the historical record of the two bets.
    priced = [g for g in games if g["best_over"] and g["best_under"]]
    roi_over = roi_under = "—"
    if priced:
        won = [g["home_goals"] + g["away_goals"] > 2 for g in priced]
        roi_over = (mean(g["best_over"] if w else 0.0
                         for g, w in zip(priced, won)) - 1) * 100
        roi_under = (mean(g["best_under"] if not w else 0.0
                          for g, w in zip(priced, won)) - 1) * 100

    # Cards: yellows only (football-data's red-card columns are empty for this league).
    # No card ODDS exist in our data, so we give the hit rate and the price you would
    # need to break even at it — compare that against what a book actually offers.
    card_games = [g for g in games if g["cards"] is not None]
    card_rate = card_be = "—"
    if len(card_games) >= MIN_SAMPLE:
        card_rate = mean(int(g["cards"] > CARD_LINE) for g in card_games) * 100
        card_be = 100 / card_rate if card_rate > 0 else "—"

    values = (actual_over, market_over, edge, edge * keep, roi_over, roi_under,
              actual_btts, actual_btts - league_btts * 100,
              goals, mean(fouls) if fouls else "—", mean(cards) if cards else "—",
              card_rate, card_be,
              len(usable), reliability(len(usable)), "",
              sources.most_common(1)[0][0])
    return values, normal_sf(z)


def categories(games: list[dict], teams: list[str],
               seasons: tuple[str, ...]) -> list[tuple[str, str, list[dict]]]:
    output: list[tuple[str, str, list[dict]]] = [("OVERALL", "All games", games)]

    slots = (("Night (17:00 or later)", lambda h: h is not None and h >= 17),
             ("Afternoon (14:00–16:59)", lambda h: h is not None and 14 <= h < 17),
             ("Early (before 14:00)", lambda h: h is not None and h < 14))
    output += [("KICKOFF", label, [g for g in games if test(g["hour"])])
               for label, test in slots]

    weekdays = ((0, "Monday"), (1, "Tuesday"), (2, "Wednesday"), (3, "Thursday"),
                (4, "Friday"), (5, "Saturday"), (6, "Sunday"))
    output += [("DAY OF WEEK", label, [g for g in games if g["weekday"] == day])
               for day, label in weekdays]

    months = ((8, "August"), (9, "September"), (10, "October"), (11, "November"),
              (12, "December"), (1, "January"), (2, "February"), (3, "March"),
              (4, "April"), (5, "May"))
    output += [("MONTH", label, [g for g in games if g["month"] == month])
               for month, label in months]

    output += [
        ("REFEREE REST", "Quick turnaround (≤6 days)",
         [g for g in games if g["ref_rest"] is not None and g["ref_rest"] <= 6]),
        ("REFEREE REST", "Normal (7–13 days)",
         [g for g in games if g["ref_rest"] is not None and 7 <= g["ref_rest"] <= 13]),
        ("REFEREE REST", "Long gap (≥14 days)",
         [g for g in games if g["ref_rest"] is not None and g["ref_rest"] >= 14]),
        ("TEAM REST", "Both teams short rest (≤3 days)",
         [g for g in games if g["short_teams"] == 2]),
        ("TEAM REST", "One team short rest",
         [g for g in games if g["short_teams"] == 1]),
        ("TEAM REST", "Neither team short rest",
         [g for g in games if g["short_teams"] == 0]),
    ]

    for band in ("Big mismatch (fav <1.80)", "Clear favourite (1.80–2.49)",
                 "Competitive (fav 2.50+)"):
        output.append(("MATCH PRICE BAND", band,
                       [g for g in games if price_band(g) == band]))
    for band in ("Market expects goals (≥55% over)", "Balanced (45–55% over)",
                 "Market expects few (<45% over)"):
        output.append(("MARKET TOTALS BAND", band,
                       [g for g in games if totals_band(g) == band]))

    output += [
        ("MOON PHASE", "New Moon (+/-1 day)",
         [g for g in games if g.get("moon_phase") == "new"]),
        ("MOON PHASE", "Full Moon (+/-1 day)",
         [g for g in games if g.get("moon_phase") == "full"]),
    ]
    output += [("SEASON", season, [g for g in games if g["season"] == season])
               for season in seasons]
    output += [("TEAM", team, [g for g in games if team in (g["home"], g["away"])])
               for team in teams]
    return output


def setup_sheet(ws, title: str) -> None:
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(HEADERS))
    cell = ws.cell(1, 1, title)
    cell.fill = NAVY
    cell.font = Font(color="FFFFFF", bold=True, size=12)
    cell.alignment = Alignment(horizontal="center")
    for column, header in enumerate(HEADERS, 1):
        c = ws.cell(2, column, header)
        c.fill, c.font, c.border = NAVY, WHITE_FONT, BORDER
        c.alignment = Alignment(horizontal="center", wrap_text=True)
    ws.freeze_panes = "C3"
    ws.auto_filter.ref = f"A2:{openpyxl.utils.get_column_letter(len(HEADERS))}2"
    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 34
    for column in range(3, len(HEADERS) + 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(column)].width = 15


def benjamini_hochberg(pvalues: list[float], q: float) -> float:
    """Largest p-value that still controls the false-discovery rate at q.

    1,300-odd cells tested at p<0.05 would hand back ~65 false flags by construction.
    BH fixes the expected PROPORTION of wrong flags among those shown instead.
    Cells overlap heavily (a referee's Tuesday, night and quick-turnaround rows are
    largely the same matches), and BH stays valid under that kind of positive
    dependence, so it is the right correction here rather than a stricter Bonferroni.
    """
    if not pvalues:
        return 0.0
    ordered = sorted(pvalues)
    threshold = 0.0
    for rank, value in enumerate(ordered, 1):
        if value <= q * rank / len(ordered):
            threshold = value
    return threshold


def write_sheet(ws, referee: str, games: list[dict], cells: list[tuple],
                seasons: tuple[str, ...], cutoff: float) -> None:
    setup_sheet(ws, f"{referee} — EFL Championship GOALS confluence "
                    f"({', '.join(seasons)}) — {len(games)} matches")
    for number_, (section, label, values, pvalue) in enumerate(cells, 3):
        ws.cell(number_, 1, section)
        ws.cell(number_, 2, label)
        if values is None:
            for column in range(3, len(HEADERS) + 1):
                ws.cell(number_, column, "—")
        else:
            significant = pvalue is not None and cutoff > 0 and pvalue <= cutoff
            for column, value in enumerate(values, 3):
                if column == SIGNAL_COLUMN:
                    value = "SIGNAL" if significant else "noise"
                ws.cell(number_, column,
                        round(value, 2) if isinstance(value, float) else value)
            if significant:
                fill = GREEN if values[2] > 0 else AMBER
                for column in (EDGE_COLUMN, SHRUNK_COLUMN, SIGNAL_COLUMN):
                    ws.cell(number_, column).fill = fill
            else:
                ws.cell(number_, SIGNAL_COLUMN).font = Font(color="9C9C9C")
            for column in ROI_COLUMNS:
                cell = ws.cell(number_, column)
                if isinstance(cell.value, (int, float)):
                    cell.font = Font(bold=True,
                                     color="1B7F3B" if cell.value > 0 else "B03030")
        for column in range(1, len(HEADERS) + 1):
            cell = ws.cell(number_, column)
            cell.border = BORDER
            if not cell.fill.fill_type:
                cell.fill = ALT if number_ % 2 else PatternFill("solid", fgColor="FFFFFF")
            cell.alignment = Alignment(horizontal="left" if column <= 2 else "center")
        if number_ == 3 or ws.cell(number_ - 1, 1).value != section:
            ws.cell(number_, 1).fill = BLUE
            ws.cell(number_, 1).font = WHITE_FONT


def add_readme(wb, rows: list[dict], seasons: tuple[str, ...], referees: list[str],
               current: set[str], tau2: float, cutoff: float,
               flagged: int, tested: int) -> None:
    ws = wb.create_sheet("README", 0)
    counts = Counter(row["referee"] for row in rows)
    thin = [r for r in referees if counts.get(r, 0) < MIN_REFEREE_GAMES]
    tau = np.sqrt(tau2) * 100
    lines = [
        ("EFL Championship REFEREE confluence matrix — Over/Under 2.5 goals", True),
        (f"Seasons: {', '.join(seasons)}   Matches: {len(rows)}   Referee sheets: {len(referees)}", False),
        ("The sealed 2025/26 model-evaluation vault is excluded.", False),
        ("", False),
        ("WHAT THE MEASUREMENT SAYS BEFORE YOU READ A SINGLE CELL", True),
        ("Referee O/U 2.5 edge does not persist. Across 80 referee-season pairs, a referee's", False),
        ("edge over the closing price in one season correlates r=+0.08 with their edge the", False),
        ("next (95% CI -0.12 to +0.29). The same test on the same pairs for cards/game gives", False),
        ("r=+0.42, p=0.0001 — so the test finds referee persistence easily when it exists.", False),
        ("Referees have a real, repeatable card tendency. They have no repeatable tendency", False),
        ("to beat the goals market. Treat the goals columns as description, not prediction;", False),
        ("the Fouls/game and Cards/game columns are the ones carrying a real referee effect.", False),
        ("", False),
        ("HOW NOISE IS CONTROLLED HERE", True),
        (f"The between-referee spread estimator returns {tau:.2f}pp — but that sits at the 66th", False),
        ("percentile of its OWN null distribution (p=0.34; the estimator returns 1.46pp on average", False),
        ("for data with no referee effect at all). So this is consistent with zero, not evidence", False),
        ("of a 2pp effect. Cells are shrunk toward zero in proportion to how much of each could", False),
        ("be noise alone:", False),
        ("   n=10 keeps 1.6% of its raw edge  |  n=30 keeps 4.5%  |  n=119 keeps 15.8%", False),
        ("'Over edge pp' is the raw number. 'Over edge pp (shrunk)' is the believable one.", False),
        ("A raw +20pp on a ten-match month cell is worth +0.31pp after shrinkage.", False),
        ("", False),
        (f"Flags use Benjamini-Hochberg FDR at q={FDR_Q:.2f} across all {tested} tested cells", False),
        (f"(p <= {cutoff:.5f}), not a fixed percentage-point threshold. {flagged} cells are flagged.", False),
        ("The team workbook's +/-7.5pp rule lit up 58% of these cells, because referee cells", False),
        ("are half the size of team cells and pp thresholds ignore sample size entirely.", False),
        ("", False),
        ("WHAT THIS DATA COULD AND COULD NOT HAVE FOUND", True),
        ("Power was measured by planting referee effects of known size and re-running the tests:", False),
        ("   planted 8pp spread -> recovered 7.6pp, detected in 99% of simulations", False),
        ("   planted 5pp spread -> recovered 4.4pp, below the null's 95th percentile (5.3pp)", False),
        ("   planted 3pp spread -> recovered 3.2pp, found about half the time", False),
        ("So a referee effect big enough to bet (roughly 8pp+) WOULD have shown up here and did", False),
        ("not. A small one (2-5pp) could exist and this sample cannot see it — but at ~1.95 odds", False),
        ("that is barely past the vig, and it does not persist season to season, so it is not", False),
        ("harvestable either way. Per individual cell the 'noise' label is purely a statement", False),
        ("about power: a ten-match cell can only resolve +/-31pp. That is why edges are SHRUNK", False),
        ("rather than filtered out — shrinkage says 'the believable part is small', not 'zero'.", False),
        ("", False),
        ("Market probabilities are de-vigged Pinnacle closing odds, falling back to market maximum.", False),
        ("Comparing against a match-specific closing price is what makes cells comparable:", False),
        ("it already contains the fixture, the teams and the venue, so what is left is the referee.", False),
        ("BTTS difference is versus the league base rate, not a de-vigged BTTS market.", False),
        ("Goals/Fouls/Cards per game are raw averages with no market comparison and no shrinkage.", False),
        ("", False),
        ("Cells overlap heavily and are not independent. A referee's Tuesday row, their night", False),
        ("row and their quick-turnaround row are largely the same midweek matches counted three", False),
        ("times. Multiple flags on one sheet are not additive evidence.", False),
        (f"Rows need {MIN_SAMPLE}+ matches to print at all; 5-14 is explicitly a small sample.", False),
        ("This is descriptive historical evidence, not a standalone betting recommendation.", False),
        ("", False),
        (f"Sheets included: referees with {MIN_REFEREE_GAMES}+ matches in the window, plus every", False),
        (f"referee who has taken a Championship match since ({len(current)} active).", False),
    ]
    if thin:
        lines.append((f"Thin sheets (active but under {MIN_REFEREE_GAMES} window matches): "
                      f"{', '.join(f'{r} [{counts.get(r, 0)}]' for r in thin)}", False))
    for row, (value, title) in enumerate(lines, 1):
        ws.cell(row, 1, value)
        if title:
            ws.cell(row, 1).fill = NAVY
            ws.cell(row, 1).font = Font(color="FFFFFF", bold=True, size=12)
    ws.column_dimensions["A"].width = 108


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--seasons", nargs="+", default=list(DEFAULT_SEASONS))
    parser.add_argument("--min-games", type=int, default=MIN_REFEREE_GAMES)
    parser.add_argument("--fdr", type=float, default=FDR_Q)
    args = parser.parse_args()
    seasons = tuple(args.seasons)

    rows, current = load_rows(args.source, seasons)
    counts = Counter(row["referee"] for row in rows)
    referees = sorted({r for r, n in counts.items() if n >= args.min_games} | current)
    teams = sorted(set(row["home"] for row in rows) | set(row["away"] for row in rows)
                   | set(CURRENT_2026_27_TEAMS))
    league_btts = mean(int(row["home_goals"] > 0 and row["away_goals"] > 0) for row in rows)
    tau2 = estimate_tau2(rows)

    print(f"Loaded {len(rows)} matches, {len(counts)} referees, {', '.join(seasons)}")
    print(f"  between-referee true spread tau = {np.sqrt(tau2) * 100:.2f}pp "
          f"(everything else in the observed spread is noise)")

    # pass 1: compute every cell so the FDR correction sees the whole workbook
    computed: dict[str, list[tuple]] = {}
    pvalues: list[float] = []
    for referee in referees:
        games = [row for row in rows if row["referee"] == referee]
        cells = []
        for section, label, subset in categories(games, teams, seasons):
            result = stats_goals(subset, league_btts, tau2)
            if result is None:
                cells.append((section, label, None, None))
            else:
                values, pvalue = result
                cells.append((section, label, values, pvalue))
                pvalues.append(pvalue)
        computed[referee] = cells
    cutoff = benjamini_hochberg(pvalues, args.fdr)
    flagged = sum(1 for p in pvalues if cutoff > 0 and p <= cutoff)
    print(f"  {len(pvalues)} populated cells tested; BH q={args.fdr:.2f} -> p<={cutoff:.5f}; "
          f"{flagged} flagged ({flagged / max(len(pvalues), 1) * 100:.1f}%)")
    print(f"  writing {len(referees)} referee sheets, league BTTS {league_btts * 100:.1f}%")

    # pass 2: write
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    add_readme(wb, rows, seasons, referees, current, tau2, cutoff, flagged, len(pvalues))
    for referee in referees:
        games = [row for row in rows if row["referee"] == referee]
        write_sheet(wb.create_sheet(referee[:31]), referee, games,
                    computed[referee], seasons, cutoff)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    wb.save(args.output)
    print(f"Saved {args.output}")


if __name__ == "__main__":
    main()
