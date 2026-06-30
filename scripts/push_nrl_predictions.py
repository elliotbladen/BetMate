#!/usr/bin/env python3
"""
scripts/push_nrl_predictions.py

Reads the latest NRL pricing CSV from BettingEngine/results/,
converts team names to Odds API format, writes data/nrl/predictions/latest.json,
and pushes to Supabase under key 'nrl_predictions'.

Run every Thursday at 09:00 after pricing is complete.
"""

import csv
import json
import os
import sys
from pathlib import Path
from datetime import datetime

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BETMATE_ROOT    = Path(os.environ.get('BETMATE_ROOT', Path(__file__).resolve().parent.parent))
ENGINE_ROOT     = BETMATE_ROOT / 'BettingEngine'
RESULTS_DIR     = ENGINE_ROOT / 'results'
PREDICTIONS_OUT = BETMATE_ROOT / 'data' / 'nrl' / 'predictions' / 'latest.json'
FIXTURE_PATH    = BETMATE_ROOT / 'data' / 'nrl' / 'fixture' / 'processed' / 'latest-fixture.json'

# ---------------------------------------------------------------------------
# Team name mapping: BettingEngine CSV name -> Odds API name
# ---------------------------------------------------------------------------
TEAM_MAP = {
    'Manly-Warringah Sea Eagles':       'Manly Warringah Sea Eagles',
    'Cronulla-Sutherland Sharks':       'Cronulla Sutherland Sharks',
    'Canterbury-Bankstown Bulldogs':    'Canterbury Bulldogs',
    'St. George Illawarra Dragons':     'St George Illawarra Dragons',
}

def to_odds_api_name(name: str) -> str:
    return TEAM_MAP.get(name.strip(), name.strip())


# ---------------------------------------------------------------------------
# Find pricing CSV for the current round
# ---------------------------------------------------------------------------
def find_current_csv() -> Path:
    # Read round + season from BetMate fixture (same source the pricing pipeline uses)
    if FIXTURE_PATH.exists():
        fixture = json.loads(FIXTURE_PATH.read_text(encoding='utf-8'))
        season  = fixture.get('season', 2026)
        round_  = fixture.get('round')
        if round_:
            candidate = RESULTS_DIR / f'r{round_}_pricing_{season}.csv'
            if candidate.exists():
                print(f'  Round {round_} from fixture — using: {candidate.name}')
                return candidate
            else:
                print(f'  WARNING: Fixture says R{round_} but {candidate.name} not found — falling back to highest round')
    else:
        print(f'  WARNING: Fixture not found at {FIXTURE_PATH} — falling back to highest round')

    # Fallback: highest round number in filename (not mtime — avoids stale edits)
    import re
    csvs = list(RESULTS_DIR.glob('r*_pricing_*.csv'))
    if not csvs:
        print('ERROR: No pricing CSV found in BettingEngine/results/')
        sys.exit(1)
    def round_num(p: Path) -> int:
        m = re.match(r'r(\d+)_pricing_', p.name)
        return int(m.group(1)) if m else 0
    latest = max(csvs, key=round_num)
    print(f'  Fallback — using: {latest.name}')
    return latest


# ---------------------------------------------------------------------------
# Parse CSV -> predictions list
# ---------------------------------------------------------------------------
def parse_predictions(csv_path: Path) -> list:
    predictions = []
    with open(csv_path, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            home = to_odds_api_name(row['home_team'])
            away = to_odds_api_name(row['away_team'])
            try:
                pred_home = round(float(row['pred_home_score']), 1)
                pred_away = round(float(row['pred_away_score']), 1)
            except (ValueError, KeyError):
                print(f'  SKIP: {home} vs {away} -- missing score data')
                continue

            def _num(field: str):
                try:
                    value = float(row.get(field, ''))
                except (TypeError, ValueError):
                    return None
                return round(value, 3)

            fair_home_odds = _num('fair_home_odds')
            fair_away_odds = _num('fair_away_odds')
            fair_hcap_line = _num('fair_hcap_line')

            predictions.append({
                'homeTeam':      home,
                'awayTeam':      away,
                'predHomeScore': pred_home,
                'predAwayScore': pred_away,
                'h2hHome105':    round(fair_home_odds / 1.05, 2) if fair_home_odds else None,
                'h2hAway105':    round(fair_away_odds / 1.05, 2) if fair_away_odds else None,
                'hcapLine105':   fair_hcap_line,
                'hcapPrice105':   1.905,
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

    url = os.environ.get('NEXT_PUBLIC_SUPABASE_URL', '').rstrip('/')
    svc_key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '')
    if not url or not svc_key:
        print('  Supabase env vars not set -- skipping push')
        return False

    try:
        import requests
        from datetime import timezone
        payload = [{
            'key':        'nrl_predictions',
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
    Hit the live Vercel endpoint and confirm at least one prediction comes back.
    Catches 401 (missing from middleware PUBLIC_PATHS), 404 (route not deployed),
    or empty response — all of which would cause silent failures on the odds board.
    """
    env_path = BETMATE_ROOT / '.env.local'
    vercel_url = None
    if env_path.exists():
        for line in env_path.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if line.startswith('NEXT_PUBLIC_SITE_URL=') or line.startswith('VERCEL_URL='):
                vercel_url = line.split('=', 1)[1].strip()
                break

    # Fallback to known production URL
    if not vercel_url:
        vercel_url = 'https://bet-mate-ten.vercel.app'

    try:
        import requests
        url = f'{vercel_url.rstrip("/")}/api/nrl-predictions'
        resp = requests.get(url, timeout=10)
        if resp.status_code == 401:
            print(f'  WARNING: /api/nrl-predictions returned 401 -- route is missing from middleware.ts PUBLIC_PATHS!')
            print(f'  ACTION:  Add "/api/nrl-predictions" to PUBLIC_PATHS in middleware.ts and redeploy.')
        elif resp.status_code == 404:
            print(f'  WARNING: /api/nrl-predictions returned 404 -- route not deployed to Vercel yet.')
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
    print(f'\n[{datetime.now().strftime("%Y-%m-%d %H:%M")}] push_nrl_predictions.py')
    print(f'  BETMATE_ROOT: {BETMATE_ROOT}')

    csv_path    = find_current_csv()
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
