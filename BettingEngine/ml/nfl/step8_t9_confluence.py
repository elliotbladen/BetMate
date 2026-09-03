"""NFL T9 matrix confluence: independent-family agreement, never vote stacking."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
T8 = ROOT / "data/nfl/predictions/step8_t8_market_disagreement.csv"
TIERS = ROOT / "data/nfl/predictions/step8_tier_ablations.csv"
WEATHER = ROOT / "data/nfl/predictions/step8_t6_weather_oracle.csv"
PREDICTIONS = ROOT / "data/nfl/predictions/step8_t9_confluence.csv"
REPORT = ROOT / "ml/nfl/reports/step8_t9_confluence.json"


def confluence_status(signals: list[dict[str, Any]], required_families: int = 3) -> dict[str, Any]:
    """Collapse correlated rows by family and require directional agreement."""
    usable = [s for s in signals if s.get("fresh", False) and s.get("confidence", 0) > 0 and s.get("direction") in {-1, 1}]
    by_family: dict[str, list[dict[str, Any]]] = {}
    for signal in usable:
        by_family.setdefault(str(signal["family"]), []).append(signal)
    collapsed = []
    for family, rows in by_family.items():
        weighted = sum(float(r["direction"]) * float(r["confidence"]) for r in rows)
        if weighted:
            collapsed.append({"family": family, "direction": int(np.sign(weighted)),
                              "confidence": min(1.0, max(float(r["confidence"]) for r in rows))})
    directions = {row["direction"] for row in collapsed}
    if len(collapsed) < required_families:
        status, direction = "insufficient_distinct_families", 0
    elif len(directions) != 1:
        status, direction = "conflict_abstain", 0
    else:
        status, direction = "watch_confluence", collapsed[0]["direction"]
    return {"status": status, "direction": direction, "distinct_families": len(collapsed),
            "families": [row["family"] for row in collapsed], "betting_action": "none"}


def _graded(rows: pd.DataFrame, direction: pd.Series, move: str, cover: str | None = None) -> dict[str, Any]:
    moved = rows[move].ne(0) & rows[move].notna()
    correct = np.sign(rows.loc[moved, move]) == direction.loc[moved]
    result: dict[str, Any] = {"games": len(rows), "moving_line_games": int(moved.sum()),
                              "closing_direction_accuracy": float(correct.mean()) if len(correct) else None,
                              "mean_clv_points": float((direction * rows[move]).mean())}
    if cover:
        graded = direction * rows[cover]
        wins, losses, pushes = int(graded.gt(0).sum()), int(graded.lt(0).sum()), int(graded.eq(0).sum())
        result.update({"wins": wins, "losses": losses, "pushes": pushes,
                       "win_rate_ex_pushes": wins / (wins + losses) if wins + losses else None,
                       "warning": "synthetic opener grading; exact prices and true-opener provenance unavailable"})
    return result


def run_audit() -> tuple[pd.DataFrame, dict]:
    market = pd.read_csv(T8)
    tiers = pd.read_csv(TIERS)[["game_id", "t1_core", "t1_plus_t2_t3"]]
    spread = market.merge(tiers, on="game_id", validate="one_to_one")
    spread["personnel_increment"] = spread.t1_plus_t2_t3 - spread.t1_core
    spread_direction = np.sign(spread.ridge_spread_disagreement)
    spread["spread_confluence"] = (
        spread.ridge_spread_disagreement.abs().ge(2.0)
        & spread.tree_spread_disagreement.abs().ge(2.0)
        & np.sign(spread.tree_spread_disagreement).eq(spread_direction)
        & np.sign(spread.personnel_increment).eq(spread_direction)
        & spread_direction.ne(0)
    )
    spread["home_cover_margin_at_open"] = spread.margin + spread.spread_home_open

    weather = pd.read_csv(WEATHER)[["game_id", "t1_core", "t1_plus_t6_oracle"]]
    total = market.merge(weather, on="game_id", validate="one_to_one")
    total["weather_increment"] = total.t1_plus_t6_oracle - total.t1_core
    total["over_result_margin_at_open"] = total.total - total.total_line_open
    total_direction = np.sign(total.tree_total_disagreement)
    total["total_confluence_oracle"] = (total.tree_total_disagreement.abs().ge(2.0)
                                         & np.sign(total.weather_increment).eq(total_direction)
                                         & total_direction.ne(0))

    selected_spread = spread[spread.spread_confluence].copy()
    selected_total = total[total.total_confluence_oracle].copy()
    season_spread = {str(int(season)): _graded(rows, np.sign(rows.ridge_spread_disagreement),
                                               "spread_move_home_strength", "home_cover_margin_at_open")
                     for season, rows in selected_spread.groupby("season")}
    season_total = {str(int(season)): _graded(rows, np.sign(rows.tree_total_disagreement),
                                              "total_market_move", "over_result_margin_at_open")
                    for season, rows in selected_total.groupby("season")}
    report = {
        "status": "t9_retrospective_discovery_only",
        "test_seasons": list(range(2020, 2025)), "vault_2025_predictions": 0,
        "spread": {"rule": "structural_and_ml_edges_at_least_2_points_plus_same_direction_t2_t3_increment",
                   "overall": _graded(selected_spread, np.sign(selected_spread.ridge_spread_disagreement),
                                      "spread_move_home_strength", "home_cover_margin_at_open"),
                   "by_season": season_spread},
        "total": {"rule": "ml_edge_at_least_2_points_plus_same_direction_observed_weather_increment",
                  "overall": _graded(selected_total, np.sign(selected_total.tree_total_disagreement),
                                     "total_market_move", "over_result_margin_at_open"),
                  "by_season": season_total, "oracle": True},
        "decision": "promising_hypothesis_freeze_for_prospective_shadow_no_bets",
        "restrictions": ["threshold discovered retrospectively", "historical open provenance incomplete",
                         "historical personnel timing is not fully prospective", "weather uses observed oracle",
                         "book prices unavailable", "staking disabled"],
    }
    output = spread[["game_id", "season", "week", "spread_confluence", "personnel_increment"]].merge(
        total[["game_id", "total_confluence_oracle", "weather_increment"]], on="game_id", validate="one_to_one")
    return output, report


def main() -> None:
    predictions, report = run_audit(); PREDICTIONS.parent.mkdir(parents=True, exist_ok=True); REPORT.parent.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(PREDICTIONS, index=False); REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
