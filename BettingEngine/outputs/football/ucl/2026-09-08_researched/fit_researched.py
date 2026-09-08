"""Reproduce the corrected UCL research fit into a new, immutable JSON file.

Usage: .venv/bin/python outputs/football/ucl/2026-09-08_researched/fit_researched.py --output /path/to/new_ratings.json
"""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import pandas as pd
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P.parents[3]))
from ml.football.ucl_shared_engine import load_matches
from ml.football.models.dixon_coles import fit


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists(): raise FileExistsError(args.output)
    aliases=json.loads((P/'aliases.json').read_text())
    cutoff=json.loads((P/'context.json').read_text())['cutoff_utc']
    m=load_matches()
    for c in ['home_team','away_team','home_club_id','away_club_id']:
        m[c]=m[c].replace(aliases)
    m=m[m.Date<pd.Timestamp(cutoff)]
    ratings=fit(m,as_of=pd.Timestamp(cutoff).to_pydatetime(),optimizer_options={'maxfun':500000,'maxiter':2000},preserve_fitted_rates=True)
    if not ratings['converged']: raise RuntimeError(ratings['optimizer_message'])
    ratings['canonical_training_sha256']=hashlib.sha256(m.to_csv(index=False).encode()).hexdigest()
    with args.output.open('x') as f: json.dump(ratings,f,default=str,indent=2)
    print('Converged:',ratings['converged'],'normalization scale:',ratings['normalization_rate_scale'])

if __name__=='__main__':main()
