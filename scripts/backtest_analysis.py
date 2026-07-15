"""
Backtest script — Tìm quy luật mua/bán tối ưu từ dữ liệu lịch sử thực tế.

Phương pháp:
- Quét toàn bộ lịch sử giá (2020-2026) của tất cả mã 3 ký tự.
- Mỗi tín hiệu mua được test với các holding period: 5, 10, 20 phiên.
- Đo lường: Win-rate, Return trung bình, Return trung vị, Sharpe.
- So sánh nhiều bộ tham số để tìm ngưỡng tối ưu.
"""
import duckdb, pandas as pd, numpy as np, os, warnings
warnings.filterwarnings('ignore')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH  = os.path.join(BASE_DIR, "data", "trading_data.duckdb")

print("=== BACKTEST PHÂN TÍCH QUY LUẬT MUA/BÁN ===\n")

# ── Tải dữ liệu ────────────────────────────────────────────────────────────────
print("Đang tải dữ liệu từ DuckDB...")
con = duckdb.connect(DB_PATH, read_only=True)
df_raw = con.execute("""
    SELECT symbol, time::DATE as date, open, high, low, close, volume
    FROM historical_prices
    WHERE length(symbol) = 3
    ORDER BY symbol, time
""").df()
con.close()
print(f"Dữ liệu: {len(df_raw):,} hàng | {df_raw['symbol'].nunique()} mã | "
      f"{df_raw['date'].min()} → {df_raw['date'].max()}\n")

# ── Tính chỉ báo kỹ thuật ──────────────────────────────────────────────────────
def compute_indicators(g):
    g = g.copy().sort_values('date').reset_index(drop=True)
    c = g['close']; v = g['volume']; h = g['high']; l = g['low']

    # Trend
    g['sma10']  = c.rolling(10).mean()
    g['sma20']  = c.rolling(20).mean()
    g['sma50']  = c.rolling(50).mean()
    g['sma200'] = c.rolling(200).mean()

    # RSI 14
    d = c.diff()
    gain = d.clip(lower=0).rolling(14).mean()
    loss = (-d.clip(upper=0)).rolling(14).mean()
    g['rsi'] = 100 - 100 / (1 + gain / loss.replace(0, np.nan))

    # MACD
    ema12 = c.ewm(span=12, adjust=False).mean()
    ema26 = c.ewm(span=26, adjust=False).mean()
    macd  = ema12 - ema26
    sig   = macd.ewm(span=9, adjust=False).mean()
    g['macd']      = macd
    g['macd_sig']  = sig
    g['macd_hist'] = macd - sig

    # ATR 14
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    g['atr14'] = tr.rolling(14).mean()

    # Volume
    g['vol_avg20'] = v.rolling(20).mean()
    g['vol_ratio']  = v / g['vol_avg20'].replace(0, np.nan)

    # Breakout levels
    g['high20'] = h.rolling(20).max()
    g['low20']  = l.rolling(20).min()
    g['high52'] = h.rolling(252).max()
    g['low52']  = l.rolling(252).min()

    # Bollinger Bands (20, 2)
    bb_mid = c.rolling(20).mean()
    bb_std = c.rolling(20).std()
    g['bb_upper'] = bb_mid + 2 * bb_std
    g['bb_lower'] = bb_mid - 2 * bb_std
    g['bb_pct']   = (c - g['bb_lower']) / (g['bb_upper'] - g['bb_lower'] + 1e-9)

    # Momentum
    g['mom5']  = c.pct_change(5)
    g['mom20'] = c.pct_change(20)

    # Stochastic %K (14)
    lowest14  = l.rolling(14).min()
    highest14 = h.rolling(14).max()
    g['stoch_k'] = (c - lowest14) / (highest14 - lowest14 + 1e-9) * 100

    return g

