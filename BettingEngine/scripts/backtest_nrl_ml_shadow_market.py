#!/usr/bin/env python3
"""Grade NRL walk-forward shadow predictions against recorded closing markets."""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
ALIASES={
    'Brisbane Broncos':'Brisbane Broncos','Canberra Raiders':'Canberra Raiders',
    'Canterbury Bulldogs':'Canterbury-Bankstown Bulldogs',
    'Cronulla Sharks':'Cronulla-Sutherland Sharks','Dolphins':'Dolphins',
    'Gold Coast Titans':'Gold Coast Titans','Manly Sea Eagles':'Manly-Warringah Sea Eagles',
    'Melbourne Storm':'Melbourne Storm','New Zealand Warriors':'New Zealand Warriors',
    'Newcastle Knights':'Newcastle Knights','North QLD Cowboys':'North Queensland Cowboys',
    'Parramatta Eels':'Parramatta Eels','Penrith Panthers':'Penrith Panthers',
    'South Sydney Rabbitohs':'South Sydney Rabbitohs',
    'St George Dragons':'St. George Illawarra Dragons','Sydney Roosters':'Sydney Roosters',
    'Wests Tigers':'Wests Tigers',
}


def market(path):
    d=pd.read_excel(path,sheet_name='Data',header=1)
    d=d.rename(columns={'Date':'date','Home Team':'home_team','Away Team':'away_team',
        'Home Odds Close':'home_close','Away Odds Close':'away_close',
        'Home Line Close':'home_line_close','Home Line Odds Close':'home_line_odds',
        'Away Line Odds Close':'away_line_odds'})
    d['date']=pd.to_datetime(d.date).dt.date.astype(str)
    d['home_team']=d.home_team.map(lambda x:ALIASES.get(str(x),str(x)))
    d['away_team']=d.away_team.map(lambda x:ALIASES.get(str(x),str(x)))
    cols=['date','home_team','away_team','home_close','away_close','home_line_close',
          'home_line_odds','away_line_odds']
    for c in cols[3:]:d[c]=pd.to_numeric(d[c],errors='coerce')
    return d[cols]


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--predictions',type=Path,default=ROOT/'ml/nrl/results/walk_forward_predictions.csv')
    ap.add_argument('--xlsx',type=Path,default=ROOT/'outputs/nrl_weekly_review/historical/latest.xlsx')
    ap.add_argument('--out-dir',type=Path,default=ROOT/'ml/nrl/results/market_backtest')
    args=ap.parse_args();args.out_dir.mkdir(parents=True,exist_ok=True)
    p=pd.read_csv(args.predictions);p['date']=pd.to_datetime(p.date).dt.date.astype(str)
    d=p.merge(market(args.xlsx),on=['date','home_team','away_team'],how='left',validate='one_to_one')
    rows=[]; bets=[]
    for threshold in (.03,.05,.07,.10):
        h=[]
        for _,r in d.dropna(subset=['home_close','away_close']).iterrows():
            ih,ia=1/r.home_close,1/r.away_close;mh=ih/(ih+ia)
            home=(r.ml_home_prob-mh)>=0;edge=abs(r.ml_home_prob-mh)
            if edge<threshold:continue
            odds=r.home_close if home else r.away_close
            won=bool(r.home_win) if home else not bool(r.home_win)
            profit=odds-1 if won else -1;h.append(profit)
            bets.append({'market':'h2h','threshold':threshold,'date':r.date,
                'home_team':r.home_team,'away_team':r.away_team,
                'selection':r.home_team if home else r.away_team,'edge':edge,
                'odds':odds,'won':won,'profit':profit})
        rows.append({'market':'h2h','threshold':threshold,'bets':len(h),
                     'profit':sum(h),'roi':np.mean(h) if h else np.nan})
    for points in (0,3,6,10):
        a=[]
        for _,r in d.dropna(subset=['home_line_close','home_line_odds','away_line_odds']).iterrows():
            edge=r.ml_margin+r.home_line_close
            if abs(edge)<points:continue
            home=edge>=0;cover=r.actual_margin+r.home_line_close
            push=cover==0;won=cover>0 if home else cover<0
            odds=r.home_line_odds if home else r.away_line_odds
            profit=0 if push else (odds-1 if won else -1);a.append(profit)
            bets.append({'market':'handicap','threshold':points,'date':r.date,
                'home_team':r.home_team,'away_team':r.away_team,
                'selection':r.home_team if home else r.away_team,'edge':abs(edge),
                'odds':odds,'won':won,'profit':profit})
        rows.append({'market':'handicap','threshold':points,'bets':len(a),
                     'profit':sum(a),'roi':np.mean(a) if a else np.nan})
    summary=pd.DataFrame(rows);summary.to_csv(args.out_dir/'summary.csv',index=False)
    pd.DataFrame(bets).to_csv(args.out_dir/'bets.csv',index=False);d.to_csv(args.out_dir/'games.csv',index=False)
    print(f'Market matches: H2H {d.home_close.notna().sum()}/{len(d)}, handicap {d.home_line_close.notna().sum()}/{len(d)}')
    print(summary.to_string(index=False,float_format=lambda x:f'{x:.4f}'))


if __name__=='__main__':main()
