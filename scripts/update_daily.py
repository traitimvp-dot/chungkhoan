import duckdb
from vnstock.ui import Market
from datetime import datetime, timedelta
import time
import os
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Bắt lỗi Rate Limit chính xác - class thực tế trong vnstock.core.exceptions
try:
    from vnstock.core.exceptions import RateLimitError
except ImportError:
    # Fallback an toàn nếu phiên bản thư viện thay đổi tên
    RateLimitError = Exception

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "trading_data.duckdb")

# Lock để đồng bộ việc ghi vào DuckDB (DuckDB không hỗ trợ multi-writer)
_db_lock = threading.Lock()
# Biến đếm toàn cục (dùng Lock để thread-safe)
_counter_lock = threading.Lock()
_success = 0
_skipped = 0
_failed = 0


class RateLimiter:
    """
    Token Bucket Rate Limiter — đảm bảo không vượt quá MAX_RATE req/phút.
    
    Cơ chế: Mỗi giây, bucket được nạp thêm (MAX_RATE / 60) tokens.
    Mỗi request tiêu thụ 1 token. Nếu bucket trống, thread tự ngủ chờ.
    
    Free tier vnstock: 60 req/phút → dùng 50 để có biên an toàn 17%.
    """
    def __init__(self, max_per_minute: int = 50):
        self._rate = max_per_minute / 60.0  # tokens/giây
        self._tokens = float(max_per_minute)
        self._max_tokens = float(max_per_minute)
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self):
        """Chờ cho đến khi có token, rồi tiêu thụ 1 token."""
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill
            self._tokens = min(self._max_tokens, self._tokens + elapsed * self._rate)
            self._last_refill = now

            if self._tokens < 1:
                wait = (1 - self._tokens) / self._rate
            else:
                wait = 0

        if wait > 0:
            time.sleep(wait)

        with self._lock:
            self._tokens -= 1


_rate_limiter = None  # Khởi tạo trong update_daily()


def fetch_and_save(symbol: str, start_date_str: str, today_str: str, mkt: Market, idx: int, total: int) -> str:
    """Hàm xử lý cho một mã duy nhất — chạy trong thread riêng."""
    global _success, _skipped, _failed
    retries = 0
    while True:
        try:
            # Tuân thủ rate limit trước khi gọi API
            _rate_limiter.acquire()

            df = mkt.equity(symbol).ohlcv(start=start_date_str, end=today_str)
            if df is not None and not df.empty:
                df['symbol'] = symbol
                df = df[['time', 'open', 'high', 'low', 'close', 'volume', 'symbol']]

                min_time_in_df = df['time'].min().strftime("%Y-%m-%d %H:%M:%S")

                # Chỉ một thread được ghi vào DB tại một thời điểm
                with _db_lock:
                    with duckdb.connect(DB_PATH) as con:
                        con.execute(f"DELETE FROM historical_prices WHERE symbol = '{symbol}' AND time >= '{min_time_in_df}'")
                        con.execute("INSERT INTO historical_prices SELECT * FROM df")

                with _counter_lock:
                    _success += 1
                    s = _success
                return f"[{s}/{total}] OK {symbol} ({start_date_str} -> {today_str})"
            else:
                with _counter_lock:
                    _skipped += 1
                    sk = _skipped
                return f"[{sk}/{total}] SKIP {symbol} (Chua co du lieu moi)"

        except KeyboardInterrupt:
            raise
        except RateLimitError:
            # Rate Limit bị vượt ở phía server: chờ 60s rồi thử lại
            retries += 1
            if retries >= 3:
                with _counter_lock:
                    _failed += 1
                return f"FAIL {symbol} do Rate Limit sau 3 lan thu"
            print(f"[Rate Limit] {symbol}: Chờ 60s rồi thử lại (lần {retries}/3)...")
            time.sleep(60)
        except Exception as e:
            # Lỗi kết nối hoặc lỗi khác: chờ 15s rồi thử lại
            retries += 1
            if retries >= 3:
                with _counter_lock:
                    _failed += 1
                return f"FAIL {symbol} sau 3 lan thu: {e}"
            print(f"[Lỗi] {symbol}: {e}. Chờ 15s rồi thử lại (lần {retries}/3)...")
            time.sleep(15)


