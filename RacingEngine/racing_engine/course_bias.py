import sqlite3, csv, json, argparse
from datetime import date, timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DEFAULT_DB=ROOT/'data'/'racing_engine.sqlite'
DEFAULT_OUT=ROOT/'reports'/'course_bias'
parser=argparse.ArgumentParser()
parser.add_argument('--database', type=Path, default=DEFAULT_DB)
parser.add_argument('--output-dir', type=Path, default=DEFAULT_OUT)
args=parser.parse_args()
DB=args.database
OUT=args.output_dir
OUT.mkdir(parents=True, exist_ok=True)
tracks=['caulfield','sportsbet-sandown-hillside','sportsbet-sandown-lakeside','flemington','rosehill','randwick']
con=sqlite3.connect(DB)
con.row_factory=sqlite3.Row
max_date=con.execute("select max(race_date) from race_results").fetchone()[0]
cutoff=(date.fromisoformat(max_date)-timedelta(days=365*3)).isoformat()
q='''select rr.source,rr.race_date,rr.track_slug,rr.race_number,rr.distance_metres,rr.track_condition,rr.rail_position,
       r.runner_number,r.barrier,r.finish_position,r.result_status
from race_results rr join runner_results r using(source,race_date,track_slug,race_number)
where rr.race_date>=? and rr.race_date<=? and rr.track_slug in ({}) and r.barrier is not null'''.format(','.join('?'*len(tracks)))
rows=con.execute(q,[cutoff,max_date,*tracks]).fetchall()

def band(d):
    if d<=1400:return 'sprint_upto_1400m'
    if d<=1800:return 'mile_1400_1800m'
    if d<=2400:return 'middle_1800_2400m'
    return 'staying_over_2400m'
def win(pos,status):
    if status and str(status).lower() not in ('finished','') and str(pos).lower() not in ('1','1st'): return False
    s=str(pos).strip().lower().replace('.0','')
    return s in ('1','1st','winner')
def key(row): return (row['track_slug'],band(float(row['distance_metres'] or 0)),int(row['barrier']))
agg={}
for row in rows:
    k=key(row); a=agg.setdefault(k,{'starts':0,'wins':0})
    a['starts']+=1;a['wins']+=win(row['finish_position'],row['result_status'])
for a in agg.values(): a['win_pct']=100*a['wins']/a['starts'] if a['starts'] else None
# Output all cells and summaries
with (OUT/'course_barrier_bias_3y.csv').open('w',newline='') as f:
    w=csv.writer(f);w.writerow(['track','distance_band','barrier','starts','wins','win_pct'])
    for (track,b,bar),a in sorted(agg.items()):w.writerow([track,b,bar,a['starts'],a['wins'],round(a['win_pct'],3)])
summary={}
for track in tracks:
  summary[track]={}
  for b in ['sprint_upto_1400m','mile_1400_1800m','middle_1800_2400m','staying_over_2400m']:
    cells=[(bar,a) for (tr,bb,bar),a in agg.items() if tr==track and bb==b]
    summary[track][b]={'starts':sum(a['starts'] for _,a in cells),'wins':sum(a['wins'] for _,a in cells),'barriers':len(cells),'top_by_win_pct':sorted([{'barrier':bar,**a} for bar,a in cells if a['starts']>=10],key=lambda x:(-x['win_pct'],-x['starts']))[:5]}
report={'date_range':{'from':cutoff,'to':max_date},'tracks':tracks,'rows':len(rows),'summary':summary,'notes':['Win percentages are descriptive only. Cells with low starts require shrinkage and should not be treated as stable bias.','Moonee Valley is intentionally excluded until the rebuilt course has prospective race data and its geometry/rail regimes are verified.']}
(OUT/'course_barrier_bias_3y_summary.json').write_text(json.dumps(report,indent=2))
print(json.dumps({'from':cutoff,'to':max_date,'rows':len(rows),'races':len({(r['source'],r['race_date'],r['track_slug'],r['race_number']) for r in rows})},indent=2))
for tr in tracks:
 print('\n',tr)
 for b,v in summary[tr].items(): print(b,v['starts'],v['wins'],v['top_by_win_pct'])
