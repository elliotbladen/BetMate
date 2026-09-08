"""
score_model_selections.py
-------------------------
Score a week's MODEL-VS-MARKET selections (paper bets, no stake placed) against
the AusSportsBetting closing workbooks.

Input : data/bets/model_selections/{week}_{tags}.csv
Output: outputs/results/{sport}_{round}_model_vs_market_{date}.{csv,md}
        data/clv/running/model_clv_supplement_{sport}_2026.csv  (appended)

CLV convention matches the rest of the engine:
  h2h              → price CLV      = odds_taken / close_odds - 1
  handicap, totals → line-adjusted CLV via scripts/compute_line_adjusted_clv
                     (closing line + sigma → fair price, then price CLV vs that)

Stake per selection comes from the `stake_u` column (default 1.00 unit).

Selections carry a `placed` flag. Headline ROI/CLV and the CLV supplement cover
PLACED bets only; unplaced rows are still scored and reported separately as
model candidates, so the "what if we had taken the whole card" record survives.

Usage:
  python scripts/score_model_selections.py --file data/bets/model_selections/<file>.csv
"""

from __future__ import annotations

import argparse
import csv
import math
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent

WORKBOOKS = {
    "NRL": ROOT / "outputs/nrl_weekly_review/historical/latest.xlsx",
    "AFL": ROOT / "outputs/afl_weekly_review/historical/latest.xlsx",
}

# from scripts/compute_line_adjusted_clv.py — derived from AusSportsBetting closings
SIGMA = {
    "NRL": {"margin": 17.30, "total": 12.80},
    "AFL": {"margin": 32.70, "total": 27.49},
}
VIG_MULTIPLIER = 2 / 1.90  # standard 1.90/1.90 two-way market → 5.26% vig

DEFAULT_STAKE_U = 1.0


def norm_cdf(x: float) -> float:
    return 0.5 * math.erfc(-x / math.sqrt(2))


def fair_close_from_line(bet_line: float, close_line: float, sigma: float,
                         direction: str) -> tuple[float, float]:
    """Closing line + sigma → (fair odds incl. vig, cover probability)."""
    if direction in ("handicap", "under"):
        z = (bet_line - close_line) / sigma
    else:  # over
        z = (close_line - bet_line) / sigma
    p = min(0.999, max(0.001, norm_cdf(z)))
    return (1.0 / p) / VIG_MULTIPLIER, p


def load_workbook(sport: str) -> pd.DataFrame:
    df = pd.read_excel(WORKBOOKS[sport], skiprows=1)
    df["D"] = pd.to_datetime(df["Date"], errors="coerce", dayfirst=True)
    return df


def find_game(df: pd.DataFrame, home: str, away: str, week_ending: str) -> pd.Series:
    lo = pd.Timestamp(week_ending) - pd.Timedelta(days=8)
    hi = pd.Timestamp(week_ending) + pd.Timedelta(days=2)
    m = df[(df.D >= lo) & (df.D <= hi) &
           (df["Home Team"] == home) & (df["Away Team"] == away)]
    if m.empty:
        raise SystemExit(f"No {home} v {away} found between {lo.date()} and {hi.date()}")
    return m.iloc[0]


