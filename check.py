import duckdb
con = duckdb.connect("trading_data.duckdb")
df = con.execute("SELECT MIN(time) as min_date, MAX(time) as max_date, COUNT(*) as total_rows FROM historical_prices WHERE symbol = 'VND'").df()
print(df)
con.close()
