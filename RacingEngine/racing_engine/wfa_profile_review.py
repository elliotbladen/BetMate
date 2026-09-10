"""Retrospective WFA profile review; no source-data or horse-rating writes.

Racing.com horse.age is current at fetch time, not the historical race date.
Use local import dates as observation proxies, never as archived PIT evidence.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from datetime import date, datetime
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3
from zoneinfo import ZoneInfo

from .horse_identity import clean_name, identity_key
from .horse_profiles import DERIVATION_VERSION, age_from_observation, australian_racing_age, normalise_sex
from .wfa import RULES_URL, TABLE_VERSION, standard_weight

VERSION = 'wfa-profile-reconstruction-v0.1-review'
COEFFICIENTS = (0.5, 0.65, 0.9)
SUPPORTED = {'racing-com-rv-authorised', 'racing-com-nsw-authorised-v2'}


def observation(row):
    """Validate the exact runner's provider ID/name and fetch-date proxy."""
    if row['source'] not in SUPPORTED:
        return None, 'unsupported_source'
    try:
        raw = json.loads(row['raw_json'] or '{}')
        horse = raw.get('raw_entry', raw).get('horse') or {}
        provider_id = str(horse.get('id') or '')
        name = identity_key(clean_name(row['source'], horse.get('fullName') or '')[0])
        expected = identity_key(clean_name(row['source'], row['horse_name'])[0])
        if not provider_id or not name or name != expected:
            return None, 'identity_not_verified'
        fetched = datetime.fromisoformat(row['imported_at'])
        if fetched.tzinfo is None:
            return None, 'missing_observation_timezone'
        observed_date = fetched.astimezone(ZoneInfo('Australia/Sydney')).date().isoformat()
        match = re.fullmatch(r'(\d+)(?:\s*YO)?', str(horse.get('age') or '').strip(), re.I)
        age = int(match[1]) if match else None
        if age is not None and not 1 <= age <= 30:
            return None, 'invalid_observed_age'
        sex = normalise_sex(horse.get('sex'))
        group = ('female' if sex in {'F', 'M'} else 'male') if sex else None
        season = int(observed_date[:4]) - (int(observed_date[5:7]) < 8)
        return {'provider_id': provider_id, 'name_key': name, 'observed_date': observed_date,
                'observed_age': age, 'season_origin': season - age if age is not None else None,
                'observed_sex': sex, 'sex_group': group}, None
    except (ValueError, TypeError, AttributeError):
        return None, 'malformed_profile_or_timestamp'


def reference(row, observations):
    """Same-ID donors only; disagreements are quarantined instead of voted on."""
    origins = {o['season_origin'] for o in observations if o['season_origin'] is not None}
    sexes = {o['sex_group'] for o in observations if o['sex_group'] is not None}
    names = {o['name_key'] for o in observations}
    if len(origins) > 1 or len(sexes) > 1 or len(names) > 1:
        return {'status': 'conflicting_provider_profile'}
    usable = [o for o in observations if o['observed_age'] is not None and o['sex_group'] is not None]
    if not usable:
        return {'status': 'missing_age_or_sex'}
    race_date = date.fromisoformat(row['race_date'])
    selected = min(usable, key=lambda o: (abs((date.fromisoformat(o['observed_date']) - race_date).days), o['observed_date']))
    try:
        age = age_from_observation(selected['observed_age'], selected['observed_date'], row['race_date'])
    except ValueError:
        return {'status': 'implausible_reconstructed_racing_age'}
    if not 2 <= age <= 20:
        return {'status': 'implausible_reconstructed_racing_age'}
    # Only male/female is projected. Do not invent historical gelding status,
    # or call an earlier 2yo filly a mare because the fetched profile says mare.
    sex = 'F' if selected['sex_group'] == 'female' else 'H'
    base = standard_weight(row['race_date'], row['distance_metres'], age, sex) if row['distance_metres'] else None
    result = {'status': 'base_reference_available' if base is not None else 'outside_schedule',
              'provider_id': selected['provider_id'], 'racing_age': age,
              'observed_age': selected['observed_age'], 'observed_date': selected['observed_date'],
              'sex_group': selected['sex_group'], 'base_wfa_kg': base,
              'retrospective': True, 'pit_eligible': False,
              'observation_after_race': selected['observed_date'] > row['race_date'],
              'ar170_status': 'not_assessed_base_reference_only'}
    if row.get('old_birth_date'):
        try:
            birth_age = australian_racing_age(row['old_birth_date'], row['race_date'])
        except ValueError:
            birth_age = None
        result['birth_date_age_check'] = birth_age
        if birth_age != age:
            result.update(status='birth_date_age_conflict', base_wfa_kg=None)
            base = None
    carried = row['weight_carried_kg']
    delta = carried - base if base is not None and carried is not None and math.isfinite(carried) else None
    result['carried_minus_base_wfa_kg'] = delta
    # Show the component only: adding it to an existing rating might count the
    # weight allowance twice. The rejected step-1 model is never loaded.
    result['component_sensitivity_points'] = {str(k): round(k * delta, 4) for k in COEFFICIENTS} if delta is not None else {}
    return result


