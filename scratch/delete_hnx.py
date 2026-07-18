import duckdb
con = duckdb.connect('data/trading_data.duckdb')
# Delete all HNX records
res = con.execute('''
DELETE FROM historical_prices 
WHERE symbol IN (SELECT "Mã CP" FROM company_info WHERE Sàn = 'HNX')
''')
print("Deleted HNX records")
con.close()
