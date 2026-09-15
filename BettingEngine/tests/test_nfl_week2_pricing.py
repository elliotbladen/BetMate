import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PRICE_DIR = ROOT / "data/nfl/pricing/2026_week02"


class Week2PricingTests(unittest.TestCase):
    def test_week2_price_card_has_all_markets_and_tier_columns(self):
        prices = pd.read_csv(PRICE_DIR / "week02_prices.csv")
        self.assertEqual(len(prices), 16)
        for column in (
            "fair_home_spread", "fair_total", "home_win_probability",
            "home_moneyline_american", "away_moneyline_american",
            "t1_injury_points", "t2_qb_points", "t2_continuity_points",
            "t2_weather_points", "t3_confluence_points",
        ):
            self.assertIn(column, prices.columns)
        self.assertTrue(prices.staking_enabled.eq(False).all())
        self.assertTrue(prices.official_price_changed.eq(False).all())

    def test_week2_manifest_records_injury_provenance(self):
        import json
        manifest = json.loads((PRICE_DIR / "manifest.json").read_text())
        self.assertEqual(manifest["games"], 16)
        self.assertIn("injury_source_file", manifest)
        self.assertEqual(manifest["weather_points"], 0.0)


if __name__ == "__main__":
    unittest.main()
