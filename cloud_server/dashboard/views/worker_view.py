import pandas as pd
import streamlit as st
from config import COLOR_PALETTE
from services.auth_service import logout_user
from services.api_client import fetch_stats, fetch_logs

def render_worker_view():
    """Giao diện dành riêng cho Công nhân giám sát tại xưởng (Operator View) - Chuẩn Industrial SCADA"""
    user = st.session_state.get("user", {})

    # --- SIDEBAR ---
    st.sidebar.markdown(f"### {user.get('full_name', 'Công Nhân')}")
    st.sidebar.markdown('<span class="role-badge-worker">CÔNG NHÂN VẬN HÀNH</span>', unsafe_allow_html=True)
    st.sidebar.markdown(f"**Tài khoản:** `{user.get('username', 'worker')}`")

    st.sidebar.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    if st.sidebar.button("Đăng Xuất", use_container_width=True):
        logout_user()

    st.sidebar.markdown("---")
    st.sidebar.markdown("<div class='section-header' style='margin-top: 0;'>TỰ ĐỘNG LÀM MỚI</div>", unsafe_allow_html=True)
    auto_refresh = st.sidebar.checkbox("Bật làm mới tự động", value=True)
    refresh_sec = st.sidebar.slider("Chu kỳ làm mới (giây)", min_value=2, max_value=20, value=3)

    # --- HEADER ---
    status_badge = f"<span class='live-badge'><span class='live-dot'></span> LIVE SCADA ({refresh_sec}s)</span>" if auto_refresh else "<span class='scada-topbar-chip'>PAUSED</span>"
    st.markdown(f"""
    <div style="display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 12px; flex-wrap: wrap; gap: 8px;">
        <div>
            <div class="app-title-gradient">TRẠM GIÁM SÁT DÂY CHUYỀN PHÂN LOẠI</div>
            <div class="app-subtitle" style="margin-bottom: 0;">Màn hình vận hành &amp; giám sát trực tiếp dành cho Công nhân trực ca</div>
        </div>
        <div style="display: flex; gap: 8px; align-items: center;">
            <span class="scada-topbar-chip"><span class="led-dot led-green"></span>PLC NODE: ONLINE</span>
            {status_badge}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Realtime Fragment: Cập nhật mượt mà tại chỗ
    @st.fragment(run_every=int(refresh_sec) if auto_refresh else None)
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
                <div style="font-size: 1.5rem; font-weight: 800; color: #EF4444; line-height: 1; padding: 4px 10px; background: rgba(239,68,68,0.2); border-radius: 8px; border: 1px solid rgba(239,68,68,0.4);">!</div>
                <div style="flex: 1;">
                    <div class="alert-title">PHÁT HIỆN DẤU HIỆU BẤT THƯỜNG TRÊN DÂY CHUYỀN</div>
                    <div class="alert-desc">{anomaly} &bull; Cần kiểm tra khay cấp liệu và camera cảm biến ngay lập tức.</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # --- 5 SCADA KPI CARDS ---
        c1, c2, c3, c4, c5 = st.columns(5)

        with c1:
            st.markdown(f"""
            <div class="scada-kpi-card kpi-total">
                <div class="scada-kpi-title">Tổng Sản Phẩm</div>
                <div class="scada-kpi-val">{total:,}</div>
                <div class="scada-kpi-sub"><span style="color: #38BDF8;">&bull;</span> Toàn ca sản xuất</div>
            </div>
            """, unsafe_allow_html=True)

        with c2:
            pct_red = (counts.get('RED', 0) / total * 100) if total > 0 else 0
            st.markdown(f"""
            <div class="scada-kpi-card kpi-red">
                <div class="scada-kpi-title" style="color: #FB7185;"><span class="led-dot led-red"></span>Khay Đỏ (45°)</div>
                <div class="scada-kpi-val" style="color: #FB7185;">{counts.get('RED', 0):,}</div>
                <div class="scada-kpi-sub">Tỷ lệ: <strong style="color: #FB7185; margin-left: 2px;">{pct_red:.1f}%</strong></div>
            </div>
            """, unsafe_allow_html=True)

        with c3:
            pct_yel = (counts.get('YELLOW', 0) / total * 100) if total > 0 else 0
            st.markdown(f"""
            <div class="scada-kpi-card kpi-yellow">
                <div class="scada-kpi-title" style="color: #FBBF24;"><span class="led-dot led-yellow"></span>Khay Vàng (90°)</div>
                <div class="scada-kpi-val" style="color: #FBBF24;">{counts.get('YELLOW', 0):,}</div>
                <div class="scada-kpi-sub">Tỷ lệ: <strong style="color: #FBBF24; margin-left: 2px;">{pct_yel:.1f}%</strong></div>
            </div>
            """, unsafe_allow_html=True)

        with c4:
            pct_grn = (counts.get('GREEN', 0) / total * 100) if total > 0 else 0
            st.markdown(f"""
            <div class="scada-kpi-card kpi-green">
                <div class="scada-kpi-title" style="color: #34D399;"><span class="led-dot led-green"></span>Khay Xanh (135°)</div>
                <div class="scada-kpi-val" style="color: #34D399;">{counts.get('GREEN', 0):,}</div>
                <div class="scada-kpi-sub">Tỷ lệ: <strong style="color: #34D399; margin-left: 2px;">{pct_grn:.1f}%</strong></div>
            </div>
            """, unsafe_allow_html=True)

        with c5:
            st.markdown(f"""
            <div class="scada-kpi-card kpi-speed">
                <div class="scada-kpi-title" style="color: #C084FC;"><span class="led-dot led-blue"></span>Vận Tốc Thực</div>
                <div class="scada-kpi-val" style="color: #C084FC;">{speed:.1f}</div>
                <div class="scada-kpi-sub">Đơn vị: <span style="color: #CBD5E1; margin-left: 2px;">SP / Phút</span></div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

        # --- RECENT SORTING LOGS ---
        st.markdown("<div class='section-header'>NHẬT KÝ GẠT SẢN PHẨM VỪA ĐI QUA</div>", unsafe_allow_html=True)

        if logs:
            df = pd.DataFrame(logs)
            df['time_str'] = pd.to_datetime(df['created_at']).dt.strftime('%H:%M:%S  (%d/%m/%Y)')
            df['confidence_pct'] = (df['confidence'] * 100).round(1).astype(str) + '%'
            
            def format_color_badge(val):
                if val == "RED":
                    return "ĐỎ (RED)"
                elif val == "YELLOW":
                    return "VÀNG (YELLOW)"
                elif val == "GREEN":
                    return "XANH (GREEN)"
                return val

            df['color_display'] = df['color_label'].apply(format_color_badge)
            df_display = df[['id', 'color_display', 'confidence_pct', 'time_str']]
            df_display.columns = ['ID', 'Màu Phân Loại', 'Độ Tin Cậy AI', 'Thời Gian Gạt']

            st.dataframe(df_display, use_container_width=True, height=420)
        else:
            st.info("Chưa có bản ghi phân loại nào được gửi lên từ hệ thống.")

    render_worker_realtime_data()