def score(row: dict, g: pd.Series, sport: str) -> dict:
    hs, as_ = float(g["Home Score"]), float(g["Away Score"])
    total = hs + as_
    market = row["market"]
    side = row["side"]
    odds = float(row["odds_taken"])
    line = float(row["line"]) if row["line"] else None

    if market == "h2h":
        is_home = side == "H"
        margin = (hs - as_) if is_home else (as_ - hs)
        won = margin > 0
        close_odds = float(g["Home Odds Close"] if is_home else g["Away Odds Close"])
        close_line = None
        clv = (odds / close_odds - 1) * 100
        clv_line = None
        basis = "price"
    elif market == "handicap":
        is_home = side == "H"
        margin = (hs - as_) if is_home else (as_ - hs)
        won = (margin + line) > 0
        close_line = float(g["Home Line Close"] if is_home else g["Away Line Close"])
        fair, _ = fair_close_from_line(line, close_line, SIGMA[sport]["margin"], "handicap")
        close_odds = fair
        clv = (odds / fair - 1) * 100
        clv_line = line - close_line
        basis = "line-adj"
    else:  # total
        margin = hs - as_
        won = (total > line) if side == "over" else (total < line)
        close_line = float(g["Total Score Close"])
        fair, _ = fair_close_from_line(line, close_line, SIGMA[sport]["total"], side)
        close_odds = fair
        clv = (odds / fair - 1) * 100
        clv_line = (close_line - line) if side == "over" else (line - close_line)
        basis = "line-adj"

    stake = float(row.get("stake_u") or DEFAULT_STAKE_U) or DEFAULT_STAKE_U
    pnl = stake * (odds - 1) if won else -stake
    return {
        "placed": row.get("placed", "yes").strip().lower(),
        "sport": sport,
        "round": row["round"],
        "game": f"{row['home_team']} v {row['away_team']}",
        "market": market,
        "selection": row["selection"] + (f" ({line:+g})" if line is not None else ""),
        "odds_taken": odds,
        "close_odds": round(close_odds, 3),
        "line": line,
        "close_line": close_line,
        "clv_basis": basis,
        "clv_pct": round(clv, 2),
        "clv_line": round(clv_line, 1) if clv_line is not None else None,
        "score": f"{int(hs)}-{int(as_)}",
        "total": int(total),
        "result": "win" if won else "loss",
        "stake_u": stake,
        "pnl_u": round(pnl, 3),
    }


def summarise(rows: list[dict]) -> dict | None:
    n = len(rows)
    if n == 0:
        return None
    wins = sum(1 for r in rows if r["result"] == "win")
    staked = sum(r["stake_u"] for r in rows)
    pnl = sum(r["pnl_u"] for r in rows)
    clvs = [r["clv_pct"] for r in rows]
    return {
        "bets": n,
        "wins": wins,
        "losses": n - wins,
        "strike_pct": round(wins / n * 100, 1),
        "staked_u": round(staked, 2),
        "pnl_u": round(pnl, 3),
        "roi_pct": round(pnl / staked * 100, 2),
        "avg_clv_pct": round(sum(clvs) / n, 2),
        "positive_clv": sum(1 for c in clvs if c > 0),
        "pct_positive_clv": round(sum(1 for c in clvs if c > 0) / n * 100, 1),
    }


def _table(rows: list[dict]) -> list[str]:
    L = ["| Market | Selection | Odds | Close | CLV % | CLV line | Score | Result | P&L (u) |",
         "|---|---|---:|---:|---:|---:|---:|:--:|---:|"]
    for r in rows:
        cl = f"{r['clv_line']:+g}" if r["clv_line"] is not None else "—"
        tick = "✅" if r["result"] == "win" else "❌"
        L.append(f"| {r['market']} | {r['selection']} | {r['odds_taken']:.2f} | "
                 f"{r['close_odds']:.2f} | {r['clv_pct']:+.2f}% | {cl} | {r['score']} | "
                 f"{tick} | {r['pnl_u']:+.2f} |")
    return L


def _summary_block(title: str, s: dict) -> list[str]:
    return ["", f"## {title}", "",
            f"- Bets: **{s['bets']}** ({s['wins']}W / {s['losses']}L, {s['strike_pct']}% strike)",
            f"- Stake: {s['staked_u'] / s['bets']:.2f}u per bet",
            f"- Staked: {s['staked_u']:.2f}u — P&L: **{s['pnl_u']:+.3f}u**",
            f"- **ROI: {s['roi_pct']:+.2f}%**",
            f"- **Average CLV: {s['avg_clv_pct']:+.2f}%** "
            f"({s['positive_clv']}/{s['bets']} positive, {s['pct_positive_clv']}%)"]


