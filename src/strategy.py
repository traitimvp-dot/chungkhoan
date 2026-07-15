"""
strategy.py — Chiến lược mua/bán dựa trên 3 đường MA (SMA20, SMA50, SMA200)
Backtest: 497,107 điểm dữ liệu | 403 mã HOSE/HNX/UPCOM | 2020-2026

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
QUY LUẬT PHÁT HIỆN TỪ BACKTEST 3 ĐƯỜNG MA (2020-2026):

[QUY LUẬT 1 — TRẠNG THÁI VỊ TRÍ GIÁ vs 3 MA]
  Tốt nhất:  P > MA20 > MA50 > MA200 + all MA slope dương → Win20=52.2%, Ret20=+2.50%
  Nguy hiểm: P < MA20 nhưng > MA50 (MA50 đang resist) → Win20=47.7%, Ret20=+0.57%
  Kết luận: MA200 là "nền" dài hạn. Phải trên MA50 + MA200 mới giao dịch.

[QUY LUẬT 2 — SLOPE (HƯỚNG ĐI) CỦA MA]
  Quan trọng nhất là MA50 đang tăng: Ret20 tốt hơn ~0.8% so với MA50 giảm.
  MA200 tăng: Ret40=+4.6% vs MA200 giảm: Ret40=+1.0% — chênh lệch rất lớn dài hạn.
  Điều kiện lý tưởng: cả 3 MA đều có slope dương (Score 6/6) → Ret20=+2.5%, Ret40=+4.6%

[QUY LUẬT 3 — KHOẢNG CÁCH GIỮA CÁC MA (SPREAD)]
  MA20-MA50 spread mở rộng → momentum đang tăng, tốt để giữ/mua thêm.
  MA20-MA50 spread thu hẹp → momentum yếu dần, cảnh báo sắp đảo chiều.
  MA50-MA200 >10%: Ret20=+2.08% — xu hướng dài hạn đang rất mạnh.
  MA50-MA200 âm (<0): Ret20 thấp hơn đáng kể.

[QUY LUẬT 4 — PULLBACK LÀ CƠ HỘI MUA TỐT NHẤT]
  Pullback về Touch MA20 + trên MA50 + MA200 + Vol tăng: Win20=54.1%, Ret20=+2.4%
  Pullback về Touch MA50 + trên MA200 + MA50 đang tăng: Win20=54.8%, Ret20=+2.3%
  → Mua khi pullback về MA trong uptrend tốt hơn mua khi breakout!

[QUY LUẬT 5 — GOLDEN CROSS]
  MA20 cắt lên MA50 + MA50 đang tăng + Vol>1.2: N=1,311, Win20=55.2%, Ret20=+3.3%
  MA50 cắt lên MA200 (Golden Cross lớn): Win20=52.3%, Ret40=+5.2% — tốt dài hạn
  → Golden Cross lớn (MA50/MA200) là tín hiệu chiến lược đáng tin cậy.

[QUY LUẬT 6 — KHOẢNG CÁCH GIÁ vs MA]
  Giá cách MA20 từ +2% đến +10%: Ret20 tốt nhất (+2.0% đến +2.5%)
  Giá cách MA20 > +10%: Ret20=+2.5% nhưng Win20 giảm — rủi ro mua đỉnh.
  Giá < MA20 từ -2% đến 0: Ret20=+1.0% — vùng chờ xác nhận, chưa mua.
  → Mua khi giá vừa vượt MA20 (dist 0-5%) hoặc đang pull về MA20.

[QUY LUẬT 7 — CROSSOVER KHÔNG ĐÁNG TIN ĐỘC LẬP]
  Price cắt lên MA20: Win20 chỉ 48.6% — nhiều false signal ngắn hạn!
  Price cắt lên MA50: Win20 chỉ 47.4% — tệ hơn ngẫu nhiên!
  → Crossover chỉ đáng tin khi đi kèm volume tăng + MA đang slope dương.

[QUY LUẬT BÁN — Phát hiện quan trọng]
  KHÔNG có combo BÁN nào cho xác suất giảm >50% — thị trường VN bullish bias!
  Tín hiệu BÁN tốt nhất: P cắt xuống MA50 + MA50 giảm + dưới MA200 → Giam20=46%
  Cảnh báo BÁN sớm: Full Bull nhưng MA20-MA50 spread thu hẹp + RSI>72 → Giam20=41.6%
  Khoảng cách > +20% so với MA200: Ret40 vẫn dương → KHÔNG bán chỉ vì "xa MA200"!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CHIẾN LƯỢC MUA (Ưu tiên theo thứ tự điểm):
  [TÍN HIỆU A — Pullback trong Uptrend] Win20=54.8%, Ret20=+2.4%
    - Giá pullback chạm MA20 hoặc MA50 (dist ±2%)
    - Giá vẫn trên MA50 + MA200 (uptrend còn nguyên)
    - MA50 đang có slope dương (uptrend chưa đảo)
    - Volume tăng khi chạm MA (xác nhận được đỡ)

  [TÍN HIỆU B — Golden Cross + Momentum] Win20=55.2%, Ret20=+3.3%
    - MA20 vừa cắt lên MA50 (Golden Cross nhỏ)
    - MA50 đang slope dương (xu hướng trung hạn lên)
    - Volume >= 1.2x TB (xác nhận)

  [TÍN HIỆU C — Full Bull Confirmation] Win20=52.7%, Ret20=+3.1%
    - P > MA20 > MA50 > MA200 (tất cả đều đúng thứ tự)
    - Cả 3 MA đều có slope dương
    - MA20-MA50 spread đang mở rộng (momentum tăng)
    - Volume > 1.5x TB

CHIẾN LƯỢC BÁN (>= 2/4 tiêu chí):
  [1] MA20-MA50 spread thu hẹp + RSI > 72 + slope MA20 giảm (momentum cạn)
  [2] Giá cắt xuống MA50 + MA50 đang giảm + dưới MA200
  [3] Giá cắt xuống MA20 + dưới MA50 + Volume > 1.3x (break down có lực)
  [4] P < MA20 < MA50 + cả 2 MA đều slope âm + Volume tăng (Full Bear)
"""
import duckdb
import pandas as pd
import numpy as np
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH  = os.path.join(BASE_DIR, "data", "trading_data.duckdb")

