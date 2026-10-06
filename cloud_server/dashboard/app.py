import os
import time
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Cấu hình trang Streamlit
st.set_page_config(
    page_title="IoT Sorting System Dashboard",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Style CSS tùy chỉnh
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 0.5rem;
    }
    .metric-card {
        background-color: #F8FAFC;
        border-radius: 10px;
        padding: 15px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    .alert-box {
        background-color: #FEF2F2;
        border-left: 5px solid #EF4444;
        color: #991B1B;
        padding: 12px 16px;
        border-radius: 6px;
        font-weight: 600;
        margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

# Lấy URL Backend API từ môi trường hoặc mặc định localhost
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

st.markdown('<div class="main-header">🏭 Giám Sát Hệ Thống Phân Loại Sản Phẩm IoT (Level 4)</div>', unsafe_allow_html=True)
st.caption("Hệ thống tự động phân loại 3 màu: Đỏ (RED), Vàng (YELLOW), Xanh lá (GREEN)")

# Sidebar Cấu hình
st.sidebar.header("⚙️ Cấu hình Dashboard")
backend_url = st.sidebar.text_input("Backend API Base URL", value=API_BASE_URL)
auto_refresh = st.sidebar.checkbox("Tự động làm mới (Auto Refresh)", value=True)
refresh_interval = st.sidebar.slider("Tần suất làm mới (giây)", min_value=2, max_value=30, value=5)

if st.sidebar.button("🔄 Nạp lại dữ liệu ngay"):
    st.rerun()

# Hàm gọi API lấy Thống kê
@st.cache_data(ttl=2)
def fetch_stats(url):
    try:
        response = requests.get(f"{url}/api/v1/stats", timeout=3)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return None

# Hàm gọi API lấy Logs gần nhất
@st.cache_data(ttl=2)
def fetch_recent_logs(url, limit=30):
    try:
        response = requests.get(f"{url}/api/v1/logs?limit={limit}", timeout=3)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return []

# Lấy dữ liệu
stats_data = fetch_stats(backend_url)
logs_data = fetch_recent_logs(backend_url)

if not stats_data:
    st.warning(f"⚠️ Không thể kết nối tới Cloud Backend API tại `{backend_url}`. Vui lòng kiểm tra server FastAPI đã khởi động chưa.")
    st.info("💡 Bạn có thể chạy Backend server bằng lệnh: `uvicorn main:app --reload --port 8000` tại thư mục `cloud_server/backend`.")
else:
    # 1. Cảnh báo bất thường nếu có
    if stats_data.get("anomaly_alert"):
        st.markdown(f'<div class="alert-box">🚨 {stats_data["anomaly_alert"]}</div>', unsafe_allow_html=True)

    # 2. Thẻ chỉ số tổng quan (KPI Metrics)
    col1, col2, col3, col4, col5 = st.columns(5)
    
    counts = stats_data.get("counts", {"RED": 0, "YELLOW": 0, "GREEN": 0})
    total_count = stats_data.get("total_count", 0)
    productivity = stats_data.get("productivity_per_minute", 0.0)

    with col1:
        st.metric(label="📦 Tổng sản phẩm", value=total_count)
    with col2:
        st.metric(label="🔴 Sản phẩm Đỏ", value=counts.get("RED", 0))
    with col3:
        st.metric(label="🟡 Sản phẩm Vàng", value=counts.get("YELLOW", 0))
    with col4:
        st.metric(label="🟢 Sản phẩm Xanh", value=counts.get("GREEN", 0))
    with col5:
        st.metric(label="⚡ Năng suất (Sp/phút)", value=f"{productivity:.1f}")

    st.markdown("---")

    # 3. Biểu đồ Visualizations
    chart_col1, chart_col2 = st.columns(2)

    colors_map = {
        'RED': '#EF4444',
        'YELLOW': '#F59E0B',
        'GREEN': '#10B981'
    }

    with chart_col1:
        st.subheader("📊 Tỷ lệ phân loại theo màu (%)")
        pie_df = pd.DataFrame([
            {"Màu": "Đỏ (RED)", "Số lượng": counts.get("RED", 0), "Color": colors_map['RED']},
            {"Màu": "Vàng (YELLOW)", "Số lượng": counts.get("YELLOW", 0), "Color": colors_map['YELLOW']},
            {"Màu": "Xanh (GREEN)", "Số lượng": counts.get("GREEN", 0), "Color": colors_map['GREEN']}
        ])
        
        if total_count > 0:
            fig_pie = px.pie(
                pie_df, 
                names="Màu", 
                values="Số lượng", 
                color="Màu",
                color_discrete_map={
                    "Đỏ (RED)": colors_map['RED'],
                    "Vàng (YELLOW)": colors_map['YELLOW'],
                    "Xanh (GREEN)": colors_map['GREEN']
                },
                hole=0.4
            )
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("Chưa có dữ liệu phân loại để vẽ biểu đồ.")

    with chart_col2:
        st.subheader("📈 Số lượng sản phẩm đếm được")
        bar_df = pd.DataFrame([
            {"Màu": "Đỏ (RED)", "Số lượng": counts.get("RED", 0)},
            {"Màu": "Vàng (YELLOW)", "Số lượng": counts.get("YELLOW", 0)},
            {"Màu": "Xanh (GREEN)", "Số lượng": counts.get("GREEN", 0)}
        ])
        fig_bar = px.bar(
            bar_df,
            x="Màu",
            y="Số lượng",
            color="Màu",
            color_discrete_map={
                "Đỏ (RED)": colors_map['RED'],
                "Vàng (YELLOW)": colors_map['YELLOW'],
                "Xanh (GREEN)": colors_map['GREEN']
            },
            text_auto=True
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    # 4. Lịch sử log phân loại gần đây
    st.subheader("📋 Lịch sử phân loại sản phẩm gần nhất")
    if logs_data:
        df_logs = pd.DataFrame(logs_data)
        df_logs['created_at'] = pd.to_datetime(df_logs['created_at']).dt.strftime('%H:%M:%S - %d/%m/%Y')
        df_logs = df_logs[['id', 'color_label', 'confidence', 'created_at']]
        df_logs.columns = ['ID Log', 'Nhãn Màu', 'Độ Tin Cậy', 'Thời Gian Phân Loại']
        st.dataframe(df_logs, use_container_width=True, height=250)
    else:
        st.info("Chưa có bản ghi log nào.")

# Tự động reload trang theo chu kỳ slider
if auto_refresh:
    time.sleep(refresh_interval)
    st.rerun()
