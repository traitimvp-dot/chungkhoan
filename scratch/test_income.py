import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from vnstock.ui import Fundamental

fun = Fundamental()
try:
    df = fun.equity("FPT").income_statement(period="quarter")
    print(df.head())
    print("Columns:", df.columns.tolist())
except Exception as e:
    print("Error:", e)
