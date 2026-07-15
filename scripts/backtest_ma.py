"""
Backtest chuyên sâu về 3 đường MA (SMA20, SMA50, SMA200)
Phân tích mọi tổ hợp tín hiệu MA có thể, từ dữ liệu 2020-2026.
"""
import duckdb, pandas as pd, numpy as np, os, warnings
warnings.filterwarnings('ignore')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH  = os.path.join(BASE_DIR, "data", "trading_data.duckdb")

print("=== BACKTEST MA STRATEGY (2020-2026) ===\n")

# ── Tải dữ liệu ────────────────────────────────────────────────────────────────
con = duckdb.connect(DB_PATH, read_only=True)
df_raw = con.execute("""
    SELECT symbol, time::DATE as date, open, high, low, close, volume
    FROM historical_prices
    WHERE length(symbol) = 3
    ORDER BY symbol, time
""").df()
con.close()
print(f"Data: {len(df_raw):,} rows | {df_raw['symbol'].nunique()} symbols | {df_raw['date'].min()} to {df_raw['date'].max()}\n")

# ── Tính toán chỉ báo ──────────────────────────────────────────────────────────
def compute(g):
    g = g.copy().sort_values('date').reset_index(drop=True)
    c, v, h, l = g['close'], g['volume'], g['high'], g['low']

    # 3 đường MA chính
    g['ma20']  = c.rolling(20).mean()
    g['ma50']  = c.rolling(50).mean()
    g['ma200'] = c.rolling(200).mean()

    # Slope của mỗi MA (tỷ lệ thay đổi 5 phiên gần nhất)
    g['slope_ma20']  = g['ma20'].pct_change(5)
    g['slope_ma50']  = g['ma50'].pct_change(5)
    g['slope_ma200'] = g['ma200'].pct_change(5)

    # Khoảng cách % giữa các MA
    g['gap_20_50']   = (g['ma20'] - g['ma50']) / g['ma50']     # MA20 vs MA50
    g['gap_50_200']  = (g['ma50'] - g['ma200']) / g['ma200']   # MA50 vs MA200
    g['gap_20_200']  = (g['ma20'] - g['ma200']) / g['ma200']   # MA20 vs MA200

    # Khoảng cách giá vs MA
    g['dist_ma20']  = (c - g['ma20'])  / g['ma20']
    g['dist_ma50']  = (c - g['ma50'])  / g['ma50']
    g['dist_ma200'] = (c - g['ma200']) / g['ma200']

    # Crossover: MA20 cắt MA50 (Golden/Death cross nhỏ)
    g['prev_gap_20_50']  = g['gap_20_50'].shift(1)
    g['cross_20_50_up']  = (g['gap_20_50'] > 0) & (g['prev_gap_20_50'] <= 0)
    g['cross_20_50_dn']  = (g['gap_20_50'] < 0) & (g['prev_gap_20_50'] >= 0)

    # Crossover: MA50 cắt MA200 (Golden/Death cross lớn)
    g['prev_gap_50_200']  = g['gap_50_200'].shift(1)
    g['cross_50_200_up']  = (g['gap_50_200'] > 0) & (g['prev_gap_50_200'] <= 0)
    g['cross_50_200_dn']  = (g['gap_50_200'] < 0) & (g['prev_gap_50_200'] >= 0)

    # Price cross MA20 (giá cắt lên/xuống MA20)
    g['prev_dist_ma20']   = g['dist_ma20'].shift(1)
    g['price_cross_ma20_up'] = (g['dist_ma20'] > 0) & (g['prev_dist_ma20'] <= 0)
    g['price_cross_ma20_dn'] = (g['dist_ma20'] < 0) & (g['prev_dist_ma20'] >= 0)

    # Price cross MA50
    g['prev_dist_ma50']   = g['dist_ma50'].shift(1)
    g['price_cross_ma50_up'] = (g['dist_ma50'] > 0) & (g['prev_dist_ma50'] <= 0)
    g['price_cross_ma50_dn'] = (g['dist_ma50'] < 0) & (g['prev_dist_ma50'] >= 0)

    # RSI
    d = c.diff()
    gain = d.clip(lower=0).rolling(14).mean()
    loss = (-d.clip(upper=0)).rolling(14).mean()
    g['rsi'] = 100 - 100 / (1 + gain / loss.replace(0, np.nan))

    # Volume
    g['vol_avg20'] = v.rolling(20).mean()
    g['vol_ratio'] = v / g['vol_avg20'].replace(0, np.nan)

    # ATR (stop loss reference)
    tr = pd.concat([h-l, (h-c.shift()).abs(), (l-c.shift()).abs()], axis=1).max(axis=1)
    g['atr14'] = tr.rolling(14).mean()

    # Forward returns
    for p in [5, 10, 20, 40]:
        g[f'fwd{p}'] = c.shift(-p) / c - 1

    return g

