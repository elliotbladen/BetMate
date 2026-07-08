import sqlite3
conn = sqlite3.connect("data/model.db")
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
print("Tables:", [t[0] for t in tables])
cols = conn.execute("PRAGMA table_info(afl_venue_profiles)").fetchall()
print("afl_venue_profiles cols:", cols)
conn.close()
