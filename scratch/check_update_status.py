import duckdb
import datetime

db_path = "data/trading_data.duckdb"
con = duckdb.connect(db_path, read_only=True)

# Lấy tổng số mã hợp lệ trong company_info
total_query = """
SELECT count(distinct "Mã CP") 
FROM company_info 
WHERE "Sàn" != 'DELISTED' AND length("Mã CP") = 3
"""
total_symbols = con.execute(total_query).fetchone()[0]

# Lấy ngày mới nhất trong dữ liệu
max_date_query = "SELECT MAX(time) FROM historical_prices WHERE length(symbol) = 3"
max_date = con.execute(max_date_query).fetchone()[0]

# Đếm số mã có dữ liệu trong ngày mới nhất
updated_query = f"""
SELECT count(distinct symbol) 
FROM historical_prices 
WHERE time = '{max_date}' AND length(symbol) = 3
"""
updated_symbols = con.execute(updated_query).fetchone()[0]

# Đếm tổng số mã từng có trong lịch sử (để đối chiếu)
total_history_query = "SELECT count(distinct symbol) FROM historical_prices WHERE length(symbol) = 3"
total_history_symbols = con.execute(total_history_query).fetchone()[0]

today = datetime.date.today().strftime('%Y-%m-%d')
today_query = f"""
SELECT count(distinct symbol) 
FROM historical_prices 
WHERE time::DATE = '{today}'::DATE AND length(symbol) = 3
"""
today_symbols = con.execute(today_query).fetchone()[0]

print(f"1. Tổng số mã theo danh sách công ty (trừ DELISTED): {total_symbols}")
print(f"2. Tổng số mã từng có dữ liệu lịch sử: {total_history_symbols}")
print(f"3. Ngày dữ liệu mới nhất trong DB: {max_date}")
print(f"4. Số mã đã cập nhật tới ngày {max_date}: {updated_symbols}")
print(f"   => Tỷ lệ cập nhật theo ngày mới nhất: {updated_symbols/total_symbols*100:.2f}%")

if str(max_date).split(' ')[0] != today:
    print(f"5. Số mã đã cập nhật đúng ngày hôm nay ({today}): {today_symbols}")

con.close()