print("Computing indicators...")
df_all = df_raw.groupby('symbol', group_keys=False).apply(compute)
df_eval = df_all.dropna(subset=['ma200','rsi','fwd5','fwd10','fwd20','fwd40']).copy()
print(f"Evaluation rows: {len(df_eval):,}\n")

H  = "─" * 110
SH = "=" * 110

# ══════════════════════════════════════════════════════════════════════════════
print(SH)
print("PHAN TICH 1: 8 Trang thai vi tri gia vs 3 MA (Price Position States)")
print(SH)

df_eval['above_ma20']  = df_eval['close'] > df_eval['ma20']
df_eval['above_ma50']  = df_eval['close'] > df_eval['ma50']
df_eval['above_ma200'] = df_eval['close'] > df_eval['ma200']

def state_label(row):
    a, b, c_ = row['above_ma20'], row['above_ma50'], row['above_ma200']
    if a and b and c_:    return '7_MA20>MA50>MA200 (Full Bull)'
    if not a and b and c_:return '6_MA50>Price>MA20 (Pullback)'
    if a and not b and c_:return '5_MA200<P<MA50, >MA20 (Bounce?)'
    if not a and not b and c_:return '4_P<MA20<MA50 >MA200 (Weak)'
    if a and b and not c_:return '3_>MA20&50, <MA200 (Mid bear)'
    if not a and b and not c_:return '2_MA50>P>MA200 (Deep)'
    if a and not b and not c_:return '1_>MA20 <MA50 <MA200 (Dead cat)'
    return '0_Full Bear (<MA20<MA50<MA200)'

df_eval['ma_state'] = df_eval.apply(state_label, axis=1)

state_stats = df_eval.groupby('ma_state').agg(
    N        = ('fwd20','count'),
    win20    = ('fwd20', lambda x: (x>0).mean()),
    ret5     = ('fwd5','mean'),
    ret10    = ('fwd10','mean'),
    ret20    = ('fwd20','mean'),
    ret40    = ('fwd40','mean'),
    med20    = ('fwd20','median'),
).round(4).sort_index(ascending=False)

print(f"\n{'Trang thai':<42} {'N':>7} {'Win20':>6} {'Ret5':>7} {'Ret10':>7} {'Ret20':>7} {'Ret40':>7} {'Med20':>7}")
print(H)
for idx, row in state_stats.iterrows():
    name = idx[2:] if len(idx)>2 else idx
    print(f"{name:<42} {int(row['N']):>7,} {row['win20']:>6.1%} "
          f"{row['ret5']:>7.3f} {row['ret10']:>7.3f} {row['ret20']:>7.3f} "
          f"{row['ret40']:>7.3f} {row['med20']:>7.3f}")

# ══════════════════════════════════════════════════════════════════════════════
print(f"\n{SH}")
print("PHAN TICH 2: MA Slope — Huong di cua 3 MA")
print(SH)