def write_markdown(path: Path, sport: str, rnd: str, week_ending: str,
                   placed: list[dict], unplaced: list[dict]) -> None:
    L = [f"# {sport} — model vs market, round {rnd} (week ending {week_ending})", "",
         "Stake per selection comes from the `stake_u` column (default 1.00 unit). CLV for handicap and totals is",
         "line-adjusted (closing line + sigma → fair price); H2H is price CLV.", "",
         "## Placed bets", ""]
    L += _table(placed)
    L += _summary_block("Placed — summary", summarise(placed))
    if unplaced:
        L += ["", "---", "", "## Model candidates not backed", "",
              "Saved on the same card but not taken. Scored for model-vs-market record",
              "only — excluded from the headline numbers and from the CLV supplement.", ""]
        L += _table(unplaced)
        L += _summary_block("Not backed — summary", summarise(unplaced))
    L.append("")
    path.write_text("\n".join(L), encoding="utf-8")


def append_supplement(sport: str, week_ending: str, rows: list[dict]) -> Path:
    path = ROOT / f"data/clv/running/model_clv_supplement_{sport.lower()}_2026.csv"
    header = ["week_ending", "sport", "round", "game", "market", "clv_pct", "result"]
    exists = path.exists()
    existing = set()
    if exists:
        with open(path, newline="", encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                existing.add((r["week_ending"], r["game"], r["market"]))
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=header)
        if not exists:
            w.writeheader()
        for r in rows:
            key = (week_ending, r["game"], r["market"])
            if key in existing:
                continue
            w.writerow({"week_ending": week_ending, "sport": sport, "round": r["round"],
                        "game": r["game"], "market": r["market"],
                        "clv_pct": r["clv_pct"], "result": r["result"]})
    return path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True, type=Path)
    ap.add_argument("--as-of", default=date.today().isoformat())
    args = ap.parse_args()

    with open(args.file, newline="", encoding="utf-8-sig") as f:
        sel = list(csv.DictReader(f))

    books = {s: load_workbook(s) for s in {r["sport"] for r in sel}}
    out_dir = ROOT / "outputs/results"
    out_dir.mkdir(parents=True, exist_ok=True)

    by_sport: dict[str, list[dict]] = {}
    for r in sel:
        g = find_game(books[r["sport"]], r["home_team"], r["away_team"], r["week_ending"])
        by_sport.setdefault(r["sport"], []).append(score(r, g, r["sport"]))

    for sport, rows in by_sport.items():
        rnd = rows[0]["round"]
        week_ending = sel[0]["week_ending"]
        placed = [r for r in rows if r["placed"] == "yes"]
        unplaced = [r for r in rows if r["placed"] != "yes"]
        if not placed:
            print(f"  {sport}: no placed bets — skipping")
            continue
        s = summarise(placed)
        stem = f"{sport.lower()}_r{rnd.lower()}_model_vs_market_{args.as_of}"
        csv_path = out_dir / f"{stem}.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(placed + unplaced)
        write_markdown(out_dir / f"{stem}.md", sport, rnd, week_ending, placed, unplaced)
        supp = append_supplement(sport, week_ending, placed)

        print(f"\n=== {sport} R{rnd} — model vs market (placed) ===")
        for r in placed:
            print(f"  {r['result']:<4} {r['selection']:<34} @{r['odds_taken']:.2f} "
                  f"close {r['close_odds']:.2f}  CLV {r['clv_pct']:+7.2f}%  "
                  f"P&L {r['pnl_u']:+.2f}u")
        print(f"  {'-'*84}")
        print(f"  {s['bets']} bets | {s['wins']}W-{s['losses']}L ({s['strike_pct']}%) | "
              f"ROI {s['roi_pct']:+.2f}% | avg CLV {s['avg_clv_pct']:+.2f}% "
              f"({s['positive_clv']}/{s['bets']} +ve)")
        if unplaced:
            u = summarise(unplaced)
            print(f"  [not backed] {u['bets']} candidates | {u['wins']}W-{u['losses']}L | "
                  f"ROI {u['roi_pct']:+.2f}% | avg CLV {u['avg_clv_pct']:+.2f}%")
        print(f"  written: {csv_path.relative_to(ROOT)}")
        print(f"           {(out_dir / (stem + '.md')).relative_to(ROOT)}")
        print(f"           {supp.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
