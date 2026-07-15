import streamlit as st
import duckdb
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from streamlit_lightweight_charts import renderLightweightCharts
import streamlit.components.v1 as components
import ta
import os
import sys
import time
import importlib.util

# Đường dẫn tuyệt đối chuẩn xác
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "trading_data.duckdb")

# Cấu hình giao diện trang web
st.set_page_config(page_title="Vnstock Dashboard", page_icon="📈", layout="wide")

# Import strategy module từ cùng thư mục src/
_strategy_path = os.path.join(BASE_DIR, "src", "strategy.py")
_spec = importlib.util.spec_from_file_location("strategy", _strategy_path)
_strategy_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_strategy_mod)
get_buy_candidates = _strategy_mod.get_buy_candidates
get_sell_candidates = _strategy_mod.get_sell_candidates

@st.cache_data(ttl=60)
def load_market_overview():
    con = duckdb.connect(DB_PATH, read_only=True)
    query = """
    WITH ordered_prices AS (
        SELECT symbol, time, close, volume,
               LAG(close, 1) OVER w as prev_close_1,
               LAG(close, 3) OVER w as prev_close_3,
               LAG(close, 7) OVER w as prev_close_7,
               LAG(close, 22) OVER w as prev_close_1m
        FROM historical_prices
        WHERE length(symbol) = 3
        WINDOW w AS (PARTITION BY symbol ORDER BY time)
    ),
    latest_dates AS (
        SELECT symbol, MAX(time) as latest_time
        FROM historical_prices
        WHERE length(symbol) = 3
        GROUP BY symbol
    )
    SELECT p.symbol as "Mã CP",
           p.close as "Giá",
           round((p.close - p.prev_close_1) / p.prev_close_1 * 100, 2) as "% Thay đổi",
           round((p.close - p.prev_close_3) / p.prev_close_3 * 100, 2) as "% 3 Ngày",
           round((p.close - p.prev_close_7) / p.prev_close_7 * 100, 2) as "% 7 Ngày",
           round((p.close - p.prev_close_1m) / p.prev_close_1m * 100, 2) as "% 1 Tháng",
           p.volume as "Khối lượng",
           c."Sàn",
           c."Ngành"
    FROM ordered_prices p
    JOIN latest_dates l ON p.symbol = l.symbol AND p.time = l.latest_time
    LEFT JOIN company_info c ON p.symbol = c."Mã CP"
    WHERE p.prev_close_1 IS NOT NULL
    ORDER BY p.symbol
    """
    df = con.execute(query).df()
    con.close()
    df = df.drop_duplicates(subset=["Mã CP"], keep='last')
    return df

@st.cache_data(ttl=300)
def load_data(symbol):
    con = duckdb.connect(DB_PATH, read_only=True)
    query = f"SELECT * FROM historical_prices WHERE symbol = '{symbol}' ORDER BY time ASC"
    df = con.execute(query).df()
    con.close()
    
    if not df.empty:
        df['time'] = pd.to_datetime(df['time']).dt.date
        df.set_index('time', inplace=True)
        # Loại bỏ các dòng bị trùng lặp ngày (giữ lại bản ghi mới nhất) để tránh lỗi biểu đồ
        df = df[~df.index.duplicated(keep='last')]
    return df

