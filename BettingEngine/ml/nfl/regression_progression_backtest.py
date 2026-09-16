"""Walk-forward NFL totals regression/progression challenger.

Train on 2021-2024 seasons and score the untouched 2025 (2025/26) season.
The challenger predicts the next-game residual to the existing total model using
only rolling pre-game team history and pre-game EPA process estimates.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT=Path(__file__).resolve().parents[2]
FEATURES=ROOT/'data/nfl/features/weekly_epa.parquet'
WF=ROOT/'data/nfl/predictions/step4_challenger.csv'
VAULT=ROOT/'data/nfl/predictions/step5_2025_vault_scored.csv'
OUT=ROOT/'data/nfl/predictions/regression_progression_2025.csv'
REPORT=ROOT/'ml/nfl/reports/regression_progression_backtest.json'

# Four prior seasons before the locked 2025/26 holdout.
TRAIN_SEASONS={2021,2022,2023,2024}; TEST_SEASON=2025

def _base_predictions() -> pd.DataFrame:
    wf=pd.read_csv(WF)
    wf=wf.rename(columns={'tree_total':'base_total'})[['game_id','season','week','base_total']]
    v=pd.read_csv(VAULT)
    v=v.rename(columns={'ridge_total':'ridge_total_v','tree_total':'base_total'})
    v=v[['game_id','season','week','base_total']]
    return pd.concat([wf,v],ignore_index=True).drop_duplicates('game_id')

def _rolling_process(frame: pd.DataFrame) -> pd.DataFrame:
    f=frame.sort_values(['gameday','game_id']).copy()
    histories: dict[str,list[dict[str,float]]]={}
    rows=[]
    for r in f.itertuples(index=False):
        def state(team, prefix):
            h=histories.get(team,[]); out={}
            for n in (4,8,12):
                z=h[-n:]
                out[f'{prefix}_points_l{n}']=float(np.mean([x['points'] for x in z])) if z else np.nan
                out[f'{prefix}_epa_l{n}']=float(np.mean([x['epa'] for x in z])) if z else np.nan
                out[f'{prefix}_gap_l{n}']=float(np.mean([x['points']-x['epa_points'] for x in z])) if z else np.nan
                out[f'{prefix}_games_l{n}']=len(z)
            return out
        h,a=r.home_team,r.away_team; vals={**state(h,'home'),**state(a,'away')}
        # Pregame process estimates are already point-in-time features.
        vals.update({'home_process_epa':float(r.home_off_epa),'away_process_epa':float(r.away_off_epa),
                     'home_def_epa':float(r.home_def_epa),'away_def_epa':float(r.away_def_epa)})
        vals['process_gap_l4_diff']=vals.get('home_gap_l4',np.nan)-vals.get('away_gap_l4',np.nan)
        vals['process_gap_l8_diff']=vals.get('home_gap_l8',np.nan)-vals.get('away_gap_l8',np.nan)
        vals['process_gap_l12_diff']=vals.get('home_gap_l12',np.nan)-vals.get('away_gap_l12',np.nan)
        vals['scoring_form_diff_l4']=vals.get('home_points_l4',np.nan)+vals.get('away_points_l4',np.nan)
        vals['scoring_form_diff_l8']=vals.get('home_points_l8',np.nan)+vals.get('away_points_l8',np.nan)
        vals.update({'game_id':r.game_id,'season':r.season,'week':r.week})
        rows.append(vals)
        # Actual scoring and EPA process are added only after this game.
        histories.setdefault(h,[]).append({'points':float(r.home_score),'epa':float(r.home_off_epa),'epa_points':float(r.home_off_epa)*30+21})
        histories.setdefault(a,[]).append({'points':float(r.away_score),'epa':float(r.away_off_epa),'epa_points':float(r.away_off_epa)*30+21})
    return pd.DataFrame(rows)

def _roi(edge, result_margin, threshold):
    over=edge>=threshold; under=edge<=-threshold; sel=over|under
    win=((over)&(result_margin>0))|((under)&(result_margin<0)); loss=((over)&(result_margin<0))|((under)&(result_margin>0)); push=sel&(result_margin==0)
    n=int(sel.sum()); w=int(win.sum()); l=int(loss.sum()); p=int(push.sum())
    return {'bets':n,'wins':w,'losses':l,'pushes':p,'win_rate_ex_pushes':w/(w+l) if w+l else None,'synthetic_roi_at_minus_110':(w*100/110-l)/n if n else None}

def run():
    raw=pd.read_parquet(FEATURES)
    raw=raw[(raw.game_type if 'game_type' in raw else pd.Series('REG',index=raw.index)).eq('REG')] if 'game_type' in raw else raw
    raw=raw[raw.season.between(2021,2025)].copy()
    process=_rolling_process(raw)
    base=_base_predictions()
    d=raw[['game_id','season','week','gameday','home_team','away_team','total','total_line_open','total_line_close']].merge(process,on=['game_id','season','week'],validate='one_to_one').merge(base,on=['game_id','season','week'],validate='one_to_one')
    d['base_error']=d.total-d.base_total
    d['feature_cols']=[None]*len(d)
    feature_cols=[c for c in process.columns if c not in {'game_id','season','week'} and pd.api.types.is_numeric_dtype(process[c])]
    train=d[d.season.isin(TRAIN_SEASONS)].copy(); test=d[d.season.eq(TEST_SEASON)].copy()
    # Drop early-season rows without a complete rolling history; fill remaining values from training medians.
    feature_cols=[c for c in feature_cols if c in d and c not in {'season','week'}]
    med=train[feature_cols].median().fillna(0)
    model=make_pipeline(StandardScaler(),Ridge(alpha=20.0))
    model.fit(train[feature_cols].fillna(med),train.base_error)
    d['adjustment']=model.predict(d[feature_cols].fillna(med)); d['adjusted_total']=d.base_total+d.adjustment
    d['adjusted_error']=d.total-d.adjusted_total; d['base_total_edge']=d.base_total-d.total_line_open; d['adjusted_total_edge']=d.adjusted_total-d.total_line_open; d['total_result_margin']=d.total-d.total_line_open
    scored=d[d.season.eq(TEST_SEASON)].copy()
    def metrics(x): return {'games':int(len(x)),'mae':float(np.abs(x.total-x.pred).mean()),'rmse':float(np.sqrt(np.mean((x.total-x.pred)**2)))}
    mb=pd.DataFrame({'total':scored.total,'pred':scored.base_total}); ma=pd.DataFrame({'total':scored.total,'pred':scored.adjusted_total})
    report={'status':'nfl_regression_progression_backtest_complete','train_seasons':sorted(TRAIN_SEASONS),'test_season':TEST_SEASON,'train_games':int(len(train)),'test_games':int(len(scored)),'feature_count':len(feature_cols),'model':'standardized_ridge_residual_alpha_20','features':feature_cols,'metrics':{'base':metrics(mb),'adjusted':metrics(ma)},'roi_minus_110':{str(t):_roi(scored.adjusted_total_edge,scored.total_result_margin,t) for t in (0,1,2,3)},'base_roi_minus_110':{str(t):_roi(scored.base_total_edge,scored.total_result_margin,t) for t in (0,1,2,3)},'by_season':{str(int(s)):{'games':int(len(g)),'base_mae':float(np.abs(g.total-g.base_total).mean()),'adjusted_mae':float(np.abs(g.total-g.adjusted_total).mean())} for s,g in d.groupby('season')},'restrictions':['2025/26 is the locked holdout','ROI is synthetic -110 because complete historical obtainable prices are unavailable','EPA-to-points conversion is a transparent proxy; no future game information is used','staking disabled']}
    d.drop(columns=['feature_cols'],errors='ignore').to_csv(OUT,index=False); REPORT.parent.mkdir(parents=True,exist_ok=True); REPORT.write_text(json.dumps(report,indent=2)+'\n'); return report
if __name__=='__main__': print(json.dumps(run(),indent=2))
