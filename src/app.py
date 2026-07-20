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
import datetime
import importlib.util
from vnstock.ui import Reference
from vnstock import Company

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

@st.cache_data(ttl=1801, show_spinner="Đang quét tín hiệu MUA (tốn khoảng 3-5s)...")
def scan_buy_signals(target_date: str = None):
    return _strategy_mod.get_buy_candidates(days=3, target_date=target_date)

@st.cache_data(ttl=1801, show_spinner="Đang quét tín hiệu MUA 2 (tốn khoảng 3-5s)...")
def scan_buy_signals2(target_date: str = None):
    return _strategy_mod.get_buy_candidates(days=3, target_date=target_date, buy_method="Tín hiệu Mua 2")

@st.cache_data(ttl=1801, show_spinner="Đang quét tín hiệu BÁN (tốn khoảng 3-5s)...")
def scan_sell_signals(target_date: str = None):
    return _strategy_mod.get_sell_candidates(days=3, target_date=target_date)

@st.cache_data(ttl=1801, show_spinner="Đang quét tín hiệu BÁN 2 (tốn khoảng 3-5s)...")
def scan_sell_signals2(target_date: str = None):
    return _strategy_mod.get_sell_candidates(days=3, target_date=target_date, sell_method="Tín hiệu Bán 2")

@st.cache_data(ttl=1801, show_spinner="Đang quét tín hiệu MUA 3 (tốn khoảng 3-5s)...")
def scan_buy_signals3(target_date: str = None):
    return _strategy_mod.get_buy_candidates(days=3, target_date=target_date, buy_method="Tín hiệu Mua 3")

@st.cache_data(ttl=1801, show_spinner="Đang quét tín hiệu BÁN 3 (tốn khoảng 3-5s)...")
def scan_sell_signals3(target_date: str = None):
    return _strategy_mod.get_sell_candidates(days=3, target_date=target_date, sell_method="Tín hiệu Bán 3")

@st.cache_data(ttl=1801, show_spinner="Đang quét tín hiệu MUA 4 (tốn khoảng 3-5s)...")
def scan_buy_signals4(target_date: str = None):
    return _strategy_mod.get_buy_candidates(days=3, target_date=target_date, buy_method="Tín hiệu Mua 4")

@st.cache_data(ttl=1801, show_spinner="Đang mô phỏng Backtest cho danh sách hiện tại...")
def run_symbols_backtest(symbols: tuple, timeframe: str, buy_method: str, sell_method: str):
    results = []
    for sym in symbols:
        res = _strategy_mod.run_portfolio_backtest(sym, 100000000, timeframe, buy_method, sell_method)
        metrics = res.get("metrics")
        if metrics:
            results.append({
                "Mã CP": sym,
                "% Lãi/Lỗ": round(metrics["total_profit_pct"], 2),
                "Số lệnh": metrics["total_trades"],
                "Tỉ lệ Thắng": round(metrics["win_rate"], 2)
            })
            
    df_results = pd.DataFrame(results)
    return df_results




get_buy_candidates = _strategy_mod.get_buy_candidates
get_sell_candidates = _strategy_mod.get_sell_candidates

# ==============================================================================
# WATCHLIST — Lưu vào file JSON trong thư mục data/
# ==============================================================================

WATCHLIST_PATH = os.path.join(BASE_DIR, "data", "watchlist.json")

