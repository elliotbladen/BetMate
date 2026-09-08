"""Converged season-forward UCL baselines for player residual evaluation."""
from pathlib import Path
import sys
import json
import hashlib
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ml.football.ucl_shared_engine import load_matches, build_elo_before, price
from ml.football.models.dixon_coles import fit


def main():
    out = ROOT/'data/ucl/player_layer/baselines_v2'
    out.mkdir(exist_ok=True)
    aliases = json.loads((ROOT/'outputs/football/ucl/2026-27/md01/_supporting/2026-09-08_researched/aliases.json').read_text())
    matches = load_matches()
    for col in ('home_team', 'away_team', 'home_club_id', 'away_club_id'):
        matches[col] = matches[col].replace(aliases)
    # Reconcile the two collected seasons by club identity and score before any fit.
    # A historical archive date error must not become a spurious duplicate fixture.
    club_ids=json.loads((ROOT/'data/ucl/player_layer/espn_club_aliases.json').read_text())
    espn={}
    for season in ('2024_25','2025_26'):
        for path in (ROOT/f'data/ucl/player_layer/espn_{season}/raw').glob('*.json'):
            if not path.stem.isdigit():continue
            comp=json.loads(path.read_text())['header']['competitions'][0]
            sides={c['homeAway']:c for c in comp['competitors']}
            h,a=sides['home'],sides['away']
            key=(season.replace('_','-'),club_ids.get(h['team']['displayName']),club_ids.get(a['team']['displayName']),int(h['score']),int(a['score']))
            espn.setdefault(key,[]).append(comp['date'])
    repairs=[]; quarantined=[]
    for i,r in matches[matches.season.isin(['2024-25','2025-26'])].iterrows():
        dates=espn.get((r.season,r.home_team,r.away_team,int(r.home_goals),int(r.away_goals)),[])
        if len(dates)!=1:
            quarantined.append({'match_id':r.match_id,'reason':'nonunique_or_missing_ESPN_score_identity'});continue
        revised=pd.Timestamp(dates[0])
        if revised!=r.Date:repairs.append({'match_id':r.match_id,'archive_date':str(r.Date),'espn_date':str(revised)})
        matches.loc[i,'Date']=revised
        matches.loc[i,'kickoff_utc']=str(revised)
    matches=matches[~matches.match_id.isin([r['match_id'] for r in quarantined])].sort_values(['Date','match_id'])
    matches.to_csv(out/'canonical_matches.csv',index=False)
    (out/'date_reconciliation.json').write_text(json.dumps({'repairs':repairs,'quarantined':quarantined},indent=2)+'\n')
    rows, failures = [], []
    for season in ('2024-25', '2025-26'):
        current = matches[matches.season == season]
        cutoff = current.Date.min()
        prior = matches[matches.Date < cutoff]
        digest = hashlib.sha256(prior.to_csv(index=False).encode()).hexdigest()
        path = out/f'ratings_{season}.json'
        if path.exists():
            ratings = json.loads(path.read_text())
            if ratings['canonical_training_sha256'] != digest:
                raise ValueError('Cached baseline training history changed')
        else:
            print(f'Fitting {season}: {len(prior)} prior games, cutoff {cutoff}', flush=True)
            ratings = fit(matches, as_of=cutoff.to_pydatetime(),
                          optimizer_options={'maxfun': 500000, 'maxiter': 2000},
                          preserve_fitted_rates=True)
            if not ratings.get('converged'):
                raise ValueError(f'Baseline failed convergence: {ratings}')
            ratings['canonical_training_sha256'] = digest
            path.write_text(json.dumps(ratings, default=str, indent=2)+'\n')
        elo = build_elo_before(matches, cutoff)
        for _, r in current.iterrows():
            if r.home_team not in ratings['teams'] or r.away_team not in ratings['teams']:
                failures.append({'match_id': r.match_id, 'reason': 'missing_prior_team_strength'})
                continue
            q = price(r.home_team, r.away_team, ratings, elo=elo, matches=matches, as_of=r.Date)
            matrix = q['scoreline_matrix']
            if matrix.min() < 0 or abs(matrix.sum()-1) > 1e-9:
                failures.append({'match_id': r.match_id, 'reason': 'invalid_score_distribution'})
                continue
            rows.append({'match_id':r.match_id, 'season':season, 'date':str(r.Date.date()),
                         'home':r.home_team, 'away':r.away_team,
                         'lambda_home':q['lambda_home'], 'lambda_away':q['lambda_away'],
                         'p_home':q['p_home'], 'p_draw':q['p_draw'], 'p_away':q['p_away'],
                         'home_goals':r.home_goals, 'away_goals':r.away_goals})
        print(f'{season}: converged; {len(rows)} cumulative predictions', flush=True)
    pd.DataFrame(rows).to_csv(out/'predictions.csv', index=False)
    (out/'audit.json').write_text(json.dumps({'failures':failures,
        'method':'Season-forward corrected DC normalization + frozen season-start UCL Elo + prior UCL form/rest',
        'limitations':['Historical domestic form and injuries unavailable for baseline; live tier inputs differ.',
                       'No market features; missing teams rejected; historical archive retains its xG/goals fallback.']}, indent=2)+'\n')


if __name__ == '__main__':
    main()
