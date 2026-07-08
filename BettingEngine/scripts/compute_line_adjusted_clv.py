"""
compute_line_adjusted_clv.py

Replaces odds-only CLV with line-adjusted CLV for all handicap and totals bets.

MATHEMATICAL BASIS
==================
The closing standard line is set so P(cover) ≈ 50%. Actual outcomes are normally
distributed around the closing line's implied median with standard deviation σ.

  For HANDICAP bets (both home & away):
      z = (bet_line - close_line) / σ_margin
      P(cover) = Φ(z)

  For TOTALS UNDER bets:
      z = (bet_line - close_line) / σ_total
      P(hit) = Φ(z)

  For TOTALS OVER bets:
      z = (close_line - bet_line) / σ_total
      P(hit) = Φ(z)

  fair_close_odds = (1/P) / VIG_MULTIPLIER   [vig = 2/1.90 = 5.26%]
  CLV% = (taken_odds / fair_close_odds - 1) × 100

SIGMA VALUES (computed from historical xlsx data)
  NRL: σ_margin=17.30, σ_total=12.80  (n=962 games, 2020-2026)
  AFL: σ_margin=32.70, σ_total=27.49  (n=976 games, 2022-2026)

All values derived from AusSportsBetting closing lines vs actual results.
Mean bias ≈ 0 for both sports — closing lines are efficiently priced.
"""
import csv, math, shutil
from pathlib import Path

ROOT     = Path(__file__).resolve().parent.parent
CLV_FILE = ROOT / "data" / "clv" / "running" / "actual_bets_clv_2026.csv"

SIGMA = {
    'NRL': {'margin': 17.30, 'total': 12.80},
    'AFL': {'margin': 32.70, 'total': 27.49},
}
VIG_MULTIPLIER = 2 / 1.90  # standard 1.90/1.90 handicap market → 5.26% vig

def norm_cdf(x: float) -> float:
    return 0.5 * math.erfc(-x / math.sqrt(2))

def line_adj_close(bet_line: float, close_line: float, sigma: float, direction: str) -> tuple[float, float]:
    """Return (fair_close_odds_with_vig, P_win)."""
    if direction == 'handicap' or direction == 'under':
        z = (bet_line - close_line) / sigma
    else:  # 'over'
        z = (close_line - bet_line) / sigma
    P = norm_cdf(z)
    P = max(0.001, min(0.999, P))
    fair = (1.0 / P) / VIG_MULTIPLIER
    return round(fair, 3), round(P * 100, 1)

def process_row(row: dict) -> tuple | None:
    market    = row.get('market', '').lower().strip()
    selection = row.get('selection', '').lower().strip()
    sport     = row.get('sport', '').upper().strip()

    if market == 'h2h':
        return None
    if sport not in SIGMA:
        return None

    # parse numbers
    try:
        bet_line  = float(row['line'])
        close_line = float(row['close_line'])
        taken     = float(row['odds_taken'])
    except (ValueError, TypeError, KeyError):
        return None  # missing close_line → can't adjust

    if market == 'handicap':
        sigma  = SIGMA[sport]['margin']
        direction = 'handicap'
    elif market in ('total', 'totals'):
        sigma = SIGMA[sport]['total']
        if 'under' in selection:
            direction = 'under'
        elif 'over' in selection:
            direction = 'over'
        else:
            return None
    else:
        return None

    fair, P_pct = line_adj_close(bet_line, close_line, sigma, direction)
    clv = round((taken / fair - 1) * 100, 2)
    return fair, clv, P_pct

def main():
    with open(CLV_FILE, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    changes = []
    for row in rows:
        result = process_row(row)
        if result is None:
            continue
        new_close, new_clv, P_pct = result
        old_close = row['close_odds']
        old_clv   = row['clv_pct']
        row['close_odds'] = str(new_close)
        row['clv_pct']    = str(new_clv)
        changes.append((row['bet_id'], row['sport'], row['market'], row['selection'],
                        row['line'], row['close_line'], old_close, str(new_close),
                        old_clv, str(new_clv), P_pct))

    backup = CLV_FILE.with_suffix('.csv.bak')
    shutil.copy(CLV_FILE, backup)

    with open(CLV_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Updated {len(changes)} bets. Backup -> {backup.name}\n")
    hdr = f"{'ID':<12} {'SP':<3} {'Mkt':<8} {'Sel':<30} {'Line':>6} {'Close':>7} {'OldOdds':>8} {'NewOdds':>8} {'OldCLV%':>8} {'NewCLV%':>8} {'P%':>5}"
    print(hdr)
    print('-' * len(hdr))
    for row in changes:
        bid,sp,mkt,sel,line,cl,oc,nc,oclv,nclv,P = row
        print(f"{bid:<12} {sp:<3} {mkt:<8} {sel:<30} {line:>6} {cl:>7} {oc:>8} {nc:>8} {oclv:>8} {nclv:>8} {P:>5}")

    # Summary by sport / market
    print()
    for sport in ('NRL', 'AFL'):
        for mkt in ('handicap', 'total', 'totals'):
            subset = [float(r[9]) for r in changes if r[1] == sport and r[2] == mkt]
            if subset:
                avg = sum(subset)/len(subset)
                pos = sum(1 for x in subset if x > 0)
                print(f"  {sport} {mkt:<8}: n={len(subset):>3}, avg_clv={avg:+.2f}%, positive={pos}/{len(subset)}")

    print()
    nrl_all = [float(r[9]) for r in changes if r[1]=='NRL']
    afl_all = [float(r[9]) for r in changes if r[1]=='AFL']
    all_    = [float(r[9]) for r in changes]
    if nrl_all: print(f"NRL line/total combined: n={len(nrl_all)}, avg={sum(nrl_all)/len(nrl_all):+.2f}%, positive={sum(1 for x in nrl_all if x>0)}/{len(nrl_all)}")
    if afl_all: print(f"AFL line/total combined: n={len(afl_all)}, avg={sum(afl_all)/len(afl_all):+.2f}%, positive={sum(1 for x in afl_all if x>0)}/{len(afl_all)}")
    if all_:    print(f"ALL  line/total combined: n={len(all_)},  avg={sum(all_)/len(all_):+.2f}%, positive={sum(1 for x in all_ if x>0)}/{len(all_)}")

if __name__ == '__main__':
    main()