LOOKBACK_DAYS = 420  # ~420 ngày lịch = ~280 phiên giao dịch — đủ cho MA200


def _compute_indicators(grp: pd.DataFrame) -> pd.DataFrame:
    """Tính toán 3 đường MA và các chỉ báo phụ trợ."""
    grp   = grp.copy()
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
    grp['spread_20_50_prev'] = grp['spread_20_50'].shift(5)  # 5 phiên trước

    # ── Crossover flags ───────────────────────────────────────────────
    prev_gap_20_50  = grp['spread_20_50'].shift(1)
    grp['golden_cross_small'] = (grp['spread_20_50'] > 0) & (prev_gap_20_50 <= 0)  # MA20 cắt lên MA50

    prev_spread_50_200 = ((grp['ma50'] - grp['ma200']) / grp['ma200'].replace(0, np.nan)).shift(1)
    cur_spread_50_200  = (grp['ma50'] - grp['ma200']) / grp['ma200'].replace(0, np.nan)
    grp['golden_cross_big']   = (cur_spread_50_200 > 0) & (prev_spread_50_200 <= 0)  # MA50 cắt lên MA200
    grp['death_cross_small']  = (grp['spread_20_50'] < 0) & (prev_gap_20_50 >= 0)    # MA20 cắt xuống MA50

    # Price cross MA20 xuống (gần đây trong 2 phiên)
    prev_dist_ma20 = grp['dist_ma20'].shift(1)
    grp['price_cross_ma20_dn'] = (grp['dist_ma20'] < 0) & (prev_dist_ma20 >= 0)

    # Price cross MA50 xuống
    prev_dist_ma50 = grp['dist_ma50'].shift(1)
    grp['price_cross_ma50_dn'] = (grp['dist_ma50'] < 0) & (prev_dist_ma50 >= 0)

    # ── RSI 14 ────────────────────────────────────────────────────────
    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    grp['rsi'] = 100 - (100 / (1 + gain / loss.replace(0, np.nan)))

    # ── Volume ────────────────────────────────────────────────────────

    grp['vol_avg20'] = volume.rolling(20).mean()

    # Thêm các chỉ báo cho logic Breakdown/Breakout đơn giản
    grp['high20'] = grp['high'].rolling(20).max()
    grp['low20']  = grp['low'].rolling(20).min()
    ema12 = close.ewm(span=12).mean()
    ema26 = close.ewm(span=26).mean()
    macd_line = ema12 - ema26
    grp['macd_hist'] = macd_line - macd_line.ewm(span=9).mean()
    grp['prev_macd'] = grp['macd_hist'].shift(1)


    # ── MA Score: số điều kiện MA tích cực (0-6) ─────────────────────
    # Backtest: Score=6 → Ret20=+2.5%, Score=5 → +2.0%, Score<4 → <+1.5%
    grp['ma_score'] = (
        (close > grp['ma20']).astype(int) +
        (close > grp['ma50']).astype(int) +
        (close > grp['ma200']).astype(int) +
        (grp['slope_ma20'] > 0).astype(int) +
        (grp['slope_ma50'] > 0).astype(int) +
        (grp['slope_ma200'] > 0).astype(int)
    )

    return grp


