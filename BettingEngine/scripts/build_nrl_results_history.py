#!/usr/bin/env python3
"""
scripts/build_nrl_results_history.py

Assemble a complete, canonical NRL results history for the ML feature pipeline.

WHY THIS EXISTS
---------------
`ml/nrl/results/features_nrl.csv` stopped at 2026-04-12, which left the NRL ML
shadow unscoreable against the rules engine for the whole 2026 season (rules
priced R11-R27; ML features only existed to R6 — zero overlap). The builder that
produced that file is not in the repo. This is its replacement for the results
layer: one script, one output, re-runnable, with the raw API responses cached so
a re-run is free and reproducible.

SOURCES
-------
  nrl.com draw API   https://www.nrl.com/draw/data?competition=111&season=Y&round=R
                     Authoritative for scores, venue and kickoff time.
                     Raw JSON cached under data/nrl/results/raw/{season}/.

Round numbers are taken from the API and never remapped — downstream joins are
on (date, home_team, away_team), which sidesteps the DB-vs-API round offset
entirely.

USAGE
-----
    python scripts/build_nrl_results_history.py --seasons 2025 2026
    python scripts/build_nrl_results_history.py --seasons 2026 --refresh
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / 'data' / 'nrl' / 'results' / 'raw'
OUT_CSV = ROOT / 'ml' / 'nrl' / 'results' / 'nrl_results_history.csv'
API = 'https://www.nrl.com/draw/data?competition=111&season={season}&round={round}'
HEADERS = {'User-Agent': ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36')}

# NRL API nickname -> canonical name used throughout the engine and in
# features_nrl.csv. Exact-match only: an unmapped nickname is a hard error, not
# a silent pass-through, because a silent miss would split one club into two
# ELO identities and corrupt every rating downstream.
NICK_TO_CANON = {
    'Broncos': 'Brisbane Broncos',
    'Raiders': 'Canberra Raiders',
    'Bulldogs': 'Canterbury-Bankstown Bulldogs',
    'Sharks': 'Cronulla-Sutherland Sharks',
    'Dolphins': 'Dolphins',
    'Titans': 'Gold Coast Titans',
    'Sea Eagles': 'Manly-Warringah Sea Eagles',
    'Storm': 'Melbourne Storm',
    'Knights': 'Newcastle Knights',
    'Cowboys': 'North Queensland Cowboys',
    'Eels': 'Parramatta Eels',
    'Panthers': 'Penrith Panthers',
    'Rabbitohs': 'South Sydney Rabbitohs',
    'Dragons': 'St. George Illawarra Dragons',
    'Roosters': 'Sydney Roosters',
    'Warriors': 'New Zealand Warriors',
    'Wests Tigers': 'Wests Tigers',
    'Tigers': 'Wests Tigers',
}


def fetch_round(season: int, rnd: int, refresh: bool) -> dict | None:
    cache_dir = RAW_DIR / str(season)
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f'api-round-{rnd}.json'
    if path.exists() and not refresh:
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError:
            pass  # corrupt cache -> refetch
    resp = requests.get(API.format(season=season, round=rnd), headers=HEADERS, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    path.write_text(json.dumps(data))
    time.sleep(0.6)  # be polite to nrl.com
    return data


def parse(data: dict, season: int, rnd: int) -> list[dict]:
    out = []
    for fx in data.get('fixtures', []):
        if fx.get('type') != 'Match':
            continue
        if fx.get('matchState') != 'FullTime':
            continue  # unplayed or in-progress — never guess a score
        h, a = fx.get('homeTeam', {}), fx.get('awayTeam', {})
        hn, an = h.get('nickName'), a.get('nickName')
        if hn not in NICK_TO_CANON or an not in NICK_TO_CANON:
            raise KeyError(f'unmapped NRL nickname {hn!r} / {an!r} '
                           f'(season {season} round {rnd}) — add it to NICK_TO_CANON')
        hs, as_ = h.get('score'), a.get('score')
        if hs is None or as_ is None:
            continue
        ko = (fx.get('clock') or {}).get('kickOffTimeLong') or ''
        out.append({
            'season': season,
            'round': rnd,
            'date': ko[:10] or None,
            'kickoff_utc': ko or None,
            'home_team': NICK_TO_CANON[hn],
            'away_team': NICK_TO_CANON[an],
            'venue': fx.get('venue'),
            'home_score': int(hs),
            'away_score': int(as_),
        })
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--seasons', type=int, nargs='+', required=True)
    ap.add_argument('--max-round', type=int, default=30)
    ap.add_argument('--refresh', action='store_true', help='ignore the raw cache and refetch')
    ap.add_argument('--out', type=Path, default=OUT_CSV)
    args = ap.parse_args()

    rows: list[dict] = []
    for season in args.seasons:
        got = 0
        for rnd in range(1, args.max_round + 1):
            try:
                data = fetch_round(season, rnd, args.refresh)
            except Exception as exc:                      # network / HTTP
                print(f'  [!] {season} R{rnd}: {type(exc).__name__}: {exc}')
                continue
            parsed = parse(data or {}, season, rnd)
            rows.extend(parsed)
            got += len(parsed)
        print(f'{season}: {got} completed matches')

    df = pd.DataFrame(rows)
    if df.empty:
        raise SystemExit('no matches parsed — refusing to write an empty history')

    before = len(df)
    df = df.drop_duplicates(subset=['date', 'home_team', 'away_team'], keep='first')
    if len(df) != before:
        print(f'  de-duplicated {before - len(df)} repeated fixtures')

    df = df.sort_values(['date', 'home_team']).reset_index(drop=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False)
    print(f'\nWrote {len(df)} rows -> {args.out}')
    print(df.groupby('season').size().to_string())


if __name__ == '__main__':
    main()
