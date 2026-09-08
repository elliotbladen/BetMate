"""Frozen diagnostic run of the existing UCL adapter; never produces bet signals."""
from pathlib import Path
from dataclasses import asdict
import hashlib
import json
import sys
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from ml.football import ucl_shared_engine as engine
from ml.football.ucl_player_shadow import run_status
from ml.football.ucl_tiers import status

OUT = Path(__file__).parent
CUTOFF = '2026-09-07T23:49:26Z'
SOURCES = {
 'fixtures': 'https://www.uefa.com/uefachampionsleague/news/02a8-2174c9e9019d-f909a77bd77a-1000--2026-27-champions-league-all-the-league-phase-fixtures/',
 'team_news': 'https://www.uefa.com/uefachampionsleague/news/02a9-2188cf675017-df8325ec95c3-1000--champions-league-predicted-line-ups-matchday-1-team-news-/',
 'referees': 'https://www.uefa.com/uefachampionsleague/news/02a9-218880e7a2aa-96adf63aa534-1000--who-is-the-referee-which-officials-are-in-charge-of-the-uefa/',
}
# Explicit IDs refer to the most recent archive identity, not a fuzzy name match.
# Missing identities stay missing; generic league-average fallback is forbidden.
FIXTURES = [
 ('2026-09-08','AEK Athens','LASK','aek-athen',None,'Luis Godinho'),
 ('2026-09-08','Club Brugge','Aston Villa','club-brugge-kv','aston-villa-fc','Sandro Schärer'),
 ('2026-09-08','Borussia Dortmund','Villarreal','borussia-dortmund','villarreal-cf','Simone Sozza'),
 ('2026-09-08','Porto','Manchester City','fc-porto','manchester-city-fc','Szymon Marciniak'),
 ('2026-09-08','Lille','Real Betis','lille-osc',None,'Georgi Kabakov'),
 ('2026-09-08','Real Madrid','Inter','real-madrid-cf','fc-internazionale-milano','Michael Oliver'),
 ('2026-09-09','Barcelona','Feyenoord','fc-barcelona','feyenoord-rotterdam','Sven Jablonski'),
 ('2026-09-09','Stuttgart','Viking','vfb-stuttgart',None,'Nenad Minaković'),
 ('2026-09-09','Liverpool','Atlético de Madrid','liverpool-fc','club-atl-tico-de-madrid','Davide Massa'),
 ('2026-09-09','Paris Saint-Germain','Slovan Bratislava','paris-saint-germain-fc','k-slovan-bratislava','Mykola Balakin'),
 ('2026-09-09','Sporting CP','Galatasaray','sporting-clube-de-portugal','galatasaray-sk','Espen Eskås'),
 ('2026-09-09','Napoli','Arsenal','ssc-napoli','arsenal-fc','Glenn Nyberg'),
]


