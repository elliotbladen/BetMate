import argparse,csv,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--observed',type=Path,required=True);p.add_argument('--priors',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
pri=json.loads(a.priors.read_text()); n0=float(pri['effective_sample_size']); d=pri['tracks']; out=[]
for row in csv.DictReader(a.observed.open()):
    track=row['track']; band=row['distance_band']; bar=row['barrier']; starts=int(row['starts']); wins=int(row['wins']); obs=float(row['win_pct'])
    prior_band=band if band in d.get(track,{}) else 'all'; pv=d.get(track,{}).get(prior_band,{}).get(bar)
    if pv is None:
        blended=obs; weight=0.0
    else:
        blended=(wins + n0*(float(pv)/100.0))/(starts+n0)*100.0; weight=n0/(starts+n0)
    out.append({**row,'visual_prior_pct': '' if pv is None else round(float(pv),3),'visual_prior_effective_n': 0 if pv is None else int(n0),'visual_weight':round(weight,4),'blended_win_pct':round(blended,3)})
a.output.parent.mkdir(parents=True,exist_ok=True)
with a.output.open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=out[0].keys());w.writeheader();w.writerows(out)
print(json.dumps({'rows':len(out),'prior_cells':sum(1 for x in out if x['visual_prior_pct']!=''),'effective_prior_n':n0}))
