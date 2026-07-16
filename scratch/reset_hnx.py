import duckdb

db_path = "data/trading_data.duckdb"
con = duckdb.connect(db_path)

print("Bắt đầu xóa dữ liệu lịch sử của sàn HNX để cập nhật lại từ 2020...")

delete_hnx_query = """
DELETE FROM historical_prices 
WHERE symbol IN (SELECT "Mã CP" FROM company_info WHERE "Sàn" = 'HNX')
"""
con.execute(delete_hnx_query)
print("Đã xóa xong dữ liệu cũ của sàn HNX.")
con.close()
