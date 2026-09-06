#!/usr/bin/env python3
"""Proper NRL T1 baseline for the 2026 finals week 1, without the DB.

Reconstructs 2026 (through R27) + 2025 season stats from the AusSportsBetting
xlsx, pulls post-R27 ELO from bootstrap_elo_historical, and calls the real
pricing.tier1_baseline.compute_baseline() — the same function prepare_round.py
uses.
"""
from __future__ import annotations
import sys, yaml
from pathlib import Path
from collections import defaultdict
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pricing.tier1_baseline import compute_baseline

XLSX = ROOT.parent / "data" / "nrl" / "historical" / "latest_with_r27.xlsx"

NAME_MAP = {
    'Canterbury Bulldogs': 'Canterbury-Bankstown Bulldogs',
    'Cronulla Sharks': 'Cronulla-Sutherland Sharks',
    'Manly Sea Eagles': 'Manly-Warringah Sea Eagles',
    'North QLD Cowboys': 'North Queensland Cowboys',
    'St George Dragons': 'St. George Illawarra Dragons',
    'Brisbane': 'Brisbane Broncos', 'Canberra': 'Canberra Raiders',
    'Gold Coast': 'Gold Coast Titans', 'Melbourne': 'Melbourne Storm',
    'Newcastle': 'Newcastle Knights', 'Parramatta': 'Parramatta Eels',
    'Penrith': 'Penrith Panthers', 'South Sydney': 'South Sydney Rabbitohs',
    'Warriors': 'New Zealand Warriors', 'NZ Warriors': 'New Zealand Warriors',
}
def canon(n): return NAME_MAP.get(str(n).strip(), str(n).strip())

# Post-R27 2026 ELO from bootstrap_elo_historical.py (train 2009-25, walk 2026)
ELO = {
    'Penrith Panthers': 1620.8, 'New Zealand Warriors': 1584.8, 'Dolphins': 1582.0,
    'Sydney Roosters': 1578.0, 'Cronulla-Sutherland Sharks': 1551.2,
    'Melbourne Storm': 1545.1, 'Canberra Raiders': 1520.3,
    'South Sydney Rabbitohs': 1511.7, 'North Queensland Cowboys': 1502.7,
    'Canterbury-Bankstown Bulldogs': 1492.9, 'Newcastle Knights': 1483.7,
    'Manly-Warringah Sea Eagles': 1480.1, 'Brisbane Broncos': 1475.4,
    'Parramatta Eels': 1445.8, 'Wests Tigers': 1387.1,
    'St. George Illawarra Dragons': 1373.9, 'Gold Coast Titans': 1364.6,
}
LADDER = {  # confirmed 2026 final top 8
    'Penrith Panthers': 1, 'New Zealand Warriors': 2, 'Dolphins': 3,
    'Sydney Roosters': 4, 'Cronulla-Sutherland Sharks': 5,
    'South Sydney Rabbitohs': 6, 'Newcastle Knights': 7,
    'North Queensland Cowboys': 8,
}

def season_stats(df, year):
    sub = df[df['year'] == year].sort_values('Date')
    g = defaultdict(lambda: dict(gp=0, w=0, l=0, d=0, pf=0, pa=0,
                                 hpf=0, hpa=0, hg=0, apf=0, apa=0, ag=0, hist=[]))
    for _, r in sub.iterrows():
        h, a = canon(r['Home Team']), canon(r['Away Team'])
        hs, as_ = int(r['home_score']), int(r['away_score'])
        for t, pf, pa, is_home in ((h, hs, as_, True), (a, as_, hs, False)):
            d = g[t]
            d['gp'] += 1; d['pf'] += pf; d['pa'] += pa
            if pf > pa: d['w'] += 1
            elif pf < pa: d['l'] += 1
            else: d['d'] += 1
            if is_home: d['hpf'] += pf; d['hpa'] += pa; d['hg'] += 1
            else: d['apf'] += pf; d['apa'] += pa; d['ag'] += 1
            d['hist'].append({'date': r['Date'], 'points_for': pf,
                              'points_against': pa, 'is_home': is_home})
    out = {}
    for t, d in g.items():
        gp = d['gp'] or 1
        out[t] = {
            'games_played': d['gp'],
            'win_pct': (d['w'] + 0.5 * d['d']) / gp,
            'points_for_avg': d['pf'] / gp,
            'points_against_avg': d['pa'] / gp,
            'home_points_for_avg': d['hpf'] / (d['hg'] or 1),
            'home_points_against_avg': d['hpa'] / (d['hg'] or 1),
            'away_points_for_avg': d['apf'] / (d['ag'] or 1),
            'away_points_against_avg': d['apa'] / (d['ag'] or 1),
            'elo_rating': ELO.get(t),
            'ladder_position': LADDER.get(t),
            'recent_form_rating': 0.0,
            '_last5': [dict(points_for=x['points_for'],
                            points_against=x['points_against'], is_home=x['is_home'])
                       for x in sorted(d['hist'], key=lambda z: z['date'])[-5:]][::-1],
        }
    return out

df = pd.read_excel(str(XLSX), header=1)
df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
df = df.dropna(subset=['Date'])
df['year'] = df['Date'].dt.year
df['home_score'] = pd.to_numeric(df['Home Score'], errors='coerce')
df['away_score'] = pd.to_numeric(df['Away Score'], errors='coerce')
df = df.dropna(subset=['home_score', 'away_score'])

s26 = season_stats(df, 2026)
s25 = season_stats(df, 2025)
t1_cfg = yaml.safe_load(open(ROOT / 'config' / 'tiers.yaml'))['tier1_baseline']
t1_cfg['season_quality_num_teams'] = 17

GAMES = [
    ('QF1', 'Penrith Panthers', 'Sydney Roosters'),
    ('QF2', 'New Zealand Warriors', 'Dolphins'),
    ('EF1', 'Cronulla-Sutherland Sharks', 'North Queensland Cowboys'),
    ('EF2', 'South Sydney Rabbitohs', 'Newcastle Knights'),
]
print(f"{'Game':5} {'Home':28} {'Away':26} {'T1 home':>8} {'T1 away':>8} {'T1 mrg':>7} {'T1 tot':>7}")
print('-' * 100)
for tag, h, a in GAMES:
    hs, as_ = s26[h], s26[a]
    t1 = compute_baseline(hs, as_, {}, t1_cfg,
                          home_last_n_results=hs['_last5'], away_last_n_results=as_['_last5'],
                          home_prior_stats=s25.get(h), away_prior_stats=s25.get(a))
    print(f"{tag:5} {h:28} {a:26} {t1['baseline_home_points']:8.2f} "
          f"{t1['baseline_away_points']:8.2f} {t1['baseline_margin']:7.2f} {t1['baseline_total']:7.2f}")
    d = t1.get('_debug', {})
    print(f"      ELO {hs['elo_rating']:.0f} v {as_['elo_rating']:.0f} | "
          f"win% {hs['win_pct']:.2f}/{as_['win_pct']:.2f} | "
          f"PF/PA {hs['points_for_avg']:.1f}-{hs['points_against_avg']:.1f} vs "
          f"{as_['points_for_avg']:.1f}-{as_['points_against_avg']:.1f} | "
          f"elo_mrg={d.get('elo_margin')} ratings_mrg={d.get('ratings_margin')} "
          f"HA={d.get('home_advantage_used') or d.get('home_advantage')}")
