"""UCL O/U2.5 challenger: direct logistic probability from pre-match rolling xG.
No same-match xG and no goals-as-xG fallback are allowed in this track.
"""
from pathlib import Path
import json, numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'data/ucl/matches/ucl_recent_complete_xg_v2.csv'
PRED=ROOT/'data/ucl/clv/ucl_totals_calibrated_predictions.csv'
ODDS=ROOT/'data/ucl/markets/ucl_footiqo_totals_backtest_2025_26.csv'
OUT=ROOT/'data/ucl/markets/ucl_ou25_challenger_2025_26.csv'
REPORT=ROOT/'ml/football/reports/ucl_ou25_challenger_backtest.json'

def features(d):
 d=d.copy(); d['kick']=pd.to_datetime(d['kickoff_utc'],utc=True); d=d.sort_values('kick').reset_index(drop=True)
 hist={}; rows=[]
 for _,r in d.iterrows():
  h=hist.get(r.home_club_id,[]); a=hist.get(r.away_club_id,[])
  # strictly prior xG; use competition-wide priors when a club has no history
  gh=d.loc[d.index < len(rows),['home_xg','away_xg']].mean() if rows else pd.Series({'home_xg':1.55,'away_xg':1.55})
  def av(x,k,default): return float(np.mean([z[k] for z in x[-5:]])) if x else default
  h_att=av(h,0,float(gh.home_xg)); h_def=av(h,1,float(gh.away_xg)); a_att=av(a,0,float(gh.away_xg)); a_def=av(a,1,float(gh.home_xg))
  stage=str(r.get('stage',''))
  rows.append({'match_id':r.match_id,'season':r.season,'stage':stage,'prematch_total_xg':max(.25,(h_att+h_def+a_att+a_def)/2),'home_att':h_att,'away_att':a_att,'knockout':int('knock' in stage.lower() or 'play' in stage.lower() or 'final' in stage.lower()),'y':int(r.home_goals+r.away_goals>2.5)})
  hist.setdefault(r.home_club_id,[]).append((float(r.home_xg),float(r.away_xg))); hist.setdefault(r.away_club_id,[]).append((float(r.away_xg),float(r.home_xg)))
 return pd.DataFrame(rows)

d=pd.read_csv(DATA); d=d.merge(pd.read_csv(PRED)[['match_id','stage']],on='match_id',how='left'); f=features(d)
tr=f[f.season=='2024-25']; te=f[f.season=='2025-26']
X=['prematch_total_xg','home_att','away_att','knockout']; model=make_pipeline(StandardScaler(),LogisticRegression(C=.5,max_iter=2000)); model.fit(tr[X],tr.y); te=te.copy(); te['p_model']=model.predict_proba(te[X])[:,1]
market=pd.read_csv(ODDS)[['match_id','xbetCloseOver25','xbetCloseUnder25','market_over25','market_under25','actual_over25']]; te=te.merge(market,on='match_id',how='inner'); te['p_market']=te.market_over25.astype(float)
# conservative market anchor; fixed before evaluation and never fitted on test outcomes
te['p_final']=.35*te.p_model+.65*te.p_market; te['edge_over']=te.p_final-te.p_market; te['edge_under']=(1-te.p_final)-te.market_under25.astype(float); te['bet']=np.where(te.edge_over>=te.edge_under,'Over','Under'); te['edge']=te[['edge_over','edge_under']].max(axis=1); te['odds']=np.where(te.bet=='Over',te.xbetCloseOver25,te.xbetCloseUnder25); te['profit']=np.where(te.bet==te.actual_over25,te.odds.astype(float)-1,-1); te.to_csv(OUT,index=False)
def metrics(q):
 return {'bets':len(q),'wins':int((q.profit>0).sum()),'profit':round(float(q.profit.sum()),2),'roi':round(float(q.profit.mean()*100),2) if len(q) else None}
report={'model':'direct logistic on strictly pre-match rolling xG; 35% model/65% market blend','training':'2024-25','test':'2025-26','coverage':len(te),'brier_model':round(float(np.mean((te.p_model-te.y)**2)),5),'brier_final':round(float(np.mean((te.p_final-te.y)**2)),5),'brier_market':round(float(np.mean((te.p_market-te.y)**2)),5),'actual_over_rate':round(float(te.y.mean()),5),'edge_bands':{}}
for t in [.05,.10,.15,.20]: report['edge_bands'][str(t)]=metrics(te[te.edge>=t])
REPORT.parent.mkdir(parents=True,exist_ok=True); REPORT.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8'); print(json.dumps(report,indent=2))
