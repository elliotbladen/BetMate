"""
InPlayEngine/core/halftime.py

Extract halftime prices from a Betfair market DataFrame.
Sport-agnostic — timing constants come from each SportConfig.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from inplay_engine.core.exchange import get_inplay_start, get_price_at_offset


@dataclass
class HalftimePrice:
    market_id: str
    kickoff: pd.Timestamp
    halftime_ts: pd.Timestamp
    prices: dict[str, float]  # selection_name → decimal odds
    found: bool


def extract_halftime(
    market_df: pd.DataFrame,
    halftime_seconds: int,
    window_seconds: int = 300,
) -> HalftimePrice:
    """
    Given a single market's DataFrame, find the Betfair price at halftime.

    Args:
        market_df: rows for a single market_id (from split_markets)
        halftime_seconds: seconds after kickoff that halftime occurs
                          NRL=2400 (40min), AFL=3900 (65min)
        window_seconds: tolerance ± when searching for the snapshot
    """
    market_id = market_df["market_id"].iloc[0]
    kickoff = get_inplay_start(market_df)

    if kickoff is None:
        return HalftimePrice(
            market_id=market_id, kickoff=pd.NaT,
            halftime_ts=pd.NaT, prices={}, found=False,
        )

    prices = get_price_at_offset(market_df, kickoff, halftime_seconds, window_seconds)
    halftime_ts = kickoff + pd.Timedelta(seconds=halftime_seconds)

    return HalftimePrice(
        market_id=market_id,
        kickoff=kickoff,
        halftime_ts=halftime_ts,
        prices=prices,
        found=bool(prices),
    )
