"""Load R16 2026 referee assignments into weekly_ref_assignments."""
import sqlite3

conn = sqlite3.connect("data/model.db")
conn.row_factory = sqlite3.Row

# R16 assignments from RLP
ASSIGNMENTS = [
    ("Newcastle Knights",  "St. George",   "Gerard Sutton"),
    ("Wests",             "Dolphins",     "Ziggy Przeklasa-Adamski"),
    ("Gold Coast",        "Penrith",      "Peter Gough"),
    ("Canterbury",        "Manly",        "Adam Gee"),
    ("New Zealand",       "North Queensland", "Grant Atkins"),
    ("Melbourne",         "Canberra",     "Todd Smith"),
    ("Sydney Roosters",   "Cronulla",     "Ashley Klein"),
]

# Get all R16 matches
r16_matches = conn.execute("""
    SELECT m.match_id, ht.team_name AS home, at.team_name AS away
    FROM matches m
    JOIN teams ht ON ht.team_id = m.home_team_id
    JOIN teams at ON at.team_id = m.away_team_id
    WHERE m.season = 2026 AND m.round_number = 16
""").fetchall()

print("R16 matches in DB:")
for m in r16_matches:
    print(f"  match_id={m['match_id']}  {m['home']} vs {m['away']}")

print()
loaded = 0
for home_kw, away_kw, ref_name in ASSIGNMENTS:
    # Find match
    match = None
    for m in r16_matches:
        if home_kw.lower() in m['home'].lower() and away_kw.lower() in m['away'].lower():
            match = m
            break
    if not match:
        print(f"  WARNING: no match found for {home_kw} vs {away_kw}")
        continue

    # Find referee_id
    ref_row = conn.execute(
        "SELECT referee_id FROM referees WHERE referee_name=?", (ref_name,)
    ).fetchone()
    if not ref_row:
        print(f"  WARNING: referee not found: {ref_name}")
        continue

    ref_id = ref_row[0]

    # Upsert assignment
    conn.execute("""
        INSERT INTO weekly_ref_assignments (match_id, referee_id, season, round_number, source)
        VALUES (?, ?, 2026, 16, 'manual')
        ON CONFLICT(match_id) DO UPDATE SET referee_id=excluded.referee_id, source='manual'
    """, (match['match_id'], ref_id))

    sd = conn.execute(
        "SELECT scoring_delta FROM referee_profiles WHERE referee_id=?", (ref_id,)
    ).fetchone()
    delta = f"{sd[0]:+.3f}" if sd and sd[0] is not None else "None"
    print(f"  ✓ {match['home']} vs {match['away']} → {ref_name}  (scoring_delta={delta})")
    loaded += 1

conn.commit()
print(f"\nLoaded {loaded}/7 R16 referee assignments.")
conn.close()
