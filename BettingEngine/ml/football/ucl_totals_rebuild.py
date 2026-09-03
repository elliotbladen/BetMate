"""Canonical U/O 2.5 rebuild: identical de-vig edge, shrinkage blend and OOS report."""
import csv,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2].parent
PRED={r['match_id']:r for r in csv.DictReader(open(ROOT/'BettingEngine/data/ucl/clv/ucl_totals_calibrated_predictions.csv',encoding='utf-8'))}
def fair(o,u):
 a,b=1/float(o),1/float(u); z=a+b; return a/z,b/z
rows=[]
# 2024/25 BetExplorer raw rows: one bet365 quote per match where available.
raw=list(csv.DictReader(open(ROOT/'BettingEngine/data/ucl/markets/ucl_betexplorer_totals_2024_25.csv',encoding='utf-8')))
bt={}
for r in raw:
 if not r.get('error'): bt.setdefault(r['event_id'],[]).append(r)
old=list(csv.DictReader(open(ROOT/'BettingEngine/data/ucl/markets/ucl_betexplorer_totals_backtest_2024_25.csv',encoding='utf-8')))
for r in old:
 eid=r['path'].rstrip('/').split('/')[-1]; rs=bt.get(eid,[])
 if not rs: continue
 q=next((x for x in rs if x['bookmaker']=='bet365'),rs[0]); p=PRED.get(r['match_id']);
 if not p: continue
 po=float(p.get('p_over25_calibrated') or p['p_over25']); o,u=float(q['over25']),float(q['under25']); mo,mu=fair(o,u)
 # 50% market shrinkage reduces overconfident tails; fixed before evaluation.
 pb=.5*po+.5*mo; bet='Over' if pb-mo >= (1-pb)-mu else 'Under'; edge=max(pb-mo,(1-pb)-mu); actual=r['actual']; win=bet==actual; odds=o if bet=='Over' else u
 rows.append({'season':'2024-25','match_id':r['match_id'],'p_model':po,'market_prob':mo,'p_blend':pb,'bet':bet,'edge':edge,'odds':odds,'actual':actual,'profit':odds-1 if win else -1})
# 2025/26 existing Footiqo file already has canonical de-vig market probability.
for r in csv.DictReader(open(ROOT/'BettingEngine/data/ucl/markets/ucl_footiqo_totals_backtest_2025_26.csv',encoding='utf-8')):
 po=float(r['model_over25']); mo=float(r['market_over25']); pb=.5*po+.5*mo; bet='Over' if pb-mo >= (1-pb)-float(r['market_under25']) else 'Under'; edge=max(pb-mo,(1-pb)-float(r['market_under25'])); odds=float(r['xbetCloseOver25'] if bet=='Over' else r['xbetCloseUnder25']); actual=r['actual_over25']; rows.append({'season':'2025-26','match_id':r['match_id'],'p_model':po,'market_prob':mo,'p_blend':pb,'bet':bet,'edge':edge,'odds':odds,'actual':actual,'profit':odds-1 if bet==actual else -1})
out=ROOT/'BettingEngine/data/ucl/markets/ucl_totals_rebuilt_two_season.csv'; out.parent.mkdir(parents=True,exist_ok=True)
with out.open('w',newline='',encoding='utf-8') as f:
 w=csv.DictWriter(f,fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
report={'method':'canonical de-vig probability edge; 50% fixed market shrinkage; bookmaker archives are static/unverified','coverage':{},'results':{}}
for s in ['2024-25','2025-26','combined']:
 x=rows if s=='combined' else [r for r in rows if r['season']==s]; report['coverage'][s]=len(x); report['results'][s]={}
 for t in [.10,.20,.30,.40,.50]:
  q=[r for r in x if float(r['edge'])>=t]; pr=sum(float(r['profit']) for r in q); report['results'][s][str(int(t*100))]={'bets':len(q),'wins':sum(float(r['profit'])>0 for r in q),'profit':round(pr,2),'roi':round(100*pr/len(q),2) if q else None}
(ROOT/'BettingEngine/ml/football/reports/ucl_totals_rebuilt_backtest.json').write_text(json.dumps(report,indent=2),encoding='utf-8'); print(json.dumps(report,indent=2))
