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


def get_buy_candidates() -> pd.DataFrame:
    """
    Trả về danh sách mã có tín hiệu MUA theo chiến lược MA 3 lớp.

    Ưu tiên 3 kịch bản tốt nhất từ backtest:
      A) Pullback về MA20/MA50 trong uptrend (Win20=54.8%)
      B) Golden Cross nhỏ + momentum (Win20=55.2%, Ret20=+3.3%)
      C) Full Bull Confirmation: P>MA20>MA50>MA200 + all slope up + vol cao (Win20=52.7%)
    """
    con    = duckdb.connect(DB_PATH, read_only=True)
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
        if len(grp) < 205:          # Cần đủ dữ liệu để tính MA200 (~200 phiên)
            continue

        grp = _compute_indicators(grp)
        grp = grp.dropna(subset=['ma200', 'rsi', 'slope_ma50', 'spread_20_50'])
        if len(grp) < 2:
            continue

        row      = grp.iloc[-1]
        close    = row['close']
        ma20     = row['ma20']
        ma50     = row['ma50']
        ma200    = row['ma200']
        dist20   = row['dist_ma20']
        dist50   = row['dist_ma50']
        slope20  = row['slope_ma20']
        slope50  = row['slope_ma50']
        slope200 = row['slope_ma200']
        spread   = row['spread_20_50']
        spread_prev = row['spread_20_50_prev']
        vol      = row['volume']
        vol_avg  = row['vol_avg20'] if row['vol_avg20'] > 0 else 1
        vol_ratio = vol / vol_avg
        rsi      = row['rsi']
        gc_small = row['golden_cross_small']
        gc_big   = row['golden_cross_big']
        ma_score = row['ma_score']

        # Các cờ vị trí
        above_ma20  = close > ma20
        above_ma50  = close > ma50
        above_ma200 = close > ma200

        # Các cờ slope
        all_slope_up = (slope20 > 0) and (slope50 > 0) and (slope200 > 0)
        slope50_up   = slope50 > 0
        spread_expanding = spread > spread_prev  # Momentum đang tăng

        # Khoảng cách giá gần MA (pullback)
        near_ma20 = -0.02 <= dist20 <= 0.03   # Trong vùng ±2% quanh MA20
        near_ma50 = -0.02 <= dist50 <= 0.03   # Trong vùng ±2% quanh MA50

        # ══════════════════════════════════════════════════════════════
        # TÍN HIỆU A: Pullback về MA20 trong Uptrend
        # Điều kiện: chạm MA20 + vẫn trên MA50 + MA200 + MA50 tăng + Vol tăng
        # Backtest: Win20=54.1%, Ret20=+2.4%
        # ══════════════════════════════════════════════════════════════
        signal_a = (
            near_ma20 and
            above_ma50 and
            above_ma200 and
            slope50_up and
            vol_ratio >= 1.2
        )

        # ══════════════════════════════════════════════════════════════
        # TÍN HIỆU A2: Pullback về MA50 trong Uptrend (sâu hơn)
        # Điều kiện: chạm MA50 + trên MA200 + MA50 đang tăng + Vol tăng
        # Backtest: Win20=54.8%, Ret20=+2.3%
        # ══════════════════════════════════════════════════════════════
        signal_a2 = (
            near_ma50 and
            above_ma200 and
            slope50_up and
            vol_ratio >= 1.2
        )

        # ══════════════════════════════════════════════════════════════
        # TÍN HIỆU B: Golden Cross nhỏ (MA20 cắt lên MA50) + Momentum
        # Điều kiện: vừa golden cross + MA50 tăng + Vol >= 1.2x
        # Backtest: Win20=55.2%, Ret20=+3.3% (N=1,311)
        # ══════════════════════════════════════════════════════════════
        signal_b = (
            gc_small and
            slope50_up and
            vol_ratio >= 1.2
        )

        # ══════════════════════════════════════════════════════════════
        # TÍN HIỆU C: Full Bull Confirmation
        # Điều kiện: P>MA20>MA50>MA200 + all 3 MA slope dương + spread mở + Vol cao
        # Backtest: Win20=52.7%, Ret20=+3.09%
        # ══════════════════════════════════════════════════════════════
        signal_c = (
            above_ma20 and above_ma50 and above_ma200 and
            all_slope_up and
            spread_expanding and
            vol_ratio >= 1.5
        )

        # ── Tính điểm tổng hợp ────────────────────────────────────────
        signal_type = None
        base_score  = 0

        if signal_b:
            signal_type = "B: Golden Cross"
            base_score = 6
        elif signal_a or signal_a2:
            signal_type = "A: Pullback MA20" if signal_a else "A2: Pullback MA50"
            base_score = 5
        elif signal_c:
            signal_type = "C: Full Bull"
            base_score = 4
        else:
            continue

        # Điểm thưởng từ MA Score
        bonus = ma_score  # 0-6
        final_score = base_score + bonus

        # Tính % thay đổi
        prev = grp.iloc[-2]
        pct_1d = (close - prev['close']) / prev['close'] * 100 if len(grp) >= 2 else 0
        pct_1m = (close / grp.iloc[-22]['close'] - 1) * 100 if len(grp) >= 22 else 0

        candidates.append({
            'Mã CP':      symbol,
            'Giá':        close,
            'Tín hiệu':   signal_type,
            '% Hôm nay':  round(pct_1d, 2),
            '% 1 Tháng':  round(pct_1m, 2),
            'MA Score':   int(ma_score),
            'RSI':        round(rsi, 1),
            'Vol/TB':     round(vol_ratio, 2),
            'Dist MA20':  f"{dist20*100:+.1f}%",
            'Dist MA50':  f"{dist50*100:+.1f}%",
            'Điểm TH':   final_score,
        })

    df_buy = pd.DataFrame(candidates)
    if df_buy.empty:
        return df_buy

    df_buy = df_buy.merge(df_info[['Mã CP', 'Sàn', 'Ngành']], on='Mã CP', how='left')
    df_buy = df_buy.sort_values(['Điểm TH', '% 1 Tháng'], ascending=[False, False])

    cols = ['Mã CP', 'Giá', 'Tín hiệu', '% Hôm nay', '% 1 Tháng',
            'MA Score', 'RSI', 'Vol/TB', 'Dist MA20', 'Dist MA50', 'Điểm TH', 'Sàn', 'Ngành']
    return df_buy[[c for c in cols if c in df_buy.columns]].reset_index(drop=True)


