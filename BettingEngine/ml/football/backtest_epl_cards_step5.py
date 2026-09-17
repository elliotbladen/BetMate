"""Backtest the selected EPL yellow-card model on 2025/26 closing prices."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).parent
PRICES = ROOT / "data" / "epl" / "cards" / "epl_cards_step4_calibrated_prices.csv"
MARKET = ROOT / "data" / "epl" / "cards" / "epl_2025_26_card_market_join.csv"
OUT = ROOT / "data" / "epl" / "cards" / "epl_cards_step5_bets.csv"
REPORT = ROOT / "reports" / "epl_cards_step5_backtest.json"
THRESHOLDS = [0.00, 0.05, 0.08, 0.10]


def settle(row: pd.Series, outcome_col: str) -> int:
    total = float(row[outcome_col])
    return int(total > 3.5) if row["selection"] == "Over 3.5" else int(total < 3.5)


def run_bets(frame: pd.DataFrame, threshold: float, outcome_col: str) -> dict[str, float | int]:
    candidates = frame[(frame["eligible_for_step5"]) & (frame["ev"] >= threshold)].copy()
    if candidates.empty:
        return {"threshold": threshold, "bets": 0, "wins": 0, "roi": 0.0, "profit": 0.0, "mean_ev": 0.0}
    candidates["win"] = candidates.apply(lambda r: settle(r, outcome_col), axis=1)
    candidates["profit"] = np.where(candidates["win"].eq(1), candidates["odds"] - 1.0, -1.0)
    return {
        "threshold": threshold,
        "bets": int(len(candidates)),
        "wins": int(candidates["win"].sum()),
        "roi": float(candidates["profit"].sum() / len(candidates)),
        "profit": float(candidates["profit"].sum()),
        "mean_ev": float(candidates["ev"].mean()),
    }


def main() -> None:
    prices = pd.read_csv(PRICES)
    market = pd.read_csv(MARKET)
    odds_cols = ["over_3_5_yellow_cards_ft_closing_odds", "under_3_5_yellow_cards_ft_closing_odds"]
    if market[odds_cols].isna().any().any():
        raise RuntimeError("closing card odds are incomplete")
    join_cols = ["Date", "HomeTeam", "AwayTeam"]
    df = prices.merge(market[join_cols + odds_cols + ["total_yellow_cards_ft", "yellow_total_match"]],
                      on=join_cols, how="outer", validate="one_to_one", indicator=True)
    if not (df["_merge"] == "both").all():
        raise RuntimeError(f"market join failed: {df['_merge'].value_counts().to_dict()}")
    df = df.drop(columns="_merge")
    df["selection"] = np.where(
        df["selected_p_over35_calibrated"] >= df["selected_p_under35_calibrated"],
        "Over 3.5", "Under 3.5",
    )
    df["model_probability"] = np.where(
        df["selection"].eq("Over 3.5"),
        df["selected_p_over35_calibrated"], df["selected_p_under35_calibrated"],
    )
    df["odds"] = np.where(
        df["selection"].eq("Over 3.5"),
        df[odds_cols[0]], df[odds_cols[1]],
    )
    df["market_implied_probability"] = 1.0 / df["odds"]
    df["probability_edge"] = df["model_probability"] - df["market_implied_probability"]
    df["ev"] = df["model_probability"] * df["odds"] - 1.0
    df["closing_odds_source"] = "Footiqo free EPL 2025/26 cards file"
    bets = []
    for _, row in df[df["eligible_for_step5"]].iterrows():
        for threshold in THRESHOLDS:
            if row.ev >= threshold:
                bets.append({
                    "Date": row.Date, "HomeTeam": row.HomeTeam, "AwayTeam": row.AwayTeam,
                    "Referee": row.Referee, "selection": row.selection,
                    "model_probability": row.model_probability, "odds": row.odds,
                    "ev": row.ev, "threshold": threshold,
                    "official_total_yellow_cards": row.total_yellow_cards,
                    "footiqo_total_yellow_cards": row.total_yellow_cards_ft,
                    "yellow_total_match": row.yellow_total_match,
                    "official_win": settle(row, "total_yellow_cards"),
                    "footiqo_win": settle(row, "total_yellow_cards_ft"),
                })
    bets_df = pd.DataFrame(bets)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    bets_df.to_csv(OUT, index=False)
    y = (df.total_yellow_cards > 3.5).astype(int).to_numpy()
    p = df.selected_p_over35_calibrated.to_numpy()
    report = {
        "season": "2025/26",
        "market": "yellow_cards_ou35",
        "model": "calibrated_glm",
        "matches": int(len(df)),
        "closing_odds_complete": bool(df[odds_cols].notna().all().all()),
        "eligible_matches": int(df.eligible_for_step5.sum()),
        "provider_outcome_mismatches": int((~df.yellow_total_match).sum()),
        "calibration": {
            "brier": float(np.mean((p - y) ** 2)),
            "log_loss": float(-np.mean(y * np.log(np.clip(p, 1e-6, 1 - 1e-6)) + (1 - y) * np.log(np.clip(1 - p, 1e-6, 1 - 1e-6)))),
            "predicted_over_rate": float(p.mean()),
            "actual_over_rate": float(y.mean()),
        },
        "official_result_thresholds": [run_bets(df, t, "total_yellow_cards") for t in THRESHOLDS],
        "footiqo_result_sensitivity": [run_bets(df, t, "total_yellow_cards_ft") for t in THRESHOLDS],
        "outputs": str(OUT.relative_to(ROOT.parent.parent)),
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
