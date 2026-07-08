import sqlite3
conn = sqlite3.connect("data/model.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# referee_profiles schema + data
cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='referee_profiles'")
row = cur.fetchone()
print("REFEREE_PROFILES TABLE:")
print(row[0] if row else "NOT FOUND")

cur.execute("SELECT COUNT(*) FROM referee_profiles")
print(f"\nRow count: {cur.fetchone()[0]}")

cur.execute("SELECT * FROM referee_profiles LIMIT 5")
rows = cur.fetchall()
if rows:
    print("\nSample rows:")
    for r in rows:
        print(dict(r))

# team_ref_bucket_stats
cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='team_ref_bucket_stats'")
row = cur.fetchone()
print("\n\nTEAM_REF_BUCKET_STATS TABLE:")
print(row[0] if row else "NOT FOUND")

cur.execute("SELECT COUNT(*) FROM team_ref_bucket_stats")
print(f"\nRow count: {cur.fetchone()[0]}")

cur.execute("SELECT * FROM team_ref_bucket_stats LIMIT 5")
rows = cur.fetchall()
if rows:
    print("\nSample rows:")
    for r in rows:
        print(dict(r))

# weekly_ref_assignments
cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='weekly_ref_assignments'")
row = cur.fetchone()
print("\n\nWEEKLY_REF_ASSIGNMENTS TABLE:")
print(row[0] if row else "NOT FOUND")

cur.execute("SELECT COUNT(*) FROM weekly_ref_assignments")
print(f"\nRow count: {cur.fetchone()[0]}")

cur.execute("SELECT * FROM weekly_ref_assignments ORDER BY season DESC, round_number DESC LIMIT 10")
rows = cur.fetchall()
if rows:
    print("\nMost recent assignments:")
    for r in rows:
        print(dict(r))

# How many matches have a referee_id assigned?
cur.execute("SELECT COUNT(*) FROM matches WHERE referee_id IS NOT NULL")
print(f"\n\nMatches with referee_id assigned: {cur.fetchone()[0]}")
cur.execute("SELECT COUNT(*) FROM matches")
print(f"Total matches: {cur.fetchone()[0]}")

conn.close()
