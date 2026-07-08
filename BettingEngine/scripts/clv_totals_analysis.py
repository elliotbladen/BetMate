#!/usr/bin/env python3
"""
clv_totals_analysis.py
----------------------
Totals-only deep dive from a CLV report CSV.

Shows:
  1. Game-by-game: model number, market open/close, actual total, direction accuracy
  2. Was the model over/under vs the market, and did the line move to you?
  3. EV simulation: $1 on every game where model was FURTHER from actual than market line
  4. Model bias: does it run high or low vs closes, and vs actuals?

Usage:
  uv run python scripts/clv_totals_analysis.py --file outputs/nrl_weekly_review/reports/r14_nrl_clv_report_2026.csv --sport NRL --round 14
"""

from __future__ import annotations
import argparse
import csv
from pathlib import Path


def flt(v) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def load(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--sport", default="NRL")
    ap.add_argument("--round", default="?")
    args = ap.parse_args()

    rows = load(args.file)
    total_rows = [r for r in rows if r.get("market") == "total"]

    # Separate by signal type
    def sig_rows(label):
        return [r for r in total_rows if r.get("signal") == label]

    # AFL uses 'normal', NRL uses 'model'
    model_sig = "normal" if any(r.get("signal") == "normal" for r in total_rows) else "model"
    ml_sig    = "ml"     if any(r.get("signal") == "ml"     for r in total_rows) else None
    mkt_rows  = sig_rows("market")
    mod_rows  = sig_rows(model_sig)
    ml_rows   = sig_rows(ml_sig) if ml_sig else []

    sport = args.sport.upper()

    print(f"\n{'='*96}")
    print(f"  {sport} R{args.round} — TOTALS ANALYSIS")
    print(f"{'='*96}")

    # ── Game-by-game table ────────────────────────────────────────────────
    print(f"\n{'─'*96}")
    print(f"  {'Game':<30} {'Actual':>7} {'Model':>7} {'ML':>7} {'Open':>7} {'Close':>7} "
          f"{'Dir':>6} {'LineMove':>10} {'Mkt→Mod?':>10} {'Result':>7}")
    print(f"  {'─'*30} {'─'*7} {'─'*7} {'─'*7} {'─'*7} {'─'*7} "
          f"{'─'*6} {'─'*10} {'─'*10} {'─'*7}")

    # Build per-game dict
    games = {}
    for r in mod_rows:
        gk = (r["date"], r["home_team"], r["away_team"])
        games[gk] = {
            "home": r["home_team"].split()[-1],
            "away": r["away_team"].split()[-1],
            "actual": flt(r.get("actual_total")),
            "model_num":  flt(r.get("model_number")),
            "model_dir":  r.get("selection","").lower(),
            "open_num":   flt(r.get("open_number")),
            "close_num":  flt(r.get("close_number")),
            "open_odds":  flt(r.get("open_odds")),
            "close_odds": flt(r.get("close_odds")),
            "clv":        flt(r.get("clv")),
            "result":     r.get("result",""),
            "ml_num": None, "ml_dir": None,
        }

    for r in ml_rows:
        gk = (r["date"], r["home_team"], r["away_team"])
        if gk in games:
            games[gk]["ml_num"] = flt(r.get("model_number"))
            games[gk]["ml_dir"] = r.get("selection","").lower()

    # Accumulate bias stats
    model_errors = []    # model_num - actual
    ml_errors    = []
    model_vs_close = []  # model_num - close_num
    direction_correct = 0
    direction_total   = 0
    ml_dir_correct    = 0
    ev_bets = []

    for gk, g in sorted(games.items()):
        home    = g["home"]
        away    = g["away"]
        actual  = g["actual"]
        model   = g["model_num"]
        ml      = g["ml_num"]
        open_n  = g["open_num"]
        close_n = g["close_num"]
        mod_dir   = g["model_dir"]  # "over" or "under"
        result    = g["result"]     # "win" or "loss" = model was right/wrong
        clv       = g["clv"]
        open_odds = g["open_odds"]

        game_str = f"{home} v {away}"

        actual_str = f"{actual:.1f}" if actual else "—"
        model_str  = f"{model:.1f}"  if model  else "—"
        ml_str     = f"{ml:.1f}"     if ml     else "—"
        open_str   = f"{open_n:.1f}" if open_n  else "—"
        close_str  = f"{close_n:.1f}" if close_n else "—"

        # Direction: did the model call over/under correctly?
        dir_correct = "—"
        if actual and model and mod_dir:
            if mod_dir == "over":
                correct = actual > open_n if open_n else False
            else:
                correct = actual < open_n if open_n else False
            dir_correct = "Y" if correct else "N"
            direction_total += 1
            if correct:
                direction_correct += 1

        # Line move: open -> close (negative = line dropped, positive = line rose)
        line_move_str = "—"
        if open_n and close_n:
            mv = close_n - open_n
            line_move_str = f"{mv:+.1f}"

        # Did line move TOWARD model number?
        toward_str = "—"
        if open_n and close_n and model:
            gap_open  = abs(open_n  - model)
            gap_close = abs(close_n - model)
            if gap_close < gap_open - 0.2:
                toward_str = "TOWARD ✓"
            elif gap_close > gap_open + 0.2:
                toward_str = "AWAY   ✗"
            else:
                toward_str = "FLAT"

        # Result symbol
        res_str = f"{result.upper()}" if result else "—"
        if result == "win":
            res_str = "WIN ✓"
        elif result == "loss":
            res_str = "LOSS ✗"

        print(f"  {game_str:<30} {actual_str:>7} {model_str:>7} {ml_str:>7} "
              f"{open_str:>7} {close_str:>7} {dir_correct:>6} "
              f"{line_move_str:>10} {toward_str:>10} {res_str:>7}")

        # Accumulate errors
        if actual and model:
            model_errors.append(model - actual)
        if actual and ml:
            ml_errors.append(ml - actual)
        if model and close_n:
            model_vs_close.append(model - close_n)
        if ml and ml != model:
            ml_dir_correct += 1 if (result == "win") else 0

        # EV sim: where model line differs from open by enough to be actionable
        # If model < open (model says UNDER), bet under at open
        # If model > open (model says OVER), bet over at open
        if model and open_n and open_odds and abs(model - open_n) >= 2.0:
            profit = (open_odds - 1) if result == "win" else -1.0
            edge = open_n - model if mod_dir == "under" else model - open_n
            ev_bets.append({
                "game":    game_str,
                "dir":     mod_dir.upper(),
                "model":   model,
                "open":    open_n,
                "close":   close_n,
                "actual":  actual,
                "edge":    edge,
                "odds":    open_odds,
                "result":  result,
                "profit":  profit,
                "clv":     clv,
            })

    # ── Model accuracy summary ────────────────────────────────────────────
    print(f"\n{'─'*96}")
    print("  MODEL ACCURACY vs ACTUALS  (positive = model predicted higher than actual)")
    print(f"{'─'*96}")

    n = len(model_errors)
    if n:
        avg_err  = sum(model_errors) / n
        mae      = sum(abs(e) for e in model_errors) / n
        over_cnt = sum(1 for e in model_errors if e > 0)
        print(f"  Rules model:  avg error {avg_err:+.2f} pts  |  MAE {mae:.2f} pts  |  "
              f"ran HIGH {over_cnt}/{n} games  ({over_cnt/n*100:.0f}%)")

    if ml_errors:
        n_ml = len(ml_errors)
        avg_ml = sum(ml_errors) / n_ml
        mae_ml = sum(abs(e) for e in ml_errors) / n_ml
        over_ml = sum(1 for e in ml_errors if e > 0)
        print(f"  ML shadow:    avg error {avg_ml:+.2f} pts  |  MAE {mae_ml:.2f} pts  |  "
              f"ran HIGH {over_ml}/{n_ml} games  ({over_ml/n_ml*100:.0f}%)")

    if model_vs_close:
        avg_mvc = sum(model_vs_close) / len(model_vs_close)
        print(f"  Model vs close line:  avg gap {avg_mvc:+.2f} pts  "
              f"({'model runs HIGH vs close' if avg_mvc > 0 else 'model runs LOW vs close'})")

    if direction_total:
        print(f"\n  Direction accuracy (model over/under vs open line):  "
              f"{direction_correct}/{direction_total}  ({direction_correct/direction_total*100:.0f}%)")

    # ── CLV summary ───────────────────────────────────────────────────────
    clv_vals = [g["clv"] for g in games.values() if g["clv"] is not None]
    if clv_vals:
        avg_clv   = sum(clv_vals) / len(clv_vals)
        pos_clv   = sum(1 for c in clv_vals if c > 0)
        print(f"  CLV (open/close - 1):  avg {avg_clv:+.4f}  |  positive {pos_clv}/{len(clv_vals)}  "
              f"({'line shortened = market confirmed direction' if avg_clv > 0 else 'line drifted = market moved away'})")

    # ── EV simulation ─────────────────────────────────────────────────────
    print(f"\n{'─'*96}")
    print(f"  EV SIMULATION — $1 bet where model line differs from open by >= 2 pts")
    print(f"  Model UNDER the open = bet under.  Model OVER the open = bet over.")
    print(f"{'─'*96}")

    if ev_bets:
        print(f"  {'Game':<28} {'Dir':<6} {'Model':>7} {'Open':>7} {'Close':>7} "
              f"{'Actual':>7} {'Edge':>6} {'Odds':>6} {'Result':<8} {'P&L':>6} {'CLV':>8}")
        print(f"  {'─'*28} {'─'*6} {'─'*7} {'─'*7} {'─'*7} {'─'*7} {'─'*6} {'─'*6} {'─'*8} {'─'*6} {'─'*8}")
        total_pl = 0.0
        for b in sorted(ev_bets, key=lambda x: -x["edge"]):
            clv_s = f"{b['clv']:+.3f}" if b["clv"] is not None else "—"
            close_s = f"{b['close']:.1f}" if b["close"] else "—"
            actual_s = f"{b['actual']:.1f}" if b["actual"] else "—"
            res_s = "WIN ✓" if b["result"] == "win" else "LOSS ✗"
            print(f"  {b['game']:<28} {b['dir']:<6} {b['model']:>7.1f} {b['open']:>7.1f} "
                  f"{close_s:>7} {actual_s:>7} {b['edge']:>+6.1f} {b['odds']:>6.2f} "
                  f"{res_s:<8} {b['profit']:>+6.2f} {clv_s:>8}")
            total_pl += b["profit"]
        nev = len(ev_bets)
        wins_ev = sum(1 for b in ev_bets if b["result"] == "win")
        roi = total_pl / nev * 100
        print(f"  {'─'*96}")
        print(f"  {nev} bets  |  {wins_ev}W / {nev-wins_ev}L  |  total P&L: {total_pl:+.2f} units  |  ROI: {roi:+.1f}%")
    else:
        print("  No totals signals with >=2pt gap vs open market")

    print(f"\n{'='*96}\n")


if __name__ == "__main__":
    main()
