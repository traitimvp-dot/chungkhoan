from vnstock.ui import Market
import duckdb
from datetime import datetime, timedelta
import pandas as pd
import time

def main():
    # Danh sách các mã cổ phiếu bạn muốn theo dõi
    # Bạn có thể thêm hoặc bớt các mã khác vào đây
    tickers = ["FPT", "VCB", "HPG", "SSI", "VND"]
    
    print("1. Khởi tạo kết nối tới cơ sở dữ liệu DuckDB...")
    # Sử dụng file mới tên chung là trading_data.duckdb
    con = duckdb.connect("trading_data.duckdb")
    
    mkt = Market()
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    
    print(f"2. Bắt đầu tải và lưu dữ liệu (Từ {start_date} đến {end_date}):")
    
    for symbol in tickers:
        print(f"\n-> Đang xử lý mã cổ phiếu {symbol}...")
        try:
            # Tải dữ liệu
            df = mkt.equity(symbol).ohlcv(start=start_date, end=end_date, count=5000)
            
            if df.empty:
                print(f"   [!] Không có dữ liệu trả về cho mã {symbol}")
                continue
                
            # Thêm cột mã cổ phiếu
            df['symbol'] = symbol
            
            # Tạo cấu trúc bảng nếu chưa tồn tại (Dựa trên cấu trúc của df)
            con.execute("CREATE TABLE IF NOT EXISTS historical_prices AS SELECT * FROM df WHERE 1=0")
            
            # Xóa sạch dữ liệu cũ của mã chứng khoán này để tránh bị trùng lặp (Duplicate)
            # Rất hữu ích nếu bạn lên lịch chạy script này mỗi ngày
            con.execute(f"DELETE FROM historical_prices WHERE symbol = '{symbol}'")
            
            # Chèn (Insert) dữ liệu mới vào bảng
            con.execute("INSERT INTO historical_prices SELECT * FROM df")
            
            print(f"   [+] Lưu thành công {len(df)} phiên giao dịch của {symbol}.")
            
            # Delay nhẹ giữa các lần gọi API để bảo vệ Rate Limit (60 lượt/phút)
            time.sleep(1)
            
        except Exception as e:
            print(f"   [!] Có lỗi xảy ra với mã {symbol}: {e}")
            
    print("\n3. Thống kê CSDL sau khi cập nhật:")
    # Gom nhóm (GROUP BY) để xem mỗi mã có bao nhiêu dòng và ngày cập nhật gần nhất
    query = """
        SELECT symbol, 
               COUNT(*) as total_rows, 
               MIN(time) as start_date, 
               MAX(time) as latest_date 
        FROM historical_prices 
        GROUP BY symbol
    """
    summary = con.execute(query).df()
    print(summary)
    
    con.close()
    print("\n✅ Hoàn tất! Dữ liệu của nhiều mã đã được gom chung vào cơ sở dữ liệu DuckDB.")

if __name__ == "__main__":
    main()
