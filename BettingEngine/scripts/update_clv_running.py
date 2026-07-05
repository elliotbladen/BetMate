"""
update_clv_running.py
---------------------
Reads actual_bets_clv_2026.csv (per-bet CLV data) and actual_bets_2026.csv
(master bets ledger with week_ending), joins on bet_id, then writes two clean
running-total CLV files:

  data/clv/running/NRL_CLV_running_2026.csv
  data/clv/running/AFL_CLV_running_2026.csv

Also reads model_clv_supplement_nrl_2026.csv for rounds where no actual bets
were tracked (e.g. NRL R8, R9) — game-level model CLV only, no P&L.

Run this after updating actual_bets_clv_2026.csv with each week's closing lines.

Usage:
  uv run python scripts/update_clv_running.py
"""

import csv
import os
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CLV_FILE        = ROOT / "data/clv/running/actual_bets_clv_2026.csv"
BETS_FILE       = ROOT / "data/bets/actual_bets_2026.csv"
SUPPLEMENT_FILE = ROOT / "data/clv/running/model_clv_supplement_nrl_2026.csv"
OUT_DIR         = ROOT / "data/clv/running"


def load_week_endings() -> dict[str, dict]:
    """Return {bet_id: {week_ending, sport, round}} from master bets ledger."""
    result = {}
    with open(BETS_FILE, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            result[row["bet_id"]] = {
                "week_ending": row["week_ending"],
                "sport":       row["sport"],
                "round":       row["round"],
            }
    return result


def load_clv_bets() -> list[dict]:
    """Return rows from actual_bets_clv_2026.csv that have a clv_pct value."""
    rows = []
    with open(CLV_FILE, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if row.get("clv_pct", "").strip() not in ("", "None"):
                rows.append(row)
    return rows


def load_supplement() -> dict[str, list[dict]]:
    """
    Return {sport_upper: [{week_ending, round, clv, result}, ...]}
    from model_clv_supplement_nrl_2026.csv.
    Used for rounds where no actual bets were tracked.
    """
    result: dict[str, list[dict]] = defaultdict(list)
    if not SUPPLEMENT_FILE.exists():
        return result
    with open(SUPPLEMENT_FILE, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if row.get("clv_pct", "").strip() not in ("", "None"):
                result[row["sport"].upper()].append({
                    "week_ending": row["week_ending"],
                    "round":       row["round"],
                    "clv":         float(row["clv_pct"]),
                    "pnl":         0.0,
                    "result":      row.get("result", ""),
                })
    return result


def build_running(rows: list[dict], lookup: dict, sport_filter: str,
                  supplement: dict[str, list[dict]] | None = None) -> list[dict]:
    """
    Group bets by week_ending, compute per-week and running CLV stats.
    Returns one dict per week, sorted by week_ending.
    """
    # Group by week_ending
    weeks: dict[str, list] = defaultdict(list)

    # Seed with supplement data for rounds without actual tracked bets
    if supplement:
        for entry in supplement.get(sport_filter, []):
            weeks[entry["week_ending"]].append({
                "round":  entry["round"],
                "clv":    entry["clv"],
                "pnl":    entry["pnl"],
                "result": entry["result"],
            })

    for row in rows:
        meta = lookup.get(row["bet_id"], {})
        if meta.get("sport", "").upper() != sport_filter:
            continue
        week = meta.get("week_ending", "unknown")
        clv  = float(row["clv_pct"])
        pnl  = float(row["pnl"]) if row.get("pnl", "") not in ("", "None") else 0.0
        weeks[week].append({
            "round":  meta.get("round", "?"),
            "clv":    clv,
            "pnl":    pnl,
            "result": row.get("result", ""),
        })

    running_clv_sum  = 0.0
    running_clv_n    = 0
    running_pnl      = 0.0
    output = []

    for week in sorted(weeks.keys()):
        bets     = weeks[week]
        rnd      = bets[0]["round"]
        clv_vals = [b["clv"] for b in bets]
        pnl_vals = [b["pnl"] for b in bets]

        n             = len(clv_vals)
        positive_n    = sum(1 for c in clv_vals if c > 0)
        week_avg_clv  = sum(clv_vals) / n
        week_pnl      = sum(pnl_vals)
        wins          = sum(1 for b in bets if b["result"] == "win")
        losses        = sum(1 for b in bets if b["result"] == "loss")

        running_clv_sum += sum(clv_vals)
        running_clv_n   += n
        running_pnl     += week_pnl

        running_avg_clv = running_clv_sum / running_clv_n

        output.append({
            "week_ending":       week,
            "round":             rnd,
            "bets":              n,
            "positive_clv":      positive_n,
            "negative_clv":      n - positive_n,
            "pct_positive":      f"{positive_n / n * 100:.1f}%",
            "week_avg_clv_pct":  f"{week_avg_clv:+.2f}%",
            "running_avg_clv_pct": f"{running_avg_clv:+.2f}%",
            "week_wins":         wins,
            "week_losses":       losses,
            "week_pnl":          f"${week_pnl:+.2f}",
            "running_pnl":       f"${running_pnl:+.2f}",
        })

    return output


def write_csv(rows: list[dict], path: Path) -> None:
    if not rows:
        print(f"  No data for {path.name} — skipping")
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    print(f"  Written: {path.name} ({len(rows)} rounds)")


def print_summary(rows: list[dict], sport: str) -> None:
    if not rows:
        return
    last = rows[-1]
    total_bets = sum(r["bets"] for r in rows)
    total_pos  = sum(r["positive_clv"] for r in rows)
    print(f"\n{'='*50}")
    print(f"  {sport} CLV — 2026 Running Total")
    print(f"{'='*50}")
    print(f"  Rounds tracked : {len(rows)}")
    print(f"  Total bets     : {total_bets}")
    print(f"  Positive CLV   : {total_pos}/{total_bets} ({total_pos/total_bets*100:.1f}%)")
    print(f"  Running avg CLV: {last['running_avg_clv_pct']}")
    print(f"  Running P&L    : {last['running_pnl']}")
    print()
    print(f"  {'Week':12} {'Rd':>4} {'Bets':>5} {'+CLV':>5} {'Wk CLV':>9} {'Run CLV':>9} {'Wk P&L':>10} {'Run P&L':>10}")
    print(f"  {'-'*70}")
    for r in rows:
        print(f"  {r['week_ending']:12} {r['round']:>4} {r['bets']:>5} "
              f"{r['positive_clv']:>5} {r['week_avg_clv_pct']:>9} "
              f"{r['running_avg_clv_pct']:>9} {r['week_pnl']:>10} {r['running_pnl']:>10}")


def main():
    print("Loading data...")
    lookup     = load_week_endings()
    bets       = load_clv_bets()
    supplement = load_supplement()
    print(f"  {len(bets)} bets with CLV data found")
    supp_nrl = len(supplement.get("NRL", []))
    supp_afl = len(supplement.get("AFL", []))
    if supp_nrl or supp_afl:
        print(f"  Supplement: {supp_nrl} NRL game rows, {supp_afl} AFL game rows")

    nrl_rows = build_running(bets, lookup, "NRL", supplement)
    afl_rows = build_running(bets, lookup, "AFL", supplement)

    write_csv(nrl_rows, OUT_DIR / "NRL_CLV_running_2026.csv")
    write_csv(afl_rows, OUT_DIR / "AFL_CLV_running_2026.csv")

    print_summary(nrl_rows, "NRL")
    print_summary(afl_rows, "AFL")


if __name__ == "__main__":
    main()
