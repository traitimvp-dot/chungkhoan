from vnstock.ui import Market
import duckdb
from datetime import datetime, timedelta

def main():
    print("1. Khởi tạo kết nối tới cơ sở dữ liệu DuckDB...")
    # Tạo (hoặc mở) file CSDL nội bộ mang tên fpt_trading_data.duckdb
    con = duckdb.connect("fpt_trading_data.duckdb")
    
    print("2. Đang kéo dữ liệu cổ phiếu FPT (1 năm qua) trực tiếp từ vnstock...")
    mkt = Market()
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    
    # Tải dữ liệu dạng pandas DataFrame
    df = mkt.equity("FPT").ohlcv(start=start_date, end=end_date)
    
    # Thêm cột mã cổ phiếu để tiện phân biệt nếu sau này bạn thêm mã khác
    df['symbol'] = 'FPT'
    
    print("3. Đang lưu dữ liệu vào bảng 'historical_prices'...")
    # DuckDB cho phép đọc thẳng từ biến 'df' của Python mà không cần parse
    # Dùng "CREATE OR REPLACE TABLE" để làm mới bảng mỗi lần chạy
    con.execute("CREATE OR REPLACE TABLE historical_prices AS SELECT * FROM df")
    
    print("\n4. Truy vấn thử CSDL DuckDB (Lấy 5 phiên mới nhất):")
    # Viết câu lệnh SQL thuần túy
    query = """
        SELECT symbol, time, close, volume 
        FROM historical_prices 
        ORDER BY time DESC 
        LIMIT 5
    """
    result = con.execute(query).df()
    print(result)
    
    # Thực hiện phép tính tổng hợp (Aggregation) bằng SQL
    avg_price = con.execute("SELECT AVG(close) FROM historical_prices").fetchone()[0]
    print(f"\n=> Thống kê bằng SQL: Giá đóng cửa trung bình của FPT trong 1 năm qua là: {avg_price:.2f} VND")
    
    # Đóng kết nối để giải phóng tài nguyên
    con.close()
    print("\n✅ Hoàn tất! Toàn bộ dữ liệu đã nằm gọn trong file 'fpt_trading_data.duckdb'")

if __name__ == "__main__":
    main()
