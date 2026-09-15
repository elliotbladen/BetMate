#!/usr/bin/env python3
"""Walk-forward the NRL matrices (h2h / handicap / totals) at ANY net threshold.

Why this exists
---------------
The original NRL study (`outputs/results/NRL_TOTALS_MATRIX_V2_HITRATE.md`) walked
forward **totals only**, and only up to **net +7**. Its net +10 figure (+18.92%) was
2026 alone, 12 bets; its h2h (-26.9%) and handicap (-5.0%) figures were **2026 alone
as well**, never walked forward.

The AFL repeat of that study held every market to a 9-season walk-forward before any
conclusion was drawn. This brings NRL to the same standard, so the decision to retire
the NRL matrices rests on the same quality of evidence the AFL decision did.

How it works
------------
Drives the **unmodified** `backtest_nrl_matrix_net7_2026.py` so the published script
keeps its behaviour. Per test season it rebuilds the market's matrix on a rolling
training window, points the backtest at that artefact, and pools per-bet P/L from the
backtest's own ``--csv`` output for a bootstrap CI.

The backtest exposes a CLI override only for the totals matrix, so for h2h/handicap the
module-level matrix constants are rebound in-process before calling ``main()``. That
reads from the temp artefact without touching the production file on disk.

Validation
----------
``--validate`` reproduces the published cells>=5%/net+5 totals row
(-15.3 / +3.3 / -21.6 / +7.0, pooled -7.93%, n=382) and exits non-zero on a mismatch.

Usage:
    python scripts/walkforward_nrl_matrix.py --market totals   --net 10 --price open
    python scripts/walkforward_nrl_matrix.py --market h2h      --net 7
    python scripts/walkforward_nrl_matrix.py --market handicap --net 7
    python scripts/walkforward_nrl_matrix.py --validate
"""

from __future__ import annotations

import argparse
import contextlib
import csv
import io
import importlib.util
import os
import random
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKTEST = ROOT / "scripts" / "backtest_nrl_matrix_net7_2026.py"
RESULTS = ROOT / "outputs" / "nrl_weekly_review" / "historical" / "latest.xlsx"

BUILDERS = {
    "totals": ROOT / "scripts" / "nrl_team_totals_matrix.py",
    "h2h": ROOT / "scripts" / "nrl_h2h_matrix.py",
    "handicap": ROOT / "scripts" / "nrl_handicap_matrix.py",
}


def _load_backtest():
    spec = importlib.util.spec_from_file_location("nrl_bt", BACKTEST)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["nrl_bt"] = mod
    spec.loader.exec_module(mod)
    return mod


def bootstrap_ci(pnls, iters=5000, seed=7):
    if not pnls:
        return (0.0, 0.0)
    rng = random.Random(seed)
    n = len(pnls)
    rois = sorted(sum(pnls[rng.randrange(n)] for _ in range(n)) / n * 100
                  for _ in range(iters))
    return (rois[int(0.025 * iters)], rois[int(0.975 * iters)])


def build(market: str, metric: str, window: list[int], out: Path, env: dict) -> Path:
    """Build one matrix for a training window; return the artefact to load."""
    cmd = [sys.executable, str(BUILDERS[market]),
           "--seasons", ",".join(map(str, window)), "--out", str(out)]
    if market == "totals":
        cmd += ["--metric", metric]
    csv_out = out.with_suffix(".csv")
    if market == "handicap":
        cmd += ["--csv-out", str(csv_out)]
    r = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if r.returncode != 0:
        raise SystemExit(f"matrix build failed ({market} {window}):\n{r.stdout}\n{r.stderr}")
    return csv_out if market == "handicap" else out


def season_bets(bt, market: str, artefact: Path, season: int, net: int,
                min_edge: float, price: str, tmp: Path) -> list[dict]:
    """Run the unmodified backtest for one season against one matrix artefact."""
    out_csv = tmp / f"bets_{market}_{season}.csv"
    argv = [str(BACKTEST), "--markets", market, "--season", str(season),
            "--net", str(net), "--min-edge", str(min_edge), "--price", price,
            "--csv", str(out_csv)]
    # Only totals has a CLI override; rebind the others in-process so the
    # production artefacts on disk are never touched.
    saved = (bt.H2H_MATRIX, bt.HANDICAP_MATRIX)
    if market == "totals":
        argv += ["--totals-matrix", str(artefact)]
    elif market == "h2h":
        bt.H2H_MATRIX = artefact
    else:
        bt.HANDICAP_MATRIX = artefact
    try:
        old_argv, sys.argv = sys.argv, argv
        with contextlib.redirect_stdout(io.StringIO()):
            bt.main()
    finally:
        sys.argv = old_argv
        bt.H2H_MATRIX, bt.HANDICAP_MATRIX = saved
    if not out_csv.exists():
        return []
    with out_csv.open(encoding="utf-8") as fh:
        return [x for x in csv.DictReader(fh) if x["result"] != "no_price"]


