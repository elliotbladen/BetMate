"""UCL chronological Ridge residual candidate using the EPL/EFL feature contract."""
from pathlib import Path
import sys
import json
import hashlib
import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from ml.football.ucl_player_features import FEATURE_COLS, lineup_features
from scripts.price_epl_week3_normal_shadow_2026 import poisson_markets


def adjust_1x2(normal, lam, mu, sh, sa):
    before, after = poisson_markets(lam,mu), poisson_markets(sh,sa)
    weights = np.array([normal[k]*after[k]/before[k] for k in ('home','draw','away')])
    return weights/weights.sum()


def main():
    folder = ROOT/'data/ucl/player_layer'
    hist = pd.read_csv(folder/'prepared/audited_history.csv',dtype={'player_id':str,'event_id':str})
    hist['date'] = pd.to_datetime(hist.kickoff,utc=True)
    hist = hist.sort_values(['date','event_id','player_id'])
    aliases = json.loads((folder/'espn_club_aliases.json').read_text())
    baseline = pd.read_csv(folder/'baselines_v2/predictions.csv')
    index = baseline.set_index(['date','home','away']).sort_index()
    joined, excluded = [], []
    for eid, game in hist[hist.league == 'uefa.champions'].groupby('event_id'):
        row = game.iloc[0]
        if row.match_status != 'STATUS_FULL_TIME':
            excluded.append({'event_id':eid,'reason':'extra_time_or_penalties_excluded_from_90min_target'})
            continue
        key = (str(row.date.date()), aliases.get(row.home_team), aliases.get(row.away_team))
        if key not in index.index:
            excluded.append({'event_id':eid,'reason':'no_validated_baseline'})
            continue
        base = index.loc[key]
        if isinstance(base,pd.DataFrame):
            raise ValueError('Ambiguous baseline match join')
        if float(row.home_goals) != base.home_goals or float(row.away_goals) != base.away_goals:
            excluded.append({'event_id':eid,'reason':'score_disagrees_with_baseline_archive'})
            continue
        lineup = game[game.starter == 1][['player_id','player_name','position_group','side']].to_dict('records')
        features, audit = lineup_features(hist,lineup,row.date)
        if len(audit)!=22 or any(p['history'] is None or p['position_group'] not in ('GK','DEF','MID','ATT') for p in audit):
            excluded.append({'event_id':eid,'reason':'incomplete_prior_player_coverage'})
            continue
        joined.append({**base.to_dict(),**features,'event_id':eid,'date':key[0]})
    data = pd.DataFrame(joined)
    data.to_csv(folder/'prepared/training_features.csv',index=False)
    train=data[data.season == '2024-25']; test=data[data.season == '2025-26']
    if len(train)<50 or len(test)<50:
        raise ValueError(f'Insufficient eligible train/test games: {len(train)}/{len(test)}')
    ytrain=np.c_[train.home_goals-train.lambda_home, train.away_goals-train.lambda_away]
    ytest=np.c_[test.home_goals-test.lambda_home, test.away_goals-test.lambda_away]
    model=Ridge(alpha=50.0,solver='lsqr').fit(train[FEATURE_COLS].values,ytrain)
    delta=np.clip(model.predict(test[FEATURE_COLS].values),-.12,.12)
    before=test[['p_home','p_draw','p_away']].values
    after=[]
    for (_, r), correction in zip(test.iterrows(),delta):
        after.append(adjust_1x2(dict(zip(('home','draw','away'),[r.p_home,r.p_draw,r.p_away])),
            r.lambda_home,r.lambda_away,max(.05,r.lambda_home+correction[0]),max(.05,r.lambda_away+correction[1])))
    after=np.array(after)
    actual=np.where(test.home_goals>test.away_goals,0,np.where(test.home_goals==test.away_goals,1,2))
    target=np.eye(3)[actual]
    def metrics(prob):
        return {'rps':float(np.mean(np.sum((np.cumsum(prob,axis=1)[:,:2]-np.cumsum(target,axis=1)[:,:2])**2,axis=1)/2)),
                'log_loss':float(-np.log(prob[np.arange(len(actual)),actual]).mean()),
                'brier':float(np.mean(np.sum((prob-target)**2,axis=1)))}
    base_mae=float(np.mean(np.abs(ytest))); shadow_mae=float(np.mean(np.abs(ytest-delta)))
    report={'model':'ridge_position_rolling_ucl_v1','train_season':'2024-25','test_season':'2025-26',
        'train_matches':len(train),'test_matches':len(test),'features':len(FEATURE_COLS),
        'base_goal_mae':base_mae,'adjusted_goal_mae':shadow_mae,'improvement':base_mae-shadow_mae,
        'base_1x2':metrics(before),'shadow_1x2':metrics(after),'cap_goals':.12,
        'efl_mae_gate_passed':shadow_mae<base_mae,
        'production_approved':False,'mode':'research_shadow_only',
        'limitations':['One UCL holdout season; no live betting promotion.',
            'Training uses final historical XIs; live use of projected XIs is a different information regime.',
            'Domestic history currently starts January 2026, so feature coverage differs between seasons.',
            'Historical baseline form/rest is UCL-only; live researched baseline has domestic form/rest and positional injuries.',
            'ID-based nominal minutes replace inherited 65/25 fallbacks; same 56 features, Ridge alpha/solver and additive cap.'],
        'excluded':excluded}
    final=Ridge(alpha=50.0,solver='lsqr').fit(data[FEATURE_COLS].values,
              np.c_[data.home_goals-data.lambda_home,data.away_goals-data.lambda_away])
    report['fit_latest_match']=str(data.date.max())
    report['training_features_sha256']=hashlib.sha256((folder/'prepared/training_features.csv').read_bytes()).hexdigest()
    joblib.dump({'model':final,'feature_cols':FEATURE_COLS,'cap':.12,'report':report},folder/'ucl_player_shadow_candidate.joblib')
    (folder/'ucl_player_shadow_evaluation.json').write_text(json.dumps(report,indent=2)+'\n')
    test=test.copy();test['delta_home']=delta[:,0];test['delta_away']=delta[:,1]
    test['shadow_p_home']=after[:,0];test['shadow_p_draw']=after[:,1];test['shadow_p_away']=after[:,2]
    test.to_csv(folder/'prepared/holdout_predictions.csv',index=False)
    print(json.dumps({k:v for k,v in report.items() if k!='excluded'},indent=2))


if __name__=='__main__':main()