# Phân nhóm slope của từng MA
for ma_name in ['ma20', 'ma50', 'ma200']:
    col = f'slope_{ma_name}'
    label = ma_name.upper()
    print(f"\n  {label} Slope vs Return 20p:")
    for name, mask in [
        (f'{label} tang manh (>+0.5%/5p)', df_eval[col] > 0.005),
        (f'{label} tang nhe (0 to +0.5%)', df_eval[col].between(0, 0.005)),
        (f'{label} giam nhe (-0.5% to 0)', df_eval[col].between(-0.005, 0)),
        (f'{label} giam manh (<-0.5%/5p)', df_eval[col] < -0.005),
    ]:
        sub = df_eval[mask]
        if len(sub) < 100: continue
        print(f"    {name:<45} N={len(sub):>7,} | win20={sub['fwd20'].gt(0).mean():.1%} | ret20={sub['fwd20'].mean():.4f} | med20={sub['fwd20'].median():.4f}")

# ══════════════════════════════════════════════════════════════════════════════
print(f"\n{SH}")
print("PHAN TICH 3: Khoang cach % giua cac MA (Ma Spread)")
print(SH)

print("\n  Gap MA20-MA50 (%) vs Return 20p:")
df_eval['gap20_50_pct'] = df_eval['gap_20_50'] * 100
spread_stats = df_eval.groupby(pd.cut(df_eval['gap20_50_pct'],
    bins=[-20,-5,-2,-0.5,0,0.5,2,5,20],
    labels=['<-5%','-5to-2%','-2to-0.5%','-0.5to0','0to0.5%','0.5to2%','2to5%','>5%']
), observed=True).agg(N=('fwd20','count'), win20=('fwd20',lambda x:(x>0).mean()), ret20=('fwd20','mean')).round(4)
for idx, row in spread_stats.iterrows():
    print(f"    MA20-MA50={str(idx):<12} N={int(row['N']):>6,} win20={row['win20']:.1%} ret20={row['ret20']:.4f}")

print("\n  Gap MA50-MA200 (%) vs Return 20p:")
df_eval['gap50_200_pct'] = df_eval['gap_50_200'] * 100
spread_stats2 = df_eval.groupby(pd.cut(df_eval['gap50_200_pct'],
    bins=[-30,-10,-3,-1,0,1,3,10,30],
    labels=['<-10%','-10to-3%','-3to-1%','-1to0','0to1%','1to3%','3to10%','>10%']
), observed=True).agg(N=('fwd20','count'), win20=('fwd20',lambda x:(x>0).mean()), ret20=('fwd20','mean')).round(4)
for idx, row in spread_stats2.iterrows():
    print(f"    MA50-MA200={str(idx):<12} N={int(row['N']):>6,} win20={row['win20']:.1%} ret20={row['ret20']:.4f}")

# ══════════════════════════════════════════════════════════════════════════════
print(f"\n{SH}")
print("PHAN TICH 4: Crossover Events — Golden Cross & Death Cross")
print(SH)

cross_events = [
    ("Price cat len MA20 (bullish retest)",   df_eval['price_cross_ma20_up']),
    ("Price cat xuong MA20 (bearish break)",  df_eval['price_cross_ma20_dn']),
    ("Price cat len MA50 (strong bull)",      df_eval['price_cross_ma50_up']),
    ("Price cat xuong MA50 (strong bear)",    df_eval['price_cross_ma50_dn']),
    ("MA20 cat len MA50 (Golden Cross nho)",  df_eval['cross_20_50_up']),
    ("MA20 cat xuong MA50 (Death Cross nho)", df_eval['cross_20_50_dn']),
    ("MA50 cat len MA200 (Golden Cross lon)", df_eval['cross_50_200_up']),
    ("MA50 cat xuong MA200 (Death Cross lon)",df_eval['cross_50_200_dn']),
]

print(f"\n  {'Su kien':<45} {'N':>6} {'Win5':>6} {'Win10':>6} {'Win20':>6} {'Win40':>6} {'Ret20':>7} {'Ret40':>7}")
print("  " + H[:100])
for name, mask in cross_events:
    sub = df_eval[mask]
    if len(sub) < 50: continue
    print(f"  {name:<45} {len(sub):>6,} "
          f"{sub['fwd5'].gt(0).mean():>6.1%} "
          f"{sub['fwd10'].gt(0).mean():>6.1%} "
          f"{sub['fwd20'].gt(0).mean():>6.1%} "
          f"{sub['fwd40'].gt(0).mean():>6.1%} "
          f"{sub['fwd20'].mean():>7.3f} "
          f"{sub['fwd40'].mean():>7.3f}")

