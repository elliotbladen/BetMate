import sqlite3
conn = sqlite3.connect('data/model.db')

# Check results table
cols = [r[1] for r in conn.execute("PRAGMA table_info(results)").fetchall()]
print("results cols:", cols)

rows = conn.execute("""
    SELECT m.round_number, COUNT(*) as n,
           ROUND(AVG(r.home_score + r.away_score), 1) as avg_total,
           ROUND(AVG(r.home_score + r.away_score) / 2.0, 1) as avg_per_team
    FROM results r
    JOIN matches m ON r.match_id = m.match_id
    WHERE m.season = 2026
    GROUP BY m.round_number ORDER BY m.round_number
""").fetchall()

print(f"\n{'Round':<8} {'Games':<7} {'AvgTotal':<12} {'AvgPerTeam'}")
print("-" * 40)
for r in rows:
    print(f"  R{r[0]:<6} {r[1]:<7} {r[2]:<12} {r[3]}")

overall = conn.execute("""
    SELECT COUNT(*), ROUND(AVG(r.home_score+r.away_score),1), ROUND(AVG(r.home_score+r.away_score)/2,1)
    FROM results r JOIN matches m ON r.match_id=m.match_id WHERE m.season=2026
""").fetchone()
print(f"\n2026 TOTAL: {overall[0]} games | avg total {overall[1]} | avg/team {overall[2]}")

# Also check recent seasons
for season in [2022, 2023, 2024, 2025]:
    row = conn.execute("""
        SELECT COUNT(*), ROUND(AVG(r.home_score+r.away_score),1), ROUND(AVG(r.home_score+r.away_score)/2,1)
        FROM results r JOIN matches m ON r.match_id=m.match_id WHERE m.season=?
    """, (season,)).fetchone()
    if row[0]:
        print(f"{season}: {row[0]} games | avg total {row[1]} | avg/team {row[2]}")

conn.close()
