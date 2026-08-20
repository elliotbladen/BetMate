#!/usr/bin/env python3
"""
scripts/push_football_predictions.py

Reads the latest EPL and Championship pricing JSONs from
BettingEngine/outputs/football/{league}/, maps team names to Odds API format,
writes data/{league}/predictions/latest.json, and pushes to Supabase.

Usage:
    python scripts/push_football_predictions.py              # both leagues
    python scripts/push_football_predictions.py --league epl  # EPL only
"""

import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BETMATE_ROOT = Path(os.environ.get('BETMATE_ROOT', Path(__file__).resolve().parent.parent))
ENGINE_ROOT  = BETMATE_ROOT / 'BettingEngine'
OUTPUTS_DIR  = ENGINE_ROOT / 'outputs' / 'football'

# ---------------------------------------------------------------------------
# Model short name -> Odds API name mapping
# The pricing engine uses short names; the Odds API and soccerTeams.ts use
# full names. Unmapped names pass through as-is (works for teams like
# Arsenal, Liverpool, Everton, etc. that are the same in both).
# ---------------------------------------------------------------------------
EPL_TEAM_MAP = {
    'Man City':       'Manchester City',
    'Man United':     'Manchester United',
    'Nott\'m Forest': 'Nottingham Forest',
    'Nottm Forest':   'Nottingham Forest',
    'Newcastle':      'Newcastle United',
    'Tottenham':      'Tottenham Hotspur',
    'Brighton':       'Brighton and Hove Albion',
    'Bournemouth':    'AFC Bournemouth',
    'Leeds':          'Leeds United',
    'Hull':           'Hull City',
    'Ipswich':        'Ipswich Town',
    'Coventry':       'Coventry City',
    'Wolves':         'Wolverhampton Wanderers',
    'West Ham':       'West Ham United',
    'Burnley':        'Burnley',
}

CHAMPIONSHIP_TEAM_MAP = {
    'Birmingham':     'Birmingham City',
    'Blackburn':      'Blackburn Rovers',
    'Bolton':         'Bolton Wanderers',
    'Cardiff':        'Cardiff City',
    'Charlton':       'Charlton Athletic',
    'Coventry':       'Coventry City',
    'Derby':          'Derby County',
    'Hull':           'Hull City',
    'Ipswich':        'Ipswich Town',
    'Leeds':          'Leeds United',
    'Leicester':      'Leicester City',
    'Lincoln':        'Lincoln City',
    'Luton':          'Luton Town',
    'Norwich':        'Norwich City',
    'Oxford':         'Oxford United',
    'Preston':        'Preston North End',
    'QPR':            'Queens Park Rangers',
    'Sheffield United': 'Sheffield United',
    'Sheffield Wed':  'Sheffield Wednesday',
    'Stoke':          'Stoke City',
    'Swansea':        'Swansea City',
    'West Brom':      'West Bromwich Albion',
    'West Ham':       'West Ham United',
    'Wolves':         'Wolverhampton Wanderers',
}

TEAM_MAPS = {
    'epl': EPL_TEAM_MAP,
    'championship': CHAMPIONSHIP_TEAM_MAP,
}


def to_odds_api_name(name: str, league: str) -> str:
    mapping = TEAM_MAPS.get(league, {})
    return mapping.get(name.strip(), name.strip())


# ---------------------------------------------------------------------------
# Find latest pricing JSON for a league
# ---------------------------------------------------------------------------
def find_latest_prices(league: str) -> Path | None:
    league_dir = OUTPUTS_DIR / league
    if not league_dir.exists():
        print(f'  WARNING: {league_dir} does not exist')
        return None

    # Look for gw*_prices_*.json files (the standard output format)
    candidates = list(league_dir.glob('gw*_prices_*.json'))
    if not candidates:
        print(f'  WARNING: No gw*_prices_*.json files in {league_dir}')
        return None

    # Sort by modification time, newest first
    latest = max(candidates, key=lambda p: p.stat().st_mtime)
    print(f'  Using: {latest.name}')
    return latest


# ---------------------------------------------------------------------------
# Parse JSON -> predictions list
# ---------------------------------------------------------------------------
def parse_predictions(json_path: Path, league: str) -> list:
    raw = json.loads(json_path.read_text(encoding='utf-8'))

    # Handle both formats: bare array (EPL) or wrapped {"games": [...]} (Championship)
    if isinstance(raw, list):
        games = raw
    elif isinstance(raw, dict) and 'games' in raw:
        games = raw['games']
    else:
        print(f'  ERROR: Unrecognised JSON format in {json_path.name}')
        return []

    predictions = []
    for g in games:
        home = to_odds_api_name(g.get('home', ''), league)
        away = to_odds_api_name(g.get('away', ''), league)

        # xG lambdas as "predicted scores" — meaningful for soccer
        pred_home = round(g.get('lambda_home', 0), 2)
        pred_away = round(g.get('lambda_away', 0), 2)

        # 3-way fair odds at 105% margin (same convention as NRL/AFL)
        fair_home = g.get('fair_home')
        fair_draw = g.get('fair_draw')
        fair_away = g.get('fair_away')
        fair_over25 = g.get('fair_over25')
        fair_under25 = g.get('fair_under25')

        def _at_105(odds):
            if odds is None:
                return None
            return round(odds / 1.05, 2)

        predictions.append({
            'homeTeam':      home,
            'awayTeam':      away,
            'predHomeScore': pred_home,
            'predAwayScore': pred_away,
            'h2hHome105':    _at_105(fair_home),
            'h2hDraw105':    _at_105(fair_draw),
            'h2hAway105':    _at_105(fair_away),
            'over25_105':    _at_105(fair_over25),
            'under25_105':   _at_105(fair_under25),
        })
    return predictions


