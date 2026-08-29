#!/usr/bin/env python3
"""Freeze injury-adjusted Championship Week 1 BTTS and 2.5-goal prices."""
from __future__ import annotations

import contextlib
import io
from datetime import datetime
from pathlib import Path

import pandas as pd

from ml.football.league_config import load_league
from ml.football.models.dixon_coles import build_scoreline_matrix
from ml.football.price_match import price_match


ROOT = Path(__file__).resolve().parents[2]
ODDS = ROOT.parent / "data" / "odds_snapshots" / "latest.csv"
OUT = ROOT / "outputs" / "football" / "championship" / "week 1 EFL goals.md"
AS_OF = datetime(2026, 8, 14)

TEAM_MAP = {
    "Wolverhampton Wanderers": "Wolves", "Blackburn Rovers": "Blackburn",
    "Bolton Wanderers": "Bolton", "Preston North End": "Preston",
    "Charlton Athletic": "Charlton", "Lincoln City": "Lincoln",
    "Norwich City": "Norwich", "West Bromwich Albion": "West Brom",
    "Queens Park Rangers": "QPR", "Stoke City": "Stoke",
    "Swansea City": "Swansea", "Sheffield United": "Sheffield United",
    "Birmingham City": "Birmingham", "West Ham United": "West Ham",
    "Cardiff City": "Cardiff", "Wrexham AFC": "Wrexham",
}

# Frozen pre-match availability assessment researched on 14-15 August 2026.
INJURIES = {
    "Blackburn": ["DM", "AM"],
    "Bristol City": ["CM", "CB", "CB", "AM"], "Millwall": ["GK"],
    "Middlesbrough": ["CM"], "Lincoln": ["ST", "CB"],
    "Norwich": ["ST", "CM", "CM", "AM"], "West Brom": ["ST"],
    "Portsmouth": ["CB", "CB", "CM"], "QPR": ["CB", "CB", "CB", "ST"],
    "Stoke": ["CM", "CB", "CB"],
    "Sheffield United": ["CB"], "Birmingham": ["CB", "CB", "CM"],
    "Watford": ["GK"], "Southampton": ["CB", "CB", "AM", "GK"],
    "Burnley": ["CM", "CB"], "West Ham": ["CM", "ST"],
    "Cardiff": ["CM"], "Wrexham": ["CM"],
}


def best(rows: pd.DataFrame, outcome: str) -> tuple[float, str]:
    found = rows[rows.outcome.eq(outcome)]
    if found.empty:
        return 0.0, ""
    row = found.loc[found.price.idxmax()]
    return float(row.price), str(row.bookmaker)


def pct(value: float) -> str:
    return f"{100 * value:.1f}%"


def odds(value: float) -> str:
    return f"{1 / value:.2f}"