print("Đang tính chỉ báo kỹ thuật (có thể mất 1-2 phút)...")
df_all = df_raw.groupby('symbol', group_keys=False).apply(compute_indicators)
df_all = df_all.dropna(subset=['sma50', 'rsi', 'macd_hist', 'vol_avg20'])
print(f"Sau khi tính chỉ báo: {len(df_all):,} hàng\n")

# ── Hàm tính forward return ────────────────────────────────────────────────────
def add_forward_returns(df, periods=[5, 10, 20]):
    out = []
    for sym, g in df.groupby('symbol'):
        g = g.sort_values('date').reset_index(drop=True)
        for p in periods:
            g[f'fwd{p}'] = g['close'].shift(-p) / g['close'] - 1
        out.append(g)
    return pd.concat(out, ignore_index=True)

print("Đang tính forward returns (5, 10, 20 phiên)...")
df_all = add_forward_returns(df_all)
# Chỉ giữ hàng có đủ forward data
df_eval = df_all.dropna(subset=['fwd5', 'fwd10', 'fwd20']).copy()
print(f"Hàng có đủ dữ liệu để đánh giá: {len(df_eval):,}\n")

# ── PHÂN TÍCH 1: RSI và forward return ────────────────────────────────────────
print("=" * 60)
print("PHÂN TÍCH 1: RSI và Return sau 20 phiên")
print("=" * 60)
df_eval['rsi_bucket'] = pd.cut(df_eval['rsi'],
    bins=[0, 30, 40, 50, 55, 60, 65, 70, 75, 80, 100],
    labels=['<30','30-40','40-50','50-55','55-60','60-65','65-70','70-75','75-80','>80'])

rsi_stats = df_eval.groupby('rsi_bucket', observed=True).agg(
    count    = ('fwd20', 'count'),
    win_rate = ('fwd20', lambda x: (x > 0).mean()),
    ret_mean = ('fwd20', 'mean'),
    ret_med  = ('fwd20', 'median'),
).round(4)
print(rsi_stats.to_string())

# ── PHÂN TÍCH 2: Volume ratio và forward return ────────────────────────────────
print("\n" + "=" * 60)
print("PHÂN TÍCH 2: Volume Ratio (vol/vol_avg20) và Return sau 20 phiên")
print("=" * 60)
df_eval['vol_bucket'] = pd.cut(df_eval['vol_ratio'].clip(0, 6),
    bins=[0, 0.5, 0.8, 1.0, 1.3, 1.5, 2.0, 3.0, 6.0],
    labels=['<0.5','0.5-0.8','0.8-1.0','1.0-1.3','1.3-1.5','1.5-2.0','2.0-3.0','>3.0'])

vol_stats = df_eval.groupby('vol_bucket', observed=True).agg(
    count    = ('fwd20', 'count'),
    win_rate = ('fwd20', lambda x: (x > 0).mean()),
    ret_mean = ('fwd20', 'mean'),
    ret_med  = ('fwd20', 'median'),
).round(4)
print(vol_stats.to_string())

# ── PHÂN TÍCH 3: BB %B và forward return ──────────────────────────────────────
print("\n" + "=" * 60)
print("PHÂN TÍCH 3: Bollinger %B và Return sau 20 phiên")
print("=" * 60)
df_eval['bb_bucket'] = pd.cut(df_eval['bb_pct'].clip(-0.2, 1.2),
    bins=[-0.2, 0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.2],
    labels=['<0 (dưới BB)','0-0.2','0.2-0.4','0.4-0.6','0.6-0.8','0.8-1.0','>1.0 (trên BB)'])

bb_stats = df_eval.groupby('bb_bucket', observed=True).agg(
    count    = ('fwd20', 'count'),
    win_rate = ('fwd20', lambda x: (x > 0).mean()),
    ret_mean = ('fwd20', 'mean'),
    ret_med  = ('fwd20', 'median'),
).round(4)
print(bb_stats.to_string())

