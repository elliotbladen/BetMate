"""
Push AFL match history to Supabase betmate_data_store key 'afl_match_history'.
Reads from BettingEngine/outputs/afl_weekly_review/historical/latest.xlsx (2022+).
Normalises short xlsx team names → full Odds API names so nickname matching works.
Run after each weekly Tuesday download.
"""
import os, json, sys
from datetime import datetime
from pathlib import Path
import openpyxl
import requests

ROOT  = Path(__file__).resolve().parent.parent
EXCEL = ROOT / "BettingEngine" / "outputs" / "afl_weekly_review" / "historical" / "latest.xlsx"
ENV   = ROOT / ".env.local"

# xlsx short name → full Odds API mascot name
# Nickname matching in the form route uses the LAST WORD of the full name:
#   "Hawthorn Hawks" → "hawks", "West Coast Eagles" → "eagles" etc.
# All 18 must map correctly or H2H/form silently returns nothing.
AFL_TEAM_MAP = {
    'Adelaide':          'Adelaide Crows',
    'Brisbane':          'Brisbane Lions',
    'Carlton':           'Carlton Blues',
    'Collingwood':       'Collingwood Magpies',
    'Essendon':          'Essendon Bombers',
    'Fremantle':         'Fremantle Dockers',
    'Geelong':           'Geelong Cats',
    'Gold Coast':        'Gold Coast Suns',
    'GWS Giants':        'Greater Western Sydney Giants',
    'Hawthorn':          'Hawthorn Hawks',
    'Melbourne':         'Melbourne Demons',
    'North Melbourne':   'North Melbourne Kangaroos',
    'Port Adelaide':     'Port Adelaide Power',
    'Richmond':          'Richmond Tigers',
    'St Kilda':          'St Kilda Saints',
    'Sydney':            'Sydney Swans',
    'West Coast':        'West Coast Eagles',
    'Western Bulldogs':  'Western Bulldogs',
}

def full_name(short: str) -> str:
    return AFL_TEAM_MAP.get(str(short).strip(), str(short).strip())

def load_env():
    env = {}
    if ENV.exists():
        for line in ENV.read_text().splitlines():
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                k, v = line.split('=', 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env

def extract_matches(cutoff_year=2022):
    wb = openpyxl.load_workbook(EXCEL, read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.rows)
    matches = []
    skipped = 0
    for row in rows[2:]:
        vals = [cell.value for cell in row[:8]]
        date, _, home, away, venue, hs, aws = vals[0], vals[1], vals[2], vals[3], vals[4], vals[5], vals[6]
        if not isinstance(date, datetime) or date.year < cutoff_year:
            continue
        if hs is None or aws is None:
            skipped += 1
            continue
        try:
            hs = int(hs); aws = int(aws)
        except (TypeError, ValueError):
            skipped += 1
            continue
        matches.append({
            'date':      date.strftime('%Y-%m-%d'),
            'homeTeam':  full_name(home),
            'awayTeam':  full_name(away),
            'homeScore': hs,
            'awayScore': aws,
            'venue':     str(venue or '').strip(),
        })
    wb.close()
    if skipped:
        print(f'  Skipped {skipped} rows (no score yet)')
    return matches  # xlsx is newest-first — no sort needed

def push(env, matches):
    url = env['NEXT_PUBLIC_SUPABASE_URL'].rstrip('/')
    key = env.get('SUPABASE_SERVICE_ROLE_KEY') or env.get('NEXT_PUBLIC_SUPABASE_ANON_KEY')
    resp = requests.post(
        f'{url}/rest/v1/betmate_data_store',
        headers={
            'apikey':        key,
            'Authorization': f'Bearer {key}',
            'Content-Type':  'application/json',
            'Prefer':        'resolution=merge-duplicates',
        },
        json={'key': 'afl_match_history', 'data': matches},
        timeout=30,
    )
    if resp.status_code in (200, 201):
        print(f'  Pushed {len(matches)} AFL matches to Supabase (afl_match_history).')
    else:
        print(f'  Error {resp.status_code}: {resp.text}')

if __name__ == '__main__':
    env  = load_env()
    matches = extract_matches(cutoff_year=2022)
    print(f'Extracted {len(matches)} AFL matches (2022+)')
    if matches:
        print(f'  Newest: {matches[0]["date"]}  {matches[0]["homeTeam"]} vs {matches[0]["awayTeam"]}')
        print(f'  Oldest: {matches[-1]["date"]}  {matches[-1]["homeTeam"]} vs {matches[-1]["awayTeam"]}')
        # Spot-check: verify a few team names mapped correctly
        sample_teams = set()
        for m in matches[:50]:
            sample_teams.add(m['homeTeam'])
            sample_teams.add(m['awayTeam'])
        print(f'  Sample team names: {sorted(sample_teams)[:6]}')
    push(env, matches)
