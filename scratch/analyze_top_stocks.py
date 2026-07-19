import duckdb
import pandas as pd
import sys
import os
from datetime import datetime

# Setup paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
DB_PATH = os.path.join(BASE_DIR, "data", "trading_data.duckdb")

from src.strategy import get_buy_signal, get_sell_signal

def run_backtest_for_year(symbol, year, buy_strategy, sell_strategy):
    con = duckdb.connect(DB_PATH, read_only=True)
    query = f"""
        SELECT symbol, time::DATE as date, close, volume, high, low, open
        FROM historical_prices
        WHERE symbol = '{symbol}'
        ORDER BY time
    """
    df = con.execute(query).df()
    con.close()
    
    if df.empty:
        return 0
        
    df = df.drop_duplicates(subset=['date'], keep='last')
    
    # Generate signals on ALL data to ensure MA is calculated correctly
    df = buy_strategy.prepare_data(df)
    df = buy_strategy.generate_signals(df)
    df_sell = sell_strategy.generate_signals(df.copy())
    df['sell_signal'] = df_sell['sell_signal']
    
    # Filter for the specific year
    df['date'] = pd.to_datetime(df['date'])
    df_year = df[df['date'].dt.year == year].copy()
    
    if df_year.empty:
        return 0
        
    # Execution
    capital = 100_000_000
    in_position = False
    buy_price = 0
    shares = 0
    
    for i, row in df_year.iterrows():
        if pd.isna(row['close']): continue
        
        if not in_position and row['buy_signal']:
            shares = capital // row['close']
            if shares > 0:
                buy_price = row['close']
                capital -= shares * buy_price
                in_position = True
        elif in_position and row['sell_signal']:
            capital += shares * row['close']
            shares = 0
            in_position = False
            
    # Close position at end of year if still holding
    if in_position and not df_year.empty:
        last_close = df_year.iloc[-1]['close']
        capital += shares * last_close
        
    profit_pct = (capital - 100_000_000) / 100_000_000 * 100
    return profit_pct

def main():
    con = duckdb.connect(DB_PATH, read_only=True)
    symbols = con.execute("SELECT DISTINCT symbol FROM historical_prices").df()['symbol'].tolist()
    
    # Load company info for characteristics
    comp_info = con.execute("SELECT * FROM company_info").df()
    con.close()
    
    buy_strat = get_buy_signal("Tín hiệu Mua 2")
    sell_strat = get_sell_signal("Tín hiệu Bán 2")
    
    years = [2021, 2022, 2023, 2024, 2025, 2026]
    
    results = []
    
    print("Starting analysis...")
    for y in years:
        print(f"Analyzing year {y}...")
        year_results = []
        for sym in symbols:
            pct = run_backtest_for_year(sym, y, buy_strat, sell_strat)
            if pct > 0:
                year_results.append({'symbol': sym, 'year': y, 'profit': pct})
                
        # Sort and get top 5
        year_results.sort(key=lambda x: x['profit'], reverse=True)
        top5 = year_results[:5]
        results.extend(top5)
        
        print(f"Top 5 for {y}:")
        for t in top5:
            print(f"  {t['symbol']}: {t['profit']:.2f}%")
            
    # Save results to analyze characteristics
    df_res = pd.DataFrame(results)
    df_res.to_csv(os.path.join(BASE_DIR, "scratch", "top5_yearly.csv"), index=False)
    
    # Merge with company info
    df_merged = df_res.merge(comp_info, left_on='symbol', right_on='Mã CP', how='left')
    
    # Count industries
    print("\n--- Ngành nghề phổ biến của Top 5 ---")
    print(df_merged['Ngành'].value_counts())
    
    print("\n--- Sàn giao dịch phổ biến của Top 5 ---")
    print(df_merged['Sàn'].value_counts())

if __name__ == "__main__":
    main()