# ── PHÂN TÍCH 4: Xu hướng (giá vs SMA) và return ─────────────────────────────
print("\n" + "=" * 60)
print("PHÂN TÍCH 4: Xu hướng (Close vs SMA) và Return sau 20 phiên")
print("=" * 60)
df_eval['above_sma20'] = df_eval['close'] > df_eval['sma20']
df_eval['above_sma50'] = df_eval['close'] > df_eval['sma50']
df_eval['above_sma200']= df_eval['close'] > df_eval['sma200']

trend_combos = df_eval.groupby(['above_sma20','above_sma50','above_sma200'], observed=True).agg(
    count    = ('fwd20', 'count'),
    win_rate = ('fwd20', lambda x: (x > 0).mean()),
    ret_mean = ('fwd20', 'mean'),
    ret_med  = ('fwd20', 'median'),
).round(4)
print(trend_combos.to_string())

# ── PHÂN TÍCH 5: MACD cross và return ─────────────────────────────────────────
print("\n" + "=" * 60)
print("PHÂN TÍCH 5: MACD Signal (cross up/down) và Return")
print("=" * 60)
df_eval['macd_cross_up']   = (df_eval['macd_hist'] > 0) & (df_eval['macd_hist'].shift(1) <= 0)
df_eval['macd_cross_down'] = (df_eval['macd_hist'] < 0) & (df_eval['macd_hist'].shift(1) >= 0)

for label, mask in [('MACD cắt LÊN (+)', df_eval['macd_cross_up']),
                    ('MACD cắt XUỐNG (-)', df_eval['macd_cross_down']),
                    ('MACD > 0 (vùng dương)', df_eval['macd_hist'] > 0),
                    ('MACD < 0 (vùng âm)', df_eval['macd_hist'] < 0)]:
    sub = df_eval[mask]
    if len(sub) < 100: continue
    print(f"  {label}: n={len(sub):,} | "
          f"Win={sub['fwd20'].gt(0).mean():.1%} | "
          f"Ret={sub['fwd20'].mean():.3f} | "
          f"Med={sub['fwd20'].median():.3f}")

# ── PHÂN TÍCH 6: Stochastic và return ────────────────────────────────────────
print("\n" + "=" * 60)
print("PHÂN TÍCH 6: Stochastic %K và Return sau 20 phiên")
print("=" * 60)
df_eval['stoch_bucket'] = pd.cut(df_eval['stoch_k'],
    bins=[0, 20, 30, 40, 50, 60, 70, 80, 100],
    labels=['<20(OversoldX)','20-30','30-40','40-50','50-60','60-70','70-80','>80(OverboughtX)'])

stoch_stats = df_eval.groupby('stoch_bucket', observed=True).agg(
    count    = ('fwd20', 'count'),
    win_rate = ('fwd20', lambda x: (x > 0).mean()),
    ret_mean = ('fwd20', 'mean'),
    ret_med  = ('fwd20', 'median'),
).round(4)
print(stoch_stats.to_string())

# ── PHÂN TÍCH 7: Breakout 20 phiên và return ─────────────────────────────────
print("\n" + "=" * 60)
print("PHÂN TÍCH 7: Breakout / Breakdown 20 phiên và Return")
print("=" * 60)
df_eval['breakout20'] = df_eval['close'] >= df_eval['high20']
df_eval['breakdown20'] = df_eval['close'] <= df_eval['low20']

for label, mask in [('Breakout đỉnh 20p', df_eval['breakout20']),
                    ('Breakdown đáy 20p', df_eval['breakdown20']),
                    ('Trong biên 20p', ~df_eval['breakout20'] & ~df_eval['breakdown20'])]:
    sub = df_eval[mask]
    if len(sub) < 100: continue
    for p in [5, 10, 20]:
        wr = sub[f'fwd{p}'].gt(0).mean()
        rt = sub[f'fwd{p}'].mean()
        if p == 20:
            print(f"  {label}: n={len(sub):,} | fwd5={sub['fwd5'].mean():.3f} | fwd10={sub['fwd10'].mean():.3f} | fwd20={rt:.3f} | win20={wr:.1%}")
        break