def show_chart_dialog_content(symbol):
    df = load_data(symbol)
    
    if df.empty:
        st.warning(f"Không có dữ liệu cho mã {symbol}.")
        return

    tab1, tab2 = st.tabs(["📈 Biểu đồ Kỹ thuật", "📋 Lịch sử Giá"])
    
    with tab1:
        # Tạo sẵn vùng chứa cho biểu đồ để render sau khi đã lấy được giá trị timeframe bên dưới
        chart_container = st.container()
        
        # Hàng chứa tùy chọn khung thời gian và ghi chú các đường MA
        col_tf, col_legend = st.columns([1, 1])
        with col_tf:
            timeframe = st.pills(
                "Khung thời gian", 
                options=["6 Tháng", "1 Năm", "Tất cả"], 
                default="1 Năm", 
                key=f"tf_{symbol}", 
                label_visibility="collapsed"
            )
        with col_legend:
            st.markdown(
                "<div style='text-align: right; padding-top: 5px; font-size: 14px;'>"
                "<span style='color: #f39c12; font-weight: bold;'>— SMA 20</span> &nbsp;&nbsp;&nbsp; "
                "<span style='color: #3498db; font-weight: bold;'>— SMA 50</span> &nbsp;&nbsp;&nbsp; "
                "<span style='color: #9b59b6; font-weight: bold;'>— SMA 150</span>"
                "</div>", 
                unsafe_allow_html=True
            )
            
        if not timeframe:
            timeframe = "1 Năm"
        
        # Nút chiến lược trong chart tab
        buy_key = f"show_buy_{symbol}"
        sell_key = f"show_sell_{symbol}"
        if buy_key not in st.session_state:
            st.session_state[buy_key] = False
        if sell_key not in st.session_state:
            st.session_state[sell_key] = False
        
        col_s1, col_s2, col_s3 = st.columns([1, 1, 2])
        if col_s1.button(
            "🟢 Tín hiệu Mua" if not st.session_state[buy_key] else "✅ Tín hiệu Mua",
            key=f"btn_buy_{symbol}", use_container_width=True,
            type="primary" if st.session_state[buy_key] else "secondary"
        ):
            st.session_state[buy_key] = not st.session_state[buy_key]
        if col_s2.button(
            "🔴 Tín hiệu Bán" if not st.session_state[sell_key] else "✅ Tín hiệu Bán",
            key=f"btn_sell_{symbol}", use_container_width=True,
            type="primary" if st.session_state[sell_key] else "secondary"
        ):
            st.session_state[sell_key] = not st.session_state[sell_key]
        
        # Hiển thị trạng thái đang bật
        status_parts = []
        if st.session_state[buy_key]:
            status_parts.append("🟢 MUA")
        if st.session_state[sell_key]:
            status_parts.append("🔴 BÁN")
        if status_parts:
            col_s3.caption(f"Đang hiện: {' + '.join(status_parts)} — bấm lại để tắt")

        df_filtered = df.copy()
        if timeframe != "Tất cả":
            end_date = df_filtered.index.max()
            if timeframe == "6 Tháng":
                start_date = end_date - pd.Timedelta(days=180)
            elif timeframe == "1 Năm":
                start_date = end_date - pd.Timedelta(days=365)
            df_filtered = df_filtered[df_filtered.index >= start_date]
            
        with chart_container:
            if df_filtered.empty:
                st.warning(f"Không có dữ liệu cho mã {symbol} trong khoảng thời gian này.")
            else:
                # Tính toán các chỉ báo kỹ thuật trước khi cắt dữ liệu (để không bị mất đoạn đầu)
                df_tv = df.reset_index()
                df_tv['sma_20'] = ta.trend.sma_indicator(df_tv['close'], window=20)
                df_tv['sma_50'] = ta.trend.sma_indicator(df_tv['close'], window=50)
                df_tv['sma_150'] = ta.trend.sma_indicator(df_tv['close'], window=150)
                
                # Tính các chỉ báo cho tín hiệu mua/bán
                close_s = df_tv['close']
                volume_s = df_tv['volume']
                high_s = df_tv['high']
                low_s = df_tv['low']
                
                delta = close_s.diff()
                gain = delta.clip(lower=0).rolling(14).mean()
                loss = (-delta.clip(upper=0)).rolling(14).mean()
                rs = gain / loss.replace(0, np.nan)
                df_tv['rsi'] = 100 - (100 / (1 + rs))
                
                ema12 = close_s.ewm(span=12).mean()
                ema26 = close_s.ewm(span=26).mean()
                macd_line = ema12 - ema26
                df_tv['macd_hist'] = macd_line - macd_line.ewm(span=9).mean()
                df_tv['prev_macd'] = df_tv['macd_hist'].shift(1)
                df_tv['vol_avg20'] = volume_s.rolling(20).mean()
                df_tv['high20'] = high_s.rolling(20).max()
                df_tv['low20'] = low_s.rolling(20).min()
                df_tv['sma50_col'] = close_s.rolling(50).mean()
                df_tv['prev_above_sma50'] = (close_s.shift(1) > df_tv['sma50_col'].shift(1))
                
                # Sau đó mới cắt df_tv theo khung thời gian giống df_filtered
                if timeframe != "Tất cả":
                    df_tv = df_tv[df_tv['time'] >= start_date]
                    
                df_tv['time'] = df_tv['time'].astype(str)
                
                candles = df_tv[['time', 'open', 'high', 'low', 'close']].to_dict('records')
                sma_20 = df_tv[['time', 'sma_20']].dropna().rename(columns={'sma_20': 'value'}).to_dict('records')
                sma_50 = df_tv[['time', 'sma_50']].dropna().rename(columns={'sma_50': 'value'}).to_dict('records')
                sma_150 = df_tv[['time', 'sma_150']].dropna().rename(columns={'sma_150': 'value'}).to_dict('records')
            
                volumes = []
                for index, row in df_tv.iterrows():
                    color = '#26a69a' if row['close'] >= row['open'] else '#ef5350'
                    volumes.append({
                        'time': row['time'],
                        'value': row['volume'],
                        'color': color
                    })
                
                # Tính markers tín hiệu mua/bán (2 loại độc lập, có thể bật cùng lúc)
                markers = []
                
                if st.session_state.get(buy_key):
                    df_sig_buy = df_tv.dropna(subset=['rsi', 'vol_avg20', 'high20', 'sma_20'])
                    buy_rows = df_sig_buy[
                        (df_sig_buy['close'] >= df_sig_buy['high20']) &
                        (df_sig_buy['volume'] >= 1.5 * df_sig_buy['vol_avg20']) &
                        (df_sig_buy['rsi'] < 70) &
                        (df_sig_buy['close'] > df_sig_buy['sma_20'])
                    ]
                    for _, r in buy_rows.iterrows():
                        markers.append({
                            "time": r['time'],
                            "position": "belowBar",
                            "color": "#00e676",
                            "shape": "arrowUp",
                            "text": "MUA"
                        })

                if st.session_state.get(sell_key):
                    df_sig_sell = df_tv.dropna(subset=['rsi', 'macd_hist', 'prev_macd', 'vol_avg20', 'low20', 'sma50_col'])
                    for _, r in df_sig_sell.iterrows():
                        score = (
                            int(r['rsi'] > 72) +
                            int(r['close'] <= r['low20'] and r['volume'] >= 1.5 * r['vol_avg20']) +
                            int(r['macd_hist'] < 0 and r['prev_macd'] >= 0 and r['rsi'] > 55) +
                            int(r['close'] < r['sma50_col'])
                        )
                        if score >= 2:
                            markers.append({
                                "time": r['time'],
                                "position": "aboveBar",
                                "color": "#ff1744",
                                "shape": "arrowDown",
                                "text": "BÁN"
                            })
                
                # Sắp xếp markers theo thời gian (bắt buộc với Lightweight Charts)
                markers.sort(key=lambda x: x['time'])
                    
                priceVolumeChartOptions = {
                    "height": 450,
                    "rightPriceScale": {
                        "scaleMargins": {
                            "top": 0.1,
                            "bottom": 0.25,
                        },
                        "borderVisible": False,
                    },
                    "overlayPriceScales": {
                        "scaleMargins": {
                            "top": 0.7,
                            "bottom": 0,
                        }
                    },
                    "layout": {
                        "background": {
                            "type": 'solid',
                            "color": '#131722'
                        },
                        "textColor": '#d1d4dc',
                    },
                    "grid": {
                        "vertLines": {
                            "color": 'rgba(42, 46, 57, 0.5)',
                        },
                        "horzLines": {
                            "color": 'rgba(42, 46, 57, 0.6)',
                        }
                    },
                    "timeScale": {
                        "barSpacing": 8,
                        "rightOffset": 5,
                    }
                }
                
                candlestick_series = {
                    "type": 'Candlestick',
                    "data": candles,
                    "options": {
                        "upColor": '#26a69a',
                        "downColor": '#ef5350',
                        "borderVisible": False,
                        "wickUpColor": '#26a69a',
                        "wickDownColor": '#ef5350',
                    }
                }
                if markers:
                    candlestick_series["markers"] = markers
                
                priceVolumeSeries = [
                    candlestick_series,
                    {
                        "type": 'Histogram',
                        "data": volumes,
                        "options": {"color": '#26a69a', "priceFormat": {"type": 'volume'}, "priceScaleId": ''},
                        "priceScale": {
                            "scaleMargins": {
                                "top": 0.8,
                                "bottom": 0,
                            }
                        }
                    },
                    {
                        "type": "Line",
                        "data": sma_20,
                        "options": {
                            "color": "#f39c12",
                            "lineWidth": 1,
                            "priceLineVisible": False
                        }
                    },
                    {
                        "type": "Line",
                        "data": sma_50,
                        "options": {
                            "color": "#3498db",
                            "lineWidth": 1,
                            "priceLineVisible": False
                        }
                    },
                    {
                        "type": "Line",
                        "data": sma_150,
                        "options": {
                            "color": "#9b59b6",
                            "lineWidth": 1,
                            "priceLineVisible": False
                        }
                    }
                ]
            
                sig_key_chart = f"{symbol}_{timeframe}_{st.session_state.get(buy_key)}_{st.session_state.get(sell_key)}"
                renderLightweightCharts([
                    {
                        "chart": priceVolumeChartOptions,
                        "series": priceVolumeSeries
                    }
                ], f"chart_{sig_key_chart}")

        
    with tab2:
        st.dataframe(
            df[['open', 'high', 'low', 'close', 'volume']].sort_index(ascending=False).rename(
                columns={
                    'open': 'Mở cửa',
                    'high': 'Cao nhất',
                    'low': 'Thấp nhất',
                    'close': 'Đóng cửa',
                    'volume': 'Khối lượng'
                }
            ),
            use_container_width=True,
            height=450,
            column_config={
                "Khối lượng": st.column_config.NumberColumn(format="%,d")
            }
        )

