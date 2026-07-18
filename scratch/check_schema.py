import duckdb

con = duckdb.connect('d:/TIEN/chungkhoan/data/trading_data.duckdb')
print(con.execute("DESCRIBE company_info").df())
print(con.execute("SELECT * FROM company_info LIMIT 1").df().to_dict('records'))
con.close()
