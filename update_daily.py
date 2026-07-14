import duckdb
from vnstock.ui import Market
from datetime import datetime, timedelta
import time
import os
import pandas as pd

def update_daily():
    lock_file = "update.lock"
    # Kiểm tra xem có tiến trình nào đang chạy không
    if os.path.exists(lock_file):
        print("Đang có tiến trình cập nhật chạy ngầm. Bỏ qua.")
        return
    
    # Tạo cờ khóa
    with open(lock_file, 'w') as f:
        f.write("running")
        
    try:
        con = duckdb.connect("trading_data.duckdb")
        # Lấy ngày mới nhất của từng mã
        df_max = con.execute("SELECT symbol, MAX(time) as last_date FROM historical_prices GROUP BY symbol").df()
        
        mkt = Market()
        today = datetime.now()
        today_str = today.strftime("%Y-%m-%d")
        
        success = 0
        skipped = 0
        
        for idx, row in df_max.iterrows():
            symbol = row['symbol']
            last_date = row['last_date']
            
            if pd.isna(last_date):
                continue
            
            # Ngày cần tải tiếp theo là ngày sau ngày cuối cùng 1 ngày
            next_date = last_date + timedelta(days=1)
            
            # Nếu ngày tiếp theo lớn hơn hôm nay -> Đã có đủ dữ liệu, BỎ QUA
            if next_date.date() > today.date():
                skipped += 1
                continue
                
            start_date_str = next_date.strftime("%Y-%m-%d")
            
            while True:
                try:
                    df = mkt.equity(symbol).ohlcv(start=start_date_str, end=today_str, count=100)
                    if df is not None and not df.empty:
                        df['symbol'] = symbol
                        # Chuẩn hóa cột
                        df = df[['time', 'open', 'high', 'low', 'close', 'volume', 'symbol']]
                        
                        # Xóa dữ liệu trùng ngày (nếu có) để tránh lặp
                        min_time_in_df = df['time'].min().strftime("%Y-%m-%d %H:%M:%S")
                        con.execute(f"DELETE FROM historical_prices WHERE symbol = '{symbol}' AND time >= '{min_time_in_df}'")
                        
                        # Chèn dữ liệu mới
                        con.execute("INSERT INTO historical_prices SELECT * FROM df")
                        success += 1
                        
                        # Đợi 1.2s để không bị Rate Limit (60req/min)
                        time.sleep(1.2)
                    else:
                        # Nếu API trả về rỗng (VD ngày lễ, cuối tuần), cũng tính là skip
                        skipped += 1
                        time.sleep(0.5)
                        
                    break # Thành công -> Thoát vòng lặp while
                except BaseException as e:
                    if isinstance(e, KeyboardInterrupt):
                        raise
                    print(f"Lỗi/Rate limit ở mã {symbol}. Đợi 65s...")
                    time.sleep(65)
                    
        con.close()
        print(f"Hoàn tất! Đã cập nhật thêm {success} mã. Bỏ qua {skipped} mã đã đủ dữ liệu.")
    finally:
        # Xóa cờ khóa khi xong
        if os.path.exists(lock_file):
            os.remove(lock_file)

if __name__ == "__main__":
    update_daily()
