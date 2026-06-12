"""
InPlayEngine/sports/afl/config.py

AFL-specific timing and scoring constants for the in-play engine.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class AFLConfig:
    sport: str = "afl"

    # Game timing — AFL quarters, halftime = end of Q2
    # Quarter = ~30 min playing time + time-on (~6 min) ≈ 36 min actual
    # Halftime break after Q2 ≈ 65–75 min into broadcast time
    halftime_seconds: int = 65 * 60          # 3900s — conservative estimate
    halftime_window_seconds: int = 8 * 60    # wider window due to variable time-on
    fulltime_seconds: int = 130 * 60

    # Betfair data source
    betfair_base_url: str = "https://betfair-datascientists.github.io/assets"
    betfair_filename_pattern: str = "AFL_{year}_Match_Odds.csv"
    available_years: tuple[int, ...] = (2021, 2022, 2023, 2024, 2025, 2026)

    # Scoring
    goal_points: int = 6
    behind_points: int = 1

    def betfair_url(self, year: int) -> str:
        filename = self.betfair_filename_pattern.format(year=year)
        return f"{self.betfair_base_url}/{filename}"


AFL = AFLConfig()