# ---------------------------------------------------------------------------
# Write local JSON
# ---------------------------------------------------------------------------
def write_local(predictions: list, league: str) -> None:
    out_path = BETMATE_ROOT / 'data' / league / 'predictions' / 'latest.json'
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(predictions, indent=2), encoding='utf-8')
    print(f'  Written: {out_path}')


# ---------------------------------------------------------------------------
# Push to Supabase
# ---------------------------------------------------------------------------
def push_supabase(predictions: list, league: str) -> bool:
    env_path = BETMATE_ROOT / '.env.local'
    if env_path.exists():
        for line in env_path.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                k, _, v = line.partition('=')
                os.environ.setdefault(k.strip(), v.strip())

    url = os.environ.get('NEXT_PUBLIC_SUPABASE_URL', '').rstrip('/')
    svc_key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '')
    if not url or not svc_key:
        print('  Supabase env vars not set -- skipping push')
        return False

    try:
        import requests
        key = f'{league}_predictions'
        payload = [{
            'key':        key,
            'data':       {'predictions': predictions},
            'updated_at': datetime.now(timezone.utc).isoformat(),
        }]
        resp = requests.post(
            f'{url}/rest/v1/betmate_data_store',
            headers={
                'apikey':        svc_key,
                'Authorization': f'Bearer {svc_key}',
                'Content-Type':  'application/json',
                'Prefer':        'resolution=merge-duplicates',
            },
            json=payload,
            timeout=10,
        )
        resp.raise_for_status()
        print(f'  Supabase push ({key}): OK')
        return True
    except Exception as e:
        print(f'  Supabase push failed: {e}')
        return False


# ---------------------------------------------------------------------------
# Endpoint health-check
# ---------------------------------------------------------------------------
def verify_endpoint(league: str) -> None:
    env_path = BETMATE_ROOT / '.env.local'
    vercel_url = None
    if env_path.exists():
        for line in env_path.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if line.startswith('NEXT_PUBLIC_SITE_URL=') or line.startswith('VERCEL_URL='):
                vercel_url = line.split('=', 1)[1].strip()
                break
    if not vercel_url:
        vercel_url = 'https://bet-mate-ten.vercel.app'

    try:
        import requests
        url = f'{vercel_url.rstrip("/")}/api/{league}-predictions'
        resp = requests.get(url, timeout=10)
        if resp.status_code == 401:
            print(f'  WARNING: /api/{league}-predictions returned 401 -- add to middleware.ts PUBLIC_PATHS!')
        elif resp.status_code == 404:
            print(f'  WARNING: /api/{league}-predictions returned 404 -- route not deployed yet.')
        elif resp.ok:
            data = resp.json()
            count = len(data.get('predictions', []))
            if count == 0:
                print(f'  WARNING: endpoint returned 0 predictions.')
            else:
                print(f'  Endpoint check: OK ({count} predictions live)')
        else:
            print(f'  WARNING: endpoint returned {resp.status_code}')
    except Exception as e:
        print(f'  Endpoint check skipped: {e}')


# ---------------------------------------------------------------------------
# Process one league
# ---------------------------------------------------------------------------
def process_league(league: str) -> None:
    print(f'\n  --- {league.upper()} ---')
    json_path = find_latest_prices(league)
    if not json_path:
        return

    predictions = parse_predictions(json_path, league)
    if not predictions:
        print('  ERROR: No predictions parsed')
        return

    print(f'  {len(predictions)} games:')
    for p in predictions:
        print(f'    {p["homeTeam"]} {p["predHomeScore"]:.2f} xG - {p["predAwayScore"]:.2f} xG {p["awayTeam"]}')
        print(f'      1X2: {p["h2hHome105"]} / {p["h2hDraw105"]} / {p["h2hAway105"]}  O/U 2.5: {p["over25_105"]} / {p["under25_105"]}')

    write_local(predictions, league)
    push_supabase(predictions, league)
    verify_endpoint(league)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--league', choices=['epl', 'championship'], default=None,
                        help='Process one league only (default: both)')
    args = parser.parse_args()

    print(f'\n[{datetime.now().strftime("%Y-%m-%d %H:%M")}] push_football_predictions.py')
    print(f'  BETMATE_ROOT: {BETMATE_ROOT}')

    leagues = [args.league] if args.league else ['epl', 'championship']
    for league in leagues:
        process_league(league)

    print('\n  Done.\n')


if __name__ == '__main__':
    main()
