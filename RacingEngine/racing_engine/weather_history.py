"""Attach timestamp-matched historic weather-station observations to races."""
from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

from .storage import RacingStore


ROOT = Path(__file__).resolve().parents[1]
WEATHER_SOURCE = "meteostat-hourly-station-v1"
STATIONS = {
    "randwick": "94767", "rosehill": "94767", "flemington": "94866",
    "caulfield": "94870", "caulfield-heath": "94870",
    "sportsbet-sandown-hillside": "94870", "sportsbet-sandown-lakeside": "94870",
}


def download_year(station: str, year: int) -> dict[tuple[int, int, int, int], dict]:
    folder = ROOT / "data" / "raw" / "weather" / "meteostat"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{station}_{year}.csv.gz"
    if not path.exists():
        url = f"https://data.meteostat.net/hourly/{year}/{station}.csv.gz"
        request = Request(url, headers={"User-Agent": "BetMate-RacingEngine/0.1 historical research"})
        with urlopen(request, timeout=60) as response:
            path.write_bytes(response.read())
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return {(int(r["year"]), int(r["month"]), int(r["day"]), int(r["hour"])): r for r in csv.DictReader(handle)}


def number(value: str | None) -> float | None:
    try: return float(value) if value not in (None, "") else None
    except ValueError: return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    store = RacingStore(ROOT / "data" / "racing_engine.sqlite")
    try:
        races = store.connection.execute(
            """SELECT source,race_date,track_slug,race_number,scheduled_start_at FROM race_results
               WHERE scheduled_start_at IS NOT NULL AND track_slug IN ({})""".format(
                ",".join("?" for _ in STATIONS)), tuple(STATIONS)).fetchall()
        if args.dry_run:
            print(json.dumps({"eligible_races": len(races), "stations": STATIONS}, sort_keys=True)); return
        cache: dict[tuple[str,int], dict] = {}; stored = missing = 0
        for race in races:
            stamp = datetime.fromisoformat(race["scheduled_start_at"].replace("Z", "+00:00")).astimezone(timezone.utc)
            station = STATIONS[race["track_slug"]]
            key = (station, stamp.year)
            if key not in cache:
                cache[key] = download_year(*key)
            observation = cache[key].get((stamp.year, stamp.month, stamp.day, stamp.hour))
            if not observation:
                missing += 1; continue
            quality = {field: observation.get(f"{field}_source") for field in ("temp","rhum","prcp","wdir","wspd","pres")}
            store.upsert_race_weather({"source": race["source"], "race_date": race["race_date"],
                "track_slug": race["track_slug"], "race_number": race["race_number"], "weather_source": WEATHER_SOURCE,
                "station_id": station, "observed_at": stamp.replace(minute=0, second=0, microsecond=0).isoformat(),
                "temperature_c": number(observation.get("temp")), "humidity_pct": number(observation.get("rhum")),
                "precipitation_mm": number(observation.get("prcp")), "wind_direction_deg": number(observation.get("wdir")),
                "wind_speed_kmh": number(observation.get("wspd")), "pressure_hpa": number(observation.get("pres")),
                "quality": quality, "raw": observation})
            stored += 1
        print(json.dumps({"stored": stored, "missing_hour": missing, "weather_source": WEATHER_SOURCE}, sort_keys=True))
    finally:
        store.close()


if __name__ == "__main__":
    main()