def main() -> None:
    raw = pd.read_csv(ODDS)
    raw = raw[raw.sport.astype(str).str.upper().eq("CHAMPIONSHIP")].copy()
    snapshot_stamp = f"{raw['snapshot_date'].max()} {raw['snapshot_time'].max()} Australia/Sydney"
    raw["commence_time"] = pd.to_datetime(raw.commence_time, utc=True)
    # The latest feed drops a match after kickoff, so restore Wolves from the
    # frozen Week 1 1X2 work even if it is absent from the live snapshot.
    fixtures = [
        ("Wolves", "Blackburn", "2026-08-14T19:00:00Z"),
        ("Bolton", "Preston", "2026-08-15T11:30:00Z"),
        ("Bristol City", "Millwall", "2026-08-15T14:00:00Z"),
        ("Charlton", "Derby County", "2026-08-15T14:00:00Z"),
        ("Middlesbrough", "Lincoln", "2026-08-15T14:00:00Z"),
        ("Norwich", "West Brom", "2026-08-15T14:00:00Z"),
        ("Portsmouth", "QPR", "2026-08-15T14:00:00Z"),
        ("Stoke", "Swansea", "2026-08-15T14:00:00Z"),
        ("Sheffield United", "Birmingham", "2026-08-15T16:30:00Z"),
        ("Watford", "Southampton", "2026-08-16T12:30:00Z"),
        ("Burnley", "West Ham", "2026-08-16T15:00:00Z"),
        ("Cardiff", "Wrexham", "2026-08-17T19:00:00Z"),
    ]
    reverse = {v: k for k, v in TEAM_MAP.items()}
    rho = float(load_league("championship").model["rho"])
    results = []

    for home, away, kickoff in fixtures:
        market_rows = raw[
            raw.home_team.eq(reverse.get(home, home))
            & raw.away_team.eq(reverse.get(away, away))
            & raw.market.eq("totals")
            & raw.point.eq(2.5)
        ]
        market_over, book_over = best(market_rows, "Over")
        market_under, book_under = best(market_rows, "Under")
        with contextlib.redirect_stdout(io.StringIO()):
            priced = price_match(
                home, away, as_of=AS_OF, league="championship", matchweek=1,
                injuries_home=INJURIES.get(home, []),
                injuries_away=INJURIES.get(away, []),
                mkt_over25=market_over,
            )
        matrix = build_scoreline_matrix(
            priced["lambda_home"], priced["lambda_away"], rho=rho
        )
        p_btts = float(matrix[1:, 1:].sum())
        results.append({
            "kickoff": kickoff, "match": f"{home} v {away}",
            "over": priced["p_over25"], "under": priced["p_under25"],
            "btts": p_btts, "nbtts": 1 - p_btts,
            "market_over": market_over, "book_over": book_over,
            "market_under": market_under, "book_under": book_under,
        })

    lines = [
        "# Week 1 EFL goals",
        "",
        "Frozen pre-match Championship prices. Model timestamp: 2026-08-15 Australia/Sydney; information cutoff: 2026-08-14 pre-kickoff.",
        "",
        "| Match | O2.5 % | Fair O2.5 | U2.5 % | Fair U2.5 | BTTS % | Fair BTTS | No BTTS % | Fair No BTTS |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in results:
        lines.append(
            f"| {row['match']} | {pct(row['over'])} | {odds(row['over'])} | "
            f"{pct(row['under'])} | {odds(row['under'])} | {pct(row['btts'])} | "
            f"{odds(row['btts'])} | {pct(row['nbtts'])} | {odds(row['nbtts'])} |"
        )
    lines += [
        "", "## Reference market snapshot", "",
        f"Current best available Over/Under 2.5 prices were frozen from the BetMate feed at {snapshot_stamp}, where the match remained available. BTTS was not present in that feed and is model-only.",
        "",
        "| Match | Market O2.5 | Book | Market U2.5 | Book |",
        "|---|---:|---|---:|---|",
    ]
    for row in results:
        mo = f"{row['market_over']:.2f}" if row["market_over"] else "—"
        mu = f"{row['market_under']:.2f}" if row["market_under"] else "—"
        lines.append(f"| {row['match']} | {mo} | {row['book_over'] or '—'} | {mu} | {row['book_under'] or '—'} |")
    lines += [
        "", "## Audit notes", "",
        "- Uses the same frozen Week 1 injury inputs as the 1X2 sheet.",
        "- T2 pressing inactive (no Championship PPDA); T6 referee inactive (failed validation/unavailable appointments).",
        "- T3, T5, T7 and T8 applied wherever inputs were available. T9 was not forced without a qualifying verified trigger.",
        "- Over/Under 2.5 is the calibrated model output. BTTS is derived directly from the adjusted Dixon-Coles score matrix and is not separately calibrated.",
        "- Closing prices and actual results must be appended later without overwriting this frozen forecast.",
    ]
    report = "\n".join(lines) + "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(report, encoding="utf-8")
    print(report)
    print(f"Saved: {OUT}")


if __name__ == "__main__":
    main()
