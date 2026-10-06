import pandas as pd
import streamlit as st
from config import COLOR_PALETTE
from services.auth_service import logout_user
from services.api_client import fetch_stats, fetch_logs

def render_worker_view():
    """Giao diện dành riêng cho Công nhân giám sát tại xưởng (Operator View)"""
    user = st.session_state.get("user", {})

    # --- SIDEBAR ---
    st.sidebar.markdown(f"### 👤 {user.get('full_name', 'Công Nhân')}")
    st.sidebar.markdown('<span class="role-badge-worker">👨‍🔧 CÔNG NHÂN VẬN HÀNH</span>', unsafe_allow_html=True)
    st.sidebar.markdown(f"**Tài khoản:** `{user.get('username', 'worker')}`")

    st.sidebar.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    if st.sidebar.button("🚪 Đăng Xuất", use_container_width=True):
        logout_user()

    st.sidebar.markdown("---")
    st.sidebar.markdown("##### ⚙️ Tự động làm mới")
    auto_refresh = st.sidebar.checkbox("Bật làm mới tự động", value=True)
    refresh_sec = st.sidebar.slider("Chu kỳ (giây)", min_value=2, max_value=20, value=3)

    # --- HEADER ---
    st.markdown('<div class="app-title-gradient">🏭 Trạm Giám Sát Dây Chuyền Phân Loại</div>', unsafe_allow_html=True)
    status_badge = f"<span class='live-badge'><span class='live-dot'></span> LIVE SCADA FEED ({refresh_sec}s)</span>" if auto_refresh else "<span style='color: #64748B; font-size: 0.85rem;'>⏸️ Tạm dừng tự động làm mới</span>"
    st.markdown(f'<div class="app-subtitle">Màn hình vận hành dành cho Công nhân trực ca &nbsp;&bull;&nbsp; {status_badge}</div>', unsafe_allow_html=True)

    # Realtime Fragment: Cập nhật mượt mà tại chỗ mà không gây tối mờ toàn màn hình
    @st.fragment(run_every=f"{refresh_sec}s" if auto_refresh else None)
    def render_worker_realtime_data():
        stats = fetch_stats()
        logs = fetch_logs(limit=25)
        counts = stats.get("counts", {"RED": 0, "YELLOW": 0, "GREEN": 0})
        total = stats.get("total_count", 0)
        speed = stats.get("productivity_per_minute", 0.0)
        anomaly = stats.get("anomaly_alert", "")

        # --- ANOMALY ALERT ---
        if anomaly:
            st.markdown(f"""
            <div class="pulse-alert-box">
                <div style="font-size: 2.2rem;">🚨</div>
                <div>
                    <div class="alert-title">PHÁT HIỆN DẤU HIỆU BẤT THƯỜNG TRÊN DÂY CHUYỀN!</div>
                    <div class="alert-desc">{anomaly} — <strong>Vui lòng kiểm tra khay cấp liệu và camera cảm biến ngay!</strong></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # --- 5 KPI CARDS ---
        c1, c2, c3, c4, c5 = st.columns(5)

        with c1:
            st.markdown(f"""
            <div class="kpi-card kpi-total">
                <div class="kpi-title">📦 Tổng Sản Phẩm</div>
                <div class="kpi-value">{total:,}</div>
                <div class="kpi-sub">Toàn ca sản xuất</div>
            </div>
            """, unsafe_allow_html=True)

        with c2:
            pct_red = (counts.get('RED', 0) / total * 100) if total > 0 else 0
            st.markdown(f"""
            <div class="kpi-card kpi-red">
                <div class="kpi-title" style="color: #FB7185;">🔴 Thùng Đỏ</div>
                <div class="kpi-value" style="color: #FB7185;">{counts.get('RED', 0):,}</div>
                <div class="kpi-sub">Chiếm {pct_red:.1f}%</div>
            </div>
            """, unsafe_allow_html=True)

        with c3:
            pct_yel = (counts.get('YELLOW', 0) / total * 100) if total > 0 else 0
            st.markdown(f"""
            <div class="kpi-card kpi-yellow">
                <div class="kpi-title" style="color: #FBBF24;">🟡 Thùng Vàng</div>
                <div class="kpi-value" style="color: #FBBF24;">{counts.get('YELLOW', 0):,}</div>
                <div class="kpi-sub">Chiếm {pct_yel:.1f}%</div>
            </div>
            """, unsafe_allow_html=True)

        with c4:
            pct_grn = (counts.get('GREEN', 0) / total * 100) if total > 0 else 0
            st.markdown(f"""
            <div class="kpi-card kpi-green">
                <div class="kpi-title" style="color: #34D399;">🟢 Thùng Xanh</div>
                <div class="kpi-value" style="color: #34D399;">{counts.get('GREEN', 0):,}</div>
                <div class="kpi-sub">Chiếm {pct_grn:.1f}%</div>
            </div>
            """, unsafe_allow_html=True)

        with c5:
            st.markdown(f"""
            <div class="kpi-card kpi-speed">
                <div class="kpi-title" style="color: #C084FC;">⚡ Năng Suất</div>
                <div class="kpi-value" style="color: #C084FC;">{speed:.1f}</div>
                <div class="kpi-sub">Sản phẩm / phút</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)

        # --- RECENT SORTING LOGS ---
        st.markdown("### 📋 Lịch Sử Gạt Sản Phẩm Vừa Đi Qua")

        if logs:
            df = pd.DataFrame(logs)
            df['time_str'] = pd.to_datetime(df['created_at']).dt.strftime('%H:%M:%S  (%d/%m/%Y)')
            df['confidence_pct'] = (df['confidence'] * 100).round(1).astype(str) + '%'
            
            def format_color_badge(val):
                if val == "RED":
                    return "🔴 ĐỎ (RED)"
                elif val == "YELLOW":
                    return "🟡 VÀNG (YELLOW)"
                elif val == "GREEN":
                    return "🟢 XANH (GREEN)"
                return val

            df['color_display'] = df['color_label'].apply(format_color_badge)
            df_display = df[['id', 'color_display', 'confidence_pct', 'time_str']]
            df_display.columns = ['ID', 'Màu Phân Loại', 'Độ Tin Cậy AI', 'Thời Gian Gạt']

            st.dataframe(df_display, use_container_width=True, height=420)
        else:
            st.info("Chưa có bản ghi phân loại nào được gửi lên từ hệ thống.")

    render_worker_realtime_data()

