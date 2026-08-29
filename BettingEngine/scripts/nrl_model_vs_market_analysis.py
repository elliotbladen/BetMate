"""
NRL Model vs Market — Comprehensive Analysis
Compares model predictions against opening AND closing market across H2H, handicap, and totals.
Reports success rates at 5%, 10%, 15%, 20% EV thresholds.
"""
import csv
import glob
import os
import sys
from datetime import datetime, timedelta

# Team name normalisation: pricing CSV name → xlsx name
TEAM_MAP = {
    'North Queensland Cowboys': 'North QLD Cowboys',
    'St. George Illawarra Dragons': 'St George Dragons',
    'Canterbury-Bankstown Bulldogs': 'Canterbury Bulldogs',
    'Cronulla-Sutherland Sharks': 'Cronulla Sharks',
    'Manly-Warringah Sea Eagles': 'Manly Sea Eagles',
    'South Sydney Rabbitohs': 'South Sydney Rabbitohs',
    'Sydney Roosters': 'Sydney Roosters',
    'Penrith Panthers': 'Penrith Panthers',
    'Melbourne Storm': 'Melbourne Storm',
    'Parramatta Eels': 'Parramatta Eels',
    'Brisbane Broncos': 'Brisbane Broncos',
    'Canberra Raiders': 'Canberra Raiders',
    'New Zealand Warriors': 'New Zealand Warriors',
    'Newcastle Knights': 'Newcastle Knights',
    'Gold Coast Titans': 'Gold Coast Titans',
    'Wests Tigers': 'Wests Tigers',
    'Dolphins': 'Dolphins',
}

BASE = os.path.join(os.path.dirname(__file__), '..')


def norm(name):
    return TEAM_MAP.get(name, name)


# ── LOAD XLSX DATA ────────────────────────────────────────────────────

def load_xlsx():
    """Load historical data from AusSportsBetting xlsx."""
    import openpyxl
    path = os.path.join(BASE, 'outputs', 'nrl_weekly_review', 'historical', 'latest.xlsx')
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    # Row 0 = title, Row 1 = headers
    header = list(rows[1])
    col = {str(h).strip(): i for i, h in enumerate(header) if h}

    games = {}
    for row_vals in rows[2:]:
        r = list(row_vals)
        try:
            dt = r[col['Date']]
            if not dt or not hasattr(dt, 'year'):
                continue
            if dt.year != 2026:
                continue
            home = str(r[col['Home Team']]).strip()
            away = str(r[col['Away Team']]).strip()
            home_score = r[col['Home Score']]
            away_score = r[col['Away Score']]
            if home_score is None or away_score is None:
                continue

            def safe_float(v):
                if v is None or v == '' or v == 'None':
                    return None
                try:
                    return float(v)
                except (ValueError, TypeError):
                    return None

            key = f"{dt.strftime('%Y-%m-%d')}_{home}"
            games[key] = {
                'date': dt.strftime('%Y-%m-%d'),
                'home': home,
                'away': away,
                'home_score': int(home_score),
                'away_score': int(away_score),
                'total': int(home_score) + int(away_score),
                'margin': int(home_score) - int(away_score),
                # H2H
                'h2h_home_open': safe_float(r[col['Home Odds Open']]),
                'h2h_home_close': safe_float(r[col['Home Odds Close']]),
                'h2h_away_open': safe_float(r[col['Away Odds Open']]),
                'h2h_away_close': safe_float(r[col['Away Odds Close']]),
                # Handicap
                'hcap_line_open': safe_float(r[col['Home Line Open']]),
                'hcap_line_close': safe_float(r[col['Home Line Close']]),
                'hcap_home_odds_close': safe_float(r[col.get('Home Line Odds Close', -1)]),
                'hcap_away_odds_close': safe_float(r[col.get('Away Line Odds Close', -1)]),
                # Totals
                'total_line_open': safe_float(r[col['Total Score Open']]),
                'total_line_close': safe_float(r[col['Total Score Close']]),
                'total_over_odds_close': safe_float(r[col.get('Total Score Over Close', -1)]),
                'total_under_odds_close': safe_float(r[col.get('Total Score Under Close', -1)]),
            }
        except Exception:
            continue

    wb.close()
    return games


