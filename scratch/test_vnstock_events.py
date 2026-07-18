from vnstock.ui import Reference

ref = Reference()
symbol = "FPT"

print("--- EVENTS ---")
try:
    df_events = ref.company(symbol).events()
    print(df_events.head())
    print(df_events.columns.tolist())
except Exception as e:
    print("Error events:", e)

print("\n--- CAPITAL HISTORY ---")
try:
    df_capital = ref.company(symbol).capital_history()
    print(df_capital.head())
    print(df_capital.columns.tolist())
except Exception as e:
    print("Error capital:", e)
    
print("\n--- GLOBAL EVENTS ---")
try:
    df_global_events = ref.events().dividend(symbol)
    print(df_global_events.head())
except Exception as e:
    print("Error global events:", e)
