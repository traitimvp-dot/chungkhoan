import duckdb
import pandas as pd
import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from src.strategy import get_buy_signal, get_sell_signal, IndicatorMixin, BaseStrategy

class BuySignal4(IndicatorMixin, BaseStrategy):
    name = "Tín hiệu Mua 4"
    description = "Siêu Breakout (Vượt đỉnh 20 phiên + Vol lớn + MA20>MA50>MA200)"
    
    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        df = super().prepare_data(df)
        if 'ma20' not in df.columns:
            df['ma20'] = df['close'].rolling(window=20).mean()
        if 'ma50' not in df.columns:
            df['ma50'] = df['close'].rolling(window=50).mean()
        if 'ma200' not in df.columns:
            df['ma200'] = df['close'].rolling(window=200).mean()
        if 'vol_ma20' not in df.columns:
            df['vol_ma20'] = df['volume'].rolling(window=20).mean()
            
        # Vượt đỉnh 20 phiên
        df['high_20'] = df['high'].rolling(window=20).max().shift(1)
        return df
        
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        uptrend = (df['ma20'] > df['ma50']) & (df['ma50'] > df['ma200'])
        breakout = df['close'] > df['high_20']
        vol_surge = df['volume'] > 1.5 * df['vol_ma20']
        
        # Mua khi thỏa mãn
        df['buy_signal'] = uptrend & breakout & vol_surge
        
        # Chỉ lấy tín hiệu đầu tiên trong một chuỗi tăng (để không mua liên tục)
        df['buy_signal'] = df['buy_signal'] & ~df['buy_signal'].shift(1).fillna(False)
        df['sell_signal'] = False
        return df

def test_strategy():
    DB_PATH = os.path.join(BASE_DIR, "data", "trading_data.duckdb")
    con = duckdb.connect(DB_PATH, read_only=True)
    query = """
        SELECT symbol, time::DATE as date, close, volume, high, low, open
        FROM historical_prices
        WHERE symbol IN ('FPT', 'SSI', 'HPG', 'DIG', 'VND', 'MWG', 'DGC', 'FRT', 'GEX', 'VCI', 'TCB', 'VCB', 'STB', 'HSG')
        ORDER BY symbol, time
    """
    df_all = con.execute(query).df()
    con.close()
    
    buy2 = get_buy_signal("Tín hiệu Mua 2")
    buy4 = BuySignal4()
    sell2 = get_sell_signal("Tín hiệu Bán 2") # Dùng chung Bán 2 cho khách quan
    
    results = []
    
    for symbol, df in df_all.groupby('symbol'):
        df = df.sort_values('date').copy()
        
        df_buy2 = buy2.prepare_data(df.copy())
        df_buy2 = buy2.generate_signals(df_buy2)
        df_sell = sell2.generate_signals(df_buy2.copy())
        
        def simulate(df_b, df_s):
            capital = 100_000_000
            shares = 0
            trades = 0
            wins = 0
            buy_price = 0
            in_pos = False
            for i, row in df_b.iterrows():
                if not in_pos and row['buy_signal']:
                    shares = capital // row['close']
                    buy_price = row['close']
                    capital -= shares * buy_price
                    in_pos = True
                elif in_pos and df_s.loc[i, 'sell_signal']:
                    capital += shares * row['close']
                    if row['close'] > buy_price:
                        wins += 1
                    shares = 0
                    in_pos = False
                    trades += 1
            if in_pos:
                capital += shares * df_b.iloc[-1]['close']
            win_rate = (wins/trades*100) if trades>0 else 0
            return (capital - 100_000_000)/1_000_000, trades, win_rate
            
        profit2, trades2, wr2 = simulate(df_buy2, df_sell)
        
        df_buy4 = buy4.prepare_data(df.copy())
        df_buy4 = buy4.generate_signals(df_buy4)
        profit4, trades4, wr4 = simulate(df_buy4, df_sell)
        
        results.append({
            'Symbol': symbol,
            'Buy2 Profit(M)': round(profit2, 1),
            'Buy2 WR(%)': round(wr2, 1),
            'Buy4 Profit(M)': round(profit4, 1),
            'Buy4 WR(%)': round(wr4, 1)
        })
        
    res_df = pd.DataFrame(results)
    print(res_df)
    
    sum_b2 = res_df['Buy2 Profit(M)'].sum()
    sum_b4 = res_df['Buy4 Profit(M)'].sum()
    print(f"\nTotal Buy2 Profit: {sum_b2:.1f} M")
    print(f"Total Buy4 Profit: {sum_b4:.1f} M")
    print(f"Buy2 Avg WR: {res_df['Buy2 WR(%)'].mean():.1f}%")
    print(f"Buy4 Avg WR: {res_df['Buy4 WR(%)'].mean():.1f}%")

if __name__ == '__main__':
    test_strategy()
