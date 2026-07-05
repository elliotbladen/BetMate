#!/usr/bin/env python3
"""Write AFL Round 8 fixture and weather prep files."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "outputs" / "afl_round_prep" / "r8_2026"

FIXTURE = [
    {"round": 8, "date": "2026-04-30", "kickoff": "19:30", "venue": "MCG", "home_team": "Collingwood Magpies", "away_team": "Hawthorn Hawks"},
    {"round": 8, "date": "2026-05-01", "kickoff": "19:30", "venue": "Marvel Stadium", "home_team": "Western Bulldogs", "away_team": "Fremantle Dockers"},
    {"round": 8, "date": "2026-05-01", "kickoff": "20:10", "venue": "Adelaide Oval", "home_team": "Adelaide Crows", "away_team": "Port Adelaide Power"},
    {"round": 8, "date": "2026-05-02", "kickoff": "12:35", "venue": "Marvel Stadium", "home_team": "Essendon Bombers", "away_team": "Brisbane Lions"},
    {"round": 8, "date": "2026-05-02", "kickoff": "16:15", "venue": "Optus Stadium", "home_team": "West Coast Eagles", "away_team": "Richmond Tigers"},
    {"round": 8, "date": "2026-05-02", "kickoff": "16:35", "venue": "GMHBA Stadium", "home_team": "Geelong Cats", "away_team": "North Melbourne Kangaroos"},
    {"round": 8, "date": "2026-05-02", "kickoff": "19:35", "venue": "Marvel Stadium", "home_team": "Carlton Blues", "away_team": "St Kilda Saints"},
    {"round": 8, "date": "2026-05-03", "kickoff": "15:15", "venue": "SCG", "home_team": "Sydney Swans", "away_team": "Melbourne Demons"},
    {"round": 8, "date": "2026-05-03", "kickoff": "19:20", "venue": "People First Stadium", "home_team": "Gold Coast Suns", "away_team": "Greater Western Sydney Giants"},
]

VENUES = {
    "MCG": (-37.8200, 144.9834),
    "Marvel Stadium": (-37.8165, 144.9476),
    "Adelaide Oval": (-34.9158, 138.5963),
    "Optus Stadium": (-31.9510, 115.8883),
    "GMHBA Stadium": (-38.1554, 144.3550),
    "SCG": (-33.8914, 151.2246),
    "People First Stadium": (-28.0034, 153.3946),
}


def fetch_open_meteo(lat: float, lon: float, day: str) -> dict:
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": day,
        "end_date": day,
        "hourly": "temperature_2m,dew_point_2m,precipitation,wind_speed_10m",
        "timezone": "Australia/Sydney",
    }
    url = "https://archive-api.open-meteo.com/v1/archive?" + urlencode(params)
    with urlopen(url, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def closest_hour_weather(raw: dict, day: str, kickoff: str) -> dict:
    target = datetime.fromisoformat(f"{day}T{kickoff}")
    times = raw["hourly"]["time"]
    idx = min(range(len(times)), key=lambda i: abs(datetime.fromisoformat(times[i]) - target))
    hourly = raw["hourly"]
    temp = hourly["temperature_2m"][idx]
    dew = hourly["dew_point_2m"][idx]
    rain = hourly["precipitation"][idx]
    wind = hourly["wind_speed_10m"][idx]
    return {
        "weather_time": times[idx],
        "temp_c": temp,
        "dew_point_c": dew,
        "precip_mm": rain,
        "wind_kmh": wind,
        "dew_risk": bool(kickoff >= "18:30" and dew is not None and temp is not None and dew > 12 and (temp - dew) < 5),
        "data_source": "Open-Meteo archive",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    fixture_path = args.out_dir / "fixture_r8_2026.csv"
    fields = ["round", "date", "kickoff", "venue", "home_team", "away_team"]
    with fixture_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(FIXTURE)

    weather_rows = []
    cache = {}
    for game in FIXTURE:
        lat, lon = VENUES[game["venue"]]
        cache_key = (lat, lon, game["date"])
        if cache_key not in cache:
            cache[cache_key] = fetch_open_meteo(lat, lon, game["date"])
        row = {**game, **closest_hour_weather(cache[cache_key], game["date"], game["kickoff"])}
        weather_rows.append(row)

    weather_csv = args.out_dir / "weather_r8_2026.csv"
    weather_fields = fields + ["weather_time", "temp_c", "dew_point_c", "precip_mm", "wind_kmh", "dew_risk", "data_source"]
    with weather_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=weather_fields)
        writer.writeheader()
        writer.writerows(weather_rows)

    weather_json = args.out_dir / "weather_r8_2026.json"
    weather_json.write_text(json.dumps({"season": 2026, "round": 8, "weather": weather_rows}, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {fixture_path}")
    print(f"Wrote {weather_csv}")
    print(f"Wrote {weather_json}")


if __name__ == "__main__":
    main()
