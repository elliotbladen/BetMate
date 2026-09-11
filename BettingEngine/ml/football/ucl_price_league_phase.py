"""Price a UCL league-phase matchday from an explicit, timestamped research context.

Usage: python -m ml.football.ucl_price_league_phase --context FILE --aliases FILE
       --ratings FILE --output NEW_DIRECTORY

This extends the 8 September research runner in two ways that the remaining
matchday-1 fixtures need:

* fixtures whose opponents have no comparable cross-league strength are blocked
  on identity alone, before their form/availability context is required, so a
  team playing its first ever Champions League match does not have to fake a
  domestic feed to be reported as unpriceable;
* the O/U 2.5 probability implied by the same score matrix is published
  alongside 1X2, carrying its own measured calibration evidence.

Nothing here is a production promotion or a bet signal.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd

from .models.tiers import MatchContext
from .ucl_researched_pricing import team_state, validate_fixture
from .ucl_shared_engine import build_elo_before, load_matches, price

ROOT = Path(__file__).resolve().parents[2]
TOTALS_EVIDENCE = ROOT / 'ml/football/reports/ucl_totals_calibration_backtest.json'
TOTALS_WALK_FORWARD = ROOT / 'data/ucl/clv/ucl_shared_walk_forward_predictions.csv'

SCENARIOS = [(False, False, 'confirmed_outs'), (True, False, 'home_doubts_out'),
             (False, True, 'away_doubts_out'), (True, True, 'both_doubts_out')]

# A club can be present in the archive and still have a strength estimate that rests on a
# handful of years-old matches. Presence is not coverage, so both are reported.
THIN_HISTORY_MATCHES = 25
STALE_HISTORY_DAYS = 400


def data_health(matches, club_id, cutoff):
    played = matches[(matches.home_team == club_id) | (matches.away_team == club_id)]
    latest = played.Date.max() if len(played) else None
    stale_days = int((pd.Timestamp(cutoff) - latest).days) if latest is not None else None
    flags = []
    if len(played) < THIN_HISTORY_MATCHES:
        flags.append(f'thin_history_{len(played)}_archive_matches')
    if stale_days is not None and stale_days > STALE_HISTORY_DAYS:
        flags.append(f'stale_history_last_archive_match_{stale_days}_days_ago')
    return {'club_id': club_id, 'archive_matches': int(len(played)),
            'latest_archive_match': str(latest.date()) if latest is not None else None,
            'days_since_latest_archive_match': stale_days, 'flags': flags}


def totals_calibrator():
    """Refit the archived isotonic O/U 2.5 calibration on pre-2024/25 predictions only."""
    from sklearn.isotonic import IsotonicRegression
    frame = pd.read_csv(TOTALS_WALK_FORWARD)
    train = frame[frame.season.astype(str) < '2024-25']
    model = IsotonicRegression(out_of_bounds='clip').fit(train.p_over25, (train.home_goals + train.away_goals > 2).astype(int))
    evidence = json.loads(TOTALS_EVIDENCE.read_text())
    return model, {'training_games': int(len(train)), **evidence}


def forecast(home, away, ratings, elo, context, calibrator):
    """One coherent score distribution -> 1X2 and O/U 2.5, with every output validated."""
    if not ratings.get('converged'):
        raise ValueError('Cannot publish prices from a nonconverged fit')
    if home not in ratings['teams'] or away not in ratings['teams']:
        raise ValueError('Missing team strength: generic fallback forbidden')
    priced = price(home, away, ratings, elo=elo, context=context)
    vector = np.array([priced['p_home'], priced['p_draw'], priced['p_away']])
    if not np.isfinite(vector).all() or vector.min() <= 0 or abs(vector.sum() - 1) > 1e-9:
        raise ValueError('Invalid 1X2 probabilities')
    matrix = priced['scoreline_matrix']
    if not np.isfinite(matrix).all() or matrix.min() < 0 or abs(matrix.sum() - 1) > 1e-9:
        raise ValueError('Invalid score distribution')
    over = float(priced['p_over25'])
    under = float(priced['p_under25'])
    if not 0 < over < 1 or abs(over + under - 1) > 1e-9:
        raise ValueError('Invalid O/U 2.5 probabilities')
    calibrated = float(np.clip(calibrator.predict([over])[0], .01, .99))
    return {
        'probabilities': dict(zip(('home', 'draw', 'away'), vector.tolist())),
        'fair_odds': dict(zip(('home', 'draw', 'away'), (1 / vector).tolist())),
        'expected_goals': {'home': priced['lambda_home'], 'away': priced['lambda_away']},
        'totals_over_under_25': {
            'raw': {'p_over': over, 'p_under': under,
                    'fair_odds': {'over': 1 / over, 'under': 1 / under}},
            'isotonic_paper_candidate': {'p_over': calibrated, 'p_under': 1 - calibrated,
                                         'fair_odds': {'over': 1 / calibrated, 'under': 1 / (1 - calibrated)}},
        },
        'adjustments': asdict(priced['tier_audit']) if priced['tier_audit'] else None,
    }


def tier_audit(totals_evidence):
    return {
        'T0_data_health': 'Research inputs validated; production gate remains closed pending model/tier validation and current quotes.',
        'T1_strength': 'Converged shared DC + internal UCL Elo on the harmonized-ID archive; no external ClubElo or domestic-strength anchor.',
        'T2_availability': 'Sourced absences applied with legacy football position weights from ESPN squad position groups; the trained player shadow is a separate run.',
        'T3_form_rest': 'Current domestic league results and latest verified club match; calendar-day rest.',
        'T3_pressing_rotation_travel': 'Not quantified: no verified PPDA, expected-minute or calibrated travel inputs.',
        'T4_league_phase': 'Matchday 1 neutral context; no invented must-win adjustment.',
        'T5_knockout': 'Not applicable in the league phase.',
        'T6_referee_weather': 'No matchday-1 referee appointments were published in any source consulted; goal-rate and weather coefficients are not populated.',
        'T7_market': 'No captured current two-sided market; EV unavailable.',
        'T8_confluence': 'Not populated; no manufactured confluence.',
        'totals_over_under_25': (
            'Published from the same score matrix as 1X2, not from the separate market-anchored O/U challenger. '
            f"On {totals_evidence['test_games']} held-out 2024/25-2025/26 matches the raw matrix probability scored Brier "
            f"{totals_evidence['raw']['brier']:.5f} with mean Over {totals_evidence['raw']['mean_probability']:.4f} against an "
            f"actual {totals_evidence['raw']['actual_rate']:.4f} rate, i.e. it is "
            f"{100 * (totals_evidence['raw']['mean_probability'] - totals_evidence['raw']['actual_rate']):.2f} percentage points "
            f"too high on Over. The isotonic paper candidate improves Brier to {totals_evidence['calibrated']['brier']:.5f} "
            'but was fitted on the earlier walk-forward predictions, not on this rating fit. Neither is a betting price.'),
        'corners': 'Not injected into 1X2 or totals; the separate corner challenger remains unpromoted.',
    }


def run(context_path: Path, aliases_path: Path, ratings_path: Path, output: Path) -> dict:
    manifest = json.loads(context_path.read_text())
    aliases = json.loads(aliases_path.read_text())
    ratings = json.loads(ratings_path.read_text())
    cutoff = manifest['cutoff_utc']
    if pd.Timestamp(ratings['as_of']) > pd.Timestamp(cutoff):
        raise ValueError('Model fit cutoff exceeds prediction cutoff')
    for gate in ('converged', 'preserve_fitted_rates'):
        if not ratings.get(gate):
            raise ValueError(f'UCL research requires ratings with {gate} set')

    matches = load_matches()
    for column in ('home_team', 'away_team', 'home_club_id', 'away_club_id'):
        matches[column] = matches[column].replace(aliases)
    matches = matches[matches.Date < pd.Timestamp(ratings['as_of'])]
    if len(matches) != ratings['n_matches'] or sorted(set(matches.home_team) | set(matches.away_team)) != sorted(ratings['teams']):
        raise ValueError('Cached ratings do not match the canonicalized training archive')
    if ratings.get('canonical_training_sha256') != hashlib.sha256(matches.to_csv(index=False).encode()).hexdigest():
        raise ValueError('Cached ratings training hash does not match the current archive')

    elo = build_elo_before(matches, cutoff)
    calibrator, totals_evidence = totals_calibrator()
    rows = []
    for fixture in manifest['fixtures']:
        home_id = fixture['home_context']['club_id']
        away_id = fixture['away_context']['club_id']
        row = {key: fixture[key] for key in ('home', 'away', 'sydney_match_date', 'kickoff_utc', 'referee')}
        row['tier_audit'] = tier_audit(totals_evidence)
        row['inputs'] = {side: fixture[side + '_context'] for side in ('home', 'away')}

        # Identity gate first: a fixture with no comparable strength cannot be rescued by
        # any amount of current form, so its context is never required to be complete.
        missing = [fixture[side] for side, club in (('home', home_id), ('away', away_id))
                   if not club or club not in ratings['teams']]
        if missing:
            row['status'] = 'BLOCKED_MISSING_CROSS_LEAGUE_STRENGTH'
            row['betting_enabled'] = False
            row['blocked_teams'] = missing
            row['tier_audit']['T1_strength'] = (
                f"No Champions League archive history for {', '.join(missing)}; recent domestic results alone do not "
                'establish comparable cross-league strength, and a league-average fallback is forbidden.')
            rows.append(row)
            continue

        validate_fixture(fixture, cutoff)
        row['data_health'] = {side: data_health(matches, club, cutoff)
                              for side, club in (('home', home_id), ('away', away_id))}
        row['data_health_flags'] = sorted({f"{fixture[side]}: {flag}"
                                           for side in ('home', 'away')
                                           for flag in row['data_health'][side]['flags']})
        if row['data_health_flags']:
            row['tier_audit']['T0_data_health'] += (
                ' Strength coverage warning — ' + '; '.join(row['data_health_flags']) +
                '. The estimate is published, but a rating built on this little recent history '
                'carries far wider uncertainty than the single number suggests.')
        row['status'] = 'PROVISIONAL_RESEARCH_PRICE'
        row['betting_enabled'] = False
        baseline = forecast(home_id, away_id, ratings, elo, None, calibrator)
        no_absences = MatchContext(team_state(home_id, fixture['home_context'], apply_absences=False),
                                   team_state(away_id, fixture['away_context'], apply_absences=False))
        row['baseline'] = baseline
        row['form_rest_only'] = forecast(home_id, away_id, ratings, elo, no_absences, calibrator)
        scenarios = {}
        for home_doubts, away_doubts, label in SCENARIOS:
            context = MatchContext(team_state(home_id, fixture['home_context'], home_doubts),
                                   team_state(away_id, fixture['away_context'], away_doubts))
            scenarios[label] = forecast(home_id, away_id, ratings, elo, context, calibrator)
        row['scenarios'] = scenarios
        central = scenarios['confirmed_outs']
        row['fair_odds'] = central['fair_odds']
        row['totals_over_under_25'] = central['totals_over_under_25']
        row['availability_scenario_odds_range'] = {
            key: [min(s['fair_odds'][key] for s in scenarios.values()),
                  max(s['fair_odds'][key] for s in scenarios.values())] for key in ('home', 'draw', 'away')}
        row['availability_scenario_over25_range'] = [
            min(s['totals_over_under_25']['raw']['p_over'] for s in scenarios.values()),
            max(s['totals_over_under_25']['raw']['p_over'] for s in scenarios.values())]
        row['home_probability_change_pp'] = 100 * (central['probabilities']['home'] - baseline['probabilities']['home'])
        rows.append(row)

    report = {
        'cutoff_utc': cutoff, 'version': 'ucl_league_phase_context_v1', 'production_promoted': False,
        'matchday': manifest.get('matchday'), 'rows': rows,
        'convergence': {key: ratings[key] for key in
                        ('converged', 'optimizer_message', 'optimizer_iterations', 'optimizer_evaluations')},
        'fit_matches': len(matches), 'fit_latest_result': str(matches.Date.max()),
        'normalization_rate_scale': ratings['normalization_rate_scale'],
        'input_manifest': str(context_path), 'method_notes': manifest['notes'],
        'totals_evidence': totals_evidence,
        'priced': sum(r['status'] == 'PROVISIONAL_RESEARCH_PRICE' for r in rows),
    }
    tracked = [context_path, aliases_path, ratings_path, Path(__file__),
               Path(__file__).parent / 'ucl_researched_pricing.py',
               Path(__file__).parent / 'ucl_shared_engine.py',
               Path(__file__).parent / 'models/dixon_coles.py',
               Path(__file__).parent / 'models/tiers.py']
    report['sha256'] = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in tracked}

    output.mkdir(parents=True, exist_ok=False)
    (output / 'prices.json').write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
    flat = []
    for row in rows:
        item = {key: row[key] for key in ('home', 'away', 'sydney_match_date', 'kickoff_utc', 'status')}
        item['data_health_flags'] = '; '.join(row.get('data_health_flags', []))
        item.update({f'{key}_fair_odds': value for key, value in row.get('fair_odds', {}).items()})
        totals = row.get('totals_over_under_25')
        if totals:
            item.update({'over25_prob_raw': totals['raw']['p_over'],
                         'over25_fair_odds_raw': totals['raw']['fair_odds']['over'],
                         'under25_fair_odds_raw': totals['raw']['fair_odds']['under'],
                         'over25_prob_isotonic': totals['isotonic_paper_candidate']['p_over'],
                         'over25_fair_odds_isotonic': totals['isotonic_paper_candidate']['fair_odds']['over'],
                         'under25_fair_odds_isotonic': totals['isotonic_paper_candidate']['fair_odds']['under']})
        flat.append(item)
    frame = pd.DataFrame(flat)
    frame.to_csv(output / 'prices.csv', index=False)
    print(frame.to_string(index=False))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('context', 'aliases', 'ratings', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    run(args.context, args.aliases, args.ratings, args.output)


if __name__ == '__main__':
    main()
