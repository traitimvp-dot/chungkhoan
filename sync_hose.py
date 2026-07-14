import duckdb
from vnstock.ui import Reference, Market
from datetime import datetime
import time

def sync_hose():
    print("Bắt đầu tiến trình đồng bộ toàn bộ mã HOSE từ 2020...")
    ref = Reference()
    try:
        # Lấy danh sách HOSE (Sử dụng nguồn VCI cho danh sách)
        df_all = ref.equity.list_by_exchange(source='VCI')
        # Lọc sàn HSX (tức là HOSE) và loại trừ trái phiếu (BOND)
        df_hose = df_all[(df_all['exchange'] == 'HSX') & (df_all['type'] != 'BOND')]
        tickers = df_hose['symbol'].tolist()
    except Exception as e:
        print("Lỗi lấy danh sách HOSE:", e)
        return
        
    print(f"Tổng cộng tìm thấy {len(tickers)} mã trên HOSE.")
    print("Tiến trình sẽ chạy ngầm, vui lòng không tắt terminal...")
    
    mkt = Market()
    start_date = "2020-01-01"
    end_date = datetime.now().strftime("%Y-%m-%d")
    success_count = 0
    fail_count = 0
    
    # Tạo bảng an toàn nếu nó chưa tồn tại (Dựa theo các cột chuẩn)
    con = duckdb.connect("trading_data.duckdb")
    con.execute("""
        CREATE TABLE IF NOT EXISTS historical_prices (
            time TIMESTAMP,
            open DOUBLE,
            high DOUBLE,
            low DOUBLE,
            close DOUBLE,
            volume BIGINT,
            symbol VARCHAR
        )
    """)
    con.close()
    
    for i, symbol in enumerate(tickers):
        print(f"[{i+1}/{len(tickers)}] Tải dữ liệu {symbol}...")
        while True:
            try:
                # count=5000 để lấy đủ dữ liệu từ 2020
                df = mkt.equity(symbol).ohlcv(start=start_date, end=end_date, count=5000)
                
                if df is None or df.empty:
                    print(f"  -> Bỏ qua {symbol} (Trống)")
                    fail_count += 1
                else:
                    df['symbol'] = symbol
                    # Đảm bảo thứ tự cột trước khi insert
                    df = df[['time', 'open', 'high', 'low', 'close', 'volume', 'symbol']]
                    
                    # Mở kết nối, ghi dữ liệu, và đóng lại ngay lập tức
                    # Việc này giúp giải phóng file để trang web có thể đọc dữ liệu đồng thời!
                    con = duckdb.connect("trading_data.duckdb")
                    # UPSERT dữ liệu: Xóa cũ -> Thêm mới
                    con.execute(f"DELETE FROM historical_prices WHERE symbol = '{symbol}'")
                    con.execute("INSERT INTO historical_prices SELECT * FROM df")
                    con.close()
                    
                    success_count += 1
                
                # Cố tình chờ 2 giây để không quá tải 60 req/min
                time.sleep(2)
                break # Thoát khỏi vòng lặp while để sang mã tiếp theo
                
            except BaseException as e:
                if isinstance(e, KeyboardInterrupt):
                    raise
                # Vnstock v4 ném SystemExit khi chạm rate limit
                print(f"  -> Chạm Rate Limit hoặc lỗi ({symbol}). Hệ thống sẽ ngủ 65 giây rồi tự động thử lại...")
                time.sleep(65)
            
    print(f"\n✅ ĐỒNG BỘ THÀNH CÔNG! Đã tải {success_count}/{len(tickers)} mã HOSE.")

if __name__ == "__main__":
    sync_hose()