# ── PHÂN TÍCH 8: Combo tốt nhất cho MUA ─────────────────────────────────────
print("\n" + "=" * 60)
print("PHÂN TÍCH 8: Combo tín hiệu MUA — Tìm bộ điều kiện tối ưu")
print("=" * 60)

# Tạo các điều kiện boolean
df_eval['cond_rsi_ok']      = df_eval['rsi'].between(40, 65)       # RSI trung lập
df_eval['cond_rsi_dip']     = df_eval['rsi'] < 40                  # RSI oversold
df_eval['cond_vol_strong']  = df_eval['vol_ratio'] >= 1.5           # Volume cao
df_eval['cond_above_sma20'] = df_eval['close'] > df_eval['sma20']
df_eval['cond_above_sma50'] = df_eval['close'] > df_eval['sma50']
df_eval['cond_macd_up']     = df_eval['macd_hist'] > 0
df_eval['cond_bb_mid']      = df_eval['bb_pct'].between(0.2, 0.8)
df_eval['cond_stoch_ok']    = df_eval['stoch_k'].between(20, 70)
df_eval['cond_breakout']    = df_eval['breakout20']
df_eval['cond_mom_pos']     = df_eval['mom5'] > 0

combos = [
    ("RSI<65 + Vol>1.5 + >SMA20 + MACD>0",
     df_eval['cond_rsi_ok'] & df_eval['cond_vol_strong'] & df_eval['cond_above_sma20'] & df_eval['cond_macd_up']),
    ("Breakout20 + Vol>1.5 + RSI<70",
     df_eval['cond_breakout'] & df_eval['cond_vol_strong'] & (df_eval['rsi'] < 70)),
    ("Breakout20 + Vol>1.5 + RSI<70 + >SMA50",
     df_eval['cond_breakout'] & df_eval['cond_vol_strong'] & (df_eval['rsi'] < 70) & df_eval['cond_above_sma50']),
    ("RSI<65 + >SMA20 + >SMA50 + MACD>0 + Vol>1.2",
     df_eval['cond_rsi_ok'] & df_eval['cond_above_sma20'] & df_eval['cond_above_sma50'] & df_eval['cond_macd_up'] & (df_eval['vol_ratio']>=1.2)),
    ("RSI40-60 + >SMA20 + >SMA50 + MACD>0 + BB%<0.7",
     df_eval['rsi'].between(40,60) & df_eval['cond_above_sma20'] & df_eval['cond_above_sma50'] & df_eval['cond_macd_up'] & (df_eval['bb_pct']<0.7)),
    ("RSI<50 + >SMA50 + MACD cắt lên + Vol>1.3",
     (df_eval['rsi']<50) & df_eval['cond_above_sma50'] & df_eval['macd_cross_up'] & (df_eval['vol_ratio']>=1.3)),
    ("MACD cắt lên + RSI<65 + >SMA20",
     df_eval['macd_cross_up'] & (df_eval['rsi']<65) & df_eval['cond_above_sma20']),
    ("Stoch<30 + RSI<40 + >SMA50 (Pullback mua)",
     (df_eval['stoch_k']<30) & (df_eval['rsi']<40) & df_eval['cond_above_sma50']),
]

print(f"{'Combo':<55} {'N':>6} {'Win5':>6} {'Win10':>6} {'Win20':>6} {'Ret20':>7} {'Med20':>7}")
print("-" * 100)
for name, mask in combos:
    sub = df_eval[mask]
    if len(sub) < 30: continue
    print(f"{name:<55} {len(sub):>6,} "
          f"{sub['fwd5'].gt(0).mean():>6.1%} "
          f"{sub['fwd10'].gt(0).mean():>6.1%} "
          f"{sub['fwd20'].gt(0).mean():>6.1%} "
          f"{sub['fwd20'].mean():>7.3f} "
          f"{sub['fwd20'].median():>7.3f}")

