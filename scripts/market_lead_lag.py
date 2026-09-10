#!/usr/bin/env python3
"""Which bookmaker moves first? Rank books by how early they complete a consensus move.

    python scripts/market_lead_lag.py                        # local CSV archive
    python scripts/market_lead_lag.py --sport NRL --resample 60min

Method: for each (game, outcome), take every book present for most of the series,
measure its total open->close journey, and record when it first crosses HALF of that
journey. Books are ranked within each move and the ranks averaged. 0.0 = always first,
1.0 = always last.

Two things this does and does not tell you:

  * It measures leadership on the SLOW multi-day repricing. Verified stable when the
    same data is downsampled -- ordering holds at hourly (rho=+0.84) and 2-hourly
    (rho=+0.74) against the 10-minute reference. That is why the production collector
    runs 2-hourly and does not need to be faster for this question.
  * It does NOT measure minute-scale reaction ("book A moved, book B copied nine
    minutes later"). That needs minute sampling and is invisible here at any cadence.

Sanity check worth repeating on new data: books sharing a parent should land on nearly
identical scores, because they share a trading team. On the first 110 moves Ladbrokes AU
and Neds both scored 0.718 with Coral at 0.715 (all Entain), and Paddy Power 0.674 sat
beside Betfair Sportsbook 0.639 (both Flutter). If that structure disappears, suspect the
metric before believing the result.
"""
from __future__ import annotations

import argparse
import glob
import os
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
ARCHIVE = ROOT / "data/odds_snapshots"

MIN_BOOKS = 5           # a move needs this many books to rank
MIN_POINTS = 8          # and this many observations in the series
MIN_CONSENSUS = 0.05    # ignore fixtures that never really moved
MIN_BOOK_MOVE = 0.02    # ignore a book that barely twitched
PRESENCE = 0.6          # a book must be quoting for this share of the series


def load_archive(min_bytes: int = 3_000_000) -> pd.DataFrame:
    files = [f for f in sorted(glob.glob(str(ARCHIVE / "*/*.csv")))
             if os.path.getsize(f) > min_bytes]
    if not files:
        raise SystemExit(f"no snapshot files over {min_bytes} bytes under {ARCHIVE}")
    d = pd.concat([pd.read_csv(f, low_memory=False) for f in files], ignore_index=True)
    d["ts"] = pd.to_datetime(d.snapshot_date + " " + d.snapshot_time)
    d["ko"] = pd.to_datetime(d.commence_time, errors="coerce", utc=True).dt.tz_localize(None)
    d = d.dropna(subset=["ko", "price"])
    return d[(d.ko - d.ts).dt.total_seconds() > 0].sort_values("ts")


def rank_moves(d: pd.DataFrame) -> tuple[pd.Series, pd.Series, int]:
    rows = []
    for _, g in d.groupby(["game_id", "outcome"]):
        piv = g.pivot_table(index="ts", columns="bookmaker", values="price",
                            aggfunc="last").sort_index()
        piv = piv.dropna(axis=1, thresh=int(len(piv) * PRESENCE))
        if piv.shape[1] < MIN_BOOKS or len(piv) < MIN_POINTS:
            continue
        first, last = piv.iloc[0], piv.iloc[-1]
        move = last - first
        consensus = move.mean()
        if abs(consensus) < MIN_CONSENSUS:
            continue
        crossed = {}
        for book in piv.columns:
            # a book that moved the other way is not "late", it disagreed — drop it
            if np.sign(move[book]) != np.sign(consensus) or abs(move[book]) < MIN_BOOK_MOVE:
                continue
            target = first[book] + 0.5 * move[book]
            hits = piv.index[(piv[book] - target) * np.sign(move[book]) >= 0]
            if len(hits):
                crossed[book] = hits[0]
        if len(crossed) >= MIN_BOOKS:
            order = pd.Series(crossed).rank(method="min")
            rows.append(order / order.max())
    frame = pd.DataFrame(rows)
    return frame.mean(), frame.notna().sum(), len(frame)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sport", help="limit to one sport code")
    ap.add_argument("--market", default="h2h")
    ap.add_argument("--resample", help="downsample first, e.g. 60min — for cadence tests")
    ap.add_argument("--min-moves", type=int, default=15,
                    help="a book needs this many ranked moves to be reported")
    args = ap.parse_args()

    d = load_archive()
    d = d[d.market == args.market]
    if args.sport:
        d = d[d.sport == args.sport]
    if args.resample:
        kos = d.groupby("game_id").ko.first()
        d["ts"] = d.ts.dt.floor(args.resample)
        d = d.groupby(["game_id", "outcome", "bookmaker", "ts"], as_index=False).price.last()
        d["ko"] = kos.reindex(d.game_id).values

    avg, counts, moves = rank_moves(d)
    keep = avg[counts >= args.min_moves].sort_values()
    label = f"{args.sport or 'all sports'} · {args.market}"
    if args.resample:
        label += f" · downsampled to {args.resample}"
    print(f"WHO MOVES FIRST — {moves} consensus moves — {label}")
    print("0.0 = always first to complete half the move, 1.0 = always last\n")
    print(f"{'bookmaker':<18}{'avg rank':>10}{'moves':>8}")
    for book, value in keep.items():
        print(f"{book:<18}{value:>10.3f}{counts[book]:>8}")
    if moves < 200:
        print(f"\n  ! only {moves} moves — provisional. Re-run once the cloud collector"
              f"\n    has filled the warehouse; 39 days of a sleeping laptop is a thin base.")


if __name__ == "__main__":
    main()
