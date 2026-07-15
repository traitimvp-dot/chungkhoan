import duckdb
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "trading_data.duckdb")

con = duckdb.connect(DB_PATH, read_only=True)

# Xem columns cua company_info
cols = con.execute("DESCRIBE company_info").df()
print("Columns of company_info:")
print(cols)

# So ma co lich su gia
r2 = con.execute('SELECT COUNT(DISTINCT symbol) FROM historical_prices').fetchone()
print(f"\nSo ma co du lieu lich su gia: {r2[0]}")

# Pham vi thoi gian
r3 = con.execute('SELECT MIN(time), MAX(time) FROM historical_prices').fetchone()
print(f"Pham vi du lieu: {r3[0]} -> {r3[1]}")

# So ma da cap nhat den ngay hom nay (2026-07-15)
r4 = con.execute("SELECT COUNT(DISTINCT symbol) FROM historical_prices WHERE time >= '2026-07-15'").fetchone()
print(f"So ma da cap nhat ngay 2026-07-15: {r4[0]}")

# Tong so ban ghi
r6 = con.execute("SELECT COUNT(*) FROM historical_prices").fetchone()
print(f"Tong so ban ghi: {r6[0]:,}")

con.close()
