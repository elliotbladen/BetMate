"""EPL-style end-to-end NFL backtest report across development and 2025 vault."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .baselines import _metrics

ROOT = Path(__file__).resolve().parents[2]
FEATURES = ROOT / "data/nfl/features/weekly_epa.parquet"
WALK_FORWARD = ROOT / "data/nfl/predictions/step4_challenger.csv"
VAULT = ROOT / "data/nfl/predictions/step5_2025_vault_scored.csv"
ROWS = ROOT / "data/nfl/predictions/step13_end_to_end_backtest.csv"
REPORT = ROOT / "ml/nfl/reports/step13_end_to_end_backtest.json"


def _roi(result: pd.Series) -> dict:
    result = result.dropna()
    wins, losses, pushes = int(result.eq("win").sum()), int(result.eq("loss").sum()), int(result.eq("push").sum())
    bets = wins + losses + pushes
    profit = wins * (100 / 110) - losses
    return {"bets": bets, "wins": wins, "losses": losses, "pushes": pushes,
            "win_rate_ex_pushes": wins / (wins + losses) if wins + losses else None,
            "synthetic_roi_at_minus_110": profit / bets if bets else None}


def _side_result(edge: pd.Series, cover: pd.Series, threshold: float) -> pd.Series:
    take_home = edge.ge(threshold); take_away = edge.le(-threshold)
    result = pd.Series(np.nan, index=edge.index, dtype=object)
    result[take_home & cover.gt(0)] = "win"; result[take_home & cover.lt(0)] = "loss"; result[take_home & cover.eq(0)] = "push"
    result[take_away & cover.lt(0)] = "win"; result[take_away & cover.gt(0)] = "loss"; result[take_away & cover.eq(0)] = "push"
    return result


def run() -> tuple[pd.DataFrame, dict]:
    # Walk-forward rows already carry closing lines; add only opener fields from
    # the feature store to avoid duplicate market columns during the join.
    features = pd.read_parquet(FEATURES)[["game_id", "spread_home_open", "total_line_open"]]
    wf = pd.read_csv(WALK_FORWARD).merge(features, on="game_id", validate="one_to_one")
    wf["model"] = "walk_forward_2019_2024"
    vault = pd.read_csv(VAULT)
    vault["model"] = "sealed_vault_2025"
    # Vault already contains labels/markets; align names with walk-forward output.
    vault = vault.rename(columns={"ridge_margin": "model_margin", "ridge_total": "model_total"})
    wf = wf.rename(columns={"ridge_margin": "model_margin", "tree_total": "model_total"})
    wf["home_win_probability"] = wf["margin_h2h_probability"]
    vault["home_win_probability"] = vault["margin_h2h_probability"]
    cols = ["game_id", "season", "week", "margin", "total", "model_margin", "model_total", "home_win_probability",
            "spread_home_open", "spread_home_close", "total_line_open", "total_line_close", "model"]
    rows = pd.concat([wf[cols], vault[cols]], ignore_index=True).drop_duplicates("game_id")
    rows["spread_edge"] = rows.model_margin + rows.spread_home_open
    rows["total_edge"] = rows.model_total - rows.total_line_open
    rows["spread_cover_margin"] = rows.margin + rows.spread_home_open
    rows["total_result_margin"] = rows.total - rows.total_line_open
    rows["home_win"] = rows.margin.gt(0).astype(int)
    rows["spread_clv_home_strength"] = (-rows.spread_home_close) - (-rows.spread_home_open)
    rows["total_clv"] = rows.total_line_close - rows.total_line_open

    thresholds = {}
    for threshold in (0.0, 1.0, 2.0, 3.0):
        spread_results = _side_result(rows.spread_edge, rows.spread_cover_margin, threshold)
        total_result = _side_result(rows.total_edge, rows.total_result_margin, threshold)
        thresholds[str(threshold)] = {"spread": _roi(spread_results), "totals": _roi(total_result)}
    scored = rows[rows.model.eq("sealed_vault_2025")]
    report = {
        "status": "nfl_end_to_end_backtest_complete",
        "walk_forward_games": int((rows.model == "walk_forward_2019_2024").sum()),
        "sealed_vault_games": int(len(scored)), "total_games": int(len(rows)),
        "development_seasons": [2019, 2020, 2021, 2022, 2023, 2024], "vault_season": 2025,
        "markets": {
            "spread_model_margin": _metrics(rows.margin, rows.model_margin),
            "spread_opening_baseline": _metrics(rows.margin, -rows.spread_home_open),
            "spread_closing_baseline": _metrics(rows.margin, -rows.spread_home_close),
            "total_model": _metrics(rows.total, rows.model_total),
            "total_opening_baseline": _metrics(rows.total, rows.total_line_open),
            "total_closing_baseline": _metrics(rows.total, rows.total_line_close),
            "h2h_model_accuracy": float((rows.home_win_probability.ge(.5) == rows.home_win).mean()),
            "h2h_model_brier": float(((rows.home_win_probability - rows.home_win) ** 2).mean()),
        },
        "thresholds": thresholds,
        "vault_2025": {"spread_model_mae": _metrics(scored.margin, scored.model_margin),
                        "total_model_mae": _metrics(scored.total, scored.model_total),
                        "h2h_accuracy": float((scored.home_win_probability.ge(.5) == scored.home_win).mean())},
        "restrictions": ["historical opener coverage is incomplete", "exact historical bookmaker prices unavailable",
                         "ROI is synthetic -110 only", "no live odds were used as model features", "staking disabled"],
        "decision": "price_paper_markets_now_collect_prospective_evidence_before_betting",
    }
    return rows, report


def main() -> None:
    rows, report = run(); ROWS.parent.mkdir(parents=True, exist_ok=True); REPORT.parent.mkdir(parents=True, exist_ok=True)
    rows.to_csv(ROWS, index=False); REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
