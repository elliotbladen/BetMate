#!/usr/bin/env python3
"""Audit 2026 logged NRL totals bets against the totals matrix at 5%+ edges.

This is deliberately separate from the H2H/handicap audit. Both teams can
contribute totals signals, but overlapping rows are treated as a confidence
screen only—not independent predictive evidence.
"""

from __future__ import annotations

import csv
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

import ephem

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import audit_nrl_matrix_staking as base  # noqa: E402

TOTALS_MATRIX = ROOT / "outputs" / "nrl_team_totals_matrix.xlsx"
OUT_DIR = ROOT / "outputs" / "results"
MIN_EDGE = 5.0


def moon_row(day) -> str | None:
    probe = ephem.Date(day.strftime("%Y/%m/%d 12:00:00"))
    distances = {
        "New Moon (±1 day)": min(abs(float(probe) - float(ephem.previous_new_moon(probe))), abs(float(ephem.next_new_moon(probe)) - float(probe))),
        "Full Moon (±1 day)": min(abs(float(probe) - float(ephem.previous_full_moon(probe))), abs(float(ephem.next_full_moon(probe)) - float(probe))),
    }
    label, distance = min(distances.items(), key=lambda item: item[1])
    return label if distance <= 1 else None


def rows_for_team(game: dict, team: str, fixtures: list[dict]) -> list[str]:
    dt = datetime.fromisoformat(game["kickoff"].replace("Z", "+00:00"))
    local_hour = (dt.hour + 10 + (1 if dt.month in (1, 2, 3, 4, 10, 11, 12) else 0)) % 24
    rest, form = base.form_context(fixtures, game, team)
    rows = ["Total Points — Home" if team == game["home"] else "Total Points — Away"]
    rows.append("Night Games (kick-off ≥ 18:00)" if local_hour >= 18 else "Day Games (kick-off < 18:00)")
    if dt.weekday() in (3, 4): rows.append("Thursday / Friday Games")
    elif dt.weekday() == 5: rows.append("Saturday Games")
    elif dt.weekday() == 6: rows.append("Sunday Games")
    if rest is not None:
        if rest <= 6: rows.append("Short Rest (≤ 6 days)")
        elif rest >= 10: rows.append("Long Rest (≥ 10 days)")
    if form == "win": rows.append("After a Win")
    elif form == "loss": rows.append("After a Loss")
    rows += [base.MONTHS.get(dt.month, ""), moon_row(dt.date()) or "", f"vs {game['away'] if team == game['home'] else game['home']}", game["venue"]]
    return [row for row in rows if row]


def side(market: str) -> str | None:
    low = market.lower()
    if "under" in low: return "unders"
    if "over" in low: return "overs"
    return None


