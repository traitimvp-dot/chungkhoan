import duckdb
con = duckdb.connect('data/trading_data.duckdb', read_only=True)
count = con.execute("SELECT COUNT(DISTINCT symbol) FROM historical_prices WHERE time >= '2026-07-14'").fetchone()[0]
print(f'Số mã cổ phiếu đã cập nhật hôm nay: {count} / 393')
