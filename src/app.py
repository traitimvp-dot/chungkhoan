import streamlit as st
import duckdb
import pandas as pd
import plotly.graph_objects as go
from streamlit_lightweight_charts import renderLightweightCharts
import streamlit.components.v1 as components
import ta
import os
import sys
import time

# Đường dẫn tuyệt đối chuẩn xác
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "trading_data.duckdb")

# Cấu hình giao diện trang web
st.set_page_config(page_title="Vnstock Dashboard", page_icon="📈", layout="wide")

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
           p.volume as "Khối lượng"
    FROM ordered_prices p
    JOIN latest_dates l ON p.symbol = l.symbol AND p.time = l.latest_time
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
                
                priceVolumeSeries = [
                    {
                        "type": 'Candlestick',
                        "data": candles,
                        "options": {
                            "upColor": '#26a69a',
                            "downColor": '#ef5350',
                            "borderVisible": False,
                            "wickUpColor": '#26a69a',
                            "wickDownColor": '#ef5350',
                        }
                    },
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
            
                renderLightweightCharts([
                    {
                        "chart": priceVolumeChartOptions,
                        "series": priceVolumeSeries
                    }
                ], f"chart_{symbol}")
        
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

st.title("📈 Toàn cảnh Thị trường")
st.markdown("Dữ liệu được lấy từ **Vnstock** và lưu trữ tốc độ cao trên **DuckDB**.")

df_market = load_market_overview()

if not df_market.empty:
    st.sidebar.header("🔍 Tra cứu Nhanh")
    search_query = st.sidebar.text_input("Gõ mã cổ phiếu (VD: FPT):").strip().upper()
    
    if "filter_vol" not in st.session_state:
        st.session_state.filter_vol = False
    if "filter_pct" not in st.session_state:
        st.session_state.filter_pct = False

    with st.sidebar.popover("➕ Thêm điều kiện"):
        st.session_state.filter_vol = st.checkbox("Khối lượng", value=st.session_state.filter_vol)
        st.session_state.filter_pct = st.checkbox("Phần trăm Tăng/Giảm", value=st.session_state.filter_pct)
        
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

