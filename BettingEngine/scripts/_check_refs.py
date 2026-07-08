import sqlite3
conn = sqlite3.connect("data/model.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='referees'")
row = cur.fetchone()
print("REFEREES TABLE:")
print(row[0] if row else "NOT FOUND")

cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%ref%'")
print("\nREF-RELATED TABLES:", [r[0] for r in cur.fetchall()])

cur.execute("SELECT COUNT(*) FROM referees")
print(f"\nRow count: {cur.fetchone()[0]}")

cur.execute("SELECT * FROM referees LIMIT 8")
rows = cur.fetchall()
if rows:
    print("\nColumns:", list(rows[0].keys()))
    for r in rows:
        print(dict(r))

# Check if matches table links to referees
cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='matches'")
row = cur.fetchone()
print("\nMATCHES TABLE (looking for ref column):")
if row:
    for line in row[0].split("\n"):
        if "ref" in line.lower():
            print(" ", line.strip())

conn.close()
