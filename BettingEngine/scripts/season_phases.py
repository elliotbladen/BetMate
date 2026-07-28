"""
season_phases.py
----------------
Season phase tagging for per-round evidence files (CLV running, model accuracy).

Purpose: build the evidence base for phase-weighted pricing next season by
tagging every 2026 round with which regime it was played in, so the
end-of-season review can measure model error / CLV per phase BEFORE any
phase weights are fitted.

NRL phases are EVENT-ANCHORED, not fixed round numbers — Origin dates drift
year to year and the fatigue effect bleeds into the round after each game
(R19 2026 was the proof: G3 played Jul 8, backup fatigue landed Jul 10-12).

  early   — round ends before the first Origin camp opens
  origin  — round falls inside the Origin era (first camp open → 7 days
            after the last game). origin_window says whether the round
            actually overlaps a camp/backup window (True) or is merely an
            Origin-era round with no camp or backup that week (False).
  late    — round starts after the Origin era closes
  finals  — round number above the regular season (NRL: 27 rounds)

Origin window per game = [camp_start, game_date + 7 days] — camp absence
plus the backup-fatigue round after the game (~66% capacity, calibrated
2026-07-07).

AFL has no Origin. Its phases are a DESCRIPTIVE calendar split only (early
R1-8, mid R9-16, late R17-23, finals R24+) — do not fit weights to them
without a mechanism.

Data sources:
  {BETMATE_ROOT}/data/nrl/origin/{season}.json  — camp windows + game dates
  data/model.db matches table                   — NRL round date ranges

CLI:
  python scripts/season_phases.py --season 2026
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
from datetime import date, timedelta
from pathlib import Path

ENGINE_ROOT = Path(__file__).resolve().parent.parent

BACKUP_DAYS = 7            # fatigue window after each Origin game
NRL_REGULAR_ROUNDS = 27
AFL_REGULAR_ROUNDS = 23


def _betmate_root() -> Path:
    return Path(os.environ.get("BETMATE_ROOT", ENGINE_ROOT.parent))


def origin_windows(season: int) -> list[tuple[str, str]]:
    """[(start, end)] per Origin game: camp_start → game date + BACKUP_DAYS."""
    path = _betmate_root() / "data" / "nrl" / "origin" / f"{season}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"Origin data not found: {path} — populate it before tagging phases"
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    windows = []
    for g in data.get("origin_games", []):
        camp_start = g.get("camp_start", "")
        game_date = g.get("date", "")
        if not (camp_start and game_date):
            continue
        end = date.fromisoformat(game_date) + timedelta(days=BACKUP_DAYS)
        windows.append((camp_start, end.isoformat()))
    return sorted(windows)


def nrl_phase(
    season: int,
    round_number: int,
    round_start: str,
    round_end: str,
) -> tuple[str, bool]:
    """
    Return (phase, origin_window) for an NRL round given its date range.
    Dates are 'YYYY-MM-DD' strings (string comparison is safe for ISO dates).
    """
    if round_number > NRL_REGULAR_ROUNDS:
        return "finals", False

    windows = origin_windows(season)
    if not windows:
        return "early", False

    era_start = windows[0][0]
    era_end = windows[-1][1]

    if round_end < era_start:
        return "early", False
    if round_start > era_end:
        return "late", False

    in_window = any(
        round_start <= w_end and round_end >= w_start
        for w_start, w_end in windows
    )
    return "origin", in_window


def nrl_round_dates(season: int) -> dict[int, tuple[str, str]]:
    """{round_number: (min_date, max_date)} for NRL from model.db."""
    db = ENGINE_ROOT / "data" / "model.db"
    conn = sqlite3.connect(db)
    try:
        rows = conn.execute(
            "SELECT round_number, MIN(match_date), MAX(match_date) "
            "FROM matches WHERE sport='NRL' AND season=? GROUP BY round_number",
            (season,),
        ).fetchall()
    finally:
        conn.close()
    return {int(r): (lo, hi) for r, lo, hi in rows}


def afl_phase(round_number: int) -> tuple[str, bool]:
    """Descriptive calendar split only — no event anchor exists for AFL."""
    if round_number > AFL_REGULAR_ROUNDS:
        return "finals", False
    if round_number <= 8:
        return "early", False
    if round_number <= 16:
        return "mid", False
    return "late", False


def phase_for_round(sport: str, season: int, round_number) -> tuple[str, bool]:
    """
    (phase, origin_window) for a (sport, round). Returns ("", False) when the
    round can't be resolved (unparseable round, no dates in DB yet).
    """
    try:
        rnd = int(str(round_number).strip())
    except (TypeError, ValueError):
        return "", False

    if sport.upper() == "AFL":
        return afl_phase(rnd)

    dates = nrl_round_dates(season)
    if rnd not in dates:
        if rnd > NRL_REGULAR_ROUNDS:
            return "finals", False
        return "", False
    lo, hi = dates[rnd]
    return nrl_phase(season, rnd, lo, hi)


def main() -> None:
    ap = argparse.ArgumentParser(description="Print season phase table")
    ap.add_argument("--season", type=int, default=2026)
    args = ap.parse_args()

    print(f"Origin windows {args.season} (camp open -> game + {BACKUP_DAYS}d):")
    for w in origin_windows(args.season):
        print(f"  {w[0]} -> {w[1]}")

    print(f"\nNRL {args.season} rounds:")
    for rnd, (lo, hi) in sorted(nrl_round_dates(args.season).items()):
        phase, window = nrl_phase(args.season, rnd, lo, hi)
        flag = " (camp/backup window)" if window else ""
        print(f"  R{rnd:>2}  {lo} .. {hi}  {phase}{flag}")


if __name__ == "__main__":
    main()
