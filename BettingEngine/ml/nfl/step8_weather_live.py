"""Timestamped Open-Meteo forecast capture for the NFL T6 totals shadow."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from .step8_live_tiers import EASTERN, ROOT, PREDICTIONS, SCHEDULES, _parse_aware


REGISTRY = ROOT / "data/nfl/live_tiers/2026_week01_stadium_registry.csv"
ARCHIVE = ROOT / "data/nfl/weather/step8"
REPORTS = ROOT / "ml/nfl/reports/weather"
API_URL = "https://api.open-meteo.com/v1/forecast"
REGISTRY_FIELDS = [
    "game_id", "stadium_id", "stadium", "roof", "latitude", "longitude",
    "coordinate_source", "coordinate_verified_at_utc", "coordinate_verified",
]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare_registry() -> dict:
    if REGISTRY.exists():
        raise RuntimeError(f"refusing to overwrite stadium registry: {REGISTRY}")
    predictions = pd.read_csv(PREDICTIONS)
    schedule = pd.read_csv(SCHEDULES)
    games = predictions[["game_id"]].merge(
        schedule[["game_id", "stadium_id", "stadium", "roof"]], on="game_id", validate="one_to_one"
    )
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    with REGISTRY.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=REGISTRY_FIELDS); writer.writeheader()
        for game in games.to_dict("records"):
            writer.writerow({**game, "latitude": "", "longitude": "", "coordinate_source": "",
                             "coordinate_verified_at_utc": "", "coordinate_verified": False})
    return {"status": "registry_created_coordinates_unresolved", "games": len(games),
            "verified_coordinates": 0, "path": str(REGISTRY.relative_to(ROOT))}


def validate_registry(path: Path = REGISTRY) -> dict:
    rows = pd.read_csv(path, dtype=str).fillna("")
    errors = []
    if rows.game_id.duplicated().any():
        errors.append("duplicate game_id")
    for row in rows.to_dict("records"):
        if row["coordinate_verified"].lower() not in {"true", "1"}:
            errors.append(f"{row['game_id']}: coordinates not verified")
            continue
        try:
            latitude, longitude = float(row["latitude"]), float(row["longitude"])
            if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
                raise ValueError("coordinates outside range")
            if not row["coordinate_source"]:
                raise ValueError("coordinate source missing")
            _parse_aware(row["coordinate_verified_at_utc"], "coordinate_verified_at_utc")
        except ValueError as exc:
            errors.append(f"{row['game_id']}: {exc}")
    return {"status": "valid" if not errors else "unresolved", "games": len(rows),
            "verified_coordinates": len(rows) - len([e for e in errors if "duplicate" not in e]),
            "errors": errors}


def forecast_url(latitude: float, longitude: float, kickoff: datetime) -> str:
    params = {
        "latitude": latitude, "longitude": longitude,
        "hourly": "temperature_2m,precipitation,wind_speed_10m,wind_gusts_10m",
        "temperature_unit": "fahrenheit", "wind_speed_unit": "mph",
        "precipitation_unit": "inch", "timezone": "UTC",
        "start_date": kickoff.date().isoformat(), "end_date": kickoff.date().isoformat(),
    }
    return f"{API_URL}?{urllib.parse.urlencode(params)}"


def normalize_forecast(payload: dict[str, Any], kickoff: datetime) -> dict[str, float | str]:
    """Aggregate kickoff through the next three hourly forecast points."""
    kickoff = kickoff.astimezone(timezone.utc)
    hourly = payload.get("hourly", {})
    times = [_parse_aware(value + "Z" if "+" not in value and not value.endswith("Z") else value, "forecast_time")
             for value in hourly.get("time", [])]
    indexes = [i for i, stamp in enumerate(times) if kickoff - timedelta(minutes=30) <= stamp <= kickoff + timedelta(hours=3, minutes=30)]
    if not indexes:
        raise ValueError("forecast does not cover kickoff window")
    def values(name: str) -> list[float]:
        source = hourly.get(name, [])
        selected = [float(source[i]) for i in indexes if i < len(source) and source[i] is not None]
        if not selected:
            raise ValueError(f"forecast variable missing in kickoff window: {name}")
        return selected
    temperature, precipitation = values("temperature_2m"), values("precipitation")
    wind, gust = values("wind_speed_10m"), values("wind_gusts_10m")
    return {
        "window_start_utc": times[indexes[0]].isoformat(), "window_end_utc": times[indexes[-1]].isoformat(),
        "temperature_f_mean": sum(temperature) / len(temperature),
        "precipitation_in_sum": sum(precipitation), "wind_mph_max": max(wind),
        "wind_gust_mph_max": max(gust), "forecast_hours": len(indexes),
    }


def collect() -> dict:
    registry = validate_registry()
    if registry["status"] != "valid":
        return {**registry, "status": "unresolved_no_weather_capture", "archived": False,
                "staking_enabled": False}
    captured_at = datetime.now(timezone.utc)
    rows = pd.read_csv(REGISTRY)
    predictions = pd.read_csv(PREDICTIONS)
    schedule = pd.read_csv(SCHEDULES)
    games = predictions[["game_id", "gameday", "gametime"]].merge(rows, on="game_id", validate="one_to_one")
    normalized, raw = [], {}
    for game in games.itertuples(index=False):
        kickoff = datetime.fromisoformat(f"{game.gameday}T{game.gametime}").replace(tzinfo=EASTERN).astimezone(timezone.utc)
        url = forecast_url(float(game.latitude), float(game.longitude), kickoff)
        with urllib.request.urlopen(url, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
        raw[game.game_id] = payload
        normalized.append({"game_id": game.game_id, "captured_at_utc": captured_at.isoformat(),
                           "kickoff_at_utc": kickoff.isoformat(), "provider": "open_meteo",
                           "latitude": game.latitude, "longitude": game.longitude,
                           **normalize_forecast(payload, kickoff), "valid_live_forecast": True,
                           "staking_enabled": False})
    stamp = captured_at.strftime("%Y%m%dT%H%M%S%fZ")
    raw_path = ARCHIVE / f"week01_{stamp}_raw.json"; csv_path = ARCHIVE / f"week01_{stamp}.csv"
    manifest_path = REPORTS / f"week01_{stamp}.json"
    for path in (raw_path, csv_path, manifest_path):
        if path.exists(): raise RuntimeError(f"refusing to overwrite forecast capture: {path}")
    ARCHIVE.mkdir(parents=True, exist_ok=True); REPORTS.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")
    pd.DataFrame(normalized).to_csv(csv_path, index=False)
    manifest = {"status": "weather_shadow_captured", "captured_at_utc": captured_at.isoformat(),
                "games": len(normalized), "staking_enabled": False,
                "sha256": {"registry": _sha256(REGISTRY), "raw": _sha256(raw_path), "normalized": _sha256(csv_path)}}
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("action", choices=("prepare-registry", "validate-registry", "collect"))
    args = parser.parse_args()
    result = prepare_registry() if args.action == "prepare-registry" else validate_registry() if args.action == "validate-registry" else collect()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
