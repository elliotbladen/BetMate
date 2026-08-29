#!/usr/bin/env python3
"""
scripts/baz_tipping.py

Registers Baz as a participant in the EPL tipping comp and submits tips.

Strategy v1: pick the favourite — the outcome with the highest model
probability (lowest fair odds) from our EPL predictions. Over the season
this will be tweaked with model-driven logic.

Usage:
    python scripts/baz_tipping.py                     # submit tips for current GW
    python scripts/baz_tipping.py --gameweek 2        # specific gameweek
    python scripts/baz_tipping.py --dry-run            # show picks without submitting
"""

import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BETMATE_ROOT = Path(os.environ.get('BETMATE_ROOT', Path(__file__).resolve().parent.parent))
PREDICTIONS_PATH = BETMATE_ROOT / 'data' / 'epl' / 'predictions' / 'latest.json'

BAZ_USER_ID = 'baz-bot'
BAZ_DISPLAY_NAME = 'Baz'
INVITE_CODE = 'BETMATE26'

# Base URL — local dev or production
BASE_URL = os.environ.get('BETMATE_URL', 'http://localhost:3000')


def load_env():
    """Load .env.local for BETMATE_URL if not set."""
    env_path = BETMATE_ROOT / '.env.local'
    if env_path.exists():
        for line in env_path.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                k, _, v = line.partition('=')
                os.environ.setdefault(k.strip(), v.strip())


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------
def api_get(path: str, params: dict | None = None) -> dict | None:
    import requests
    try:
        resp = requests.get(f'{BASE_URL}{path}', params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f'  ERROR GET {path}: {e}')
        return None


def api_post(path: str, body: dict) -> dict | None:
    import requests
    try:
        resp = requests.post(f'{BASE_URL}{path}', json=body, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f'  ERROR POST {path}: {e}')
        return None


# ---------------------------------------------------------------------------
# Step 1: Ensure Baz is in the comp
# ---------------------------------------------------------------------------
def ensure_joined() -> str | None:
    """Join the comp (idempotent). Returns comp_id or None."""
    # Check if already joined
    data = api_get('/api/tipping/join', {'user_id': BAZ_USER_ID})
    if data and data.get('comp'):
        comp_id = data['comp']['id']
        print(f'  Baz already in comp: {data["comp"]["name"]} (id: {comp_id})')
        return comp_id

    # Join
    data = api_post('/api/tipping/join', {
        'invite_code': INVITE_CODE,
        'user_id': BAZ_USER_ID,
        'display_name': BAZ_DISPLAY_NAME,
    })
    if data and data.get('comp'):
        comp_id = data['comp']['id']
        print(f'  Baz joined comp: {data["comp"]["name"]} (id: {comp_id})')
        return comp_id

    print('  ERROR: Could not join comp')
    return None


# ---------------------------------------------------------------------------
# Step 2: Load fixtures for the gameweek
# ---------------------------------------------------------------------------
def load_fixtures(gameweek: int) -> list:
    data = api_get('/api/tipping/fixtures', {'gameweek': str(gameweek)})
    if not data:
        return []
    fixtures = data.get('fixtures', [])
    print(f'  {len(fixtures)} fixtures for GW{gameweek}')
    return fixtures


# ---------------------------------------------------------------------------
# Step 3: Pick favourites from model predictions
# ---------------------------------------------------------------------------
def pick_tips(fixtures: list) -> list:
    """For each fixture, pick the outcome with the lowest fair odds (= highest probability)."""
    # Load predictions
    if not PREDICTIONS_PATH.exists():
        print(f'  WARNING: No predictions at {PREDICTIONS_PATH} — defaulting to home')
        return [{'game_id': f['id'], 'home_team': f['home_team'],
                 'away_team': f['away_team'], 'selection': 'home'} for f in fixtures]

    preds = json.loads(PREDICTIONS_PATH.read_text(encoding='utf-8'))
    pred_map = {p['homeTeam']: p for p in preds}

    tips = []
    for fix in fixtures:
        pred = pred_map.get(fix['home_team'])
        if not pred:
            # No prediction for this game — default to home
            print(f'    {fix["home_team"]} vs {fix["away_team"]}: no model prediction, defaulting to home')
            tips.append({
                'game_id': fix['id'],
                'home_team': fix['home_team'],
                'away_team': fix['away_team'],
                'selection': 'home',
            })
            continue

        # Find the outcome with the lowest odds (highest probability)
        home_odds = pred.get('h2hHome105') or 99
        draw_odds = pred.get('h2hDraw105') or 99
        away_odds = pred.get('h2hAway105') or 99

        best = min(
            ('home', home_odds),
            ('draw', draw_odds),
            ('away', away_odds),
            key=lambda x: x[1],
        )
        selection = best[0]

        print(f'    {fix["home_team"]} vs {fix["away_team"]}: '
              f'H {home_odds:.2f} / D {draw_odds:.2f} / A {away_odds:.2f} '
              f'-> {selection.upper()}')

        tips.append({
            'game_id': fix['id'],
            'home_team': fix['home_team'],
            'away_team': fix['away_team'],
            'selection': selection,
        })

    return tips


# ---------------------------------------------------------------------------
# Step 4: Submit tips
# ---------------------------------------------------------------------------
def submit_tips(comp_id: str, gameweek: int, tips: list) -> bool:
    data = api_post('/api/tipping/tips', {
        'comp_id': comp_id,
        'user_id': BAZ_USER_ID,
        'gameweek': gameweek,
        'tips': tips,
    })
    if not data:
        return False

    results = data.get('results', [])
    ok = sum(1 for r in results if r.get('success'))
    locked = sum(1 for r in results if 'kicked off' in str(r.get('error', '')))
    errors = sum(1 for r in results if r.get('error') and 'kicked off' not in str(r.get('error', '')))

    print(f'  Submitted: {ok} OK, {locked} locked, {errors} errors')
    return errors == 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description='Baz EPL tipping bot')
    parser.add_argument('--gameweek', type=int, default=1, help='Gameweek number (default: 1)')
    parser.add_argument('--dry-run', action='store_true', help='Show picks without submitting')
    args = parser.parse_args()

    load_env()

    print(f'\n[{datetime.now().strftime("%Y-%m-%d %H:%M")}] baz_tipping.py — GW{args.gameweek}')
    print(f'  Base URL: {BASE_URL}')

    # Step 1: Join
    if not args.dry_run:
        comp_id = ensure_joined()
        if not comp_id:
            sys.exit(1)
    else:
        comp_id = 'dry-run'
        print('  DRY RUN — skipping join')

    # Step 2: Fixtures
    fixtures = load_fixtures(args.gameweek)
    if not fixtures:
        print('  No fixtures — nothing to tip')
        sys.exit(0)

    # Step 3: Pick
    print('\n  Picks:')
    tips = pick_tips(fixtures)

    # Step 4: Submit
    if args.dry_run:
        print('\n  DRY RUN — not submitting')
    else:
        print()
        submit_tips(comp_id, args.gameweek, tips)

    print('\n  Done.\n')


if __name__ == '__main__':
    main()
