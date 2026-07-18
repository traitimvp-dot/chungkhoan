from vnstock.ui import Reference, Fundamental

ref = Reference()
fun = Fundamental()

symbol = 'FPT'

print("--- OVERVIEW ---")
try:
    df_overview = ref.company(symbol).overview()
    print(df_overview.head())
    print(df_overview.columns.tolist())
except Exception as e:
    print("Error overview:", e)

print("\n--- PROFILE ---")
try:
    df_profile = ref.company(symbol).profile()
    print(df_profile.head())
    print(df_profile.columns.tolist())
except Exception as e:
    print("Error profile:", e)

print("\n--- RATIO ---")
try:
    df_ratio = fun.equity(symbol).ratio()
    print(df_ratio.head())
    print(df_ratio.columns.tolist())
except Exception as e:
    print("Error ratio:", e)
