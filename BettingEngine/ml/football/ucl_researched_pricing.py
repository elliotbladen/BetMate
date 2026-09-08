"""Price sourced UCL research scenarios without promoting them to production.

Usage: python -m ml.football.ucl_researched_pricing --context FILE --aliases FILE
       --ratings FILE --output NEW_DIRECTORY

The explicit context replaces stale UCL-only form/rest. The trained player shadow
and separate totals challenger remain separate; no bet signals are emitted.
"""
from __future__ import annotations
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from .ucl_shared_engine import load_matches, build_elo_before, price
from .models.tiers import TeamState, MatchContext, POSITION_WEIGHTS


def team_state(club_id: str, context: dict, include_doubtful: bool = False,
               apply_absences: bool = True) -> TeamState:
    games=context['league_results']
    if not 1 <= len(games) <= 5:
        raise ValueError('Need one to five verified current league results')
    points=sum(r['points'] for r in games)
    if any(r['points'] not in (0,1,3) for r in games):
        raise ValueError('Invalid form result')
    # Explicit neutral prior for unplayed early-season slots; never fake rows.
    form=points+1.5*(5-len(games))
    selected=[]
    for e in context['availability']:
        if e['position'] not in POSITION_WEIGHTS or not e.get('source'):
            raise ValueError('Unreviewed availability event')
        if apply_absences and (e['status']=='out' or include_doubtful and e['status']=='doubtful'):
            selected.append(e['position'])
    return TeamState(name=club_id,form5_pts=form,rest_days=context['rest_days'],injuries=selected)


def validate_fixture(fixture: dict, cutoff: str) -> None:
    cut=pd.Timestamp(cutoff)
    kick=pd.Timestamp(fixture['kickoff_utc'])
    if cut.tzinfo is None or kick.tzinfo is None or cut>=kick:
        raise ValueError('Prediction cutoff must precede kickoff in UTC')
    for side in ('home_context','away_context'):
        c=fixture[side]
        if pd.Timestamp(c['data_as_of_utc'])>cut:
            raise ValueError('Context was observed after prediction cutoff')
        for r in c['league_results']:
            date=pd.Timestamp(r['date'],tz='UTC')
            if date>=cut.normalize() or date<cut-pd.Timedelta(days=70):
                raise ValueError('Future or stale form result')
            if not r.get('source'):
                raise ValueError('Missing result provenance')
        if c['rest_days']<0 or c['rest_days']>30:
            raise ValueError('Invalid or stale rest input')
        for e in c['availability']:
            if pd.Timestamp(e['retrieved_at_utc'])>cut:
                raise ValueError('Availability observed after cutoff')


def forecast(home: str,away: str,ratings: dict,elo,context: MatchContext | None) -> dict:
    if not ratings.get('converged'):
        raise ValueError('Cannot publish prices from a nonconverged fit')
    if home not in ratings['teams'] or away not in ratings['teams']:
        raise ValueError('Missing team strength: generic fallback forbidden')
    p=price(home,away,ratings,elo=elo,context=context)
    v=np.array([p['p_home'],p['p_draw'],p['p_away']])
    if not np.isfinite(v).all() or min(v)<=0 or abs(v.sum()-1)>1e-9:
        raise ValueError('Invalid 1X2 probabilities')
    matrix=p['scoreline_matrix']
    if not np.isfinite(matrix).all() or np.min(matrix)<0 or abs(matrix.sum()-1)>1e-9:
        raise ValueError('Invalid score distribution')
    return {'probabilities':dict(zip(('home','draw','away'),v.tolist())),
            'fair_odds':dict(zip(('home','draw','away'),(1/v).tolist())),
            'expected_goals':{'home':p['lambda_home'],'away':p['lambda_away']},
            'adjustments':asdict(p['tier_audit']) if p['tier_audit'] else None}


