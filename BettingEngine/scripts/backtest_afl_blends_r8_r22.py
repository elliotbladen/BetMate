#!/usr/bin/env python3
"""Rules-heavy AFL blends versus closing H2H and handicap, R8-R22 only."""

import re
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, log_loss

ROOT = Path(__file__).resolve().parents[1]
HISTORY = ROOT/'outputs'/'backtests'/'afl_features_2009_2026.csv'
OUT = ROOT/'outputs'/'backtests'/'afl_blends_r8_r22'

NICK = {
    'Magpies':'Collingwood Magpies', 'Hawks':'Hawthorn Hawks',
    'Bulldogs':'Western Bulldogs', 'Dockers':'Fremantle Dockers',
    'Crows':'Adelaide Crows', 'Power':'Port Adelaide Power',
    'Bombers':'Essendon Bombers', 'Lions':'Brisbane Lions',
    'Eagles':'West Coast Eagles', 'Tigers':'Richmond Tigers',
    'Cats':'Geelong Cats', 'Kangaroos':'North Melbourne Kangaroos',
    'Blues':'Carlton Blues', 'Saints':'St Kilda Saints',
    'Swans':'Sydney Swans', 'Demons':'Melbourne Demons',
    'Suns':'Gold Coast Suns', 'Giants':'Greater Western Sydney Giants',
}


def parse_shadow_text(path, round_num):
    text = Path(path).read_text()
    block = text.split('AFL R%d 2026 — ML Shadow Mode' % round_num, 1)[1]
    block = block.split('DIVERGENCE SUMMARY', 1)[0]
    rows = []
    pattern = re.compile(
        r'^\s*(\w+) vs (\w+)\s+([+-]\d+\.\d)\s+([+-]\d+\.\d)\s+'
        r'[+-]\d+\.\d\s+\d+\.\d\s+\d+\.\d\s+[+-]\d+\.\d\s+'
        r'(\d+\.\d)%\s+(\d+\.\d)%', re.M)
    for home, away, rules_m, ml_m, rules_p, ml_p in pattern.findall(block):
        rows.append({'round_number':round_num, 'home_team':NICK[home], 'away_team':NICK[away],
                     'rules_margin':float(rules_m), 'ml_margin':float(ml_m),
                     'rules_home_prob':float(rules_p)/100, 'ml_h2h':float(ml_p)/100})
    if len(rows) != 9:
        raise ValueError(f'Expected 9 parsed games in {path}, got {len(rows)}')
    return pd.DataFrame(rows)


def load_predictions():
    r8 = parse_shadow_text(ROOT/'results'/'afl'/'r8_afl_2026.txt', 8)
    r8_dates = pd.read_csv(ROOT/'outputs'/'afl_weekly_review'/'reports'/'r8_afl_ml_clv_comparison_2026.csv')[
        ['home_team','away_team','date']].drop_duplicates()
    r8 = r8.merge(r8_dates, on=['home_team','away_team'], how='left').rename(columns={'date':'game_date'})
    r10 = parse_shadow_text(ROOT/'outputs'/'afl_round_prep'/'r10_2026'/'afl_r10_pricing_2026.txt', 10)
    r10_dates = pd.read_csv(ROOT/'outputs'/'afl_round_prep'/'r10_2026'/'fixture_r10_2026.csv')[
        ['home_team','away_team','date']]
    r10 = r10.merge(r10_dates, on=['home_team','away_team'], how='left').rename(columns={'date':'game_date'})
    frames = [
        r8,
        pd.read_csv(ROOT/'outputs'/'afl_round_prep'/'r9_2026'/'afl_r9_pricing_2026.csv')
          .rename(columns={'round':'round_number', 'fair_margin_home':'rules_margin',
                           'ml_margin_home':'ml_margin', 'ml_home_prob':'ml_h2h',
                           'date':'game_date'})[
              ['round_number','home_team','away_team','rules_margin','ml_margin',
               'rules_home_prob','ml_h2h','game_date']],
        r10,
    ]
    for r in list(range(11, 20)) + [21, 22]:
        path = ROOT/'results'/f'r{r}_afl_2026.csv'
        if path.exists():
            d = pd.read_csv(path)
            frames.append(d[['round_number','home_team','away_team','rules_margin','ml_margin',
                             'rules_home_prob','ml_h2h','game_date']])
    out = pd.concat(frames, ignore_index=True)
    for c in ['round_number','rules_margin','ml_margin','rules_home_prob','ml_h2h']:
        out[c] = pd.to_numeric(out[c], errors='coerce')
    return out[out.round_number.between(8,22)]