# ══════════════════════════════════════════════════════════════════════════════
print(f"\n{SH}")
print("PHAN TICH 5: Khoang cach gia vs MA — Khi nao mua tot nhat?")
print(SH)

print("\n  Khoang cach Gia vs MA20 (dist_ma20 %)")
df_eval['dist20_pct'] = df_eval['dist_ma20'] * 100
d20_stats = df_eval.groupby(pd.cut(df_eval['dist20_pct'].clip(-20,20),
    bins=[-20,-10,-5,-2,0,2,5,10,20],
    labels=['<-10%','-10to-5%','-5to-2%','-2to0','0to2%','2to5%','5to10%','>10%']
), observed=True).agg(N=('fwd20','count'), win20=('fwd20',lambda x:(x>0).mean()), ret20=('fwd20','mean'), ret10=('fwd10','mean')).round(4)
for idx, row in d20_stats.iterrows():
    print(f"    P vs MA20={str(idx):<12} N={int(row['N']):>6,} win20={row['win20']:.1%} ret10={row['ret10']:.4f} ret20={row['ret20']:.4f}")

print("\n  Khoang cach Gia vs MA50 (dist_ma50 %)")
df_eval['dist50_pct'] = df_eval['dist_ma50'] * 100
d50_stats = df_eval.groupby(pd.cut(df_eval['dist50_pct'].clip(-30,30),
    bins=[-30,-15,-5,-2,0,2,5,15,30],
    labels=['<-15%','-15to-5%','-5to-2%','-2to0','0to2%','2to5%','5to15%','>15%']
), observed=True).agg(N=('fwd20','count'), win20=('fwd20',lambda x:(x>0).mean()), ret20=('fwd20','mean')).round(4)
for idx, row in d50_stats.iterrows():
    print(f"    P vs MA50={str(idx):<12} N={int(row['N']):>6,} win20={row['win20']:.1%} ret20={row['ret20']:.4f}")

# ══════════════════════════════════════════════════════════════════════════════
print(f"\n{SH}")
print("PHAN TICH 6: COMBO MA + Volume — Tim chien luoc toi uu")
print(SH)

# Điều kiện cơ bản
F = df_eval  # alias

# Các điều kiện boolean
above_all    = F['above_ma20'] & F['above_ma50'] & F['above_ma200']
above_50_200 = F['above_ma50'] & F['above_ma200']
ma20_slope_up   = F['slope_ma20'] > 0
ma50_slope_up   = F['slope_ma50'] > 0
ma200_slope_up  = F['slope_ma200'] > 0
vol_hi       = F['vol_ratio'] >= 1.5
vol_norm     = F['vol_ratio'].between(0.8, 1.5)
rsi_ok       = F['rsi'] < 70
rsi_mid      = F['rsi'].between(40, 65)
near_ma20    = F['dist_ma20'].between(-0.02, 0.03)  # Giá gần MA20 (pullback touch)
near_ma50    = F['dist_ma50'].between(-0.02, 0.03)  # Giá gần MA50 (retest)
ma20_above_50 = F['gap_20_50'] > 0
spread_expanding = (F['gap_20_50'] > F['gap_20_50'].shift(5))  # MA20 đang tăng khoảng cách vs MA50

