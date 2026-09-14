#!/usr/bin/env python3
"""Walk-forward test of the AFL matrices (h2h / handicap / totals).

Mirror of the NRL walk-forward in outputs/results/NRL_TOTALS_MATRIX_V2_HITRATE.md:
a rolling training window, each test season strictly out of sample, flat stakes,
one unit per qualifying side, pooled ROI with a bootstrap 95% CI.

The AFL file carries closing totals from 2014, so AFL supports a much longer
walk-forward than the NRL one (which only had 2023-26).

⚠️ 2020 was COVID-shortened (16-minute quarters, mean total 121.2 vs 160-180).
The market tracked it (mean close 122.4), so a relative metric is not distorted
by it, but any window containing 2020 is flagged in the output.

Usage:
    python scripts/walkforward_afl_totals_matrix.py --train-window 4 --net 7
"""

from __future__ import annotations

import argparse
import importlib.util
import random
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDERS = {
    "totals": ROOT / "scripts" / "afl_team_totals_matrix.py",
    "h2h": ROOT / "scripts" / "afl_h2h_matrix.py",
    "handicap": ROOT / "scripts" / "afl_handicap_matrix.py",
}


def _load_backtest():
    spec = importlib.util.spec_from_file_location(
        "afl_bt", ROOT / "scripts" / "backtest_afl_matrix_2026.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["afl_bt"] = mod
    spec.loader.exec_module(mod)
    return mod


def build_matrix(market: str, metric: str, seasons: list[int], out: Path,
                 source: str | None) -> Path:
    """Build one matrix for a training window. Returns the artefact to load."""
    cmd = [sys.executable, str(BUILDERS[market]),
           "--seasons", ",".join(str(s) for s in seasons), "--out", str(out)]
    if market == "totals":
        cmd += ["--metric", metric]
    csv_out = out.with_suffix(".csv")
    if market == "handicap":
        cmd += ["--csv-out", str(csv_out)]
    if source:
        cmd += ["--source", source]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"matrix build failed for {metric} {seasons}:\n{r.stdout}\n{r.stderr}")
    if "WARNING" in r.stdout:
        for line in r.stdout.splitlines():
            if "WARNING" in line:
                print(f"      {line.strip()}")
    return csv_out if market == "handicap" else out


def bootstrap_ci(pnls: list[float], iters: int = 5000, seed: int = 7):
    if not pnls:
        return (0.0, 0.0)
    rng = random.Random(seed)
    n = len(pnls)
    rois = []
    for _ in range(iters):
        s = sum(pnls[rng.randrange(n)] for _ in range(n))
        rois.append(s / n * 100)
    rois.sort()
    return (rois[int(0.025 * iters)], rois[int(0.975 * iters)])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--market", choices=["totals", "h2h", "handicap"], default="totals")
    ap.add_argument("--train-window", type=int, default=4)
    ap.add_argument("--net", type=int, default=7)
    ap.add_argument("--min-edge", type=float, default=5.0)
    ap.add_argument("--price", choices=["close", "open"], default="close")
    ap.add_argument("--first-test", type=int, default=2018,
                    help="first test season (needs train-window seasons of lines before it)")
    ap.add_argument("--last-test", type=int, default=2026)
    ap.add_argument("--source", default=None)
    args = ap.parse_args()

    bt = _load_backtest()
    games = bt.load_games(bt.RESULTS_XLSX)
    bt.attach_context(games)

    # totals is the only market with two metric variants
    variants = [("mean", "v1"), ("hitrate", "v2")] if args.market == "totals" else [("", "--")]

    test_seasons = list(range(args.first_test, args.last_test + 1))
    results: dict[str, dict[int, tuple]] = {v: {} for _, v in variants}
    pooled: dict[str, list[float]] = {v: [] for _, v in variants}

    tmpdir = Path(tempfile.mkdtemp(prefix="afl_wf_"))
    print(f"AFL {args.market} matrix walk-forward — {args.train_window}-season rolling window, "
          f"net +{args.net}, cells >={args.min_edge:g}%, {args.price} price\n")

    for ts in test_seasons:
        window = list(range(ts - args.train_window, ts))
        flag = "  [window includes COVID 2020]" if 2020 in window else ""
        print(f"  test {ts}  train {window[0]}-{window[-1]}{flag}")
        for metric, ver in variants:
            out = tmpdir / f"afl_{args.market}_{ver}_{ts}.xlsx"
            artefact = build_matrix(args.market, metric, window, out, args.source)
            mx = (bt.load_handicap_matrix(artefact) if args.market == "handicap"
                  else bt.load_sheet_matrix(artefact))
            bets = bt.run(games, ts, [(args.market, mx)], args.net,
                          args.min_edge, 0, False, args.price)
            priced = [b for b in bets if b["result"] != "no_price"]
            pnls = [b["pnl"] for b in priced]
            roi = (sum(pnls) / len(pnls) * 100) if pnls else 0.0
            wins = sum(1 for b in priced if b["result"] == "win")
            staked = sum(1 for b in priced if b["result"] != "push")
            strike = wins / staked * 100 if staked else 0.0
            results[ver][ts] = (len(priced), strike, roi)
            pooled[ver].extend(pnls)
            print(f"      {ver}: {len(priced):>3} bets  strike {strike:5.1f}%  ROI {roi:+7.2f}%")

    print("\n" + "=" * 78)
    hdr = "  ".join(f"{ts:>8}" for ts in test_seasons)
    print(f"{'':<5}{hdr}{'':>4}  pooled")
    for _, ver in variants:
        cells = "  ".join(f"{results[ver][ts][2]:>+7.1f}%" for ts in test_seasons)
        p = pooled[ver]
        proi = (sum(p) / len(p) * 100) if p else 0.0
        lo, hi = bootstrap_ci(p)
        print(f"{ver:<5}{cells}   {proi:+.2f}% (n={len(p)}) CI [{lo:+.1f},{hi:+.1f}]")

    print("\nbets per season")
    for _, ver in variants:
        print(f"  {ver}: " + "  ".join(f"{ts}:{results[ver][ts][0]}" for ts in test_seasons))
    print(f"\nmatrices written to {tmpdir}")


if __name__ == "__main__":
    main()
