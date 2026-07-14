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

# Tắt cache cho load_data vì truy vấn DuckDB nội bộ vốn đã rất nhanh
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

st.title("📈 Dashboard Phân Tích Cổ Phiếu")
st.markdown("Dữ liệu được lấy từ **Vnstock** và lưu trữ tốc độ cao trên **DuckDB**.")

try:
    con = duckdb.connect(DB_PATH, read_only=True)
    symbols_df = con.execute("SELECT DISTINCT symbol FROM historical_prices WHERE length(symbol) = 3 ORDER BY symbol ASC").df()
    symbols = symbols_df['symbol'].tolist()
    con.close()
except Exception:
    symbols = []

if not symbols:
    st.warning("🔄 Hệ thống đang đồng bộ dữ liệu. File CSDL đang bị khóa hoặc chưa có dữ liệu. Bạn vui lòng đợi 1 chút rồi Refresh lại trang nhé!")
    st.stop()

st.sidebar.header("🔍 Bộ lọc tra cứu")
selected_symbol = st.sidebar.selectbox("Chọn mã cổ phiếu (Tự động cập nhật):", symbols)

if st.sidebar.button("Làm mới dữ liệu (Refresh)"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")
timeframe = st.sidebar.selectbox("Khung thời gian:", ["6 Tháng", "1 Năm", "Tất cả"], index=1)

st.sidebar.markdown("---")
st.sidebar.subheader("🔄 Cập nhật Dữ liệu")

if os.path.exists(os.path.join(BASE_DIR, "scripts", "update.lock")):
    st.sidebar.button("⏳ Đang tải...", type="secondary", use_container_width=True, disabled=True)
else:
    if st.sidebar.button("📥 Tải thêm Dữ liệu Cuối ngày", type="primary", use_container_width=True):
        import subprocess
        script_path = os.path.join(BASE_DIR, "scripts", "update_daily.py")
        subprocess.Popen([sys.executable, script_path], creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP)
        time.sleep(1) 
        st.rerun()

chart_type = st.sidebar.radio("Loại biểu đồ:", ["TradingView (Mượt nhất)", "Đường (Line)"])

st.sidebar.markdown("---")
st.sidebar.info("Ứng dụng phát triển bởi Vnstock Vibe Coder")

df = load_data(selected_symbol)

if not df.empty:
    st.subheader(f"Tổng quan mã: {selected_symbol}")

    # Cắt dữ liệu theo khung thời gian
    df_filtered = df.copy()
    if timeframe != "Tất cả":
        end_date = df_filtered.index.max()
        if timeframe == "6 Tháng":
            start_date = end_date - pd.Timedelta(days=180)
        elif timeframe == "1 Năm":
            start_date = end_date - pd.Timedelta(days=365)
        df_filtered = df_filtered[df_filtered.index >= start_date]

    if df_filtered.empty:
        df_filtered = df # Fallback nếu dữ liệu quá ít

    latest_data = df_filtered.iloc[-1]
    start_price = df_filtered.iloc[0]['close']
    end_price = latest_data['close']
    growth = ((end_price - start_price) / start_price) * 100

    delta_price = end_price - df_filtered.iloc[-2]['close'] if len(df_filtered) >= 2 else 0

    col1, col2, col3 = st.columns(3)
    col1.metric(label="Giá đóng cửa (mới nhất)", value=f"{end_price:,.2f}", delta=f"{delta_price:,.2f}")
    col2.metric(label="Khối lượng giao dịch", value=f"{int(latest_data['volume']):,}")
    col3.metric(label=f"Mức tăng trưởng ({timeframe})", value=f"{growth:.2f}%")

    st.markdown("---")

    st.subheader("Biểu đồ giá")
    if chart_type == "Đường (Line)":
        st.line_chart(df_filtered['close'], height=600, use_container_width=True)
    else:
        # Tính toán chỉ báo trên toàn bộ dữ liệu df (để SMA không bị NaN ở đoạn đầu)
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
            color = 'rgba(0, 150, 136, 0.8)' if row['close'] >= row['open'] else 'rgba(255, 82, 82, 0.8)'
            volumes.append({'time': row['time'], 'value': row['volume'], 'color': color})
            
        priceVolumeChartOptions = {
            "height": 500,
            "rightPriceScale": {
                "scaleMargins": {
                    "top": 0.2,
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
                    "color": 'rgba(42, 46, 57, 0)',
                },
                "horzLines": {
                    "color": 'rgba(42, 46, 57, 0.6)',
                }
            },
            "timeScale": {
                "barSpacing": 8,  # 8 pixels per candle, ~200-250 candles visible -> ~1 year
                "rightOffset": 5,
                "timeVisible": True
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
                    "wickDownColor": '#ef5350'
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
                    "title": "SMA 20",
                    "priceLineVisible": False
                }
            },
            {
                "type": "Line",
                "data": sma_50,
                "options": {
                    "color": "#3498db",
                    "lineWidth": 1,
                    "title": "SMA 50",
                    "priceLineVisible": False
                }
            },
            {
                "type": "Line",
                "data": sma_150,
                "options": {
                    "color": "#9b59b6",
                    "lineWidth": 1,
                    "title": "SMA 150",
                    "priceLineVisible": False
                }
            }
        ]
    
        renderLightweightCharts([
            {
                "chart": priceVolumeChartOptions,
                "series": priceVolumeSeries
            }
        ], "priceAndVolume")
    
    st.subheader("Bảng dữ liệu chi tiết")
    st.dataframe(df_filtered.sort_index(ascending=False), use_container_width=True)
