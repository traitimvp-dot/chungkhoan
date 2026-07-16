import duckdb

db_path = "data/trading_data.duckdb"
con = duckdb.connect(db_path)

print("Bắt đầu xóa dữ liệu sàn UPCOM...")

# Lấy danh sách mã UPCOM
upcom_query = "SELECT \"Mã CP\" FROM company_info WHERE \"Sàn\" = 'UPCOM'"
upcom_symbols = [row[0] for row in con.execute(upcom_query).fetchall()]
print(f"Tìm thấy {len(upcom_symbols)} mã thuộc sàn UPCOM.")

if len(upcom_symbols) > 0:
    # 1. Xóa khỏi historical_prices
    print("Đang xóa dữ liệu giá lịch sử của sàn UPCOM...")
    # Dùng IN list có thể dài, duckdb xử lý được. Hoặc xóa dựa trên join.
    delete_prices_query = """
    DELETE FROM historical_prices 
    WHERE symbol IN (SELECT "Mã CP" FROM company_info WHERE "Sàn" = 'UPCOM')
    """
    con.execute(delete_prices_query)
    
    # 2. Xóa khỏi company_info
    print("Đang xóa mã UPCOM khỏi bảng company_info...")
    con.execute("DELETE FROM company_info WHERE \"Sàn\" = 'UPCOM'")
    
    print("Đã xóa xong!")
else:
    print("Không còn mã UPCOM nào trong CSDL.")

# Kiểm tra lại số lượng mã còn lại
count_query = "SELECT \"Sàn\", count(*) FROM company_info GROUP BY \"Sàn\""
print("Thống kê số mã hiện tại theo sàn:")
print(con.execute(count_query).df())

con.close()
