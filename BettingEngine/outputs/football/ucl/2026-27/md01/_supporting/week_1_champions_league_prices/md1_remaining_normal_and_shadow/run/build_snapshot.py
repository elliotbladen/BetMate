"""Resolve the archived UEFA projected XIs for the remaining matchday-1 fixtures.

Same identity method as scripts/build_ucl_player_snapshot.py — unique normalized
name-token match inside the current ESPN squad registry, goalkeeper separated —
but parameterised over this run's context, history and output paths instead of the
8 September ones.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup

ROOT = next(parent for parent in Path(__file__).resolve().parents
            if (parent / "ml/football").is_dir())   # BettingEngine root, wherever this run is filed
sys.path.insert(0, str(ROOT))
from ml.football.ucl_player_features import player_prior
from scripts.build_ucl_player_snapshot import normalize, resolve

# UEFA news heading -> ESPN team display name for this matchday's twelve clubs.
ESPN_TEAM = {
    'PSV': 'PSV Eindhoven', 'Shakhtar': 'Shakhtar Donetsk', 'Fenerbahçe': 'Fenerbahce',
    'Roma': 'AS Roma', 'Bayern München': 'Bayern Munich', 'Bodø/Glimt': 'Bodo/Glimt',
    'Man United': 'Manchester United', 'Sabah': 'Sabah FK', 'Slavia Praha': 'Slavia Prague',
    'Lens': 'Lens', 'Como': 'Como', 'Leipzig': 'RB Leipzig',
}
ROLE = {'G': 'GK', 'D': 'DEF', 'M': 'MID', 'F': 'ATT'}


def projected_lineups(html_path: Path) -> dict:
    soup = BeautifulSoup(html_path.read_text(), 'html.parser')
    found = {}
    for paragraph in soup.find_all('p'):
        text = paragraph.get_text(' ', strip=True)
        if not text.startswith('Possible line-up'):
            continue
        heading = paragraph.find_previous_sibling('p')
        if heading is None:
            continue
        team = heading.get_text(' ', strip=True)
        if team not in ESPN_TEAM:
            continue
        part = text.split(':', 1)[1].split('Out', 1)[0].strip()
        names = [n.strip() for n in re.split('[;,]', part) if n.strip()]
        if len(names) == 11:
            found[ESPN_TEAM[team]] = names
    return found, soup


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--context', type=Path, required=True)
    parser.add_argument('--news', type=Path, required=True)
    parser.add_argument('--history', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--overrides', type=Path, required=True,
                        help='Reviewed identity overrides for names the token matcher cannot resolve')
    args = parser.parse_args()
    overrides = {(o['team'], o['name']): o for o in json.loads(args.overrides.read_text())}

    history = pd.read_csv(args.history, dtype={'player_id': str, 'event_id': str}, low_memory=False)
    history['date'] = pd.to_datetime(history.kickoff, utc=True)
    history = history.sort_values(['date', 'event_id', 'player_id'])
    context = json.loads(args.context.read_text())
    projected, soup = projected_lineups(args.news)
    cutoff = pd.Timestamp(datetime.now(timezone.utc))

    rosters = {}
    folder = ROOT / 'data/ucl/player_layer/rosters'
    for path in folder.glob('*.json'):
        if path.name.endswith('.meta.json'):
            continue
        data = json.loads(path.read_text())
        meta = json.loads(path.with_suffix('.meta.json').read_text())
        if pd.Timestamp(meta['retrieved_at_utc']) > cutoff:
            raise ValueError('Future roster observation')
        rosters[data['team']['displayName']] = (data, meta)

    teams = {}
    for fixture in context['fixtures']:
        if cutoff >= pd.Timestamp(fixture['kickoff_utc']):
            raise ValueError('Cannot create a prematch snapshot after kickoff')
        for side in ('home', 'away'):
            name = fixture[side]
            if name in teams:
                continue
            if name not in rosters:
                teams[name] = {'espn_team': name, 'status': 'requires_review', 'projected_players': [],
                               'unresolved': [{'name': 'team', 'candidate_ids': [],
                                               'reason': 'no cached ESPN squad registry'}],
                               'confirmed_out_conflicts': []}
                continue
            roster_data, roster_meta = rosters[name]
            athletes = roster_data.get('athletes') or []
            if athletes and isinstance(athletes[0], dict) and 'items' in athletes[0]:
                athletes = [a for group in athletes for a in group['items']]
            registry = []
            for athlete in athletes:
                pid = str(athlete['id'])
                role = ROLE.get((athlete.get('position') or {}).get('abbreviation'), 'UNKNOWN')
                played = history[(history.player_id == pid) & (history.date < cutoff)
                                 & history.position_group.isin(['GK', 'DEF', 'MID', 'ATT'])]
                if len(played):
                    role = played.iloc[-1].position_group
                registry.append({'player_id': pid, 'player_name': athlete['displayName'], 'position_group': role})
            roster = pd.DataFrame(registry)

            players, unresolved = [], []
            for index, label in enumerate(projected.get(name, [])):
                ids = resolve(label, roster, goalkeeper=index == 0)
                override = overrides.get((name, label))
                if override and override['player_id'] in set(roster.player_id):
                    ids = [override['player_id']]
                if len(ids) != 1:
                    unresolved.append({'name': label, 'candidate_ids': ids})
                    continue
                player = roster[roster.player_id == ids[0]].iloc[0]
                prior = player_prior(history, ids[0], cutoff)
                players.append({
                    'uefa_name': label, 'player_id': ids[0], 'player_name': player.player_name,
                    'position_group': player.position_group, 'side': side,
                    'identity_method': 'unique normalized name-token match within the current team roster; goalkeeper separated',
                    'identity_override': override, 'lineup_source': None,
                    'expected_minutes_share': min(1., prior['roll_minutes'] / 90) if prior else None,
                    'expected_minutes_method': 'prior-eight-roster-row mean; scenario estimate, not a source observation',
                    'history': prior})
            if not projected.get(name):
                unresolved.append({'name': 'possible line-up', 'candidate_ids': [],
                                   'reason': 'no eleven-name possible line-up parsed from the UEFA article'})

            conflicts = []
            for event in fixture[side + '_context']['availability']:
                if event['status'] != 'out':
                    continue
                tokens = normalize(event['player'])
                for player in players:
                    full = normalize(player['player_name'])
                    if (tokens[0] == full[-1] if len(tokens) == 1 else set(tokens).issubset(set(full))):
                        conflicts.append({'player_id': player['player_id'], 'name': player['player_name'],
                                          'source': event['source']})
            teams[name] = {
                'espn_team': name,
                'latest_collected_match': str(history[(history.team == name) & (history.date < cutoff)].date.max()),
                'collected_matches': int(history[history.team == name].event_id.nunique()),
                'projected_players': players, 'unresolved': unresolved, 'confirmed_out_conflicts': conflicts,
                'status': 'complete' if len(players) == 11 and not unresolved and not conflicts else 'requires_review',
                'roster_source': roster_meta,
                'available_recent_roster': roster[['player_id', 'player_name', 'position_group']].to_dict('records')}

    canonical = soup.find('link', rel='canonical')
    payload = {
        'cutoff_utc': str(cutoff),
        'source': canonical['href'] if canonical else context['fixtures'][0]['home_context']['predicted_lineup_source'],
        'source_archive': str(args.news.resolve().relative_to(ROOT)),
        'source_sha256': hashlib.sha256(args.news.read_bytes()).hexdigest(),
        'source_published_at_utc': '2026-09-07T12:46:00Z',
        'source_modified_at_utc': '2026-09-07T21:45:19Z',
        'source_retrieved_at_utc': '2026-09-08T00:00:00Z',
        'lineup_type': 'uefa_predicted_not_confirmed',
        'identity_overrides': json.loads(args.overrides.read_text()),
        'lineup_age_note': ('The UEFA possible line-ups were last modified on 7 September 2026, three days before this '
                            'snapshot. UEFA was unreachable for a fresher pull, so no matchday lineup news is included.'),
        'teams': teams}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n')
    for name, team in teams.items():
        rows = [p['history']['history_rows'] if p['history'] else 0 for p in team['projected_players']]
        print(f"{name:20s} {team['status']:16s} players={len(team['projected_players']):2d} "
              f"matches={team.get('collected_matches')} min_history_rows={min(rows) if rows else '-'} "
              f"no_history={sum(r == 0 for r in rows)} unresolved={[u['name'] for u in team['unresolved']]} "
              f"out_conflicts={[c['name'] for c in team['confirmed_out_conflicts']]}")


if __name__ == '__main__':
    main()
