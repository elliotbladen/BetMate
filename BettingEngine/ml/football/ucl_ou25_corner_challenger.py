"""Corner-enhanced UCL O/U2.5 challenger with strict pre-match feature timing."""
from pathlib import Path
import json, numpy as np, pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
ROOT=Path(__file__).resolve().parents[2]
M=ROOT/'data/ucl/matches/ucl_recent_complete_xg_v2.csv'; S=ROOT/'data/ucl/xg/ucl_sofascore_match_stats.csv'; O=ROOT/'data/ucl/markets/ucl_footiqo_totals_backtest_2025_26.csv'
OUT=ROOT/'data/ucl/markets/ucl_ou25_corner_challenger_2025_26.csv'; REP=ROOT/'ml/football/reports/ucl_ou25_corner_challenger_backtest.json'
d=pd.read_csv(M).merge(pd.read_csv(S)[['match_id','cornerKicks_home','cornerKicks_away']],on='match_id',how='inner').merge(pd.read_csv(ROOT/'data/ucl/clv/ucl_totals_calibrated_predictions.csv')[['match_id','stage']],on='match_id',how='left'); d['kick']=pd.to_datetime(d.kickoff_utc,utc=True); d=d.sort_values('kick').reset_index(drop=True)
hist={}; rows=[]
for _,r in d.iterrows():
 h=hist.get(r.home_club_id,[]); a=hist.get(r.away_club_id,[])
 def av(x,i,z): return float(np.mean([v[i] for v in x[-5:]])) if x else z
 # prior-only xG and corners; no current-match statistics enter features
 rows.append({'match_id':r.match_id,'season':r.season,'stage':r.stage,'y':int(r.home_goals+r.away_goals>2.5),'total_xg':(av(h,0,1.55)+av(h,1,1.55)+av(a,0,1.55)+av(a,1,1.55))/2,'home_att':av(h,0,1.55),'away_att':av(a,0,1.55),'home_corners_for':av(h,2,5.0),'home_corners_against':av(h,3,5.0),'away_corners_for':av(a,2,5.0),'away_corners_against':av(a,3,5.0),'knockout':int(any(k in str(r.stage).lower() for k in ['knock','play','final']))})
 if pd.notna(r.cornerKicks_home) and pd.notna(r.cornerKicks_away):
  hist.setdefault(r.home_club_id,[]).append((float(r.home_xg),float(r.away_xg),float(r.cornerKicks_home),float(r.cornerKicks_away))); hist.setdefault(r.away_club_id,[]).append((float(r.away_xg),float(r.home_xg),float(r.cornerKicks_away),float(r.cornerKicks_home)))
f=pd.DataFrame(rows); tr=f[f.season=='2024-25']; te=f[f.season=='2025-26'].copy(); X=['total_xg','home_att','away_att','home_corners_for','home_corners_against','away_corners_for','away_corners_against','knockout']; mdl=make_pipeline(StandardScaler(),LogisticRegression(C=.5,max_iter=2000)); mdl.fit(tr[X],tr.y); te['p_model']=mdl.predict_proba(te[X])[:,1]
market=pd.read_csv(O)[['match_id','xbetCloseOver25','xbetCloseUnder25','market_over25','market_under25','actual_over25']]; te=te.merge(market,on='match_id',how='inner'); te['p_market']=te.market_over25.astype(float); te['p_final']=.35*te.p_model+.65*te.p_market; te['edge_over']=te.p_final-te.p_market; te['edge_under']=(1-te.p_final)-te.market_under25.astype(float); te['bet']=np.where(te.edge_over>=te.edge_under,'Over','Under'); te['edge']=te[['edge_over','edge_under']].max(axis=1); te['odds']=np.where(te.bet=='Over',te.xbetCloseOver25,te.xbetCloseUnder25).astype(float); te['profit']=np.where(te.bet==te.actual_over25,te.odds-1,-1); te.to_csv(OUT,index=False)
def met(q):
 p=float(q.profit.sum()); return {'bets':len(q),'wins':int((q.profit>0).sum()),'profit':round(p,2),'roi':round(100*p/len(q),2) if len(q) else None}
rep={'model':'pre-match rolling xG + rolling corners; 35% model/65% market blend','train_matches':len(tr),'test_matches':len(te),'brier_model':round(float(np.mean((te.p_model-te.y)**2)),5),'brier_final':round(float(np.mean((te.p_final-te.y)**2)),5),'brier_market':round(float(np.mean((te.p_market-te.y)**2)),5),'edge_bands':{str(t):met(te[te.edge>=t]) for t in [.05,.10,.15]}}
REP.parent.mkdir(parents=True,exist_ok=True); REP.write_text(json.dumps(rep,indent=2)+'\n',encoding='utf-8'); print(json.dumps(rep,indent=2))
