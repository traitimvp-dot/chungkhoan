import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

import vnstock
print(dir(vnstock))
try:
    print(dir(vnstock.ui))
except:
    pass

try:
    df = vnstock.financial_report("FPT", "IncomeStatement", "quarterly")
    print(df.head())
except Exception as e:
    print("Old api fail:", e)