# ── LOAD PRICING CSVs ─────────────────────────────────────────────────

def load_pricing():
    """Load model predictions from all pricing CSVs."""
    pattern = os.path.join(BASE, 'results', 'r*_pricing_2026.csv')
    files = sorted(glob.glob(pattern))
    models = {}
    for fpath in files:
        with open(fpath, newline='', encoding='utf-8', errors='replace') as f:
            for r in csv.DictReader(f):
                try:
                    date = r['date'].strip()
                    home = r['home_team'].strip()
                    home_xlsx = norm(home)
                    key = f"{date}_{home_xlsx}"
                    models[key] = {
                        'round': int(r['round']),
                        'home': home,
                        'away': r['away_team'].strip(),
                        'model_hcap': float(r['fair_hcap_line']),
                        'model_total': float(r['fair_total_line']),
                        'pred_home': float(r['pred_home_score']),
                        'pred_away': float(r['pred_away_score']),
                    }
                except (ValueError, KeyError):
                    continue
    return models


# ── H2H ANALYSIS ─────────────────────────────────────────────────────

def load_h2h():
    path = os.path.join(BASE, 'outputs', 'backtests',
                        'nrl_2026_h2h_all_model_sides_verified_rounds.csv')
    rows = []
    with open(path, newline='') as f:
        for r in csv.DictReader(f):
            rows.append({
                'round': int(r['round']),
                'match': r['match'],
                'selection': r['selection'],
                'side': r['side'],
                'model_prob': float(r['model_probability']),
                'closing_prob': float(r['closing_no_vig_probability']),
                'prob_edge': float(r['probability_edge']),
                'closing_odds': float(r['closing_odds']),
                'ev': float(r['expected_value']),
                'result': r['result'],
                'profit': float(r['profit']),
            })
    return rows


