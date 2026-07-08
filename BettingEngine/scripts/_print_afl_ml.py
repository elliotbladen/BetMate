import sqlite3
from pathlib import Path

conn = sqlite3.connect(r'C:\Users\ElliotBladen\Apps\BettingEngine\data\model.db')
conn.row_factory = sqlite3.Row

rows = conn.execute("""
    SELECT home_team, away_team,
           rules_margin, ml_margin,
           rules_total,  ml_total,
           rules_home_prob, ml_h2h,
           agreement_flag
    FROM afl_shadow_predictions
    WHERE season=2026 AND round_number=11
    ORDER BY game_date, home_team
""").fetchall()

print(f"  {'Matchup':<36} {'Rules Mrg':>10} {'ML Mrg':>8} {'Gap':>7}  {'Rules Tot':>10} {'ML Tot':>8}  {'Rules H%':>9} {'ML H%':>7}  Flag")
print("  " + "─" * 110)
for r in rows:
    home = r['home_team'].split()[-1]
    away = r['away_team'].split()[-1]
    matchup = f"{home} vs {away}"
    mrg_gap = (r['ml_margin'] or 0) - r['rules_margin']
    tot_gap = (r['ml_total'] or 0) - r['rules_total']
    flag = r['agreement_flag'] or ''
    print(f"  {matchup:<36} {r['rules_margin']:>+10.1f} {r['ml_margin'] or 0:>+8.1f} {mrg_gap:>+7.1f}  "
          f"{r['rules_total']:>10.1f} {r['ml_total'] or 0:>8.1f}  "
          f"{r['rules_home_prob']*100:>8.1f}% {(r['ml_h2h'] or 0)*100:>6.1f}%  {flag}")

conn.close()