def run(market, metric, net, min_edge, price, seasons, window_len, quiet=False):
    env = dict(os.environ, NRL_HISTORICAL_XLSX=str(RESULTS))
    bt = _load_backtest()
    tmp = Path(tempfile.mkdtemp(prefix="nrl_wf_"))
    per, pooled = {}, []
    for ts in seasons:
        window = list(range(ts - window_len, ts))
        art = build(market, metric, window, tmp / f"{market}_{ts}.xlsx", env)
        rows = season_bets(bt, market, art, ts, net, min_edge, price, tmp)
        pnls = [float(x["pnl"]) for x in rows]
        roi = (sum(pnls) / len(pnls) * 100) if pnls else 0.0
        wins = sum(1 for x in rows if x["result"] == "win")
        staked = sum(1 for x in rows if x["result"] != "push")
        per[ts] = (len(rows), wins / staked * 100 if staked else 0.0, roi)
        pooled.extend(pnls)
        if not quiet:
            print(f"  test {ts}  train {window[0]}-{window[-1]}"
                  f"{'  [COVID 2020 in window]' if 2020 in window else ''}"
                  f"   {len(rows):>3} bets  strike {per[ts][1]:5.1f}%  ROI {roi:+7.2f}%")
    return per, pooled


def report(market, per, pooled, seasons):
    lo, hi = bootstrap_ci(pooled)
    proi = (sum(pooled) / len(pooled) * 100) if pooled else 0.0
    pos = sum(1 for ts in seasons if per[ts][2] > 0)
    print("\n" + "=" * 72)
    print("  ".join(f"{ts:>7}" for ts in seasons))
    print("  ".join(f"{per[ts][2]:>+6.1f}%" for ts in seasons))
    print(f"\n{market}: pooled ROI {proi:+.2f}%  (n={len(pooled)})  "
          f"95% CI [{lo:+.1f}, {hi:+.1f}]   seasons positive {pos}/{len(seasons)}")
    return proi


def validate() -> int:
    """Reproduce the published totals row; non-zero exit on mismatch."""
    want = {2023: -15.3, 2024: +3.3, 2025: -21.6, 2026: +7.0}
    seasons = list(want)
    per, pooled = run("totals", "hitrate", 5, 5.0, "close", seasons, 4, quiet=True)
    ok = True
    print("validation — published cells>=5% / net+5 totals row")
    for ts in seasons:
        got = round(per[ts][2], 1)
        hit = abs(got - want[ts]) <= 0.15
        ok &= hit
        print(f"  {ts}: expected {want[ts]:+.1f}%  got {got:+.1f}%  {'OK' if hit else 'MISMATCH'}")
    proi = sum(pooled) / len(pooled) * 100
    pool_ok = abs(proi + 7.93) <= 0.05 and len(pooled) == 382
    ok &= pool_ok
    print(f"  pooled: expected -7.93% (n=382)  got {proi:+.2f}% (n={len(pooled)})  "
          f"{'OK' if pool_ok else 'MISMATCH'}")
    print("VALIDATION PASSED" if ok else "VALIDATION FAILED")
    return 0 if ok else 1


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--market", choices=["totals", "h2h", "handicap"], default="totals")
    ap.add_argument("--metric", choices=["mean", "hitrate"], default="hitrate",
                    help="totals only")
    ap.add_argument("--train-window", type=int, default=4)
    ap.add_argument("--net", type=int, default=10)
    ap.add_argument("--min-edge", type=float, default=5.0)
    ap.add_argument("--price", choices=["close", "open"], default="close")
    ap.add_argument("--first-test", type=int, default=2017)
    ap.add_argument("--last-test", type=int, default=2026)
    ap.add_argument("--skip-seasons", default=None,
                    help="comma list of seasons to exclude. ⚠️ The NRL file is missing "
                         "H2H and LINE-ODDS closing prices for 70%% of 2024 and 99.5%% of "
                         "2025 (totals are complete). Those seasons must be skipped for "
                         "h2h/handicap or they enter as silent zeros.")
    ap.add_argument("--validate", action="store_true",
                    help="reproduce the published totals row and exit")
    args = ap.parse_args()

    if args.validate:
        raise SystemExit(validate())

    seasons = list(range(args.first_test, args.last_test + 1))
    if args.skip_seasons:
        skip = {int(x) for x in args.skip_seasons.split(",")}
        seasons = [s for s in seasons if s not in skip]
        print(f"⚠️ skipping {sorted(skip)} — insufficient market coverage\n")
    print(f"NRL {args.market} matrix walk-forward — {args.train_window}-season window, "
          f"net +{args.net}, cells >={args.min_edge:g}%, {args.price} price\n")
    per, pooled = run(args.market, args.metric, args.net, args.min_edge,
                      args.price, seasons, args.train_window)
    report(args.market, per, pooled, seasons)


if __name__ == "__main__":
    main()
