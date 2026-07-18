from vnstock.ui import Market, Reference, Fundamental

print("--- MARKET ---")
print(dir(Market()))

print("\n--- REFERENCE ---")
print(dir(Reference()))
print("Reference.equity:", dir(Reference().equity))

print("\n--- FUNDAMENTAL ---")
print(dir(Fundamental()))
print("Fundamental.equity:", dir(Fundamental().equity("VCB")))