def join_results(pred):
    h = pd.read_csv(HISTORY, low_memory=False)
    h = h[h.season.eq(2026)][['home_team','away_team','date','home_win','home_margin',
                              'mkt_home_prob_open','h2h_home_close','h2h_away_close',
                              'home_line_close']]
    pred=pred.copy(); pred['game_date']=pd.to_datetime(pred.game_date)
    h['date']=pd.to_datetime(h.date)
    candidates=pred.reset_index(names='prediction_id').merge(
        h,on=['home_team','away_team'],how='left')
    candidates['date_gap']=(candidates.game_date-candidates.date).abs().dt.days
    matched=(candidates[candidates.date_gap.le(2)].sort_values(['prediction_id','date_gap'])
             .drop_duplicates('prediction_id'))
    return pred.merge(matched.drop(columns=pred.columns,errors='ignore'),
                      left_index=True,right_on='prediction_id',how='left').drop(columns='prediction_id')


def h2h_test(d, weights, thresholds=(.05,.07,.10)):
    rows=[]
    for w in weights:
        p = w*d.rules_home_prob+(1-w)*d.ml_h2h
        settled=d.home_win.notna() & d.h2h_home_close.notna() & d.h2h_away_close.notna()
        z=d[settled].copy(); z['p']=p[settled]
        base={'rules_weight':w,'games':len(z),'brier':brier_score_loss(z.home_win,z.p),
              'log_loss':log_loss(z.home_win,np.clip(z.p,.001,.999),labels=[0,1])}
        for t in thresholds:
            profits=[]
            for _,r in z.iterrows():
                ih,ia=1/r.h2h_home_close,1/r.h2h_away_close; mh=ih/(ih+ia)
                home=(r.p-mh)>=((1-r.p)-(1-mh)); edge=abs(r.p-mh)
                if edge<t: continue
                won=bool(r.home_win) if home else not bool(r.home_win)
                odds=r.h2h_home_close if home else r.h2h_away_close
                profits.append(odds-1 if won else -1)
            rows.append(base|{'threshold':t,'bets':len(profits),'profit':sum(profits),
                              'roi':np.mean(profits) if profits else np.nan})
    return pd.DataFrame(rows)


