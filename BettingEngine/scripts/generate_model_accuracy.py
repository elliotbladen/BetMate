"""
generate_model_accuracy.py
--------------------------
Reads ml_comparison CLV files (which contain both 'normal' rules model rows
and 'ml' shadow rows per game) and generates clean per-round model accuracy
CSVs comparing model lines to market closing lines.

Purpose: end-of-season calibration — track whether rules model and ML shadow
are pricing efficiently vs the market (ideal = 0% bias across all markets).

Output:
  data/model_accuracy/nrl/NRL_MODEL_ACCURACY_R{rr}_{date}.csv
  data/model_accuracy/afl/AFL_MODEL_ACCURACY_R{rr}_{date}.csv
  data/model_accuracy/MODEL_ACCURACY_RUNNING_2026.csv

Columns per-round CSV:
  season, round, week_ending, date, home_team, away_team, market,
  rules_model, ml_model, market_open, market_close,
  rules_vs_open, rules_vs_close, ml_vs_open, ml_vs_close,
  actual, rules_vs_actual, ml_vs_actual

For H2H: values are home win probability % (1/home_odds * 100, raw implied).
For handicap/totals: values are in points.

Usage:
  uv run python scripts/generate_model_accuracy.py
"""

import csv
import math
from collections import defaultdict
from pathlib import Path

ROOT    = Path(__file__).resolve().parent.parent
CLV_DIR = ROOT / "data" / "clv"
OUT_DIR = ROOT / "data" / "model_accuracy"

# Maps each source CLV file → (sport, round_num, week_ending)
SOURCES = [
    (CLV_DIR / "nrl" / "NRL_CLV_R09_2026-04-28_ml_comparison.csv",  "NRL",  9,  "2026-04-28"),
    (CLV_DIR / "nrl" / "NRL_CLV_R10_2026-05-05_ml_comparison.csv",  "NRL", 10,  "2026-05-05"),
    (CLV_DIR / "nrl" / "NRL_CLV_R11_2026-05-19_ml_comparison.csv",  "NRL", 11,  "2026-05-12"),
    (CLV_DIR / "afl" / "AFL_CLV_R08_2026-05-05.csv",                "AFL",  8,  "2026-05-05"),
    (CLV_DIR / "afl" / "AFL_CLV_R09_2026-05-12.csv",                "AFL",  9,  "2026-05-12"),
]

# Sanity bounds for total-points values (outside = treat as N/A)
TOTAL_BOUNDS = {
    "NRL": (20, 90),
    "AFL": (80, 350),
}

HCAP_BOUNDS = {
    "NRL": (-60, 60),
    "AFL": (-100, 100),
}


def safe_float(val: str) -> float | None:
    try:
        f = float(val)
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None


def home_win_pct(odds: float) -> float:
    return round(100 / odds, 1)


def diff(a, b) -> str:
    if a is None or b is None or a == "" or b == "":
        return ""
    try:
        return f"{float(a) - float(b):+.2f}"
    except (TypeError, ValueError):
        return ""


