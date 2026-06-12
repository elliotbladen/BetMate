"""
InPlayEngine/sports/_template/config.py

Copy this to sports/{new_sport}/config.py when adding a new sport.
Fill in all FIXME values.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class TemplateConfig:
    sport: str = "FIXME"  # e.g. "epl", "nba", "nfl", "cricket_t20"

    # FIXME: set halftime timing for this sport
    halftime_seconds: int = 45 * 60
    halftime_window_seconds: int = 5 * 60
    fulltime_seconds: int = 90 * 60

    # FIXME: Betfair data source details
    betfair_base_url: str = "https://betfair-datascientists.github.io/assets"
    betfair_filename_pattern: str = "SPORT_{year}_Match_Odds.csv"
    available_years: tuple[int, ...] = ()

    def betfair_url(self, year: int) -> str:
        filename = self.betfair_filename_pattern.format(year=year)
        return f"{self.betfair_base_url}/{filename}"
