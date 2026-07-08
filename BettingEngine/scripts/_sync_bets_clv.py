"""
Sync closing_price, closing_line, clv from actual_bets_clv_2026.csv
back into actual_bets_2026.csv using bet_id as the join key.
"""
import csv
from pathlib import Path

ROOT     = Path(__file__).resolve().parent.parent
MASTER   = ROOT / 'data' / 'bets' / 'actual_bets_2026.csv'
CLV_FILE = ROOT / 'data' / 'clv' / 'running' / 'actual_bets_clv_2026.csv'

# ── Load CLV lookup ────────────────────────────────────────────────────────
# actual_bets_clv_2026.csv columns:
#   bet_id, sport, round, match, market, selection, line, odds_taken,
#   close_line, open_line, line_move, close_odds, clv_pct, clv_line, result, pnl

clv_lookup = {}
with open(CLV_FILE, newline='', encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        bid = row['bet_id'].strip()
        clv_lookup[bid] = {
            'closing_price': row.get('close_odds', '').strip(),
            'closing_line':  row.get('close_line', '').strip(),
            'clv':           row.get('clv_pct', '').strip(),
        }

print(f'CLV lookup loaded: {len(clv_lookup)} entries')

# ── Read master ledger ─────────────────────────────────────────────────────
with open(MASTER, newline='', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    fieldnames = [fn for fn in reader.fieldnames if fn is not None]
    rows = [{k: v for k, v in row.items() if k is not None} for row in reader]

# ── Sync ──────────────────────────────────────────────────────────────────
updated = 0
not_found = []

for row in rows:
    bid = row['bet_id'].strip()
    if bid not in clv_lookup:
        not_found.append(bid)
        continue

    clv = clv_lookup[bid]

    # Only fill if currently empty
    if not row.get('closing_price') and clv['closing_price']:
        row['closing_price'] = clv['closing_price']
        updated += 1

    if not row.get('closing_line') and clv['closing_line']:
        row['closing_line'] = clv['closing_line']

    if not row.get('clv') and clv['clv']:
        row['clv'] = clv['clv']

print(f'Updated closing_price for {updated} rows')
if not_found:
    print(f'No CLV data for: {not_found}')

# ── Write back ────────────────────────────────────────────────────────────
with open(MASTER, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f'Written: {MASTER}')
print()

# ── Preview ───────────────────────────────────────────────────────────────
print(f'{"bet_id":<14} {"selection":<28} {"odds_taken":>10} {"closing_price":>13} {"closing_line":>12} {"clv":>8}')
print('-' * 90)
for row in rows:
    print(f'{row["bet_id"]:<14} {row["selection"][:27]:<28} '
          f'{row["odds_taken"]:>10} {row["closing_price"]:>13} '
          f'{row["closing_line"]:>12} {row["clv"]:>8}')
