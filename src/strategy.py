"""
strategy.py — Chiến lược mua/bán dựa trên các chỉ báo kỹ thuật
Kiến trúc Hướng đối tượng (Strategy Pattern) cho phép dễ dàng mở rộng nhiều phương pháp.
"""
import duckdb
import pandas as pd
import numpy as np
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH  = os.path.join(BASE_DIR, "data", "trading_data.duckdb")

LOOKBACK_DAYS = 420  # ~420 ngày lịch = ~280 phiên giao dịch — đủ cho MA200

# ==============================================================================
# HỆ THỐNG CLASS CHIẾN LƯỢC (STRATEGY PATTERN)
# ==============================================================================

class BaseStrategy:
    name: str = "Base"
    
    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Tính toán các chỉ báo kỹ thuật cần thiết cho chiến lược này."""
        return df.copy()
        
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Tính toán và tạo 2 cột 'buy_signal' và 'sell_signal' (boolean)."""
        df = df.copy()
        df['buy_signal'] = False
        df['sell_signal'] = False
        return df

class IndicatorMixin:
    """Mixin tính toán chỉ báo kỹ thuật dùng chung cho cả tín hiệu Mua và Bán."""
    
    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        grp = df.copy()
        close  = grp['close']
        volume = grp['volume']
        high   = grp['high']
        low    = grp['low']

        # ── 3 đường MA chính ───────────────────────────────────────────────
        grp['ma20']  = close.rolling(20).mean()
        grp['ma50']  = close.rolling(50).mean()
        grp['ma200'] = close.rolling(200).mean()

        # ── Slope 5 phiên (xu hướng từng MA) ─────────────────────────────
        grp['slope_ma20']  = grp['ma20'].pct_change(5)
        grp['slope_ma50']  = grp['ma50'].pct_change(5)
        grp['slope_ma200'] = grp['ma200'].pct_change(5)

        # ── Khoảng cách % giá vs từng MA ─────────────────────────────────
        grp['dist_ma20']  = (close - grp['ma20'])  / grp['ma20'].replace(0, np.nan)
        grp['dist_ma50']  = (close - grp['ma50'])  / grp['ma50'].replace(0, np.nan)
        grp['dist_ma200'] = (close - grp['ma200']) / grp['ma200'].replace(0, np.nan)

        # ── Spread giữa các MA ────────────────────────────────────────────
        grp['spread_20_50']  = (grp['ma20'] - grp['ma50'])  / grp['ma50'].replace(0, np.nan)
        grp['spread_20_50_prev'] = grp['spread_20_50'].shift(5)

        # ── Crossover flags ───────────────────────────────────────────────
        prev_gap_20_50  = grp['spread_20_50'].shift(1)
        grp['golden_cross_small'] = (grp['spread_20_50'] > 0) & (prev_gap_20_50 <= 0)
        
        prev_spread_50_200 = ((grp['ma50'] - grp['ma200']) / grp['ma200'].replace(0, np.nan)).shift(1)
        cur_spread_50_200  = (grp['ma50'] - grp['ma200']) / grp['ma200'].replace(0, np.nan)
        grp['golden_cross_big']   = (cur_spread_50_200 > 0) & (prev_spread_50_200 <= 0)
        grp['death_cross_small']  = (grp['spread_20_50'] < 0) & (prev_gap_20_50 >= 0)

        # Price cross MA20/MA50 xuống
        prev_dist_ma20 = grp['dist_ma20'].shift(1)
        grp['price_cross_ma20_dn'] = (grp['dist_ma20'] < 0) & (prev_dist_ma20 >= 0)
        prev_dist_ma50 = grp['dist_ma50'].shift(1)
        grp['price_cross_ma50_dn'] = (grp['dist_ma50'] < 0) & (prev_dist_ma50 >= 0)

        # ── RSI 14 ────────────────────────────────────────────────────────
        delta = close.diff()
        gain  = delta.clip(lower=0).rolling(14).mean()
        loss  = (-delta.clip(upper=0)).rolling(14).mean()
        grp['rsi'] = 100 - (100 / (1 + gain / loss.replace(0, np.nan)))

        # ── Volume & Breakdown/Breakout ──────────────────────────────────
        grp['vol_avg20'] = volume.rolling(20).mean()
        grp['high20'] = high.rolling(20).max()
        grp['low20']  = low.rolling(20).min()
        
        ema12 = close.ewm(span=12).mean()
        ema26 = close.ewm(span=26).mean()
        macd_line = ema12 - ema26
        grp['macd_hist'] = macd_line - macd_line.ewm(span=9).mean()
        grp['prev_macd'] = grp['macd_hist'].shift(1)

        # ── MA Score (0-6) ────────────────────────────────────────────────
        grp['ma_score'] = (
            (close > grp['ma20']).astype(int) +
            (close > grp['ma50']).astype(int) +
            (close > grp['ma200']).astype(int) +
            (grp['slope_ma20'] > 0).astype(int) +
            (grp['slope_ma50'] > 0).astype(int) +
            (grp['slope_ma200'] > 0).astype(int)
        )
        return grp


