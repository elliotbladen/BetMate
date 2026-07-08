"""
Rebuild actual_bets_2026.csv from weekly files + CLV file,
then sync closing_price, closing_line, clv from the CLV file.
"""
import csv
from pathlib import Path

ROOT    = Path(__file__).resolve().parent.parent
WEEKLY  = ROOT / 'data' / 'bets' / 'weekly'
CLV_F   = ROOT / 'data' / 'clv' / 'running' / 'actual_bets_clv_2026.csv'
MASTER  = ROOT / 'data' / 'bets' / 'actual_bets_2026.csv'

FIELDNAMES = [
    'bet_id','week_ending','placed_date','placed_time','sport','season','round',
    'home_team','away_team','market_type','selection','line','odds_taken',
    'stake','return_amount','result','pnl','bookmaker','model_price','model_line',
    'closing_price','closing_line','clv','source_signal_id','source_text','notes'
]

# ── Step 1: load CLV lookup ────────────────────────────────────────────────
clv_lookup = {}
with open(CLV_F, newline='', encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        bid = row['bet_id'].strip()
        clv_lookup[bid] = {
            'closing_price': row.get('close_odds', '').strip(),
            'closing_line':  row.get('close_line', '').strip(),
            'clv':           row.get('clv_pct', '').strip(),
            # also carry result/pnl for reconstruction
            '_result': row.get('result', '').strip(),
            '_pnl':    row.get('pnl', '').strip(),
            '_sport':  row.get('sport', '').strip(),
            '_round':  row.get('round', '').strip(),
            '_match':  row.get('match', '').strip(),
            '_market': row.get('market', '').strip(),
            '_selection': row.get('selection', '').strip(),
            '_line':   row.get('line', '').strip(),
            '_odds_taken': row.get('odds_taken', '').strip(),
        }

# ── Step 2: load all weekly files ─────────────────────────────────────────
rows = {}  # bet_id → row dict
for f in sorted(WEEKLY.glob('*.csv')):
    with open(f, newline='', encoding='utf-8-sig') as fh:
        for row in csv.DictReader(fh):
            bid = row['bet_id'].strip()
            # clean None keys
            clean = {k: v for k, v in row.items() if k is not None}
            rows[bid] = clean

print(f'Weekly files: {len(rows)} bets loaded (0001-0044)')

# ── Step 3: reconstruct bets 0045-0061 from CLV file ──────────────────────
known_ids = set(rows.keys())
reconstructed = 0
for bid, clv in clv_lookup.items():
    if bid in known_ids:
        continue
    # Reconstruct minimal row — we have odds, pnl, result from CLV
    try:
        odds = float(clv['_odds_taken']) if clv['_odds_taken'] else 0
        pnl  = float(clv['_pnl'])        if clv['_pnl']        else 0
        # derive stake from pnl
        if clv['_result'].upper() in ('WIN', 'W') and odds > 1:
            stake = round(pnl / (odds - 1), 2)
            return_amt = round(stake * odds, 2)
        else:
            stake = round(abs(pnl), 2)
            return_amt = 0.0
    except (ValueError, ZeroDivisionError):
        stake = 25.0
        return_amt = 0.0

    # parse home/away from match string e.g. "Saints v Hawks"
    match_parts = clv['_match'].split(' v ')
    home_t = match_parts[0].strip() if len(match_parts) > 1 else clv['_match']
    away_t = match_parts[1].strip() if len(match_parts) > 1 else ''

    # infer week_ending and placed_date from round/sport
    rnd = clv['_round']
    if clv['_sport'] == 'AFL':
        week_map = {'12': '2026-06-01', '13': '2026-06-08'}
        wk = week_map.get(rnd, '2026-06-01')
    else:
        week_map = {'12': '2026-05-25', '13': '2026-06-01'}
        wk = week_map.get(rnd, '2026-06-01')

    rows[bid] = {
        'bet_id':          bid,
        'week_ending':     wk,
        'placed_date':     '',
        'placed_time':     '',
        'sport':           clv['_sport'],
        'season':          '2026',
        'round':           rnd,
        'home_team':       home_t,
        'away_team':       away_t,
        'market_type':     clv['_market'],
        'selection':       clv['_selection'],
        'line':            clv['_line'],
        'odds_taken':      clv['_odds_taken'],
        'stake':           str(stake),
        'return_amount':   str(return_amt),
        'result':          clv['_result'],
        'pnl':             clv['_pnl'],
        'bookmaker':       'sportsbet',
        'model_price':     '',
        'model_line':      '',
        'closing_price':   '',
        'closing_line':    '',
        'clv':             '',
        'source_signal_id':'',
        'source_text':     f'{clv["_selection"]} @ {clv["_odds_taken"]} | {clv["_match"]}',
        'notes':           '',
    }
    reconstructed += 1

print(f'Reconstructed {reconstructed} bets from CLV file (0045-0061)')

# ── Step 4: sync closing_price / closing_line / clv ───────────────────────
synced = 0
for bid, row in rows.items():
    if bid not in clv_lookup:
        continue
    clv = clv_lookup[bid]

    # Always trust the CLV file for closing_price — weekly files sometimes
    # had the bet line (e.g. -9.5) incorrectly stored there instead of close odds.
    if clv['closing_price']:
        row['closing_price'] = clv['closing_price']
        synced += 1
    if clv['closing_line']:
        row['closing_line'] = clv['closing_line']
    if clv['clv']:
        row['clv'] = clv['clv']

print(f'Synced close/CLV data for {synced} rows')

# ── Step 5: write master ───────────────────────────────────────────────────
ordered = sorted(rows.values(), key=lambda r: r['bet_id'])

with open(MASTER, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(ordered)

print(f'Written {len(ordered)} rows → {MASTER}')
print()

# ── Preview ────────────────────────────────────────────────────────────────
print(f'{"ID":<14} {"Sport":<5} {"R":<3} {"Selection":<28} {"Odds":>5} {"Close":>6} {"CLV":>7}  Result')
print('-' * 80)
for row in ordered:
    print(f'{row["bet_id"]:<14} {row["sport"]:<5} {row["round"]:<3} '
          f'{row["selection"][:27]:<28} {row["odds_taken"]:>5} '
          f'{row["closing_price"]:>6} {row["clv"]:>7}  {row["result"]}')