def get_sell_candidates() -> pd.DataFrame:
    """
    Trả về danh sách mã có tín hiệu BÁN theo chiến lược MA 3 lớp.

    Phát hiện từ backtest:
    - Không có combo nào cho P(giảm) > 50% — thị trường VN bullish bias.
    - Tín hiệu bán đáng tin nhất: MA đảo chiều + volume xác nhận.
    - BÁN sớm (cảnh báo): spread MA20-MA50 thu hẹp + RSI cao.
    - BÁN muộn (xác nhận): cắt xuống MA50/MA200 kèm volume.
    Cần >= 2/4 điều kiện để hiện tín hiệu bán.
    """
    con    = duckdb.connect(DB_PATH, read_only=True)
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
        if len(grp) < 210:
            continue

        grp = _compute_indicators(grp)
        grp = grp.dropna(subset=['ma200', 'rsi', 'slope_ma50'])
        if len(grp) < 6:
            continue

        row      = grp.iloc[-1]
        close    = row['close']
        ma20     = row['ma20']
        ma50     = row['ma50']
        ma200    = row['ma200']
        slope20  = row['slope_ma20']
        slope50  = row['slope_ma50']
        spread   = row['spread_20_50']
        spread_prev = row['spread_20_50_prev']
        vol      = row['volume']
        vol_avg  = row['vol_avg20'] if row['vol_avg20'] > 0 else 1
        vol_ratio = vol / vol_avg
        rsi      = row['rsi']
        death_cross = row['death_cross_small']
        p_cross_ma20_dn = row['price_cross_ma20_dn']
        p_cross_ma50_dn = row['price_cross_ma50_dn']

        above_ma20  = close > ma20
        above_ma50  = close > ma50
        above_ma200 = close > ma200

        # ── Tiêu chí BÁN (mỗi tiêu chí = 1 điểm) ─────────────────────────

        # [1] Spread thu hẹp + RSI > 72 + slope MA20 giảm
        #     Backtest: Full Bull nhưng spread shrink + RSI>72 → Giam20=41.6%
        #     Đây là "cảnh báo sớm" — momentum đang suy yếu trước khi giá giảm
        cond_spread_warn = (
            above_ma20 and above_ma50 and
            (spread < spread_prev) and   # Spread đang thu hẹp
            (rsi > 72) and
            (slope20 < 0)                # MA20 bắt đầu quay đầu
        )

        # [2] Price cắt xuống MA20 + dưới MA50 + Volume > 1.3x
        #     Backtest: Giam20=44.4%, phổ biến và đáng tin khi có volume xác nhận
        cond_ma20_break = (
            p_cross_ma20_dn and
            not above_ma50 and
            vol_ratio >= 1.3
        )

        # [3] Price cắt xuống MA50 + MA50 đang giảm + dưới MA200
        #     Backtest: Giam20=46.0% — tín hiệu BÁN mạnh nhất
        cond_ma50_break = (
            p_cross_ma50_dn and
            (slope50 < 0) and
            not above_ma200
        )

        # [4] Full Bear: P < MA20 < MA50 + cả 2 slope âm + Volume tăng
        #     Backtest: Giam20=45.5% — xu hướng giảm có xác nhận
        cond_full_bear = (
            not above_ma20 and
            not above_ma50 and
            (slope20 < 0) and (slope50 < 0) and
            vol_ratio >= 1.3
        )

        sell_score = sum([cond_spread_warn, cond_ma20_break, cond_ma50_break, cond_full_bear])

        if sell_score >= 2:
            prev = grp.iloc[-2]
            pct_1d = (close - prev['close']) / prev['close'] * 100 if len(grp) >= 2 else 0
            pct_1m = (close / grp.iloc[-22]['close'] - 1) * 100 if len(grp) >= 22 else 0

            # Xác định loại tín hiệu bán
            if cond_spread_warn:
                sig_type = "Cảnh báo (spread thu hẹp)"
            elif cond_ma50_break:
                sig_type = "Phá MA50 (bán mạnh)"
            elif cond_full_bear:
                sig_type = "Full Bear"
            else:
                sig_type = "Phá MA20"

            candidates.append({
                'Mã CP':     symbol,
                'Giá':       close,
                'Tín hiệu':  sig_type,
                '% Hôm nay': round(pct_1d, 2),
                '% 1 Tháng': round(pct_1m, 2),
                'RSI':       round(rsi, 1),
                'Vol/TB':    round(vol_ratio, 2),
                'Dist MA50': f"{(close/ma50-1)*100:+.1f}%",
                'MA Score':  int(row['ma_score']),
                'Điểm Yếu': sell_score,
            })

    df_sell = pd.DataFrame(candidates)
    if df_sell.empty:
        return df_sell

    df_sell = df_sell.merge(df_info[['Mã CP', 'Sàn', 'Ngành']], on='Mã CP', how='left')
    df_sell = df_sell.sort_values(['Điểm Yếu', '% 1 Tháng'], ascending=[False, True])

    cols = ['Mã CP', 'Giá', 'Tín hiệu', '% Hôm nay', '% 1 Tháng',
            'RSI', 'Vol/TB', 'Dist MA50', 'MA Score', 'Điểm Yếu', 'Sàn', 'Ngành']
    return df_sell[[c for c in cols if c in df_sell.columns]].reset_index(drop=True)