class BuySignal1(IndicatorMixin, BaseStrategy):
    name = "Tín hiệu Mua 1"
    description = "Breakout 20 phiên + Khối lượng ≥ 1.5x + RSI < 70 + Trên MA20"
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        valid = df['rsi'].notna() & df['vol_avg20'].notna() & df['high20'].notna() & df['ma20'].notna()
        vol_avg = df['vol_avg20'].copy()
        vol_avg[vol_avg <= 0] = 1
        vol_ratio = df['volume'] / vol_avg
        
        # BUY SIGNAL: Breakout 20 phiên + Vol ≥ 1.5x + RSI < 70 + Trên MA20
        df['buy_signal'] = valid & (df['close'] >= df['high20']) & (vol_ratio >= 1.5) & (df['rsi'] < 70) & (df['close'] > df['ma20'])
        df['sell_signal'] = False
        return df


class BuySignal2(IndicatorMixin, BaseStrategy):
    name = "Tín hiệu Mua 2"
    description = "MA20 cắt lên MA50 (Golden Cross ngắn hạn)"
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        valid_buy = df['ma20'].notna() & df['ma50'].notna()
        
        # Lấy giá trị MA20 và MA50 của phiên trước
        prev_ma20 = df['ma20'].shift(1)
        prev_ma50 = df['ma50'].shift(1)
        
        # MA20 cắt lên MA50: MA20 hiện tại > MA50 hiện tại VÀ MA20 trước đó <= MA50 trước đó
        ma_cross_up = (df['ma20'] > df['ma50']) & (prev_ma20 <= prev_ma50)
        
        df['buy_signal'] = valid_buy & ma_cross_up
        df['sell_signal'] = False
        return df


class BuySignal3(IndicatorMixin, BaseStrategy):
    name = "Tín hiệu Mua 3"
    description = "Pullback Uptrend: Chỉnh chạm MA20 trong sóng tăng mạnh (MA20>MA50>MA200)"
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        # Mua khi: MA20 > MA50 > MA200 (Uptrend mạnh) VÀ Giá cắt ngược lên MA20 (Bật tăng sau nhịp chỉnh)
        valid = df['ma20'].notna() & df['ma50'].notna() & df['ma200'].notna()
        uptrend = (df['ma20'] > df['ma50']) & (df['ma50'] > df['ma200'])
        
        prev_close = df['close'].shift(1)
        prev_ma20 = df['ma20'].shift(1)
        price_cross_ma20_up = (df['close'] > df['ma20']) & (prev_close <= prev_ma20)
        
        df['buy_signal'] = valid & uptrend & price_cross_ma20_up
        df['sell_signal'] = False
        return df


