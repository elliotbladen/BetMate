"""Audited ESPN player inputs and the existing 56-feature football contract."""
from __future__ import annotations
import json
import re
from pathlib import Path
import numpy as np
import pandas as pd
from .player_layer.backfill_espn_player_stats import parse_match
from .player_layer.train_starter_shadow import ROLLING_STATS, ROLLING_WINDOW, POSITION_GROUPS

STAT_KEYS = dict(zip(ROLLING_STATS, ['totalGoals','goalAssists','totalShots','shotsOnTarget','saves']))
FEATURE_COLS = [f'{side}_{pg}_{col}' for side in ('home','away') for pg in POSITION_GROUPS
                for col in [*[f'roll_{s}_p90' for s in ROLLING_STATS], 'roll_minutes', 'count']]


def minute_audit(payload: dict) -> dict:
    comp = payload.get('header', {}).get('competitions', [{}])[0]
    status = comp.get('status', {}).get('type', {})
    periods = [e.get('period', {}).get('number', 0) for e in payload.get('keyEvents', []) if not e.get('shootout')]
    duration = 120 if status.get('name') == 'STATUS_FINAL_AET' or any(p in (3,4) for p in periods) else 90
    incoming, outgoing, sent_off = {}, {}, {}
    for e in payload.get('keyEvents', []):
        if e.get('shootout'):
            continue
        kind = e.get('type', {}).get('text', '').lower()
        ids = [str(p.get('athlete', {}).get('id', '')) for p in e.get('participants', [])]
        value = re.search(r'\d+', e.get('clock', {}).get('displayValue', ''))
        if not value:
            continue
        minute = min(duration, int(value.group()))  # nominal match minutes, excludes stoppage time
        if kind == 'substitution' and len(ids) == 2 and all(ids):
            incoming[ids[0]] = minute
            outgoing[ids[1]] = minute
        if ('red card' in kind or 'second yellow' in kind) and ids:
            sent_off[ids[0]] = minute
    result = {}
    for team in payload.get('rosters', []):
        for p in team.get('roster', []):
            pid = str(p.get('athlete', {}).get('id', ''))
            stats = {s['name']:s['value'] for s in p.get('stats', [])}
            issues = []
            if not status.get('completed'):
                issues.append('match_not_completed')
            start = 0 if p.get('starter') else incoming.get(pid)
            if not p.get('starter') and not p.get('subbedIn'):
                start = duration  # unused bench player
            if p.get('subbedIn') and pid not in incoming:
                issues.append('sub_in_time_missing')
            if p.get('subbedOut') and pid not in outgoing:
                issues.append('sub_out_time_missing')
            if stats.get('redCards',0) and pid not in sent_off:
                issues.append('dismissal_time_missing')
            end = min(outgoing.get(pid,duration), sent_off.get(pid,duration))
            if start is None or end < start:
                issues.append('invalid_minute_interval')
            result[pid] = {'minutes_audited':None if issues else end-start,
                           'minutes_issues':','.join(issues), 'match_duration':duration}
    return result


def load_history(root: Path, output: Path) -> pd.DataFrame:
    rows, seen, conflicts = [], {}, []
    for folder in sorted(root.iterdir()):
        coverage = folder/'coverage.json'
        if not coverage.exists():
            continue
        league = json.loads(coverage.read_text())['league']
        for path in sorted((folder/'raw').glob('*.json')):
            if not path.stem.isdigit():
                continue
            payload = json.loads(path.read_text())
            minute = minute_audit(payload)
            players = {str(p['athlete']['id']):p for r in payload.get('rosters', [])
                       for p in r.get('roster', []) if p.get('athlete', {}).get('id')}
            status = payload.get('header',{}).get('competitions',[{}])[0].get('status',{}).get('type',{}).get('name')
            for row in parse_match(path.stem, payload):
                pid = row['player_id']
                raw = players[pid]
                stats = {s['name']:s['value'] for s in raw.get('stats', [])}
                required = [s for s in ROLLING_STATS if s != 'saves' or row['position_group'] == 'GK']
                missing = [s for s in required if STAT_KEYS[s] not in stats]
                row.update(minute[pid])
                row.update(league=league, raw_file=str(path), match_status=status,
                           missing_required_stats=','.join(missing),
                           source=f'https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/summary?event={path.stem}')
                row['minutes_legacy'] = row['minutes']
                row['minutes'] = row['minutes_audited']
                row['quality_ok'] = not missing and not row['minutes_issues']
                key = (row['event_id'], pid)
                comparable = {k:v for k,v in row.items() if k not in ('raw_file','source')}
                if key in seen:
                    if seen[key] != comparable:
                        conflicts.append(key)
                    continue
                seen[key] = comparable
                rows.append(row)
    if conflicts:
        raise ValueError(f'Conflicting cached player observations: {conflicts[:10]}')
    df = pd.DataFrame(rows)
    df['date'] = pd.to_datetime(df.kickoff, utc=True)
    df = df.sort_values(['date','event_id','player_id']).reset_index(drop=True)
    output.mkdir(parents=True, exist_ok=True)
    df.to_csv(output/'audited_history.csv', index=False)
    (output/'history_audit.json').write_text(json.dumps({
        'rows':len(df), 'matches':int(df.event_id.nunique()),
        'quality_rows':int(df.quality_ok.sum()),
        'minutes_changed':int((df.minutes.notna() & (df.minutes != df.minutes_legacy)).sum()),
        'minute_issues':df.minutes_issues.value_counts().to_dict(),
        'missing_stats':df.missing_required_stats.value_counts().to_dict(),
        'minutes_convention':'Nominal 90/120-minute intervals from athlete-ID substitution/dismissal events; stoppage time excluded.',
        'non_goalkeeper_missing_saves':'Structural zero, matching existing EPL/EFL features.'},indent=2)+'\n')
    return df


def player_prior(history: pd.DataFrame, pid: str, cutoff: pd.Timestamp):
    prior = history[(history.player_id == pid) & (history.date < cutoff) & history.quality_ok].tail(ROLLING_WINDOW)
    if prior.empty:
        return None
    vals = {f'roll_{s}_p90':float(np.where(prior.minutes > 0,
                prior[s]/prior.minutes.clip(lower=1)*90, 0).mean()) for s in ROLLING_STATS}
    vals['roll_minutes'] = float(prior.minutes.mean())
    vals['history_rows'] = len(prior)
    vals['latest_history'] = str(prior.date.max())
    return vals


def lineup_features(history: pd.DataFrame, lineup: list[dict], cutoff: pd.Timestamp):
    values = {c:0.0 for c in FEATURE_COLS}
    audit = []
    for player in lineup:
        pid, pg, side = str(player['player_id']), player['position_group'], player['side']
        prior = player_prior(history, pid, cutoff)
        audit.append({**player, 'history':prior})
        if prior is None or pg not in POSITION_GROUPS:
            continue
        for k,v in prior.items():
            key = f'{side}_{pg}_{k}'
            if key in values:
                values[key] += v
        values[f'{side}_{pg}_count'] += 1
    return values, audit
