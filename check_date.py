import duckdb
con = duckdb.connect("data/trading_data.duckdb")
df = con.execute("SELECT symbol, MAX(time) FROM historical_prices WHERE symbol IN ('FPT', 'VND', 'VCB') GROUP BY symbol").df()
print(df)
