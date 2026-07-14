import os
import duckdb
import pandas as pd
from vnstock.ui import Reference

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "trading_data.duckdb")

def sync_company_info():
    print("Bắt đầu đồng bộ thông tin công ty (Sàn, Ngành)...")
    try:
        ref = Reference()
        df_eq = ref.equity.list_by_exchange(source='VCI')
        df_ind = ref.industry.list()
        
        # Merge by ICB code
        df_eq['icb_code'] = df_eq['icb_code2'].astype(str)
        df_ind['icb_code'] = df_ind['icb_code'].astype(str)
        
        # Keep level 2 or level 4? icb_code2 means level 2? Let's just merge.
        # df_ind contains multiple levels. Let's map icb_code2 directly.
        # df_ind might have duplicate icb_code if not filtered. Actually icb_code is unique.
        
        df_merged = pd.merge(df_eq, df_ind[['icb_code', 'icb_name']], on='icb_code', how='left')
        
        # Format
        df_merged['exchange'] = df_merged['exchange'].replace({'HSX': 'HOSE'})
        df_merged = df_merged[['symbol', 'exchange', 'icb_name']].rename(columns={
            'symbol': 'Mã CP',
            'exchange': 'Sàn',
            'icb_name': 'Ngành'
        })
        df_merged['Ngành'] = df_merged['Ngành'].fillna('Khác')
        
        # Filter valid symbols (3 chars)
        df_merged = df_merged[df_merged['Mã CP'].str.len() == 3]
        
        print(f"Lấy thành công {len(df_merged)} mã. Lưu vào DuckDB...")
        
        con = duckdb.connect(DB_PATH)
        con.execute("DROP TABLE IF EXISTS company_info")
        con.execute("CREATE TABLE company_info AS SELECT * FROM df_merged")
        con.close()
        
        print("Đồng bộ hoàn tất!")
        
    except Exception as e:
        print(f"Lỗi: {e}")

if __name__ == "__main__":
    sync_company_info()
