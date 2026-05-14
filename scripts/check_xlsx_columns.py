# /// script
# dependencies = ["openpyxl", "pandas"]
# ///
import pandas as pd
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
f = ROOT / "data/nrl/historical/latest.xlsx"
df = pd.read_excel(f, nrows=3)
print("Columns:", list(df.columns))
print(df.head(3).to_string())
