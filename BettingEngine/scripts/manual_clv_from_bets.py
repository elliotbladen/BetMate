"""
manual_clv_from_bets.py
Compare actual bets vs closing odds from AusSportsBetting historical xlsx.
Calculates CLV for H2H, handicap lines, and totals.
"""
import csv, openpyxl
from datetime import datetime, date
from collections import defaultdict

# ── Team name normaliser ─────────────────────────────────────────────────────
NRL_ALIASES = {
    "st george dragons": "st george illawarra dragons",
    "st george/illa dragons": "st george illawarra dragons",
    "cronulla sharks": "cronulla-sutherland sharks",
    "newcastle": "newcastle knights",
    "manly sea eagles": "manly-warringah sea eagles",
    "parramatta eels": "parramatta eels",
    "north qld cowboys": "north queensland cowboys",
    "brisbane broncos": "brisbane broncos",
    "nz warriors": "new zealand warriors",
    "new zealand warriors": "new zealand warriors",
}
AFL_ALIASES = {
    "gold coast": "gold coast suns",
    "gws giants": "gws giants",
    "greater western sydney": "gws giants",
    "western bulldogs": "western bulldogs",
    "port adelaide power": "port adelaide",
    "geelong cats": "geelong",
    "north melbourne kangaroos": "north melbourne",
    "richmond tigers": "richmond",
    "carlton blues": "carlton",
    "st kilda saints": "st kilda",
    "essendon bombers": "essendon",
    "hawthorn hawks": "hawthorn",
    "collingwood magpies": "collingwood",
    "fremantle dockers": "fremantle",
    "adelaide crows": "adelaide",
}

def norm(name, aliases):
    n = name.lower().strip()
    return aliases.get(n, n)

# ── Load historical xlsx ─────────────────────────────────────────────────────
def load_hist(path, sport):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.worksheets[0]
    rows = list(ws.iter_rows(values_only=True))
    header = rows[1]
    col = {h: i for i, h in enumerate(header) if h}
    games = {}
    aliases = AFL_ALIASES if sport == "AFL" else NRL_ALIASES
    for row in rows[2:]:
        if not row[0] or not hasattr(row[0], 'year'):
            continue
        dt = row[0].date() if hasattr(row[0], 'date') else row[0]
        home = norm(str(row[col['Home Team']]), aliases)
        away = norm(str(row[col['Away Team']]), aliases)
        key = (dt, home, away)
        def g(c): return row[col[c]] if c in col and row[col[c]] is not None else None
        games[key] = {
            'home_score': g('Home Score'), 'away_score': g('Away Score'),
            'h2h_home_close': g('Home Odds Close'), 'h2h_away_close': g('Away Odds Close'),
            'h2h_home_open':  g('Home Odds Open'),  'h2h_away_open':  g('Away Odds Open'),
            'hcap_home_close': g('Home Line Close'), 'hcap_away_close': g('Away Line Close'),
            'hcap_home_odds_close': g('Home Line Odds Close'),
            'hcap_away_odds_close': g('Away Line Odds Close'),
            'hcap_home_open': g('Home Line Open'),  'hcap_away_open': g('Away Line Open'),
            'total_close': g('Total Score Close'),  'total_open': g('Total Score Open'),
            'total_over_close': g('Total Score Over Close'),
            'total_under_close': g('Total Score Under Close'),
        }
    return games, aliases

nrl_hist, nrl_alias = load_hist(
    r'C:\Users\ElliotBladen\Apps\data\nrl\historical\raw\nrl_20260512.xlsx', 'NRL')
afl_hist, afl_alias = load_hist(
    r'C:\Users\ElliotBladen\Apps\BettingEngine\outputs\afl_weekly_review\historical\latest.xlsx', 'AFL')

