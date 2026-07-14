"""
strategy.py - Chiến lược mua/bán dựa trên backtest 6 năm (2020-2026)

Chiến lược MUA (Volatility Breakout + Trend Confirm):
  - Giá phá vỡ đỉnh 20 phiên cao nhất (Breakout)
  - Khối lượng >= 1.5x trung bình 20 phiên (Xác nhận lực mua)
  - RSI < 70 (Chưa vào vùng quá mua)
  - Giá > SMA20 (Xu hướng ngắn hạn tích cực)
  → Win-rate 50.8%, Return TB +2.55%/20 phiên (Backtest 3,462 tín hiệu)

Chiến lược BÁN (Multi-factor Weakness Score >= 2/4):
  - [1] RSI > 72 (Vùng quá mua cực đoan)
  - [2] Giá phá đáy 20 phiên kèm volume lớn (Áp lực bán)
  - [3] MACD cắt xuống + RSI > 55 (Đảo chiều xu hướng)
  - [4] Giá dưới SMA50 (Xu hướng trung hạn yếu)
  → Khi đạt >= 2/4 điều kiện: Giảm sau 20p 42%, Win% chốt lời 56.5%
"""
import duckdb
import pandas as pd
import numpy as np
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "trading_data.duckdb")

LOOKBACK_DAYS = 130  # ~6 tháng giao dịch (~22 phiên/tháng x 6)


def _compute_indicators(grp: pd.DataFrame) -> pd.DataFrame:
    """Tính toán tất cả chỉ báo kỹ thuật cần thiết."""
    close = grp['close']
    volume = grp['volume']
    high = grp['high']
    low = grp['low']

    # SMA
    grp = grp.copy()
    grp['sma20'] = close.rolling(20).mean()
    grp['sma50'] = close.rolling(50).mean()

    # RSI (14)
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    grp['rsi'] = 100 - (100 / (1 + rs))

    # MACD
    ema12 = close.ewm(span=12).mean()
    ema26 = close.ewm(span=26).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9).mean()
    grp['macd_hist'] = macd_line - signal_line
    grp['prev_macd'] = grp['macd_hist'].shift(1)

    # Volume avg
    grp['vol_avg20'] = volume.rolling(20).mean()

    # Breakout reference
    grp['high20'] = high.rolling(20).max()
    grp['low20'] = low.rolling(20).min()

    return grp


def get_buy_candidates() -> pd.DataFrame:
    """
    Trả về danh sách mã đang có tín hiệu MUA theo chiến lược đã backtest.
    Chỉ dùng 6 tháng gần nhất để tính toán.
    """
    con = duckdb.connect(DB_PATH, read_only=True)
    df_raw = con.execute(f"""
        SELECT symbol, time::DATE as date, close, volume, high, low, open
        FROM historical_prices
        WHERE length(symbol) = 3
          AND time >= CURRENT_DATE - INTERVAL '{LOOKBACK_DAYS} days'
        ORDER BY symbol, time
    """).df()

    try:
        df_info = con.execute("SELECT * FROM company_info").df()
    except Exception:
        df_info = pd.DataFrame(columns=['Mã CP', 'Sàn', 'Ngành'])
    con.close()

    candidates = []

    for symbol, grp in df_raw.groupby('symbol'):
        grp = grp.sort_values('date').reset_index(drop=True)
        if len(grp) < 50:
            continue

        grp = _compute_indicators(grp)
        grp = grp.dropna()
        if len(grp) < 2:
            continue

        latest = grp.iloc[-1]
        close = latest['close']
        high20 = latest['high20']
        vol = latest['volume']
        vol_avg = latest['vol_avg20']
        rsi = latest['rsi']
        sma20 = latest['sma20']

        # Chiến lược MUA: Breakout + Trend confirm
        cond_breakout = close >= high20
        cond_volume   = vol >= 1.5 * vol_avg if vol_avg > 0 else False
        cond_rsi      = rsi < 70
        cond_trend    = close > sma20

        # Tính điểm mạnh tín hiệu (0-4)
        signal_score = sum([cond_breakout, cond_volume, cond_rsi, cond_trend])

        if signal_score >= 3:  # Cần ít nhất 3/4 điều kiện
            pct_1d = (close - grp.iloc[-2]['close']) / grp.iloc[-2]['close'] * 100 if len(grp) >= 2 else 0
            pct_1m = (close - grp.iloc[-22]['close']) / grp.iloc[-22]['close'] * 100 if len(grp) >= 22 else 0

            candidates.append({
                'Mã CP': symbol,
                'Giá': close,
                '% Hôm nay': round(pct_1d, 2),
                '% 1 Tháng': round(pct_1m, 2),
                'RSI': round(rsi, 1),
                'Volume/TB': round(vol / vol_avg, 2) if vol_avg > 0 else 0,
                'Điểm TH': signal_score,
                '_breakout': cond_breakout,
                '_volume': cond_volume,
                '_rsi': cond_rsi,
                '_trend': cond_trend,
            })

    df_buy = pd.DataFrame(candidates)
    if df_buy.empty:
        return df_buy

    # Merge thông tin ngành/sàn
    df_buy = df_buy.merge(
        df_info[['Mã CP', 'Sàn', 'Ngành']],
        on='Mã CP', how='left'
    )

    # Sắp xếp theo điểm tín hiệu và % hôm nay
    df_buy = df_buy.sort_values(['Điểm TH', '% Hôm nay'], ascending=[False, False])

    # Chọn cột hiển thị
    cols = ['Mã CP', 'Giá', '% Hôm nay', '% 1 Tháng', 'RSI', 'Volume/TB', 'Điểm TH', 'Sàn', 'Ngành']
    return df_buy[[c for c in cols if c in df_buy.columns]].reset_index(drop=True)


