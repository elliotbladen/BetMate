"""Join Footiqo 2025/26 card closing prices to the official result archive."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent
RESULTS = ROOT / "data" / "epl" / "cards" / "epl_card_results_2022_23_to_2025_26.csv"
ODDS = ROOT / "data" / "epl" / "cards" / "footiqo_epl_cards_closing_odds_2025_26.csv"
OUT = ROOT / "data" / "epl" / "cards" / "epl_2025_26_card_market_join.csv"
ALIASES = {
    "Man City": "Manchester City",
    "Man United": "Manchester Utd",
    "Nott'm Forest": "Nottingham",
}


def main() -> None:
    results = pd.read_csv(RESULTS)
    results = results[results["Season"] == "2025/26"].copy()
    results["date_key"] = pd.to_datetime(results["Date"], dayfirst=True).dt.date.astype(str)
    results["home_key"] = results["HomeTeam"].replace(ALIASES)
    results["away_key"] = results["AwayTeam"].replace(ALIASES)

    odds = pd.read_csv(ODDS)
    odds["date_key"] = pd.to_datetime(odds["start_datetime"]).dt.date.astype(str)
    odds["home_key"] = odds["home_team"]
    odds["away_key"] = odds["away_team"]
    keep = [
        "date_key", "home_key", "away_key", "match_id", "referee",
        "over_3_5_yellow_cards_ft_closing_odds",
        "under_3_5_yellow_cards_ft_closing_odds",
        "total_yellow_cards_ft",
    ]
    joined = results.merge(odds[keep], on=["date_key", "home_key", "away_key"], how="outer", indicator=True)
    if not (joined["_merge"] == "both").all():
        raise RuntimeError(f"unmatched fixtures: {joined['_merge'].value_counts().to_dict()}")
    joined["yellow_total_match"] = joined["total_yellow_cards"] == joined["total_yellow_cards_ft"]
    joined["market_outcome_source"] = "football-data.co.uk"
    joined = joined.drop(columns=["_merge"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    joined.to_csv(OUT, index=False)
    print(f"joined={len(joined)} outcome_mismatches={(~joined.yellow_total_match).sum()} output={OUT}")


if __name__ == "__main__":
    main()
