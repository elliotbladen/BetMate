"""Build the EPL/EFL-style combined UCL 1X2 + O/U2.5 pricing matrix."""
from pathlib import Path
import numpy as np, pandas as pd
ROOT=Path(__file__).resolve().parents[2]
pred=pd.read_csv(ROOT/'data/ucl/clv/ucl_shared_walk_forward_predictions.csv'); pred=pred[pred.season.astype(str).isin(['2024-25','2025-26'])].copy()
markets=[]
for s,fn in [('2024-25','ucl_betexplorer_backtest_2024_25_date_safe.csv'),('2025-26','ucl_footiqo_backtest_2025_26_date_safe.csv')]:
 m=pd.read_csv(ROOT/'data/ucl/markets'/fn); m['season']=s; markets.append(m)
m=pd.concat(markets,ignore_index=True)
cols=['match_id','home_odds','draw_odds','away_odds','xbetClose1FT','xbetCloseXFT','xbetClose2FT']
for c in cols:
 if c not in m: m[c]=np.nan
j=pred.merge(m[cols],on='match_id',how='left')
def pick(r,a,b): return r[a] if pd.notna(r[a]) else r[b]
j['market_home_odds']=j.apply(lambda r:pick(r,'home_odds','xbetClose1FT'),axis=1); j['market_draw_odds']=j.apply(lambda r:pick(r,'draw_odds','xbetCloseXFT'),axis=1); j['market_away_odds']=j.apply(lambda r:pick(r,'away_odds','xbetClose2FT'),axis=1)
for c in ['market_home_odds','market_draw_odds','market_away_odds']: j[c]=pd.to_numeric(j[c],errors='coerce')
q=1/j[['market_home_odds','market_draw_odds','market_away_odds']]; q=q.div(q.sum(axis=1),axis=0); j['market_home_prob']=q.iloc[:,0]; j['market_draw_prob']=q.iloc[:,1]; j['market_away_prob']=q.iloc[:,2]
j['fair_home_odds']=1/j.p_home; j['fair_draw_odds']=1/j.p_draw; j['fair_away_odds']=1/j.p_away; j['edge_home']=j.p_home-j.market_home_prob; j['edge_draw']=j.p_draw-j.market_draw_prob; j['edge_away']=j.p_away-j.market_away_prob
j['one_x_two_selection']=np.array(['Home','Draw','Away'])[j[['edge_home','edge_draw','edge_away']].fillna(-999).to_numpy().argmax(axis=1)]; j['one_x_two_edge']=j[['edge_home','edge_draw','edge_away']].max(axis=1)
t=pd.read_csv(ROOT/'data/ucl/markets/ucl_totals_rebuilt_two_season.csv').drop_duplicates('match_id'); t=t[['match_id','p_model','market_prob','p_blend','bet','edge','odds','actual']].rename(columns={'p_model':'ou_model_over_prob','market_prob':'ou_market_over_prob','p_blend':'ou_final_over_prob','bet':'ou_selection','edge':'ou_edge','odds':'ou_selected_odds','actual':'ou_actual'})
j=j.merge(t,on='match_id',how='left'); j['ou_model_under_prob']=1-j.ou_model_over_prob; j['ou_market_under_prob']=1-j.ou_market_over_prob; j['ou_final_under_prob']=1-j.ou_final_over_prob; j['ou_fair_over_odds']=1/j.ou_final_over_prob; j['ou_fair_under_odds']=1/j.ou_final_under_prob
j['ou_model_over_prob']=j.ou_model_over_prob.fillna(j.get('p_over25_calibrated',j.p_over25)); j['ou_model_under_prob']=1-j.ou_model_over_prob
j['corner_data_available']=j.match_id.isin(set(pd.read_csv(ROOT/'data/ucl/xg/ucl_sofascore_match_stats.csv').match_id)); j['player_shadow_status']='shadow_pending'; j['data_quality']=np.where(j.corner_data_available,'xg+corners','xg_only'); j['best_market']=np.where(j.one_x_two_edge.fillna(-999)>=j.ou_edge.fillna(-999),'1X2','OU2.5'); j['promotion_status']='paper_only'
out=ROOT/'data/ucl/markets/ucl_combined_1x2_ou25_matrix.csv'; out.parent.mkdir(parents=True,exist_ok=True); j.to_csv(out,index=False)
print({'rows':len(j),'one_x_two_market_rows':int(j.market_home_prob.notna().sum()),'ou_rows':int(j.ou_model_over_prob.notna().sum()),'corner_rows':int(j.corner_data_available.sum()),'output':str(out)})