class SellSignal1(IndicatorMixin, BaseStrategy):
    name = "Tín hiệu Bán 1"
    description = "Gãy MA20/MA50, MACD cắt xuống, hoặc RSI > 70 + Vol xả ≥ 1.5x"
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        valid_sell = df['rsi'].notna() & df['macd_hist'].notna() & df['prev_macd'].notna() & df['vol_avg20'].notna() & df['ma20'].notna() & df['ma50'].notna()
        vol_avg = df['vol_avg20'].copy()
        vol_avg[vol_avg <= 0] = 1
        vol_ratio = df['volume'] / vol_avg
        
        # 1. Gãy nền MA20 hoặc MA50 (Đảo chiều Trend)
        prev_close = df['close'].shift(1)
        prev_ma20 = df['ma20'].shift(1)
        prev_ma50 = df['ma50'].shift(1)
        break_ma20 = (df['close'] < df['ma20']) & (prev_close >= prev_ma20)
        break_ma50 = (df['close'] < df['ma50']) & (prev_close >= prev_ma50)
        
        # 2. MACD cắt xuống Signal line (Mất động lượng)
        macd_cross_down = (df['macd_hist'] < 0) & (df['prev_macd'] >= 0)
        
        # 3. Quá mua + Khối lượng xả đột biến (Phân phối đỉnh)
        exhaustion = (df['rsi'] > 70) & (vol_ratio >= 1.5)
        
        df['buy_signal'] = False
        df['sell_signal'] = valid_sell & (break_ma20 | break_ma50 | macd_cross_down | exhaustion)
        return df


class SellSignal2(IndicatorMixin, BaseStrategy):
    name = "Tín hiệu Bán 2"
    description = "MA20 cắt xuống MA50 (Death Cross ngắn hạn)"
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        valid_sell = df['ma20'].notna() & df['ma50'].notna()
        
        # Lấy giá trị MA20 và MA50 của phiên trước
        prev_ma20 = df['ma20'].shift(1)
        prev_ma50 = df['ma50'].shift(1)
        
        # MA20 cắt xuống MA50: MA20 hiện tại < MA50 hiện tại VÀ MA20 trước đó >= MA50 trước đó
        ma_cross_down = (df['ma20'] < df['ma50']) & (prev_ma20 >= prev_ma50)
        
        df['buy_signal'] = False
        df['sell_signal'] = valid_sell & ma_cross_down
        return df


class SellSignal3(IndicatorMixin, BaseStrategy):
    name = "Tín hiệu Bán 3"
    description = "Gãy nền MA50 hoặc MA20 cắt xuống MA50"
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        # Bán khi: Giá gãy MA50 (Mất nền giá trung hạn) HOẶC MA20 cắt xuống MA50
        valid = df['ma20'].notna() & df['ma50'].notna()
        
        prev_close = df['close'].shift(1)
        prev_ma50 = df['ma50'].shift(1)
        price_break_ma50 = (df['close'] < df['ma50']) & (prev_close >= prev_ma50)
        
        prev_ma20 = df['ma20'].shift(1)
        ma_cross_down = (df['ma20'] < df['ma50']) & (prev_ma20 >= prev_ma50)
        
        df['buy_signal'] = False
        df['sell_signal'] = valid & (price_break_ma50 | ma_cross_down)
        return df


# ==============================================================================
# REGISTRY TÍN HIỆU MUA / BÁN TÁCH BIỆT
# ==============================================================================

BUY_SIGNAL_REGISTRY = {
    BuySignal1.name: BuySignal1(),
    BuySignal2.name: BuySignal2(),
    BuySignal3.name: BuySignal3()
}

SELL_SIGNAL_REGISTRY = {
    SellSignal1.name: SellSignal1(),
    SellSignal2.name: SellSignal2(),
    SellSignal3.name: SellSignal3()
}

# --- Backward-compat shim: STRATEGY_REGISTRY dùng cho code cũ chưa kịp migrate ---
class _CombinedSignal(IndicatorMixin, BaseStrategy):
    """Chiến lược kết hợp dùng nội bộ cho backtest."""
    name = "_combined"
    def __init__(self, buy: BaseStrategy, sell: BaseStrategy):
        self._buy = buy
        self._sell = sell
    def prepare_data(self, df):
        return self._buy.prepare_data(df)
    def generate_signals(self, df):
        df = self._buy.generate_signals(df)
        df2 = self._sell.generate_signals(df.copy())
        df['sell_signal'] = df2['sell_signal']
        return df


