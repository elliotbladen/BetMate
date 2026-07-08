"""Load R17 2026 referee assignments into weekly_ref_assignments."""
import sqlite3

conn = sqlite3.connect("data/model.db")
conn.row_factory = sqlite3.Row

# R17 assignments confirmed Thu Jun 25 2026
ASSIGNMENTS = [
    ("Parramatta",    "South Sydney",    "Gerard Sutton"),
    ("Gold Coast",    "Canterbury",       "Todd Smith"),
    ("Brisbane",      "Sydney Roosters",  "Grant Atkins"),
    ("Dolphins",      "New Zealand",      "Adam Gee"),
    ("North Queensland", "Penrith",       "Wyatt Raymond"),
    ("Manly",         "Melbourne",        "Ashley Klein"),
    ("Canberra",      "St. George",       "Ziggy Przeklasa-Adamski"),
    ("Newcastle",     "Wests Tigers",     "Peter Gough"),
]

r17_matches = conn.execute("""
    SELECT m.match_id, ht.team_name AS home, at.team_name AS away
    FROM matches m
    JOIN teams ht ON ht.team_id = m.home_team_id
    JOIN teams at ON at.team_id = m.away_team_id
    WHERE m.season = 2026 AND m.round_number = 17
""").fetchall()

print("R17 matches in DB:")
for m in r17_matches:
    print(f"  match_id={m['match_id']}  {m['home']} vs {m['away']}")
print()

loaded = 0
for home_kw, away_kw, ref_name in ASSIGNMENTS:
    match = None
    for m in r17_matches:
        if home_kw.lower() in m['home'].lower() and away_kw.lower() in m['away'].lower():
            match = m
            break
    if not match:
        print(f"  WARNING: no match found for {home_kw} vs {away_kw}")
        continue

    ref_row = conn.execute(
        "SELECT referee_id FROM referees WHERE referee_name=?", (ref_name,)
    ).fetchone()
    if not ref_row:
        print(f"  WARNING: referee not found in DB: {ref_name}")
        continue

    ref_id = ref_row[0]

    conn.execute("""
        INSERT INTO weekly_ref_assignments (match_id, referee_id, season, round_number, source)
        VALUES (?, ?, 2026, 17, 'manual')
        ON CONFLICT(match_id) DO UPDATE SET referee_id=excluded.referee_id, source='manual'
    """, (match['match_id'], ref_id))

    sd = conn.execute(
        "SELECT scoring_delta, home_bias_adj FROM referee_profiles WHERE referee_id=?", (ref_id,)
    ).fetchone()
    delta_s = f"{sd[0]:+.3f}" if sd and sd[0] is not None else "None"
    delta_h = f"{sd[1]:+.3f}" if sd and sd[1] is not None else "None"
    print(f"  OK  {match['home']} vs {match['away']}  ->  {ref_name}  "
          f"(scoring_delta={delta_s}, home_bias={delta_h})")
    loaded += 1

conn.commit()
print(f"\nLoaded {loaded}/8 R17 referee assignments.")
conn.close()
