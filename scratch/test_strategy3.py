import duckdb
import pandas as pd
import numpy as np
import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from src.strategy import IndicatorMixin, BaseStrategy, run_portfolio_backtest

class TestBuy3(IndicatorMixin, BaseStrategy):
    name = "Tín hiệu Mua 3"
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        valid = df['ma20'].notna() & df['ma50'].notna() & df['ma200'].notna()
        
        # Golden Cross MA20 lên MA50 nhưng chỉ mua khi đang trên MA200 (Thế uptrend dài hạn)
        prev_ma20 = df['ma20'].shift(1)
        prev_ma50 = df['ma50'].shift(1)
        
        ma_cross_up = (df['ma20'] > df['ma50']) & (prev_ma20 <= prev_ma50)
        uptrend = (df['close'] > df['ma200']) & (df['ma50'] > df['ma200'])
        
        # Mua bùng nổ: Giá cắt lên MA20 với khối lượng x2
        vol_avg = df['vol_avg20'].replace(0, 1)
        vol_ratio = df['volume'] / vol_avg
        prev_close = df['close'].shift(1)
        price_break_up = (df['close'] > df['ma20']) & (prev_close <= prev_ma20) & (vol_ratio >= 1.5)
        
        df['buy_signal'] = valid & uptrend & (ma_cross_up | price_break_up)
        df['sell_signal'] = False
        return df

class TestSell3(IndicatorMixin, BaseStrategy):
    name = "Tín hiệu Bán 3"
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        valid = df['ma20'].notna() & df['ma50'].notna()
        
        # 1. Death Cross MA20 cắt xuống MA50
        prev_ma20 = df['ma20'].shift(1)
        prev_ma50 = df['ma50'].shift(1)
        ma_cross_down = (df['ma20'] < df['ma50']) & (prev_ma20 >= prev_ma50)
        
        # 2. Stoploss / Chặn lãi: Thủng MA50 hoặc thủng MA20 với Volume lớn
        prev_close = df['close'].shift(1)
        break_ma50 = (df['close'] < df['ma50']) & (prev_close >= prev_ma50)
        
        vol_avg = df['vol_avg20'].replace(0, 1)
        vol_ratio = df['volume'] / vol_avg
        break_ma20_vol = (df['close'] < df['ma20']) & (prev_close >= prev_ma20) & (vol_ratio >= 1.5)
        
        df['buy_signal'] = False
        df['sell_signal'] = valid & (ma_cross_down | break_ma50 | break_ma20_vol)
        return df

if __name__ == "__main__":
    from src.strategy import BUY_SIGNAL_REGISTRY, SELL_SIGNAL_REGISTRY
    BUY_SIGNAL_REGISTRY["Tín hiệu Mua 3"] = TestBuy3()
    SELL_SIGNAL_REGISTRY["Tín hiệu Bán 3"] = TestSell3()
    
    vn30 = ['SSI', 'FPT', 'VCB', 'ACB', 'MBB', 'TCB', 'VPB', 'HDB', 'STB', 'BID', 'CTG']
    
    total_profit = 0
    total_trades = 0
    wins = 0
    
    for sym in vn30:
        res = run_portfolio_backtest(sym, 100000000, "Tất cả", "Tín hiệu Mua 3", "Tín hiệu Bán 3")
        m = res.get("metrics")
        if m and m['total_trades'] > 0:
            total_profit += m['total_profit_pct']
            total_trades += m['total_trades']
            wins += (m['win_rate'] * m['total_trades'] / 100)
            print(f"{sym}: Lãi {m['total_profit_pct']:.2f}%, Số lệnh {m['total_trades']}, Win {m['win_rate']:.1f}%")
            
    print("-" * 40)
    print(f"TRUNG BÌNH: Lãi {total_profit/len(vn30):.2f}%, Win rate: {wins/total_trades*100:.1f}%")

