#!/usr/bin/env python3
"""Collect free ESPN history using the existing EPL/EFL player parser.

Date-bounded discovery avoids current-team schedule bias. Raw responses and
retrieval metadata are cached; missing fields and estimated minutes are audited.
This collector does not train, infer prices, or fabricate availability events.
"""
from __future__ import annotations

import argparse
import calendar
import hashlib
import json
import sys
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pandas as pd
from ml.football.player_layer.backfill_espn_player_stats import parse_match

FIELDS = {"goals": "totalGoals", "assists": "goalAssists", "shots": "totalShots",
          "shots_on_target": "shotsOnTarget", "saves": "saves"}


def month_windows(start: date, end: date):
    while start <= end:
        last = min(end, start.replace(day=calendar.monthrange(start.year, start.month)[1]))
        yield start, last
        start = last + timedelta(days=1)


def cached_json(url: str, path: Path):
    if path.exists():
        return json.loads(path.read_text())
    raw = subprocess.run(['curl', '-sS', '--compressed', '--fail', '--max-time', '30',
                          '--retry', '2', url], check=True, capture_output=True).stdout
    payload = json.loads(raw)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    path.with_suffix('.meta.json').write_text(json.dumps({
        "url": url, "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "sha256": hashlib.sha256(raw).hexdigest()}, indent=2) + '\n')
    return payload


def audited_rows(eid: str, payload: dict, league: str):
    rows = parse_match(eid, payload)
    raw_players = {str(p['athlete']['id']): p
                   for team in payload.get('rosters', [])
                   for p in team.get('roster', []) if p.get('athlete', {}).get('id')}
    for row in rows:
        raw = raw_players[row['player_id']]
        keys = {s['name'] for s in raw.get('stats', [])}
        row['league'] = league
        row['source'] = f'https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/summary?event={eid}'
        row['minutes_method'] = 'existing_efl_parser_estimate_90min_with_65_25_fallbacks'
        row['missing_stat_fields'] = ','.join(k for k, v in FIELDS.items() if v not in keys)
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--manifest', type=Path, help='JSON collection jobs; runs up to four leagues concurrently')
    ap.add_argument('--rosters', action='store_true', help='With manifest, collect current team rosters only')
    ap.add_argument('--league', default='uefa.champions')
    ap.add_argument('--from-date', type=date.fromisoformat)
    ap.add_argument('--to-date', type=date.fromisoformat)
    ap.add_argument('--output', type=Path)
    ap.add_argument('--team-ids', nargs='*', help='Collect only fixtures involving these ESPN team IDs')
    args = ap.parse_args()
    if args.manifest:
        jobs = json.loads(args.manifest.read_text())
        def run_job(job):
            if args.rosters:
                for tid in job['team_ids']:
                    code = job['league']
                    cached_json(f'https://site.api.espn.com/apis/site/v2/sports/soccer/{code}/teams/{tid}/roster',
                                ROOT/'data/ucl/player_layer/rosters'/f'{code}_{tid}.json')
                print(f"{job['league']}: {len(job['team_ids'])} rosters cached",flush=True)
                return 0
            command = [sys.executable, str(Path(__file__).resolve()), '--league', job['league'],
                       '--from-date', job['from_date'], '--to-date', job['to_date'],
                       '--output', job['output'], '--team-ids', *job['team_ids']]
            result = subprocess.run(command, capture_output=True, text=True)
            Path(job['output']).mkdir(parents=True, exist_ok=True)
            (Path(job['output'])/'collection.log').write_text(result.stdout + result.stderr)
            print(f"{job['league']}: exit {result.returncode}; {result.stdout.splitlines()[-1:]}", flush=True)
            return result.returncode
        with ThreadPoolExecutor(max_workers=4) as pool:
            codes = list(pool.map(run_job, jobs))
        raise SystemExit(int(any(codes)))
    if not (args.from_date and args.to_date and args.output):
        ap.error('from-date, to-date and output are required without a manifest')
    if args.from_date > args.to_date:
        ap.error('from-date must be no later than to-date')
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    base = f'https://site.api.espn.com/apis/site/v2/sports/soccer/{args.league}'
    events, failures, discovery = {}, [], []
    for start, end in month_windows(args.from_date, args.to_date):
        key = f'{start:%Y%m%d}-{end:%Y%m%d}'
        payload = cached_json(f'{base}/scoreboard?dates={key}&limit=1000', out/'raw'/f'scoreboard_{key}.json')
        items = payload.get('events', [])
        if len(items) >= 1000:
            raise RuntimeError('Discovery limit reached; split the date range before continuing')
        discovery.append({'from': str(start), 'to': str(end), 'events_returned': len(items)})
        for e in items:
            kickoff = datetime.fromisoformat(e['date'].replace('Z', '+00:00')).date()
            if not start <= kickoff <= end:
                continue
            comp = e.get('competitions', [{}])[0]
            if not comp.get('status', e.get('status', {})).get('type', {}).get('completed'):
                continue
            ids = {str(c['team']['id']) for c in comp.get('competitors', [])}
            if args.team_ids and not ids.intersection(args.team_ids):
                continue
            events[str(e['id'])] = e
        print(f'{args.league} {key}: {len(items)} events returned', flush=True)
    all_rows, audits = [], []
    for i, (eid, event) in enumerate(sorted(events.items()), 1):
        try:
            payload = cached_json(f'{base}/summary?event={eid}', out/'raw'/f'{eid}.json')
            rows = audited_rows(eid, payload, args.league)
            starters = {side: sum(r['starter'] for r in rows if r['side'] == side) for side in ('home', 'away')}
            audits.append({'event_id': eid, 'name': event.get('name'), 'kickoff': event['date'],
                           'rows': len(rows), 'starters': starters,
                           'lineup_complete': starters == {'home': 11, 'away': 11},
                           'rows_with_missing_stats': sum(bool(r['missing_stat_fields']) for r in rows),
                           'minutes_verified': False})
            all_rows.extend(rows)
        except Exception as exc:
            failures.append({'event_id': eid, 'error': str(exc)})
        if i % 25 == 0:
            print(f'Processed {i}/{len(events)}; {len(all_rows)} rows; {len(failures)} failures', flush=True)
    pd.DataFrame(all_rows).to_csv(out/'player_match_stats.csv', index=False)
    (out/'coverage.json').write_text(json.dumps({
        'league': args.league, 'from_date': str(args.from_date), 'to_date': str(args.to_date),
        'team_ids_filter': args.team_ids,
        'parser_sha256': hashlib.sha256((ROOT/'ml/football/player_layer/backfill_espn_player_stats.py').read_bytes()).hexdigest(),
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'discovery': discovery, 'discovered_completed_matches': len(events),
        'parsed_matches': len(audits), 'player_rows': len(all_rows),
        'matches': audits, 'failures': failures,
        'status': 'history_collected_requires_quality_audit',
        'player_shadow_ready': False,
        'limitations': ['Coverage is discovered ESPN events, not independently reconciled full competition coverage.',
                       'Minutes use unchanged EPL/EFL estimates; extra time and dismissal handling require validation.',
                       'Missing stats retain parser defaults and are explicitly flagged, not certified true zeros.',
                       'Historical final lineups are not early prematch snapshots.']}, indent=2) + '\n')
    print(f'Saved {len(all_rows)} player rows from {len(audits)} matches to {out}', flush=True)
    if failures:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