buy_combos = [
    # ── Full Bull scenarios ─────────────────────────────────────────────
    ("Full Bull: P>MA20>MA50>MA200, Vol>1.5, RSI<70",
     above_all & vol_hi & rsi_ok),
    ("Full Bull: P>MA20>MA50>MA200, all MA tang",
     above_all & ma20_slope_up & ma50_slope_up & ma200_slope_up),
    ("Full Bull: P>MA20>MA50>MA200, spread dang mo rong",
     above_all & spread_expanding & ma50_slope_up),
    # ── Pullback to MA scenarios ────────────────────────────────────────
    ("Pullback MA20: Touch MA20 + >MA50 + >MA200 + Vol tang",
     near_ma20 & above_50_200 & vol_hi),
    ("Pullback MA20: Touch MA20 + all MA tang + RSI<65",
     near_ma20 & above_50_200 & ma20_slope_up & ma50_slope_up & (F['rsi']<65)),
    ("Pullback MA50: Touch MA50 + >MA200 + MA50 tang",
     near_ma50 & F['above_ma200'] & ma50_slope_up & vol_hi),
    ("Pullback MA50: Touch MA50 + >MA200 + RSI 40-60",
     near_ma50 & F['above_ma200'] & rsi_mid),
    # ── Golden Cross scenarios ───────────────────────────────────────────
    ("Price cat len MA50 + >MA200 + Vol>1.5",
     F['price_cross_ma50_up'] & F['above_ma200'] & vol_hi),
    ("MA20 cat len MA50 (Golden Cross nho) + >MA200",
     F['cross_20_50_up'] & F['above_ma200']),
    ("MA20 cat len MA50 + MA50 tang + Vol>1.2",
     F['cross_20_50_up'] & ma50_slope_up & (F['vol_ratio']>=1.2)),
    # ── Recovery scenarios ───────────────────────────────────────────────
    ("Recovery: P>MA20, <MA50, MA20 tang manh (>1%)",
     F['above_ma20'] & ~F['above_ma50'] & (F['slope_ma20']>0.01) & vol_hi),
]

print(f"\n  {'Combo MUA':<58} {'N':>6} {'Win5':>6} {'Win10':>6} {'Win20':>6} {'Win40':>6} {'Ret20':>7} {'Ret40':>7}")
print("  " + H[:108])
best_buys = []
for name, mask in buy_combos:
    sub = F[mask]
    if len(sub) < 30: continue
    w20 = sub['fwd20'].gt(0).mean()
    r20 = sub['fwd20'].mean()
    r40 = sub['fwd40'].mean()
    best_buys.append((name, len(sub), w20, r20, r40))
    print(f"  {name:<58} {len(sub):>6,} "
          f"{sub['fwd5'].gt(0).mean():>6.1%} "
          f"{sub['fwd10'].gt(0).mean():>6.1%} "
          f"{w20:>6.1%} "
          f"{sub['fwd40'].gt(0).mean():>6.1%} "
          f"{r20:>7.3f} "
          f"{r40:>7.3f}")

# ── Chiến lược BÁN ──────────────────────────────────────────────────────────
print(f"\n{SH}")
print("PHAN TICH 7: COMBO MA + Indicators — Tin hieu BAN")
print(SH)

below_ma20   = ~F['above_ma20']
below_ma50   = ~F['above_ma50']
below_ma200  = ~F['above_ma200']
ma20_slope_dn  = F['slope_ma20'] < 0
ma50_slope_dn  = F['slope_ma50'] < 0
spread_shrink  = F['gap_20_50'] < F['gap_20_50'].shift(5)  # MA20 đang thu hẹp vs MA50
rsi_high     = F['rsi'] > 70

sell_combos = [
    ("P cat xuong MA20 + <MA50 + Vol>1.3",
     F['price_cross_ma20_dn'] & below_ma50 & (F['vol_ratio']>=1.3)),
    ("P cat xuong MA50 + Vol>1.5",
     F['price_cross_ma50_dn'] & vol_hi),
    ("P cat xuong MA50 + MA50 giam + <MA200",
     F['price_cross_ma50_dn'] & ma50_slope_dn & below_ma200),
    ("MA20 cat xuong MA50 (Death Cross nho) + <MA200",
     F['cross_20_50_dn'] & below_ma200),
    ("MA20 cat xuong MA50 + Vol>1.2",
     F['cross_20_50_dn'] & (F['vol_ratio']>=1.2)),
    ("Full Bear: P<MA20<MA50 + MA50 giam + Vol>1.3",
     below_ma20 & below_ma50 & ma20_slope_dn & ma50_slope_dn & (F['vol_ratio']>=1.3)),
    ("Spread thu hep: MA20-MA50 gap giam + RSI>65",
     spread_shrink & (F['rsi']>65) & F['above_ma50']),
    ("P>MA20>MA50>MA200 nhung spread thu hep + RSI>72",
     above_all & spread_shrink & (F['rsi']>72) & ma20_slope_dn),
    ("P vuot MA200 qua xa (>+20%) + RSI>70",
     (F['dist_ma200']>0.20) & rsi_high),
    ("P vuot MA50 qua xa (>+15%) + Vol thap",
     (F['dist_ma50']>0.15) & (F['vol_ratio']<0.8)),
]

