import csv, sqlite3

conn = sqlite3.connect("data/model.db")

ref_map = {}
for row in conn.execute("""
    SELECT m.match_id, r.referee_name, rp.scoring_delta, rp.bucket
    FROM weekly_ref_assignments wra
    JOIN matches m ON m.match_id = wra.match_id
    JOIN referees r ON r.referee_id = wra.referee_id
    LEFT JOIN referee_profiles rp ON rp.referee_id = wra.referee_id
    WHERE wra.season=2026 AND wra.round_number=16
""").fetchall():
    ref_map[row[1]] = (row[2], row[3])

rows = list(csv.DictReader(open("results/r16_pricing_2026.csv", encoding="utf-8-sig")))

print("R16 TOTALS BREAKDOWN — with real referee scoring data")
print("=" * 100)
print(f"{'Game':<32} {'T1':>6} {'T6':>6} {'T7':>5} {'T8':>5} {'T10':>5} {'Final':>7}  {'Referee':<24} (scoring_delta)")
print("-" * 100)

for r in rows:
    home  = r["home_team"].split()[-1]
    away  = r["away_team"].split()[-1]
    game  = f"{home} vs {away}"
    t1    = float(r["t1_totals"])
    t6    = float(r["t6_totals"])
    t7    = float(r["t7_totals"])
    t8    = float(r["t8_totals"])
    t10   = float(r["t10_totals"])
    final = float(r["final_total"])
    ref   = r["referee"]
    sd, bucket = ref_map.get(ref, (None, "—"))
    sd_str = f"{sd:+.2f}" if sd is not None else "none"

    print(f"  {game:<30} {t1:>6.1f} {t6:>+6.2f} {t7:>+5.1f} {t8:>+5.1f} {t10:>+5.1f} {final:>7.1f}  {ref:<24} ({sd_str})")

print()
print("  T6 source: real RLP scraped data 2022-2026 (season-adjusted effect)")
print("  Ziggy = no scraped data → falls back to neutral bucket (0.0)")
conn.close()
