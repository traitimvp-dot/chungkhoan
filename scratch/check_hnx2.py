import sys, os
import duckdb
sys.path.append(os.path.abspath('src'))
from app import load_data

df = load_data('PVS')
print(f"Min date for PVS: {df.index.min()}")
print(f"Max date for PVS: {df.index.max()}")
print(f"Total rows: {len(df)}")