# ── Load actual bets ─────────────────────────────────────────────────────────
bets = []
with open(r'C:\Users\ElliotBladen\Apps\BettingEngine\data\bets\actual_bets_2026.csv', encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        if row.get('bet_id'):
            bets.append(row)

target = bets

# ── CLV calculator ───────────────────────────────────────────────────────────
results = []
for b in target:
    sport = b['sport']
    hist  = afl_hist if sport == 'AFL' else nrl_hist
    alias = afl_alias if sport == 'AFL' else nrl_alias
    placed_date = datetime.strptime(b['placed_date'], '%Y-%m-%d').date()
    home = norm(b['home_team'], alias)
    away = norm(b['away_team'], alias)

    # Try exact date, then ±1 day
    game = None
    for delta in [0, -1, 1]:
        from datetime import timedelta
        key = (placed_date + timedelta(days=delta), home, away)
        if key in hist:
            game = hist[key]
            break
        # also try swapped home/away (rare but safe)
        key2 = (placed_date + timedelta(days=delta), away, home)
        if key2 in hist:
            game = hist[key2]
            home, away = away, home  # swap for this bet
            break

    market   = b['market_type']
    sel      = b['selection']
    odds     = float(b['odds_taken'])
    line     = float(b['line']) if b['line'] else None
    stake    = float(b['stake'])
    pnl      = float(b['pnl'])
    result   = b['result']

    clv = clv_line = None
    close_odds = close_line = open_line = None
    line_move = None

    if game:
        if market == 'h2h':
            sel_norm = norm(sel, alias)
            if sel_norm == home:
                close_odds = game['h2h_home_close']
                open_odds  = game['h2h_home_open']
            else:
                close_odds = game['h2h_away_close']
                open_odds  = game['h2h_away_open']
            if close_odds:
                clv = round((odds / close_odds - 1) * 100, 2)

        elif market == 'handicap':
            sel_norm = norm(sel, alias)
            if sel_norm == home:
                close_line = game['hcap_home_close']
                open_line  = game['hcap_home_open']
                close_odds = game['hcap_home_odds_close']
            else:
                close_line = game['hcap_away_close']
                open_line  = game['hcap_away_open']
                close_odds = game['hcap_away_odds_close']
            if close_line is not None and line is not None:
                clv_line = round(line - close_line, 1)
                if open_line is not None:
                    line_move = round(open_line - close_line, 1)
            if close_odds:
                clv = round((odds / close_odds - 1) * 100, 2)

        elif market == 'total':
            close_line = game['total_close']
            open_line  = game['total_open']
            if sel.lower() == 'under':
                close_odds = game['total_under_close']
                if close_line and line:
                    clv_line = round(line - close_line, 1)
            else:
                close_odds = game['total_over_close']
                if close_line and line:
                    clv_line = round(close_line - line, 1)
            if open_line and close_line:
                line_move = round(open_line - close_line, 1)
            if close_odds:
                clv = round((odds / close_odds - 1) * 100, 2)

    results.append({
        'bet_id': b['bet_id'], 'sport': sport, 'round': b['round'],
        'match': f"{b['home_team']} v {b['away_team']}",
        'market': market, 'selection': sel, 'line': line,
        'odds_taken': odds, 'close_odds': close_odds, 'close_line': close_line,
        'open_line': open_line, 'line_move': line_move,
        'clv_pct': clv, 'clv_line': clv_line,
        'result': result, 'pnl': pnl,
        'game_found': game is not None,
    })

# ── Print results ─────────────────────────────────────────────────────────────
print("=" * 90)
print(f"{'MANUAL CLV — AFL R9 + NRL R11':^90}")
print("=" * 90)

for r in results:
    tag = "✓" if r['result'] == 'win' else "✗"
    print(f"\n{tag} {r['bet_id']}  {r['sport']} R{r['round']}  {r['match']}")
    print(f"  Market: {r['market']:10s}  Selection: {r['selection']}  Line: {r['line']}  Odds taken: {r['odds_taken']}")
    if not r['game_found']:
        print("  ⚠ Could not match game in historical data")
        continue
    if r['market'] == 'h2h':
        print(f"  Closing H2H: {r['close_odds']}  →  CLV: {r['clv_pct']:+.1f}% ({'beat close' if r['clv_pct'] and r['clv_pct'] > 0 else 'missed close'})")
    elif r['market'] == 'handicap':
        move_desc = ""
        if r['line_move'] is not None:
            if r['line_move'] > 0: move_desc = f"line eased {r['line_move']:+.1f} pts (market less confident)"
            elif r['line_move'] < 0: move_desc = f"line tightened {r['line_move']:+.1f} pts (market more confident)"
            else: move_desc = "line unchanged"
        print(f"  Open line: {r['open_line']}  Close line: {r['close_line']}  {move_desc}")
        print(f"  You took: {r['line']}  vs close {r['close_line']}  →  Line CLV: {r['clv_line']:+.1f} pts  Odds CLV: {r['clv_pct']:+.1f}%")
    elif r['market'] == 'total':
        move_desc = ""
        if r['line_move'] is not None:
            if r['line_move'] > 0: move_desc = f"total rose {r['line_move']:+.1f} (more scoring expected)"
            elif r['line_move'] < 0: move_desc = f"total fell {r['line_move']:+.1f} (less scoring expected)"
            else: move_desc = "total unchanged"
        print(f"  Open total: {r['open_line']}  Close total: {r['close_line']}  {move_desc}")
        print(f"  You took: {r['selection']} {r['line']}  vs close {r['close_line']}  →  Line CLV: {r['clv_line']:+.1f} pts  Odds CLV: {r['clv_pct']:+.1f}%")
    print(f"  Result: {r['result'].upper():4s}  P&L: ${r['pnl']:+.2f}")

# ── Summary ───────────────────────────────────────────────────────────────────
print("\n" + "=" * 90)
print("SUMMARY")
print("=" * 90)
beat_close = [r for r in results if r['clv_pct'] and r['clv_pct'] > 0]
beat_line  = [r for r in results if r['clv_line'] and r['clv_line'] > 0]
avg_clv    = sum(r['clv_pct'] for r in results if r['clv_pct'] is not None) / max(1, len([r for r in results if r['clv_pct']]))
print(f"  Bets: {len(results)}  |  Beat closing odds: {len(beat_close)}/{len(results)}  |  Beat closing line: {len(beat_line)}/{len([r for r in results if r['clv_line'] is not None])}")
print(f"  Avg CLV vs close: {avg_clv:+.2f}%")
total_pnl = sum(r['pnl'] for r in results)
total_stake = sum(abs(float(b['stake'])) for b in target)
print(f"  P&L: ${total_pnl:+.2f}  |  Stake: ${total_stake:.0f}  |  ROI: {total_pnl/total_stake*100:+.1f}%")

# ── Running CLV by round ──────────────────────────────────────────────────
print("\n" + "=" * 90)
print("RUNNING CLV BY ROUND")
print("=" * 90)
print(f"  {'Round':12s} {'Bets':>4} {'W-L':>6} {'Beat Close':>10} {'Avg CLV':>9} {'Cum CLV':>9} {'P&L':>9} {'ROI':>7}")
print("  " + "-" * 72)

from collections import defaultdict
rounds_order = sorted(set((r['sport'], int(r['round'])) for r in results))
cum_clv_sum = 0; cum_clv_n = 0; cum_pnl = 0; cum_stake = 0

for sport, rnd in rounds_order:
    rr = [r for r in results if r['sport'] == sport and int(r['round']) == rnd]
    clvs   = [r['clv_pct'] for r in rr if r['clv_pct'] is not None]
    beat   = sum(1 for c in clvs if c > 0)
    wins   = sum(1 for r in rr if r['result'] == 'win')
    losses = sum(1 for r in rr if r['result'] == 'loss')
    pnl    = sum(r['pnl'] for r in rr)
    stake  = sum(float(b['stake']) for b in target if b['sport'] == sport and int(b['round']) == rnd)
    roi    = pnl / stake * 100 if stake else 0
    avg_clv = sum(clvs) / len(clvs) if clvs else 0
    cum_clv_sum += sum(clvs); cum_clv_n += len(clvs)
    cum_pnl += pnl; cum_stake += stake
    cum_clv = cum_clv_sum / cum_clv_n if cum_clv_n else 0
    print(f"  {sport+' R'+str(rnd):12s} {len(rr):>4} {str(wins)+'-'+str(losses):>6} {str(beat)+'/'+str(len(clvs)):>10} {avg_clv:>+8.2f}% {cum_clv:>+8.2f}% {pnl:>+8.2f} {roi:>+6.1f}%")

print("  " + "-" * 72)
cum_roi = cum_pnl / cum_stake * 100 if cum_stake else 0
cum_avg = cum_clv_sum / cum_clv_n if cum_clv_n else 0
wins_all = sum(1 for r in results if r['result'] == 'win')
losses_all = sum(1 for r in results if r['result'] == 'loss')
beat_all = sum(1 for r in results if r['clv_pct'] and r['clv_pct'] > 0)
clv_n_all = sum(1 for r in results if r['clv_pct'] is not None)
print(f"  {'TOTAL':12s} {len(results):>4} {str(wins_all)+'-'+str(losses_all):>6} {str(beat_all)+'/'+str(clv_n_all):>10} {cum_avg:>+8.2f}% {cum_avg:>+8.2f}% {cum_pnl:>+8.2f} {cum_roi:>+6.1f}%")

# ── Save master CLV file ─────────────────────────────────────────────────
import os
master_file = r'C:\Users\ElliotBladen\Apps\BettingEngine\outputs\clv_running\actual_bets_clv_2026.csv'
fields = ['bet_id','sport','round','match','market','selection','line','odds_taken',
          'close_line','open_line','line_move','close_odds','clv_pct','clv_line','result','pnl']
with open(master_file, 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
    w.writeheader(); w.writerows(results)
print(f"\n  Saved master: {os.path.basename(master_file)}")
