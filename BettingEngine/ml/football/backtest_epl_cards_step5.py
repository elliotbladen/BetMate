"""Backtest the selected EPL yellow-card model on 2025/26 closing prices."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).parent
PRICES = ROOT / "data" / "epl" / "cards" / "epl_cards_step4_calibrated_prices.csv"
RAW_PRICES = ROOT / "data" / "epl" / "cards" / "epl_cards_step3_prices.csv"
MARKET = ROOT / "data" / "epl" / "cards" / "epl_2025_26_card_market_join.csv"
OUT = ROOT / "data" / "epl" / "cards" / "epl_cards_step5_bets.csv"
REPORT = ROOT / "reports" / "epl_cards_step5_backtest.json"
THRESHOLDS = [0.00, 0.05, 0.08, 0.10, 0.20]


def settle(row: pd.Series, outcome_col: str) -> int:
    total = float(row[outcome_col])
    return int(total > 3.5) if row["selection"] == "Over 3.5" else int(total < 3.5)


def run_bets(frame: pd.DataFrame, threshold: float, outcome_col: str) -> dict[str, float | int]:
    candidates = frame[(frame["eligible_variant"]) & (frame["ev"] >= threshold)].copy()
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
    raw_prices = pd.read_csv(RAW_PRICES)[["Date", "HomeTeam", "AwayTeam", "baseline_p_over35"]]
    for frame in (prices, raw_prices):
        frame["Date"] = pd.to_datetime(frame["Date"], format="mixed", dayfirst=False)
    prices = prices.merge(raw_prices, on=["Date", "HomeTeam", "AwayTeam"], how="left", validate="one_to_one")
    market = pd.read_csv(MARKET)
    market["Date"] = pd.to_datetime(market["Date"], format="mixed", dayfirst=True)
    odds_cols = ["over_3_5_yellow_cards_ft_closing_odds", "under_3_5_yellow_cards_ft_closing_odds"]
    if market[odds_cols].isna().any().any():
        raise RuntimeError("closing card odds are incomplete")
    join_cols = ["Date", "HomeTeam", "AwayTeam"]
    df = prices.merge(market[join_cols + odds_cols + ["total_yellow_cards_ft", "yellow_total_match"]],
                      on=join_cols, how="outer", validate="one_to_one", indicator=True)
    if not (df["_merge"] == "both").all():
        raise RuntimeError(f"market join failed: {df['_merge'].value_counts().to_dict()}")
    df = df.drop(columns="_merge")
    variant_probs = {
        "baseline": df["baseline_p_over35"],
        "raw_enriched_glm": df["selected_p_over35_raw"],
        "calibrated_enriched_glm": df["selected_p_over35_calibrated"],
    }
    bets = []
    summaries = {}
    for model_name, p_over in variant_probs.items():
        work = df.copy()
        work["model_name"] = model_name
        work["p_over"] = p_over
        work["p_under"] = 1.0 - p_over
        work["selection"] = np.where(work.p_over >= work.p_under, "Over 3.5", "Under 3.5")
        work["model_probability"] = np.where(work.selection.eq("Over 3.5"), work.p_over, work.p_under)
        work["odds"] = np.where(work.selection.eq("Over 3.5"), work[odds_cols[0]], work[odds_cols[1]])
        work["market_implied_probability"] = 1.0 / work.odds
        work["probability_edge"] = work.model_probability - work.market_implied_probability
        work["ev"] = work.model_probability * work.odds - 1.0
        work["eligible_variant"] = work.ref_sample_ok & (work[["p_over", "p_under"]].max(axis=1) >= 0.57)
        summaries[model_name] = {
            "calibration": {"brier": float(np.mean((work.p_over - (work.total_yellow_cards > 3.5)) ** 2)),
                            "predicted_over_rate": float(work.p_over.mean()),
                            "actual_over_rate": float((work.total_yellow_cards > 3.5).mean())},
            "eligible_matches": int(work.eligible_variant.sum()),
            "official_result_thresholds": [run_bets(work, t, "total_yellow_cards") for t in THRESHOLDS],
            "footiqo_result_sensitivity": [run_bets(work, t, "total_yellow_cards_ft") for t in THRESHOLDS],
        }
        for _, row in work[work.eligible_variant].iterrows():
            for threshold in THRESHOLDS:
                if row.ev >= threshold:
                    bets.append({"model": model_name, "Date": row.Date, "HomeTeam": row.HomeTeam, "AwayTeam": row.AwayTeam,
                                 "Referee": row.Referee, "selection": row.selection, "model_probability": row.model_probability,
                                 "odds": row.odds, "ev": row.ev, "threshold": threshold,
                                 "official_total_yellow_cards": row.total_yellow_cards, "footiqo_total_yellow_cards": row.total_yellow_cards_ft,
                                 "yellow_total_match": row.yellow_total_match, "official_win": settle(row, "total_yellow_cards"),
                                 "footiqo_win": settle(row, "total_yellow_cards_ft")})
    bets_df = pd.DataFrame(bets)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    bets_df.to_csv(OUT, index=False)
    report = {
        "season": "2025/26",
        "market": "yellow_cards_ou35",
        "models": summaries,
        "matches": int(len(df)),
        "closing_odds_complete": bool(df[odds_cols].notna().all().all()),
        "provider_outcome_mismatches": int((~df.yellow_total_match).sum()),
        "outputs": str(OUT.relative_to(ROOT.parent.parent)),
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