# ── PHÂN TÍCH 9: Combo tốt nhất cho BÁN ─────────────────────────────────────
print("\n" + "=" * 60)
print("PHÂN TÍCH 9: Combo tín hiệu BÁN — Tìm bộ điều kiện tối ưu")
print("=" * 60)

sell_combos = [
    ("RSI>72",
     df_eval['rsi'] > 72),
    ("RSI>72 + BB%>0.9",
     (df_eval['rsi'] > 72) & (df_eval['bb_pct'] > 0.9)),
    ("MACD cắt xuống + RSI>55",
     df_eval['macd_cross_down'] & (df_eval['rsi'] > 55)),
    ("MACD cắt xuống + RSI>55 + <SMA20",
     df_eval['macd_cross_down'] & (df_eval['rsi'] > 55) & (df_eval['close'] < df_eval['sma20'])),
    ("Breakdown20 + Vol>1.5",
     df_eval['breakdown20'] & (df_eval['vol_ratio'] >= 1.5)),
    ("Breakdown20 + Vol>1.5 + RSI<50",
     df_eval['breakdown20'] & (df_eval['vol_ratio'] >= 1.5) & (df_eval['rsi'] < 50)),
    ("<SMA50 + <SMA20 + MACD<0 + RSI<50",
     ~df_eval['cond_above_sma50'] & ~df_eval['cond_above_sma20'] & (df_eval['macd_hist']<0) & (df_eval['rsi']<50)),
    ("Stoch>80 + RSI>70 + BB%>0.85",
     (df_eval['stoch_k']>80) & (df_eval['rsi']>70) & (df_eval['bb_pct']>0.85)),
    ("RSI>65 + MACD cắt xuống + <SMA50",
     (df_eval['rsi']>65) & df_eval['macd_cross_down'] & ~df_eval['cond_above_sma50']),
]

# Tín hiệu BÁN tốt = fwd return âm sau đó (tức win = giá giảm)
print(f"{'Combo BÁN':<55} {'N':>6} {'Giảm5':>6} {'Giảm10':>6} {'Giảm20':>6} {'Ret20':>7} {'Med20':>7}")
print("-" * 100)
for name, mask in sell_combos:
    sub = df_eval[mask]
    if len(sub) < 30: continue
    print(f"{name:<55} {len(sub):>6,} "
          f"{sub['fwd5'].lt(0).mean():>6.1%} "
          f"{sub['fwd10'].lt(0).mean():>6.1%} "
          f"{sub['fwd20'].lt(0).mean():>6.1%} "
          f"{sub['fwd20'].mean():>7.3f} "
          f"{sub['fwd20'].median():>7.3f}")

# ── PHÂN TÍCH 10: Holding period tối ưu ─────────────────────────────────────
print("\n" + "=" * 60)
print("PHÂN TÍCH 10: Holding Period tối ưu cho Breakout + Vol cao")
print("=" * 60)
mask_buy_best = df_eval['cond_breakout'] & df_eval['cond_vol_strong'] & (df_eval['rsi'] < 70) & df_eval['cond_above_sma50']
sub_best = df_eval[mask_buy_best]
if len(sub_best) > 0:
    print(f"Điều kiện: Breakout20 + Vol>1.5 + RSI<70 + >SMA50 | N={len(sub_best):,}")
    for p in [5, 10, 20]:
        wr  = sub_best[f'fwd{p}'].gt(0).mean()
        ret = sub_best[f'fwd{p}'].mean()
        med = sub_best[f'fwd{p}'].median()
        print(f"  Hold {p:>2} phiên: Win={wr:.1%} | Ret={ret:.3f} ({ret*100:.2f}%) | Med={med:.3f}")

print("\n=== HOÀN TẤT BACKTEST ===")