def main():
    m = engine.load_matches()
    m = m[m.Date < pd.Timestamp(CUTOFF)].copy()
    print('Fitting existing UCL adapter on',len(m),'rows; latest:',m.Date.max(),flush=True)
    ratings = engine.fit_before(m, CUTOFF)
    elo = engine.build_elo_before(m, CUTOFF)
    print('Fit converged:',ratings.get('converged'),flush=True)
    rows = []
    for date,home,away,h,a,ref in FIXTURES:
        row = dict(european_match_date=date, sydney_match_date=str(pd.Timestamp(date).date()+pd.Timedelta(days=1)),home=home,away=away,home_id=h,away_id=a,referee=ref,live_status='ABSTAIN',all_tiers_priced=False)
        coverage={}
        for side,team in [('home',h),('away',a)]:
            d=m[(m.home_team==team)|(m.away_team==team)] if team else m.iloc[:0]
            coverage[side]={'matches':len(d),'last_archive_match':str(d.Date.max()) if len(d) else None,'archive_age_days':int((pd.Timestamp(CUTOFF)-d.Date.max()).days) if len(d) else None}
        row['history_coverage']=coverage
        row['tiers']={
            'T0':'FAIL: stale current inputs; incomplete full-tier integration; no verified live market captured',
            'T1':'historical paper baseline only; no current domestic strength input; archive aliases split',
            'T2':'UEFA team news reviewed; player-event file missing; no fitted active player adjustment',
            'T3':'adapter uses old UCL form/rest; domestic schedule, rotation, pressing and travel not loaded',
            'T4':'league-phase diagnostic only; no live incentive adjustment',
            'T5':'not applicable: league phase, not knockout',
            'T6':'referee appointment sourced; no referee-rate/weather pricing input consumed by adapter',
            'T7':'market diagnostic unavailable: no current timestamped two-sided quote captured',
            'T8':'confluence diagnostic; no validated current family signals',
        }
        if not h or not a or h not in ratings['teams'] or a not in ratings['teams']:
            row['baseline_status']='BLOCKED_MISSING_TEAM_HISTORY'
            row['diagnostic_prices']=None
        else:
            p=engine.price(h,a,ratings,elo=elo,matches=m,as_of=CUTOFF)
            probs=[p[k] for k in ('p_home','p_draw','p_away')]
            assert np.isfinite(probs).all() and min(probs)>0 and abs(sum(probs)-1)<1e-8
            assert np.isfinite(p['scoreline_matrix']).all() and (p['scoreline_matrix']>=0).all()
            row['baseline_status']='UNVALIDATED_DIAGNOSTIC_ONLY'
            row['diagnostic_prices']={k:round(1/p[k],4) for k in ('p_home','p_draw','p_away','p_over25','p_under25')}
            row['diagnostic_probabilities']={k:p[k] for k in ('p_home','p_draw','p_away','p_over25','p_under25')}
            row['shared_engine_adjustments']=asdict(p['tier_audit'])
            # Raw score-matrix totals are diagnostics, NOT the separate O/U champion/challenger.
            row['totals_status']='raw shared-matrix diagnostic; separate live O/U model not run'
        rows.append(row)
        print(home,'v',away,row['baseline_status'],flush=True)
    report={'cutoff_utc':CUTOFF,'scope':'European 8–9 September / Sydney mornings 9–10 September 2026','sources':SOURCES,'source_pages_reviewed_at_utc':CUTOFF,'generic_cli_failure':"price_match.py --league ucl: KeyError: 'rho'",'history_rows':len(m),'history_latest':str(m.Date.max()),'xg_sources':m.xg_source.value_counts().to_dict(),'fit_converged':bool(ratings.get('converged')),'player_shadow':run_status(),'configured_tiers':status('league_phase'),'matches_requested':len(rows),'diagnostic_baselines':sum(r['diagnostic_prices'] is not None for r in rows),'proper_full_tier_prices':0,'staking_enabled':False,'rows':rows}
    paths=[Path(engine.__file__),ROOT/'ml/football/models/dixon_coles.py',ROOT/'ml/football/models/tiers.py',engine.REPAIRED,engine.XG_COMPLETE]
    report['input_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.exists()}
    with (OUT/'audit.json').open('x') as f: json.dump(report,f,indent=2,ensure_ascii=False,allow_nan=False)
    lines=['# UCL pricing attempt — 8 September 2026','','**Outcome: 0 of 12 matches can be priced properly with all tiers.**', '', 'Scope: European 8–9 September; Sydney mornings 9–10 September. Existing Python UCL adapter executed; no model parameters or production gates changed.', '', f"The generic CLI fails with `KeyError: rho`. The adapter generated {report['diagnostic_baselines']} numerical baselines; 3 matches were blocked before pricing because an opponent has no archive history. Numerical output is not full-tier pricing.",'',f"History: {len(m)} rows, latest {m.Date.max()}. Optimizer convergence: {report['fit_converged']}. Current domestic form and 2026/27 availability are not consumed. Multiple clubs have split historic aliases; selecting their latest ID does not repair the missing earlier history.",'', '## All-tier audit','','| Tier | Result |','|---|---|']
    lines += [f'| {k} | {v} |' for k,v in rows[0]['tiers'].items()]
    lines += ['', 'Official team news and all 12 referee appointments were found. Their availability does not mean the Python model uses them. Player shadow remains data-pending and cannot set prices. Separate U/O scripts are historical challenger backtests, not a ready live full-tier pricer. No live market EV was calculated.', '', '## Match coverage','','| Match | Sydney date | Baseline result |','|---|---|---|']
    lines += [f"| {r['home']} v {r['away']} | {r['sydney_match_date']} | {r['baseline_status']} |" for r in rows]
    lines += ['', 'Raw numerical diagnostics and individual tier/history coverage are retained in `audit.json` for debugging; none is a bet-ready quote.','','## Required before a proper price-up','','1. Implement a compatible UCL live entry point and tier input contract.','2. Reconcile club identities and load domestic strength for teams absent from UCL history.','3. Load timestamped current form/schedule and availability; validate the player model before price influence.','4. Connect approved market-specific models and current bookmaker quotes; keep unpromoted tiers diagnostic.','5. Re-run data-health, tier-coverage and model-validity checks.','','## Sources','']
    lines += [f'- [{k}]({v})' for k,v in SOURCES.items()]
    with (OUT/'report.md').open('x') as f: f.write('\n'.join(lines)+'\n')
    print(json.dumps({k:report[k] for k in ('matches_requested','diagnostic_baselines','proper_full_tier_prices','fit_converged')},indent=2))

if __name__=='__main__': main()
