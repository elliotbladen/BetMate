import unittest

import numpy as np
import pandas as pd

from scripts.line_mover.afl_movement_direction import (
    MARKETS, baseline_probabilities, build_market_rows, chronological_split, direction,
)


def sample_history(days: int = 20) -> pd.DataFrame:
    rows = []
    for day in range(days):
        for game in range(3):
            rows.append({
                "date": pd.Timestamp("2026-05-01") + pd.Timedelta(days=day),
                "home_team": f"H{game}", "away_team": f"A{game}",
                "home_odds_open": 1.8, "away_odds_open": 2.1,
                "Home Line Open": -4.5, "Home Line Close": -4.5 + ((day % 3) - 1) * 2,
                "Total Score Open": 170.5, "Total Score Close": 170.5 + ((game % 3) - 1) * 2,
            })
    return pd.DataFrame(rows)


class AFLMovementDirectionTests(unittest.TestCase):
    def test_material_direction_has_three_classes(self):
        self.assertEqual(
            direction(pd.Series([-2.0, -1.0, 0.0, 1.0, 2.0]), 1.5).tolist(),
            ["DOWN", "NO_MOVE", "NO_MOVE", "NO_MOVE", "UP"],
        )

    def test_rolling_priors_do_not_see_current_close(self):
        frame = build_market_rows(sample_history(2), MARKETS["handicap"])
        self.assertEqual(frame.iloc[0]["home_games_prior"], 0)
        self.assertEqual(frame.iloc[0]["global_prior_mean"], 0)
        self.assertEqual(frame.iloc[1]["global_prior_mean"], frame.iloc[0]["line_move"])

    def test_chronological_split_keeps_dates_disjoint(self):
        frame = build_market_rows(sample_history(), MARKETS["total"])
        train, calibrate, test = chronological_split(frame)
        self.assertLess(train["date"].max(), calibrate["date"].min())
        self.assertLess(calibrate["date"].max(), test["date"].min())

    def test_baseline_probabilities_are_valid(self):
        frame = build_market_rows(sample_history(), MARKETS["handicap"])
        probabilities = baseline_probabilities(frame)
        self.assertEqual(probabilities.shape, (len(frame), 3))
        self.assertTrue(np.allclose(probabilities.sum(axis=1), 1.0))
        self.assertTrue(np.all((probabilities >= 0) & (probabilities <= 1)))


if __name__ == "__main__":
    unittest.main()
