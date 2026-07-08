import csv

rows = list(csv.DictReader(open("results/r16_pricing_2026.csv", encoding="utf-8-sig")))

print("R16 FINAL PRICES — with T6 home bias wired in")
print("=" * 115)
print(f"  {'Game':<32} {'Fair Margin':>12} {'T6 Hcap':>9} {'T6 Tot':>8} {'Fair Total':>11} {'H fair':>8} {'A fair':>8}  Referee")
print("-" * 115)

for r in rows:
    home      = r["home_team"].split()[-1]
    away      = r["away_team"].split()[-1]
    game      = f"{home} vs {away}"
    margin    = float(r["final_margin"])
    t6h       = float(r["t6_hcap"])
    t6t       = float(r["t6_totals"])
    final_tot = float(r["final_total"])
    hfair     = float(r["fair_home_odds"])
    afair     = float(r["fair_away_odds"])
    ref       = r["referee"]
    print(f"  {game:<32} {margin:>+10.1f}  {t6h:>+7.2f}  {t6t:>+7.2f}  {final_tot:>9.1f}    {hfair:>6.3f}   {afair:>6.3f}  {ref}")

print()
print("  T6 Hcap: +ve = favours home team (Klein +3.20), -ve = favours away (Sutton -3.14)")
print("  Fair Margin: positive = home team wins by that margin")
