#!/usr/bin/env python3
"""
clv_plain_english.py
--------------------
Reads a CLV report CSV and prints:
  1. Per-game: did market move TO or AWAY from the model's number?
  2. Market-type summary: avg CLV, % positive CLV, W/L record
  3. EV sim: $1 on every model signal where model odds > open market odds

Usage:
  uv run python scripts/clv_plain_english.py --file outputs/nrl_weekly_review/reports/r14_nrl_clv_report_2026.csv --sport NRL --round 14
  uv run python scripts/clv_plain_english.py --file outputs/afl_weekly_review/reports/r13_afl_ml_clv_comparison_2026.csv --sport AFL --round 13
"""

from __future__ import annotations
import argparse
import csv
from collections import defaultdict
from pathlib import Path


def load(path: str) -> list[dict]:
    rows = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            rows.append(row)
    return rows


def flt(v) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def game_key(row: dict) -> str:
    return f"{row['date']} {row['home_team']} v {row['away_team']}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--sport", default="NRL")
    ap.add_argument("--round", default="?")
    ap.add_argument("--signal", default="model",
                    help="Which signal rows to use: model | normal | ml (default: model)")
    args = ap.parse_args()

    rows = load(args.file)
    # For AFL reports the signal column uses 'normal' instead of 'model'
    signal_label = args.signal
    if signal_label == "model" and any(r.get("signal") == "normal" for r in rows):
        signal_label = "normal"

    model_rows = [r for r in rows if r.get("signal") == signal_label]
    market_rows = [r for r in rows if r.get("signal") == "market"]

    print(f"\n{'='*80}")
    print(f"  {args.sport} R{args.round} CLV — Plain English")
    print(f"{'='*80}")

    # ── 1. Per-game: market movement direction ─────────────────────────────
    print(f"\n{'─'*80}")
    print("  MARKET MOVEMENT PER GAME  (did market move TOWARD or AWAY from model?)")
    print(f"{'─'*80}")
    print(f"  {'Game':<42} {'Mkt':<8} {'Selection':<28} {'Model':<8} {'Open':<8} {'Close':<8} {'Move'}")
    print(f"  {'─'*42} {'─'*8} {'─'*28} {'─'*8} {'─'*8} {'─'*8} {'─'*20}")

    games_seen = {}
    for row in model_rows:
        gk = game_key(row)
        mkt = row.get("market", "")
        sel = row.get("selection", "")
        model_odds = flt(row.get("model_home_fair_odds")) if "home" in sel.lower() or sel == row.get("home_team","") else flt(row.get("model_away_fair_odds"))
        # fallback: use model_number for lines/totals
        model_num = flt(row.get("model_number"))
        open_odds = flt(row.get("open_odds"))
        close_odds = flt(row.get("close_odds"))
        open_num = flt(row.get("open_number"))
        close_num = flt(row.get("close_number"))
        clv = flt(row.get("clv"))
        result = row.get("result", "?")
        h_score = row.get("home_score", "?")
        a_score = row.get("away_score", "?")

        # Shorten game name
        home = row.get("home_team","").split()[-1]
        away = row.get("away_team","").split()[-1]
        game_short = f"{home} v {away} ({h_score}-{a_score})"

        if mkt == "h2h":
            if model_odds and open_odds and close_odds:
                # Did close move toward model fair odds?
                gap_open  = abs(open_odds  - model_odds)
                gap_close = abs(close_odds - model_odds)
                if gap_close < gap_open:
                    direction = "→ TOWARD  ✓"
                elif gap_close > gap_open:
                    direction = "← AWAY   ✗"
                else:
                    direction = "= FLAT"
                clv_str = f"{clv:+.3f}" if clv is not None else "—"
                res_str = result.upper()
                move_str = f"{direction}  CLV {clv_str}  [{res_str}]"
                print(f"  {game_short:<42} {mkt:<8} {sel:<28} {model_odds:<8.3f} {open_odds:<8.3f} {close_odds:<8.3f} {move_str}")

        elif mkt in ("spreads", "handicap"):
            if model_num is not None and open_num is not None and close_num is not None:
                gap_open  = abs(open_num  - model_num)
                gap_close = abs(close_num - model_num)
                if gap_close < gap_open:
                    direction = "→ TOWARD  ✓"
                elif gap_close > gap_open:
                    direction = "← AWAY   ✗"
                else:
                    direction = "= FLAT"
                clv_str = f"{clv:+.3f}" if clv is not None else "—"
                move_str = f"{direction}  model {model_num:+.1f}  open {open_num:+.1f}  close {close_num:+.1f}  [{result.upper()}]"
                print(f"  {game_short:<42} {mkt:<8} {sel:<28} {'':8} {'':8} {'':8} {move_str}")

        elif mkt in ("totals", "over_under"):
            if model_num is not None and open_num is not None and close_num is not None:
                gap_open  = abs(open_num  - model_num)
                gap_close = abs(close_num - model_num)
                if gap_close < gap_open:
                    direction = "→ TOWARD  ✓"
                elif gap_close > gap_open:
                    direction = "← AWAY   ✗"
                else:
                    direction = "= FLAT"
                clv_str = f"{clv:+.3f}" if clv is not None else "—"
                move_str = f"{direction}  model {model_num:.1f}  open {open_num:.1f}  close {close_num:.1f}  [{result.upper()}]"
                print(f"  {game_short:<42} {mkt:<8} {sel:<28} {'':8} {'':8} {'':8} {move_str}")

    # ── 2. Summary by market type ──────────────────────────────────────────
    print(f"\n{'─'*80}")
    print("  SUMMARY BY MARKET TYPE  (model signals only)")
    print(f"{'─'*80}")

    by_mkt: dict[str, list] = defaultdict(list)
    for row in model_rows:
        mkt = row.get("market","")
        clv = flt(row.get("clv"))
        result = row.get("result","")
        open_odds = flt(row.get("open_odds"))
        close_odds = flt(row.get("close_odds"))
        if clv is not None:
            by_mkt[mkt].append({
                "clv": clv, "result": result,
                "open_odds": open_odds, "close_odds": close_odds
            })

    total_clv_pos = 0
    total_clv_neg = 0

    for mkt in ["h2h", "spreads", "handicap", "totals", "over_under"]:
        items = by_mkt.get(mkt, [])
        if not items:
            continue
        avg_clv = sum(i["clv"] for i in items) / len(items)
        pct_pos = sum(1 for i in items if i["clv"] > 0) / len(items) * 100
        wins = sum(1 for i in items if i["result"] == "win")
        losses = sum(1 for i in items if i["result"] == "loss")
        # Market confirmed = CLV positive = close moved in your direction
        confirmed = sum(1 for i in items if i["clv"] > 0)
        market_label = mkt.upper()
        print(f"  {market_label:<12}  {len(items):2} signals  |  avg CLV: {avg_clv:+.4f}  |  market confirmed: {confirmed}/{len(items)} ({pct_pos:.0f}%)  |  W/L: {wins}/{losses}")
        total_clv_pos += sum(i["clv"] for i in items if i["clv"] > 0)
        total_clv_neg += sum(i["clv"] for i in items if i["clv"] < 0)

    overall = [(r["clv"], r["result"]) for mkt_rows in by_mkt.values() for r in mkt_rows]
    if overall:
        avg_all = sum(c for c,_ in overall) / len(overall)
        pct_pos_all = sum(1 for c,_ in overall if c > 0) / len(overall) * 100
        wins_all = sum(1 for _,r in overall if r == "win")
        print(f"  {'OVERALL':<12}  {len(overall):2} signals  |  avg CLV: {avg_all:+.4f}  |  market confirmed: {sum(1 for c,_ in overall if c>0)}/{len(overall)} ({pct_pos_all:.0f}%)  |  W/L: {wins_all}/{len(overall)-wins_all}")

    # ── 3. EV simulation — $1 on every model signal where model beats open ─
    print(f"\n{'─'*80}")
    print("  EV SIMULATION  — $1 per bet, only where model odds > open market odds")
    print("  (i.e. model says team is underpriced at open — these are your buy signals)")
    print(f"{'─'*80}")

    ev_bets = []
    for row in model_rows:
        mkt = row.get("market","")
        sel = row.get("selection","")
        open_odds = flt(row.get("open_odds"))
        model_h = flt(row.get("model_home_fair_odds"))
        model_a = flt(row.get("model_away_fair_odds"))
        result = row.get("result","")
        home = row.get("home_team","")
        away = row.get("away_team","")
        h_score = row.get("home_score","?")
        a_score = row.get("away_score","?")
        clv = flt(row.get("clv"))

        if mkt != "h2h" or open_odds is None:
            continue

        # Determine if model says this side is value vs open
        is_home_sel = (sel == home)
        model_odds = model_h if is_home_sel else model_a

        if model_odds is None or open_odds is None:
            continue

        # Model says team is underpriced if model_odds > open_odds
        # (model says fair value is longer than market is offering)
        if model_odds > open_odds * 1.02:  # 2% threshold to filter noise
            profit = (open_odds - 1) if result == "win" else -1.0
            game_short = f"{home.split()[-1]} v {away.split()[-1]} ({h_score}-{a_score})"
            ev_bets.append({
                "game": game_short,
                "sel": sel.split()[-1],
                "model": model_odds,
                "open": open_odds,
                "edge_pct": (model_odds / open_odds - 1) * 100,
                "result": result,
                "profit": profit,
                "clv": clv,
            })

    if ev_bets:
        print(f"  {'Game':<38} {'Sel':<12} {'Model':<8} {'Open':<8} {'Edge':<8} {'Result':<8} {'P&L':<8} {'CLV'}")
        print(f"  {'─'*38} {'─'*12} {'─'*8} {'─'*8} {'─'*8} {'─'*8} {'─'*8} {'─'*8}")
        total_pl = 0
        for b in sorted(ev_bets, key=lambda x: -x["edge_pct"]):
            clv_str = f"{b['clv']:+.3f}" if b["clv"] is not None else "—"
            print(f"  {b['game']:<38} {b['sel']:<12} {b['model']:<8.3f} {b['open']:<8.3f} {b['edge_pct']:+5.1f}%  {b['result'].upper():<8} {b['profit']:+.2f}    {clv_str}")
            total_pl += b["profit"]
        n = len(ev_bets)
        roi = total_pl / n * 100
        wins_ev = sum(1 for b in ev_bets if b["result"] == "win")
        print(f"  {'─'*80}")
        print(f"  {n} bets  |  {wins_ev}W / {n-wins_ev}L  |  total P&L: {total_pl:+.2f} units  |  ROI: {roi:+.1f}%")
    else:
        print("  No signals where model odds > open market odds (no buy signals this round)")

    print(f"\n{'='*80}\n")


if __name__ == "__main__":
    main()