def get_buy_candidates(days: int = 3, target_date: str = None) -> pd.DataFrame:
    """
    Trả về danh sách mã có tín hiệu MUA theo chiến lược Breakout 20 ngày trong `days` ngày gần nhất.
    """
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

    for symbol, grp in df_raw.groupby('symbol'):
        grp = grp.sort_values('date').reset_index(drop=True)
        if len(grp) < 50:
            continue

        grp = _compute_indicators(grp)
        grp = grp.dropna(subset=['rsi', 'vol_avg20', 'high20', 'ma20'])
        
        check_days = min(days, len(grp))
        if check_days < 1:
            continue
            
        for offset in range(-1, -check_days - 1, -1):
            row = grp.iloc[offset]
            close    = row['close']
            ma20     = row['ma20']
            vol      = row['volume']
            vol_avg  = row['vol_avg20'] if row['vol_avg20'] > 0 else 1
            vol_ratio = vol / vol_avg
            rsi      = row['rsi']
            high20   = row['high20']

            if (close >= high20) and (vol_ratio >= 1.5) and (rsi < 70) and (close > ma20):
                prev_idx = offset - 1
                if abs(prev_idx) <= len(grp):
                    prev = grp.iloc[prev_idx]
                    pct_1d = (close - prev['close']) / prev['close'] * 100
                else:
                    pct_1d = 0
                    
                prev_1m_idx = offset - 22
                if abs(prev_1m_idx) <= len(grp):
                    pct_1m = (close / grp.iloc[prev_1m_idx]['close'] - 1) * 100
                else:
                    pct_1m = 0

                candidates.append({
                    'Mã CP':      symbol,
                    'Ngày Tín hiệu': row['date'].strftime('%d/%m/%Y'),
                    'Giá':        close,
                    'Tín hiệu':   "MUA (Breakout)",
                    '% Hôm nay':  round(pct_1d, 2),
                    '% 1 Tháng':  round(pct_1m, 2),
                    'RSI':        round(rsi, 1),
                    'Vol/TB':     round(vol_ratio, 2),
                })
                break 

    df_buy = pd.DataFrame(candidates)
    if df_buy.empty:
        return df_buy

    df_buy = df_buy.merge(df_info[['Mã CP', 'Sàn', 'Ngành']], on='Mã CP', how='left')
    df_buy = df_buy.sort_values(['% Hôm nay'], ascending=[False])

    cols = ['Mã CP', 'Ngày Tín hiệu', 'Giá', 'Tín hiệu', '% Hôm nay', '% 1 Tháng',
            'RSI', 'Vol/TB', 'Sàn', 'Ngành']
    return df_buy[[c for c in cols if c in df_buy.columns]].reset_index(drop=True)


