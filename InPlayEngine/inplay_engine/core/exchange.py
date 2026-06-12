"""
InPlayEngine/core/exchange.py

Betfair Exchange CSV loader. Handles the Betfair Datascientists format:
  market_id, status, inplay, selection_id, selection, last_price_traded,
  ex_wom, ex_best_back_3..1, ex_best_lay_1..3, publish_time, interval_seconds

Sport-agnostic — pass a SportConfig to interpret timing correctly.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class Selection:
    name: str
    selection_id: int


@dataclass
class MarketSnapshot:
    """Prices for all selections at a single point in time."""
    market_id: str
    publish_time: pd.Timestamp
    inplay: bool
    prices: dict[str, float]  # selection_name → last_price_traded


def load_match_odds_csv(path: Path | str) -> pd.DataFrame:
    """
    Load a Betfair Match Odds CSV. Returns a tidy DataFrame with:
      market_id, publish_time (tz-aware UTC), inplay (bool),
      selection, last_price_traded
    """
    df = pd.read_csv(path, low_memory=False)

    required = {"market_id", "inplay", "selection", "last_price_traded", "publish_time"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in {path}: {missing}")

    df["publish_time"] = pd.to_datetime(df["publish_time"], utc=True)
    df["inplay"] = df["inplay"].astype(str).str.strip().str.lower().map(
        {"true": True, "false": False, "1": True, "0": False}
    ).fillna(False)
    df["last_price_traded"] = pd.to_numeric(df["last_price_traded"], errors="coerce")

    return df[["market_id", "publish_time", "inplay", "selection_id", "selection", "last_price_traded"]].copy()


def get_inplay_start(market_df: pd.DataFrame) -> pd.Timestamp | None:
    """Return the first timestamp where inplay=True (≈ kickoff)."""
    inplay_rows = market_df[market_df["inplay"] == True].sort_values("publish_time")
    if inplay_rows.empty:
        return None
    return inplay_rows["publish_time"].iloc[0]


def get_price_at_offset(
    market_df: pd.DataFrame,
    kickoff: pd.Timestamp,
    offset_seconds: int,
    window_seconds: int = 300,
) -> dict[str, float]:
    """
    Return {selection_name: price} at kickoff + offset_seconds.
    Searches within ±window_seconds of the target time.
    Returns the snapshot closest to the target.
    """
    target = kickoff + pd.Timedelta(seconds=offset_seconds)
    lo = target - pd.Timedelta(seconds=window_seconds)
    hi = target + pd.Timedelta(seconds=window_seconds)

    window_df = market_df[
        (market_df["publish_time"] >= lo) &
        (market_df["publish_time"] <= hi) &
        (market_df["inplay"] == True)
    ].copy()

    if window_df.empty:
        return {}

    window_df["dist"] = (window_df["publish_time"] - target).abs()
    best_time = window_df["dist"].min()
    closest = window_df[window_df["dist"] == best_time]

    return dict(zip(closest["selection"], closest["last_price_traded"]))


def get_selections(market_df: pd.DataFrame) -> list[str]:
    """Return unique selection names in this market."""
    return list(market_df["selection"].dropna().unique())


def split_markets(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Split a multi-market CSV into per-market DataFrames."""
    return {mid: grp.copy() for mid, grp in df.groupby("market_id")}