def load_watchlist() -> list:
    if os.path.exists(WATCHLIST_PATH):
        try:
            import json
            with open(WATCHLIST_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_watchlist(symbols: list):
    import json
    os.makedirs(os.path.dirname(WATCHLIST_PATH), exist_ok=True)
    with open(WATCHLIST_PATH, "w", encoding="utf-8") as f:
        json.dump(sorted(set(symbols)), f, ensure_ascii=False, indent=2)

def toggle_watchlist(symbol: str):
    wl = load_watchlist()
    if symbol in wl:
        wl.remove(symbol)
    else:
        wl.append(symbol)
    save_watchlist(wl)


@st.cache_data(ttl=60)
def load_market_overview():
    con = duckdb.connect(DB_PATH, read_only=True)
    query = """
    WITH ordered_prices AS (
        SELECT symbol, time, close, volume,
               LAG(close, 1) OVER w as prev_close_1,
               LAG(close, 3) OVER w as prev_close_3,
               LAG(close, 7) OVER w as prev_close_7,
               LAG(close, 22) OVER w as prev_close_1m,
               AVG(volume) OVER (PARTITION BY symbol ORDER BY time ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) as vol_ma20
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
           ROUND(p.vol_ma20, 0) as "KL TB 20 Phiên",
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
    df = df[df["Sàn"].isin(["HOSE", "HNX"])]
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

@st.cache_data(ttl=86400, show_spinner="Đang tải thông tin cơ bản...")
def get_or_fetch_company_profile(symbol):
    con = duckdb.connect(DB_PATH)
    # Check if table exists
    tables = con.execute("SHOW TABLES").df()
    if 'company_profile' not in tables['name'].values:
        import sys
        sys.path.append(BASE_DIR)
        from scripts.update_profile import init_db
        init_db(con)
        
    query = f"SELECT * FROM company_profile WHERE symbol = '{symbol}'"
    df = con.execute(query).df()
    
    if df.empty:
        # Fetch on demand
        ref = Reference()
        try:
            df_info = ref.company(symbol).info()
            if df_info is not None and not df_info.empty:
                df_info['symbol'] = symbol
                cols = [
                    'symbol', 'business_model', 'founded_date', 'charter_capital',
                    'number_of_employees', 'listing_date', 'par_value', 'exchange',
                    'listing_price', 'listed_volume', 'ceo_name', 'ceo_position',
                    'inspector_name', 'inspector_position', 'establishment_license',
                    'business_code', 'tax_id', 'auditor', 'company_type', 'address',
                    'phone', 'fax', 'email', 'website', 'branches', 'history',
                    'free_float_percentage', 'free_float', 'outstanding_shares', 'as_of_date'
                ]
                for c in cols:
                    if c not in df_info.columns:
                        df_info[c] = None
                df_info = df_info[cols]
                con.execute(f"DELETE FROM company_profile WHERE symbol = '{symbol}'")
                con.execute("INSERT INTO company_profile SELECT * FROM df_info")
                df = df_info
        except Exception as e:
            st.error(f"Lỗi tải thông tin cơ bản: {e}")
            
    con.close()
    
    if not df.empty:
        return df.iloc[0].to_dict()
    return None

@st.cache_data(ttl=86400, show_spinner="Đang tải sự kiện...")
def get_company_events(symbol):
    try:
        comp = Company(source="VCI", symbol=symbol)
        df_events = comp.events()
        if df_events is not None and not df_events.empty:
            # Lọc các sự kiện liên quan đến cổ tức (Cash Dividend, Stock Dividend) và phát hành (Issue)
            # Dựa vào event_list_name hoặc category
            df_div_issue = df_events[df_events['category'].str.contains('DIVIDEND|ISSUE|RIGHT', case=False, na=False) | 
                                     df_events['action_type_en'].str.contains('Dividend|Issue|Right', case=False, na=False)]
            return df_div_issue
    except Exception as e:
        print(f"Lỗi tải events cho {symbol}: {e}")
    return pd.DataFrame()

@st.cache_data(ttl=86400, show_spinner="Đang tải lịch sử tăng vốn...")
def get_capital_history(symbol):
    try:
        ref = Reference()
        df_cap = ref.company(symbol).capital_history()
        if df_cap is not None and not df_cap.empty:
            return df_cap
    except Exception as e:
        print(f"Lỗi tải capital history cho {symbol}: {e}")
    return pd.DataFrame()

@st.cache_data(ttl=86400, show_spinner="Đang tải KQKD...")
def get_income_statement(symbol):
    try:
        from vnstock.ui import Fundamental
        fun = Fundamental()
        df = fun.equity(symbol).income_statement(period="quarter")
        if df is not None and not df.empty:
            return df
    except Exception as e:
        print(f"Lỗi tải KQKD cho {symbol}: {e}")
    return pd.DataFrame()

def show_chart_dialog_content(symbol):
    df = load_data(symbol)
    
    if df.empty:
        st.warning(f"Không có dữ liệu cho mã {symbol}.")
        return


    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📈 Biểu đồ Kỹ thuật", "📋 Lịch sử Giá", "🧪 Backtest Chiến lược", "🏢 Thông tin Cơ bản", "📅 Lịch sử & Sự kiện"])
    
    with tab1:
        # Tạo sẵn vùng chứa cho biểu đồ để render sau khi đã lấy được giá trị timeframe bên dưới
        chart_container = st.container()
        
        # Hàng chứa tùy chọn khung thời gian và MA legend
        col_tf, col_legend = st.columns([1, 1])
        with col_tf:
            timeframe = st.pills(
                "Khung thời gian", 
                options=["6 Tháng", "1 Năm", "3 Năm", "Tất cả"], 
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
        
        st.markdown('''<style>
        div[data-testid="stButton"] button {
            padding: 0.2rem 0.5rem;
            min-height: 32px;
            height: 32px;
            font-size: 14px;
        }
        </style>''', unsafe_allow_html=True)
        
        # 2 combobox tín hiệu Mua / Bán + checkbox Theo dõi cùng hàng
        buy_signal_options = ["🟢 Tín hiệu Mua: (Tắt)"] + [f"🟢 {s}" for s in _strategy_mod.get_available_buy_signals()]
        sell_signal_options = ["🔴 Tín hiệu Bán: (Tắt)"] + [f"🔴 {s}" for s in _strategy_mod.get_available_sell_signals()]
        
        # Chia làm 6 cột: 2 cột đầu cho combobox, 3 cột giữa trống, cột 6 cho checkbox
        col_sig1, col_sig2, _, _, _, col_watch_sig = st.columns([1, 1, 1, 1, 1, 1])
        selected_buy_signal = col_sig1.selectbox(
            "Tín hiệu Mua",
            options=buy_signal_options,
            index=0,
            key=f"sel_buy_sig_{symbol}",
            label_visibility="collapsed"
        )
        selected_sell_signal = col_sig2.selectbox(
            "Tín hiệu Bán",
            options=sell_signal_options,
            index=0,
            key=f"sel_sell_sig_{symbol}",
            label_visibility="collapsed"
        )
        
        # Checkbox Theo dõi nằm ở cột thứ 6
        wl_tab = load_watchlist()
        is_watching_tab = symbol in wl_tab
        watch_label_tab = "⭐ Đang theo dõi" if is_watching_tab else "☆ Theo dõi"
        
        # Đẩy checkbox xuống một chút để cân đối với combobox
        col_watch_sig.markdown("<div style='padding-top: 5px;'></div>", unsafe_allow_html=True)
        if col_watch_sig.checkbox(watch_label_tab, value=is_watching_tab, key=f"watch_{symbol}"):
            if not is_watching_tab:
                toggle_watchlist(symbol)
                st.rerun()
        else:
            if is_watching_tab:
                toggle_watchlist(symbol)
                st.rerun()
        
        show_buy = not selected_buy_signal.endswith("(Tắt)")
        show_sell = not selected_sell_signal.endswith("(Tắt)")
        # Lấy tên thực từ option (bỏ emoji prefix "🟢 " / "🔴 ")
        buy_method_name = selected_buy_signal[2:].strip() if show_buy else None
        sell_method_name = selected_sell_signal[2:].strip() if show_sell else None
        active_signals = {
            "buy_method": buy_method_name,
            "sell_method": sell_method_name,
            "show_buy": show_buy,
            "show_sell": show_sell
        }

        df_filtered = df.copy()
        if timeframe != "Tất cả":
            end_date = df_filtered.index.max()
            if timeframe == "6 Tháng":
                start_date = end_date - pd.Timedelta(days=180)
            elif timeframe == "1 Năm":
                start_date = end_date - pd.Timedelta(days=365)
            elif timeframe == "3 Năm":
                start_date = end_date - pd.Timedelta(days=1095)
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
                
                # Cắt df_tv theo khung thời gian giống df_filtered
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
                
                # Markers tín hiệu mua/bán từ 2 selectbox độc lập
                markers = []
                
                if active_signals["show_buy"] or active_signals["show_sell"]:
                    # Dùng chiến lược Mua để tính chỉ báo cơ sở
                    buy_strat = _strategy_mod.get_buy_signal(active_signals["buy_method"]) if active_signals["show_buy"] else _strategy_mod.get_buy_signal(list(_strategy_mod.BUY_SIGNAL_REGISTRY.keys())[0])
                    df_sig = df.reset_index().copy()
                    df_sig = buy_strat.prepare_data(df_sig)
                    
                    if active_signals["show_buy"]:
                        df_sig_buy = buy_strat.generate_signals(df_sig.copy())
                        if timeframe != "Tất cả":
                            df_sig_buy = df_sig_buy[df_sig_buy['time'] >= start_date]
                        buy_rows = df_sig_buy[df_sig_buy['buy_signal']]
                        for _, r in buy_rows.iterrows():
                            markers.append({
                                "time": str(r['time']),
                                "position": "belowBar",
                                "color": "#00e676",
                                "shape": "arrowUp",
                                "text": "MUA"
                            })
                    
                    if active_signals["show_sell"]:
                        sell_strat = _strategy_mod.get_sell_signal(active_signals["sell_method"])
                        df_sig_sell = sell_strat.generate_signals(df_sig.copy())
                        if timeframe != "Tất cả":
                            df_sig_sell = df_sig_sell[df_sig_sell['time'] >= start_date]
                        sell_rows = df_sig_sell[df_sig_sell['sell_signal']]
                        for _, r in sell_rows.iterrows():
                            markers.append({
                                "time": str(r['time']),
                                "position": "aboveBar",
                                "color": "#ff1744",
                                "shape": "arrowDown",
                                "text": "BÁN"
                            })
                
                # Sắp xếp markers theo thời gian
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
            
                key_suffix = f"{show_buy}_{selected_buy_signal}_{show_sell}_{selected_sell_signal}"
                sig_key_chart = f"{symbol}_{timeframe}_{key_suffix}"
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
        
    with tab3:
        st.markdown("### 🧪 Hệ thống Backtest Mô phỏng")
        col_bt1, col_bt2, col_bt3, col_bt4 = st.columns(4)
        capital = col_bt1.number_input("Số tiền đầu tư (VNĐ)", value=100000000, step=10000000, key=f"bt_cap_{symbol}")
        bt_timeframe = col_bt2.selectbox("Khoảng thời gian", ["1 Năm", "2 Năm", "3 Năm", "4 Năm", "5 Năm", "Tất cả"], index=5, key=f"bt_tf_{symbol}")
        buy_sigs = _strategy_mod.get_available_buy_signals()
        sell_sigs = _strategy_mod.get_available_sell_signals()
        buy_idx = buy_sigs.index("Tín hiệu Mua 4") if "Tín hiệu Mua 4" in buy_sigs else 0
        sell_idx = sell_sigs.index("Tín hiệu Bán 2") if "Tín hiệu Bán 2" in sell_sigs else 0
        bt_buy_method = col_bt3.selectbox("🟢 Tín hiệu Mua", buy_sigs, index=buy_idx, key=f"bt_buy_{symbol}")
        bt_sell_method = col_bt4.selectbox("🔴 Tín hiệu Bán", sell_sigs, index=sell_idx, key=f"bt_sell_{symbol}")
        
        if st.button("🚀 Chạy Backtest", type="primary", use_container_width=True, key=f"btn_run_bt_{symbol}"):
            with st.spinner("Đang chạy mô phỏng giao dịch..."):
                bt_results = _strategy_mod.run_portfolio_backtest(symbol, capital, bt_timeframe, bt_buy_method, bt_sell_method)
                
                df_trades = bt_results["trades"]
                if df_trades.empty:
                    st.info(f"Không có giao dịch nào được thực hiện trong thời gian {bt_timeframe}.")
                else:
                    m = bt_results["metrics"]
                    st.markdown("---")
                    c1, c2, c3 = st.columns(3)
                    
                    c1.metric("Tổng Tài sản (VNĐ)", f"{m['final_capital']:,.0f}", f"{m['total_profit_pct']:.2f}%", delta_color="normal")
                    c2.metric("Số lệnh giao dịch", f"{m['total_trades']}", "")
                    c3.metric("Tỉ lệ Thắng (Win rate)", f"{m['win_rate']:.1f}%", "")
                    
                    # BIỂU ĐỒ TRỰC QUAN
                    df_chart = bt_results.get("df_chart")
                    if df_chart is not None and not df_chart.empty:
                        st.markdown("#### 📊 Biểu đồ Trực quan")
                        df_chart['time'] = pd.to_datetime(df_chart['date']).dt.strftime('%Y-%m-%d')
                        
                        candles = df_chart[['time', 'open', 'high', 'low', 'close']].to_dict('records')
                        
                        # Sử dụng MA đã tính từ strategy (nằm trên full data) để không bị hụt đoạn đầu
                        if 'ma20' in df_chart.columns:
                            df_chart['sma_20'] = df_chart['ma20']
                        else:
                            df_chart['sma_20'] = ta.trend.sma_indicator(df_chart['close'], window=20)
                            
                        if 'ma50' in df_chart.columns:
                            df_chart['sma_50'] = df_chart['ma50']
                        else:
                            df_chart['sma_50'] = ta.trend.sma_indicator(df_chart['close'], window=50)
                            
                        if 'ma200' in df_chart.columns:
                            df_chart['sma_150'] = df_chart['ma200']
                        else:
                            df_chart['sma_150'] = ta.trend.sma_indicator(df_chart['close'], window=150)
                            
                        sma_20 = df_chart[['time', 'sma_20']].dropna().rename(columns={'sma_20': 'value'}).to_dict('records')
                        sma_50 = df_chart[['time', 'sma_50']].dropna().rename(columns={'sma_50': 'value'}).to_dict('records')
                        sma_150 = df_chart[['time', 'sma_150']].dropna().rename(columns={'sma_150': 'value'}).to_dict('records')
                        
                        volumes = []
                        for _, row in df_chart.iterrows():
                            color = '#26a69a' if row['close'] >= row['open'] else '#ef5350'
                            volumes.append({
                                'time': row['time'],
                                'value': row['volume'],
                                'color': color
                            })
                            
                        markers = []
                        for _, trade in df_trades.iterrows():
                            buy_date_str = str(trade['Ngày Mua'])[:10]
                            sell_date_str = str(trade['Ngày Bán'])[:10]
                            # Buy marker
                            markers.append({
                                "time": buy_date_str,
                                "position": "belowBar",
                                "color": "#00e676",
                                "shape": "arrowUp",
                                "text": "MUA"
                            })
                            # Sell marker
                            markers.append({
                                "time": sell_date_str,
                                "position": "aboveBar",
                                "color": "#ff5252",
                                "shape": "arrowDown",
                                "text": "BÁN"
                            })
                            
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
                                    "top": 0.8,
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
                                    "color": 'rgba(42, 46, 57, 0)'
                                },
                                "horzLines": {
                                    "color": 'rgba(42, 46, 57, 0.6)'
                                }
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
                            }
                        ]
                        
                        if sma_20:
                            priceVolumeSeries.append({
                                "type": "Line",
                                "data": sma_20,
                                "options": {"color": "#f39c12", "lineWidth": 1, "priceLineVisible": False}
                            })
                        if sma_50:
                            priceVolumeSeries.append({
                                "type": "Line",
                                "data": sma_50,
                                "options": {"color": "#3498db", "lineWidth": 1, "priceLineVisible": False}
                            })
                        if sma_150:
                            priceVolumeSeries.append({
                                "type": "Line",
                                "data": sma_150,
                                "options": {"color": "#9b59b6", "lineWidth": 1, "priceLineVisible": False}
                            })
                        
                        renderLightweightCharts([
                            {
                                "chart": priceVolumeChartOptions,
                                "series": priceVolumeSeries
                            }
                        ], f"bt_chart_{symbol}")
                    
                    st.markdown("#### 📜 Lịch sử Giao dịch")
                    def color_profit_loss(val):
                        if isinstance(val, (int, float)):
                            color = '#00e676' if val > 0 else '#ff5252' if val < 0 else 'inherit'
                            return f'color: {color}'
                        return ''
                        
                    styled_df = df_trades.style.map(color_profit_loss, subset=['Lãi/Lỗ (%)', 'Tiền Lãi/Lỗ'])
                    
                    st.dataframe(
                        styled_df, 
                        use_container_width=True, 
                        hide_index=True,
                        column_config={
                            "Ngày Mua": st.column_config.DateColumn(format="DD/MM/YYYY"),
                            "Ngày Bán": st.column_config.DateColumn(format="DD/MM/YYYY"),
                            "Giá Mua": st.column_config.NumberColumn(format="%,.2f"),
                            "Giá Bán": st.column_config.NumberColumn(format="%,.2f"),
                            "Khối lượng": st.column_config.NumberColumn(format="%,d"),
                            "Tiền Lãi/Lỗ": st.column_config.NumberColumn(format="%,.0f"),
                            "Lãi/Lỗ (%)": st.column_config.NumberColumn(format="%.2f%%")
                        }
                    )

    with tab4:
        profile = get_or_fetch_company_profile(symbol)
        
        # Lấy thêm tên công ty từ bảng company_info
        company_name = ""
        try:
            con_tmp = duckdb.connect(DB_PATH, read_only=True)
            res = con_tmp.execute(f"SELECT \"Tên CTY\" FROM company_info WHERE \"Mã CP\" = '{symbol}'").fetchone()
            if res:
                company_name = f" - {res[0]}"
            con_tmp.close()
        except Exception:
            pass
            
        if not profile:
            st.warning(f"Không tìm thấy thông tin cơ bản cho mã {symbol}.")
        else:
            st.markdown(f"### 🏢 Thông tin Cơ bản: {symbol}{company_name}")
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Ngày thành lập", str(profile.get('founded_date', 'N/A')))
            c2.metric("Vốn điều lệ (Tỷ VNĐ)", f"{profile.get('charter_capital', 0):,.0f}" if profile.get('charter_capital') else "N/A")
            c3.metric("Số nhân viên", f"{profile.get('number_of_employees', 0):,.0f}" if profile.get('number_of_employees') else "N/A")
            c4.metric("Ngày niêm yết", str(profile.get('listing_date', 'N/A')))
            
            c5, c6, c7, c8 = st.columns(4)
            c5.metric("Sàn", str(profile.get('exchange', 'N/A')))
            c6.metric("Giá chào sàn", f"{profile.get('listing_price', 0):,.0f}" if profile.get('listing_price') else "N/A")
            c7.metric("KL Niêm yết (Triệu CP)", f"{profile.get('listed_volume', 0):,.1f}" if profile.get('listed_volume') else "N/A")
            c8.metric("Chủ tịch HĐQT", str(profile.get('ceo_name', 'N/A')))
            
            st.markdown("---")
            
            st.markdown(f"**Website:** [{profile.get('website', 'N/A')}]({profile.get('website', '')})")
            st.markdown(f"**Địa chỉ:** {profile.get('address', 'N/A')}")
            
            st.markdown("#### 🏢 Mô hình Kinh doanh")
            st.info(str(profile.get('business_model', 'Chưa cập nhật')))
            
            with st.expander("Lịch sử Hình thành"):
                st.markdown(str(profile.get('history', 'Chưa cập nhật')))

            with st.expander("📊 Báo cáo Kết quả Kinh doanh (Các Quý gần nhất)", expanded=True):
                st.info("Lưu ý: Gói tài khoản Vnstock hiện tại (Free) chỉ hỗ trợ lấy tối đa 8 Quý gần nhất. Để xem từ năm 2020, vui lòng sử dụng gói tài trợ (Sponsor).")
                df_income = get_income_statement(symbol)
                if df_income.empty:
                    st.warning("Chưa có dữ liệu Kết quả Kinh doanh.")
                else:
                    if 'item_id' in df_income.columns:
                        df_income_display = df_income.drop(columns=['item_id'])
                    else:
                        df_income_display = df_income.copy()
                    df_income_display = df_income_display.rename(columns={'item': 'Chỉ tiêu'})
                    
                    # Format các cột số thành có dấu phẩy ngăn cách hàng nghìn
                    cols_format = {}
                    
                    # Sắp xếp các cột quý theo thứ tự thời gian (tăng dần)
                    quarter_cols = [col for col in df_income_display.columns if col != 'Chỉ tiêu']
                    quarter_cols.sort()
                    df_income_display = df_income_display[['Chỉ tiêu'] + quarter_cols]
                    
                    for col in df_income_display.columns:
                        if col != 'Chỉ tiêu':
                            cols_format[col] = st.column_config.NumberColumn(format="%,.0f")
                            
                    st.dataframe(
                        df_income_display, 
                        use_container_width=True, 
                        hide_index=True,
                        column_config=cols_format
                    )

    with tab5:
        st.markdown(f"### 📅 Lịch sử Sự kiện & Tăng vốn - {symbol}")
        
        col_ev, col_cap = st.columns([6, 4])
        
        with col_ev:
            st.markdown("#### Lịch sử Cổ tức & Phát hành")
            df_events = get_company_events(symbol)
            if df_events.empty:
                st.info("Chưa có dữ liệu sự kiện hoặc công ty chưa trả cổ tức.")
            else:
                # Select important columns: public_date or exright_date, event_title_vi, exercise_ratio, value_per_share
                cols_to_show = {}
                if 'exright_date' in df_events.columns:
                    cols_to_show['exright_date'] = "Ngày GDKHQ"
                if 'payout_date' in df_events.columns:
                    cols_to_show['payout_date'] = "Ngày Thực Hiện"
                if 'event_title_vi' in df_events.columns:
                    cols_to_show['event_title_vi'] = "Sự Kiện"
                if 'exercise_ratio' in df_events.columns:
                    cols_to_show['exercise_ratio'] = "Tỷ Lệ"
                if 'value_per_share' in df_events.columns:
                    cols_to_show['value_per_share'] = "Giá Trị (VNĐ)"
                    
                df_events_display = df_events[list(cols_to_show.keys())].rename(columns=cols_to_show)
                
                # Format dates to string
                if "Ngày GDKHQ" in df_events_display.columns:
                    df_events_display["Ngày GDKHQ"] = pd.to_datetime(df_events_display["Ngày GDKHQ"]).dt.strftime('%d/%m/%Y')
                if "Ngày Thực Hiện" in df_events_display.columns:
                    df_events_display["Ngày Thực Hiện"] = pd.to_datetime(df_events_display["Ngày Thực Hiện"]).dt.strftime('%d/%m/%Y')
                
                st.dataframe(
                    df_events_display,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Giá Trị (VNĐ)": st.column_config.NumberColumn(format="%,.0f")
                    }
                )

        with col_cap:
            st.markdown("#### Lịch sử Thay đổi Vốn")
            df_cap = get_capital_history(symbol)
            if df_cap.empty:
                st.info("Chưa có dữ liệu thay đổi vốn.")
            else:
                df_cap_display = df_cap.copy()
                if 'date' in df_cap_display.columns:
                    df_cap_display['date'] = pd.to_datetime(df_cap_display['date']).dt.strftime('%d/%m/%Y').fillna('N/A')
                
                cols_cap = {'date': 'Ngày', 'charter_capital': 'Vốn Điều Lệ (VNĐ)'}
                
                df_cap_display = df_cap_display[list(cols_cap.keys())].rename(columns=cols_cap)
                st.dataframe(
                    df_cap_display,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Vốn Điều Lệ (VNĐ)": st.column_config.NumberColumn(format="%,.0f")
                    }
                )

# --- PHẦN GIAO DIỆN CHÍNH ---


df_market = load_market_overview()

if "max_date" not in st.session_state:
    try:
        con_tmp = duckdb.connect(DB_PATH, read_only=True)
        max_date_str = con_tmp.execute("SELECT MAX(time::DATE) FROM historical_prices").fetchone()[0]
        con_tmp.close()
        st.session_state.max_date = datetime.datetime.strptime(str(max_date_str), "%Y-%m-%d").date()
    except Exception:
        st.session_state.max_date = datetime.date.today()

if not df_market.empty:
    st.sidebar.header("🔍 Tra cứu Nhanh")
    search_query = st.sidebar.text_input("Gõ mã cổ phiếu (VD: FPT):", key="search_input").strip().upper()


    
    if "filter_watchlist" not in st.session_state:
        st.session_state.filter_watchlist = False
    if "filter_vol" not in st.session_state:
        st.session_state.filter_vol = False
    if "filter_pct" not in st.session_state:
        st.session_state.filter_pct = False
    if "filter_exchange" not in st.session_state:
        st.session_state.filter_exchange = False
    if "filter_industry" not in st.session_state:
        st.session_state.filter_industry = False
    if "filter_buy" not in st.session_state:
        st.session_state.filter_buy = False
    if "filter_buy2" not in st.session_state:
        st.session_state.filter_buy2 = False
    if "filter_buy3" not in st.session_state:
        st.session_state.filter_buy3 = False
    if "filter_buy4" not in st.session_state:
        st.session_state.filter_buy4 = False
    if "filter_sell" not in st.session_state:
        st.session_state.filter_sell = False
    if "filter_date" not in st.session_state:
        st.session_state.filter_date = False

    st.sidebar.checkbox("Danh sách theo dõi", key="filter_watchlist")
    st.sidebar.checkbox("Khối lượng", key="filter_vol")
    st.sidebar.checkbox("Phần trăm Tăng/Giảm", key="filter_pct")
    st.sidebar.checkbox("Sàn giao dịch", key="filter_exchange")
    st.sidebar.checkbox("Ngành", key="filter_industry")
    st.sidebar.checkbox("Ngày quét tín hiệu", key="filter_date")
    
    def on_filter_buy_change():
        if st.session_state.filter_buy:
            st.session_state.filter_buy2 = False
            st.session_state.filter_buy3 = False
            st.session_state.filter_buy4 = False
            st.session_state.filter_sell = False
            st.session_state.filter_sell2 = False
            st.session_state.filter_sell3 = False
            
    def on_filter_buy2_change():
        if st.session_state.filter_buy2:
            st.session_state.filter_buy = False
            st.session_state.filter_buy3 = False
            st.session_state.filter_buy4 = False
            st.session_state.filter_sell = False
            st.session_state.filter_sell2 = False
            st.session_state.filter_sell3 = False

    def on_filter_buy3_change():
        if st.session_state.filter_buy3:
            st.session_state.filter_buy = False
            st.session_state.filter_buy2 = False
            st.session_state.filter_buy4 = False
            st.session_state.filter_sell = False
            st.session_state.filter_sell2 = False
            st.session_state.filter_sell3 = False
            
    def on_filter_buy4_change():
        if st.session_state.filter_buy4:
            st.session_state.filter_buy = False
            st.session_state.filter_buy2 = False
            st.session_state.filter_buy3 = False
            st.session_state.filter_sell = False
            st.session_state.filter_sell2 = False
            st.session_state.filter_sell3 = False

    def on_filter_sell_change():
        if st.session_state.filter_sell:
            st.session_state.filter_buy = False
            st.session_state.filter_buy2 = False
            st.session_state.filter_buy3 = False
            st.session_state.filter_buy4 = False
            st.session_state.filter_sell2 = False
            st.session_state.filter_sell3 = False
            
    def on_filter_sell2_change():
        if st.session_state.filter_sell2:
            st.session_state.filter_buy = False
            st.session_state.filter_buy2 = False
            st.session_state.filter_buy3 = False
            st.session_state.filter_buy4 = False
            st.session_state.filter_sell = False
            st.session_state.filter_sell3 = False

    def on_filter_sell3_change():
        if st.session_state.filter_sell3:
            st.session_state.filter_buy = False
            st.session_state.filter_buy2 = False
            st.session_state.filter_buy3 = False
            st.session_state.filter_buy4 = False
            st.session_state.filter_sell = False
            st.session_state.filter_sell2 = False
            
    st.sidebar.checkbox("Tín hiệu MUA 1 (3 ngày)", key="filter_buy", on_change=on_filter_buy_change)
    st.sidebar.checkbox("Tín hiệu MUA 2 (3 ngày)", key="filter_buy2", on_change=on_filter_buy2_change)
    st.sidebar.checkbox("Tín hiệu MUA 3 (3 ngày)", key="filter_buy3", on_change=on_filter_buy3_change)
    st.sidebar.checkbox("Tín hiệu MUA 4 (3 ngày)", key="filter_buy4", on_change=on_filter_buy4_change)
    st.sidebar.checkbox("Tín hiệu BÁN 1 (3 ngày)", key="filter_sell", on_change=on_filter_sell_change)
    st.sidebar.checkbox("Tín hiệu BÁN 2 (3 ngày)", key="filter_sell2", on_change=on_filter_sell2_change)
    st.sidebar.checkbox("Tín hiệu BÁN 3 (3 ngày)", key="filter_sell3", on_change=on_filter_sell3_change)
    
    st.sidebar.checkbox("Lọc theo Backtest toàn TT", key="filter_strategy")
    if st.session_state.get("filter_strategy", False):
        st.sidebar.markdown("<p style='margin-bottom: 0px; margin-top: 5px; font-weight: bold;'>Tín hiệu Backtest</p>", unsafe_allow_html=True)
        buy_opts = _strategy_mod.get_available_buy_signals()
        sell_opts = _strategy_mod.get_available_sell_signals()
        buy_idx = buy_opts.index("Tín hiệu Mua 4") if "Tín hiệu Mua 4" in buy_opts else 0
        sell_idx = sell_opts.index("Tín hiệu Bán 2") if "Tín hiệu Bán 2" in sell_opts else 0
        st.sidebar.selectbox("Tín hiệu Mua", buy_opts, index=buy_idx, key="bt_buy_sig", label_visibility="collapsed")
        st.sidebar.selectbox("Tín hiệu Bán", sell_opts, index=sell_idx, key="bt_sell_sig", label_visibility="collapsed")
        st.sidebar.markdown("<p style='margin-bottom: 0px; margin-top: 5px; font-weight: bold;'>Thời gian Backtest</p>", unsafe_allow_html=True)
        timeframes = ["1 Năm", "2 Năm", "3 Năm", "4 Năm", "5 Năm", "Tất cả"]
        st.sidebar.selectbox("Thời gian", timeframes, index=5, key="bt_timeframe", label_visibility="collapsed")

    if search_query:
        df_market = df_market[df_market["Mã CP"].str.contains(search_query)]

    if st.session_state.filter_watchlist:
        watchlist = load_watchlist()
        if watchlist:
            df_market = df_market[df_market["Mã CP"].isin(watchlist)]
        else:
            df_market = df_market.iloc[0:0]  # Rỗng nếu chưa theo dõi ai

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
            
    if st.session_state.filter_date:
        st.sidebar.markdown("<p style='margin-bottom: 0px; margin-top: 10px; font-weight: bold;'>Chọn ngày quá khứ</p>", unsafe_allow_html=True)
        target_date = st.sidebar.date_input("Chọn ngày", value=st.session_state.max_date, max_value=st.session_state.max_date, format="DD/MM/YYYY", key="target_date_picker", label_visibility="collapsed")
        target_date_str = target_date.strftime("%Y-%m-%d")
    else:
        target_date_str = None
            
    if st.session_state.get("filter_buy", False):
        df_buy = scan_buy_signals(target_date_str)
        if not df_buy.empty:
            df_buy['TH Mua'] = 'Mua 1'
            df_market = df_market.merge(df_buy[['Mã CP', 'Ngày', 'TH Mua']].rename(columns={'Ngày': 'Ngày Mua'}), on='Mã CP', how='inner')
        else:
            df_market = df_market.iloc[0:0]
            
    if st.session_state.get("filter_buy2", False):
        df_buy2 = scan_buy_signals2(target_date_str)
        if not df_buy2.empty:
            df_buy2['TH Mua'] = 'Mua 2'
            df_market = df_market.merge(df_buy2[['Mã CP', 'Ngày', 'TH Mua']].rename(columns={'Ngày': 'Ngày Mua'}), on='Mã CP', how='inner')
        else:
            df_market = df_market.iloc[0:0]
            
    if st.session_state.get("filter_sell", False):
        df_sell = scan_sell_signals(target_date_str)
        if not df_sell.empty:
            df_sell['TH Bán'] = 'Bán 1'
            df_market = df_market.merge(df_sell[['Mã CP', 'Ngày', 'TH Bán']].rename(columns={'Ngày': 'Ngày Bán'}), on='Mã CP', how='inner')
        else:
            df_market = df_market.iloc[0:0]
            
    if st.session_state.get("filter_sell2", False):
        df_sell2 = scan_sell_signals2(target_date_str)
        if not df_sell2.empty:
            df_sell2['TH Bán'] = 'Bán 2'
            df_market = df_market.merge(df_sell2[['Mã CP', 'Ngày', 'TH Bán']].rename(columns={'Ngày': 'Ngày Bán'}), on='Mã CP', how='inner')
        else:
            df_market = df_market.iloc[0:0]
            
    if st.session_state.get("filter_buy3", False):
        df_buy3 = scan_buy_signals3(target_date_str)
        if not df_buy3.empty:
            df_buy3['TH Mua'] = 'Mua 3'
            df_market = df_market.merge(df_buy3[['Mã CP', 'Ngày', 'TH Mua']].rename(columns={'Ngày': 'Ngày Mua'}), on='Mã CP', how='inner')
        else:
            df_market = df_market.iloc[0:0]
            
    if st.session_state.get("filter_buy4", False):
        df_buy4 = scan_buy_signals4(target_date_str)
        if not df_buy4.empty:
            df_buy4['TH Mua'] = 'Mua 4'
            df_buy4['Sức mạnh Breakout'] = df_buy4['Vol/Avg20']
            df_market = df_market.merge(df_buy4[['Mã CP', 'Ngày', 'TH Mua', 'Sức mạnh Breakout']].rename(columns={'Ngày': 'Ngày Mua'}), on='Mã CP', how='inner')
            df_market = df_market.sort_values(by='Sức mạnh Breakout', ascending=False)
        else:
            df_market = df_market.iloc[0:0]
            
    if st.session_state.get("filter_sell3", False):
        df_sell3 = scan_sell_signals3(target_date_str)
        if not df_sell3.empty:
            df_sell3['TH Bán'] = 'Bán 3'
            df_market = df_market.merge(df_sell3[['Mã CP', 'Ngày', 'TH Bán']].rename(columns={'Ngày': 'Ngày Bán'}), on='Mã CP', how='inner')
        else:
            df_market = df_market.iloc[0:0]
            
    if st.session_state.get("filter_strategy", False):
        bt_buy = st.session_state.get("bt_buy_sig")
        bt_sell = st.session_state.get("bt_sell_sig")
        bt_tf = st.session_state.get("bt_timeframe", "Tất cả")
        if bt_buy and bt_sell:
            current_symbols = tuple(df_market['Mã CP'].tolist())
            if current_symbols:
                df_bt = run_symbols_backtest(current_symbols, bt_tf, bt_buy, bt_sell)
                if not df_bt.empty:
                    df_market = df_market.merge(df_bt, on='Mã CP', how='inner')
                    df_market = df_market.sort_values(by="% Lãi/Lỗ", ascending=False)
        
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

    active_filters = []
    if st.session_state.filter_vol:
        active_filters.append(f"Khối lượng {st.session_state.vol_op} {st.session_state.vol_val:,.0f}")
    if st.session_state.filter_pct:
        active_filters.append(f"% Thay đổi {st.session_state.pct_op} {st.session_state.pct_val}%")
    if st.session_state.filter_exchange:
        selected_exchanges = st.session_state.get("sel_exchange", [])
        if selected_exchanges:
            active_filters.append(f"Sàn: {', '.join(selected_exchanges)}")
    if st.session_state.filter_industry:
        selected_industries = st.session_state.get("sel_industry", [])
        if selected_industries:
            active_filters.append(f"Ngành: {', '.join(selected_industries)}")
    if st.session_state.get("filter_buy", False):
        active_filters.append(f"Tín hiệu MUA 1 (3 ngày trước {target_date_str})" if target_date_str else "Tín hiệu MUA 1 (3 ngày)")
    if st.session_state.get("filter_buy2", False):
        active_filters.append(f"Tín hiệu MUA 2 (3 ngày trước {target_date_str})" if target_date_str else "Tín hiệu MUA 2 (3 ngày)")
    if st.session_state.get("filter_buy3", False):
        active_filters.append(f"Tín hiệu MUA 3 (3 ngày trước {target_date_str})" if target_date_str else "Tín hiệu MUA 3 (3 ngày)")
    if st.session_state.get("filter_buy4", False):
        active_filters.append(f"Tín hiệu MUA 4 (3 ngày trước {target_date_str})" if target_date_str else "Tín hiệu MUA 4 (3 ngày)")
    if st.session_state.get("filter_sell", False):
        active_filters.append(f"Tín hiệu BÁN 1 (3 ngày trước {target_date_str})" if target_date_str else "Tín hiệu BÁN 1 (3 ngày)")
    if st.session_state.get("filter_sell2", False):
        active_filters.append(f"Tín hiệu BÁN 2 (3 ngày trước {target_date_str})" if target_date_str else "Tín hiệu BÁN 2 (3 ngày)")
    if st.session_state.get("filter_sell3", False):
        active_filters.append(f"Tín hiệu BÁN 3 (3 ngày trước {target_date_str})" if target_date_str else "Tín hiệu BÁN 3 (3 ngày)")
    if st.session_state.get("filter_strategy", False):
        bt_buy = st.session_state.get("bt_buy_sig")
        bt_sell = st.session_state.get("bt_sell_sig")
        bt_tf = st.session_state.get("bt_timeframe", "Tất cả")
        active_filters.append(f"Backtest {bt_buy} & {bt_sell} ({bt_tf})")
        
    if active_filters:
        msg = "🔍 **Đang lọc theo:** " + " | ".join(active_filters)
        if st.session_state.get("filter_buy", False):
            msg += " | 🟢 **Tín hiệu Mua 1:** Breakout 20 phiên + KL ≥ 1.5x + RSI < 70 + Trên MA20"
        if st.session_state.get("filter_buy2", False):
            msg += " | 🟢 **Tín hiệu Mua 2:** MA20 cắt lên MA50 (Golden Cross)"
        if st.session_state.get("filter_buy3", False):
            msg += " | 🟢 **Tín hiệu Mua 3:** Pullback MAs (Thuận thế 3 MA)"
        if st.session_state.get("filter_buy4", False):
            msg += " | 🟢 **Tín hiệu Mua 4:** Siêu Breakout (Vượt đỉnh 20 phiên + Vol lớn + MA20>MA50>MA200)"
        if st.session_state.get("filter_sell", False):
            msg += " | 🔴 **Tín hiệu Bán 1:** Gãy MA20/MA50, MACD cắt xuống, hoặc RSI > 70 kèm Vol xả"
        if st.session_state.get("filter_sell2", False):
            msg += " | 🔴 **Tín hiệu Bán 2:** MA20 cắt xuống MA50 (Death Cross)"
        if st.session_state.get("filter_sell3", False):
            msg += " | 🔴 **Tín hiệu Bán 3:** Gãy nền MA50 hoặc MA20 cắt xuống MA50"
        st.info(msg)
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
            "Khối lượng": st.column_config.NumberColumn(format="%,d"),
            "KL TB 20 Phiên": st.column_config.NumberColumn(format="%,d"),
            "Sức mạnh Breakout": st.column_config.NumberColumn(format="%.1fx", help="Tỷ lệ Đột biến Khối lượng so với trung bình 20 phiên. Càng cao càng mạnh.")
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