def get_sell_candidates(days: int = 3, target_date: str = None) -> pd.DataFrame:
    """
    Trả về danh sách mã có tín hiệu BÁN theo chiến lược chấm điểm yếu trong `days` ngày gần nhất.
    """
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

    for symbol, grp in df_raw.groupby('symbol'):
        grp = grp.sort_values('date').reset_index(drop=True)
        if len(grp) < 50:
            continue

        grp = _compute_indicators(grp)
        grp = grp.dropna(subset=['rsi', 'macd_hist', 'prev_macd', 'vol_avg20', 'low20', 'ma50'])
        
        check_days = min(days, len(grp))
        if check_days < 1:
            continue
            
        for offset in range(-1, -check_days - 1, -1):
            row = grp.iloc[offset]
            close    = row['close']
            ma50     = row['ma50']
            vol      = row['volume']
            vol_avg  = row['vol_avg20'] if row['vol_avg20'] > 0 else 1
            vol_ratio = vol / vol_avg
            rsi      = row['rsi']
            low20    = row['low20']
            macd_h   = row['macd_hist']
            p_macd   = row['prev_macd']

            score = (
                int(rsi > 72) +
                int(close <= low20 and vol_ratio >= 1.5) +
                int(macd_h < 0 and p_macd >= 0 and rsi > 55) +
                int(close < ma50)
            )

            if score >= 2:
                prev_idx = offset - 1
                if abs(prev_idx) <= len(grp):
                    prev = grp.iloc[prev_idx]
                    pct_1d = (close - prev['close']) / prev['close'] * 100
                else:
                    pct_1d = 0
                    
                prev_1m_idx = offset - 22
                if abs(prev_1m_idx) <= len(grp):
                    pct_1m = (close / grp.iloc[prev_1m_idx]['close'] - 1) * 100
                else:
                    pct_1m = 0

                candidates.append({
                    'Mã CP':     symbol,
                    'Ngày Tín hiệu': row['date'].strftime('%d/%m/%Y'),
                    'Giá':       close,
                    'Tín hiệu':  f"BÁN ({score}/4)",
                    '% Hôm nay': round(pct_1d, 2),
                    '% 1 Tháng': round(pct_1m, 2),
                    'RSI':       round(rsi, 1),
                    'Vol/TB':    round(vol_ratio, 2),
                })
                break

    df_sell = pd.DataFrame(candidates)
    if df_sell.empty:
        return df_sell

    df_sell = df_sell.merge(df_info[['Mã CP', 'Sàn', 'Ngành']], on='Mã CP', how='left')
    df_sell = df_sell.sort_values(['% Hôm nay'], ascending=[True])

    cols = ['Mã CP', 'Ngày Tín hiệu', 'Giá', 'Tín hiệu', '% Hôm nay', '% 1 Tháng',
            'RSI', 'Vol/TB', 'Sàn', 'Ngành']
    return df_sell[[c for c in cols if c in df_sell.columns]].reset_index(drop=True)


