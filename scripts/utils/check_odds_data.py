# /// script
# dependencies = ["pandas"]
# ///
import pandas as pd
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
df = pd.concat([
    pd.read_csv(ROOT/'BettingEngine/data/import/odds_2023.csv'),
    pd.read_csv(ROOT/'BettingEngine/data/import/odds_2025.csv'),
    pd.read_csv(ROOT/'BettingEngine/data/import/odds_2026_r1_r5.csv'),
])
print("is_opening:", df['is_opening'].value_counts().to_dict())
print("is_closing:", df['is_closing'].value_counts().to_dict())
print("market_type:", df['market_type'].value_counts().to_dict())
print("Total rows:", len(df))
print("\nSample opening row:")
print(df[df['is_opening']==1].head(1).to_string())