def get_buy_signal(name: str) -> BaseStrategy:
    return BUY_SIGNAL_REGISTRY.get(name, list(BUY_SIGNAL_REGISTRY.values())[0])

def get_sell_signal(name: str) -> BaseStrategy:
    return SELL_SIGNAL_REGISTRY.get(name, list(SELL_SIGNAL_REGISTRY.values())[0])

def get_available_buy_signals() -> list:
    return list(BUY_SIGNAL_REGISTRY.keys())

def get_available_sell_signals() -> list:
    return list(SELL_SIGNAL_REGISTRY.keys())

# Backward compat
STRATEGY_REGISTRY = {}
def get_strategy(name: str) -> BaseStrategy:
    return list(BUY_SIGNAL_REGISTRY.values())[0]
def get_available_strategies() -> list:
    return []



# ==============================================================================
# HỆ THỐNG SCANNER VÀ BACKTEST
# ==============================================================================

def get_buy_candidates(days: int = 3, target_date: str = None, buy_method: str = None) -> pd.DataFrame:
    if buy_method is None:
        buy_method = list(BUY_SIGNAL_REGISTRY.keys())[0]
    con    = duckdb.connect(DB_PATH, read_only=True)
    date_filter = f"AND time >= CURRENT_DATE - INTERVAL '{LOOKBACK_DAYS} days'"
    if target_date:
        date_filter = f"AND time::DATE BETWEEN CAST('{target_date}' AS DATE) - INTERVAL {LOOKBACK_DAYS} DAYS AND CAST('{target_date}' AS DATE)"
        
    df_raw = con.execute(f"""
        SELECT symbol, time::DATE as date, close, volume, high, low, open
        FROM historical_prices
        WHERE length(symbol) = 3
          {date_filter}
        ORDER BY symbol, time
    """).df()
    try:
        df_info = con.execute("SELECT * FROM company_info").df()
    except Exception:
        df_info = pd.DataFrame(columns=['Mã CP', 'Sàn', 'Ngành'])
    con.close()

    candidates = []
    strategy = get_buy_signal(buy_method)

    for symbol, grp in df_raw.groupby('symbol'):
        grp = grp.sort_values('date').reset_index(drop=True)
        if len(grp) < 50:
            continue

        grp = strategy.prepare_data(grp)
        grp = strategy.generate_signals(grp)
        
        check_days = min(days, len(grp))
        if check_days < 1:
            continue
            
        # Lọc các dòng có tín hiệu mua trong N ngày gần nhất
        recent_grp = grp.tail(check_days)
        buy_events = recent_grp[recent_grp['buy_signal']]
        
        for _, row in buy_events.iterrows():
            # Gather metrics for reporting
            info_row = df_info[df_info['Mã CP'] == symbol]
            san = info_row['Sàn'].values[0] if not info_row.empty else "N/A"
            if san == "DELISTED":
                continue
            nganh = info_row['Ngành'].values[0] if not info_row.empty else "N/A"
            
            candidates.append({
                "Ngày": row['date'],
                "Mã CP": symbol,
                "Sàn": san,
                "Ngành": nganh,
                "Giá Đóng Cửa": row['close'],
                "Volume": row['volume'],
                "RSI": row['rsi'],
                "MA Score": row['ma_score'],
                "Vol/Avg20": round(row['volume'] / (row['vol_avg20'] if row['vol_avg20'] > 0 else 1), 2),
                "MA20 Trend": "Tăng" if row['slope_ma20'] > 0 else "Giảm",
                "MA50 Trend": "Tăng" if row['slope_ma50'] > 0 else "Giảm"
            })

    df_candidates = pd.DataFrame(candidates)
    if not df_candidates.empty:
        df_candidates = df_candidates.sort_values(by=['Ngày', 'Mã CP'], ascending=[False, True])
    return df_candidates


