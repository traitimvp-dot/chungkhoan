from vnstock.ui import Market
mkt = Market()
try:
    df = mkt.equity('PVS').ohlcv(start="2020-01-01", end="2026-07-17", count=1500)
    print(f"Loaded with count=1500: {len(df)} rows")
except Exception as e:
    print(f"Error with count: {e}")