print(f"\n  {'Combo BAN':<58} {'N':>6} {'Giam5':>6} {'Giam10':>6} {'Giam20':>6} {'Ret20':>7} {'Ret40':>7}")
print("  " + H[:108])
for name, mask in sell_combos:
    sub = F[mask]
    if len(sub) < 30: continue
    print(f"  {name:<58} {len(sub):>6,} "
          f"{sub['fwd5'].lt(0).mean():>6.1%} "
          f"{sub['fwd10'].lt(0).mean():>6.1%} "
          f"{sub['fwd20'].lt(0).mean():>6.1%} "
          f"{sub['fwd20'].mean():>7.3f} "
          f"{sub['fwd40'].mean():>7.3f}")

# ══════════════════════════════════════════════════════════════════════════════
print(f"\n{SH}")
print("PHAN TICH 8: OPTIMAL — Combo tot nhat theo Ret20 x Win20")
print(SH)

# So sánh tất cả MA state + vol + slope
df_eval['score_state'] = (
    df_eval['above_ma20'].astype(int) +
    df_eval['above_ma50'].astype(int) +
    df_eval['above_ma200'].astype(int) +
    ma20_slope_up.astype(int) +
    ma50_slope_up.astype(int) +
    ma200_slope_up.astype(int)
)
print("\n  Score (0-6): so tieu chi MA duong thoa man")
print(f"  {'Score':<10} {'N':>7} {'Win5':>6} {'Win20':>6} {'Win40':>6} {'Ret20':>7} {'Ret40':>7}")
for sc in range(7):
    sub = df_eval[df_eval['score_state'] == sc]
    if len(sub) < 100: continue
    print(f"  {sc}/6{'':<6} {len(sub):>7,} "
          f"{sub['fwd5'].gt(0).mean():>6.1%} "
          f"{sub['fwd20'].gt(0).mean():>6.1%} "
          f"{sub['fwd40'].gt(0).mean():>6.1%} "
          f"{sub['fwd20'].mean():>7.3f} "
          f"{sub['fwd40'].mean():>7.3f}")

# Score 6 (tất cả dương) + volume cao
sub6_vol = df_eval[(df_eval['score_state']==6) & vol_hi]
sub6_all = df_eval[df_eval['score_state']==6]
print(f"\n  Score=6 (all MA bullish) + Vol>1.5: N={len(sub6_vol):,} | Win20={sub6_vol['fwd20'].gt(0).mean():.1%} | Ret20={sub6_vol['fwd20'].mean():.4f} | Ret40={sub6_vol['fwd40'].mean():.4f}")
print(f"  Score=6 (all MA bullish) no filter: N={len(sub6_all):,} | Win20={sub6_all['fwd20'].gt(0).mean():.1%} | Ret20={sub6_all['fwd20'].mean():.4f} | Ret40={sub6_all['fwd40'].mean():.4f}")

# Optimal: pullback to MA20 trong full bull
sub_pb = df_eval[near_ma20 & above_50_200 & ma50_slope_up & (df_eval['vol_ratio']>=1.2)]
print(f"  Pullback MA20 in uptrend: N={len(sub_pb):,} | Win20={sub_pb['fwd20'].gt(0).mean():.1%} | Ret20={sub_pb['fwd20'].mean():.4f} | Ret40={sub_pb['fwd40'].mean():.4f}")

print(f"\n=== HOAN TAT ===")
