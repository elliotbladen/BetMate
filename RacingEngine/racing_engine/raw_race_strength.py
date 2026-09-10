"""Step 1: raw-clock, race-level research ratings. No production writes.

Run with explicit --database, --output and exclusive --as-of. Output must be
new. Event chronology is enforced; source corrections are not an archived
point-in-time feed (the broader validation belongs to step 3).
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date
import hashlib
from itertools import groupby
import json
import math
from pathlib import Path
import sqlite3
import statistics as st

from .performance import SECONDS_PER_LENGTH, going_bucket
from .sectional_features import derive
from .v2_ratings import CLASS_STANDARDS, plausible_race_clock, pounds_per_length

MODEL_VERSION = 'race-strength-raw-v0.1-shadow'
MIN_PAR = 5
HISTORY_DAYS = 730
FORM_DAYS = 365
HUBER_POINTS = 6.0
CLOCK_CAP = 20.0


def robust_level(channels):
    """Weighted Huber location; each channel has bounded influence.

    Channels are (name, points, reliability). Bisection solves the monotone
    Huber score, avoiding dependence on an initialisation or channel order.
    """
    active = [(name, value, weight) for name, value, weight in channels if weight > 0]
    if not active or any(not math.isfinite(v) or not math.isfinite(w) for _, v, w in active):
        raise ValueError('Finite evidence with positive reliability is required')
    lo, hi = min(v for _, v, _ in active), max(v for _, v, _ in active)
    for _ in range(70):
        mid = (lo + hi) / 2
        score = sum(w * max(-HUBER_POINTS, min(HUBER_POINTS, v - mid)) for _, v, w in active)
        if score > 0:
            lo = mid
        else:
            hi = mid
    level = (lo + hi) / 2
    effective = {name: w * min(1.0, HUBER_POINTS / max(abs(v - level), 1e-9))
                 for name, v, w in active}
    total = sum(effective.values())
    weights = {k: v / total for k, v in effective.items()}
    disagreement = math.sqrt(sum(weights[n] * (v - level) ** 2 for n, v, _ in active))
    return level, weights, disagreement


def sectional_balance(source, splits, distance, clock):
    """Observed opening-vs-final-400 contrast, in seconds per 400m.

    NSW 200m intervals and VIC 400m blocks have different semantics. The
    opening includes acceleration; pace is relative to prior comparable races,
    never inferred from a fixed early-minus-late threshold.
    """
    if not clock or distance <= 800:
        return None
    clean = [r for r in splits if r['section_seconds'] is not None
             and math.isfinite(r['section_seconds']) and r['section_seconds'] > 0]
    features = derive(source, clean, finish_time_seconds=clock, distance_metres=distance)
    late = features['final_400_seconds']
    if features['quality_status'] != 'ok' or late is None or late >= clock:
        return None
    opening = clock - late
    if not 10 <= (distance - 400) / opening <= 22:
        return None
    return opening * 400 / (distance - 400) - late


def estimate(standard, distance, clock, pars, balance, anchors, eligible):
    """One race level, with sectionals controlling reliability, not bonuses."""
    ppl = pounds_per_length(distance)
    prior_balances = [p['balance'] for p in pars if p['balance'] is not None]
    pace_z = None
    if balance is not None and len(prior_balances) >= MIN_PAR:
        centre = st.median(prior_balances)
        scale = max(0.5, 1.4826 * st.median(abs(v - centre) for v in prior_balances))
        pace_z = max(-3.0, min(3.0, (balance - centre) / scale))
    # Slow, bunched races: larger margin multiplier; fast, spread races: smaller.
    margin_ppl = ppl * (1 + 0.15 * math.tanh(pace_z or 0.0))
    channels = [('class', standard, 0.15)]
    clock_level = None
    clock_clipped = False
    if clock is not None and len(pars) >= MIN_PAR:
        # Past race standards put raw seconds on the existing points scale.
        # No affine fit, daily variant, wind correction or imputed clock.
        reference = st.median(p['standard'] for p in pars)
        raw = st.median(p['standard'] + (p['clock'] - clock) / SECONDS_PER_LENGTH * ppl for p in pars)
        clock_level = max(reference - CLOCK_CAP, min(reference + CLOCK_CAP, raw))
        clock_clipped = clock_level != raw
        median_clock = st.median(p['clock'] for p in pars)
        spread = st.median(abs(p['clock'] - median_clock) for p in pars)
        reliability = min(0.85, len(pars) / 20) / (1 + spread / 3)
        reliability /= 1 + 0.30 * max(0, pace_z or 0)
        if pace_z is None:
            reliability *= 0.8
        channels.append(('clock', clock_level, reliability))
    form_level = None
    if anchors:
        # Only principals with genuine earlier runs. Large beaten tails cannot
        # mechanically raise the winner's race level.
        values = [a['prior'] + min(a['margin'], 6.0) * margin_ppl for a in anchors]
        form_level, anchor_weights, _ = robust_level([
            (str(i), value, anchor['reliability'])
            for i, (value, anchor) in enumerate(zip(values, anchors))
        ])
        spread = sum(anchor_weights[str(i)] * abs(value - form_level)
                     for i, value in enumerate(values))
        reliability = min(0.85, sum(a['reliability'] for a in anchors) / max(eligible, 1))
        reliability /= 1 + spread / 8
        channels.append(('form', form_level, reliability))
    level, weights, disagreement = robust_level(channels)
    return {'race_strength': level, 'margin_ppl': margin_ppl,
            'clock_level': clock_level, 'form_level': form_level,
            'class_standard': standard, 'clock_clipped': clock_clipped,
            'par_n': len(pars), 'sectional_par_n': len(prior_balances), 'pace_z': pace_z,
            'channels': channels, 'effective_weights': weights,
            'disagreement_points': disagreement,
            'evidence_status': 'class_only' if len(channels) == 1 else 'observed_evidence'}


def build(database: Path, output: Path, as_of: str):
    date.fromisoformat(as_of)
    if database.resolve() == output.resolve():
        raise ValueError('Source and output must differ')
    # Opening read-only also prevents accidentally creating a missing source.
    source = sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True)
    source.row_factory = sqlite3.Row
    try:
        source.execute('BEGIN')
        races = [dict(r) for r in source.execute('''
            SELECT r.*, raw.track_condition FROM v2_clean_races r
            LEFT JOIN race_results raw ON raw.source=r.source AND raw.race_date=r.race_date
              AND raw.track_slug=r.track_slug AND raw.race_number=r.race_number
            WHERE r.race_date < ? ORDER BY r.race_date,r.track_slug,r.race_number''', (as_of,))]
        runners = defaultdict(list)
        for r in source.execute('''SELECT u.* FROM v2_clean_runner_results u
            JOIN v2_clean_races r USING(race_id) WHERE r.race_date < ?
            ORDER BY r.race_date,r.race_id,u.runner_number''', (as_of,)):
            runners[r['race_id']].append(dict(r))
        splits = defaultdict(list)
        for s in source.execute('''SELECT r.race_id,s.runner_number,s.marker_metres,
                s.section_seconds,s.position_at_marker FROM runner_sectionals s
            JOIN v2_clean_races r ON r.source=s.source AND r.race_date=s.race_date
              AND r.track_slug=s.track_slug AND r.race_number=s.race_number
            WHERE r.race_date < ? ORDER BY r.race_id,s.runner_number,s.marker_metres''', (as_of,)):
            splits[(s['race_id'], s['runner_number'])].append(dict(s))
    finally:
        source.close()
    # Exclusive creation: never replace an earlier review/prospective snapshot.
    with output.open('xb'):
        pass
    out = sqlite3.connect(output)
    try:
        out.executescript('''CREATE TABLE race_strength_races (
            model_version TEXT, race_id TEXT PRIMARY KEY, race_date TEXT, state TEXT,
            race_strength REAL, detail_json TEXT);
            CREATE TABLE race_strength_runs (
            model_version TEXT, race_id TEXT, runner_number INTEGER, horse_key TEXT,
            horse_name TEXT, at_weights_rating REAL, margin_component REAL,
            PRIMARY KEY(race_id,runner_number));
            CREATE TABLE build_metadata (report_json TEXT);''')
        past_times, history = defaultdict(list), defaultdict(list)
        counts, states = Counter(), defaultdict(Counter)
        digest = hashlib.sha256()
        for day, meetings in groupby(races, key=lambda r: r['race_date']):
            current_day = date.fromisoformat(day)
            pending_times, pending_runs = [], []
            # Nothing from the current day enters another race's priors or pars.
            for race in meetings:
                rid = race['race_id']
                field = runners[rid]
                digest.update(json.dumps([race, field, [splits[(rid, u['runner_number'])] for u in field]], sort_keys=True).encode())
                distance = race['distance_metres']
                valid = [u for u in field if u['result_status'] == 'finished' and u['finish_position'] is not None
                         and u['finish_position'] > 0 and (u['finish_position'] == 1 or
                         (u['beaten_lengths'] is not None and math.isfinite(u['beaten_lengths']) and u['beaten_lengths'] >= 0))]
                winners = [u for u in valid if u['finish_position'] == 1]
                if not distance or distance <= 0 or len(valid) < 3 or not winners:
                    counts['skipped_ineligible_races'] += 1
                    continue
                standard = CLASS_STANDARDS.get(race['class_family'], CLASS_STANDARDS['other'])
                clock = race['official_time_seconds']
                clock_ok = (race['clock_status'] == 'valid' and clock is not None
                            and math.isfinite(clock) and plausible_race_clock(distance, clock)[0])
                clock = clock if clock_ok else None
                # Exact track/distance/going only: unknown going does not donate.
                going = going_bucket(race['track_condition'])
                key = (race['track_slug'], distance, going)
                pars = [p for p in past_times[key] if (current_day - p['day']).days <= HISTORY_DAYS]
                balances = [sectional_balance(race['source'], splits[(rid, w['runner_number'])], distance, clock) for w in winners]
                balance = st.median([v for v in balances if v is not None]) if any(v is not None for v in balances) else None
                principals = [u for u in valid if u['finish_position'] <= 4]
                anchors = []
                for u in principals:
                    previous = [p for p in history[u['horse_key']] if (current_day - p['day']).days <= FORM_DAYS
                                and abs(p['distance'] - distance) <= max(200, distance * 0.2)][-3:]
                    if previous:
                        age = (current_day - previous[-1]['day']).days
                        anchors.append({'horse_key': u['horse_key'], 'prior': st.median(p['rating'] for p in previous),
                                        'latest_prior_date': previous[-1]['day'].isoformat(),
                                        'margin': 0 if u['finish_position'] == 1 else u['beaten_lengths'],
                                        'reliability': len(previous) / (len(previous) + 1) * math.exp(-age / 180)})
                result = estimate(standard, distance, clock, pars, balance, anchors, len(principals))
                result.update({'anchors': anchors, 'raw_clock_seconds': clock, 'clock_status': race['clock_status'],
                               'going': going, 'sectional_balance': balance, 'par_latest_date': max((p['day'].isoformat() for p in pars), default=None),
                               'excluded_finishers_missing_margin': sum(u['result_status'] == 'finished' for u in field) - len(valid)})
                out.execute('INSERT INTO race_strength_races VALUES (?,?,?,?,?,?)',
                            (MODEL_VERSION, rid, day, race['state'], result['race_strength'], json.dumps(result, sort_keys=True)))
                for u in valid:
                    margin = 0 if u['finish_position'] == 1 else u['beaten_lengths']
                    component = -margin * result['margin_ppl']
                    rating = result['race_strength'] + component
                    out.execute('INSERT INTO race_strength_runs VALUES (?,?,?,?,?,?,?)',
                                (MODEL_VERSION, rid, u['runner_number'], u['horse_key'], u['horse_name'], rating, component))
                    # A class-only holding figure is not independent proven form.
                    if result['evidence_status'] != 'class_only':
                        pending_runs.append((u['horse_key'], {'day': current_day, 'rating': rating, 'distance': distance}))
                    counts['runs'] += 1
                for counter in (counts, states[race['state'] or 'unknown']):
                    counter['races'] += 1
                    counter['with_clock_channel'] += result['clock_level'] is not None
                    counter['with_form_channel'] += result['form_level'] is not None
                    counter['with_sectional_context'] += result['pace_z'] is not None
                    counter['class_only'] += result['evidence_status'] == 'class_only'
                    counter['clock_clipped'] += result['clock_clipped']
                if clock is not None and going != 'unknown':
                    pending_times.append((key, {'day': current_day, 'clock': clock, 'standard': standard, 'balance': balance}))
            for key, value in pending_times:
                past_times[key].append(value)
            for key, value in pending_runs:
                history[key].append(value)
        report = {'model_version': MODEL_VERSION, 'as_of_exclusive': as_of, 'status': 'research_only_step_1',
                  'input_sha256': digest.hexdigest(), 'counts': dict(counts), 'by_state': {k: dict(v) for k, v in states.items()},
                  'rating_type': 'at_weights_run_rating_not_WFA_or_current_ability',
                  'limitations': ['Research coefficients not yet validated (step 3)', 'WFA normalisation is step 2',
                                  'Current corrected source snapshot, not historical ingestion vintages',
                                  'No wind, daily variant or rail adjustment; going buckets only',
                                  'Clock scale uses existing class standards; no claim of matching Dan ratings']}
        out.execute('INSERT INTO build_metadata VALUES (?)', (json.dumps(report, sort_keys=True),))
        out.commit()
        return report
    finally:
        out.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--as-of', required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.database, args.output, args.as_of), indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
