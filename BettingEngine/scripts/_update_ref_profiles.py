"""
Update referee_profiles in model.db with real scraped data.
Also adds referee_game_stats averages back to the profile record.
"""
import sqlite3
from pathlib import Path

conn = sqlite3.connect("data/model.db")

# Season averages (from all 7 refs = proxy for league)
season_avgs = {r[0]: r[1] for r in conn.execute(
    "SELECT season, AVG(total_score) FROM referee_game_stats GROUP BY season"
).fetchall()}

# Compute season-adjusted effect per referee
ref_stats = {}
for ref, season, total in conn.execute(
    "SELECT referee_name, season, total_score FROM referee_game_stats"
).fetchall():
    sea_avg = season_avgs.get(season, 45.0)
    ref_stats.setdefault(ref, []).append(total - sea_avg)

ref_summary = {}
for ref, residuals in ref_stats.items():
    n       = len(residuals)
    effect  = sum(residuals) / n
    # Recent (2025-2026) avg total
    recent  = conn.execute("""
        SELECT AVG(total_score), AVG(total_penalties), COUNT(*)
        FROM referee_game_stats WHERE referee_name=? AND season>=2025
    """, (ref,)).fetchone()
    ref_summary[ref] = {
        "n": n, "effect": effect,
        "recent_avg_total": recent[0],
        "recent_avg_pen": recent[1],
        "recent_n": recent[2],
    }

# Bucket assignment based on season-adjusted effect
def effect_to_bucket(effect):
    if effect < -0.8:  return "whistle_heavy"
    if effect >  0.8:  return "flow_heavy"
    return "neutral"

# Map referee names to referee_ids
ref_ids = {r[1]: r[0] for r in conn.execute(
    "SELECT referee_id, referee_name FROM referees"
).fetchall()}

print("Updating referee_profiles...")
print(f"{'Referee':<26} {'ID':>4} {'N':>6} {'Effect':>8} {'Bucket':<16} {'Recent Avg':>11}")
print("-" * 75)

for ref, stats in sorted(ref_summary.items(), key=lambda x: x[1]["effect"]):
    ref_id = ref_ids.get(ref)
    if ref_id is None:
        # Ref not in referees table yet — insert them
        conn.execute(
            "INSERT INTO referees (referee_name) VALUES (?)", (ref,)
        )
        conn.commit()
        ref_id = conn.execute(
            "SELECT referee_id FROM referees WHERE referee_name=?", (ref,)
        ).fetchone()[0]
        print(f"  Added new referee: {ref} (ID {ref_id})")

    bucket  = effect_to_bucket(stats["effect"])
    notes   = (f"Data-backed from RLP scrape 2022-2026 ({stats['n']} games). "
               f"Season-adj effect: {stats['effect']:+.2f} pts. "
               f"Recent (2025-26) avg total: {stats['recent_avg_total']:.1f} "
               f"({stats['recent_n']} games).")

    # Upsert referee_profiles
    existing = conn.execute(
        "SELECT referee_id FROM referee_profiles WHERE referee_id=?", (ref_id,)
    ).fetchone()

    if existing:
        conn.execute("""
            UPDATE referee_profiles
            SET bucket=?, games_in_sample=?, notes=?, updated_at=CURRENT_TIMESTAMP
            WHERE referee_id=?
        """, (bucket, stats["n"], notes, ref_id))
    else:
        conn.execute("""
            INSERT INTO referee_profiles (referee_id, bucket, games_in_sample, notes)
            VALUES (?, ?, ?, ?)
        """, (ref_id, bucket, stats["n"], notes))

    print(f"  {ref:<26} {ref_id:>4} {stats['n']:>6} {stats['effect']:>+8.2f} {bucket:<16} "
          f"{stats['recent_avg_total']:>11.1f}")

conn.commit()
print("\n✓ referee_profiles updated.")

# Final summary query
print("\n\nFINAL PROFILE STATE:")
for row in conn.execute("""
    SELECT r.referee_name, rp.bucket, rp.games_in_sample,
           rp.notes
    FROM referee_profiles rp
    JOIN referees r ON r.referee_id = rp.referee_id
    ORDER BY rp.bucket, r.referee_name
""").fetchall():
    print(f"  {row[0]:<26} {row[1]:<16} games={row[2]}")
    print(f"    {row[3][:90]}")

conn.close()
