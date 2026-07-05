import csv
from collections import defaultdict

bets = []
with open(r'C:\Users\ElliotBladen\Apps\BettingEngine\data\bets\actual_bets_2026.csv', encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        if row.get('bet_id'):
            bets.append(row)

def roi_summary(rows, label='ALL'):
    total_stake = sum(float(b['stake']) for b in rows)
    total_pnl = sum(float(b['pnl']) for b in rows)
    wins = sum(1 for b in rows if b['result'] == 'win')
    losses = sum(1 for b in rows if b['result'] == 'loss')
    roi = (total_pnl / total_stake * 100) if total_stake else 0
    print(f"{label:30s}  bets={len(rows):2d}  W={wins} L={losses}  stake=${total_stake:.0f}  pnl=${total_pnl:+.2f}  ROI={roi:+.1f}%")

print("=== ROI BY ROUND ===")
by_round = defaultdict(list)
for b in bets:
    by_round[(b['sport'], int(b['round']))].append(b)
for k in sorted(by_round):
    roi_summary(by_round[k], f"{k[0]} R{k[1]}")

print()
print("=== ROI BY SPORT ===")
afl_bets = [b for b in bets if b['sport'] == 'AFL']
nrl_bets = [b for b in bets if b['sport'] == 'NRL']
roi_summary(afl_bets, "AFL (all rounds)")
roi_summary(nrl_bets, "NRL (all rounds)")
print()
roi_summary(bets, "TOTAL")

print()
print("=== ROI BY MARKET TYPE ===")
by_market = defaultdict(list)
for b in bets:
    by_market[(b['sport'], b['market_type'])].append(b)
for k in sorted(by_market):
    roi_summary(by_market[k], f"{k[0]} {k[1]}")

print()
print("=== RUNNING ROI (bet by bet) ===")
running_stake = 0.0
running_pnl = 0.0
for i, b in enumerate(bets, 1):
    running_stake += float(b['stake'])
    running_pnl += float(b['pnl'])
    roi = running_pnl / running_stake * 100
    sport_round = f"{b['sport']} R{b['round']} {b['market_type']}"
    print(f"  {i:2d}. {sport_round:25s}  cumul stake=${running_stake:.0f}  pnl=${running_pnl:+.2f}  ROI={roi:+.1f}%")
