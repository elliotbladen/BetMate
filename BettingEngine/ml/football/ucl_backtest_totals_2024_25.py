import csv, re, unicodedata, json
from pathlib import Path
from difflib import SequenceMatcher
ROOT=Path(__file__).resolve().parents[2].parent
pred=ROOT/'BettingEngine/data/ucl/clv/ucl_totals_calibrated_predictions.csv'
odds=ROOT/'BettingEngine/data/ucl/markets/ucl_betexplorer_totals_2024_25.csv'
def norm(s):
 s=re.sub(r'\s*\([^)]*\)','',s)
 s=unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().lower()
 s=re.sub(r'\b(fc|cf|afc|fk|sc|ac|club|kv|sk|calcio)\b','',s)
 s=re.sub(r'[^a-z0-9]','',s)
 aliases={'athleticbilbao':'athleticclub','atleticomadrid':'atlmadrid','parissaintgermain':'psg','psge':'psg','intermilan':'inter','internazionale':'inter','fcinternazionale':'inter','sportinglisbon':'sportingcp','sportingcp':'sportingcp','redbullsalzburg':'salzburg','bayerleverkusen':'leverkusen','shakhtardonetsk':'shakhtard','shakhtard':'shakhtar','dinamozagreb':'dinamozagreb','clubbrugge':'clubbrugge','astonvilla':'astonvilla'}
 return aliases.get(s,s)
P=list(csv.DictReader(open(pred,encoding='utf-8')))
O=list(csv.DictReader(open(odds,encoding='utf-8')))
groups={}
for r in O:
 if r.get('error'): continue
 groups.setdefault(r['path'],[]).append(r)
out=[]; unmatched=[]
for path,rs in groups.items():
 parts=path.rstrip('/').split('/')[-2].split('-')
 # use full slug path components by splitting only around final slash
 slug=path.rstrip('/').split('/')[-2]
 # compare joined model names to path slug (team names themselves contain hyphens)
 best=None; bs=0
 for p in P:
  if p['season']!='2024-25': continue
  a=norm(p['home_name_source']); b=norm(p['away_name_source']); target=slug.replace('-','')
  score=SequenceMatcher(None,a+ b,target).ratio()
  # one-sided containment helps abbreviations
  if a in target: score+=.25
  if b in target: score+=.25
  if score>bs: bs,best=score,p
 if not best or bs<.45: unmatched.append((path,bs)); continue
 # prefer bet365; otherwise median available archive snapshot
 r=next((x for x in rs if x['bookmaker']=='bet365'),rs[len(rs)//2])
 try: over=float(r['over25']); under=float(r['under25'])
 except: continue
 po=float(best.get('p_over25_calibrated') or best['p_over25']); pu=1-po
 bet='Over' if po*over-1 >= pu*under-1 else 'Under'
 edge=max(po*over-1,pu*under-1)
 actual=best['actual_over25']=='1'
 win=(actual if bet=='Over' else not actual)
 profit=(over-1 if bet=='Over' else under-1) if win else -1
 out.append({'match_id':best['match_id'],'home':best['home_name_source'],'away':best['away_name_source'],'bet':bet,'edge':edge,'odds':over if bet=='Over' else under,'actual':'Over' if actual else 'Under','win':win,'profit':profit,'bookmaker':r['bookmaker'],'path':path})
report={}
for threshold in [0.10,0.20,0.30]:
 q=[x for x in out if x['edge']>=threshold]; st=sum(x['profit'] for x in q)
 report[str(threshold)]={'bets':len(q),'wins':sum(x['win'] for x in q),'profit':round(st,2),'roi':round(st/len(q),4) if q else None}
report['coverage']={'matched':len(out),'unmatched':len(unmatched),'available_market_rows':len(groups)}
csvout=ROOT/'BettingEngine/data/ucl/markets/ucl_betexplorer_totals_backtest_2024_25.csv'
with csvout.open('w',newline='',encoding='utf-8') as f:
 w=csv.DictWriter(f,fieldnames=out[0].keys()); w.writeheader(); w.writerows(out)
(ROOT/'BettingEngine/ml/football/reports/ucl_2024_25_totals_backtest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2)); print('unmatched sample',unmatched[:8])
