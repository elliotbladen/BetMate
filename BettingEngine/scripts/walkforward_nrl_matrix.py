#!/usr/bin/env python3
"""Walk-forward the NRL totals matrix at ANY net threshold.

The original NRL study (outputs/results/NRL_TOTALS_MATRIX_V2_HITRATE.md) only
walked forward four configurations, none above **net +7**. Its net +10 figure
(+18.92%) was 2026 alone, 12 bets. The AFL repeat of that study found the edge
living specifically at net >=10 and climbing with selectivity, so the threshold
NRL never tested is the one worth testing.

This drives the EXISTING, unmodified backtest so the published NRL script keeps
its behaviour: it rebuilds the totals matrix per rolling window, shells out to
``backtest_nrl_matrix_net7_2026.py`` per test season, and pools per-bet P/L from
its --csv output for a bootstrap CI.

Usage:
    python scripts/walkforward_nrl_matrix.py --net 10 --price open
"""

from __future__ import annotations

import argparse
import csv
import os
import random
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "nrl_team_totals_matrix.py"
BACKTEST = ROOT / "scripts" / "backtest_nrl_matrix_net7_2026.py"
RESULTS = ROOT / "outputs" / "nrl_weekly_review" / "historical" / "latest.xlsx"


def bootstrap_ci(pnls, iters=5000, seed=7):
    if not pnls:
        return (0.0, 0.0)
    rng = random.Random(seed)
    n = len(pnls)
    rois = sorted(sum(pnls[rng.randrange(n)] for _ in range(n)) / n * 100
                  for _ in range(iters))
    return (rois[int(0.025 * iters)], rois[int(0.975 * iters)])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--metric", choices=["mean", "hitrate"], default="hitrate")
    ap.add_argument("--train-window", type=int, default=4)
    ap.add_argument("--net", type=int, default=10)
    ap.add_argument("--min-edge", type=float, default=5.0)
    ap.add_argument("--price", choices=["close", "open"], default="close")
    ap.add_argument("--first-test", type=int, default=2017)
    ap.add_argument("--last-test", type=int, default=2026)
    args = ap.parse_args()

    env = dict(os.environ, NRL_HISTORICAL_XLSX=str(RESULTS))
    tmp = Path(tempfile.mkdtemp(prefix="nrl_wf_"))
    seasons = list(range(args.first_test, args.last_test + 1))
    per_season, pooled = {}, []

    ver = "v2" if args.metric == "hitrate" else "v1"
    print(f"NRL totals matrix walk-forward [{ver}/{args.metric}] — "
          f"{args.train_window}-season window, net +{args.net}, "
          f"cells >={args.min_edge:g}%, {args.price} price\n")

    for ts in seasons:
        window = list(range(ts - args.train_window, ts))
        mx = tmp / f"nrl_{ver}_{ts}.xlsx"
        b = subprocess.run(
            [sys.executable, str(BUILDER), "--metric", args.metric,
             "--seasons", ",".join(map(str, window)), "--out", str(mx)],
            capture_output=True, text=True, env=env)
        if b.returncode != 0:
            raise SystemExit(f"build failed {ts}:\n{b.stdout}\n{b.stderr}")

        out_csv = tmp / f"bets_{ts}.csv"
        r = subprocess.run(
            [sys.executable, str(BACKTEST), "--markets", "totals",
             "--season", str(ts), "--net", str(args.net),
             "--min-edge", str(args.min_edge), "--price", args.price,
             "--totals-matrix", str(mx), "--csv", str(out_csv)],
            capture_output=True, text=True, env=env)
        if r.returncode != 0:
            raise SystemExit(f"backtest failed {ts}:\n{r.stdout}\n{r.stderr}")

        rows = []
        if out_csv.exists():
            with out_csv.open(encoding="utf-8") as fh:
                rows = [x for x in csv.DictReader(fh) if x["result"] != "no_price"]
        pnls = [float(x["pnl"]) for x in rows]
        roi = (sum(pnls) / len(pnls) * 100) if pnls else 0.0
        wins = sum(1 for x in rows if x["result"] == "win")
        staked = sum(1 for x in rows if x["result"] != "push")
        strike = wins / staked * 100 if staked else 0.0
        per_season[ts] = (len(rows), strike, roi)
        pooled.extend(pnls)
        print(f"  test {ts}  train {window[0]}-{window[-1]}"
              f"{'  [COVID 2020 in window]' if 2020 in window else ''}"
              f"   {len(rows):>3} bets  strike {strike:5.1f}%  ROI {roi:+7.2f}%")

    lo, hi = bootstrap_ci(pooled)
    proi = (sum(pooled) / len(pooled) * 100) if pooled else 0.0
    pos = sum(1 for ts in seasons if per_season[ts][2] > 0)
    print("\n" + "=" * 70)
    print("  ".join(f"{ts:>7}" for ts in seasons))
    print("  ".join(f"{per_season[ts][2]:>+6.1f}%" for ts in seasons))
    print(f"\npooled ROI {proi:+.2f}%  (n={len(pooled)})  95% CI [{lo:+.1f}, {hi:+.1f}]"
          f"   seasons positive {pos}/{len(seasons)}")


if __name__ == "__main__":
    main()
