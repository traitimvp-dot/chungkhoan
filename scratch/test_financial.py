import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from vnstock import Company

try:
    comp = Company(source="VCI", symbol="FPT")
    # Tries to get income statement
    # from the old API docs:
    df = comp.financial_report(period="quarter", report_type="IncomeStatement")
    print("VCI Income Statement Columns:")
    print(df.columns.tolist())
    print("Length:", len(df.columns) - 1)
except Exception as e:
    print("Error:", e)
    
try:
    comp2 = Company(source="TCBS", symbol="FPT")
    df2 = comp2.financial_report(period="quarter", report_type="IncomeStatement")
    print("TCBS Income Statement Columns:")
    print(df2.columns.tolist())
except Exception as e:
    print("Error:", e)
