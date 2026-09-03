#!/usr/bin/env python3
"""Provisional AFL finals Monte Carlo pricing layer.

The simulator deliberately does not use the direct H2H classifier. It blends
the rules and ML point estimates, bootstraps paired out-of-sample 2025 margin
and total residuals, and increases uncertainty when the two models disagree.
This preserves the observed relationship between margin and total errors.
"""

from __future__ import annotations

import argparse
import csv
import pickle
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
DB = ROOT / "data" / "model.db"
FEATURES = ROOT / "ml" / "afl" / "results" / "features_afl.csv"
MODELS = ROOT / "ml" / "afl" / "results" / "models"
SNAPSHOT = ROOT.parent / "data" / "odds_snapshots" / "2026" / "2026-09-02_afl_finals_week2_sportsbet.csv"
OUT_DIR = ROOT / "outputs" / "monte_carlo"

# Players listed as Test/TBC on September 1. The deterministic engine assumes
# they play; each tuple is (team, probability_out, team margin impact if out,
# game total impact if out). These are deliberately modest T5 table values.
UNCERTAIN_AVAILABILITY = {
    ("Fremantle Dockers", "Hawthorn Hawks"): [
        ("Hawthorn Hawks", 0.15, -1.0, -0.5),  # Jack Ginnivan, expected to play
        ("Hawthorn Hawks", 0.50, -1.5, +1.0),  # Jack Scrimshaw, TBC
        ("Hawthorn Hawks", 0.60, -2.0, -1.0),  # Ned Reeves, TBC
    ],
    ("Geelong Cats", "Carlton Blues"): [
        ("Geelong Cats", 0.25, -3.0, -1.5),    # Max Holmes, test
        ("Carlton Blues", 0.35, -1.0, -0.5),  # Will Hayward, test
        ("Carlton Blues", 0.40, -1.5, +1.0),  # Nick Haynes, test
    ],
    ("Sydney Swans", "Brisbane Lions"): [
        ("Sydney Swans", 0.50, -3.0, -2.0),   # Joel Amartey, test
        ("Brisbane Lions", 0.10, -3.0, -1.5), # Hugh McCluggage, expected in
    ],
}


def fair(probability: float) -> float:
    return round(1.0 / probability, 2) if probability > 0 else 999.0


def load_markets() -> dict[tuple[str, str], dict]:
    markets: dict[tuple[str, str], dict] = {}
    with SNAPSHOT.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            key = (row["home_team"], row["away_team"])
            game = markets.setdefault(key, {})
            market = row["market"]
            outcome = row["outcome"]
            game.setdefault(market, {})[outcome] = {
                "price": float(row["price"]),
                "line": float(row["line"]) if row["line"] else None,
            }
    return markets


def out_of_sample_residuals() -> np.ndarray:
    """Paired residuals from the untouched 2025 test season."""
    from ml.afl.features import FEATURES_MARGIN_TOTAL

    data = pd.read_csv(FEATURES, low_memory=False)
    test = data.loc[data["season"] == 2025].copy()
    X = test[FEATURES_MARGIN_TOTAL].apply(pd.to_numeric, errors="coerce")
    with (MODELS / "margin_model.pkl").open("rb") as handle:
        margin_model = pickle.load(handle)
    with (MODELS / "total_model.pkl").open("rb") as handle:
        total_model = pickle.load(handle)
    margin_error = test["home_margin"].to_numpy(float) - margin_model.predict(X)
    total_error = test["total_score"].to_numpy(float) - total_model.predict(X)
    residuals = np.column_stack((margin_error, total_error))
    # Point estimates are separately bias-corrected; simulation errors therefore
    # represent dispersion around zero, not a second bias adjustment.
    return residuals - residuals.mean(axis=0)