def get_sell_candidates(days: int = 3, target_date: str = None, sell_method: str = None) -> pd.DataFrame:
    if sell_method is None:
        sell_method = list(SELL_SIGNAL_REGISTRY.keys())[0]
    con = duckdb.connect(DB_PATH, read_only=True)
    date_filter = f"AND time >= CURRENT_DATE - INTERVAL '{LOOKBACK_DAYS} days'"
    if target_date:
        date_filter = f"AND time::DATE BETWEEN CAST('{target_date}' AS DATE) - INTERVAL {LOOKBACK_DAYS} DAYS AND CAST('{target_date}' AS DATE)"
        
    df_raw = con.execute(f"""
        SELECT symbol, time::DATE as date, close, volume, high, low, open
        FROM historical_prices
        WHERE length(symbol) = 3
          {date_filter}
        ORDER BY symbol, time
    """).df()
    try:
        df_info = con.execute("SELECT * FROM company_info").df()
    except Exception:
        df_info = pd.DataFrame(columns=['Mã CP', 'Sàn', 'Ngành'])
    con.close()

    candidates = []
    strategy = get_sell_signal(sell_method)

    for symbol, grp in df_raw.groupby('symbol'):
        grp = grp.sort_values('date').reset_index(drop=True)
        if len(grp) < 50:
            continue

        grp = strategy.prepare_data(grp)
        grp = strategy.generate_signals(grp)
        
        check_days = min(days, len(grp))
        if check_days < 1:
            continue
            
        # Lọc các dòng có tín hiệu bán trong N ngày gần nhất
        recent_grp = grp.tail(check_days)
        sell_events = recent_grp[recent_grp['sell_signal']]
        
        for _, row in sell_events.iterrows():
            info_row = df_info[df_info['Mã CP'] == symbol]
            san = info_row['Sàn'].values[0] if not info_row.empty else "N/A"
            if san == "DELISTED":
                continue
            nganh = info_row['Ngành'].values[0] if not info_row.empty else "N/A"
            
            candidates.append({
                "Ngày": row['date'],
                "Mã CP": symbol,
                "Sàn": san,
                "Ngành": nganh,
                "Giá Đóng Cửa": row['close'],
                "Volume": row['volume'],
                "RSI": row['rsi'],
                "MA Score": row['ma_score'],
                "Vol/Avg20": round(row['volume'] / (row['vol_avg20'] if row['vol_avg20'] > 0 else 1), 2),
                "MA20 Trend": "Tăng" if row['slope_ma20'] > 0 else "Giảm",
                "MA50 Trend": "Tăng" if row['slope_ma50'] > 0 else "Giảm"
            })

    df_candidates = pd.DataFrame(candidates)
    if not df_candidates.empty:
        df_candidates = df_candidates.sort_values(by=['Ngày', 'Mã CP'], ascending=[False, True])
    return df_candidates