def update_daily(max_workers: int = 1):
    """
    Cập nhật dữ liệu hàng ngày tuần tự để tránh Rate Limit của vnstock.
    """
    global _success, _skipped, _failed, _rate_limiter
    _success = 0
    _skipped = 0
    _failed = 0

    # Khởi tạo Rate Limiter: 40 req/phút để an toàn
    _rate_limiter = RateLimiter(max_per_minute=40)

    lock_file = os.path.join(BASE_DIR, "scripts", "update.lock")

    if os.path.exists(lock_file):
        print("Dang co tien trinh cap nhat chay ngam. Bo qua.")
        return

    with open(lock_file, 'w') as f:
        f.write("running")

    try:
        with duckdb.connect(DB_PATH) as con:
            query_max = """
                SELECT c."Mã CP" as symbol, MAX(h.time) as last_date 
                FROM company_info c 
                LEFT JOIN historical_prices h ON c."Mã CP" = h.symbol 
                WHERE length(c."Mã CP") = 3 
                  AND c."Sàn" IN ('HOSE', 'HNX')
                GROUP BY c."Mã CP"
            """
            df_max = con.execute(query_max).df()

        mkt = Market()
        today = datetime.now()
        today_str = today.strftime("%Y-%m-%d")

        # Xây dựng danh sách công việc cần làm
        tasks = []
        pre_skipped = 0
        for _, row in df_max.iterrows():
            symbol = row['symbol']
            last_date = row['last_date']

            if pd.isna(last_date):
                start_date_str = "2020-01-01"
            else:
                next_date = last_date + timedelta(days=1)
                if next_date.date() > today.date():
                    pre_skipped += 1
                    continue
                start_date_str = next_date.strftime("%Y-%m-%d")

            tasks.append((symbol, start_date_str))

        total = len(tasks)
        # Ước tính thời gian: 50 req/phút → 1 req/1.2s
        est_minutes = total / 50
        print(f"Can cap nhat: {total} ma | Bo qua (da du lieu): {pre_skipped} ma")
        print(f"Rate limit: 50 req/phut | Uoc tinh: ~{est_minutes:.0f} phut")
        print(f"Chay song song voi {max_workers} luong...\n")

        t_start = time.time()
        # Dùng vòng lặp đồng bộ thay vì ThreadPoolExecutor để kiểm soát hoàn toàn rate limit
        for i, (sym, start) in enumerate(tasks):
            try:
                # Ngủ cứng 1.5 giây giữa mỗi request (tối đa 40 req/phút)
                time.sleep(1.5)
                
                df_res = mkt.equity(sym).ohlcv(start=start, end=today_str)
                if df_res is not None and not df_res.empty:
                    df_res['symbol'] = sym
                    df_res = df_res[['time', 'open', 'high', 'low', 'close', 'volume', 'symbol']]
                    min_time_in_df = df_res['time'].min().strftime("%Y-%m-%d %H:%M:%S")

                    with duckdb.connect(DB_PATH) as con_write:
                        con_write.execute(f"DELETE FROM historical_prices WHERE symbol = '{sym}' AND time >= '{min_time_in_df}'")
                        con_write.execute("INSERT INTO historical_prices SELECT * FROM df_res")
                    
                    _success += 1
                    print(f"[{i+1}/{total}] OK {sym} ({start} -> {today_str})")
                else:
                    _skipped += 1
                    print(f"[{i+1}/{total}] SKIP {sym} (Chua co du lieu moi)")
            
            except SystemExit:
                # Bắt SystemExit nếu vnstock ép thoát chương trình
                print(f"[Rate Limit / SystemExit] vnstock đã ép dừng khi gọi {sym}. Tạm nghỉ 65 giây...")
                time.sleep(65)
            except Exception as e:
                _failed += 1
                print(f"[{i+1}/{total}] FAIL {sym}: {e}")

        elapsed = time.time() - t_start
        print(f"\n=== HOAN TAT ===")
        print(f"  Thanh cong: {_success} ma")
        print(f"  Bo qua (du du lieu): {pre_skipped + _skipped} ma")
        print(f"  That bai: {_failed} ma")
        print(f"  Thoi gian: {elapsed:.0f}s ({elapsed/60:.1f} phut)")
        if total > 0:
            print(f"  Toc do trung binh: {elapsed/total:.1f}s/ma")

    finally:
        if os.path.exists(lock_file):
            os.remove(lock_file)


if __name__ == "__main__":
    update_daily(max_workers=5)
