"""Week 1 normal versus UCL-trained player shadow; never a production signal."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import sys
import json
import hashlib
import shutil
import joblib
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from ml.football.ucl_player_features import FEATURE_COLS, lineup_features
from scripts.train_ucl_player_shadow import adjust_1x2


def shadow_price(normal, features, model):
    if model['feature_cols']!=FEATURE_COLS or not 0<float(model['cap'])<=.12:
        raise ValueError('Player model feature contract or adjustment cap differs')
    x=np.array([[features[c] for c in FEATURE_COLS]])
    if not np.isfinite(x).all():raise ValueError('Nonfinite player features')
    delta=np.clip(model['model'].predict(x)[0],-model['cap'],model['cap'])
    lam,mu=normal['expected_goals']['home'],normal['expected_goals']['away']
    sh,sa=max(.05,lam+float(delta[0])),max(.05,mu+float(delta[1]))
    prob=adjust_1x2(normal['probabilities'],lam,mu,sh,sa)
    if not np.isfinite(prob).all() or np.min(prob)<=0 or abs(sum(prob)-1)>1e-9:
        raise ValueError('Invalid player-shadow probabilities')
    return {'expected_goals':{'home':sh,'away':sa},'delta_goals':dict(zip(('home','away'),delta.tolist())),
            'probabilities':dict(zip(('home','draw','away'),prob.tolist())),
            'fair_odds':dict(zip(('home','draw','away'),(1/prob).tolist()))}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--snapshot',type=Path,default=ROOT/'data/ucl/player_layer/week1_projected_snapshot.json')
    ap.add_argument('--model',type=Path,default=ROOT/'data/ucl/player_layer/ucl_player_shadow_candidate.joblib')
    ap.add_argument('--baseline',type=Path,default=ROOT/'outputs/football/ucl/2026-27/md01/_supporting/2026-09-08_researched/run1/prices.json')
    ap.add_argument('--history',type=Path,default=ROOT/'data/ucl/player_layer/prepared/audited_history.csv')
    args=ap.parse_args()
    folder=ROOT/'data/ucl/player_layer'
    model_path=args.model.resolve()
    snapshot_path=args.snapshot.resolve()
    baseline_path=args.baseline.resolve()
    model=joblib.load(model_path)
    snapshot=json.loads(snapshot_path.read_text())
    baseline=json.loads(baseline_path.read_text())
    hist=pd.read_csv(args.history,dtype={'player_id':str,'event_id':str})
    hist['date']=pd.to_datetime(hist.kickoff,utc=True)
    hist=hist.sort_values(['date','event_id','player_id'])
    cutoff=pd.Timestamp(snapshot['cutoff_utc'])
    if pd.Timestamp(model['report']['fit_latest_match'],tz='UTC')>=cutoff:
        raise ValueError('Player model trained on results after snapshot')
    for name in ['source_published_at_utc','source_modified_at_utc','source_retrieved_at_utc']:
        if pd.Timestamp(snapshot[name])>cutoff:raise ValueError('Future snapshot provenance')
    rows=[]; events=[]
    for base in baseline['rows']:
        row={k:base[k] for k in ['home','away','sydney_match_date','kickoff_utc']}
        if cutoff>=pd.Timestamp(base['kickoff_utc']):raise ValueError('Snapshot is not prematch')
        row.update(status='BLOCKED',normal=base.get('scenarios',{}).get('confirmed_outs'),
                   shadow=None,betting_enabled=False,tiers=base['tier_audit'].copy(),blockers=[])
        row['tiers']['T2_availability']='UCL-trained Ridge player residual, capped at +/-0.12 additive goals, on sourced projected XI; added to frozen positional-injury research baseline.'
        row['tiers']['T3_player_workload']='Prior eight roster records enter rolling minutes; prior-30-day minutes and last appearance retained as diagnostics.'
        lineup=[]
        for side in ('home','away'):
            team=snapshot['teams'][base[side]]
            if team['status']!='complete':row['blockers'].append({'team':base[side],'reason':'projected_lineup_unresolved','details':team['unresolved']+team['confirmed_out_conflicts']})
            for player in team['projected_players']:
                item={**player,'side':side}
                lineup.append(item)
                recent=hist[(hist.player_id==item['player_id'])&(hist.date<cutoff)&
                            (hist.date>=cutoff-pd.Timedelta(days=30))&hist.quality_ok]
                item['minutes_prior_30_days']=float(recent.minutes.sum())
                item['latest_valid_appearance']=str(recent[recent.minutes>0].date.max())
                source=player.get('lineup_source') or snapshot['source']
                published='2026-09-07T12:25:09Z' if player.get('lineup_source') else snapshot['source_published_at_utc']
                if item['expected_minutes_share'] is not None:
                    events.append({'event_id':f"{base['home']}--{base['away']}--{item['player_id']}",
                        'match_id':f"{base['home']}--{base['away']}--{base['sydney_match_date']}",
                        'club_id':base['inputs'][side]['club_id'] or base[side],
                        'player_id':item['player_id'],'role':item['position_group'],'status':'projected_starter',
                        'expected_minutes_share':item['expected_minutes_share'],
                        'announced_at_utc':published,'source':source,'source_published_at_utc':published,
                        'recorded_at_utc':str(cutoff),'cutoff_utc':str(cutoff),'kickoff_utc':base['kickoff_utc'],
                        'minutes_method':item['expected_minutes_method']})
        feat,audit=lineup_features(hist,lineup,cutoff)
        missing=[p['player_name'] for p in audit if p['history'] is None or p['position_group'] not in ('GK','DEF','MID','ATT')]
        if missing or len(audit)!=22:row['blockers'].append({'reason':'incomplete_player_features','players':missing,'count':len(audit)})
        if row['normal'] is None:row['blockers'].append({'reason':'missing_cross_league_baseline_strength'})
        row['player_audit']=audit;row['features']=feat
        if not row['blockers']:
            row['shadow']=shadow_price(row['normal'],feat,model)
            row['status']='RESEARCH_PLAYER_SHADOW'
        rows.append(row)
    report={'generated_at_utc':datetime.now(timezone.utc).isoformat(),'cutoff_utc':str(cutoff),
        'normal_cutoff_utc':baseline['cutoff_utc'],'production_promoted':False,'model_evaluation':model['report'],
        'method':'Same Ridge alpha=50/lsqr, 56 position-grouped rolling features, eight prior roster rows, +/-0.12 additive goal cap and 1X2 probability-ratio adjustment as EPL/EFL; UCL-specific coefficients.',
        'limitations':['Predicted lineups are not confirmed XIs.',
            'Baseline remains the saved researched 1X2 price, including positional injuries and domestic form/rest.',
            'Positional injury effects and player residuals can overlap; chronological baseline lacks historical injury input.',
            'Totals withheld: the separate live U/O champion has not been integrated.',
            'Referee/weather, pressing/travel/rotation, market quotes and confluence are not numerical adjustments.',
            'No market EV, betting signals, stakes or placements.'],
        'rows':rows,'priced':sum(r['shadow'] is not None for r in rows),
        'sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
                  [model_path,snapshot_path,baseline_path,args.history.resolve(),Path(__file__),ROOT/'ml/football/ucl_player_features.py']}}
    args.output.mkdir(parents=True,exist_ok=False)
    frozen=args.output/'inputs';frozen.mkdir()
    for path in [model_path,snapshot_path,baseline_path,args.history,Path(__file__),ROOT/'ml/football/ucl_player_features.py']:
        shutil.copy2(path,frozen/path.name)
    (args.output/'prices.json').write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
    pd.DataFrame(events).to_csv(args.output/'projected_player_events.csv',index=False)
    flat=[]
    lines=['# Week 1 Champions League — normal and player shadow','',
           'Research comparison only. Normal is the saved injury/form/rest price; shadow adds a UCL-trained player residual from the sourced projected XI. Decimal fair odds, 90 minutes.','',
           '| Match | Normal H | D | A | Shadow H | D | A |','|---|---:|---:|---:|---:|---:|---:|']
    for row in rows:
        cells=[]; item={k:row[k] for k in ['home','away','status']}
        for kind in ('normal','shadow'):
            odds=row[kind]['fair_odds'] if row[kind] else {}
            cells.extend(f'{odds[k]:.2f}' if k in odds else '—' for k in ('home','draw','away'))
            item.update({f'{kind}_{k}':odds.get(k) for k in ('home','draw','away')})
        lines.append(f"| {row['home']} v {row['away']} | "+' | '.join(cells)+' |');flat.append(item)
    ev=model['report']
    lines+=['','## Holdout evidence','',
        f"Trained on {ev['train_matches']} eligible 2024/25 matches; tested on {ev['test_matches']} eligible 2025/26 matches. Goal MAE: {ev['base_goal_mae']:.6f} normal, {ev['adjusted_goal_mae']:.6f} shadow. 1X2 RPS: {ev['base_1x2']['rps']:.6f} normal, {ev['shadow_1x2']['rps']:.6f} shadow. Lower is better. No production approval.",'',
        '## Tiers','',
        'T0 validates inputs/cutoffs and blocks missing strengths or player identities. T1 is the frozen converged DC/Elo strength. T2 now uses identified projected players, rolling statistics and minutes, alongside the baseline positional absences. T3 retains domestic form/rest and records player workload. T4 is neutral for MD1. T5 is not applicable. T6 referee/weather, T7 market disagreement and T8 confluence remain diagnostic/unpopulated; they do not change prices.','',
        '## Limits','',*['- '+s for s in report['limitations']+ev['limitations']],
        '', 'Per-player IDs, rolling-history counts, expected-minute estimates, workload, sources, blockers and all 56 inputs are saved in prices.json.']
    pd.DataFrame(flat).to_csv(args.output/'prices.csv',index=False)
    (args.output/'report.md').write_text('\n'.join(lines)+'\n')
    print(f"Saved {report['priced']} player-shadow prices to {args.output}")


if __name__=='__main__':main()
