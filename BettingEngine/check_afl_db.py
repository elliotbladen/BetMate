import sqlite3
conn = sqlite3.connect('data/model.db')
conn.row_factory = sqlite3.Row

rounds = conn.execute("""SELECT DISTINCT round_number, COUNT(*) as cnt FROM matches
    WHERE season=2026 AND (sport='AFL' OR competition='AFL')
    GROUP BY round_number ORDER BY round_number""").fetchall()
print('AFL matches by round:')
for r in rounds:
    print(f'  R{r["round_number"]}: {r["cnt"]} matches')

latest = conn.execute("""SELECT m.round_number, m.match_date, th.team_name home, ta.team_name away, r.home_score, r.away_score
    FROM matches m
    JOIN teams th ON m.home_team_id=th.team_id
    JOIN teams ta ON m.away_team_id=ta.team_id
    LEFT JOIN results r ON m.match_id=r.match_id
    WHERE m.season=2026 AND (m.sport='AFL' OR m.competition='AFL')
    ORDER BY m.round_number DESC, m.match_date DESC LIMIT 20""").fetchall()
print()
print('Recent AFL matches:')
for r in latest:
    score = f"{r['home_score']}-{r['away_score']}" if r['home_score'] is not None else 'no result'
    print(f'  R{r["round_number"]} {r["match_date"][:10]} {r["home"][:22]:<22} vs {r["away"][:22]:<22} {score}')

# Check sport column values
sports = conn.execute("SELECT DISTINCT sport, competition FROM matches WHERE season=2026 LIMIT 10").fetchall()
print()
print('Sport/competition values:', [(s['sport'], s['competition']) for s in sports])
conn.close()
