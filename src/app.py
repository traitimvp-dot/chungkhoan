import streamlit as st
import duckdb
import pandas as pd
import plotly.graph_objects as go
from streamlit_lightweight_charts import renderLightweightCharts
import os
import sys
import time

# Đường dẫn tuyệt đối chuẩn xác
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "trading_data.duckdb")

# Cấu hình giao diện trang web
st.set_page_config(page_title="Vnstock Dashboard", page_icon="📈", layout="wide")


# Tắt cache cho load_data vì truy vấn DuckDB nội bộ vốn đã rất nhanh
# Việc tắt cache giúp biểu đồ tự động cập nhật ngay khi CSDL có dữ liệu mới
def load_data(symbol):
    con = duckdb.connect(DB_PATH, read_only=True)
    # Lấy toàn bộ dữ liệu của 1 mã, sắp xếp theo thời gian tăng dần
    query = f"SELECT * FROM historical_prices WHERE symbol = '{symbol}' ORDER BY time ASC"
    df = con.execute(query).df()
    con.close()
    
    if not df.empty:
        # Chuyển đổi định dạng ngày tháng để vẽ biểu đồ cho đẹp
        df['time'] = pd.to_datetime(df['time']).dt.date
        df.set_index('time', inplace=True)
    return df

# Xây dựng giao diện chính
st.title("📈 Dashboard Phân Tích Cổ Phiếu")
st.markdown("Dữ liệu được lấy từ **Vnstock** và lưu trữ tốc độ cao trên **DuckDB**.")

# Lấy danh sách mã cổ phiếu
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

# Sidebar (Thanh công cụ bên trái)
st.sidebar.header("🔍 Bộ lọc tra cứu")
selected_symbol = st.sidebar.selectbox("Chọn mã cổ phiếu (Tự động cập nhật):", symbols)

# Nút bấm để reload dữ liệu (Clear Cache)
if st.sidebar.button("Làm mới dữ liệu (Refresh)"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")

# Nút cập nhật dữ liệu tự động bị thiếu
is_updating = os.path.exists(os.path.join(BASE_DIR, "scripts", "update.lock"))

if is_updating:
    st.sidebar.warning("⏳ Đang tải dữ liệu ngầm...")
    st.sidebar.button("Đang xử lý...", disabled=True, use_container_width=True)
else:
    # Nút có màu nổi bật (primary) khi rảnh rỗi
    if st.sidebar.button("📥 Tải thêm Dữ liệu Cuối ngày", type="primary", use_container_width=True):
        import subprocess
        script_path = os.path.join(BASE_DIR, "scripts", "update_daily.py")
        subprocess.Popen([sys.executable, script_path])
        # Chờ 1 chút để script tạo file update.lock
        time.sleep(1) 
        # F5 lại giao diện ngay lập tức để chuyển nút sang trạng thái đang chạy
        st.rerun()

# Lựa chọn loại biểu đồ
chart_type = st.sidebar.radio("Loại biểu đồ:", ["Đường (Line)", "Nến Nhật (Plotly)", "TradingView (Mượt nhất)"])

st.sidebar.markdown("---")
st.sidebar.info("Ứng dụng phát triển bởi Vnstock Vibe Coder")

# Khu vực hiển thị chính
df = load_data(selected_symbol)

if not df.empty:
    st.subheader(f"Tổng quan mã: {selected_symbol}")

    # Lấy thông số để tính toán
    latest_data = df.iloc[-1]
    start_price = df.iloc[0]['close']
    end_price = latest_data['close']
    growth = ((end_price - start_price) / start_price) * 100

    # Bố cục 3 cột hiển thị thẻ thông số (Metrics)
    col1, col2, col3 = st.columns(3)
    col1.metric(label="Giá đóng cửa (mới nhất)", value=f"{end_price:,.2f}", delta=f"{end_price - df.iloc[-2]['close']:,.2f}")
    col2.metric(label="Khối lượng giao dịch", value=f"{int(latest_data['volume']):,}")
    col3.metric(label="Mức tăng trưởng (1 năm)", value=f"{growth:.2f}%")

    st.markdown("---")

    # Vẽ biểu đồ giá
    st.subheader("Biểu đồ giá")
    if chart_type == "Đường (Line)":
        st.line_chart(df['close'], height=600, use_container_width=True)
    elif chart_type == "Nến Nhật (Plotly)":
        fig = go.Figure(data=[go.Candlestick(
            x=df.index,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name=selected_symbol
        )])
        fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0), 
            xaxis_rangeslider_visible=False,
            height=600
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        # Dùng lõi TradingView (Lightweight Charts)
        # Chuẩn bị dữ liệu định dạng dictionary
        df_tv = df.reset_index()
        df_tv['time'] = df_tv['time'].astype(str)
        candles = df_tv[['time', 'open', 'high', 'low', 'close']].to_dict('records')
    
        # Tính màu cho Volume
        volumes = []
        for _, row in df_tv.iterrows():
            color = 'rgba(38, 166, 154, 0.5)' if row['close'] >= row['open'] else 'rgba(239, 83, 80, 0.5)'
            volumes.append({"time": row['time'], "value": row['volume'], "color": color})
        
        chartOptions = {
            "height": 600,
            "layout": {"textColor": 'black', "background": {"type": 'solid', "color": 'white'}},
            "rightPriceScale": {"scaleMargins": {"top": 0.1, "bottom": 0.3}},
            "timeScale": {"timeVisible": True, "secondsVisible": False}
        }
    
        series = [
            {
                "type": 'Candlestick',
                "data": candles,
                "options": {"upColor": '#26a69a', "downColor": '#ef5350', "borderVisible": False, "wickUpColor": '#26a69a', "wickDownColor": '#ef5350'}
            },
            {
                "type": 'Histogram',
                "data": volumes,
                "options": {"color": '#26a69a', "priceFormat": {"type": 'volume'}, "priceScaleId": ''},
                "priceScale": {"scaleMargins": {"top": 0.8, "bottom": 0}}
            }
        ]
    
        renderLightweightCharts([{"chart": chartOptions, "series": series}], 'tv_chart')

    # Hiển thị bảng dữ liệu thô
    st.subheader("Bảng dữ liệu chi tiết")
    # Đảo ngược lại để xem ngày mới nhất ở trên cùng
    st.dataframe(df.sort_index(ascending=False), use_container_width=True)
