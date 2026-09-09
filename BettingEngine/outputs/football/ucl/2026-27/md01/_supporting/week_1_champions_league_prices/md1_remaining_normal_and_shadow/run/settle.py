"""Settle the matchday-1 predictions against the played results and score them.

Run this once the matches are finished:

    .venv/bin/python .../run/settle.py --predictions .../predictions.csv --output .../settled

Fetches each fixture's final score from the same ESPN endpoint the fixtures came from,
fills the result columns, and scores 1X2 and O/U 2.5 for each mode. Matches that are not
finished are left unsettled rather than scored on a partial scoreline, and a mode is only
compared against another mode on the fixtures both of them priced.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

SUMMARY = 'https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.champions/summary?event={}'
FINISHED = {'STATUS_FULL_TIME', 'STATUS_FINAL', 'STATUS_FINAL_AET', 'STATUS_FINAL_PEN'}


def fetch(event_id: str) -> dict:
    raw = subprocess.run(['curl', '-sS', '--compressed', '--fail', '--max-time', '30',
                          '--retry', '2', SUMMARY.format(event_id)],
                         check=True, capture_output=True).stdout
    payload = json.loads(raw)
    competition = payload['header']['competitions'][0]
    status = competition['status']['type']['name']
    sides = {c['homeAway']: c for c in competition['competitors']}
    scores = {side: c.get('score') for side, c in sides.items()}
    if status not in FINISHED or any(v in (None, '') for v in scores.values()):
        return {'status': status, 'home_goals': None, 'away_goals': None}
    return {'status': status, 'home_goals': int(scores['home']), 'away_goals': int(scores['away'])}


def rps(probabilities, outcome_index):
    """Ranked probability score over the ordered home/draw/away outcomes."""
    forecast = np.cumsum(probabilities)
    actual = np.cumsum(np.eye(3)[outcome_index])
    return float(np.sum((forecast - actual) ** 2) / 2)


def score(frame: pd.DataFrame) -> dict:
    if frame.empty:
        return {'matches': 0}
    result = {'matches': int(len(frame))}
    index = frame.apply(lambda r: 0 if r.home_goals > r.away_goals
                        else (1 if r.home_goals == r.away_goals else 2), axis=1).to_numpy()
    probabilities = frame[['p_home', 'p_draw', 'p_away']].to_numpy()
    onehot = np.eye(3)[index]
    result['1x2'] = {
        'rps': float(np.mean([rps(p, i) for p, i in zip(probabilities, index)])),
        'brier': float(np.mean(np.sum((probabilities - onehot) ** 2, axis=1))),
        'log_loss': float(-np.mean(np.log(np.clip(probabilities[np.arange(len(index)), index], 1e-12, 1)))),
        'hit_rate': float(np.mean(probabilities.argmax(axis=1) == index)),
    }
    over = ((frame.home_goals + frame.away_goals) > 2).to_numpy().astype(float)
    for label, column in (('raw', 'p_over25'), ('isotonic', 'p_over25_isotonic')):
        p = frame[column].to_numpy(dtype=float)
        result[f'over25_{label}'] = {
            'brier': float(np.mean((p - over) ** 2)),
            'log_loss': float(-np.mean(over * np.log(np.clip(p, 1e-12, 1))
                                       + (1 - over) * np.log(np.clip(1 - p, 1e-12, 1)))),
            'hit_rate': float(np.mean((p >= .5) == (over == 1))),
            'mean_probability': float(np.mean(p)), 'actual_rate': float(np.mean(over)),
        }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--predictions', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()

    frame = pd.read_csv(args.predictions, dtype={'espn_event_id': str})
    now = datetime.now(timezone.utc).isoformat()
    results = {}
    for event_id in sorted(frame.espn_event_id.unique()):
        results[event_id] = fetch(event_id)
    frame['result_status'] = frame.espn_event_id.map(lambda e: results[e]['status'])
    frame['home_goals'] = frame.espn_event_id.map(lambda e: results[e]['home_goals'])
    frame['away_goals'] = frame.espn_event_id.map(lambda e: results[e]['away_goals'])
    frame['settled_at_utc'] = np.where(frame.home_goals.notna(), now, None)

    settled = frame[frame.home_goals.notna() & frame.p_home.notna()].copy()
    scores = {mode: score(settled[settled['mode'] == mode]) for mode in frame['mode'].unique()}
    both = set(settled[settled['mode'] == 'normal'].match_key) & set(settled[settled['mode'] == 'shadow'].match_key)
    head_to_head = {mode: score(settled[(settled['mode'] == mode) & settled.match_key.isin(both)])
                    for mode in ('normal', 'shadow')} if both else {}

    args.output.mkdir(parents=True, exist_ok=True)
    frame.to_csv(args.output / 'settled.csv', index=False)
    report = {
        'settled_at_utc': now, 'predictions': str(args.predictions),
        'fixtures': len(results),
        'fixtures_finished': sum(r['home_goals'] is not None for r in results.values()),
        'scored_rows': int(len(settled)),
        'per_mode_all_priced_fixtures': scores,
        'per_mode_common_fixtures_only': head_to_head,
        'common_fixtures': sorted(both),
        'unfinished': [e for e, r in results.items() if r['home_goals'] is None],
        'note': ('Scores cover only the fixtures each mode actually priced. Shadow priced far '
                 'fewer fixtures than normal, so the per-mode table is not a like-for-like '
                 'comparison; use the common-fixtures block for that.'),
    }
    (args.output / 'scores.json').write_text(json.dumps(report, indent=2) + '\n')

    lines = ['# Matchday 1 remaining fixtures — settled', '',
             f"{report['fixtures_finished']} of {report['fixtures']} fixtures finished; "
             f"{report['scored_rows']} priced predictions scored.", '',
             '| Fixture | Result | Normal 1X2 top pick | Over 2.5 (normal) |', '|---|---|---|---|']
    for _, row in frame[frame['mode'] == 'normal'].iterrows():
        if pd.isna(row.home_goals):
            lines.append(f'| {row.home} v {row.away} | not finished | — | — |')
            continue
        outcome = f'{int(row.home_goals)}-{int(row.away_goals)}'
        if pd.isna(row.p_home):
            lines.append(f'| {row.home} v {row.away} | {outcome} | not priced | not priced |')
            continue
        pick = ['home', 'draw', 'away'][int(np.argmax([row.p_home, row.p_draw, row.p_away]))]
        lines.append(f'| {row.home} v {row.away} | {outcome} | {pick} | {row.p_over25:.3f} |')
    lines += ['', '```json', json.dumps({'per_mode': scores, 'common_fixtures_only': head_to_head}, indent=2), '```', '']
    (args.output / 'report.md').write_text('\n'.join(lines) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