def run_portfolio_backtest(symbol: str, initial_capital: float, timeframe: str,
                           buy_method: str = None, sell_method: str = None) -> dict:
    if buy_method is None:
        buy_method = list(BUY_SIGNAL_REGISTRY.keys())[0]
    if sell_method is None:
        sell_method = list(SELL_SIGNAL_REGISTRY.keys())[0]
    con = duckdb.connect(DB_PATH, read_only=True)
    # Luôn lấy toàn bộ thời gian từ DB để tính toán Indicator chính xác nhất
    query = f"""
        SELECT symbol, time::DATE as date, close, volume, high, low, open
        FROM historical_prices
        WHERE symbol = '{symbol}'
        ORDER BY time
    """
    df = con.execute(query).df()
    con.close()
    
    if df.empty:
        return {"metrics": None, "trades": pd.DataFrame()}
        
    # Loại bỏ các dòng bị trùng lặp ngày để tránh lỗi crash biểu đồ
    df = df.drop_duplicates(subset=['date'], keep='last')

    # 2. Dùng tín hiệu Mua và Bán riêng biệt
    buy_strategy = get_buy_signal(buy_method)
    sell_strategy = get_sell_signal(sell_method)
    df = buy_strategy.prepare_data(df)
    df = buy_strategy.generate_signals(df)
    df_sell = sell_strategy.generate_signals(df.copy())
    df['sell_signal'] = df_sell['sell_signal']
    
    # Lọc lại data theo timeframe thực tế hiển thị
    if timeframe != "Tất cả":
        df['date'] = pd.to_datetime(df['date'])
        if timeframe == "1 Năm":
            start_date = pd.Timestamp.now().normalize() - pd.Timedelta(days=365)
        elif timeframe == "2 Năm":
            start_date = pd.Timestamp.now().normalize() - pd.Timedelta(days=365*2)
        elif timeframe == "3 Năm":
            start_date = pd.Timestamp.now().normalize() - pd.Timedelta(days=365*3)
        elif timeframe == "4 Năm":
            start_date = pd.Timestamp.now().normalize() - pd.Timedelta(days=365*4)
        elif timeframe == "5 Năm":
            start_date = pd.Timestamp.now().normalize() - pd.Timedelta(days=365*5)
        else:
            start_date = df['date'].min()
        df = df[df['date'] >= start_date].copy()

    # 3. Vòng lặp giao dịch (Execution Engine)
    capital = initial_capital
    in_position = False
    buy_price = 0
    buy_date = None
    shares = 0
    trades = []
    
    days_held = 0
    
    for i, row in df.iterrows():
        if pd.isna(row['close']):
            continue
            
        if in_position:
            days_held += 1
            
        # MUA
        if not in_position:
            if row['buy_signal']:
                in_position = True
                buy_price = row['close']
                buy_date = row['date']
                shares = int(capital // buy_price)
                capital -= (shares * buy_price)
                days_held = 0
                
        # BÁN
        elif in_position:
            # T+2 constraint
            if days_held >= 2:
                if row['sell_signal']:
                    sell_price = row['close']
                    sell_date = row['date']
                    capital += (shares * sell_price)
                    
                    profit = (sell_price - buy_price) * shares
                    profit_pct = (sell_price - buy_price) / buy_price * 100
                    
                    trades.append({
                        "Ngày Mua": buy_date,
                        "Giá Mua": buy_price,
                        "Khối lượng": shares,
                        "Ngày Bán": sell_date,
                        "Giá Bán": sell_price,
                        "Lãi/Lỗ (%)": round(profit_pct, 2),
                        "Tiền Lãi/Lỗ": int(profit)
                    })
                    
                    in_position = False
                    shares = 0

    # Tự động chốt nếu còn cầm cổ phiếu cuối kỳ
    if in_position:
        sell_price = df.iloc[-1]['close']
        sell_date = df.iloc[-1]['date']
        capital += (shares * sell_price)
        
        profit = (sell_price - buy_price) * shares
        profit_pct = (sell_price - buy_price) / buy_price * 100
        
        trades.append({
            "Ngày Mua": buy_date,
            "Giá Mua": buy_price,
            "Khối lượng": shares,
            "Ngày Bán": sell_date,
            "Giá Bán": sell_price,
            "Lãi/Lỗ (%)": round(profit_pct, 2),
            "Tiền Lãi/Lỗ": int(profit)
        })
        in_position = False
        shares = 0

    # 4. Tính metrics
    df_trades = pd.DataFrame(trades)
    
    if not df_trades.empty:
        total_trades = len(df_trades)
        winning_trades = len(df_trades[df_trades["Lãi/Lỗ (%)"] > 0])
        win_rate = winning_trades / total_trades * 100
        
        final_capital = capital
        total_profit_pct = (final_capital - initial_capital) / initial_capital * 100
    else:
        total_trades = 0
        win_rate = 0.0
        final_capital = initial_capital
        total_profit_pct = 0.0

    metrics = {
        "final_capital": final_capital,
        "total_profit_pct": total_profit_pct,
        "total_trades": total_trades,
        "win_rate": win_rate
    }
    
    return {
        "metrics": metrics, 
        "trades": df_trades,
        "df_chart": df  # Trả về cả df kỹ thuật để biểu diễn chart trực quan
    }
