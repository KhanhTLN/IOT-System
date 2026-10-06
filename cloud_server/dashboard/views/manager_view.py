import time
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from config import COLOR_PALETTE
from services.auth_service import logout_user
from services.api_client import (
    fetch_stats, fetch_logs, fetch_configs, 
    update_config_value, fetch_all_users, 
    create_user_account, export_logs_csv_data
)

def render_manager_view():
    """Giao diện Quản trị viên cấp cao (Executive Dashboard) với 4 Tabs chi tiết"""
    user = st.session_state.get("user", {})

    # --- SIDEBAR ---
    st.sidebar.markdown(f"### 👤 {user.get('full_name', 'Quản Lý')}")
    st.sidebar.markdown('<span class="role-badge-manager">👔 QUẢN LÝ NHÀ MÁY</span>', unsafe_allow_html=True)
    st.sidebar.markdown(f"**Tài khoản:** `{user.get('username', 'admin')}`")

    st.sidebar.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    if st.sidebar.button("🚪 Đăng Xuất", use_container_width=True):
        logout_user()

    st.sidebar.markdown("---")
    st.sidebar.markdown("##### ⚙️ Tự động làm mới")
    auto_refresh = st.sidebar.checkbox("Bật làm mới tự động", value=True)
    refresh_sec = st.sidebar.slider("Chu kỳ (giây)", min_value=2, max_value=30, value=4)

    # Màu sắc cho biểu đồ Plotly
    plotly_color_map = {
        "Đỏ (RED)": COLOR_PALETTE["RED"]["hex"],
        "Vàng (YELLOW)": COLOR_PALETTE["YELLOW"]["hex"],
        "Xanh (GREEN)": COLOR_PALETTE["GREEN"]["hex"],
        "RED": COLOR_PALETTE["RED"]["hex"],
        "YELLOW": COLOR_PALETTE["YELLOW"]["hex"],
        "GREEN": COLOR_PALETTE["GREEN"]["hex"],
    }

    # --- HEADER ---
    st.markdown('<div class="app-title-gradient">📊 Bảng Điều Khiển Quản Lý Sản Xuất</div>', unsafe_allow_html=True)
    status_badge = f"<span class='live-badge'><span class='live-dot'></span> LIVE SCADA FEED ({refresh_sec}s)</span>" if auto_refresh else "<span style='color: #64748B; font-size: 0.85rem;'>⏸️ Tạm dừng tự động làm mới</span>"
    st.markdown(f'<div class="app-subtitle">Trung tâm phân tích hiệu suất dây chuyền, xuất báo cáo & cấu hình thiết bị IoT &nbsp;&bull;&nbsp; {status_badge}</div>', unsafe_allow_html=True)

    # --- 4 TABS ---
    tab_realtime, tab_analytics, tab_config, tab_users = st.tabs([
        "📡 Giám Sát Realtime",
        "📈 Báo Cáo Năng Suất",
        "⚙️ Cấu Hình & Export CSV",
        "👥 Quản Lý Người Dùng"
    ])

    # ==========================================
    # TAB 1: GIÁM SÁT REALTIME (STREAMLIT FRAGMENT)
    # ==========================================
    with tab_realtime:
        @st.fragment(run_every=f"{refresh_sec}s" if auto_refresh else None)
        def render_realtime_tab_content():
            stats = fetch_stats()
            logs = fetch_logs(limit=50)
            counts = stats.get("counts", {"RED": 0, "YELLOW": 0, "GREEN": 0})
            total = stats.get("total_count", 0)
            speed = stats.get("productivity_per_minute", 0.0)
            anomaly = stats.get("anomaly_alert", "")

            if anomaly:
                st.markdown(f"""
                <div class="pulse-alert-box">
                    <div style="font-size: 2.2rem;">🚨</div>
                    <div>
                        <div class="alert-title">CẢNH BÁO BẤT THƯỜNG TRÊN DÂY CHUYỀN SẢN XUẤT!</div>
                        <div class="alert-desc">{anomaly} — Cần kiểm tra khay cấp liệu và cảm biến phân loại ngay!</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            # 5 KPI Cards
            c1, c2, c3, c4, c5 = st.columns(5)
            with c1:
                st.markdown(f"""
                <div class="kpi-card kpi-total">
                    <div class="kpi-title">📦 Tổng Sản Phẩm</div>
                    <div class="kpi-value">{total:,}</div>
                    <div class="kpi-sub">Tổng tích lũy</div>
                </div>
                """, unsafe_allow_html=True)

            with c2:
                pct_red = (counts.get('RED', 0) / total * 100) if total > 0 else 0
                st.markdown(f"""
                <div class="kpi-card kpi-red">
                    <div class="kpi-title" style="color: #FB7185;">🔴 Thùng Đỏ</div>
                    <div class="kpi-value" style="color: #FB7185;">{counts.get('RED', 0):,}</div>
                    <div class="kpi-sub">Tỷ lệ: {pct_red:.1f}%</div>
                </div>
                """, unsafe_allow_html=True)

            with c3:
                pct_yel = (counts.get('YELLOW', 0) / total * 100) if total > 0 else 0
                st.markdown(f"""
                <div class="kpi-card kpi-yellow">
                    <div class="kpi-title" style="color: #FBBF24;">🟡 Thùng Vàng</div>
                    <div class="kpi-value" style="color: #FBBF24;">{counts.get('YELLOW', 0):,}</div>
                    <div class="kpi-sub">Tỷ lệ: {pct_yel:.1f}%</div>
                </div>
                """, unsafe_allow_html=True)

            with c4:
                pct_grn = (counts.get('GREEN', 0) / total * 100) if total > 0 else 0
                st.markdown(f"""
                <div class="kpi-card kpi-green">
                    <div class="kpi-title" style="color: #34D399;">🟢 Thùng Xanh</div>
                    <div class="kpi-value" style="color: #34D399;">{counts.get('GREEN', 0):,}</div>
                    <div class="kpi-sub">Tỷ lệ: {pct_grn:.1f}%</div>
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

            st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

            # 2 Biểu đồ thống kê Realtime
            col_pie, col_bar = st.columns(2)

            with col_pie:
                st.markdown("##### 🍩 Tỷ lệ phân loại màu sắc (%)")
                if total > 0:
                    df_pie = pd.DataFrame([
                        {"Màu": "Đỏ (RED)", "Số lượng": counts.get("RED", 0)},
                        {"Màu": "Vàng (YELLOW)", "Số lượng": counts.get("YELLOW", 0)},
                        {"Màu": "Xanh (GREEN)", "Số lượng": counts.get("GREEN", 0)}
                    ])
                    fig_pie = px.pie(
                        df_pie, names="Màu", values="Số lượng",
                        color="Màu",
                        color_discrete_map=plotly_color_map,
                        hole=0.55
                    )
                    fig_pie.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="#94A3B8", family="Outfit"),
                        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
                        margin=dict(l=10, r=10, t=10, b=10)
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)
                else:
                    st.info("Chưa có dữ liệu phân loại.")

            with col_bar:
                st.markdown("##### 📊 Phân bố số lượng sản phẩm theo thùng")
                df_bar = pd.DataFrame([
                    {"Màu": "Đỏ (RED)", "Số lượng": counts.get("RED", 0)},
                    {"Màu": "Vàng (YELLOW)", "Số lượng": counts.get("YELLOW", 0)},
                    {"Màu": "Xanh (GREEN)", "Số lượng": counts.get("GREEN", 0)}
                ])
                fig_bar = px.bar(
                    df_bar, x="Màu", y="Số lượng", color="Màu",
                    color_discrete_map=plotly_color_map,
                    text="Số lượng"
                )
                fig_bar.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#94A3B8", family="Outfit"),
                    xaxis=dict(showgrid=False),
                    yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
                    showlegend=False,
                    margin=dict(l=10, r=10, t=10, b=10)
                )
                st.plotly_chart(fig_bar, use_container_width=True)

            st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
            st.markdown("##### 📋 Nhật ký phân loại thời gian thực (50 bản ghi gần nhất)")
            if logs:
                df_logs = pd.DataFrame(logs)
                df_logs['time_str'] = pd.to_datetime(df_logs['created_at']).dt.strftime('%H:%M:%S - %d/%m/%Y')
                df_logs['confidence_pct'] = (df_logs['confidence'] * 100).round(1).astype(str) + '%'
                df_logs_view = df_logs[['id', 'color_label', 'confidence_pct', 'time_str']]
                df_logs_view.columns = ['ID', 'Nhãn Màu', 'Độ Tin Cậy', 'Thời Gian Gạt']
                st.dataframe(df_logs_view, use_container_width=True, height=350)
            else:
                st.info("Chưa có lịch sử gạt sản phẩm.")

        render_realtime_tab_content()

    # ==========================================
    # TAB 2: BÁO CÁO NĂNG SUẤT & DIỄN BIẾN
    # ==========================================
    with tab_analytics:
        @st.fragment(run_every=f"{refresh_sec*2}s" if auto_refresh else None)
        def render_analytics_tab_content():
            st.markdown("##### 📈 Diễn biến phân loại sản phẩm theo thời gian (Timeline Trend)")
            logs_analytics = fetch_logs(limit=100)
            if logs_analytics:
                df_time = pd.DataFrame(logs_analytics)
                df_time['dt'] = pd.to_datetime(df_time['created_at'])
                df_time['minute'] = df_time['dt'].dt.strftime('%H:%M')

                grouped = df_time.groupby(['minute', 'color_label']).size().reset_index(name='count')
                
                fig_line = px.line(
                    grouped, x="minute", y="count", color="color_label",
                    markers=True,
                    color_discrete_map=plotly_color_map,
                    labels={"minute": "Thời gian (Giờ:Phút)", "count": "Số lượng sản phẩm", "color_label": "Màu"}
                )
                fig_line.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#94A3B8", family="Outfit"),
                    xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
                    yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
                    margin=dict(l=10, r=10, t=10, b=10)
                )
                st.plotly_chart(fig_line, use_container_width=True)
            else:
                st.info("Cần thêm dữ liệu sản phẩm để phân tích biểu đồ diễn biến.")

        render_analytics_tab_content()

    # ==========================================
    # TAB 3: CẤU HÌNH & XUẤT BÁO CÁO CSV (STABLE NO-REFRESH)
    # ==========================================
    with tab_config:
        col_export, col_cfg = st.columns([1, 1.2])

        with col_export:
            st.markdown("##### 📥 Xuất File Báo Cáo Sản Xuất (CSV)")
            st.write("Tải toàn bộ dữ liệu nhật ký phân loại phục vụ lưu trữ, báo cáo ca hoặc tích hợp ERP:")
            
            csv_data = export_logs_csv_data()
            if csv_data:
                st.download_button(
                    label="📥 Tải Báo Cáo CSV Toàn Bộ Dữ Liệu",
                    data=csv_data,
                    file_name="iot_factory_sorting_report.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            else:
                st.warning("Chưa có dữ liệu hoặc không thể tải file CSV.")

        with col_cfg:
            st.markdown("##### ⚙️ Cấu Hình Tham Số Vận Hành Hệ Thống")
            configs = fetch_configs()

            with st.form("sys_config_form"):
                threshold = st.number_input(
                    "Ngưỡng Cảnh Báo Bất Thường (Số sản phẩm cùng màu liên tiếp)", 
                    min_value=3, max_value=50, 
                    value=int(configs.get("anomaly_threshold", 10))
                )
                angle_red = st.number_input("Góc xoay Servo - Màu Đỏ (°)", min_value=0, max_value=180, value=int(configs.get("servo_red_angle", 45)))
                angle_yellow = st.number_input("Góc xoay Servo - Màu Vàng (°)", min_value=0, max_value=180, value=int(configs.get("servo_yellow_angle", 90)))
                angle_green = st.number_input("Góc xoay Servo - Màu Xanh (°)", min_value=0, max_value=180, value=int(configs.get("servo_green_angle", 135)))

                save_btn = st.form_submit_button("💾 Lưu Cấu Hình Vận Hành", use_container_width=True)
                if save_btn:
                    update_config_value("anomaly_threshold", threshold)
                    update_config_value("servo_red_angle", angle_red)
                    update_config_value("servo_yellow_angle", angle_yellow)
                    update_config_value("servo_green_angle", angle_green)
                    st.success("✅ Đã cập nhật cấu hình hệ thống thành công!")

    # ==========================================
    # TAB 4: QUẢN LÝ NGƯỜI DÙNG & NHÂN SỰ (STABLE NO-REFRESH)
    # ==========================================
    with tab_users:
        st.markdown("##### 👥 Danh Sách Tài Khoản Nhân Viên Nhà Máy")
        user_list = fetch_all_users()
        if user_list:
            df_u = pd.DataFrame(user_list)
            df_u['created_str'] = pd.to_datetime(df_u['created_at']).dt.strftime('%H:%M:%S  %d/%m/%Y')
            df_u_view = df_u[['id', 'username', 'full_name', 'role', 'is_active', 'created_str']]
            df_u_view.columns = ['ID', 'Tên Đăng Nhập', 'Họ Và Tên', 'Vai Trò (Role)', 'Đang Hoạt Động', 'Ngày Tạo']
            st.dataframe(df_u_view, use_container_width=True)
        else:
            st.info("Chưa có danh sách người dùng.")

        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
        st.markdown("##### ➕ Tạo Tài Khoản Nhân Viên Mới")
        
        with st.form("create_new_user_form"):
            cu_user = st.text_input("Tên đăng nhập mới (username)")
            cu_pass = st.text_input("Mật khẩu (tối thiểu 6 ký tự)", type="password")
            cu_name = st.text_input("Họ và tên nhân viên")
            cu_role = st.selectbox("Vai trò (Role)", ["WORKER", "MANAGER"])

            create_btn = st.form_submit_button("✨ Đăng Ký Tài Khoản", use_container_width=True)
            if create_btn:
                if not cu_user or not cu_pass:
                    st.error("⚠️ Vui lòng điền đủ Username và Password!")
                else:
                    ok, msg = create_user_account(cu_user, cu_pass, cu_name, cu_role)
                    if ok:
                        st.success(f"Tạo tài khoản `{cu_user}` thành công!")
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")

