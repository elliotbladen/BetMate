#!/usr/bin/env python3
"""Assemble T1-T8 for the 2026 NRL finals week 1 using the real tier functions.
T1 from _nrl_finals_t1 logic; T3/T4/T5/T7 via pricing.tier* ; T6 skipped (refs
unannounced); T8 manual (forecast). ML deliberately excluded per user."""
from __future__ import annotations
import sys, yaml
from pathlib import Path
from collections import defaultdict
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pricing.tier1_baseline import compute_baseline
from pricing.tier3_situational import compute_situational_adjustments
from pricing.tier4_venue import compute_venue_adjustments
from pricing.tier5_injury import compute_injury_adjustments
from pricing.tier7_emotional import compute_emotional_adjustments

XLSX = ROOT.parent / "data" / "nrl" / "historical" / "latest_with_r27.xlsx"
TIERS = yaml.safe_load(open(ROOT / "config" / "tiers.yaml"))

NM = {'Canterbury Bulldogs':'Canterbury-Bankstown Bulldogs','Cronulla Sharks':'Cronulla-Sutherland Sharks',
 'Manly Sea Eagles':'Manly-Warringah Sea Eagles','North QLD Cowboys':'North Queensland Cowboys',
 'St George Dragons':'St. George Illawarra Dragons','Brisbane':'Brisbane Broncos','Canberra':'Canberra Raiders',
 'Gold Coast':'Gold Coast Titans','Melbourne':'Melbourne Storm','Newcastle':'Newcastle Knights',
 'Parramatta':'Parramatta Eels','Penrith':'Penrith Panthers','South Sydney':'South Sydney Rabbitohs',
 'Warriors':'New Zealand Warriors','NZ Warriors':'New Zealand Warriors'}
def canon(n): return NM.get(str(n).strip(), str(n).strip())

ELO = {'Penrith Panthers':1620.8,'New Zealand Warriors':1584.8,'Dolphins':1582.0,'Sydney Roosters':1578.0,
 'Cronulla-Sutherland Sharks':1551.2,'Melbourne Storm':1545.1,'Canberra Raiders':1520.3,
 'South Sydney Rabbitohs':1511.7,'North Queensland Cowboys':1502.7,'Canterbury-Bankstown Bulldogs':1492.9,
 'Newcastle Knights':1483.7,'Manly-Warringah Sea Eagles':1480.1,'Brisbane Broncos':1475.4,
 'Parramatta Eels':1445.8,'Wests Tigers':1387.1,'St. George Illawarra Dragons':1373.9,'Gold Coast Titans':1364.6}
LADDER = {'Penrith Panthers':1,'New Zealand Warriors':2,'Dolphins':3,'Sydney Roosters':4,
 'Cronulla-Sutherland Sharks':5,'South Sydney Rabbitohs':6,'Newcastle Knights':7,'North Queensland Cowboys':8}

df = pd.read_excel(str(XLSX), header=1)
df['Date'] = pd.to_datetime(df['Date'], errors='coerce'); df = df.dropna(subset=['Date'])
df['year'] = df['Date'].dt.year
df['home_score'] = pd.to_numeric(df['Home Score'], errors='coerce')
df['away_score'] = pd.to_numeric(df['Away Score'], errors='coerce')
df = df.dropna(subset=['home_score', 'away_score'])

def season_stats(year):
    sub = df[df['year'] == year].sort_values('Date')
    g = defaultdict(lambda: dict(gp=0,w=0,d=0,pf=0,pa=0,hpf=0,hpa=0,hg=0,apf=0,apa=0,ag=0,hist=[]))
    for _, r in sub.iterrows():
        h, a = canon(r['Home Team']), canon(r['Away Team']); hs, as_ = int(r['home_score']), int(r['away_score'])
        for t, pf, pa, ih in ((h,hs,as_,True),(a,as_,hs,False)):
            d = g[t]; d['gp']+=1; d['pf']+=pf; d['pa']+=pa
            if pf>pa: d['w']+=1
            elif pf==pa: d['d']+=1
            if ih: d['hpf']+=pf; d['hpa']+=pa; d['hg']+=1
            else: d['apf']+=pf; d['apa']+=pa; d['ag']+=1
            d['hist'].append((r['Date'], pf, pa, ih))
    out = {}
    for t, d in g.items():
        gp = d['gp'] or 1
        out[t] = {'games_played':d['gp'],'win_pct':(d['w']+0.5*d['d'])/gp,
            'points_for_avg':d['pf']/gp,'points_against_avg':d['pa']/gp,
            'home_points_for_avg':d['hpf']/(d['hg'] or 1),'home_points_against_avg':d['hpa']/(d['hg'] or 1),
            'away_points_for_avg':d['apf']/(d['ag'] or 1),'away_points_against_avg':d['apa']/(d['ag'] or 1),
            'elo_rating':ELO.get(t),'ladder_position':LADDER.get(t),'recent_form_rating':0.0,
            '_last5':[{'points_for':x[1],'points_against':x[2],'is_home':x[3]}
                      for x in sorted(d['hist'])[-5:]][::-1]}
    return out

def vedge(team, venuekey, yrs=(2024,2025,2026)):
    m = []
    for _, r in df[df['year'].isin(yrs)].iterrows():
        if venuekey.lower() not in str(r['Venue']).lower(): continue
        if canon(r['Home Team']) == team: m.append(r['home_score']-r['away_score'])
        elif canon(r['Away Team']) == team: m.append(r['away_score']-r['home_score'])
    return (sum(m)/len(m), len(m)) if len(m) >= 3 else (0.0, len(m))

