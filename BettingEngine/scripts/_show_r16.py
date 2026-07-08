import csv
rows = list(csv.DictReader(open("results/r16_pricing_2026.csv", encoding="utf-8-sig")))
print(f"{'Game':<45} {'T1':>6} {'Margin':>8} {'Hcap':>8} {'FairH2H(h)':>12} {'H@105':>8} {'A@105':>8}")
print("-"*95)
for r in rows:
    home = r["home_team"].split()[-1]
    away = r["away_team"].split()[-1]
    game = f"{home} vs {away}"
    t1 = float(r.get("t1_hcap", r.get("t1_margin",0)))
    margin = float(r.get("final_margin",0))
    hcap = float(r.get("fair_hcap_line",0))
    fh2h = float(r.get("fair_home_odds",0))
    h105 = float(r.get("h2h_home_105",0))
    a105 = float(r.get("h2h_away_105",0))
    print(f"{game:<45} {t1:>+6.1f} {margin:>+8.1f} {hcap:>+8.1f} {fh2h:>12.3f} {h105:>8.3f} {a105:>8.3f}")
