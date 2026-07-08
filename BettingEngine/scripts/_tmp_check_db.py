import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect('data/model.db')
conn.row_factory = sqlite3.Row
# Sample matches to see PK name
rows = conn.execute("SELECT * FROM matches LIMIT 2").fetchall()
print("matches cols:", rows[0].keys() if rows else "empty")
for r in rows:
    print({k: r[k] for k in r.keys()})

# Check join - matches.match_id -> results.match_id
rows2 = conn.execute("""
    SELECT m.match_id, m.round_number, m.match_date, r.home_score, r.away_score
    FROM matches m
    LEFT JOIN results r ON r.match_id = m.match_id
    WHERE r.home_score IS NOT NULL
    LIMIT 3
""").fetchall()
print("\nJoin test:")
for r in rows2:
    print({k: r[k] for k in r.keys()})
conn.close()
