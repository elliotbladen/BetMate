import sqlite3
conn = sqlite3.connect(r'C:\Users\ElliotBladen\Apps\BettingEngine\data\model.db')
conn.row_factory = sqlite3.Row

r11 = conn.execute("""
    SELECT ht.team_name as home, at.team_name as away,
           r.home_score, r.away_score, m.round_number
    FROM results r
    JOIN matches m ON m.match_id = r.match_id
    JOIN teams ht ON ht.team_id = m.home_team_id
    JOIN teams at ON at.team_id = m.away_team_id
    WHERE m.season=2026 AND m.round_number=11
""").fetchall()
print(f"R11 results in DB: {len(r11)}")
for r in r11:
    print(f"  {r['home']} {r['home_score']} - {r['away_score']} {r['away']}")

latest_elo = conn.execute(
    "SELECT MAX(as_of_date) FROM team_stats WHERE season=2026"
).fetchone()[0]
print(f"\nNRL ELO last updated (as_of_date): {latest_elo}")

# Show current ELO ratings
elos = conn.execute("""
    SELECT t.team_name, ts.elo_rating, ts.as_of_date
    FROM team_stats ts JOIN teams t ON t.team_id = ts.team_id
    WHERE ts.season=2026 AND ts.as_of_date = (
        SELECT MAX(as_of_date) FROM team_stats WHERE season=2026
    )
    ORDER BY ts.elo_rating DESC
""").fetchall()
print("\nCurrent NRL ELO ratings:")
for e in elos:
    print(f"  {e['team_name']:<40} {e['elo_rating']:.0f}  (as of {e['as_of_date']})")

conn.close()
