#!/usr/bin/env python3
"""Audit actual 2026 AFL H2H bets against the frozen H2H matrix."""

from __future__ import annotations

import csv
import re
from collections import Counter
from pathlib import Path

import audit_afl_totals_matrix_staking as afl
import audit_nrl_matrix_staking as base

ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "outputs" / "afl_h2h_matrix.xlsx"
OUT_DIR = ROOT / "outputs" / "results"
THRESHOLDS = (10, 20, 30)


def selected_team(bet: base.Bet, game: dict) -> str | None:
    teams = [team for team in afl.teams_in(bet.market) if team in (game["home"], game["away"])]
    return teams[0] if len(teams) == 1 else None


def is_h2h_candidate(market: str) -> bool:
    low = market.lower()
    if any(word in low for word in ("over", "under", "total", "line", "handicap", "goal", "possession", "disposal", "trade", "multi", "either", "half")):
        return False
    return not bool(re.search(r"(?<![\w.])[+-]\d+(?:\.\d+)?", market))


def applicable_rows(game: dict, team: str, games: list[dict]) -> list[str]:
    dt = afl.datetime.fromisoformat(game["kickoff"].replace("Z", "+00:00"))
    hour = (dt.hour + (11 if dt.month in (1, 2, 3, 4, 10, 11, 12) else 10)) % 24
    rest, last = afl.form(games, game, team)
    opponent = game["away"] if team == game["home"] else game["home"]
    out = [
        "Win % — Home" if team == game["home"] else "Win % — Away",
        "Night Games (kick-off ≥ 18:00)" if hour >= 18 else "Day Games (kick-off < 18:00)",
    ]
    if dt.weekday() in (3, 4): out.append("Thursday / Friday Games")
    elif dt.weekday() == 5: out.append("Saturday Games")
    elif dt.weekday() == 6: out.append("Sunday Games")
    if rest is not None:
        if rest <= 6: out.append("Short Rest (≤ 6 days)")
        elif rest >= 10: out.append("Long Rest (≥ 10 days)")
    if last == "win": out.append("After a Win")
    elif last == "loss": out.append("After a Loss")
    month = {3:"March",4:"April",5:"May",6:"June",7:"July",8:"August",9:"September"}.get(dt.month)
    out += [month, afl.moon(dt.date()), f"vs {afl.MATRIX_KEY[opponent]}", game["venue"]]
    return [x for x in out if x]


def qualifies(record: dict, threshold: int) -> bool:
    return (sum(edge >= threshold for edge, *_ in record["support"]) >= 3
            and not any(edge >= threshold for edge, *_ in record["conflict"]))


def main() -> None:
    matrix, games = base.load_matrix_xlsx(MATRIX), afl.fixtures()
    records, exclusions = [], []
    for bet in afl.parse_bets():
        if not is_h2h_candidate(bet.market):
            continue
        game = afl.fixture_for(bet, games)
        if not game:
            exclusions.append((bet, "fixture not uniquely matched")); continue
        team = selected_team(bet, game)
        if not team:
            exclusions.append((bet, "backed club not explicit in ledger")); continue
        # A market explicitly marked live cannot be evaluated using a pre-match matrix.
        # The compact Bet dataclass intentionally does not retain ledger notes.
        if "live" in bet.market.lower():
            exclusions.append((bet, "live or traded bet")); continue
        support, conflict = [], []
        for row in applicable_rows(game, team, games):
            value = matrix.get(afl.MATRIX_KEY[team], {}).get(row)
            if not value: continue
            edge, direction = value
            (support if direction == "backing" else conflict).append((edge, row, team))
        records.append({"bet": bet, "team": team, "support": support, "conflict": conflict})

    ladders = {t: [r for r in records if qualifies(r, t)] for t in THRESHOLDS}
    actual = sum(base.pnl(r["bet"]) for r in records)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUT_DIR / "afl_2026_actual_h2h_matrix_staking_audit.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["id","date","match","market","team","odds","stake","result","support_10","support_20","support_30","conflict_10","conflict_20","conflict_30","support_rows","conflict_rows"])
        for r in records:
            b, s, c = r["bet"], r["support"], r["conflict"]
            w.writerow([b.ident,b.date,b.match,b.market,r["team"],b.odds,b.stake,b.result,
                        *[sum(x[0] >= t for x in s) for t in THRESHOLDS], *[sum(x[0] >= t for x in c) for t in THRESHOLDS],
                        "; ".join(f"{e:.1f}% {row}" for e,row,_ in s), "; ".join(f"{e:.1f}% {row}" for e,row,_ in c)])
    md_path = OUT_DIR / "afl_2026_actual_h2h_matrix_staking_audit.md"
    with md_path.open("w", encoding="utf-8") as fh:
        fh.write("# 2026 AFL actual H2H bets — matrix staking audit\n\n")
        fh.write("Source: BetMate's actual-bet ledger. Matrix: frozen 2022–25 AFL H2H matrix. A qualifier requires **3+ aligned signals** at the stated threshold and **no opposing signal** at that same threshold.\n\n")
        fh.write("| Rule | Qualifying bets | Wins–losses | P&L from those bets | P&L if doubled | Increment from doubling |\n|---|---:|---:|---:|---:|---:|\n")
        for t, rs in ladders.items():
            pnl = sum(base.pnl(r["bet"]) for r in rs); wl = Counter(r["bet"].result for r in rs)
            fh.write(f"| 3+ aligned {t}% signals; no opposing {t}% | {len(rs)} | {wl['win']}–{wl['loss']} | ${pnl:+.2f} | ${actual+pnl:+.2f} | ${pnl:+.2f} |\n")
        fh.write(f"\n- Eligible, pre-game 2026 H2H bets: **{len(records)}**; excluded/ambiguous: **{len(exclusions)}**.\n- Actual P&L across eligible bets: **${actual:+.2f}**.\n\n")
        for t, rs in ladders.items():
            fh.write(f"## {t}% qualifying bets\n\n| Date | Bet | Result | Stake | aligned signals |\n|---|---|---:|---:|---|\n")
            for r in rs:
                b = r["bet"]
                signals = ", ".join(f"{e:.0f}% {row}" for e,row,_ in sorted(r["support"], reverse=True) if e >= t)
                fh.write(f"| {b.date} | {b.market} — {b.match} | {b.result} | ${b.stake:.2f} | {signals} |\n")
            if not rs: fh.write("| — | No qualifying bets | — | — | — |\n")
            fh.write("\n")
        fh.write("## Interpretation\n\nThis is a small retrospective test of selected bets, not proof of a staking edge. Matrix rows overlap and are not independent. Do not change live staking from this alone; freeze a rule and assess it prospectively.\n")
    print(f"Eligible: {len(records)} | excluded: {len(exclusions)} | actual P&L: ${actual:+.2f}")
    for t, rs in ladders.items():
        inc = sum(base.pnl(r["bet"]) for r in rs)
        print(f"{t}%: {len(rs)} qualifiers | incremental doubled P&L ${inc:+.2f} | counterfactual ${actual+inc:+.2f}")
    print(f"Wrote {md_path}\nWrote {csv_path}")


if __name__ == "__main__":
    main()
