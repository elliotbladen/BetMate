"""
One-off: South Sydney Rabbitohs odds drift analysis 2022-2026.
When Souths drift from open to close:
  1. Does the market get it right (do they lose more)?
  2. What is the ROI backing them at their opening price?
"""
import openpyxl
from datetime import datetime

XLSX     = r'C:\Users\ElliotBladen\Apps\data\nrl\historical\latest.xlsx'
TARGET   = 'South Sydney Rabbitohs'
MIN_YEAR = 2022
DRIFT_THRESHOLD = 1.02   # closed 2%+ longer = drifted
SHORTEN_THRESHOLD = 0.98  # closed 2%+ shorter = shortened

wb = openpyxl.load_workbook(XLSX, read_only=True)
ws = wb.active
rows = list(ws.iter_rows(values_only=True))

# Column indices (row index 1 = actual column headers)
DATE        = 0
HOME_TEAM   = 2
AWAY_TEAM   = 3
HOME_SCORE  = 5
AWAY_SCORE  = 6
HOME_O_OPEN = 13
HOME_O_CLOS = 16
AWAY_O_OPEN = 17
AWAY_O_CLOS = 20

results = []

for row in rows[2:]:
    date = row[DATE]
    if not isinstance(date, datetime):
        continue
    if date.year < MIN_YEAR:
        continue

    home = str(row[HOME_TEAM] or '').strip()
    away = str(row[AWAY_TEAM] or '').strip()

    if TARGET not in (home, away):
        continue

    hs = row[HOME_SCORE]
    aws = row[AWAY_SCORE]
    if hs is None or aws is None:
        continue

    if home == TARGET:
        o_open  = row[HOME_O_OPEN]
        o_close = row[HOME_O_CLOS]
        won     = int(hs) > int(aws)
        role    = 'home'
        opp     = away
    else:
        o_open  = row[AWAY_O_OPEN]
        o_close = row[AWAY_O_CLOS]
        won     = int(aws) > int(hs)
        role    = 'away'
        opp     = home

    if o_open is None or o_close is None:
        continue

    try:
        o_open  = float(o_open)
        o_close = float(o_close)
    except (TypeError, ValueError):
        continue

    move_pct = (o_close / o_open - 1) * 100
    drifted   = o_close > o_open * DRIFT_THRESHOLD
    shortened = o_close < o_open * SHORTEN_THRESHOLD

    results.append({
        'date':      date.strftime('%Y-%m-%d'),
        'year':      date.year,
        'opp':       opp.split()[-1],   # nickname only
        'role':      role,
        'o_open':    o_open,
        'o_close':   o_close,
        'move_pct':  move_pct,
        'won':       won,
        'drifted':   drifted,
        'shortened': shortened,
    })


def analyse(games, label):
    if not games:
        print(f'{label}: no games')
        return
    n    = len(games)
    wins = [g for g in games if g['won']]
    nw   = len(wins)
    wr   = nw / n * 100
    profit = sum((g['o_open'] - 1) for g in wins) - (n - nw)
    roi_pct = profit / n * 100
    avg_open  = sum(g['o_open']  for g in games) / n
    avg_close = sum(g['o_close'] for g in games) / n
    print(f'{label}')
    print(f'  Games : {n}   Wins: {nw}   Losses: {n - nw}   Win rate: {wr:.1f}%')
    print(f'  Avg open: {avg_open:.2f}   Avg close: {avg_close:.2f}')
    print(f'  ROI backing at open price (flat $1): {roi_pct:+.1f}%')
    print(f'  Profit/loss per $100 staked: ${roi_pct:.0f}')
    print()


drifted   = [g for g in results if g['drifted']]
shortened = [g for g in results if g['shortened']]
stable    = [g for g in results if not g['drifted'] and not g['shortened']]

print('=' * 65)
print(f'SOUTH SYDNEY RABBITOHS — ODDS DRIFT ANALYSIS {MIN_YEAR}–2026')
print(f'Total games: {len(results)}   Drift threshold: ±2% open→close')
print('=' * 65)
print()

analyse(drifted,   'DRIFTED  (closed 2%+ longer  — market moved against)')
analyse(shortened, 'SHORTENED (closed 2%+ shorter — market moved toward)')
analyse(stable,    'STABLE   (within 2% — no significant move)')

overall_wins = sum(g['won'] for g in results)
print(f'OVERALL: {len(results)} games  {overall_wins}W / {len(results)-overall_wins}L  '
      f'{overall_wins/len(results)*100:.1f}% win rate')
print()

# Year-by-year for drifted
print('Drifted games by year:')
for yr in range(MIN_YEAR, 2027):
    yr_g = [g for g in drifted if g['year'] == yr]
    if not yr_g:
        continue
    nw = sum(g['won'] for g in yr_g)
    profit = sum((g['o_open'] - 1) for g in yr_g if g['won']) - (len(yr_g) - nw)
    roi = profit / len(yr_g) * 100
    print(f'  {yr}: {len(yr_g):2d} games  {nw}W / {len(yr_g)-nw}L  '
          f'win={nw/len(yr_g)*100:.0f}%  ROI={roi:+.1f}%')

print()
print('Last 20 drifted games (newest first):')
print(f'  {"Date":<12} {"Opp":<14} {"Role":<5} {"Open":>5} {"Close":>5} {"Drift":>6}  Result')
print(f'  {"-"*12} {"-"*14} {"-"*5} {"-"*5} {"-"*5} {"-"*6}  ------')
for g in sorted(drifted, key=lambda x: x['date'], reverse=True)[:20]:
    print(f'  {g["date"]:<12} {g["opp"]:<14} {g["role"]:<5} '
          f'{g["o_open"]:>5.2f} {g["o_close"]:>5.2f} {g["move_pct"]:>+5.1f}%  '
          f'{"WIN " if g["won"] else "LOSS"}')
