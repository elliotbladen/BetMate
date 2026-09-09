"""Freeze the matchday-1 prices into one settlement-ready prediction record.

One row per fixture per mode, in the same probability shape as
data/ucl/clv/ucl_shared_walk_forward_predictions.csv, with the result columns left
empty for settle.py to fill once the matches are played. Blocked fixtures are kept as
rows with empty probabilities so next week's coverage is honest rather than implied.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

MODES = ('normal', 'shadow')


def espn_event_ids(raw: Path) -> dict:
    """Read the archived ESPN summaries so the event ids are sourced, not retyped."""
    ids = {}
    for path in sorted(raw.glob('ucl_summary_*.json')):
        payload = json.loads(path.read_text())
        competition = payload['header']['competitions'][0]
        sides = {c['homeAway']: c['team']['displayName'] for c in competition['competitors']}
        ids[(sides['home'], sides['away'])] = str(payload['header']['id'])
    return ids


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--normal', type=Path, required=True)
    parser.add_argument('--shadow', type=Path, required=True)
    parser.add_argument('--raw', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()

    normal = json.loads(args.normal.read_text())
    shadow = {(r['home'], r['away']): r for r in json.loads(args.shadow.read_text())['rows']}
    events = espn_event_ids(args.raw)
    # ESPN prints a few clubs differently from the fixture list; map only what differs.
    espn_name = {'Manchester United': 'Manchester United', 'Bodo/Glimt': 'Bodo/Glimt',
                 'Fenerbahce': 'Fenerbahce', 'AS Roma': 'AS Roma'}

    rows = []
    for base in normal['rows']:
        home, away = base['home'], base['away']
        key = (espn_name.get(home, home), espn_name.get(away, away))
        if key not in events:
            raise ValueError(f'No archived ESPN summary for {home} v {away}')
        shade = shadow.get((home, away), {})
        priced = {'normal': base.get('scenarios', {}).get('confirmed_outs'),
                  'shadow': shade.get('shadow')}
        for mode in MODES:
            values = priced[mode]
            totals = (values or {}).get('totals_over_under_25', {}).get('raw', {})
            isotonic = (values or {}).get('totals_over_under_25', {}).get('isotonic_paper_candidate', {})
            rows.append({
                'match_key': f'{home}--{away}--{base["sydney_match_date"]}',
                'competition': 'UEFA Champions League 2026/27 league phase', 'matchday': 1,
                'sydney_match_date': base['sydney_match_date'], 'kickoff_utc': base['kickoff_utc'],
                'espn_event_id': events[key], 'home': home, 'away': away, 'mode': mode,
                'status': base['status'] if mode == 'normal' else shade.get('status', 'NOT_RUN'),
                'cutoff_utc': normal['cutoff_utc'],
                'p_home': (values or {}).get('probabilities', {}).get('home'),
                'p_draw': (values or {}).get('probabilities', {}).get('draw'),
                'p_away': (values or {}).get('probabilities', {}).get('away'),
                'p_over25': totals.get('p_over'), 'p_under25': totals.get('p_under'),
                'p_over25_isotonic': isotonic.get('p_over'),
                'lambda_home': (values or {}).get('expected_goals', {}).get('home'),
                'lambda_away': (values or {}).get('expected_goals', {}).get('away'),
                'data_health_flags': '; '.join(base.get('data_health_flags', [])),
                'blocked_reason': ('; '.join(base.get('blocked_teams', [])) if mode == 'normal'
                                   else '; '.join(sorted({b['reason'] for b in shade.get('blockers', [])}))),
                'home_goals': None, 'away_goals': None, 'settled_at_utc': None,
            })

    frame = pd.DataFrame(rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(args.output, index=False)
    priced = frame[frame.p_home.notna()]
    print(f'Wrote {len(frame)} prediction rows ({len(priced)} priced) to {args.output}')
    print(frame[['home', 'away', 'mode', 'status', 'espn_event_id']].to_string(index=False))


if __name__ == '__main__':
    main()
