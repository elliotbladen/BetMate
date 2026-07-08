"""Hawks vs Bulldogs — full breakdown from AFL historical xlsx."""
import openpyxl
from datetime import datetime
import statistics

XLSX = r'C:\Users\ElliotBladen\Apps\BettingEngine\outputs\afl_weekly_review\historical\latest.xlsx'
HAW  = 'Hawthorn'
DOG  = 'Western Bulldogs'

wb   = openpyxl.load_workbook(XLSX, read_only=True)
ws   = wb.active
rows = list(ws.iter_rows(values_only=True))

games = []
for row in rows[2:]:
    date = row[0]
    if not isinstance(date, datetime):
        continue
    hs, aws = row[5], row[6]
    if hs is None or aws is None:
        continue
    games.append({
        'date':  date,
        'year':  date.year,
        'home':  str(row[2] or '').strip(),
        'away':  str(row[3] or '').strip(),
        'hs':    int(hs),
        'aws':   int(aws),
    })

def team_games(team, all_games):
    return [g for g in all_games if g['home'] == team or g['away'] == team]

def margin_for(team, g):
    if g['home'] == team:
        return g['hs'] - g['aws']
    return g['aws'] - g['hs']

def won(team, g):
    return margin_for(team, g) > 0

# ── Recent form (last 8 games each, 2026 season) ──────────────────────────
for team in [HAW, DOG]:
    tg = sorted(team_games(team, games), key=lambda x: x['date'], reverse=True)[:8]
    print(f'=== RECENT FORM — {team} (last 8) ===')
    wins   = sum(1 for g in tg if won(team, g))
    losses = len(tg) - wins
    margins = [margin_for(team, g) for g in tg]
    for g in tg:
        opp = g['away'] if g['home'] == team else g['home']
        m   = margin_for(team, g)
        r   = 'WIN ' if m > 0 else 'LOSS'
        role = 'H' if g['home'] == team else 'A'
        print(f'  {g["date"].strftime("%Y-%m-%d")} ({role})  vs {opp:<22} {r}  {m:+d}')
    print(f'  Record: {wins}W / {losses}L  |  Avg margin: {sum(margins)/len(margins):+.1f}  |  '
          f'Best: {max(margins):+d}  Worst: {min(margins):+d}')
    print()

# ── 2026 season only ──────────────────────────────────────────────────────
for team in [HAW, DOG]:
    tg = [g for g in team_games(team, games) if g['year'] == 2026]
    tg_sorted = sorted(tg, key=lambda x: x['date'])
    wins = sum(1 for g in tg_sorted if won(team, g))
    margins = [margin_for(team, g) for g in tg_sorted]
    pf_avg = 0
    pa_avg = 0
    for g in tg_sorted:
        if g['home'] == team:
            pf_avg += g['hs']; pa_avg += g['aws']
        else:
            pf_avg += g['aws']; pa_avg += g['hs']
    n = len(tg_sorted)
    print(f'2026 season — {team}: {wins}W / {n-wins}L  '
          f'PF={pf_avg/n:.1f}  PA={pa_avg/n:.1f}  '
          f'Avg margin: {sum(margins)/n:+.1f}')

print()

# ── H2H last 10 ───────────────────────────────────────────────────────────
h2h = [g for g in games
       if (g['home'] == HAW and g['away'] == DOG)
       or (g['home'] == DOG and g['away'] == HAW)]
h2h = sorted(h2h, key=lambda x: x['date'], reverse=True)[:10]

haw_wins = sum(1 for g in h2h if won(HAW, g))
h2h_margins = [margin_for(HAW, g) for g in h2h]

print(f'=== H2H — {HAW} vs {DOG} (last 10) ===')
for g in h2h:
    m = margin_for(HAW, g)
    w = 'HAW ✓' if m > 0 else 'DOG ✓'
    print(f'  {g["date"].strftime("%Y-%m-%d")}  {g["home"]:<22} {g["hs"]:3d} – {g["aws"]:3d} '
          f'{g["away"]:<22}  ({m:+d} Hawks)  {w}')

print(f'\n  Hawks H2H:       {haw_wins}W – {len(h2h)-haw_wins}L  '
      f'({haw_wins/len(h2h)*100:.0f}% win rate)')
print(f'  Avg H2H margin:  {sum(h2h_margins)/len(h2h_margins):+.1f} pts (Hawks perspective)')
print(f'  Median margin:   {statistics.median(h2h_margins):+.1f} pts')

# ── Home advantage at MCG ─────────────────────────────────────────────────
mcg_haw = [g for g in games if g['home'] == HAW and 'MCG' in str(g.get('venue',''))]
# venue isn't in our parsed dict — skip, note below
print()
print(f'=== SCORING ENVIRONMENT 2026 ===')
for team in [HAW, DOG]:
    tg = [g for g in team_games(team, games) if g['year'] == 2026]
    pf = [margin_for(team, g) + 2*min(g['hs'],g['aws']) for g in tg]   # rough
    scores = []
    for g in tg:
        scores.append(g['hs'] + g['aws'])
    print(f'  {team:<22} avg game total={sum(scores)/len(scores):.1f}  '
          f'n={len(tg)}')
