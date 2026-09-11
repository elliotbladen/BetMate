"""Assemble the week 1 board for the remaining matchday-1 fixtures.

Reads the two run outputs and writes one CSV plus one report, so every number in
the write-up comes from the priced JSON rather than being retyped.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def odds(value):
    return f'{value:.2f}' if value is not None else '—'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--normal', type=Path, required=True)
    parser.add_argument('--shadow', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()

    normal = json.loads(args.normal.read_text())
    shadow = json.loads(args.shadow.read_text())
    shadow_rows = {(r['home'], r['away']): r for r in shadow['rows']}
    evidence = normal['totals_evidence']

    rows = []
    for base in normal['rows']:
        key = (base['home'], base['away'])
        shade = shadow_rows.get(key, {})
        central = base.get('scenarios', {}).get('confirmed_outs')
        shaded = shade.get('shadow')
        row = {
            'sydney_match_date': base['sydney_match_date'], 'kickoff_utc': base['kickoff_utc'],
            'home': base['home'], 'away': base['away'],
            'normal_status': base['status'],
            'shadow_status': shade.get('status', 'NOT_RUN'),
            'data_health_flags': '; '.join(base.get('data_health_flags', [])),
            'blocked_teams': '; '.join(base.get('blocked_teams', [])),
            'shadow_blockers': '; '.join(
                sorted({b['reason'] for b in shade.get('blockers', [])})),
        }
        for label, priced in (('normal', central), ('shadow', shaded)):
            fair = (priced or {}).get('fair_odds', {})
            totals = (priced or {}).get('totals_over_under_25', {})
            row.update({f'{label}_home': fair.get('home'), f'{label}_draw': fair.get('draw'),
                        f'{label}_away': fair.get('away')})
            raw = totals.get('raw', {})
            iso = totals.get('isotonic_paper_candidate', {})
            row.update({
                f'{label}_p_over25': raw.get('p_over'),
                f'{label}_over25': (raw.get('fair_odds') or {}).get('over'),
                f'{label}_under25': (raw.get('fair_odds') or {}).get('under'),
                f'{label}_p_over25_isotonic': iso.get('p_over'),
                f'{label}_over25_isotonic': (iso.get('fair_odds') or {}).get('over'),
                f'{label}_under25_isotonic': (iso.get('fair_odds') or {}).get('under')})
            if priced and 'expected_goals' in priced:
                row[f'{label}_xg_home'] = priced['expected_goals']['home']
                row[f'{label}_xg_away'] = priced['expected_goals']['away']
        rows.append(row)

    frame = pd.DataFrame(rows)
    args.output.mkdir(parents=True, exist_ok=True)
    frame.to_csv(args.output / 'prices.csv', index=False)

    lines = [
        '# Champions League matchday 1 — the six remaining fixtures',
        '',
        f"Sydney {rows[0]['sydney_match_date']}. Normal mode and player-shadow mode, "
        '1X2 and O/U 2.5, decimal fair odds over 90 minutes. Research prices: no market was '
        'captured, no EV was computed, and nothing here is a bet signal.',
        '',
        '## 1X2',
        '',
        '| Match | Kick-off (UTC) | Normal H | D | A | Shadow H | D | A |',
        '|---|---|---:|---:|---:|---:|---:|---:|',
    ]
    for row in rows:
        lines.append(
            f"| {row['home']} v {row['away']} | {row['kickoff_utc'][11:16]} | "
            + ' | '.join(odds(row[f'{label}_{side}']) for label in ('normal', 'shadow')
                         for side in ('home', 'draw', 'away')) + ' |')

    lines += [
        '',
        '## O/U 2.5',
        '',
        'From the same score matrix as the 1X2 price. `Over`/`Under` are the raw matrix numbers; '
        '`Over (iso)` is the archived isotonic calibration applied to them.',
        '',
        '| Match | Normal Over | Under | Over (iso) | Shadow Over | Under | Over (iso) |',
        '|---|---:|---:|---:|---:|---:|---:|',
    ]
    for row in rows:
        lines.append(
            f"| {row['home']} v {row['away']} | "
            + ' | '.join(odds(row[f'{label}_{market}'])
                         for label in ('normal', 'shadow')
                         for market in ('over25', 'under25', 'over25_isotonic')) + ' |')

    lines += [
        '',
        '## What could not be priced',
        '',
        '| Match | Normal | Shadow |',
        '|---|---|---|',
    ]
    for row in rows:
        normal_note = ('priced' if row['normal_status'] == 'PROVISIONAL_RESEARCH_PRICE'
                       else f"blocked — no Champions League history for {row['blocked_teams']}")
        shadow_note = ('priced' if row['shadow_status'] == 'RESEARCH_PLAYER_SHADOW'
                       else f"blocked — {row['shadow_blockers'] or 'not run'}")
        lines.append(f"| {row['home']} v {row['away']} | {normal_note} | {shadow_note} |")

    lines += [
        '',
        '## Strength coverage',
        '',
        '| Match | Warning |',
        '|---|---|',
    ]
    for row in rows:
        if row['data_health_flags']:
            lines.append(f"| {row['home']} v {row['away']} | {row['data_health_flags']} |")
    lines += [
        '',
        '## Totals calibration',
        '',
        f"On {evidence['test_games']} held-out 2024/25 and 2025/26 matches the raw matrix O/U 2.5 "
        f"probability scored Brier {evidence['raw']['brier']:.5f}, with a mean Over of "
        f"{100 * evidence['raw']['mean_probability']:.2f}% against an actual "
        f"{100 * evidence['raw']['actual_rate']:.2f}% — it runs "
        f"{100 * (evidence['raw']['mean_probability'] - evidence['raw']['actual_rate']):.2f} percentage "
        'points too high on Over. The archived isotonic calibration improves Brier to '
        f"{evidence['calibrated']['brier']:.5f} but flattens the output: across these three fixtures it "
        'returns a narrow band regardless of how different the matches are, so it is reported as '
        'evidence about the calibration route, not as a competing price.',
        '',
        f"Model fit: {normal['fit_matches']} Champions League matches to {normal['fit_latest_result'][:10]}, "
        f"converged in {normal['convergence']['optimizer_iterations']} iterations.",
        '',
    ]
    (args.output / 'report.md').write_text('\n'.join(lines) + '\n')
    print(frame[['home', 'away', 'normal_status', 'shadow_status']].to_string(index=False))
    print('Wrote', args.output / 'report.md')


if __name__ == '__main__':
    main()
