try:
    from vnstock.ui import Reference
    ref = Reference(source="VCI")
    events = ref.company("FPT").events()
    print("VCI Events with Reference:")
    print(events.head())
    print(events.columns.tolist())
except Exception as e:
    print("Reference error:", e)

try:
    from vnstock import Company
    comp = Company(source="VCI", symbol="FPT")
    events = comp.events()
    print("\nVCI Events with Company:")
    print(events.head())
    print(events.columns.tolist())
except Exception as e:
    print("Company error:", e)
