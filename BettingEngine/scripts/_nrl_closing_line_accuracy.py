"""
NRL Closing Handicap Line Accuracy — 2022-2026
Same methodology as AFL equivalent for direct comparison.
"""
import openpyxl
from datetime import datetime
import statistics

XLSX     = r'C:\Users\ElliotBladen\Apps\data\nrl\historical\latest.xlsx'
MIN_YEAR = 2022

DATE             = 0
HOME_TEAM        = 2
AWAY_TEAM        = 3
HOME_SCORE       = 5
AWAY_SCORE       = 6
HOME_LINE_CLOSE  = 24   # NRL: 'Home Line Close'
HOME_LINE_OPEN   = 21   # NRL: 'Home Line Open'

wb = openpyxl.load_workbook(XLSX, read_only=True)
ws = wb.active
rows = list(ws.iter_rows(values_only=True))

games = []

for row in rows[2:]:
    date = row[DATE]
    if not isinstance(date, datetime):
        continue
    if date.year < MIN_YEAR:
        continue

    hs  = row[HOME_SCORE]
    aws = row[AWAY_SCORE]
    if hs is None or aws is None:
        continue

    line_close = row[HOME_LINE_CLOSE]
    line_open  = row[HOME_LINE_OPEN]
    if line_close is None:
        continue

    try:
        line_close = float(line_close)
        hs         = int(hs)
        aws        = int(aws)
        line_open  = float(line_open) if line_open is not None else None
    except (TypeError, ValueError):
        continue

    actual_margin = hs - aws
    error         = actual_margin - (-line_close)
    abs_error     = abs(error)
    home_covered  = error > 0

    games.append({
        'date':         date.strftime('%Y-%m-%d'),
        'year':         date.year,
        'home':         str(row[HOME_TEAM] or '').strip(),
        'away':         str(row[AWAY_TEAM] or '').strip(),
        'line_close':   line_close,
        'line_open':    line_open,
        'actual':       actual_margin,
        'error':        error,
        'abs_error':    abs_error,
        'home_covered': home_covered,
        'home_fav':     line_close < 0,
        'fav_covered':  home_covered if line_close < 0 else not home_covered,
    })

n    = len(games)
mae  = sum(g['abs_error'] for g in games) / n
bias = sum(g['error'] for g in games) / n
stdev = statistics.stdev(g['error'] for g in games)
median_err = statistics.median(g['abs_error'] for g in games)
covered_pct = sum(g['home_covered'] for g in games) / n * 100
fav_covered = sum(g['fav_covered'] for g in games) / n * 100

def within(games, pts):
    return sum(1 for g in games if g['abs_error'] <= pts) / len(games) * 100

print('=' * 65)
print(f'NRL CLOSING HANDICAP LINE ACCURACY  {MIN_YEAR}–2026')
print(f'Games analysed: {n}')
print('=' * 65)
print()
print(f'MAE (mean absolute error):       {mae:.1f} pts')
print(f'Median absolute error:           {median_err:.1f} pts')
print(f'Bias (avg signed error):         {bias:+.2f} pts  (+ = home beats line)')
print(f'Standard deviation:              {stdev:.1f} pts')
print()
print(f'Home team covered closing line:  {covered_pct:.1f}%')
print(f'Favourite covered closing line:  {fav_covered:.1f}%')
print()
print('Error distribution (% of games within X pts of closing line):')
for pts in [3, 6, 9, 12, 18, 24]:
    w = within(games, pts)
    bar = '#' * int(w / 2)
    print(f'  Within {pts:2d} pts: {w:5.1f}%  {bar}')
print()

print('Year-by-year breakdown:')
print(f'  {"Year":<6} {"N":>4}  {"MAE":>6}  {"Bias":>6}  {"Median":>7}  {"±3pts":>6}  {"±6pts":>6}  {"±12pts":>7}')
print(f'  {"-"*6} {"-"*4}  {"-"*6}  {"-"*6}  {"-"*7}  {"-"*6}  {"-"*6}  {"-"*7}')
for yr in range(MIN_YEAR, 2027):
    yg = [g for g in games if g['year'] == yr]
    if not yg:
        continue
    yr_mae    = sum(g['abs_error'] for g in yg) / len(yg)
    yr_bias   = sum(g['error'] for g in yg) / len(yg)
    yr_median = statistics.median(g['abs_error'] for g in yg)
    w3  = within(yg, 3)
    w6  = within(yg, 6)
    w12 = within(yg, 12)
    print(f'  {yr:<6} {len(yg):>4}  {yr_mae:>6.1f}  {yr_bias:>+6.2f}  {yr_median:>7.1f}  '
          f'{w3:>5.1f}%  {w6:>5.1f}%  {w12:>6.1f}%')
print()

favs = [g for g in games if g['home_fav']]
dogs = [g for g in games if not g['home_fav']]
print('Favourite vs Underdog:')
print(f'  Favourites   n={len(favs):3d}  MAE={sum(g["abs_error"] for g in favs)/len(favs):.1f}  '
      f'fav_cover={sum(g["fav_covered"] for g in favs)/len(favs)*100:.1f}%')
print(f'  Underdogs    n={len(dogs):3d}  MAE={sum(g["abs_error"] for g in dogs)/len(dogs):.1f}  '
      f'dog_cover={sum(g["fav_covered"] for g in dogs)/len(dogs)*100:.1f}%')
print()

print('Accuracy by line size:')
buckets = [
    ('Very tight  (<3.5)',   lambda g: abs(g['line_close']) < 3.5),
    ('Tight       (3.5-6)',  lambda g: 3.5 <= abs(g['line_close']) < 6.5),
    ('Medium      (6.5-12)', lambda g: 6.5 <= abs(g['line_close']) < 12.5),
    ('Large       (12.5-18)',lambda g: 12.5 <= abs(g['line_close']) < 18.5),
    ('Blowout     (18.5+)',  lambda g: abs(g['line_close']) >= 18.5),
]
for label, fn in buckets:
    bg = [g for g in games if fn(g)]
    if not bg:
        continue
    bg_mae = sum(g['abs_error'] for g in bg) / len(bg)
    bg_cov = sum(g['fav_covered'] for g in bg) / len(bg) * 100
    w6 = within(bg, 6)
    print(f'  {label:<24}  n={len(bg):3d}  MAE={bg_mae:5.1f}  fav_cvr={bg_cov:5.1f}%  within6={w6:5.1f}%')
print()

print('Top 10 biggest closing line misses:')
print(f'  {"Date":<12} {"Home":<30} {"Away":<30} {"Line":>6} {"Actual":>7} {"Error":>7}')
print(f'  {"-"*12} {"-"*30} {"-"*30} {"-"*6} {"-"*7} {"-"*7}')
for g in sorted(games, key=lambda x: -x['abs_error'])[:10]:
    line_str = f'{-g["line_close"]:+.1f}'
    print(f'  {g["date"]:<12} {g["home"]:<30} {g["away"]:<30} '
          f'{line_str:>6} {g["actual"]:>+7} {g["error"]:>+7.1f}')