def handicap_test(d, weights, thresholds=(0,3,6,10)):
    rows=[]
    for w in weights:
        margin=w*d.rules_margin+(1-w)*d.ml_margin
        settled=d.home_margin.notna() & d.home_line_close.notna()
        z=d[settled].copy(); z['model_margin']=margin[settled]
        z['edge_home']=z.model_margin+z.home_line_close
        for t in thresholds:
            q=z[z.edge_home.abs()>=t]
            profits=[]; clv_edges=[]; pushes=0
            for _,r in q.iterrows():
                home=r.edge_home>0
                result=r.home_margin+r.home_line_close
                covered=result>0 if home else result<0
                push=result==0
                pushes+=int(push); profits.append(0 if push else (.90 if covered else -1))
                clv_edges.append(abs(r.edge_home))
            rows.append({'rules_weight':w,'threshold_points':t,'bets':len(q),
                         'avg_model_edge_to_close':np.mean(clv_edges) if clv_edges else np.nan,
                         'wins':sum(x>.0 for x in profits),'losses':sum(x<0 for x in profits),
                         'pushes':pushes,'profit_at_1_90':sum(profits),
                         'roi_at_1_90':np.mean(profits) if profits else np.nan})
    return pd.DataFrame(rows)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    d=join_results(load_predictions())
    weights=[0,.25,.5,.6,.7,.75,.8,.9,1]
    h=h2h_test(d,weights); a=handicap_test(d,weights)
    d.to_csv(OUT/'games.csv',index=False); h.to_csv(OUT/'h2h.csv',index=False); a.to_csv(OUT/'handicap.csv',index=False)
    # Frozen prospective specification requested after the exploratory sweep.
    fixed=d.copy()
    fixed['combined_h2h_home_prob']=.60*fixed.rules_home_prob+.40*fixed.ml_h2h
    fixed['combined_h2h_home_odds']=1/fixed.combined_h2h_home_prob
    fixed['combined_h2h_away_odds']=1/(1-fixed.combined_h2h_home_prob)
    ih=1/fixed.h2h_home_close; ia=1/fixed.h2h_away_close
    fixed['closing_no_vig_home_prob']=ih/(ih+ia)
    fixed['h2h_home_edge']=fixed.combined_h2h_home_prob-fixed.closing_no_vig_home_prob
    fixed['h2h_selection']=np.where(fixed.h2h_home_edge>=0,fixed.home_team,fixed.away_team)
    fixed['h2h_edge']=fixed.h2h_home_edge.abs()
    fixed['h2h_qualifies_7pp']=fixed.h2h_edge.ge(.07)
    fixed['h2h_odds']=np.where(fixed.h2h_home_edge>=0,fixed.h2h_home_close,fixed.h2h_away_close)
    fixed['h2h_won']=np.where(fixed.h2h_home_edge>=0,fixed.home_win.eq(1),fixed.home_win.eq(0))
    fixed['h2h_profit']=np.where(~fixed.h2h_qualifies_7pp,np.nan,
        np.where(fixed.h2h_won,fixed.h2h_odds-1,-1))
    fixed['combined_margin']=.25*fixed.rules_margin+.75*fixed.ml_margin
    fixed['handicap_edge_home']=fixed.combined_margin+fixed.home_line_close
    fixed['handicap_selection']=np.where(fixed.handicap_edge_home>=0,fixed.home_team,fixed.away_team)
    fixed['handicap_edge']=fixed.handicap_edge_home.abs()
    fixed['handicap_qualifies_6pt']=fixed.handicap_edge.ge(6)
    cover=fixed.home_margin+fixed.home_line_close
    fixed['handicap_won']=np.where(fixed.handicap_edge_home>=0,cover.gt(0),cover.lt(0))
    fixed['handicap_push']=cover.eq(0)
    fixed['handicap_profit_at_1_90']=np.where(~fixed.handicap_qualifies_6pt,np.nan,
        np.where(fixed.handicap_push,0,np.where(fixed.handicap_won,.90,-1)))
    fixed.to_csv(OUT/'fixed_combined_game_results.csv',index=False)

    settled=fixed[fixed.home_win.notna()].copy()
    hb=settled[settled.h2h_qualifies_7pp]
    ab=settled[settled.handicap_qualifies_6pt]
    summary=pd.DataFrame([
        {'market':'H2H','rules_weight':.60,'ml_weight':.40,'trigger':'7 probability points',
         'settled_games':len(settled),'bets':len(hb),'wins':int(hb.h2h_won.sum()),
         'losses':int((~hb.h2h_won).sum()),'pushes':0,'profit':hb.h2h_profit.sum(),
         'roi':hb.h2h_profit.mean()},
        {'market':'Handicap','rules_weight':.25,'ml_weight':.75,'trigger':'6 line points',
         'settled_games':len(settled),'bets':len(ab),'wins':int(ab.handicap_won.sum()),
         'losses':int((~ab.handicap_won & ~ab.handicap_push).sum()),
         'pushes':int(ab.handicap_push.sum()),'profit':ab.handicap_profit_at_1_90.sum(),
         'roi':ab.handicap_profit_at_1_90.mean()},
    ])
    summary.to_csv(OUT/'fixed_combined_summary.csv',index=False)
    print(f'Archived predictions: {len(d)} games, rounds {sorted(d.round_number.unique())}')
    print(f'Settled with close: H2H {int((d.home_win.notna()&d.h2h_home_close.notna()).sum())}, '
          f'handicap {int((d.home_margin.notna()&d.home_line_close.notna()).sum())}')
    print('\nH2H, 7pp edge to closing market')
    print(h[h.threshold.eq(.07)].sort_values('roi',ascending=False).to_string(index=False,float_format=lambda x:f'{x:.4f}'))
    print('\nHandicap, 6pt edge to closing line ($1.90 settlement)')
    print(a[a.threshold_points.eq(6)].sort_values('roi_at_1_90',ascending=False).to_string(index=False,float_format=lambda x:f'{x:.4f}'))
    print('\nFrozen combined-model specification')
    print(summary.to_string(index=False,float_format=lambda x:f'{x:.4f}'))


if __name__=='__main__': main()
