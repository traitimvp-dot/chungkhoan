from vnstock.ui import Reference
ref = Reference()
symbol = "FPT"
df_info = ref.company(symbol).info()
print("Columns:", df_info.columns.tolist())
print(df_info.iloc[0].to_dict())
