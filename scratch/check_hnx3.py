import duckdb
con = duckdb.connect('data/trading_data.duckdb', read_only=True)
q = "SELECT MIN(time), MAX(time), COUNT(*) FROM historical_prices WHERE symbol = 'PVS'"
print(con.execute(q).df())
con.close()