def parse_file(path: Path, sport: str, round_num: int, week_ending: str) -> list[dict]:
    rows = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    # Group by (date, home_team, away_team, market)
    groups: dict[tuple, dict] = defaultdict(dict)
    for r in rows:
        key = (r["date"], r["home_team"], r["away_team"], r["market"])
        sig = r.get("signal", r.get("signal", "")).strip()
        groups[key][sig] = r

    total_lo, total_hi = TOTAL_BOUNDS[sport]
    hcap_lo, hcap_hi = HCAP_BOUNDS[sport]

    output = []
    for (date, home, away, market), sigs in sorted(groups.items()):
        normal = sigs.get("normal") or sigs.get("model")
        ml     = sigs.get("ml")
        mkt    = sigs.get("market")

        ref = normal or ml or mkt
        if not ref:
            continue

        actual_margin = safe_float(ref.get("actual_margin_home", ""))
        actual_total  = safe_float(ref.get("actual_total", ""))

        if market == "h2h":
            # ---- Rules model home win % ----
            rules_line = None
            if normal and normal.get("model_home_fair_odds"):
                v = safe_float(normal["model_home_fair_odds"])
                rules_line = home_win_pct(v) if v and v > 1 else None

            # ---- ML model home win % ----
            ml_line = None
            if ml and ml.get("model_home_fair_odds"):
                v = safe_float(ml["model_home_fair_odds"])
                ml_line = home_win_pct(v) if v and v > 1 else None

            # ---- Market open/close home win % ----
            mkt_open = mkt_close = None
            if mkt:
                sel = mkt.get("selection", "")
                is_home = (sel.strip() == home.strip())
                o = safe_float(mkt.get("open_odds", ""))
                c = safe_float(mkt.get("close_odds", ""))
                if o and o > 1:
                    mkt_open = round(100/o if is_home else 100 - 100/o, 1)
                if c and c > 1:
                    mkt_close = round(100/c if is_home else 100 - 100/c, 1)

            actual = None
            if actual_margin is not None:
                actual = 1.0 if actual_margin > 0 else (0.0 if actual_margin < 0 else 0.5)

        elif market == "handicap":
            def norm_hcap(row) -> float | None:
                if not row:
                    return None
                v = safe_float(row.get("model_number", ""))
                if v is None or not (hcap_lo <= v <= hcap_hi):
                    return None
                sel = row.get("selection", "").strip()
                return v if sel == home.strip() else -v

            rules_line = norm_hcap(normal)
            ml_line    = norm_hcap(ml)

            mkt_open = mkt_close = None
            if mkt:
                sel = mkt.get("selection", "").strip()
                is_home = (sel == home.strip())
                o = safe_float(mkt.get("open_number", ""))
                c = safe_float(mkt.get("close_number", ""))
                if o is not None:
                    mkt_open = o if is_home else -o
                if c is not None:
                    mkt_close = c if is_home else -c

            actual = actual_margin

        elif market == "total":
            def get_total(row) -> float | None:
                if not row:
                    return None
                v = safe_float(row.get("model_number", ""))
                return v if v is not None and total_lo <= v <= total_hi else None

            rules_line = get_total(normal)
            ml_line    = get_total(ml)

            mkt_open = mkt_close = None
            if mkt:
                o = safe_float(mkt.get("open_number", ""))
                c = safe_float(mkt.get("close_number", ""))
                mkt_open  = o if o is not None and total_lo <= o <= total_hi else None
                mkt_close = c if c is not None and total_lo <= c <= total_hi else None

            actual = actual_total

        else:
            continue

        output.append({
            "season":           ref.get("season", 2026),
            "round":            round_num,
            "week_ending":      week_ending,
            "date":             date,
            "home_team":        home,
            "away_team":        away,
            "market":           market,
            "rules_model":      "" if rules_line is None else rules_line,
            "ml_model":         "" if ml_line is None else ml_line,
            "market_open":      "" if mkt_open is None else mkt_open,
            "market_close":     "" if mkt_close is None else mkt_close,
            "rules_vs_open":    diff(rules_line, mkt_open),
            "rules_vs_close":   diff(rules_line, mkt_close),
            "ml_vs_open":       diff(ml_line, mkt_open),
            "ml_vs_close":      diff(ml_line, mkt_close),
            "actual":           "" if actual is None else actual,
            "rules_vs_actual":  diff(rules_line, actual),
            "ml_vs_actual":     diff(ml_line, actual),
        })

    return output