def load_prices(round_number: int) -> list[dict]:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT home_team, away_team, rules_margin, rules_total,
               primary_margin, primary_total, ml_total
          FROM afl_shadow_predictions
         WHERE season = 2026 AND round_number = ?
         ORDER BY game_date
        """,
        (round_number,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--round", type=int, default=25)
    parser.add_argument("--sims", type=int, default=100_000)
    parser.add_argument("--seed", type=int, default=20260902)
    args = parser.parse_args()

    rng = np.random.default_rng(args.seed)
    residuals = out_of_sample_residuals()
    markets = load_markets()
    rows = []

    for game in load_prices(args.round):
        home, away = game["home_team"], game["away_team"]
        # Frozen AFL finals specification used for the 2026 wildcard round:
        # 75% ML / 25% rules for margin; rules-only for totals. H2H is derived
        # coherently from the simulated margin rather than separately blended.
        margin_mean = 0.25 * game["rules_margin"] + 0.75 * game["primary_margin"]
        total_mean = game["rules_total"]

        sampled = residuals[rng.integers(0, len(residuals), args.sims)]
        margin_disagreement = abs(game["rules_margin"] - game["primary_margin"])
        total_disagreement = abs(game["rules_total"] - game["ml_total"])
        margin = margin_mean + sampled[:, 0]
        total = total_mean + sampled[:, 1]
        # Model disagreement is epistemic uncertainty. It widens the forecast
        # without quietly pulling the price toward the bookmaker.
        margin += rng.normal(0.0, margin_disagreement / 2.0, args.sims)
        total += rng.normal(0.0, total_disagreement / 2.0, args.sims)
        for team, probability_out, team_margin_impact, total_impact in UNCERTAIN_AVAILABILITY.get((home, away), []):
            absent = rng.random(args.sims) < probability_out
            # Negative team impact lowers the home margin for a home player and
            # raises it for an away player.
            sign = 1.0 if team == home else -1.0
            margin += absent * sign * team_margin_impact
            total += absent * total_impact
        total = np.maximum(total, np.abs(margin) + 12.0)

        mkt = markets[(home, away)]
        home_prob = float(np.mean(margin > 0))
        away_prob = 1.0 - home_prob
        home_line = mkt["handicap"][home]["line"]
        away_line = mkt["handicap"][away]["line"]
        home_cover = float(np.mean(margin + home_line > 0))
        away_cover = float(np.mean(-margin + away_line > 0))
        total_line = mkt["total"]["Over"]["line"]
        over_prob = float(np.mean(total > total_line))
        under_prob = 1.0 - over_prob

        row = {
            "home_team": home,
            "away_team": away,
            "margin_mean": round(margin_mean, 2),
            "total_mean": round(total_mean, 2),
            "home_win_prob": round(home_prob, 4),
            "home_fair_odds": fair(home_prob),
            "away_win_prob": round(away_prob, 4),
            "away_fair_odds": fair(away_prob),
            "home_market_odds": mkt["h2h"][home]["price"],
            "away_market_odds": mkt["h2h"][away]["price"],
            "home_h2h_ev": round(home_prob * mkt["h2h"][home]["price"] - 1, 4),
            "away_h2h_ev": round(away_prob * mkt["h2h"][away]["price"] - 1, 4),
            "home_line": home_line,
            "home_cover_prob": round(home_cover, 4),
            "home_line_ev": round(home_cover * mkt["handicap"][home]["price"] - 1, 4),
            "away_line": away_line,
            "away_cover_prob": round(away_cover, 4),
            "away_line_ev": round(away_cover * mkt["handicap"][away]["price"] - 1, 4),
            "total_line": total_line,
            "over_prob": round(over_prob, 4),
            "over_ev": round(over_prob * mkt["total"]["Over"]["price"] - 1, 4),
            "under_prob": round(under_prob, 4),
            "under_ev": round(under_prob * mkt["total"]["Under"]["price"] - 1, 4),
            "margin_model_gap": round(margin_disagreement, 2),
            "total_model_gap": round(total_disagreement, 2),
        }
        rows.append(row)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    output = OUT_DIR / "afl_finals_week2_2026_100k.csv"
    pd.DataFrame(rows).to_csv(output, index=False)
    print(pd.DataFrame(rows).to_string(index=False))
    print(f"\nSaved: {output}")
    print(f"Residual calibration: 2025 out-of-sample games={len(residuals)}")


if __name__ == "__main__":
    main()