def build(database: Path, output: Path, as_of: str, observed_through: str):
    date.fromisoformat(as_of)
    date.fromisoformat(observed_through)
    if database.resolve() == output.resolve():
        raise ValueError('Output must differ from source')
    source = sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True)
    source.row_factory = sqlite3.Row
    try:
        rows = [dict(r) for r in source.execute('''
            SELECT r.race_id,r.source,r.race_date,r.state,r.distance_metres,
                u.runner_number,u.horse_name,u.weight_carried_kg,rr.raw_json,rr.imported_at,
                dp.racing_age old_age,dp.sex old_sex,dp.birth_date old_birth_date
            FROM v2_clean_races r JOIN v2_clean_runner_results u USING(race_id)
            LEFT JOIN runner_results rr ON rr.source=r.source AND rr.race_date=r.race_date
                AND rr.track_slug=r.track_slug AND rr.race_number=r.race_number AND rr.runner_number=u.runner_number
            LEFT JOIN runner_derived_profiles dp ON dp.derivation_version=? AND dp.source=r.source
                AND dp.race_date=r.race_date AND dp.track_slug=r.track_slug AND dp.race_number=r.race_number
                AND dp.runner_number=u.runner_number
            WHERE r.race_date<? AND u.result_status='finished' AND u.finish_position IS NOT NULL
                AND u.finish_position>0 ORDER BY r.race_date,r.race_id,u.runner_number''', (DERIVATION_VERSION, as_of))]
    finally:
        source.close()
    groups, parsed = defaultdict(list), []
    for row in rows:
        obs, reason = observation(row)
        if obs is not None and obs['observed_date'] > observed_through:
            obs, reason = None, 'observation_after_review_cutoff'
        parsed.append((obs, reason))
        if obs:
            groups[obs['provider_id']].append(obs)
    with output.open('xb'):
        pass
    out = sqlite3.connect(output)
    counts, states, reasons = Counter(), defaultdict(Counter), Counter()
    examples = []
    digest = hashlib.sha256()
    try:
        out.executescript('''CREATE TABLE wfa_profile_review (
            race_id TEXT,runner_number INTEGER,horse_name TEXT,detail_json TEXT,
            PRIMARY KEY(race_id,runner_number)); CREATE TABLE review_metadata (report_json TEXT);''')
        for row, (obs, reason) in zip(rows, parsed):
            digest.update(json.dumps(row, sort_keys=True).encode())
            result = reference(row, groups[obs['provider_id']]) if obs else {'status': reason}
            old_ref = None
            if row['old_age'] is not None and normalise_sex(row['old_sex']) and row['distance_metres']:
                old_ref = standard_weight(row['race_date'], row['distance_metres'], row['old_age'], row['old_sex'])
            result.update({'retrospective': True, 'pit_eligible': False, 'table_version': TABLE_VERSION,
                           'race_date': row['race_date'], 'distance_metres': row['distance_metres'],
                           'carried_kg': row['weight_carried_kg'], 'old_derived_base_wfa_kg': old_ref})
            for counter in (counts, states[row['state'] or 'unknown']):
                counter['runs'] += 1
                counter['old_base_reference_available'] += old_ref is not None
                counter['reconstructed_base_reference_available'] += result.get('base_wfa_kg') is not None
                counter['projected_age_differs_from_observed'] += result.get('racing_age') != result.get('observed_age')
                counter['birth_date_checked'] += 'birth_date_age_check' in result
                counter['birth_date_conflicts'] += result['status'] == 'birth_date_age_conflict'
            reasons[result['status']] += 1
            out.execute('INSERT INTO wfa_profile_review VALUES (?,?,?,?)',
                        (row['race_id'], row['runner_number'], row['horse_name'], json.dumps(result, sort_keys=True)))
            if (row['race_date'] == '2026-09-05' and row['horse_name'] in {'Tempted', 'Lindermann', 'Ceolwulf'}) or (
                row['horse_name'] == 'Tempted' and row['race_date'] == '2025-02-01'):
                examples.append({'horse_name': row['horse_name'], **result})
        report = {'version': VERSION, 'race_cutoff_exclusive': as_of, 'observed_through_inclusive': observed_through,
                  'table_version': TABLE_VERSION, 'rules_url': RULES_URL, 'input_sha256': digest.hexdigest(),
                  'counts': dict(counts), 'by_state': {k: dict(v) for k, v in states.items()},
                  'status_counts': dict(reasons), 'examples': examples,
                  'pit_eligible_runs': 0, 'ratings_changed': 0,
                  'sensitivity_note': 'Uncapped standalone kg delta times coefficient; not fitted or added to any rating',
                  'scope': 'Retrospective base WFA references and component sensitivity only; AR170 not assessed',
                  'observation_date_note': 'Local import date in Australia/Sydney is a fetch-date proxy, not an archived pre-race timestamp'}
        out.execute('INSERT INTO review_metadata VALUES (?)', (json.dumps(report, sort_keys=True),))
        out.commit()
        return report
    finally:
        out.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--as-of', required=True)
    parser.add_argument('--observed-through', required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.database, args.output, args.as_of, args.observed_through), indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
