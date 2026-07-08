"""Season-adjusted referee scoring analysis — removes NRL-wide scoring trend."""
import sqlite3
from pathlib import Path

conn = sqlite3.connect("data/model.db")

# Season league averages (from all 7 refs combined = proxy for league)
season_avgs = {}
for row in conn.execute("""
    SELECT season, AVG(total_score), COUNT(*)
    FROM referee_game_stats
    GROUP BY season ORDER BY season
""").fetchall():
    season_avgs[row[0]] = row[1]
    print(f"  Season {row[0]}: league avg = {row[1]:.1f}  ({row[2]} games)")

print()

# Per-game residual (actual - season_avg) per referee
# Then average the residuals = season-adjusted referee effect
ref_residuals = {}
for ref, season, total in conn.execute("""
    SELECT referee_name, season, total_score
    FROM referee_game_stats
""").fetchall():
    sea_avg = season_avgs.get(season)
    if sea_avg is None:
        continue
    residual = total - sea_avg
    if ref not in ref_residuals:
        ref_residuals[ref] = []
    ref_residuals[ref].append(residual)

print("=" * 72)
print("  SEASON-ADJUSTED REFEREE EFFECT  (removes NRL scoring trend)")
print("  A positive value = games score MORE than expected that season")
print("=" * 72)
print(f"\n  {'Referee':<26} {'Games':>6} {'Adj Effect':>12} {'Raw Avg':>9} {'T6 Adj':>8}")
print(f"  {'-'*63}")

results = []
for ref, residuals in ref_residuals.items():
    n = len(residuals)
    effect = sum(residuals) / n
    raw_avg = conn.execute(
        "SELECT AVG(total_score) FROM referee_game_stats WHERE referee_name=?", (ref,)
    ).fetchone()[0]
    results.append((ref, n, effect, raw_avg))

results.sort(key=lambda x: x[2])

for ref, n, effect, raw_avg in results:
    t6_adj = round(effect / 2, 1)
    flag = "▲" if effect > 1.5 else ("▼" if effect < -1.5 else " ")
    print(f"  {ref:<26} {n:>6} {effect:>+11.2f}{flag} {raw_avg:>9.1f} {t6_adj:>+8.1f}")

print(f"\n  T6 Adj = season-adjusted effect / 2 (conservative dampener)")

# Penalty correlation
print(f"\n\n  PENALTY COUNT vs SCORING  (do more penalties = lower scoring?)")
print(f"  {'Referee':<26} {'Avg Pen':>9} {'Avg Total':>10} {'Under 48.5%':>12}")
print(f"  {'-'*60}")

for ref, n, effect, raw_avg in sorted(results, key=lambda x: x[0]):
    stats = conn.execute("""
        SELECT AVG(total_penalties), AVG(total_score),
               SUM(CASE WHEN total_score < 48.5 THEN 1 ELSE 0 END) * 1.0 / COUNT(*)
        FROM referee_game_stats WHERE referee_name=?
    """, (ref,)).fetchone()
    pen_avg, score_avg, under_rate = stats
    print(f"  {ref:<26} {pen_avg:>9.1f} {score_avg:>10.1f} {under_rate*100:>11.0f}%")

# Recent form — 2025+2026 only
print(f"\n\n  RECENT FORM (2025-2026 only — most relevant for current pricing)")
print(f"  {'Referee':<26} {'Games':>6} {'Avg Total':>10} {'vs 48.5 avg':>12} {'Under 48.5%':>12}")
print(f"  {'-'*68}")

for row in conn.execute("""
    SELECT referee_name,
           COUNT(*) AS n,
           ROUND(AVG(total_score),1) AS avg_total,
           SUM(CASE WHEN total_score < 48.5 THEN 1 ELSE 0 END)*1.0/COUNT(*) AS under_rate
    FROM referee_game_stats
    WHERE season >= 2025
    GROUP BY referee_name
    ORDER BY avg_total
""").fetchall():
    delta = row[2] - 48.5
    print(f"  {row[0]:<26} {row[1]:>6} {row[2]:>10.1f} {delta:>+11.1f} {row[3]*100:>11.0f}%")

conn.close()
