import csv
from pathlib import Path
from collections import defaultdict

rows = list(csv.DictReader(open('data/odds_movements/latest.csv', encoding='utf-8')))
afl  = [r for r in rows if r['sport'] == 'AFL' and r['market'] == 'totals']

print('=== AFL TOTALS MOVEMENTS (vs Monday baseline) ===\n')

by_game = defaultdict(lambda: defaultdict(list))
for r in afl:
    game = f"{r['home_team']} vs {r['away_team']}"
    by_game[game][r['outcome']].append({
        'dir': r['direction'],
        'pct': float(r['change_pct']),
        'old': float(r['old_price']),
        'new': float(r['new_price']),
        'bk':  r['bookmaker'],
        'pt':  r.get('point', ''),
    })

for game, outcomes in sorted(by_game.items()):
    print(game)
    for outcome, moves in sorted(outcomes.items()):
        short = [m for m in moves if m['dir'] == 'down']
        drift = [m for m in moves if m['dir'] == 'up']
        for m in short:
            pt = m['pt']
            print(f"  SHORT  {outcome:<6}  line={pt:<7} {m['old']:.2f}->{m['new']:.2f} ({m['pct']:+.1f}%)  {m['bk']}")
        for m in drift:
            pt = m['pt']
            print(f"  drift  {outcome:<6}  line={pt:<7} {m['old']:.2f}->{m['new']:.2f} ({m['pct']:+.1f}%)  {m['bk']}")
    print()