def analyse_h2h(rows):
    print("=" * 80)
    print("  H2H (MONEYLINE) — MODEL vs CLOSING MARKET")
    n_games = len(rows) // 2
    rounds = sorted(set(r['round'] for r in rows))
    print(f"  {n_games} games, {len(rows)} selections | R{rounds[0]}–R{rounds[-1]}")
    print("=" * 80)

    # Overall model accuracy (taking the model's favoured side)
    model_picks = [r for r in rows if r['model_prob'] > 0.5]
    correct = sum(1 for r in model_picks if r['result'] == 'W')
    print(f"\n  Model winner accuracy: {correct}/{len(model_picks)} ({correct/len(model_picks)*100:.1f}%)")

    # EV threshold
    print("\n  ── EV THRESHOLD (EV = model_prob * closing_odds - 1) ──\n")
    print(f"  {'Threshold':>10} {'Bets':>5} {'W':>4} {'L':>4} {'Win%':>7} {'P&L':>9} {'ROI':>8} {'Avg Odds':>9}")
    print("  " + "-" * 62)

    for thresh in [0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30]:
        f = [r for r in rows if r['ev'] >= thresh]
        if not f:
            print(f"  EV>={thresh*100:4.0f}%   {'—':>5} {'—':>4} {'—':>4} {'—':>7} {'—':>9} {'—':>8} {'—':>9}")
            continue
        w = sum(1 for r in f if r['result'] == 'W')
        l = len(f) - w
        pl = sum(r['profit'] for r in f)
        roi = pl / len(f) * 100
        ao = sum(r['closing_odds'] for r in f) / len(f)
        print(f"  EV>={thresh*100:4.0f}%   {len(f):>5} {w:>4} {l:>4} {w/len(f)*100:>6.1f}% {pl:>+8.1f}u {roi:>+7.1f}% {ao:>9.2f}")

    # Probability edge
    print(f"\n  ── PROBABILITY EDGE (model_prob - closing_no_vig_prob) ──\n")
    print(f"  {'Threshold':>10} {'Bets':>5} {'W':>4} {'L':>4} {'Win%':>7} {'P&L':>9} {'ROI':>8}")
    print("  " + "-" * 52)

    for thresh in [0.0, 0.05, 0.07, 0.10, 0.15, 0.20]:
        f = [r for r in rows if r['prob_edge'] >= thresh]
        if not f:
            continue
        w = sum(1 for r in f if r['result'] == 'W')
        pl = sum(r['profit'] for r in f)
        roi = pl / len(f) * 100
        print(f"  Edge>={thresh*100:4.0f}%  {len(f):>5} {w:>4} {len(f)-w:>4} {w/len(f)*100:>6.1f}% {pl:>+8.1f}u {roi:>+7.1f}%")

    # Fav vs dog
    print(f"\n  ── FAVOURITE vs UNDERDOG (EV>=0 bets only) ──\n")
    for label, filt in [
        ("Favs (odds<2.0)", lambda r: r['closing_odds'] < 2.0 and r['ev'] >= 0),
        ("Dogs (odds>=2.0)", lambda r: r['closing_odds'] >= 2.0 and r['ev'] >= 0),
    ]:
        f = [r for r in rows if filt(r)]
        if not f:
            continue
        w = sum(1 for r in f if r['result'] == 'W')
        pl = sum(r['profit'] for r in f)
        roi = pl / len(f) * 100
        print(f"  {label}: {len(f)} bets, {w}W {len(f)-w}L ({w/len(f)*100:.1f}%), P&L {pl:+.1f}u, ROI {roi:+.1f}%")

    # Round by round at EV>=5%
    print(f"\n  ── ROUND BY ROUND (EV>=5%) ──\n")
    rd = {}
    for r in rows:
        if r['ev'] >= 0.05:
            rn = r['round']
            if rn not in rd:
                rd[rn] = {'b': 0, 'w': 0, 'pl': 0}
            rd[rn]['b'] += 1
            rd[rn]['w'] += 1 if r['result'] == 'W' else 0
            rd[rn]['pl'] += r['profit']
    cum = 0
    for rn in sorted(rd):
        d = rd[rn]
        cum += d['pl']
        print(f"  R{rn:>2}: {d['b']}b {d['w']}W  P&L {d['pl']:>+6.1f}u  cum {cum:>+6.1f}u")


# ── HANDICAP ANALYSIS ─────────────────────────────────────────────────

