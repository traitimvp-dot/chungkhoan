"""
Script do luong thoi gian mot lan goi API + ghi DB, de tinh toan tong thoi gian du kien.
"""
import duckdb, time, os
from vnstock.ui import Market
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "trading_data.duckdb")

# --- Do toc do mot lan goi API ---
mkt = Market()
today_str = datetime.now().strftime("%Y-%m-%d")
start_str = "2026-07-14"

print("=== Benchmark mot lan goi API ===")
test_symbols = ["FPT", "VCB", "HPG", "VNM", "MWG"]
for sym in test_symbols:
    t0 = time.time()
    df = mkt.equity(sym).ohlcv(start=start_str, end=today_str)
    elapsed = time.time() - t0
    rows = len(df) if df is not None else 0
    print(f"  {sym}: {elapsed:.2f}s | {rows} rows")
    time.sleep(0.5)  # tranh spam

# --- Dem so ma can cap nhat hom nay ---
con = duckdb.connect(DB_PATH, read_only=True)
r = con.execute("""
    SELECT COUNT(DISTINCT symbol) as can_cap_nhat
    FROM historical_prices
    GROUP BY symbol
    HAVING MAX(time) < '2026-07-15'
""").fetchone()
total_need_update = r[0] if r else 0

r2 = con.execute("SELECT COUNT(DISTINCT symbol) FROM historical_prices WHERE time >= '2026-07-15'").fetchone()
already_done = r2[0]

total_ma = 403
remaining = total_ma - already_done
con.close()

print(f"\n=== Uoc tinh toc do ===")
print(f"  Tong so ma: {total_ma}")
print(f"  Da cap nhat hom nay: {already_done}")
print(f"  Con lai: {remaining}")
print(f"\n  Rate limit an toan: 1.2s/ma")
print(f"  Thoi gian goi API trung binh: ~2s/ma (bao gom overhead)")
print(f"  => Thoi gian xu ly moi ma: ~3.2s (1.2s sleep + 2s API)")
print(f"  => Thoi gian du kien hoan thanh {remaining} ma con lai: {remaining * 3.2 / 60:.1f} phut")

print(f"\n=== Van de hien tai ===")
print(f"  - Dang xu ly tuan tu, 1 ma 1 lan: rat cham voi 400+ ma")
print(f"  - Moi ngay can cap nhat: ~{total_ma - already_done} ma")
print(f"  - Van de chinh: sleep(1.2) x {total_ma} ma = {total_ma * 1.2 / 60:.0f} phut chi cho sleep!")
