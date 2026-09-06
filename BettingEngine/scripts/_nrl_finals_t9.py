#!/usr/bin/env python3
"""T9 matrix net-lean for the 4 NRL finals week 1 games. Signs toward the HOME
team (+). Reads nrl_h2h_matrix.xlsx directly (DB-free). Sample-weighted:
N<10=0.3, 10-25=0.6, 25+=1.0."""
import openpyxl, re
from pathlib import Path
MX = Path(__file__).resolve().parent.parent / "outputs" / "nrl_h2h_matrix.xlsx"
wb = openpyxl.load_workbook(MX)

def sheet(name):
    ws = wb[name]; out = {}
    for r in list(ws.iter_rows(values_only=True))[2:]:
        if r[0] is None: continue
        diff = r[3] if isinstance(r[3], (int, float)) else None
        m = re.match(r'^([\d.]+)%\s+(backing|opposing)', str(r[4] or ''))
        edge = (float(m.group(1)), m.group(2)) if m else None
        n = r[5] if isinstance(r[5], (int, float)) else None
        out[str(r[0])] = (diff, edge, n)
    return out

def w(n):
    if not n: return 0.0
    return 0.3 if n < 10 else (0.6 if n < 25 else 1.0)

# matrix sheet names
SH = {'Penrith Panthers':'Penrith Panthers','Sydney Roosters':'Sydney Roosters',
 'New Zealand Warriors':'New Zealand Warriors','Dolphins':'Dolphins',
 'Cronulla Sharks':'Cronulla Sharks','North QLD Cowboys':'North QLD Cowboys',
 'South Sydney Rabbitohs':'South Sydney Rabbitohs','Newcastle Knights':'Newcastle Knights'}

# (game, home, away, [rows to check for home], [rows for away], opp-row-home, opp-row-away)
GAMES = [
 ('QF1', 'Penrith Panthers', 'Sydney Roosters',
  ['Win % — Home','Finals','Night Games','After a Win','Short Rest'],
  ['Win % — Away','Finals','Night Games','After a Loss','Normal Rest'],
  'vs Sydney Roosters', 'vs Penrith Panthers'),
 ('QF2', 'New Zealand Warriors', 'Dolphins',
  ['Win % — Home','Finals','After a Win'],
  ['Win % — Away','Finals','After a Win','Long Haul'],
  'vs Dolphins', 'vs New Zealand Warriors'),
 ('EF1', 'Cronulla Sharks', 'North QLD Cowboys',
  ['Win % — Home','Finals','Night Games','After a Loss'],
  ['Win % — Away','Finals','Night Games','After a Loss'],
  'vs North QLD Cowboys', 'vs Cronulla Sharks'),
 ('EF2', 'South Sydney Rabbitohs', 'Newcastle Knights',
  ['Win % — Home','Finals','Night Games','After a Win'],
  ['Win % — Away','Finals','After a Bye','Off Bye'],
  'vs Newcastle Knights', 'vs South Sydney Rabbitohs'),
]

def match_row(sh_data, wanted):
    for k in sh_data:
        kl = k.lower()
        if wanted.lower() in kl or all(t in kl for t in wanted.lower().split()):
            return k, sh_data[k]
    return None, (None, None, None)

for tag, home, away, hrows, arows, opp_h, opp_a in GAMES:
    hs = sheet(SH[home]); as_ = sheet(SH[away])
    print(f"\n=== {tag}: {home} (H) vs {away} (A) ===")
    net_raw = net_wtd = 0.0
    def add(label, cell, favours_home_if_backing):
        global net_raw, net_wtd
        diff, edge, n = cell
        if not edge:
            print(f"   {label:34} —")
            return
        pct, d = edge
        pos = (d == 'backing') == favours_home_if_backing
        signed = pct if pos else -pct
        net_raw += signed; net_wtd += signed * w(n)
        print(f"   {label:34} {signed:+6.1f}%   (n={n})")
    for wanted in hrows:
        k, cell = match_row(hs, wanted)
        add(f"H {k or wanted}", cell, True)
    for wanted in arows:
        k, cell = match_row(as_, wanted)
        add(f"A {k or wanted}", cell, False)   # away 'backing' = bad for home
    k, cell = match_row(hs, opp_h); add(f"H {opp_h}", cell, True)
    k, cell = match_row(as_, opp_a); add(f"A {opp_a}", cell, False)
    print(f"   {'-'*46}")
    print(f"   NET raw {net_raw:+.1f}%   |   NET sample-weighted {net_wtd:+.1f}%   (+ = leans {home.split()[-1]})")