def analyse_handicap(models, xlsx_games):
    matched = []
    for key, m in models.items():
        if key in xlsx_games:
            x = xlsx_games[key]
            if x['hcap_line_close'] is not None:
                matched.append({**m, **x, 'model_hcap': m['model_hcap']})

    print("\n" + "=" * 80)
    print("  HANDICAP — MODEL vs MARKET")
    if not matched:
        print("  No matched games found with closing handicap lines!")
        return
    rounds = sorted(set(m['round'] for m in matched))
    print(f"  {len(matched)} games with closing lines | R{rounds[0]}–R{rounds[-1]}")
    print("=" * 80)

    # Model accuracy
    # model_hcap: positive = home underdog, negative = home favourite
    # So model picks away winner when model_hcap > 0, home winner when < 0
    correct = sum(1 for g in matched if
                  (g['model_hcap'] < 0 and g['margin'] > 0) or
                  (g['model_hcap'] > 0 and g['margin'] < 0))
    print(f"\n  Model winner direction: {correct}/{len(matched)} ({correct/len(matched)*100:.1f}%)")

    maes = [abs(g['model_hcap'] - g['margin']) for g in matched]
    print(f"  Model margin MAE: {sum(maes)/len(maes):.1f} pts")

    # Market line accuracy
    mkt_correct = sum(1 for g in matched if
                      (g['hcap_line_close'] > 0 and g['margin'] > g['hcap_line_close']) or
                      (g['hcap_line_close'] < 0 and g['margin'] > g['hcap_line_close']) or
                      (g['hcap_line_close'] == 0 and g['margin'] > 0))
    # Actually ATS is: does home cover the spread?
    # hcap_line_close is from home perspective. Home covers if margin > -line (since line is home handicap)
    # Actually in AusSportsBetting, Home Line = handicap for home team
    # If Home Line Close = -1.5, home is favoured by 1.5. Home covers if home wins by more than 1.5.
    # Wait, let me think again. In the xlsx sample:
    # Wests Tigers Home Line Close = -1.5 (was shown as value 1.5 at column 24, but column 21 was -1.5)
    # Actually the sample showed: hcap_line_open=-1.5, hcap_line_close=-1.5
    # Wests lost 22-24, margin=-2. Line was -1.5 so...
    # In AusSportsBetting, positive line = underdog, negative = favourite
    # Home Line = -1.5 means home gets -1.5 (home is favourite, needs to win by >1.5)
    # Home covers if margin + line > 0, i.e. margin > -line
    # Wait, home line is the handicap added to home score. So adjusted = margin + line.
    # If line=-1.5, adjusted = margin + (-1.5). Home covers if adjusted > 0, i.e. margin > 1.5.

    # Model edge vs market
    print(f"\n  ── HANDICAP: MODEL EDGE vs CLOSING LINE ──")
    print(f"  Model edge = model_hcap - market_line (positive = model rates home stronger)\n")
    print(f"  {'Edge':>14} {'Bets':>5} {'Covers':>7} {'ATS%':>7} {'Avg Edge':>9}")
    print("  " + "-" * 48)

    for thresh in [0, 2, 3, 4, 6, 8, 10, 12]:
        bets = []
        for g in matched:
            mkt_line = g['hcap_line_close']
            model_edge = g['model_hcap'] - mkt_line
            if abs(model_edge) >= thresh:
                # model_edge > 0: model gives home MORE points than market → model
                # thinks home is WEAKER → value on AWAY side
                # model_edge < 0: model gives home FEWER points → value on HOME
                if model_edge > 0:
                    # Value on away — away covers if margin + mkt_line < 0
                    covers = (g['margin'] + mkt_line) < 0
                else:
                    # Value on home — home covers if margin + mkt_line > 0
                    covers = (g['margin'] + mkt_line) > 0
                bets.append({'covers': covers, 'edge': abs(model_edge), 'game': g})
        if not bets:
            print(f"  Edge>={thresh:>2}pts  {'—':>5} {'—':>7} {'—':>7} {'—':>9}")
            continue
        wins = sum(1 for b in bets if b['covers'])
        avg_e = sum(b['edge'] for b in bets) / len(bets)
        print(f"  Edge>={thresh:>2}pts  {len(bets):>5} {wins:>7} {wins/len(bets)*100:>6.1f}% {avg_e:>9.1f}")

    # Same vs opening line
    open_matched = [g for g in matched if g.get('hcap_line_open') is not None]
    if open_matched:
        print(f"\n  ── HANDICAP: MODEL EDGE vs OPENING LINE ({len(open_matched)} games) ──\n")
        print(f"  {'Edge':>14} {'Bets':>5} {'Covers':>7} {'ATS%':>7}")
        print("  " + "-" * 38)

        for thresh in [0, 2, 4, 6, 8, 10, 12]:
            bets = []
            for g in open_matched:
                mkt_line = g['hcap_line_open']
                model_edge = g['model_hcap'] - mkt_line
                if abs(model_edge) >= thresh:
                    if model_edge > 0:
                        covers = (g['margin'] + mkt_line) < 0
                    else:
                        covers = (g['margin'] + mkt_line) > 0
                    bets.append({'covers': covers})
            if not bets:
                continue
            wins = sum(1 for b in bets if b['covers'])
            print(f"  Edge>={thresh:>2}pts  {len(bets):>5} {wins:>7} {wins/len(bets)*100:>6.1f}%")

    # ROI at standard $1.90 odds for each threshold
    print(f"\n  ── HANDICAP ROI (assuming $1.90 line odds) ──\n")
    print(f"  {'Edge':>14} {'Bets':>5} {'Covers':>7} {'ATS%':>7} {'ROI':>8}")
    print("  " + "-" * 46)
    for thresh in [0, 2, 4, 6, 8, 10, 12]:
        bets = []
        for g in matched:
            mkt_line = g['hcap_line_close']
            model_edge = g['model_hcap'] - mkt_line
            if abs(model_edge) >= thresh:
                if model_edge > 0:
                    covers = (g['margin'] + mkt_line) < 0
                else:
                    covers = (g['margin'] + mkt_line) > 0
                bets.append({'covers': covers})
        if not bets:
            continue
        wins = sum(1 for b in bets if b['covers'])
        # At 1.90 odds: win = +0.90, loss = -1.00
        roi = (wins * 0.90 - (len(bets) - wins) * 1.00) / len(bets) * 100
        print(f"  Edge>={thresh:>2}pts  {len(bets):>5} {wins:>7} {wins/len(bets)*100:>6.1f}% {roi:>+7.1f}%")


