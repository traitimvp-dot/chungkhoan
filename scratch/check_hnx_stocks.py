import duckdb
con = duckdb.connect('data/trading_data.duckdb', read_only=True)
q = """
SELECT symbol, MIN(time) as min_time, COUNT(*) as rows
FROM historical_prices h
JOIN company_info c ON h.symbol = c."Mã CP"
WHERE c.Sàn = 'HNX'
GROUP BY symbol
ORDER BY min_time ASC
LIMIT 10
"""
print(con.execute(q).df())
con.close()