def write_csv(rows: list[dict], path: Path) -> None:
    if not rows:
        print(f"  No data — skipping {path.name}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    print(f"  Written: {path.name} ({len(rows)} rows)")


def stats(values: list[float]) -> tuple[float, float]:
    """Return (mean_bias, mae) or (nan, nan) if empty."""
    if not values:
        return float("nan"), float("nan")
    bias = sum(values) / len(values)
    mae  = sum(abs(v) for v in values) / len(values)
    return round(bias, 2), round(mae, 2)


def build_running(all_rounds: list[tuple]) -> list[dict]:
    """
    all_rounds: [(sport, round_num, week_ending, rows), ...]
    Returns one summary dict per round.
    """
    summary = []
    for sport, round_num, week_ending, rows in sorted(all_rounds, key=lambda x: (x[0], x[2])):
        def collect(market, col):
            vals = []
            for r in rows:
                if r["market"] != market:
                    continue
                v = safe_float(str(r.get(col, "")))
                if v is not None:
                    vals.append(v)
            return vals

        rh_bias, rh_mae = stats(collect("h2h",      "rules_vs_close"))
        mh_bias, mh_mae = stats(collect("h2h",      "ml_vs_close"))
        rk_bias, rk_mae = stats(collect("handicap", "rules_vs_close"))
        mk_bias, mk_mae = stats(collect("handicap", "ml_vs_close"))
        rt_bias, rt_mae = stats(collect("total",    "rules_vs_close"))
        mt_bias, mt_mae = stats(collect("total",    "ml_vs_close"))

        # vs actual
        rka_bias, rka_mae = stats(collect("handicap", "rules_vs_actual"))
        mka_bias, mka_mae = stats(collect("handicap", "ml_vs_actual"))
        rta_bias, rta_mae = stats(collect("total",    "rules_vs_actual"))
        mta_bias, mta_mae = stats(collect("total",    "ml_vs_actual"))

        games = len({(r["date"], r["home_team"], r["away_team"]) for r in rows})

        fmt = lambda v: "" if math.isnan(v) else f"{v:+.2f}"

        summary.append({
            "sport":                sport,
            "round":                round_num,
            "week_ending":          week_ending,
            "games":                games,
            # vs market close
            "rules_h2h_bias_pct":   fmt(rh_bias),
            "rules_h2h_mae_pct":    fmt(rh_mae),
            "ml_h2h_bias_pct":      fmt(mh_bias),
            "ml_h2h_mae_pct":       fmt(mh_mae),
            "rules_hcap_bias_pts":  fmt(rk_bias),
            "rules_hcap_mae_pts":   fmt(rk_mae),
            "ml_hcap_bias_pts":     fmt(mk_bias),
            "ml_hcap_mae_pts":      fmt(mk_mae),
            "rules_total_bias_pts": fmt(rt_bias),
            "rules_total_mae_pts":  fmt(rt_mae),
            "ml_total_bias_pts":    fmt(mt_bias),
            "ml_total_mae_pts":     fmt(mt_mae),
            # vs actual result
            "rules_hcap_vs_actual_bias": fmt(rka_bias),
            "rules_hcap_vs_actual_mae":  fmt(rka_mae),
            "ml_hcap_vs_actual_bias":    fmt(mka_bias),
            "ml_hcap_vs_actual_mae":     fmt(mka_mae),
            "rules_total_vs_actual_bias": fmt(rta_bias),
            "rules_total_vs_actual_mae":  fmt(rta_mae),
            "ml_total_vs_actual_bias":    fmt(mta_bias),
            "ml_total_vs_actual_mae":     fmt(mta_mae),
        })
    return summary


def print_summary(summary: list[dict]) -> None:
    if not summary:
        return
    print(f"\n{'='*90}")
    print("  MODEL ACCURACY — 2026 Running Summary (vs Market Close)")
    print(f"{'='*90}")
    hdr = f"  {'Sp':3} {'Rd':>3} {'Week':12} {'G':>3} | {'RuH2H':>7} {'MLH2H':>7} | {'RuHcap':>8} {'MLHcap':>8} | {'RuTot':>8} {'MLTot':>8}"
    print(hdr)
    print(f"  {'-'*88}")
    for r in summary:
        print(
            f"  {r['sport']:3} {r['round']:>3} {r['week_ending']:12} {r['games']:>3} | "
            f"{r['rules_h2h_bias_pct']:>7} {r['ml_h2h_bias_pct']:>7} | "
            f"{r['rules_hcap_bias_pts']:>8} {r['ml_hcap_bias_pts']:>8} | "
            f"{r['rules_total_bias_pts']:>8} {r['ml_total_bias_pts']:>8}"
        )
    print()
    print("  Bias = rules_model - market_close. +ve = model overestimates home/total.")
    print("  Ideal bias = 0.00 across all markets.\n")


def main():
    all_rounds = []

    for path, sport, round_num, week_ending in SOURCES:
        if not path.exists():
            print(f"  MISSING: {path.name} — skipping")
            continue
        print(f"Processing {path.name}...")
        rows = parse_file(path, sport, round_num, week_ending)

        sport_lo = sport.lower()
        out_path = OUT_DIR / sport_lo / f"{sport}_MODEL_ACCURACY_R{round_num:02d}_{week_ending}.csv"
        write_csv(rows, out_path)
        all_rounds.append((sport, round_num, week_ending, rows))

    summary = build_running(all_rounds)
    write_csv(summary, OUT_DIR / "MODEL_ACCURACY_RUNNING_2026.csv")
    print_summary(summary)


if __name__ == "__main__":
    main()
