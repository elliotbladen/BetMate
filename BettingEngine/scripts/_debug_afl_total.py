import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
df = pd.read_csv(ROOT / 'ml/afl/results/features_afl.csv', encoding='latin-1')
df['date'] = pd.to_datetime(df['date'])

LEAGUE_AVG = 83.5

def avg_scored(team, before_date, n=8):
    home = df[(df['home_team'] == team) & (df['date'] < before_date)][['date','home_score']].rename(columns={'home_score':'score'})
    away = df[(df['away_team'] == team) & (df['date'] < before_date)][['date','away_score']].rename(columns={'away_score':'score'})
    games = pd.concat([home, away]).sort_values('date').tail(n)
    return float(games['score'].mean()) if not games.empty else LEAGUE_AVG

game_date = '2026-05-23'
col_rate = avg_scored('Collingwood Magpies', game_date)
wce_rate = avg_scored('West Coast Eagles',   game_date)

col_reg = col_rate * 0.75 + LEAGUE_AVG * 0.25
wce_reg = wce_rate * 0.75 + LEAGUE_AVG * 0.25

print(f"Collingwood raw avg scored (last 8): {col_rate:.1f}  → regressed: {col_reg:.1f}")
print(f"West Coast   raw avg scored (last 8): {wce_rate:.1f}  → regressed: {wce_reg:.1f}")
print(f"T1 total (regressed sum):             {col_reg + wce_reg:.1f}")
print()

# Show WCE last 8 results
home = df[(df['home_team']=='West Coast Eagles')][['date','home_team','away_team','home_score','away_score']]
away = df[(df['away_team']=='West Coast Eagles')][['date','home_team','away_team','home_score','away_score']]
all_wce = pd.concat([home, away]).sort_values('date').tail(8)
print("West Coast last 8 games:")
for _, r in all_wce.iterrows():
    if r['home_team'] == 'West Coast Eagles':
        print(f"  {r['date'].date()}  WCE {r['home_score']} - {r['away_score']} {r['away_team']}")
    else:
        print(f"  {r['date'].date()}  {r['home_team']} {r['home_score']} - {r['away_score']} WCE")
