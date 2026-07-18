from vnstock.ui import Reference, Fundamental

ref = Reference()
fun = Fundamental()
symbol = "FPT"

print("--- SHAREHOLDERS ---")
try:
    df_sh = ref.company(symbol).shareholders()
    print(df_sh.head())
except Exception as e:
    print("Error sh:", e)

print("\n--- FUNDAMENTAL RATIOS ---")
try:
    df_ratio = fun.equity(symbol).ratio()
    print(df_ratio.head())
except Exception as e:
    print("Error ratio:", e)
    
print("\n--- FUNDAMENTAL DIVIDEND ---")
try:
    df_div = fun.equity(symbol).dividend()
    print(df_div.head())
except Exception as e:
    print("Error dividend:", e)
