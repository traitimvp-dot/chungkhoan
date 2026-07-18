import sys
import os
import time
import duckdb
sys.path.append(os.path.abspath('src'))
from strategy import run_portfolio_backtest

# Get all symbols
con = duckdb.connect('data/trading_data.duckdb', read_only=True)
symbols = con.execute("SELECT DISTINCT \"Mã CP\" FROM company_info WHERE Sàn IN ('HOSE', 'HNX')").df()['Mã CP'].tolist()
con.close()

print(f"Total symbols: {len(symbols)}")

start = time.time()
results = {}
# Only test the first 50 symbols to estimate time
for sym in symbols[:50]:
    res = run_portfolio_backtest(sym, 100000000, "Tất cả", "Tín hiệu Mua 1", "Tín hiệu Bán 1")
    metrics = res.get("metrics")
    if metrics:
        results[sym] = metrics["total_profit_pct"]

end = time.time()
print(f"Time for 50 symbols: {end - start:.2f} seconds")
print(f"Estimated time for {len(symbols)} symbols: {(end - start) / 50 * len(symbols):.2f} seconds")
