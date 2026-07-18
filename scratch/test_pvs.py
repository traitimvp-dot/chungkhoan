from vnstock.ui import Market
mkt = Market()
df = mkt.equity('PVS').ohlcv(start="2020-01-01", end="2026-07-17")
print(f"Loaded: {len(df)} rows")
print(f"Min time: {df['time'].min()}")
print(f"Max time: {df['time'].max()}")
