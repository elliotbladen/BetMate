"""
AFL Closing Handicap Line Accuracy — 2022-2026
How close does the closing line get to the actual result?
"""
import openpyxl
from datetime import datetime
import statistics

XLSX     = r'C:\Users\ElliotBladen\Apps\BettingEngine\outputs\afl_weekly_review\historical\latest.xlsx'
MIN_YEAR = 2022

# Column indices
DATE             = 0
HOME_TEAM        = 2
AWAY_TEAM        = 3
HOME_SCORE       = 5
AWAY_SCORE       = 6
HOME_LINE_CLOSE  = 26   # negative = home favoured (e.g. -12.5)
HOME_LINE_OPEN   = 23

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
        line_close  = float(line_close)
        hs          = int(hs)
        aws         = int(aws)
        line_open   = float(line_open) if line_open is not None else None
    except (TypeError, ValueError):
        continue

    actual_margin = hs - aws             # home perspective
    # "covered" = actual margin BEAT the closing line
    # e.g. line=-12.5 (home fav by 12.5), actual=+15 → covered (+2.5)
    # e.g. line=+6.5 (home dog by 6.5),   actual=-3  → covered (+9.5)
    cover_margin = actual_margin - (-line_close)  # positive = home covered
    home_covered = cover_margin > 0
    error = actual_margin - (-line_close)   # signed error (positive = home beat line)
    abs_error = abs(error)

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
        'home_fav':     line_close < 0,    # negative = home is fav
        'fav_covered':  home_covered if line_close < 0 else not home_covered,
    })

# ── Overall stats ─────────────────────────────────────────────────────────
n = len(games)
mae  = sum(g['abs_error'] for g in games) / n
bias = sum(g['error'] for g in games) / n
covered_pct = sum(g['home_covered'] for g in games) / n * 100
fav_covered = sum(g['fav_covered'] for g in games) / n * 100
median_err  = statistics.median(g['abs_error'] for g in games)
stdev       = statistics.stdev(g['error'] for g in games)

# % within various error bands
def within(games, pts):
    return sum(1 for g in games if g['abs_error'] <= pts) / len(games) * 100

print('=' * 65)
print(f'AFL CLOSING HANDICAP LINE ACCURACY  {MIN_YEAR}–2026')
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
for pts in [6, 12, 18, 24, 36, 48]:
    w = within(games, pts)
    bar = '#' * int(w / 2)
    print(f'  Within {pts:2d} pts: {w:5.1f}%  {bar}')
print()

# ── Year by year ──────────────────────────────────────────────────────────
print('Year-by-year breakdown:')
print(f'  {"Year":<6} {"N":>4}  {"MAE":>6}  {"Bias":>6}  {"Median":>7}  {"±6pts":>6}  {"±12pts":>7}  {"±24pts":>7}')
print(f'  {"-"*6} {"-"*4}  {"-"*6}  {"-"*6}  {"-"*7}  {"-"*6}  {"-"*7}  {"-"*7}')
for yr in range(MIN_YEAR, 2027):
    yg = [g for g in games if g['year'] == yr]
    if not yg:
        continue
    yr_mae    = sum(g['abs_error'] for g in yg) / len(yg)
    yr_bias   = sum(g['error'] for g in yg) / len(yg)
    yr_median = statistics.median(g['abs_error'] for g in yg)
    w6  = within(yg, 6)
    w12 = within(yg, 12)
    w24 = within(yg, 24)
    print(f'  {yr:<6} {len(yg):>4}  {yr_mae:>6.1f}  {yr_bias:>+6.2f}  {yr_median:>7.1f}  '
          f'{w6:>5.1f}%  {w12:>6.1f}%  {w24:>6.1f}%')
print()

# ── Favourites vs underdogs ───────────────────────────────────────────────
favs = [g for g in games if g['home_fav']]
dogs = [g for g in games if not g['home_fav']]
print('Favourite vs Underdog:')
print(f'  Favourites   n={len(favs):3d}  MAE={sum(g["abs_error"] for g in favs)/len(favs):.1f}  '
      f'fav_cover={sum(g["fav_covered"] for g in favs)/len(favs)*100:.1f}%')
print(f'  Underdogs    n={len(dogs):3d}  MAE={sum(g["abs_error"] for g in dogs)/len(dogs):.1f}  '
      f'dog_cover={sum(g["fav_covered"] for g in dogs)/len(dogs)*100:.1f}%')
print()

# ── Line size buckets ─────────────────────────────────────────────────────
print('Accuracy by line size (abs closing line):')
buckets = [
    ('Very tight  (<6.5)',   lambda g: abs(g['line_close']) < 6.5),
    ('Tight       (6.5-12)', lambda g: 6.5 <= abs(g['line_close']) < 12.5),
    ('Medium      (12.5-24)',lambda g: 12.5 <= abs(g['line_close']) < 24.5),
    ('Large       (24.5-36)',lambda g: 24.5 <= abs(g['line_close']) < 36.5),
    ('Blowout     (36.5+)',  lambda g: abs(g['line_close']) >= 36.5),
]
for label, fn in buckets:
    bg = [g for g in games if fn(g)]
    if not bg:
        continue
    bg_mae = sum(g['abs_error'] for g in bg) / len(bg)
    bg_cov = sum(g['fav_covered'] for g in bg) / len(bg) * 100
    w12 = within(bg, 12)
    print(f'  {label:<24}  n={len(bg):3d}  MAE={bg_mae:5.1f}  fav_cvr={bg_cov:5.1f}%  within12={w12:5.1f}%')
print()

# ── Biggest misses ────────────────────────────────────────────────────────
print('Top 10 biggest closing line misses (actual vs line):')
print(f'  {"Date":<12} {"Home":<22} {"Away":<22} {"Line":>6} {"Actual":>7} {"Error":>7}')
print(f'  {"-"*12} {"-"*22} {"-"*22} {"-"*6} {"-"*7} {"-"*7}')
for g in sorted(games, key=lambda x: -x['abs_error'])[:10]:
    line_str = f'{-g["line_close"]:+.1f}'
    print(f'  {g["date"]:<12} {g["home"]:<22} {g["away"]:<22} '
          f'{line_str:>6} {g["actual"]:>+7} {g["error"]:>+7.1f}')
