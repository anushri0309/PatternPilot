import pandas as pd
from pathlib import Path

LABEL_MAP_FILE = Path("data/raw/imaterialist/label_map_228.xlsx")

print("📂 Loading label map...")
df = pd.read_excel(LABEL_MAP_FILE)

print(f"Shape: {df.shape}")
print(f"\nColumns: {df.columns.tolist()}")
print(f"\nFirst 5 rows:")
print(df.head())
print(f"\nSample data:")
print(df.iloc[:10].to_string())