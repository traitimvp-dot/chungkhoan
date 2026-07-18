import duckdb
import os
import time
from vnstock.ui import Reference

try:
    from vnstock.core.exceptions import RateLimitError
except ImportError:
    RateLimitError = Exception

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "trading_data.duckdb")

def init_db(con):
    """Khởi tạo bảng company_profile nếu chưa có."""
    con.execute("""
        CREATE TABLE IF NOT EXISTS company_profile (
            symbol VARCHAR PRIMARY KEY,
            business_model VARCHAR,
            founded_date VARCHAR,
            charter_capital DOUBLE,
            number_of_employees BIGINT,
            listing_date VARCHAR,
            par_value DOUBLE,
            exchange VARCHAR,
            listing_price DOUBLE,
            listed_volume DOUBLE,
            ceo_name VARCHAR,
            ceo_position VARCHAR,
            inspector_name VARCHAR,
            inspector_position VARCHAR,
            establishment_license VARCHAR,
            business_code VARCHAR,
            tax_id VARCHAR,
            auditor VARCHAR,
            company_type VARCHAR,
            address VARCHAR,
            phone VARCHAR,
            fax VARCHAR,
            email VARCHAR,
            website VARCHAR,
            branches VARCHAR,
            history VARCHAR,
            free_float_percentage DOUBLE,
            free_float DOUBLE,
            outstanding_shares DOUBLE,
            as_of_date VARCHAR
        )
    """)

def run_update():
    print("Bắt đầu cập nhật Thông tin Cơ bản (Company Profile) cho các mã cổ phiếu...")
    con = duckdb.connect(DB_PATH)
    init_db(con)
    
    # Lấy danh sách các mã cần quét
    query = """
        SELECT "Mã CP" as symbol
        FROM company_info
        WHERE Sàn IN ('HOSE', 'HNX')
        ORDER BY "Mã CP"
    """
    symbols = con.execute(query).df()['symbol'].tolist()
    
    # Chỉ lấy các mã chưa có trong company_profile
    existing_query = "SELECT symbol FROM company_profile"
    existing_symbols = con.execute(existing_query).df()['symbol'].tolist()
    
    pending_symbols = [s for s in symbols if s not in existing_symbols]
    
    print(f"Tổng số mã: {len(symbols)}")
    print(f"Số mã đã quét: {len(existing_symbols)}")
    print(f"Số mã cần quét: {len(pending_symbols)}")
    
    if not pending_symbols:
        print("Đã quét đủ tất cả các mã. Không cần chạy thêm.")
        con.close()
        return

    ref = Reference()
    success = 0
    failed = 0
    
    for i, sym in enumerate(pending_symbols):
        retries = 0
        while retries < 3:
            try:
                time.sleep(1.5) # vnstock free limit: 60 req/phút
                df_info = ref.company(sym).info()
                
                if df_info is not None and not df_info.empty:
                    df_info['symbol'] = sym # Ensure symbol is set explicitly
                    # Ensure columns order matches DB
                    cols = [
                        'symbol', 'business_model', 'founded_date', 'charter_capital',
                        'number_of_employees', 'listing_date', 'par_value', 'exchange',
                        'listing_price', 'listed_volume', 'ceo_name', 'ceo_position',
                        'inspector_name', 'inspector_position', 'establishment_license',
                        'business_code', 'tax_id', 'auditor', 'company_type', 'address',
                        'phone', 'fax', 'email', 'website', 'branches', 'history',
                        'free_float_percentage', 'free_float', 'outstanding_shares', 'as_of_date'
                    ]
                    
                    # Missing columns check
                    for c in cols:
                        if c not in df_info.columns:
                            df_info[c] = None
                            
                    df_info = df_info[cols]
                    
                    con.execute(f"DELETE FROM company_profile WHERE symbol = '{sym}'")
                    con.execute("INSERT INTO company_profile SELECT * FROM df_info")
                    
                    success += 1
                    print(f"[{i+1}/{len(pending_symbols)}] OK: {sym}")
                else:
                    failed += 1
                    print(f"[{i+1}/{len(pending_symbols)}] SKIP (Empty): {sym}")
                break # Success, escape retry loop
                
            except RateLimitError:
                print(f"[RateLimit] {sym}: Đợi 60s...")
                time.sleep(60)
                retries += 1
            except SystemExit:
                print(f"[RateLimit/SystemExit] {sym}: Đợi 65s...")
                time.sleep(65)
                retries += 1
            except Exception as e:
                print(f"[{i+1}/{len(pending_symbols)}] FAIL: {sym} | Lỗi: {e}")
                failed += 1
                break # Other error, escape retry loop

    print(f"\n--- KẾT QUẢ ---")
    print(f"Thành công: {success}")
    print(f"Thất bại/Bỏ qua: {failed}")
    con.close()

if __name__ == "__main__":
    run_update()