def main() -> None:
    matrix = base.load_matrix_xlsx(TOTALS_MATRIX)
    fixtures, bets = base.load_fixtures(), base.parse_ledger(base.LEDGER)
    records, excluded = [], []
    for bet in bets:
        wanted = side(bet.market)
        if not wanted:
            continue  # this audit intentionally considers totals only
        game = base.fixture_for_bet(bet, fixtures)
        if not game:
            excluded.append((bet, "fixture not uniquely matched")); continue
        support, conflict = [], []
        for team in (game["home"], game["away"]):
            for category in rows_for_team(game, team, fixtures):
                value = matrix.get(team, {}).get(category)
                if not value: continue
                edge, direction = value
                (support if direction.startswith(wanted) else conflict).append((edge, category, team, direction))
        records.append({"bet": bet, "game": game, "wanted": wanted, "support": support, "conflict": conflict})

    # Requested 5% matrix-confluence setting. To be a stake-increase candidate
    # a bet must have three aligned 5% signals and zero opposing 5% signal.
    for record in records:
        record["qualifies_double"] = sum(edge >= MIN_EDGE for edge, *_ in record["support"]) >= 3 and not any(edge >= MIN_EDGE for edge, *_ in record["conflict"])

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUT_DIR / "nrl_2026_actual_totals_matrix_staking_audit.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["id", "date", "match", "market", "odds", "stake", "result", "support_5", "support_10", "support_20", "support_30", "support_40", "conflict_5", "qualifies_double", "support_rows", "conflict_rows"])
        for r in records:
            b, support, conflict = r["bet"], r["support"], r["conflict"]
            writer.writerow([b.ident, b.date, b.match, b.market, b.odds, b.stake, b.result,
                             *[sum(edge >= threshold for edge, *_ in support) for threshold in (5, 10, 20, 30, 40)],
                             sum(edge >= 5 for edge, *_ in conflict), r["qualifies_double"],
                             "; ".join(f"{edge:.1f}% {team} {row}" for edge, row, team, _ in support),
                             "; ".join(f"{edge:.1f}% {team} {row}" for edge, row, team, _ in conflict)])

    actual = sum(base.pnl(r["bet"]) for r in records)
    qualifying = [r for r in records if r["qualifies_double"]]
    counterfactual = actual + sum(base.pnl(r["bet"]) for r in qualifying)
    threshold_rules = {
        threshold: [r for r in records if sum(edge >= threshold for edge, *_ in r["support"]) >= 3 and not any(edge >= threshold for edge, *_ in r["conflict"])]
        for threshold in (5, 10, 20, 30, 40)
    }
    md_path = OUT_DIR / "nrl_2026_actual_totals_matrix_staking_audit.md"
    with md_path.open("w", encoding="utf-8") as fh:
        fh.write("# 2026 NRL actual totals bets — matrix staking audit\n\n")
        fh.write("## Scope and frozen rule\n\n")
        fh.write("This covers only logged 2026 NRL over/under bets. The totals matrix is the frozen 2022–25 version; 2026 results were not used to create its rows. The confluence threshold is **5%**, as requested. Both teams' applicable totals rows are examined.\n\n")
        fh.write("| Confluence rule | Bets | Wins–losses | Increment if doubled |\n|---|---:|---:|---:|\n")
        for threshold, rows in threshold_rules.items():
            outcomes = Counter(r["bet"].result for r in rows)
            increment = sum(base.pnl(r["bet"]) for r in rows)
            fh.write(f"| 3+ aligned {threshold}% signals; no opposing {threshold}% signal | {len(rows)} | {outcomes['win']}–{outcomes['loss']} | ${increment:+.2f} |\n")
        fh.write("\n## 5% double-stake test\n\n")
        fh.write("Predefined rule: **3+ aligned 5%+ signals and no opposing 5%+ signal**.\n\n")
        fh.write(f"- Eligible totals bets: **{len(records)}**; unmatched: **{len(excluded)}**.\n")
        fh.write(f"- Actual P&L: **${actual:+.2f}**.\n")
        fh.write(f"- Qualifying double-stake bets: **{len(qualifying)}**.\n")
        fh.write(f"- Counterfactual P&L: **${counterfactual:+.2f}**.\n")
        fh.write(f"- Change from doubling: **${counterfactual - actual:+.2f}**.\n\n")
        fh.write("## Qualifying bets\n\n| Date | Bet | Result | Stake | Supporting signals ≥5% |\n|---|---|---:|---:|---|\n")
        for r in qualifying:
            b = r["bet"]
            signals = ", ".join(f"{edge:.0f}% {row}" for edge, row, _, _ in sorted(r["support"], reverse=True) if edge >= 5)
            fh.write(f"| {b.date} | {b.market} — {b.match} | {b.result} | ${b.stake:.2f} | {signals} |\n")
        fh.write("\n## Interpretation\n\n")
        fh.write("At a 5% threshold, small historical deviations are intentionally admitted as context flags, not as proof of an edge. The rows overlap substantially (month, day, venue and opponent can describe the same games), so this is a useful stake-filter test but not a Kelly input by itself. Freeze any chosen rule and test it prospectively before changing stake sizes.\n")
    print(f"Eligible totals: {len(records)} | unmatched: {len(excluded)} | 5% qualifiers: {len(qualifying)}")
    print(f"Actual P&L: ${actual:+.2f} | counterfactual: ${counterfactual:+.2f} | change: ${counterfactual - actual:+.2f}")
    print(f"Wrote {md_path}\nWrote {csv_path}")


if __name__ == "__main__":
    main()
