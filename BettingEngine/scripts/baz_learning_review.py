#!/usr/bin/env python
"""Write a lightweight Baz learning review from the local pricing database."""

from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any


def _rows(conn: sqlite3.Connection, query: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
    conn.row_factory = sqlite3.Row
    return list(conn.execute(query, params))


def _avg(values: list[float | None]) -> float | None:
    usable = [float(value) for value in values if value is not None]
    return round(mean(usable), 3) if usable else None


def _pct(values: list[int | None]) -> float | None:
    usable = [int(value) for value in values if value is not None]
    return round(sum(usable) / len(usable), 3) if usable else None


def _count(conn: sqlite3.Connection, table: str) -> int:
    return int(conn.execute(f"select count(*) from {table}").fetchone()[0])


def build_review(db_path: Path, season: int | None, round_number: int | None) -> dict[str, Any]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    filters = []
    params: list[Any] = []
    if season is not None:
        filters.append("season = ?")
        params.append(season)
    if round_number is not None:
        filters.append("round_number = ?")
        params.append(round_number)
    where = f"where {' and '.join(filters)}" if filters else ""

    tier_rows = _rows(conn, f"select * from tier2_performance {where}", tuple(params))
    completed_tier_rows = [row for row in tier_rows if row["actual_margin"] is not None]

    shadow_rows = _rows(conn, f"select * from ml_shadow_predictions {where}", tuple(params))
    completed_shadow_rows = [row for row in shadow_rows if row["actual_margin"] is not None]

    total_errors = []
    for row in completed_tier_rows:
        if row["actual_home_score"] is not None and row["actual_away_score"] is not None:
            actual_total = row["actual_home_score"] + row["actual_away_score"]
            total_errors.append(abs(row["final_total"] - actual_total))

    review = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "database": str(db_path),
        "scope": {
            "season": season,
            "round": round_number,
        },
        "data_coverage": {
            "tier2_rows": len(tier_rows),
            "tier2_completed_rows": len(completed_tier_rows),
            "ml_shadow_rows": len(shadow_rows),
            "ml_shadow_completed_rows": len(completed_shadow_rows),
            "signals": _count(conn, "signals"),
            "bets": _count(conn, "bets"),
            "bankroll_log": _count(conn, "bankroll_log"),
        },
        "rules_model": {
            "t1_margin_mae": _avg([row["t1_abs_error"] for row in completed_tier_rows]),
            "final_margin_mae": _avg([row["t12_abs_error"] for row in completed_tier_rows]),
            "avg_margin_improvement": _avg([row["abs_improvement"] for row in completed_tier_rows]),
            "final_total_mae": _avg(total_errors),
            "t1_winner_accuracy": _pct([row["t1_winner_correct"] for row in completed_tier_rows]),
            "final_winner_accuracy": _pct([row["final_winner_correct"] for row in completed_tier_rows]),
            "t2_direction_accuracy": _pct([row["t2_direction_correct"] for row in completed_tier_rows]),
        },
        "ml_shadow": {
            "ml_margin_mae": _avg([row["ml_margin_error"] for row in completed_shadow_rows]),
            "rules_margin_mae": _avg([row["rules_margin_error"] for row in completed_shadow_rows]),
            "ml_total_mae": _avg([row["ml_total_error"] for row in completed_shadow_rows]),
            "rules_total_mae": _avg([row["rules_total_error"] for row in completed_shadow_rows]),
            "ml_h2h_accuracy": _pct([row["ml_h2h_correct"] for row in completed_shadow_rows]),
            "rules_h2h_accuracy": _pct([row["rules_h2h_correct"] for row in completed_shadow_rows]),
        },
        "blockers": [],
        "recommendations": [],
    }

    if review["data_coverage"]["signals"] == 0:
        review["blockers"].append("signals table is empty; Baz cannot produce official bet/watch/pass recommendations yet")
    if review["data_coverage"]["bets"] == 0 or review["data_coverage"]["bankroll_log"] == 0:
        review["blockers"].append("bets/bankroll_log are empty; ROI, CLV by stake, and staking feedback loops are not active")
    if review["data_coverage"]["ml_shadow_rows"] and not review["data_coverage"]["ml_shadow_completed_rows"]:
        review["blockers"].append("ml_shadow_predictions exist but actual outcomes have not been backfilled")
    if not completed_tier_rows:
        review["blockers"].append("no completed tier2_performance rows in scope")

    if completed_tier_rows:
        review["recommendations"].append("use this report as the weekly calibration baseline before changing model weights")
    if review["data_coverage"]["signals"] == 0:
        review["recommendations"].append("wire prepare_round.py into model_runs and signals before building MCP tools")

    conn.close()
    return review


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Baz pricing learning review")
    parser.add_argument("--db", default="data/model.db")
    parser.add_argument("--season", type=int)
    parser.add_argument("--round", dest="round_number", type=int)
    parser.add_argument("--output", default="outputs/baz/latest_learning_review.json")
    args = parser.parse_args()

    review = build_review(Path(args.db), args.season, args.round_number)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(review, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(output_path), "blockers": review["blockers"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