# --- PHẦN GIAO DIỆN CHÍNH ---


df_market = load_market_overview()

if not df_market.empty:
    st.sidebar.header("🔍 Tra cứu Nhanh")
    search_query = st.sidebar.text_input("Gõ mã cổ phiếu (VD: FPT):", key="search_input").strip().upper()


    
    if "filter_vol" not in st.session_state:
        st.session_state.filter_vol = False
    if "filter_pct" not in st.session_state:
        st.session_state.filter_pct = False
    if "filter_exchange" not in st.session_state:
        st.session_state.filter_exchange = False
    if "filter_industry" not in st.session_state:
        st.session_state.filter_industry = False

    with st.sidebar.popover("➕ Thêm điều kiện"):
        st.session_state.filter_vol = st.checkbox("Khối lượng", value=st.session_state.filter_vol)
        st.session_state.filter_pct = st.checkbox("Phần trăm Tăng/Giảm", value=st.session_state.filter_pct)
        st.session_state.filter_exchange = st.checkbox("Sàn giao dịch", value=st.session_state.filter_exchange)
        st.session_state.filter_industry = st.checkbox("Ngành", value=st.session_state.filter_industry)
        
    has_active_filters = (
        st.session_state.filter_vol or 
        st.session_state.filter_pct or 
        st.session_state.filter_exchange or 
        st.session_state.filter_industry or 
        search_query != ""
    )
    
    if has_active_filters:
        if st.sidebar.button("❌ Bỏ tất cả điều kiện lọc", use_container_width=True):
            st.session_state.filter_vol = False
            st.session_state.filter_pct = False
            st.session_state.filter_exchange = False
            st.session_state.filter_industry = False
            if "search_input" in st.session_state:
                st.session_state.search_input = ""
            st.rerun()
    if search_query:
        df_market = df_market[df_market["Mã CP"].str.contains(search_query)]


        
    if st.session_state.filter_vol:
        st.sidebar.markdown("<p style='margin-bottom: 0px; font-weight: bold;'>Lọc theo Khối lượng</p>", unsafe_allow_html=True)
        c1, c2 = st.sidebar.columns([1, 2])
        vol_op = c1.selectbox("Phép so sánh", [">", "<", "="], key="vol_op", label_visibility="collapsed")
        vol_val = c2.number_input("Giá trị", min_value=0, value=100000, step=10000, key="vol_val", label_visibility="collapsed")
        
        if vol_op == ">":
            df_market = df_market[df_market["Khối lượng"] > vol_val]
        elif vol_op == "<":
            df_market = df_market[df_market["Khối lượng"] < vol_val]
        else:
            df_market = df_market[df_market["Khối lượng"] == vol_val]

    if st.session_state.filter_pct:
        st.sidebar.markdown("<p style='margin-bottom: 0px; margin-top: 10px; font-weight: bold;'>Lọc theo % Thay đổi</p>", unsafe_allow_html=True)
        c1, c2 = st.sidebar.columns([1, 2])
        pct_op = c1.selectbox("Phép so sánh", [">", "<", "="], key="pct_op", label_visibility="collapsed")
        pct_val = c2.number_input("Giá trị (%)", value=2.0, step=0.1, format="%.2f", key="pct_val", label_visibility="collapsed")
        
        if pct_op == ">":
            df_market = df_market[df_market["% Thay đổi"] > pct_val]
        elif pct_op == "<":
            df_market = df_market[df_market["% Thay đổi"] < pct_val]
        else:
            df_market = df_market[df_market["% Thay đổi"] == pct_val]

    if st.session_state.filter_exchange:
        st.sidebar.markdown("<p style='margin-bottom: 0px; margin-top: 10px; font-weight: bold;'>Lọc theo Sàn</p>", unsafe_allow_html=True)
        exchanges = df_market["Sàn"].dropna().unique().tolist()
        selected_exchanges = st.sidebar.multiselect("Chọn sàn", exchanges, default=[], key="sel_exchange", label_visibility="collapsed", placeholder="Chọn sàn (Mặc định: Tất cả)")
        if selected_exchanges:
            df_market = df_market[df_market["Sàn"].isin(selected_exchanges)]

    if st.session_state.filter_industry:
        st.sidebar.markdown("<p style='margin-bottom: 0px; margin-top: 10px; font-weight: bold;'>Lọc theo Ngành</p>", unsafe_allow_html=True)
        industries = sorted(df_market["Ngành"].dropna().unique().tolist())
        selected_industries = st.sidebar.multiselect("Chọn ngành", industries, default=[], key="sel_industry", label_visibility="collapsed", placeholder="Chọn ngành (Mặc định: Tất cả)")
        if selected_industries:
            df_market = df_market[df_market["Ngành"].isin(selected_industries)]
        
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔄 Cập nhật Dữ liệu")
    if os.path.exists(os.path.join(BASE_DIR, "scripts", "update.lock")):
        try:
            con2 = duckdb.connect(DB_PATH, read_only=True)
            q = "SELECT COUNT(*) FROM (SELECT symbol, CAST(MAX(time) AS DATE) as m FROM historical_prices WHERE length(symbol) = 3 GROUP BY symbol) t WHERE m = (SELECT CAST(MAX(time) AS DATE) FROM historical_prices)"
            updated = con2.execute(q).fetchone()[0]
            total = con2.execute("SELECT COUNT(DISTINCT symbol) FROM historical_prices WHERE length(symbol) = 3").fetchone()[0]
            con2.close()
            st.sidebar.button(f"⏳ Đang tải... ({updated}/{total})", type="secondary", use_container_width=True, disabled=True)
        except Exception:
            st.sidebar.button("⏳ Đang tải...", type="secondary", use_container_width=True, disabled=True)
    else:
        if st.sidebar.button("📥 Tải thêm Dữ liệu Cuối ngày", type="primary", use_container_width=True):
            import subprocess
            script_path = os.path.join(BASE_DIR, "scripts", "update_daily.py")
            subprocess.Popen([sys.executable, script_path], creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP)
            time.sleep(1) 
            st.rerun()
            
    st.sidebar.markdown("---")
    st.sidebar.info("Ứng dụng phát triển bởi Vnstock Vibe Coder")

    # Banner chiến lược hiện tại
    mode = st.session_state.get("strategy_mode")
    if mode == "buy":
        st.success(
            "🟢 **Chiến lược Mua đang kích hoạt** — "
            "Hiển thị các mã có tín hiệu: Giá phá đỉnh 20 phiën + KL 1.5x + RSI < 70 + Trên SMA20. "
            f"| Win-rate backtest: **50.8%** | Return TB: **+2.55%/20 phiẫn** | "
            f"Tìm thấy **{len(df_market)} mã**")
    elif mode == "sell":
        st.error(
            "🔴 **Chiến lược Bán đang kích hoạt** — "
            "Hiển thị các mã yếu: RSI>72 / Phá đáy 20p / MACD cắt xuống / Dưới SMA50 (>= 2 tiêu chí). "
            f"| Giảm sau 20p: **42%** | "
            f"Tìm thấy **{len(df_market)} mã**")
    else:
        st.markdown("💡 *Bấm vào một dòng bất kỳ để xem biểu đồ kỹ thuật chi tiết*")
    
    # Custom styling for % Thay đổi (optional, but requested by user if we could, we can just use dataframe default formatting)
    event = st.dataframe(
        df_market,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        height=600,
        column_config={
            "Khối lượng": st.column_config.NumberColumn(format="%,d")
        }
    )
    
    st.caption(f"**Tổng số:** {len(df_market)} bản ghi")
    
    if event.selection.rows:
        selected_idx = event.selection.rows[0]
        selected_symbol = df_market.iloc[selected_idx]["Mã CP"]
        
        # Lấy lại giá và tính % để đưa vào title
        df_temp = load_data(selected_symbol)
        if len(df_temp) >= 2:
            latest_close = df_temp.iloc[-1]['close']
            prev_close = df_temp.iloc[-2]['close']
            change_pct = (latest_close - prev_close) / prev_close * 100
            
            if change_pct > 6.5:
                color = "violet" # Tím
            elif change_pct < -6.5:
                color = "blue" # Xanh lơ
            elif change_pct > 0:
                color = "green" # Xanh lá
            elif change_pct < 0:
                color = "red" # Đỏ
            else:
                color = "orange" # Vàng
                
            sign = "+" if change_pct > 0 else ""
            dialog_title = f"{selected_symbol} | Giá: {latest_close:,.2f} | :{color}[{sign}{change_pct:.2f}%]"
        else:
            dialog_title = f"{selected_symbol}"
            
        @st.dialog(dialog_title, width="large")
        def dynamic_dialog():
            show_chart_dialog_content(selected_symbol)
            
        dynamic_dialog()
else:
    st.warning("🔄 Hệ thống đang đồng bộ dữ liệu. File CSDL đang bị khóa hoặc chưa có dữ liệu. Bạn vui lòng đợi 1 chút rồi Refresh lại trang nhé!")

