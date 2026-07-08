"""
clv_closing_line_sim.py
-----------------------
"What if I had waited and bet the closing line/odds?"

For each totals bet:
  - Recalculates P&L using close_odds instead of odds_taken (same win/loss result)
  - Shows the difference: did betting early cost or save money?
  - Summarises by sport and overall

If close_odds > odds_taken  → you paid TOO early (market lengthened, you got ripped)
If close_odds < odds_taken  → you got great early value (market shortened before close)

Usage:
  uv run python scripts/clv_closing_line_sim.py
"""
import csv
from collections import defaultdict
from pathlib import Path

ROOT      = Path(__file__).resolve().parent.parent
CLV_FILE  = ROOT / "data/clv/running/actual_bets_clv_2026.csv"
BETS_FILE = ROOT / "data/bets/actual_bets_2026.csv"


def flt(v, default=None):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def main():
    bets_meta = {}
    with open(BETS_FILE, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            bets_meta[r["bet_id"]] = {
                "week_ending": r["week_ending"],
                "sport":       r["sport"].upper(),
                "round":       r["round"],
                "stake":       flt(r.get("stake")),
            }

    rows = []
    with open(CLV_FILE, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if r.get("market") != "total":
                continue
            meta = bets_meta.get(r["bet_id"], {})
            r["sport_upper"]  = meta.get("sport", "")
            r["week_ending"]  = meta.get("week_ending", "")
            r["round_num"]    = meta.get("round", "")
            r["stake"]        = meta.get("stake")
            rows.append(r)

    for sport in ("NRL", "AFL"):
        sport_rows = [r for r in rows if r["sport_upper"] == sport]
        if not sport_rows:
            continue

        print(f"\n{'='*108}")
        print(f"  {sport} TOTALS — ACTUAL vs CLOSING LINE  (same outcome, close_odds used for P&L)")
        print(f"{'='*108}")
        print(f"  {'Game':<24} {'Rd':>3} {'Dir':>5} {'Line':>6} {'CloseLn':>8} {'Taken':>7} {'ClsOdd':>8} "
              f"{'Res':>4} {'Actual P&L':>11} {'@ Close P&L':>13} {'Diff':>9} {'Judgment':>16}")
        print(f"  {'-'*24} {'-'*3} {'-'*5} {'-'*6} {'-'*8} {'-'*7} {'-'*8} "
              f"{'-'*4} {'-'*11} {'-'*13} {'-'*9} {'-'*16}")

        total_actual = 0.0
        total_close  = 0.0
        total_stake  = 0.0

        for r in sport_rows:
            match      = r.get("match","")
            home, away = match.split(" v ") if " v " in match else (match, "")
            short      = f"{home[:10]} v {away[:10]}"
            rnd        = r["round_num"]
            sel        = r.get("selection","")[:5]
            line       = r.get("line","")
            close_line = r.get("close_line","")
            taken      = flt(r.get("odds_taken"))
            close_odd  = flt(r.get("close_odds"))
            result     = r.get("result","").upper()[:1]
            pnl_actual = flt(r.get("pnl"), 0.0)
            stake      = r["stake"]

            # Recalculate P&L at close odds, same win/loss
            if stake is None and taken and pnl_actual is not None:
                stake = abs(pnl_actual) / (taken - 1) if result == "W" else abs(pnl_actual)

            if stake and close_odd and result == "W":
                pnl_close = round((close_odd - 1) * stake, 2)
            elif stake and result == "L":
                pnl_close = -stake
            else:
                pnl_close = None

            diff = round(pnl_close - pnl_actual, 2) if pnl_close is not None else None

            # Judgment: was betting early good or bad?
            if taken and close_odd:
                if close_odd > taken + 0.04:
                    judgment = "WAIT NEXT TIME"   # market lengthened — we paid too early
                elif close_odd < taken - 0.04:
                    judgment = "GOOD EARLY BET"   # market shortened — we got value
                else:
                    judgment = "NO DIFFERENCE"
            else:
                judgment = "—"

            actual_s = f"${pnl_actual:+.2f}" if pnl_actual is not None else "—"
            close_s  = f"${pnl_close:+.2f}"  if pnl_close  is not None else "—"
            diff_s   = f"${diff:+.2f}"        if diff        is not None else "—"
            taken_s  = f"{taken:.2f}"  if taken     else "—"
            close_s2 = f"{close_odd:.2f}" if close_odd else "—"

            print(f"  {short:<24} {rnd:>3} {sel:>5} {line:>6} {close_line:>8} {taken_s:>7} {close_s2:>8} "
                  f"{result:>4} {actual_s:>11} {close_s:>13} {diff_s:>9} {judgment:>16}")

            if pnl_actual is not None: total_actual += pnl_actual
            if pnl_close  is not None: total_close  += pnl_close
            if stake:                  total_stake  += stake

        diff_total = total_close - total_actual
        roi_actual = total_actual / total_stake * 100 if total_stake else 0
        roi_close  = total_close  / total_stake * 100 if total_stake else 0

        print(f"\n  {'─'*108}")
        print(f"  {sport} TOTALS TOTALS:")
        print(f"    Actual P&L  (odds taken):   ${total_actual:+.2f}  ({roi_actual:+.1f}% ROI)")
        print(f"    Closing P&L (close odds):   ${total_close:+.2f}  ({roi_close:+.1f}% ROI)")
        print(f"    Difference (close - actual): ${diff_total:+.2f}  "
              f"({'waiting would have made more' if diff_total > 0 else 'betting early was BETTER'})")

        # Count judgments
        waits = sum(1 for r in sport_rows
                    if flt(r.get("close_odds"),0) > flt(r.get("odds_taken"),0) + 0.04)
        goods = sum(1 for r in sport_rows
                    if flt(r.get("close_odds"),0) < flt(r.get("odds_taken"),0) - 0.04)
        flat  = len(sport_rows) - waits - goods
        print(f"    'WAIT NEXT TIME' signals: {waits}/{len(sport_rows)}  |  "
              f"'GOOD EARLY BET': {goods}/{len(sport_rows)}  |  Flat: {flat}/{len(sport_rows)}")


if __name__ == "__main__":
    main()