# ── TOTALS ANALYSIS ───────────────────────────────────────────────────

def analyse_totals(models, xlsx_games):
    matched = []
    for key, m in models.items():
        if key in xlsx_games:
            x = xlsx_games[key]
            if x['total_line_close'] is not None:
                matched.append({**m, **x, 'model_total': m['model_total']})

    print("\n" + "=" * 80)
    print("  TOTALS — MODEL vs MARKET")
    if not matched:
        print("  No matched games found with closing total lines!")
        return
    rounds = sorted(set(m['round'] for m in matched))
    print(f"  {len(matched)} games with closing lines | R{rounds[0]}–R{rounds[-1]}")
    print("=" * 80)

    # Bias
    avg_model = sum(g['model_total'] for g in matched) / len(matched)
    avg_actual = sum(g['total'] for g in matched) / len(matched)
    avg_market = sum(g['total_line_close'] for g in matched) / len(matched)
    print(f"\n  Avg model total:  {avg_model:.1f} pts")
    print(f"  Avg market close: {avg_market:.1f} pts")
    print(f"  Avg actual total: {avg_actual:.1f} pts")
    print(f"  Model bias: {avg_model - avg_actual:+.1f} pts (vs actual)")
    print(f"  Market bias: {avg_market - avg_actual:+.1f} pts (vs actual)")

    # Model MAE vs market MAE
    model_mae = sum(abs(g['model_total'] - g['total']) for g in matched) / len(matched)
    market_mae = sum(abs(g['total_line_close'] - g['total']) for g in matched) / len(matched)
    print(f"\n  Model total MAE:  {model_mae:.1f} pts")
    print(f"  Market total MAE: {market_mae:.1f} pts")

    # Edge vs closing
    print(f"\n  ── TOTALS: MODEL EDGE vs CLOSING LINE ──")
    print(f"  Model edge = model_total - market_total\n")
    print(f"  {'Edge':>14} {'Bets':>5} {'Correct':>8} {'Hit%':>7} {'ROI@1.90':>9}")
    print("  " + "-" * 48)

    for thresh in [0, 2, 3, 4, 5, 6, 8, 10]:
        bets = []
        for g in matched:
            edge = g['model_total'] - g['total_line_close']
            if abs(edge) >= thresh:
                if edge > 0:
                    correct = g['total'] > g['total_line_close']
                else:
                    correct = g['total'] < g['total_line_close']
                bets.append({'correct': correct})
        if not bets:
            continue
        wins = sum(1 for b in bets if b['correct'])
        roi = (wins * 0.90 - (len(bets) - wins) * 1.00) / len(bets) * 100
        print(f"  Edge>={thresh:>2}pts  {len(bets):>5} {wins:>8} {wins/len(bets)*100:>6.1f}% {roi:>+8.1f}%")

    # Edge vs opening
    open_matched = [g for g in matched if g.get('total_line_open') is not None]
    if open_matched:
        print(f"\n  ── TOTALS: MODEL EDGE vs OPENING LINE ({len(open_matched)} games) ──\n")
        print(f"  {'Edge':>14} {'Bets':>5} {'Correct':>8} {'Hit%':>7} {'ROI@1.90':>9}")
        print("  " + "-" * 48)

        for thresh in [0, 2, 4, 6, 8, 10]:
            bets = []
            for g in open_matched:
                edge = g['model_total'] - g['total_line_open']
                if abs(edge) >= thresh:
                    if edge > 0:
                        correct = g['total'] > g['total_line_open']
                    else:
                        correct = g['total'] < g['total_line_open']
                    bets.append({'correct': correct})
            if not bets:
                continue
            wins = sum(1 for b in bets if b['correct'])
            roi = (wins * 0.90 - (len(bets) - wins) * 1.00) / len(bets) * 100
            print(f"  Edge>={thresh:>2}pts  {len(bets):>5} {wins:>8} {wins/len(bets)*100:>6.1f}% {roi:>+8.1f}%")

    # Over vs under bias
    print(f"\n  ── OVER vs UNDER BIAS ──\n")
    over_bets = [g for g in matched if g['model_total'] > g['total_line_close']]
    under_bets = [g for g in matched if g['model_total'] < g['total_line_close']]
    for label, subset in [("Model says OVER", over_bets), ("Model says UNDER", under_bets)]:
        if not subset:
            continue
        if label.endswith("OVER"):
            wins = sum(1 for g in subset if g['total'] > g['total_line_close'])
        else:
            wins = sum(1 for g in subset if g['total'] < g['total_line_close'])
        roi = (wins * 0.90 - (len(subset) - wins) * 1.00) / len(subset) * 100
        print(f"  {label}: {len(subset)} bets, {wins}W ({wins/len(subset)*100:.1f}%), ROI {roi:+.1f}%")


