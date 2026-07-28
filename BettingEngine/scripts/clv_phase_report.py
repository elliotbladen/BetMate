"""
clv_phase_report.py
-------------------
Per-phase CLV report on ACTUAL BETS ONLY (excludes the model-CLV supplement
rows that inflate the running file's early-season numbers — R8/R9 NRL are
game-level model CLV with no bets placed).

Splits NRL bets by:
  - season phase (scripts/season_phases.py — event-anchored)
  - Origin camp/backup window vs clean Origin-era week
  - bet timing vs team-list release (Tue 16:00 of game week; NRL rounds
    start Thursday, so cut = round_start - 2 days)

Bets missing placed_date in the ledger are reported but excluded from the
timing split. Fill placed_date in data/bets/actual_bets_2026.csv to include
them (as of 2026-07-10 the R13 bets — the worst CLV round — have no
placed_date, so the timing hypothesis can't be tested on them).

Usage:
  python scripts/clv_phase_report.py [--season 2026]
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

from season_phases import nrl_round_dates, phase_for_round

ROOT = Path(__file__).resolve().parent.parent

TEAMLIST_TIME = "16:00"  # NRL team lists drop Tuesday ~4pm AEST


def load_rows(season: int) -> tuple[list[tuple], list[str]]:
    clv = {}
    clv_file = ROOT / f"data/clv/running/actual_bets_clv_{season}.csv"
    with open(clv_file, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if r.get("clv_pct", "").strip() not in ("", "None"):
                clv[r["bet_id"]] = float(r["clv_pct"])

    dates = nrl_round_dates(season)
    rows, missing = [], []
    bets_file = ROOT / f"data/bets/actual_bets_{season}.csv"
    with open(bets_file, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if r["sport"].upper() != "NRL" or r["bet_id"] not in clv:
                continue
            rnd = int(r["round"])
            if rnd not in dates:
                continue
            phase, window = phase_for_round("NRL", season, rnd)
            if not r["placed_date"].strip():
                missing.append(f"{r['bet_id']} (R{rnd}, {phase})")
                timing = "unknown-timing"
            else:
                round_start = date.fromisoformat(dates[rnd][0])
                cut = round_start - timedelta(days=2)
                placed = date.fromisoformat(r["placed_date"])
                pt = (r["placed_time"] or "00:00").strip()
                pre = placed < cut or (placed == cut and pt < TEAMLIST_TIME)
                timing = "pre-teamlist" if pre else "post-teamlist"
            rows.append((phase, window, timing, clv[r["bet_id"]], rnd))
    return rows, missing


def summarize(rows: list[tuple], keyfn, label: str) -> None:
    groups = defaultdict(list)
    for row in rows:
        groups[keyfn(row)].append(row[3])
    print(f"\n{label}")
    for k in sorted(groups, key=str):
        v = groups[k]
        pos = sum(1 for x in v if x > 0)
        print(f"  {str(k):42} n={len(v):>3}  avg CLV {sum(v)/len(v):+.2f}%  positive {pos}/{len(v)}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Per-phase CLV report (actual bets only)")
    ap.add_argument("--season", type=int, default=2026)
    args = ap.parse_args()

    rows, missing = load_rows(args.season)
    print(f"NRL actual bets with CLV: {len(rows)}")
    if missing:
        print(f"  WARNING — {len(missing)} bets have no placed_date (timing unknown):")
        for m in missing:
            print(f"    {m}")

    summarize(rows, lambda r: r[0], "By phase:")
    summarize(rows, lambda r: (r[0], r[1]), "By phase x Origin camp/backup window:")
    summarize(rows, lambda r: (r[0], r[2]), "By phase x bet timing (team lists Tue 16:00):")
    summarize(rows, lambda r: (r[0], r[4]), "By phase x round:")


if __name__ == "__main__":
    main()
