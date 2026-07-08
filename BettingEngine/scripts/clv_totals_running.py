"""
clv_totals_running.py
---------------------
Running CLV for totals (over/under) bets only, by sport and round.
Shows: week, round, bet count, direction, line taken vs close, CLV%, result, running totals.

Usage:
  uv run python scripts/clv_totals_running.py
"""
import csv
from collections import defaultdict
from pathlib import Path

ROOT     = Path(__file__).resolve().parent.parent
CLV_FILE = ROOT / "data/clv/running/actual_bets_clv_2026.csv"
BETS_FILE = ROOT / "data/bets/actual_bets_2026.csv"


def load():
    bets_meta = {}
    with open(BETS_FILE, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            bets_meta[r["bet_id"]] = {"week_ending": r["week_ending"], "sport": r["sport"], "round": r["round"]}

    rows = []
    with open(CLV_FILE, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if r.get("market") != "total":
                continue
            meta = bets_meta.get(r["bet_id"], {})
            r["week_ending"] = meta.get("week_ending", "")
            r["sport_upper"] = meta.get("sport", r.get("sport","")).upper()
            rows.append(r)
    return rows


def flt(v, default=None):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def run_sport(rows, sport):
    by_week = defaultdict(list)
    for r in rows:
        if r["sport_upper"] == sport:
            by_week[r["week_ending"]].append(r)

    print(f"\n{'='*110}")
    print(f"  {sport} — TOTALS RUNNING CLV")
    print(f"{'='*110}")
    print(f"  {'Week':12} {'Rd':>3} {'N':>3} {'Dir':>5} {'Line':>6} {'Close':>6} {'Move':>6} {'Taken':>6} {'ClsOdds':>8} {'CLV%':>7} {'Res':>5} {'Wk P&L':>9} {'WkCLV':>8} {'RunCLV':>8} {'RunP&L':>9}")
    print(f"  {'-'*12} {'-'*3} {'-'*3} {'-'*5} {'-'*6} {'-'*6} {'-'*6} {'-'*6} {'-'*8} {'-'*7} {'-'*5} {'-'*9} {'-'*8} {'-'*8} {'-'*9}")

    run_clv_sum = 0.0
    run_clv_n   = 0
    run_pnl     = 0.0
    all_bets    = []

    for week in sorted(by_week.keys()):
        bets = by_week[week]
        rnd  = bets[0]["round"]
        wk_pnl = 0.0
        wk_clvs = []

        for b in bets:
            clv   = flt(b.get("clv_pct"))
            p     = flt(b.get("pnl"))
            sel   = b.get("selection","")[:5]
            line  = b.get("line","")
            cl    = b.get("close_line","")
            move  = b.get("line_move","")
            odds  = b.get("odds_taken","")
            codds = b.get("close_odds","")
            res   = b.get("result","")[:1].upper()
            clv_s = f"{clv:+.2f}%" if clv is not None else "—"
            res_s = "W" if res == "W" else "L"
            pnl_s = f"${p:+.2f}" if p is not None else "—"

            print(f"  {week:12} {rnd:>3} {'1':>3} {sel:>5} {line:>6} {cl:>6} {move:>6} {odds:>6} {codds:>8} {clv_s:>7} {res_s:>5} {pnl_s:>9}")

            if clv is not None:
                wk_clvs.append(clv)
            if p is not None:
                wk_pnl += p
            all_bets.append({"clv": clv, "pnl": p, "result": res, "week": week})

        if wk_clvs:
            run_clv_sum += sum(wk_clvs)
            run_clv_n   += len(wk_clvs)
            run_pnl     += wk_pnl
            wk_avg  = sum(wk_clvs) / len(wk_clvs)
            run_avg = run_clv_sum / run_clv_n
            pos_n   = sum(1 for c in wk_clvs if c > 0)
            print(f"  {'':12} {'':>3} {len(wk_clvs):>3} {'↑' if wk_avg >= 0 else '↓':>5} {'':>6} {'':>6} {'':>6} {'':>6} {'':>8} "
                  f"  WEEK {wk_avg:+.2f}%  RUN {run_avg:+.2f}%  POS {pos_n}/{len(wk_clvs)}  Wk P&L ${wk_pnl:+.2f}  Run P&L ${run_pnl:+.2f}")
            print()

    # Summary
    clv_vals = [b["clv"] for b in all_bets if b["clv"] is not None]
    pnl_vals = [b["pnl"] for b in all_bets if b["pnl"] is not None]
    wins = sum(1 for b in all_bets if b["result"] == "W")
    losses = sum(1 for b in all_bets if b["result"] == "L")

    print(f"  {'─'*110}")
    print(f"  {sport} TOTALS SUMMARY")
    print(f"  Bets: {len(clv_vals)}  |  W/L: {wins}/{losses}  ({wins/(wins+losses)*100:.0f}% win rate)" if wins+losses else "")
    if clv_vals:
        avg_clv = sum(clv_vals) / len(clv_vals)
        pos_n   = sum(1 for c in clv_vals if c > 0)
        print(f"  Avg CLV: {avg_clv:+.2f}%  |  Positive CLV: {pos_n}/{len(clv_vals)} ({pos_n/len(clv_vals)*100:.0f}%)")
    if pnl_vals:
        total_pnl = sum(pnl_vals)
        total_stake = sum(abs(b["pnl"]) if b["result"] == "L" else 0 for b in all_bets if b["pnl"] is not None)
        # approx stake from pnl
        print(f"  Running P&L: ${total_pnl:+.2f}")


def main():
    rows = load()
    print(f"Loaded {len(rows)} totals bets")
    run_sport(rows, "NRL")
    run_sport(rows, "AFL")


if __name__ == "__main__":
    main()
