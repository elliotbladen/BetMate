#!/usr/bin/env python3
"""Summarize weekly NRL/AFL CLV reports with cumulative averages."""

from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
REPORT_SOURCES = {
    "NRL": ROOT / "outputs" / "nrl_weekly_review" / "reports",
    "AFL": ROOT / "outputs" / "afl_weekly_review" / "reports",
}
DEFAULT_OUT = ROOT / "outputs" / "clv_running" / "running_clv_summary.csv"


def as_float(raw: str | None) -> float | None:
    if raw in ("", None):
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def report_files(sport: str) -> list[Path]:
    folder = REPORT_SOURCES[sport]
    if not folder.exists():
        return []
    if sport == "NRL":
        return sorted(folder.glob("r*_nrl_ml_comparison_*.csv"))
    return sorted(folder.glob("r*_afl_ml_clv_comparison_*.csv"))


def round_from_path(path: Path) -> int:
    match = re.search(r"r(\d+)_", path.name)
    if not match:
        raise ValueError(f"Could not parse round from {path}")
    return int(match.group(1))


def season_from_path(path: Path) -> int:
    match = re.search(r"_(\d{4})\.csv$", path.name)
    if not match:
        raise ValueError(f"Could not parse season from {path}")
    return int(match.group(1))


def load_summary_rows(sports: list[str]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, int, int, str, str], dict[str, object]] = {}
    for sport in sports:
        for path in report_files(sport):
            rnd = round_from_path(path)
            season = season_from_path(path)
            with path.open(newline="", encoding="utf-8-sig") as fh:
                for row in csv.DictReader(fh):
                    signal = row.get("signal", "")
                    market = row.get("market", "")
                    if signal not in {"normal", "ml", "market", "model"} or market not in {"h2h", "handicap", "total"}:
                        continue
                    if signal == "model":
                        signal = "normal"
                    key = (sport, season, rnd, signal, market)
                    rec = grouped.setdefault(
                        key,
                        {
                            "sport": sport,
                            "season": season,
                            "round": rnd,
                            "signal": signal,
                            "market": market,
                            "clv_count": 0,
                            "clv_sum": 0.0,
                            "positive_clv": 0,
                            "negative_clv": 0,
                            "wins": 0,
                            "losses": 0,
                            "pushes": 0,
                            "source_file": path.name,
                        },
                    )
                    clv = as_float(row.get("clv"))
                    if clv is not None:
                        rec["clv_count"] = int(rec["clv_count"]) + 1
                        rec["clv_sum"] = float(rec["clv_sum"]) + clv
                        if clv > 0:
                            rec["positive_clv"] = int(rec["positive_clv"]) + 1
                        elif clv < 0:
                            rec["negative_clv"] = int(rec["negative_clv"]) + 1
                    result = row.get("result", "")
                    if result == "win":
                        rec["wins"] = int(rec["wins"]) + 1
                    elif result == "loss":
                        rec["losses"] = int(rec["losses"]) + 1
                    elif result == "push":
                        rec["pushes"] = int(rec["pushes"]) + 1

    rows = []
    for rec in grouped.values():
        n = int(rec["clv_count"])
        avg = float(rec["clv_sum"]) / n if n else None
        rec["round_avg_clv"] = round(avg, 4) if avg is not None else ""
        rec["clv_sum"] = round(float(rec["clv_sum"]), 4)
        rows.append(rec)
    rows.sort(key=lambda r: (str(r["sport"]), int(r["season"]), int(r["round"]), str(r["signal"]), str(r["market"])))
    add_running_averages(rows)
    return rows


def add_running_averages(rows: list[dict[str, object]]) -> None:
    by_key: dict[tuple[str, int, str, str], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        by_key[(str(row["sport"]), int(row["season"]), str(row["signal"]), str(row["market"]))].append(row)

    for group in by_key.values():
        group.sort(key=lambda r: int(r["round"]))
        total = 0.0
        rounds = 0
        for row in group:
            if row["round_avg_clv"] != "":
                total += float(row["round_avg_clv"])
                rounds += 1
            row["running_avg_clv"] = round(total / rounds, 4) if rounds else ""


def write_rows(rows: list[dict[str, object]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "sport", "season", "round", "signal", "market",
        "round_avg_clv", "running_avg_clv",
        "clv_count", "positive_clv", "negative_clv",
        "wins", "losses", "pushes", "clv_sum", "source_file",
    ]
    with out_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def print_summary(rows: list[dict[str, object]], out_path: Path) -> None:
    print(f"Written {len(rows)} rows -> {out_path}")
    for row in rows:
        if row["signal"] == "normal":
            print(
                f"{row['sport']} R{row['round']} {row['market']:<8} "
                f"normal round_avg={row['round_avg_clv']} running_avg={row['running_avg_clv']} "
                f"W-L-P={row['wins']}-{row['losses']}-{row['pushes']}"
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build cumulative CLV average summary across NRL and AFL weekly reports.")
    parser.add_argument("--sport", choices=["NRL", "AFL", "ALL"], default="ALL")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    sports = ["NRL", "AFL"] if args.sport == "ALL" else [args.sport]
    rows = load_summary_rows(sports)
    write_rows(rows, args.out)
    print_summary(rows, args.out)


if __name__ == "__main__":
    main()
