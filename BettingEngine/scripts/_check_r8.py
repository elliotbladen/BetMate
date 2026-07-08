import sqlite3
conn = sqlite3.connect('data/model.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("R8 game-by-game:")
cur.execute("""
    SELECT ht.team_name as home, at2.team_name as away,
           r.home_score, r.away_score, r.total_score
    FROM results r
    JOIN matches m ON m.match_id = r.match_id
    JOIN teams ht ON ht.team_id = m.home_team_id
    JOIN teams at2 ON at2.team_id = m.away_team_id
    WHERE m.season = 2026 AND m.round_number = 8
    ORDER BY m.match_id
""")
for row in cur.fetchall():
    print(f"  {row['home'][:22]:<22} vs {row['away'][:22]:<22}  {row['home_score']:>3}-{row['away_score']:<3}  total={row['total_score']}")

print()
print("Round averages (R8-R15):")
cur.execute("""
    SELECT m.round_number, AVG(r.total_score) as avg_total, COUNT(*) as n
    FROM results r JOIN matches m ON m.match_id = r.match_id
    WHERE m.season = 2026 AND m.round_number >= 8
    GROUP BY m.round_number ORDER BY m.round_number
""")
for row in cur.fetchall():
    print(f"  R{row['round_number']}: avg_actual={row['avg_total']:.1f}  games={row['n']}")

conn.close()
