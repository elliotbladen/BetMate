"""Fetch the four completed EPL seasons with yellow and red-card results."""
from __future__ import annotations

import io
from pathlib import Path
from urllib.request import Request, urlopen

import pandas as pd

ROOT = Path(__file__).parent
OUT = ROOT / "data" / "epl" / "cards" / "epl_card_results_2022_23_to_2025_26.csv"
SEASONS = {
    "2022/23": "2223",
    "2023/24": "2324",
    "2024/25": "2425",
    "2025/26": "2526",
}
URL = "https://www.football-data.co.uk/mmz4281/{code}/E0.csv"
KEEP = ["Season", "Date", "HomeTeam", "AwayTeam", "Referee", "HY", "AY", "HR", "AR"]


def fetch(season: str, code: str) -> pd.DataFrame:
    req = Request(URL.format(code=code), headers={"User-Agent": "BetMate research data audit"})
    with urlopen(req, timeout=30) as response:
        frame = pd.read_csv(io.BytesIO(response.read()), low_memory=False)
    missing = sorted(set(KEEP[1:]) - set(frame.columns))
    if missing:
        raise RuntimeError(f"{season}: source missing {missing}")
    frame = frame[KEEP[1:]].copy()
    frame.insert(0, "Season", season)
    for col in ["HY", "AY", "HR", "AR"]:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    if frame[["HY", "AY", "HR", "AR"]].isna().any().any():
        raise RuntimeError(f"{season}: missing card values")
    return frame


def main() -> None:
    frames = [fetch(season, code) for season, code in SEASONS.items()]
    out = pd.concat(frames, ignore_index=True)
    out["total_yellow_cards"] = out.HY + out.AY
    out["total_red_cards"] = out.HR + out.AR
    out["total_cards_including_red"] = out.total_yellow_cards + out.total_red_cards
    key = ["Season", "Date", "HomeTeam", "AwayTeam"]
    if out.duplicated(key).any():
        raise RuntimeError("duplicate fixture keys in fetched card results")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT, index=False)
    print(f"wrote {len(out)} rows to {OUT}")
    print(out.groupby("Season").size().to_string())
    print(f"yellow mean={out.total_yellow_cards.mean():.3f} "
          f"including-red mean={out.total_cards_including_red.mean():.3f}")


if __name__ == "__main__":
    main()
