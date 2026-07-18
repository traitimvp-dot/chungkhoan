from vnstock.ui import Reference, Fundamental

ref = Reference()
fun = Fundamental()
symbol = "FPT"

print("--- INFO ---")
try:
    df_info = ref.company(symbol).info()
    print(df_info.head())
except Exception as e:
    print("Error info:", e)

print("\n--- DIVIDEND ---")
try:
    df_div = fun.equity(symbol).dividend()
    print(df_div.head())
except Exception as e:
    print("Error dividend:", e)
