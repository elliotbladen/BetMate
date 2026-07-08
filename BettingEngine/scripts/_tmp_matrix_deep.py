"""
Full matrix analysis: Manly (HOME) vs South Sydney (AWAY)
Hypothetical game — Thursday 4 June 2026, 20:00, 4 Pines Park (Brookvale Oval)
"""
import sys, sqlite3, re, openpyxl, csv, math
from datetime import date, datetime, timedelta
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.stdout.reconfigure(encoding='utf-8')

OUTPUTS = Path('outputs')

def parse_edge(val):
    if not val: return None
    s = str(val).strip()
    if s in ('--', '-', '', 'None', 'nan', '—'): return None
    m = re.match(r'^([\d.]+)%\s+(.+)$', s)
    if not m: return None
    return float(m.group(1)), m.group(2).strip()

def load_xlsx_matrix(path):
    wb = openpyxl.load_workbook(path)
    result = {}
    for sheet in wb.sheetnames:
        ws = wb[sheet]
        rows = list(ws.iter_rows(values_only=True))
        data = {}
        for row in rows[2:]:
            cat = row[0]; raw = row[4] if len(row) > 4 else None
            if not cat: continue
            data[str(cat)] = parse_edge(raw)
        result[sheet] = data
    return result

def load_handicap_csv(path):
    from collections import defaultdict
    result = defaultdict(dict)
    with open(path, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            result[row.get('team','').strip()][row.get('category','').strip()] = parse_edge(row.get('edge','').strip())
    return dict(result)

def get_moon_phase_row(game_date):
    try:
        import ephem
        d = ephem.Date(game_date.strftime('%Y/%m/%d 12:00:00'))
        prev_new  = ephem.previous_new_moon(d);  next_new  = ephem.next_new_moon(d)
        prev_full = ephem.previous_full_moon(d); next_full = ephem.next_full_moon(d)
        cn = min(abs(float(d)-float(prev_new)),  abs(float(next_new) -float(d)))
        cf = min(abs(float(d)-float(prev_full)), abs(float(next_full)-float(d)))
        if cn <= 1.0: return 'New Moon (±1 day)', cn
        if cf <= 1.0: return 'Full Moon (±1 day)', cf
        return None, min(cn, cf)
    except Exception as e:
        return None, None

MONTH_LABELS = {3:'March',4:'April',5:'May',6:'June',7:'July',
                8:'August',9:'September',10:'October',11:'November',12:'December'}

def applicable_row_names(hour, weekday, game_date, team_role,
                         home_key, away_key, venue, rest_days, last_result, generic_row):
    rows = [generic_row]
    rows.append('Night Games (kick-off ≥ 18:00)' if hour >= 18 else 'Day Games (kick-off < 18:00)')
    day_label = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'][weekday]
    rows.append('Thursday / Friday Games' if weekday in (3,4) else f'{day_label} Games')
    if rest_days is not None:
        if rest_days <= 6:   rows.append('Short Rest (≤ 6 days)')
        elif rest_days >= 10: rows.append('Long Rest (≥ 10 days)')
    if last_result == 'win':  rows.append('After a Win')
    elif last_result == 'loss': rows.append('After a Loss')
    ml = MONTH_LABELS.get(game_date.month)
    if ml: rows.append(ml)
    moon_row, _ = get_moon_phase_row(game_date)
    if moon_row: rows.append(moon_row)
    opp = away_key if team_role == 'home' else home_key
    rows.append(f'vs {opp}')
    rows.append(venue)
    return rows

def normalise(raw, role, market):
    d = raw.lower().strip()
    if market == 'h2h':
        is_wins = 'backing' in d
        return 'HOME_WIN' if (is_wins == (role=='home')) else 'AWAY_WIN'
    elif market == 'handicap':
        is_cov = 'covers' in d and 'fades' not in d
        if role=='home': return 'HOME_COVERS' if is_cov else 'AWAY_COVERS'
        else:            return 'AWAY_COVERS' if is_cov else 'HOME_COVERS'
    elif market == 'totals':
        if 'overs' in d: return 'OVERS'
        if 'unders' in d: return 'UNDERS'
    return None

# ── Get actual last results from DB ──────────────────────────────────────────
conn = sqlite3.connect('data/model.db')
conn.row_factory = sqlite3.Row

print("=== RECENT RESULTS (2026) ===")
last_info = {}
for tname, tkey in [('Manly', 'Manly'), ('South Sydney', 'Souths')]:
    rows = conn.execute("""
        SELECT m.round_number, m.match_date, t_h.team_name as home, t_a.team_name as away,
               r.home_score, r.away_score, m.home_team_id, m.away_team_id,
               (SELECT team_id FROM teams WHERE team_name LIKE ?) as tid
        FROM matches m
        JOIN teams t_h ON t_h.team_id = m.home_team_id
        JOIN teams t_a ON t_a.team_id = m.away_team_id
        LEFT JOIN results r ON r.match_id = m.match_id
        WHERE (t_h.team_name LIKE ? OR t_a.team_name LIKE ?)
          AND m.season = 2026
          AND r.home_score IS NOT NULL
        ORDER BY m.match_date DESC
        LIMIT 4
    """, (f'%{tname}%', f'%{tname}%', f'%{tname}%')).fetchall()
    print(f"\n{tname}:")
    for i, r in enumerate(rows):
        tid = conn.execute("SELECT team_id FROM teams WHERE team_name LIKE ?", (f'%{tname}%',)).fetchone()['team_id']
        is_home = (r['home_team_id'] == tid)
        my_score  = r['home_score'] if is_home else r['away_score']
        opp_score = r['away_score'] if is_home else r['home_score']
        won = my_score > opp_score
        role = 'HOME' if is_home else 'AWAY'
        print(f"  R{r['round_number']} {r['match_date']}  [{role}]  {r['home']} {r['home_score']}-{r['away_score']} {r['away']}  -> {'WIN' if won else 'LOSS'}")
        if i == 0:
            last_info[tkey] = {
                'last_result': 'win' if won else 'loss',
                'last_date': r['match_date'],
            }
conn.close()

# ── Game parameters ───────────────────────────────────────────────────────────
# R14 — Thu June 4 2026, 20:00 Thursday night
GAME_DATE    = date(2026, 6, 4)
KICKOFF_HOUR = 20
WEEKDAY      = GAME_DATE.weekday()
VENUE        = '4 Pines Park (Brookvale Oval)'
HOME_KEY     = 'Manly Sea Eagles'
AWAY_KEY     = 'South Sydney Rabbitohs'

# Rest days — Manly last played R13 Thu May 29. Souths — check
manly_last_date = date.fromisoformat(last_info['Manly']['last_date'][:10])
souths_last_date = date.fromisoformat(last_info['Souths']['last_date'][:10])
manly_rest  = (GAME_DATE - manly_last_date).days
souths_rest = (GAME_DATE - souths_last_date).days

print(f"\n\n=== GAME CONTEXT ===")
print(f"  Date:     {GAME_DATE}  ({['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][WEEKDAY]})")
print(f"  Kickoff:  {KICKOFF_HOUR}:00 ({'Night' if KICKOFF_HOUR >= 18 else 'Day'})")
print(f"  Venue:    {VENUE}")
moon_row, moon_dist = get_moon_phase_row(GAME_DATE)
print(f"  Moon:     {moon_row or 'None'} (dist={moon_dist:.2f}d)")
print(f"  Month:    {MONTH_LABELS[GAME_DATE.month]}")
print(f"\n  Manly  last game: {manly_last_date}  rest={manly_rest}d  last_result={last_info['Manly']['last_result']}")
print(f"  Souths last game: {souths_last_date}  rest={souths_rest}d  last_result={last_info['Souths']['last_result']}")

# ── Build applicable rows ─────────────────────────────────────────────────────
GENERIC_HOME = {'h2h': 'Win % — Home', 'handicap': 'Cover Rate — Home', 'totals': 'Total Points — Home'}
GENERIC_AWAY = {'h2h': 'Win % — Away', 'handicap': 'Cover Rate — Away', 'totals': 'Total Points — Away'}

print(f"\n=== APPLICABLE ROWS ===")
for market in ['h2h', 'handicap', 'totals']:
    home_rows = applicable_row_names(KICKOFF_HOUR, WEEKDAY, GAME_DATE, 'home',
                                     HOME_KEY, AWAY_KEY, VENUE,
                                     manly_rest, last_info['Manly']['last_result'],
                                     GENERIC_HOME[market])
    away_rows = applicable_row_names(KICKOFF_HOUR, WEEKDAY, GAME_DATE, 'away',
                                     HOME_KEY, AWAY_KEY, VENUE,
                                     souths_rest, last_info['Souths']['last_result'],
                                     GENERIC_AWAY[market])
    print(f"\n  {market.upper()} — Manly rows: {home_rows}")
    print(f"  {market.upper()} — Souths rows: {away_rows}")

# ── Load matrices and run full analysis ───────────────────────────────────────
print(f"\n\n{'='*72}")
print(f"  FULL MATRIX ANALYSIS")
print(f"{'='*72}")

h2h_m   = load_xlsx_matrix(OUTPUTS / 'nrl_h2h_matrix.xlsx')
tot_m   = load_xlsx_matrix(OUTPUTS / 'nrl_team_totals_matrix.xlsx')
hcap_m  = load_handicap_csv(OUTPUTS / 'nrl_handicap_matrix.csv')

matrices = [
    ('h2h',      h2h_m,  GENERIC_HOME['h2h'],   GENERIC_AWAY['h2h']),
    ('handicap', hcap_m, GENERIC_HOME['handicap'], GENERIC_AWAY['handicap']),
    ('totals',   tot_m,  GENERIC_HOME['totals'],   GENERIC_AWAY['totals']),
]

from collections import defaultdict
all_results = {}

for market, matrix, home_generic, away_generic in matrices:
    buckets = defaultdict(list)
    print(f"\n  --- {market.upper()} ---")

    for team_key, team_label, role, generic, rest, form in [
        (HOME_KEY, 'Manly',  'home', home_generic, manly_rest,  last_info['Manly']['last_result']),
        (AWAY_KEY, 'Souths', 'away', away_generic, souths_rest, last_info['Souths']['last_result']),
    ]:
        team_data = matrix.get(team_key, {})
        rows = applicable_row_names(KICKOFF_HOUR, WEEKDAY, GAME_DATE, role,
                                    HOME_KEY, AWAY_KEY, VENUE, rest, form, generic)
        print(f"\n  {team_label} ({role.upper()}) — {len(rows)} rows to check:")
        for row_name in rows:
            val = team_data.get(row_name)
            if val:
                edge_pct, raw_dir = val
                nd = normalise(raw_dir, role, market)
                print(f"    {'✓':2s} {edge_pct:5.1f}%  {raw_dir:<16}  [{nd}]  {row_name}")
                buckets[nd].append((edge_pct, row_name, team_label))
            else:
                raw_val = team_data.get(row_name)
                print(f"    {'—':2s}   —       —                          {row_name}  (no edge / missing)")

    # Confluence summary
    print(f"\n  {market.upper()} CONFLUENCE:")
    any_conf = False
    for direction, edges in sorted(buckets.items(), key=lambda x: -len(x[1])):
        n20 = [e for e in edges if e[0] >= 20.0]
        n10 = [e for e in edges if e[0] >= 10.0]
        n5  = [e for e in edges if e[0] >= 5.0]
        total = len(edges)
        if total >= 2:
            any_conf = True
            print(f"    {direction:<15}  {total} total edges  |  {len(n20)} ≥20%  |  {len(n10)} ≥10%  |  {len(n5)} ≥5%")
            for ep, rn, tl in sorted(edges, key=lambda x: -x[0]):
                flag = ' ⚡' if ep >= 20 else (' *' if ep >= 10 else '')
                print(f"      {ep:5.1f}%  {tl:<8}  {rn}{flag}")
    if not any_conf:
        print(f"    No 2+ directional confluence found")
    all_results[market] = dict(buckets)