def run(context_path: Path, aliases_path: Path, ratings_path: Path, output: Path) -> dict:
    manifest=json.loads(context_path.read_text())
    aliases=json.loads(aliases_path.read_text())
    ratings=json.loads(ratings_path.read_text())
    cut=manifest['cutoff_utc']
    if pd.Timestamp(ratings['as_of'])>pd.Timestamp(cut):
        raise ValueError('Model fit cutoff exceeds prediction cutoff')
    if not ratings.get('converged'):
        raise ValueError('Model fit did not converge')
    if not ratings.get('preserve_fitted_rates'):
        raise ValueError('UCL research requires rate-preserving rating normalization')
    m=load_matches()
    for c in ['home_team','away_team','home_club_id','away_club_id']:
        m[c]=m[c].replace(aliases)
    m=m[m.Date<pd.Timestamp(ratings['as_of'])]
    if len(m)!=ratings['n_matches'] or sorted(set(m.home_team)|set(m.away_team))!=sorted(ratings['teams']):
        raise ValueError('Cached ratings do not match canonicalized training archive')
    canonical_hash=hashlib.sha256(m.to_csv(index=False).encode()).hexdigest()
    if ratings.get('canonical_training_sha256')!=canonical_hash:
        raise ValueError('Cached ratings training hash does not match current archive')
    elo=build_elo_before(m,cut)
    rows=[]
    for f in manifest['fixtures']:
        validate_fixture(f,cut)
        h,a=f['home_context']['club_id'],f['away_context']['club_id']
        row={k:f[k] for k in ['home','away','sydney_match_date','kickoff_utc','referee']}
        row['status']='PROVISIONAL_RESEARCH_PRICE'
        row['betting_enabled']=False
        row['tier_audit']={
            'T0_data_health':'Research inputs validated; production gate remains closed pending model/tier validation and current quotes.',
            'T1_strength':'Converged shared DC + internal UCL Elo, harmonized IDs; no external ClubElo/domestic-strength anchor.',
            'T2_availability':'Current sourced absences applied using legacy football position weights in this research scenario; trained player shadow untouched.',
            'T3_form_rest':'Current domestic league results and latest club-match date replace old UCL-only context; calendar-day rest.',
            'T3_pressing_rotation_travel':'Not quantified: no verified PPDA, expected-minute or calibrated travel inputs.',
            'T4_league_phase':'MD1 neutral context; no invented must-win adjustment.',
            'T5_knockout':'Not applicable in league phase.',
            'T6_referee_weather':'Referee identity sourced; goal-rate/weather coefficients not populated or applied.',
            'T7_market':'No captured current two-sided market; EV unavailable.',
            'T8_confluence':'Not populated; no manufactured confluence.',
            'corners':'Not injected into 1X2; separate corner/O-U challenger remains unpromoted.'}
        row['inputs']={side:f[side+'_context'] for side in ['home','away']}
        row['totals_status']='Separate live O/U model not ready; no score-matrix totals relabelled as the O/U champion.'
        if not h or not a or h not in ratings['teams'] or a not in ratings['teams']:
            row['status']='BLOCKED_MISSING_CROSS_LEAGUE_STRENGTH'
            row['tier_audit']['T1_strength']='Missing established UCL baseline; recent domestic results alone do not establish comparable cross-league strength.'
        else:
            baseline=forecast(h,a,ratings,elo,None)
            no_abs=MatchContext(team_state(h,f['home_context'],apply_absences=False),team_state(a,f['away_context'],apply_absences=False))
            row['baseline']=baseline
            row['form_rest_only']=forecast(h,a,ratings,elo,no_abs)
            scenarios={}
            for hi,ai,label in [(False,False,'confirmed_outs'),(True,False,'home_doubts_out'),(False,True,'away_doubts_out'),(True,True,'both_doubts_out')]:
                c=MatchContext(team_state(h,f['home_context'],hi),team_state(a,f['away_context'],ai))
                scenarios[label]=forecast(h,a,ratings,elo,c)
            row['scenarios']=scenarios
            row['fair_odds']=scenarios['confirmed_outs']['fair_odds']
            row['availability_scenario_odds_range']={k:[min(s['fair_odds'][k] for s in scenarios.values()),max(s['fair_odds'][k] for s in scenarios.values())] for k in ['home','draw','away']}
            row['home_probability_change_pp']=100*(scenarios['confirmed_outs']['probabilities']['home']-baseline['probabilities']['home'])
        rows.append(row)
    report={'cutoff_utc':cut,'version':'ucl_researched_context_v1','production_promoted':False,'rows':rows,
            'convergence':{k:ratings[k] for k in ['converged','optimizer_message','optimizer_iterations','optimizer_evaluations']},
            'fit_matches':len(m),'fit_latest_result':str(m.Date.max()),'normalization_rate_scale':ratings['normalization_rate_scale'],'input_manifest':str(context_path),
            'method_notes':manifest['notes'],'priced':sum(r['status']=='PROVISIONAL_RESEARCH_PRICE' for r in rows)}
    paths=[context_path,aliases_path,ratings_path,Path(__file__),Path(__file__).parent/'ucl_shared_engine.py',Path(__file__).parent/'models/dixon_coles.py',Path(__file__).parent/'models/tiers.py']
    report['sha256']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    output.mkdir(parents=True,exist_ok=False)
    (output/'prices.json').write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
    flat=[]
    for r in rows:
        item={k:r[k] for k in ['home','away','sydney_match_date','status']}
        item.update({k+'_fair_odds':v for k,v in r.get('fair_odds',{}).items()})
        flat.append(item)
    pd.DataFrame(flat).to_csv(output/'prices.csv',index=False)
    lines=['# Researched UCL prices — 8 September 2026','',f"{report['priced']} provisional 1X2 prices from 12 fixtures. All use current researched form/rest and confirmed absences. These are research scenarios, not promoted full-tier production prices.",'', 'Decimal fair odds; H/D/A refers to home win/draw/away win over 90 minutes. Doubtful players are not assumed absent in the central price. Their alternative scenarios are in prices.json.','','| Sydney date | Match | Home | Draw | Away |','|---|---|---:|---:|---:|']
    for r in rows:
        odds=r.get('fair_odds')
        cells=' | '.join(f'{odds[k]:.2f}' for k in ['home','draw','away']) if odds else '— | — | —'
        lines.append(f"| {r['sydney_match_date']} | {r['home']} v {r['away']} | {cells} |")
    lines+=['','## Model and coverage','',f"The fit converged in {ratings['optimizer_iterations']} iterations and {ratings['optimizer_evaluations']} evaluations after explicit club-ID reconciliation. The likelihood and default tier coefficients were retained. Normalization now preserves fitted goal rates with base-rate compensation {ratings['normalization_rate_scale']:.6f}; legacy production callers retain their prior version. The cached fit uses {len(m)} UCL matches through {m.Date.max()}.",'', 'Current domestic form/rest and sourced availability enter the price explicitly. The injury method is the legacy football positional prior, not a trained UCL player valuation. Returning, doubtful and disputed players are scenario inputs. Replacement quality and expected minutes remain unmodelled; long-term absences can overlap with historical team strength. This limits confidence in large changes.','', 'Verified referee names do not supply referee scoring coefficients. PPDA, calibrated travel/rotation/weather and confluence remain missing; current bookmaker quotes were not captured. No EV or bet recommendation is generated. The player shadow is not promoted.','', 'AEK–LASK, Lille–Betis and Stuttgart–Viking still lack comparable baseline strength for an opponent. Recent domestic records were researched for them, but a few domestic results cannot replace the missing cross-league model.','', 'Totals are withheld: the separate U/O market model is not ready to consume these live tiers. Raw shared-score-matrix totals are not substituted for that model.','','## Current domestic input audit','','| Team | Points / games observed | Latest competitive match | Rest days |','|---|---:|---|---:|']
    for r in rows:
        for side in ['home','away']:
            c=r['inputs'][side]
            lines.append(f"| {r[side]} | {c['league_form_points']} / {c['form_matches']} | {c['latest_competitive_date']} | {c['rest_days']} |")
    lines+=['','Short early-season form samples use a neutral 1.5-point prior for each unplayed slot to fit the existing five-game feature; no match outcomes are invented. Form is league-only; rest uses the latest verified competitive club match.','','## Sources','','- [UEFA team news](https://www.uefa.com/uefachampionsleague/news/02a9-2188cf675017-df8325ec95c3-1000--champions-league-predicted-line-ups-matchday-1-team-news-/)','- [Football-Data domestic results](https://www.football-data.co.uk/downloadm.php)','- [Slovan official results](https://www.skslovan.com/zapasy/index.php?season=202627)','- [Real Madrid training](https://www.realmadrid.com/es-ES/noticias/futbol/primer-equipo/entrenamientos/el-equipo-se-esta-entrenando-07-09-2026)','- [Real Madrid press conference](https://www.realmadrid.com/es-ES/noticias/futbol/primer-equipo/ruedas-de-prensa/mourinho-07-09-2026)','- [Dimarco update](https://www.gazzetta.it/en/football/teams/inter/news/07-09-2026/dimarco-injury-wing-back-misses-real-madrid-clash.shtml)']
    (output/'report.md').write_text('\n'.join(lines)+'\n')
    print(pd.DataFrame(flat).to_string(index=False))
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['context','aliases','ratings','output']: p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();run(a.context,a.aliases,a.ratings,a.output)

if __name__=='__main__':main()
