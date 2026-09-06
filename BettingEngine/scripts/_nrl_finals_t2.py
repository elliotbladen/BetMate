#!/usr/bin/env python3
"""T2 style matchup for the 4 NRL finals week 1 games, from fresh Fox Sports
team stats (user-supplied URLs, fetched 2026-09-06). Uses the real
pricing.tier2_matchup family functions + league norms computed the same way as
db.queries.get_style_league_norms."""
from __future__ import annotations
import sys, json, math
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pricing.tier2_matchup import compute_family_a, compute_family_b, compute_family_c, compute_family_d

FOX = Path("C:/Users/INSIGH~1/AppData/Local/Temp/fox/fox_attack.json")
TIERS = yaml.safe_load(open(ROOT / "config" / "tiers.yaml"))
T2CFG = TIERS.get("tier2_matchup", {})

FOX_NAME = {
    'Warriors': 'New Zealand Warriors', 'South Sydney': 'South Sydney Rabbitohs',
    'Cronulla': 'Cronulla-Sutherland Sharks', 'Dolphins': 'Dolphins',
    'Penrith': 'Penrith Panthers', 'Newcastle': 'Newcastle Knights',
    'Manly': 'Manly-Warringah Sea Eagles', 'Sydney Roosters': 'Sydney Roosters',
    'Melbourne': 'Melbourne Storm', 'Canberra': 'Canberra Raiders',
    'North Queensland': 'North Queensland Cowboys', 'Parramatta': 'Parramatta Eels',
    'Gold Coast Titans': 'Gold Coast Titans', 'Canterbury': 'Canterbury-Bankstown Bulldogs',
    'Brisbane': 'Brisbane Broncos', 'Wests Tigers': 'Wests Tigers',
    'St George Illawarra': 'St. George Illawarra Dragons',
}

d = json.load(open(FOX))
teams = d['data']['tableStream']['seriesTeamsStatsApiStream']['teams']
STYLE = {}
for t in teams:
    s = t['stats']; g = s['games'] or 24
    STYLE[FOX_NAME[t['name']]] = {
        'lb_pg': s['lineBreaks'] / g,
        'tb_pg': (s.get('tackleBreaks') or s.get('tackleBusts') or 0) / g,
        'mt_pg': s['missedTackles'] / g,
        'lbc_pg': s['lineBreaksConceded'] / g,
        'completion_rate': s['completionRate'] / 100.0,
        'kick_metres_pg': s['kickMetres'] / g,
        'errors_pg': s['errors'] / g,
        'penalties_pg': s['penaltiesConceded'] / g,
        'run_metres_pg': s['runMetres'] / g,
        'fdo_pg': s['forcedDropOuts'] / g,
        'krm_pg': s['kickReturnMetres'] / g,
    }

# league norms (population std, same as get_style_league_norms)
NORMS = {}
for col in ('lb_pg','tb_pg','mt_pg','lbc_pg','completion_rate','kick_metres_pg',
            'errors_pg','penalties_pg','run_metres_pg','fdo_pg','krm_pg'):
    vals = [v[col] for v in STYLE.values() if v.get(col) is not None]
    avg = sum(vals) / len(vals)
    std = math.sqrt(sum((x - avg) ** 2 for x in vals) / len(vals))
    NORMS[col] = (avg, max(std, 1e-6))

# T1 margins from the assemble step (sign of home lean) for the directional cap
T1_MRG = {'QF1': 7.77, 'QF2': 4.42, 'EF1': 7.49, 'EF2': 4.56}
GAMES = [
    ('QF1', 'Penrith Panthers', 'Sydney Roosters'),
    ('QF2', 'New Zealand Warriors', 'Dolphins'),
    ('EF1', 'Cronulla-Sutherland Sharks', 'North Queensland Cowboys'),
    ('EF2', 'South Sydney Rabbitohs', 'Newcastle Knights'),
]

print(f"{'G':4}{'Matchup':44}{'2A':>7}{'2B':>7}{'2C':>7}{'2D':>7}{'rawH':>7}{'rawA':>7}"
      f"{'T2net':>8}{'T2tot':>7}")
print('-' * 104)
RESULT = {}
for tag, h, a in GAMES:
    hs, as_ = STYLE[h], STYLE[a]
    fa = compute_family_a(hs, as_, NORMS, T2CFG)
    fb = compute_family_b(hs, as_, NORMS, T2CFG)
    fc = compute_family_c(hs, as_, NORMS, T2CFG)
    fd = compute_family_d(hs, as_, NORMS, T2CFG,
                          home_2a_delta=fa['home_delta'], away_2a_delta=fa['away_delta'])
    rawH = fa['home_delta'] + fb['home_delta'] + fc['home_delta'] + fd['home_delta']
    rawA = fa['away_delta'] + fb['away_delta'] + fc['away_delta'] + fd['away_delta']
    rawTot = (fa.get('totals_delta', 0) + fb.get('totals_delta', 0)
              + fc.get('totals_delta', 0) + fd.get('totals_delta', 0))
    totals_T2 = round(max(-3.0, min(3.0, rawTot)), 3)

    cap = float(T2CFG.get('max_home_points_delta', 3.0))
    net_cap = float(T2CFG.get('max_net_handicap_delta', 3.0))
    net_raw = rawH - rawA
    if (T1_MRG[tag] > 0 and net_raw > 0) or (T1_MRG[tag] < 0 and net_raw < 0):
        cap *= 0.5; net_cap *= 0.5
    scale = 1.0
    for x in (rawH, rawA):
        if abs(x) > cap and x != 0:
            scale = min(scale, cap / abs(x))
    if abs(net_raw) > net_cap and net_raw != 0:
        scale = min(scale, net_cap / abs(net_raw))
    t2_net = round((rawH - rawA) * scale, 2)

    print(f"{tag:4}{h.split()[-1]+' v '+a.split()[-1]:44}"
          f"{fa['home_delta']-fa['away_delta']:>7.2f}{fb['home_delta']-fb['away_delta']:>7.2f}"
          f"{fc['home_delta']-fc['away_delta']:>7.2f}{fd['home_delta']-fd['away_delta']:>7.2f}"
          f"{rawH:>7.2f}{rawA:>7.2f}{t2_net:>8.2f}{totals_T2:>7.2f}")
    RESULT[tag] = (t2_net, totals_T2)

print()
print("style snapshot (per game):")
for n in ['Penrith Panthers','Sydney Roosters','New Zealand Warriors','Dolphins',
          'Cronulla-Sutherland Sharks','North Queensland Cowboys',
          'South Sydney Rabbitohs','Newcastle Knights']:
    s = STYLE[n]
    print(f"  {n:30} CR {s['completion_rate']:.2f}  RM {s['run_metres_pg']:.0f}  "
          f"KM {s['kick_metres_pg']:.0f}  err {s['errors_pg']:.1f}  pen {s['penalties_pg']:.1f}  "
          f"MT {s['mt_pg']:.1f}  LB {s['lb_pg']:.1f}  LBC {s['lbc_pg']:.1f}  FDO {s['fdo_pg']:.1f}  KRM {s['krm_pg']:.0f}")
json.dump(RESULT, open(ROOT / 'outputs' / 'results' / '_nrl_finals_t2.json', 'w'))
