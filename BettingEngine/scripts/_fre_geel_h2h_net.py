#!/usr/bin/env python3
"""One-off: net H2H matrix lean for Fremantle (home) vs Geelong (away),
Semi Final, Optus Stadium, Fri 11 Sep 2026 (night). Signs everything toward
Fremantle (+) vs Geelong (-)."""
import openpyxl, re
from pathlib import Path

MX = Path(__file__).resolve().parent.parent / 'outputs' / 'afl_h2h_matrix.xlsx'
wb = openpyxl.load_workbook(MX)

def sheet(name):
    ws = wb[name]
    out = {}
    for r in list(ws.iter_rows(values_only=True))[2:]:
        if r[0] is None:
            continue
        diff = r[3] if isinstance(r[3], (int, float)) else None
        m = re.match(r'^([\d.]+)%\s+(backing|opposing)', str(r[4] or ''))
        edge = (float(m.group(1)), m.group(2)) if m else None
        n = r[5] if isinstance(r[5], (int, float)) else None
        out[str(r[0])] = (diff, edge, n)
    return out

fre = sheet('Fremantle')
geel = sheet('Geelong')

# (label, fremantle-row, geelong-row)  — None = not applicable to that team
ROWS = [
    ('Generic home / away',      'Win % — Home',                 'Win % — Away'),
    ('Night game (>=18:00)',     'Night Games (kick-off ≥ 18:00)','Night Games (kick-off ≥ 18:00)'),
    ('Thursday / Friday',        'Thursday / Friday Games',           'Thursday / Friday Games'),
    ('Normal rest 7-9d',         'Normal Rest (7–9 days)',       'Normal Rest (7–9 days)'),
    ('After a Loss / Win',       'After a Loss',                      'After a Win'),
    ('September',                'September',                         'September'),
    ('Finals games',             'Finals Games',                      'Finals Games'),
    ('Head-to-head vs opp',      'vs Geelong',                        'vs Fremantle'),
    ('Venue: Optus Stadium',     'Optus Stadium',                     'Optus Stadium'),
    ('Geelong away: interstate', None,                                'Away — Interstate'),
    ('Geelong away: long haul',  None,                                'Away — Long Haul (Perth / TAS / NT / OS)'),
]

def w(n):
    if n is None: return 0.0
    if n < 10: return 0.3
    if n < 25: return 0.6
    return 1.0

def signed_edge(cell, team):
    """+ve favours Fremantle. team = 'fre' or 'geel'."""
    if not cell or not cell[1]:
        return None, None, None
    pct, direction = cell[1]
    n = cell[2]
    backing_helps_fre = (team == 'fre') == (direction == 'backing')
    return (pct if backing_helps_fre else -pct), n, direction

def signed_diff(cell, team):
    if not cell or cell[0] is None:
        return None, None
    d, _, n = cell
    # diff(pp) = actual - market-implied for THAT team's win.
    # +ve diff for fre-row favours Fremantle; +ve diff for geel-row favours Geelong.
    return (d if team == 'fre' else -d), n

print(f"{'Context row':26s} {'Fre edge%':>10s} {'Geel edge%':>11s} {'net edge%':>10s} "
      f"{'net Δpp':>9s} {'wtd net%':>9s}  N(fre/geel)")
print('-' * 100)

tot_raw_edge = tot_raw_diff = tot_wtd_edge = 0.0
for label, frow, grow in ROWS:
    fe, fn, fd_ = signed_edge(fre.get(frow), 'fre') if frow else (None, None, None)
    ge, gn, gd_ = signed_edge(geel.get(grow), 'geel') if grow else (None, None, None)
    fdiff, fdn = signed_diff(fre.get(frow), 'fre') if frow else (None, None)
    gdiff, gdn = signed_diff(geel.get(grow), 'geel') if grow else (None, None)

    net_edge = sum(x for x in (fe, ge) if x is not None)
    net_diff = sum(x for x in (fdiff, gdiff) if x is not None)
    wtd = sum((x * w(nn)) for x, nn in ((fe, fn), (ge, gn)) if x is not None)

    tot_raw_edge += net_edge
    tot_raw_diff += net_diff
    tot_wtd_edge += wtd

    fes = f"{fe:+.1f}" if fe is not None else "  ."
    ges = f"{ge:+.1f}" if ge is not None else "  ."
    print(f"{label:26s} {fes:>10s} {ges:>11s} {net_edge:>+10.1f} {net_diff:>+9.1f} {wtd:>+9.1f}  "
          f"{fn}/{gn}")

print('-' * 100)
print(f"{'NET (raw sum)':26s} {'':>10s} {'':>11s} {tot_raw_edge:>+10.1f} {tot_raw_diff:>+9.1f} {tot_wtd_edge:>+9.1f}")
print()
print("Positive = leans Fremantle, negative = leans Geelong.")
print(f"Raw net edge%:            {tot_raw_edge:+.1f}")
print(f"Raw net difference (pp):  {tot_raw_diff:+.1f}")
print(f"Sample-weighted net edge%: {tot_wtd_edge:+.1f}   (N<10=0.3, 10-25=0.6, 25+=1.0)")
