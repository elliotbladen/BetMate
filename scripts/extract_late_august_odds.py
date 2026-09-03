"""Extract the completed 28-31 August 2026 weekend from historical sources."""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/odds/weekends/2026-08-27"
# Include Thursday night because it belongs to the NRL weekend round.
START, END = pd.Timestamp("2026-08-27"), pd.Timestamp("2026-09-01")

MARKETS = [
    "Date", "Home Team", "Away Team", "Home Score", "Away Score",
    "Home Odds Open", "Home Odds Close", "Away Odds Open", "Away Odds Close",
    "Home Line Open", "Home Line Close", "Away Line Open", "Away Line Close",
    "Home Line Odds Open", "Home Line Odds Close",
    "Away Line Odds Open", "Away Line Odds Close",
    "Total Score Open", "Total Score Close", "Total Score Over Open",
    "Total Score Over Close", "Total Score Under Open", "Total Score Under Close",
]


def australian(sport: str, path: Path) -> pd.DataFrame:
    frame = pd.read_excel(path, sheet_name="Data", header=1)
    frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce")
    frame = frame[(frame["Date"] >= START) & (frame["Date"] < END)]
    frame = frame[[column for column in MARKETS if column in frame.columns]].copy()
    frame.insert(0, "Sport", sport)
    return frame.sort_values("Date")


def football(league: str, path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, low_memory=False)
    frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce")
    frame = frame[(frame["Date"] >= START) & (frame["Date"] < END)].copy()
    frame.insert(0, "League", league)
    return frame.sort_values("Date")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    sources = {
        "afl": australian("AFL", ROOT / "data/afl/historical/latest.xlsx"),
        "nrl": australian("NRL", ROOT / "data/nrl/historical/latest.xlsx"),
        "epl": football("EPL", ROOT / "BettingEngine/ml/football/data/epl/matches/epl_matches.csv"),
        "championship": football("Championship", ROOT / "BettingEngine/ml/football/data/championship/matches/championship_matches.csv"),
    }
    for name, frame in sources.items():
        destination = OUT / f"{name}.csv"
        frame.to_csv(destination, index=False)
        print(f"{name}: {len(frame)} games -> {destination.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
