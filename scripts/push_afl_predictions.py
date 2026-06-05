#!/usr/bin/env python3
"""
scripts/push_afl_predictions.py

Reads the latest AFL pricing CSV from BettingEngine/results/,
derives home/away scores from rules margin + total,
writes data/afl/predictions/latest.json, and pushes to Supabase
under key 'afl_predictions'.

Run every Thursday at 09:00 alongside NRL predictions push.

Round detection:
  1. Reads round_number from inside the highest-numbered r{N}_afl_2026.csv
  2. Fallback: highest N from filename regex
"""

import csv
import json
import os
import re
import sys
from pathlib import Path
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BETMATE_ROOT    = Path(os.environ.get('BETMATE_ROOT', Path(__file__).resolve().parent.parent))
ENGINE_ROOT     = BETMATE_ROOT / 'BettingEngine'
RESULTS_DIR     = ENGINE_ROOT / 'results'
PREDICTIONS_OUT = BETMATE_ROOT / 'data' / 'afl' / 'predictions' / 'latest.json'


# ---------------------------------------------------------------------------
# Find latest AFL pricing CSV (by highest round number in filename)
# ---------------------------------------------------------------------------
def find_latest_csv() -> Path:
    def round_num(p: Path) -> int:
        m = re.match(r'r(\d+)_afl_\d+\.csv$', p.name)
        return int(m.group(1)) if m else -1

    csvs = [p for p in RESULTS_DIR.glob('r*_afl_*.csv') if round_num(p) >= 0]
    if not csvs:
        print('ERROR: No AFL pricing CSV found in BettingEngine/results/')
        sys.exit(1)
    latest = max(csvs, key=round_num)
    print(f'  Using: {latest.name}  (round {round_num(latest)})')
    return latest


# ---------------------------------------------------------------------------
# Parse CSV -> predictions list
# Scores derived from rules model: home = (total + margin) / 2
# ---------------------------------------------------------------------------
def parse_predictions(csv_path: Path) -> list:
    predictions = []
    with open(csv_path, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            home = row['home_team'].strip()
            away = row['away_team'].strip()
            try:
                margin = float(row['rules_margin'])
                total  = float(row['rules_total'])
                home_score = round((total + margin) / 2, 1)
                away_score = round((total - margin) / 2, 1)
            except (ValueError, KeyError):
                print(f'  SKIP: {home} vs {away} -- missing score data')
                continue
            predictions.append({
                'homeTeam':      home,
                'awayTeam':      away,
                'predHomeScore': home_score,
                'predAwayScore': away_score,
            })
    return predictions


# ---------------------------------------------------------------------------
# Write local JSON
# ---------------------------------------------------------------------------
def write_local(predictions: list) -> None:
    PREDICTIONS_OUT.parent.mkdir(parents=True, exist_ok=True)
    PREDICTIONS_OUT.write_text(json.dumps(predictions, indent=2), encoding='utf-8')
    print(f'  Written: {PREDICTIONS_OUT}')


# ---------------------------------------------------------------------------
# Push to Supabase
# ---------------------------------------------------------------------------
def push_supabase(predictions: list) -> bool:
    env_path = BETMATE_ROOT / '.env.local'
    if env_path.exists():
        for line in env_path.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                k, _, v = line.partition('=')
                os.environ.setdefault(k.strip(), v.strip())

    url     = os.environ.get('NEXT_PUBLIC_SUPABASE_URL', '').rstrip('/')
    svc_key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '')
    if not url or not svc_key:
        print('  Supabase env vars not set -- skipping push')
        return False

    try:
        import requests
        payload = [{
            'key':        'afl_predictions',
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
        print(f'  Supabase push: OK')
        return True
    except Exception as e:
        print(f'  Supabase push failed: {e}')
        return False


# ---------------------------------------------------------------------------
# Endpoint health-check — catches middleware/deployment issues immediately
# ---------------------------------------------------------------------------
def verify_endpoint(predictions: list) -> None:
    """
    Hit the live Vercel endpoint and confirm predictions come back.
    Catches 401 (missing from middleware PUBLIC_PATHS), 404 (route not deployed),
    or empty response — all of which cause silent failures on the odds board.
    """
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
        url = f'{vercel_url.rstrip("/")}/api/afl-predictions'
        resp = requests.get(url, timeout=10)
        if resp.status_code == 401:
            print(f'  WARNING: /api/afl-predictions returned 401 -- route is missing from middleware.ts PUBLIC_PATHS!')
            print(f'  ACTION:  Add "/api/afl-predictions" to PUBLIC_PATHS in middleware.ts and redeploy.')
        elif resp.status_code == 404:
            print(f'  WARNING: /api/afl-predictions returned 404 -- route not deployed to Vercel yet.')
        elif resp.ok:
            data = resp.json()
            count = len(data.get('predictions', []))
            if count == 0:
                print(f'  WARNING: endpoint returned 0 predictions -- Supabase data may not have been read.')
            else:
                print(f'  Endpoint check: OK ({count} predictions live on Vercel)')
        else:
            print(f'  WARNING: endpoint returned {resp.status_code}')
    except Exception as e:
        print(f'  Endpoint check skipped (could not reach {vercel_url}): {e}')


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print(f'\n[{datetime.now().strftime("%Y-%m-%d %H:%M")}] push_afl_predictions.py')
    print(f'  BETMATE_ROOT: {BETMATE_ROOT}')

    csv_path    = find_latest_csv()
    predictions = parse_predictions(csv_path)

    if not predictions:
        print('  ERROR: No predictions parsed -- aborting')
        sys.exit(1)

    print(f'\n  {len(predictions)} games:')
    for p in predictions:
        print(f'    {p["homeTeam"]} {p["predHomeScore"]} - {p["predAwayScore"]} {p["awayTeam"]}')

    write_local(predictions)
    push_supabase(predictions)
    verify_endpoint(predictions)
    print('\n  Done.\n')


if __name__ == '__main__':
    main()