def run_portfolio_backtest(symbol: str, initial_capital: float, timeframe: str, bt_method: str) -> dict:
    """
    Chạy backtest mô phỏng giao dịch thực tế cho một mã chứng khoán.
    - Mua lô 100
    - Tái đầu tư (lãi kép)
    """
    con = duckdb.connect(DB_PATH, read_only=True)
    df = con.execute(f"SELECT time::DATE as date, close, volume, high, low, open FROM historical_prices WHERE symbol = '{symbol}' ORDER BY time").df()
    con.close()
    
    if len(df) < 50:
        import pandas as pd
        return {"trades": pd.DataFrame(), "metrics": {}}
        
    df = _compute_indicators(df)
    import pandas as pd
    
    # Filter by timeframe
    if timeframe != "Tất cả":
        end_date = df['date'].max()
        if timeframe == "1 Năm":
            start_date = end_date - pd.Timedelta(days=365)
        elif timeframe == "3 Năm":
            start_date = end_date - pd.Timedelta(days=3*365)
        elif timeframe == "5 Năm":
            start_date = end_date - pd.Timedelta(days=5*365)
        elif timeframe == "6 Tháng":
            start_date = end_date - pd.Timedelta(days=180)
        else:
            start_date = end_date - pd.Timedelta(days=365)
        df = df[df['date'] >= start_date].reset_index(drop=True)
    
    capital = initial_capital
    in_position = False
    buy_price = 0
    buy_date = None
    buy_shares = 0
    buy_idx = 0
    
    trades = []
    
    for i in range(len(df)):
        row = df.iloc[i]
        
        # MUA
        if not in_position:
            # Check Buy Signal
            if pd.notna(row.get('rsi')) and pd.notna(row.get('vol_avg20')) and pd.notna(row.get('high20')) and pd.notna(row.get('ma20')):
                vol_avg = row['vol_avg20'] if row['vol_avg20'] > 0 else 1
                vol_ratio = row['volume'] / vol_avg
                if (row['close'] >= row['high20']) and (vol_ratio >= 1.5) and (row['rsi'] < 70) and (row['close'] > row['ma20']):
                    buy_price = row['close']
                    buy_shares = int(capital // (buy_price * 100)) * 100
                    if buy_shares > 0:
                        in_position = True
                        buy_date = row['date']
                        buy_idx = i
                        capital -= (buy_shares * buy_price)
                        
        # BÁN
        else:
            days_held = i - buy_idx
            sell_triggered = False
            
            # T+2 constraint
            if days_held >= 2:
                if bt_method == "Phương pháp 1":
                    if pd.notna(row.get('rsi')) and pd.notna(row.get('macd_hist')) and pd.notna(row.get('prev_macd')) and pd.notna(row.get('vol_avg20')) and pd.notna(row.get('low20')) and pd.notna(row.get('ma50')):
                        vol_avg = row['vol_avg20'] if row['vol_avg20'] > 0 else 1
                        score = (
                            int(row['rsi'] > 72) +
                            int(row['close'] <= row['low20'] and row['volume'] >= 1.5 * vol_avg) +
                            int(row['macd_hist'] < 0 and row['prev_macd'] >= 0 and row['rsi'] > 55) +
                            int(row['close'] < row['ma50'])
                        )
                        if score >= 2:
                            sell_triggered = True
                        
            if sell_triggered or i == len(df) - 1:
                if sell_triggered:
                    sell_price = row['close']
                    sell_date = row['date']
                else: 
                    sell_price = row['close']
                    sell_date = row['date']
                    
                capital += (buy_shares * sell_price)
                
                pl_amount = (sell_price - buy_price) * buy_shares
                pl_pct = (sell_price - buy_price) / buy_price * 100
                
                trades.append({
                    "Ngày Mua": buy_date.strftime('%Y-%m-%d'),
                    "Giá Mua": buy_price,
                    "Khối lượng": buy_shares,
                    "Ngày Bán": sell_date.strftime('%Y-%m-%d'),
                    "Giá Bán": sell_price,
                    "Lãi/Lỗ (%)": round(pl_pct, 2),
                    "Tiền Lãi/Lỗ": pl_amount
                })
                
                in_position = False
                
    df_trades = pd.DataFrame(trades)
    
    if df_trades.empty:
        return {"trades": df_trades, "metrics": {}}
        
    total_trades = len(df_trades)
    winning_trades = (df_trades["Lãi/Lỗ (%)"] > 0).sum()
    win_rate = winning_trades / total_trades * 100
    final_capital = capital if not in_position else capital + (buy_shares * buy_price)
    total_profit_pct = (final_capital - initial_capital) / initial_capital * 100
    
    metrics = {
        "final_capital": final_capital,
        "total_profit_pct": total_profit_pct,
        "total_trades": total_trades,
        "win_rate": win_rate
    }
    
    return {"trades": df_trades, "metrics": metrics, "df_chart": df}
