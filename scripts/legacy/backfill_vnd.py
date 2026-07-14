from vnstock.ui import Market
import duckdb
from datetime import datetime

def main():
    symbol = "VND"
    start_date = "2020-01-01"
    end_date = datetime.now().strftime("%Y-%m-%d")
    
    print(f"1. Đang tải dữ liệu lịch sử mã {symbol} từ {start_date} đến {end_date}...")
    mkt = Market()
    # Tăng count=5000 để đảm bảo lấy hết dữ liệu từ 2020 (khoảng ~1500 phiên)
    df = mkt.equity(symbol).ohlcv(start=start_date, end=end_date, count=5000)
    
    if df.empty:
        print("Không có dữ liệu trả về.")
        return
        
    # Chuẩn hóa format
    df['symbol'] = symbol
    
    print("2. Kết nối tới cơ sở dữ liệu DuckDB...")
    con = duckdb.connect("trading_data.duckdb")
    
    # Xóa sạch dữ liệu VND 1 năm trước đó để tránh lẫn lộn
    con.execute(f"DELETE FROM historical_prices WHERE symbol = '{symbol}'")
    
    # Lưu toàn bộ dữ liệu 6 năm qua vào
    print("3. Đang lưu dữ liệu mới...")
    con.execute("INSERT INTO historical_prices SELECT * FROM df")
    
    # Kiểm tra lại số dòng
    count = con.execute(f"SELECT count(*) FROM historical_prices WHERE symbol = '{symbol}'").fetchone()[0]
    print(f"\n✅ Cập nhật thành công! Tổng cộng có {count} phiên giao dịch của {symbol} trong CSDL.")
    
    con.close()

if __name__ == "__main__":
    main()
