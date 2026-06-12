"""
InPlayEngine/sports/nrl/config.py

NRL-specific timing and scoring constants for the in-play engine.
"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class NRLConfig:
    sport: str = "nrl"

    # Game timing
    halftime_seconds: int = 40 * 60          # 2400s — end of 40-min first half
    halftime_window_seconds: int = 5 * 60    # ±5 min tolerance for price lookup
    fulltime_seconds: int = 80 * 60
    extra_time_seconds: int = 90 * 60        # OT approx

    # Betfair data source
    betfair_base_url: str = "https://betfair-datascientists.github.io/assets"
    betfair_filename_pattern: str = "NRL_{year}_Match_Odds.csv"
    available_years: tuple[int, ...] = (2021, 2022, 2023, 2024, 2025, 2026)

    # Scoring
    try_points: int = 4
    conversion_points: int = 2
    penalty_goal_points: int = 2
    drop_goal_points: int = 1

    # Origin period (for filtering)
    origin_months: tuple[int, ...] = (6, 7)  # June–July

    def betfair_url(self, year: int) -> str:
        filename = self.betfair_filename_pattern.format(year=year)
        return f"{self.betfair_base_url}/{filename}"


NRL = NRLConfig()
