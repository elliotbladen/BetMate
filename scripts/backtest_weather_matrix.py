import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
WEATHER_DIR = ROOT / "data" / "weather" / "2026"


def old_flags(wind_speed: float, wind_gust: float) -> list[str]:
    if wind_speed > 60:
        return ["STRONG WIND"]
    if wind_speed > 35:
        return ["WIND"]
    return []


def new_flags(wind_speed: float, wind_gust: float) -> list[str]:
    effective_wind = max(wind_speed, wind_gust * 0.65)
    if effective_wind > 60 or wind_gust >= 70:
        return ["STRONG WIND"]
    if effective_wind > 35 or wind_gust >= 45:
        return ["WIND"]
    if wind_gust >= 35:
        return ["GUSTS"]
    return []


def to_float(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def main() -> None:
    rows = []
    for path in sorted(WEATHER_DIR.glob("*.csv")):
        with open(path, newline="", encoding="utf-8-sig") as fh:
            for row in csv.DictReader(fh):
                wind_speed = to_float(row.get("wind_speed", "0"))
                wind_gust = to_float(row.get("wind_gust", "0"))
                old = old_flags(wind_speed, wind_gust)
                new = new_flags(wind_speed, wind_gust)
                rows.append((path.name, row, old, new))

    missed_gusts = [
        (path_name, row, new)
        for path_name, row, old, new in rows
        if not old and new
    ]
    upgraded = [
        (path_name, row, old, new)
        for path_name, row, old, new in rows
        if old != new
    ]

    print(f"Weather rows checked: {len(rows)}")
    print(f"Rows with changed wind classification: {len(upgraded)}")
    print(f"Rows old model marked no-wind but new model flags: {len(missed_gusts)}")
    print()
    print("Top missed gust rows:")
    for path_name, row, new in sorted(
        missed_gusts,
        key=lambda item: to_float(item[1].get("wind_gust", "0")),
        reverse=True,
    )[:15]:
        print(
            f"{path_name} {row.get('commence_time', '')} "
            f"lat={row.get('lat')} lon={row.get('lon')} "
            f"temp={row.get('temperature')} wind={row.get('wind_speed')} "
            f"gust={row.get('wind_gust')} new={'|'.join(new)} "
            f"old_flags={row.get('flags', '')}"
        )


if __name__ == "__main__":
    main()
