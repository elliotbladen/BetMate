"""
scripts/fetch_weather.py

Fetch weather conditions for all matches in a given round and upsert into
the weather_conditions table.

Data sources:
  - Open-Meteo (free, no key)  — all Australian venues
  - MetService (NZ met service) — Auckland venues (Go Media Stadium)

The integration seam is fetch_weather_for_match().  To replace with an
agent/OpenClaw call, swap out that function's body only — the caller and
DB upsert logic remain unchanged.

Usage:
    python scripts/fetch_weather.py --season 2026 --round 7
    python scripts/fetch_weather.py --season 2026 --round 7 --mock-clear
    python scripts/fetch_weather.py --season 2026 --round 7 --dry-run
"""

import argparse
import sqlite3
import sys
import urllib.request
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / 'data' / 'model.db'

sys.path.insert(0, str(ROOT))
from pricing.tier8_weather import classify_condition, compute_dew_risk


# ---------------------------------------------------------------------------
# Tomorrow.io fetch — same source as BetMate weather API
# ---------------------------------------------------------------------------

def _load_tomorrow_api_key() -> str:
    env_path = ROOT.parent / '.env.local'
    if not env_path.exists():
        raise RuntimeError(f'.env.local not found at {env_path}')
    with open(env_path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith('TOMORROW_API_KEY='):
                return line.split('=', 1)[1].strip().strip('"').strip("'")
    raise RuntimeError('TOMORROW_API_KEY not found in .env.local')


def _fetch_tomorrow_io(lat: float, lng: float, kickoff_datetime: str) -> dict:
    """
    Fetch hourly weather from Tomorrow.io for (lat, lng) at kickoff time.
    Uses the same endpoint and field set as the BetMate weather API route.

    windSpeed is returned in m/s by Tomorrow.io — converted to km/h here.
    Returns dict: temp_c, dew_point_c, humidity_pct, wind_kmh, precipitation_mm, data_source
    Raises RuntimeError on API failure.
    """
    api_key = _load_tomorrow_api_key()
    fields = (
        'temperature,windSpeed,windGust,'
        'precipitationProbability,precipitationIntensity,'
        'dewPoint,humidity'
    )
    url = (
        f'https://api.tomorrow.io/v4/weather/forecast'
        f'?location={lat},{lng}'
        f'&apikey={api_key}'
        f'&fields={fields}'
        f'&timesteps=1h'
        f'&units=metric'
    )
    try:
        req = urllib.request.Request(url, headers={'Accept': 'application/json'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
    except Exception as exc:
        raise RuntimeError(f'Tomorrow.io request failed: {exc}') from exc

    hourly = data.get('timelines', {}).get('hourly', [])
    if not hourly:
        raise RuntimeError('Tomorrow.io returned no hourly data')

    # Find the entry closest to kickoff time
    try:
        game_ts = datetime.fromisoformat(
            kickoff_datetime.replace('Z', '+00:00')
        ).timestamp()
        target = min(
            hourly,
            key=lambda h: abs(
                datetime.fromisoformat(h['time'].replace('Z', '+00:00')).timestamp()
                - game_ts
            ),
        )
    except (ValueError, AttributeError):
        target = hourly[0]

    v = target['values']
    # Tomorrow.io windSpeed is in m/s — multiply by 3.6 for km/h
    wind_kmh = round((v.get('windSpeed') or 0.0) * 3.6, 1)

    return {
        'temp_c':           v.get('temperature'),
        'dew_point_c':      v.get('dewPoint'),
        'humidity_pct':     v.get('humidity'),
        'wind_kmh':         wind_kmh,
        'precipitation_mm': v.get('precipitationIntensity') or 0.0,
        'data_source':      'tomorrow_io',
    }


# ---------------------------------------------------------------------------
# Main fetch integration seam
# ---------------------------------------------------------------------------

def fetch_weather_for_match(
    match_id: int,
    venue_id: int,
    venue_name: str,
    lat: float,
    lng: float,
    kickoff_datetime: str,
) -> dict:
    """
    Fetch raw weather for a single match via Tomorrow.io.

    Args:
        match_id:         DB match_id (for logging only).
        venue_id:         DB venue_id (for logging only).
        venue_name:       Human-readable name (for logging only).
        lat, lng:         Venue coordinates.
        kickoff_datetime: ISO local datetime, e.g. '2026-04-10T19:50:00'.

    Returns raw weather dict (without classification or delta).
    Raises RuntimeError on failure.
    """
    return _fetch_tomorrow_io(lat, lng, kickoff_datetime)


# ---------------------------------------------------------------------------
# Classification + upsert
# ---------------------------------------------------------------------------

def _mock_clear_row(match_id: int, venue_id: int, kickoff_datetime: str) -> dict:
    return {
        'match_id':         match_id,
        'venue_id':         venue_id,
        'kickoff_time':     kickoff_datetime,
        'temp_c':           20.0,
        'dew_point_c':      5.0,
        'humidity_pct':     40.0,
        'wind_kmh':         5.0,
        'precipitation_mm': 0.0,
        'condition_type':   'clear',
        'dew_risk':         0,
        'totals_delta':     0.0,
        'data_source':      'mock_clear',
    }


def build_weather_row(
    match_id: int,
    venue_id: int,
    kickoff_datetime: str,
    raw: dict,
) -> dict:
    """Classify raw weather data and assemble the full DB row."""
    temp_c           = raw.get('temp_c') or 0.0
    dew_point_c      = raw.get('dew_point_c') or 0.0
    wind_kmh         = raw.get('wind_kmh') or 0.0
    precipitation_mm = raw.get('precipitation_mm') or 0.0

    dew_risk_bool = compute_dew_risk(kickoff_datetime, temp_c, dew_point_c)
    condition_type, totals_delta = classify_condition(precipitation_mm, wind_kmh, dew_risk_bool)

    return {
        'match_id':         match_id,
        'venue_id':         venue_id,
        'kickoff_time':     kickoff_datetime,
        'temp_c':           round(temp_c, 1) if temp_c is not None else None,
        'dew_point_c':      round(dew_point_c, 1) if dew_point_c is not None else None,
        'humidity_pct':     round(raw.get('humidity_pct') or 0.0, 1),
        'wind_kmh':         round(wind_kmh, 1),
        'precipitation_mm': round(precipitation_mm, 2),
        'condition_type':   condition_type,
        'dew_risk':         int(dew_risk_bool),
        'totals_delta':     totals_delta,
        'data_source':      raw.get('data_source', 'open_meteo'),
    }


def upsert_weather(conn: sqlite3.Connection, row: dict, dry_run: bool = False) -> None:
    if dry_run:
        return
    conn.execute(
        """
        INSERT INTO weather_conditions
            (match_id, venue_id, kickoff_time, temp_c, dew_point_c, humidity_pct,
             wind_kmh, precipitation_mm, condition_type, dew_risk, totals_delta,
             data_source, fetched_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)
        ON CONFLICT(match_id) DO UPDATE SET
            venue_id          = excluded.venue_id,
            kickoff_time      = excluded.kickoff_time,
            temp_c            = excluded.temp_c,
            dew_point_c       = excluded.dew_point_c,
            humidity_pct      = excluded.humidity_pct,
            wind_kmh          = excluded.wind_kmh,
            precipitation_mm  = excluded.precipitation_mm,
            condition_type    = excluded.condition_type,
            dew_risk          = excluded.dew_risk,
            totals_delta      = excluded.totals_delta,
            data_source       = excluded.data_source,
            fetched_at        = CURRENT_TIMESTAMP
        """,
        (
            row['match_id'], row['venue_id'], row['kickoff_time'],
            row['temp_c'], row['dew_point_c'], row['humidity_pct'],
            row['wind_kmh'], row['precipitation_mm'], row['condition_type'],
            row['dew_risk'], row['totals_delta'], row['data_source'],
        ),
    )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='Fetch T7 weather for a round')
    parser.add_argument('--season', type=int, required=True)
    parser.add_argument('--round', type=int, required=True, dest='round_number')
    parser.add_argument('--mock-clear', action='store_true',
                        help='Skip API calls — insert clear conditions for all games')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    matches = conn.execute(
        """
        SELECT m.match_id, m.venue_id, m.kickoff_datetime,
               v.venue_name, v.lat, v.lng
        FROM matches m
        LEFT JOIN venues v ON v.venue_id = m.venue_id
        WHERE m.season = ? AND m.round_number = ?
        ORDER BY m.match_date, m.match_id
        """,
        (args.season, args.round_number),
    ).fetchall()

    if not matches:
        print(f'No matches found for S{args.season} R{args.round_number}', file=sys.stderr)
        sys.exit(1)

    print(f'Fetching T7 weather for S{args.season} R{args.round_number} '
          f'({len(matches)} games)'
          + (' [mock-clear]' if args.mock_clear else '')
          + (' [dry-run]' if args.dry_run else ''))
    print()

    ok = 0
    for m in matches:
        mid        = m['match_id']
        vid        = m['venue_id']
        vname      = m['venue_name'] or f'venue_id={vid}'
        lat        = m['lat']
        lng        = m['lng']
        kickoff    = m['kickoff_datetime']

        if lat is None or lng is None:
            print(f'  match={mid}  {vname}: SKIP — no lat/lng in venues table')
            continue

        try:
            if args.mock_clear:
                row = _mock_clear_row(mid, vid, kickoff)
            else:
                raw = fetch_weather_for_match(mid, vid, vname, lat, lng, kickoff)
                row = build_weather_row(mid, vid, kickoff, raw)

            upsert_weather(conn, row, dry_run=args.dry_run)

            dew_str = ' [dew]' if row['dew_risk'] else ''
            print(f'  match={mid}  {vname:<32}  '
                  f'{row["condition_type"]:<28}  '
                  f'T={row["temp_c"]}°C  '
                  f'Dp={row["dew_point_c"]}°C  '
                  f'W={row["wind_kmh"]}km/h  '
                  f'P={row["precipitation_mm"]}mm  '
                  f'Δtot={row["totals_delta"]:+.1f}{dew_str}  '
                  f'[{row["data_source"]}]')
            ok += 1

        except Exception as exc:
            print(f'  match={mid}  {vname}: ERROR — {exc}')

    if not args.dry_run:
        conn.commit()

    print()
    print(f'Done — {ok}/{len(matches)} weather rows written.')
    conn.close()


if __name__ == '__main__':
    main()