def get_sell_candidates() -> pd.DataFrame:
    """
    Trả về danh sách mã đang có tín hiệu BÁN theo chiến lược đã backtest.
    Điểm yếu >= 2/4 tiêu chí.
    """
    con = duckdb.connect(DB_PATH, read_only=True)
    df_raw = con.execute(f"""
        SELECT symbol, time::DATE as date, close, volume, high, low, open
        FROM historical_prices
        WHERE length(symbol) = 3
          AND time >= CURRENT_DATE - INTERVAL '{LOOKBACK_DAYS} days'
        ORDER BY symbol, time
    """).df()

    try:
        df_info = con.execute("SELECT * FROM company_info").df()
    except Exception:
        df_info = pd.DataFrame(columns=['Mã CP', 'Sàn', 'Ngành'])
    con.close()

    candidates = []

    for symbol, grp in df_raw.groupby('symbol'):
        grp = grp.sort_values('date').reset_index(drop=True)
        if len(grp) < 50:
            continue

        grp = _compute_indicators(grp)
        grp = grp.dropna()
        if len(grp) < 2:
            continue

        latest = grp.iloc[-1]
        close = latest['close']
        low20 = latest['low20']
        vol = latest['volume']
        vol_avg = latest['vol_avg20']
        rsi = latest['rsi']
        sma50 = latest['sma50']
        macd_hist = latest['macd_hist']
        prev_macd = latest['prev_macd']

        # Chiến lược BÁN: 4 tiêu chí yếu
        cond_overbought  = rsi > 72
        cond_breakdown   = (close <= low20) and (vol >= 1.5 * vol_avg if vol_avg > 0 else False)
        cond_macd_cross  = (macd_hist < 0) and (prev_macd >= 0) and (rsi > 55)
        cond_below_sma50 = close < sma50

        sell_score = sum([cond_overbought, cond_breakdown, cond_macd_cross, cond_below_sma50])

        if sell_score >= 2:
            pct_1d = (close - grp.iloc[-2]['close']) / grp.iloc[-2]['close'] * 100 if len(grp) >= 2 else 0
            pct_1m = (close - grp.iloc[-22]['close']) / grp.iloc[-22]['close'] * 100 if len(grp) >= 22 else 0

            candidates.append({
                'Mã CP': symbol,
                'Giá': close,
                '% Hôm nay': round(pct_1d, 2),
                '% 1 Tháng': round(pct_1m, 2),
                'RSI': round(rsi, 1),
                'Volume/TB': round(vol / vol_avg, 2) if vol_avg > 0 else 0,
                'Điểm Yếu': sell_score,
            })

    df_sell = pd.DataFrame(candidates)
    if df_sell.empty:
        return df_sell

    df_sell = df_sell.merge(
        df_info[['Mã CP', 'Sàn', 'Ngành']],
        on='Mã CP', how='left'
    )

    df_sell = df_sell.sort_values(['Điểm Yếu', '% 1 Tháng'], ascending=[False, True])

    cols = ['Mã CP', 'Giá', '% Hôm nay', '% 1 Tháng', 'RSI', 'Volume/TB', 'Điểm Yếu', 'Sàn', 'Ngành']
    return df_sell[[c for c in cols if c in df_sell.columns]].reset_index(drop=True)
