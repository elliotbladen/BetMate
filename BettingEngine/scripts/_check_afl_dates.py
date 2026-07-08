import pandas as pd

df = pd.read_excel(
    r'C:\Users\ElliotBladen\Apps\BettingEngine\outputs\afl_weekly_review\historical\latest.xlsx',
    header=1
)
df.columns = [str(c).strip() for c in df.columns]
df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
df = df.dropna(subset=['Date']).sort_values('Date')

print(f"Date range: {df['Date'].min().date()} to {df['Date'].max().date()}")
print(f"Total games: {len(df)}")
print()
print("Latest 10 games:")
print(df.tail(10)[['Date','Home Team','Away Team','Home Score','Away Score']].to_string(index=False))