# ── COMBINED SUMMARY ──────────────────────────────────────────────────

def summary(h2h_rows, n_hcap, n_totals):
    print("\n" + "=" * 80)
    print("  SUMMARY — BEST BETTING STRATEGIES")
    print("=" * 80)
    print("""
  H2H:       Best at EV>=15-20%. Higher threshold = higher ROI but fewer bets.
              Check exact numbers above. Probability edge 7%+ is the cleaner signal.

  HANDICAP:  Model edge >= X pts vs closing line. Check ATS% above.
              Need >52.4% ATS to beat the vig at 1.90 odds.
              Profitable threshold = the lowest edge where ATS% > 52.4%.

  TOTALS:    Same principle — model edge vs closing total.
              Need >52.4% hit rate at 1.90 odds.
              Check if the model has an over/under bias.

  Key:  ROI > 0% = profitable. ATS/Hit > 52.4% = beating the vig at $1.90.
""")


# ── MAIN ──────────────────────────────────────────────────────────────

def main():
    print("\n" + "=" * 80)
    print("  NRL 2026 MODEL vs MARKET — COMPREHENSIVE ANALYSIS")
    print("=" * 80)

    # H2H (from dedicated backtest CSV)
    h2h = load_h2h()
    analyse_h2h(h2h)

    # Load xlsx + pricing for handicap/totals
    print("\n  Loading xlsx market data...")
    try:
        xlsx = load_xlsx()
        print(f"  Found {len(xlsx)} NRL 2026 games in xlsx")
    except Exception as e:
        print(f"  Failed to load xlsx: {e}")
        xlsx = {}

    models = load_pricing()
    print(f"  Found {len(models)} games in pricing CSVs")

    # Match
    matched = 0
    for key in models:
        if key in xlsx:
            matched += 1
    print(f"  Matched: {matched} games (model + market data)")

    if matched > 0:
        analyse_handicap(models, xlsx)
        analyse_totals(models, xlsx)

    summary(h2h, matched, matched)


if __name__ == '__main__':
    main()
