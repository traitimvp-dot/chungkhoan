import duckdb
con = duckdb.connect('data/trading_data.duckdb', read_only=True)
q = """
SELECT c.Sàn, MIN(h.time) as min_time, MAX(h.time) as max_time, COUNT(DISTINCT h.symbol) as num_symbols
FROM historical_prices h
JOIN company_info c ON h.symbol = c."Mã CP"
GROUP BY c.Sàn
"""
print(con.execute(q).df())
con.close()