s26, s25 = season_stats(2026), season_stats(2025)
t1_cfg = dict(TIERS['tier1_baseline']); t1_cfg['season_quality_num_teams'] = 17

# per-game context: rest days, travel km, venue key, T5 pts, T7 flags, T8 totals delta
GAMES = [
 dict(tag='QF1', home='Penrith Panthers', away='Sydney Roosters', venue='CommBank',
      h_rest=6, a_rest=8, h_travel=0, a_travel=45,
      h_inj=0.8, a_inj=4.25,   # Cogger ban ; Walker(3.5)+Radley(0.75)
      h_flags=[], a_flags=[{'flag_type':'shame_blowout','flag_strength':'normal'}],
      t8_tot=0.0),
 dict(tag='QF2', home='New Zealand Warriors', away='Dolphins', venue='Go Media',
      h_rest=7, a_rest=7, h_travel=0, a_travel=2300,
      h_inj=1.0, a_inj=1.0,    # DWZ out ; Dolphins hamstring niggle
      h_flags=[], a_flags=[],
      t8_tot=-1.0),            # Auckland Sept — wet/windy risk
 dict(tag='EF1', home='Cronulla-Sutherland Sharks', away='North Queensland Cowboys', venue='Allianz',
      h_rest=7, a_rest=7, h_travel=22, a_travel=1700,
      h_inj=0.5, a_inj=1.2,    # Sharks minor ; Laybutt concussion (Dearden BACK = manual +)
      h_flags=[], a_flags=[{'flag_type':'shame_blowout','flag_strength':'normal'}],
      t8_tot=0.0),
 dict(tag='EF2', home='South Sydney Rabbitohs', away='Newcastle Knights', venue='Accor',
      h_rest=7, a_rest=15, h_travel=5, a_travel=120,
      h_inj=0.5, a_inj=3.5,    # Souths ~full ; Knights Crossland(3.0)+Frizell(0.5?) — SHAKY, may be served bans
      h_flags=[{'flag_type':'star_return','flag_strength':'normal'}],  # Latrell back
      a_flags=[],
      t8_tot=0.0),
]

print(f"{'G':4}{'Matchup':46}{'T1':>7}{'T3':>7}{'T4':>7}{'T5':>7}{'T7':>7}{'MARGIN':>9}{'TOTAL':>8}")
print('-'*103)
rows = []
for g in GAMES:
    h, a = s26[g['home']], s26[g['away']]
    t1 = compute_baseline(h, a, {}, t1_cfg, home_last_n_results=h['_last5'], away_last_n_results=a['_last5'],
                          home_prior_stats=s25.get(g['home']), away_prior_stats=s25.get(g['away']))
    t1_mrg, t1_tot = t1['baseline_margin'], t1['baseline_total']

    ctx = {'home_rest_days':g['h_rest'],'away_rest_days':g['a_rest'],
           'home_travel_km':g['h_travel'],'away_travel_km':g['a_travel']}
    t3 = compute_situational_adjustments(ctx, TIERS)
    t3_mrg = t3['home_delta_capped'] - t3['away_delta_capped']; t3_tot = t3.get('totals_delta',0.0)

    he = vedge(g['home'], g['venue']); ae = vedge(g['away'], g['venue'])
    t4 = compute_venue_adjustments(0, 0, 0, he[0], ae[0], 0.0, TIERS['tier4_venue'])
    t4_mrg, t4_tot = t4['handicap_delta'], t4['totals_delta']

    t5 = compute_injury_adjustments(g['h_inj'], g['a_inj'], TIERS['tier5_injury'])
    t5_mrg, t5_tot = t5['handicap_delta'], t5['totals_delta']

    t7 = compute_emotional_adjustments(g['h_flags'], g['a_flags'], TIERS['tier7_emotional'])
    t7_mrg = t7.get('handicap_delta', t7.get('home_delta',0.0) - t7.get('away_delta',0.0))
    t7_tot = t7.get('totals_delta', 0.0)

    margin = t1_mrg + t3_mrg + t4_mrg + t5_mrg + t7_mrg
    total  = t1_tot + t3_tot + t4_tot + t5_tot + t7_tot + g['t8_tot']
    print(f"{g['tag']:4}{g['home'].split()[-1]+' v '+g['away'].split()[-1]:46}"
          f"{t1_mrg:>7.2f}{t3_mrg:>7.2f}{t4_mrg:>7.2f}{t5_mrg:>7.2f}{t7_mrg:>7.2f}{margin:>9.2f}{total:>8.1f}")
    rows.append((g['tag'], g['home'], g['away'], round(margin,1), round(total,1),
                 he, ae, t3['debug'] if 'debug' in t3 else {}))

import math
print()
print("Fair H2H (margin_std=12.0):")
for tag, h, a, m, tot, he, ae, _ in rows:
    p = 1/(1+10**(-(m/12.0*0.4)))   # rough logistic; engine uses norm cdf
    from statistics import NormalDist
    p = NormalDist(0,12.0).cdf(m)
    print(f"  {tag}: {h.split()[-1]} {m:+.1f}  -> {h.split()[-1]} {1/p:.2f} / {a.split()[-1]} {1/(1-p):.2f}   total {tot:.1f}   "
          f"[venue h={he[0]:+.1f}(n{he[1]}) a={ae[0]:+.1f}(n{ae[1]})]")
