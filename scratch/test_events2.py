from vnstock.ui import Reference

ref = Reference()
symbol = "FPT"

print("--- ref.events().symbol(FPT) ---")
try:
    df = ref.events().symbol(symbol)
    print(df.head())
    print(df.columns.tolist())
except Exception as e:
    print("Error:", e)

print("\n--- ref.events().calendar() ---")
try:
    df2 = ref.events().calendar()
    print(df2.head())
except Exception as e:
    print("Error:", e)
