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
    create_user_account, export_logs_csv_data,
    fetch_servo_health
)

def render_manager_view():
    """Giao diện Quản trị viên cấp cao (Executive Dashboard) chuẩn Industrial Minimalism"""
    user = st.session_state.get("user", {})

    # --- SIDEBAR ---
    st.sidebar.markdown(f"### {user.get('full_name', 'Quản Lý')}")
    st.sidebar.markdown('<span class="role-badge-manager">QUẢN TRỊ VIÊN HỆ THỐNG</span>', unsafe_allow_html=True)
    st.sidebar.markdown(f"**Tài khoản:** `{user.get('username', 'admin')}`")

    st.sidebar.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    if st.sidebar.button("Đăng Xuất", use_container_width=True):
        logout_user()

    st.sidebar.markdown("---")
    st.sidebar.markdown("<div class='section-header' style='margin-top: 0;'>TỰ ĐỘNG LÀM MỚI</div>", unsafe_allow_html=True)
    auto_refresh = st.sidebar.checkbox("Bật làm mới tự động", value=True)
    refresh_sec = st.sidebar.slider("Chu kỳ làm mới (giây)", min_value=2, max_value=30, value=4)

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
    st.markdown('<div class="app-title-gradient">BẢNG ĐIỀU KHIỂN QUẢN LÝ SẢN XUẤT</div>', unsafe_allow_html=True)
    status_badge = f"<span class='live-badge'><span class='live-dot'></span> LIVE SCADA FEED ({refresh_sec}s)</span>" if auto_refresh else "<span style='color: #64748B; font-size: 0.85rem;'>Tạm dừng tự động làm mới</span>"
    st.markdown(f'<div class="app-subtitle">Trung tâm phân tích hiệu suất dây chuyền, xuất báo cáo & cấu hình thiết bị IoT &nbsp;&bull;&nbsp; {status_badge}</div>', unsafe_allow_html=True)

    # --- 4 TABS (NO EMOJI) ---
    tab_realtime, tab_analytics, tab_config, tab_users = st.tabs([
        "Giám Sát Trực Tiếp",
        "Báo Cáo Năng Suất",
        "Cấu Hình & Xuất Dữ Liệu",
        "Quản Trị Người Dùng"
    ])

    # ==========================================
    # TAB 1: GIÁM SÁT TRỰC TIẾP (STREAMLIT FRAGMENT)
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
                    <div style="font-size: 1.8rem; font-weight: 800; color: #F87171;">!</div>
                    <div>
                        <div class="alert-title">CẢNH BÁO BẤT THƯỜNG TRÊN DÂY CHUYỀN SẢN XUẤT</div>
                        <div class="alert-desc">{anomaly} — Cần kiểm tra khay cấp liệu và cảm biến phân loại ngay lập tức.</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            # 5 KPI Cards
            c1, c2, c3, c4, c5 = st.columns(5)
            with c1:
                st.markdown(f"""
                <div class="kpi-card kpi-total">
                    <div class="kpi-title">Tổng Sản Phẩm</div>
                    <div class="kpi-value">{total:,}</div>
                    <div class="kpi-sub">Tích lũy toàn bộ</div>
                </div>
                """, unsafe_allow_html=True)

            with c2:
                pct_red = (counts.get('RED', 0) / total * 100) if total > 0 else 0
                st.markdown(f"""
                <div class="kpi-card kpi-red">
                    <div class="kpi-title" style="color: #FB7185;"><span class="led-dot led-red"></span>Khay Đỏ</div>
                    <div class="kpi-value" style="color: #FB7185;">{counts.get('RED', 0):,}</div>
                    <div class="kpi-sub">Tỷ lệ: {pct_red:.1f}%</div>
                </div>
                """, unsafe_allow_html=True)

            with c3:
                pct_yel = (counts.get('YELLOW', 0) / total * 100) if total > 0 else 0
                st.markdown(f"""
                <div class="kpi-card kpi-yellow">
                    <div class="kpi-title" style="color: #FBBF24;"><span class="led-dot led-yellow"></span>Khay Vàng</div>
                    <div class="kpi-value" style="color: #FBBF24;">{counts.get('YELLOW', 0):,}</div>
                    <div class="kpi-sub">Tỷ lệ: {pct_yel:.1f}%</div>
                </div>
                """, unsafe_allow_html=True)

            with c4:
                pct_grn = (counts.get('GREEN', 0) / total * 100) if total > 0 else 0
                st.markdown(f"""
                <div class="kpi-card kpi-green">
                    <div class="kpi-title" style="color: #34D399;"><span class="led-dot led-green"></span>Khay Xanh</div>
                    <div class="kpi-value" style="color: #34D399;">{counts.get('GREEN', 0):,}</div>
                    <div class="kpi-sub">Tỷ lệ: {pct_grn:.1f}%</div>
                </div>
                """, unsafe_allow_html=True)

            with c5:
                st.markdown(f"""
                <div class="kpi-card kpi-speed">
                    <div class="kpi-title" style="color: #C084FC;"><span class="led-dot led-blue"></span>Năng Suất</div>
                    <div class="kpi-value" style="color: #C084FC;">{speed:.1f}</div>
                    <div class="kpi-sub">Sản phẩm / phút</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

            # 2 Biểu đồ thống kê Realtime
            col_pie, col_bar = st.columns(2)

            with col_pie:
                st.markdown("<div class='section-header'>TỶ LỆ PHÂN LOẠI MÀU SẮC (%)</div>", unsafe_allow_html=True)
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
                st.markdown("<div class='section-header'>PHÂN BỐ SẢN LƯỢNG THEO KHAY</div>", unsafe_allow_html=True)
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
            st.markdown("<div class='section-header'>NHẬT KÝ PHÂN LOẠI THỜI GIAN THỰC (50 BẢN GHI GẦN NHẤT)</div>", unsafe_allow_html=True)
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
    # TAB 2: BÁO CÁO NĂNG SUẤT & SỨC KHỎE THIẾT BỊ
    # ==========================================
    with tab_analytics:
        # Khởi tạo state bộ lọc nếu chưa có
        if "analytics_filter_applied" not in st.session_state:
            st.session_state.analytics_filter_applied = {
                "time_preset": "Toàn bộ lịch sử",
                "shift": "Tất cả các ca",
                "color": "Tất cả màu",
                "start_time": None,
                "end_time": None,
                "shift_param": None,
                "color_param": None,
                "summary_label": "Toàn bộ lịch sử"
            }

        # ----------------------------------------------------
        # 1. BỘ LỌC PHÂN TÍCH DỮ LIỆU (FORM SUBMIT - KHÔNG SPAM REQUEST)
        # ----------------------------------------------------
        st.markdown("<div class='section-header'>BỘ LỌC DỮ LIỆU SẢN XUẤT</div>", unsafe_allow_html=True)
        
        with st.container():
            f_col1, f_col2, f_col3 = st.columns(3)
            
            with f_col1:
                sel_time_preset = st.selectbox(
                    "Khoảng thời gian",
                    ["Toàn bộ lịch sử", "Hôm nay", "Hôm qua", "7 ngày gần nhất", "Tùy chọn khoảng ngày"],
                    index=["Toàn bộ lịch sử", "Hôm nay", "Hôm qua", "7 ngày gần nhất", "Tùy chọn khoảng ngày"].index(
                        st.session_state.analytics_filter_applied.get("time_preset", "Toàn bộ lịch sử")
                    )
                )
            
            with f_col2:
                sel_shift = st.selectbox(
                    "Ca sản xuất",
                    ["Tất cả các ca", "Ca 1 (06:00 - 14:00)", "Ca 2 (14:00 - 22:00)", "Ca 3 (22:00 - 06:00)"],
                    index=["Tất cả các ca", "Ca 1 (06:00 - 14:00)", "Ca 2 (14:00 - 22:00)", "Ca 3 (22:00 - 06:00)"].index(
                        st.session_state.analytics_filter_applied.get("shift", "Tất cả các ca")
                    )
                )

            with f_col3:
                sel_color = st.selectbox(
                    "Phân loại màu sắc",
                    ["Tất cả màu", "Đỏ (RED)", "Vàng (YELLOW)", "Xanh lá (GREEN)"],
                    index=["Tất cả màu", "Đỏ (RED)", "Vàng (YELLOW)", "Xanh lá (GREEN)"].index(
                        st.session_state.analytics_filter_applied.get("color", "Tất cả màu")
                    )
                )

            custom_start_time = None
            custom_end_time = None
            now_vn = pd.Timestamp.now(tz='Asia/Ho_Chi_Minh').tz_localize(None)

            if sel_time_preset == "Tùy chọn khoảng ngày":
                cd1, cd2 = st.columns(2)
                with cd1:
                    d_start = st.date_input("Từ ngày", value=now_vn.date() - pd.Timedelta(days=1))
                    custom_start_time = f"{d_start} 00:00:00"
                with cd2:
                    d_end = st.date_input("Đến ngày", value=now_vn.date())
                    custom_end_time = f"{d_end} 23:59:59"

            # 2 Nút bấm hành động
            btn_col1, btn_col2, _ = st.columns([1.2, 1, 3])
            
            with btn_col1:
                apply_clicked = st.button("Áp Dụng Bộ Lọc", type="primary", use_container_width=True)
            with btn_col2:
                reset_clicked = st.button("Đặt Lại Mặc Định", use_container_width=True)

            if apply_clicked:
                start_p = None
                end_p = None
                if sel_time_preset == "Hôm nay":
                    start_p = now_vn.strftime('%Y-%m-%d 00:00:00')
                    end_p = now_vn.strftime('%Y-%m-%d 23:59:59')
                elif sel_time_preset == "Hôm qua":
                    yesterday = now_vn - pd.Timedelta(days=1)
                    start_p = yesterday.strftime('%Y-%m-%d 00:00:00')
                    end_p = yesterday.strftime('%Y-%m-%d 23:59:59')
                elif sel_time_preset == "7 ngày gần nhất":
                    seven_days = now_vn - pd.Timedelta(days=7)
                    start_p = seven_days.strftime('%Y-%m-%d 00:00:00')
                    end_p = now_vn.strftime('%Y-%m-%d 23:59:59')
                elif sel_time_preset == "Tùy chọn khoảng ngày":
                    start_p = custom_start_time
                    end_p = custom_end_time

                shift_p = None
                if "Ca 1" in sel_shift: shift_p = "SHIFT_1"
                elif "Ca 2" in sel_shift: shift_p = "SHIFT_2"
                elif "Ca 3" in sel_shift: shift_p = "SHIFT_3"

                color_p = None
                if "RED" in sel_color: color_p = "RED"
                elif "YELLOW" in sel_color: color_p = "YELLOW"
                elif "GREEN" in sel_color: color_p = "GREEN"

                st.session_state.analytics_filter_applied = {
                    "time_preset": sel_time_preset,
                    "shift": sel_shift,
                    "color": sel_color,
                    "start_time": start_p,
                    "end_time": end_p,
                    "shift_param": shift_p,
                    "color_param": color_p,
                    "summary_label": f"{sel_time_preset} &bull; {sel_shift} &bull; {sel_color}"
                }
                st.rerun()

            if reset_clicked:
                st.session_state.analytics_filter_applied = {
                    "time_preset": "Toàn bộ lịch sử",
                    "shift": "Tất cả các ca",
                    "color": "Tất cả màu",
                    "start_time": None,
                    "end_time": None,
                    "shift_param": None,
                    "color_param": None,
                    "summary_label": "Toàn bộ lịch sử"
                }
                st.rerun()

        # Hiển thị Chip trạng thái bộ lọc đang kích hoạt
        active_f = st.session_state.analytics_filter_applied
        st.markdown(f"""
        <div class="filter-active-status">
            <span class="led-dot led-blue"></span>Phạm vi dữ liệu đang lọc: 
            <span class="filter-active-val">{active_f.get('summary_label', 'Toàn bộ lịch sử')}</span>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

        # ----------------------------------------------------
        # 2. KHUNG HIỂN THỊ DỮ LIỆU PHÂN TÍCH (FRAGMENT)
        # ----------------------------------------------------
        @st.fragment(run_every=f"{refresh_sec*2}s" if auto_refresh else None)
        def render_analytics_display_content():
            current_filter = st.session_state.analytics_filter_applied
            
            logs_analytics = fetch_logs(
                limit=500,
                color_label=current_filter.get("color_param"),
                start_time=current_filter.get("start_time"),
                end_time=current_filter.get("end_time"),
                shift=current_filter.get("shift_param")
            )

            if logs_analytics and len(logs_analytics) > 0:
                df_time = pd.DataFrame(logs_analytics)
                df_time['dt'] = pd.to_datetime(df_time['created_at'])
                df_time['dt_minute'] = df_time['dt'].dt.floor('min')

                is_multi_day = (df_time['dt'].dt.date.nunique() > 1)
                time_fmt = '%H:%M\n%d/%m' if is_multi_day else '%H:%M'

                # Gom nhóm đếm số lượng theo phút và màu sắc
                grouped = df_time.groupby(['dt_minute', 'color_label']).size().reset_index(name='count')
                grouped = grouped.sort_values(by='dt_minute', ascending=True)
                grouped['time_display'] = grouped['dt_minute'].dt.strftime(time_fmt)

                # Tabs con cho 2 dạng biểu đồ
                sub_t1, sub_t2 = st.tabs(["Diễn Biến Năng Suất (Timeline Trend)", "Sản Lượng Tích Lũy (Cumulative S-Curve)"])

                with sub_t1:
                    fig_line = px.line(
                        grouped, 
                        x="time_display", 
                        y="count", 
                        color="color_label",
                        markers=True,
                        line_shape="linear",
                        color_discrete_map=plotly_color_map,
                        labels={
                            "time_display": "Thời gian (Giờ:Phút)", 
                            "count": "Số lượng sản phẩm", 
                            "color_label": "Màu"
                        }
                    )
                    fig_line.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="#94A3B8", family="Outfit"),
                        xaxis=dict(
                            showgrid=True, 
                            gridcolor="rgba(255,255,255,0.06)",
                            type='category',
                            categoryorder='array',
                            categoryarray=grouped['time_display'].unique().tolist()
                        ),
                        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)", rangemode="tozero"),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                        margin=dict(l=10, r=10, t=30, b=10)
                    )
                    st.plotly_chart(fig_line, use_container_width=True)

                with sub_t2:
                    # Tính toán tổng sản lượng tích lũy (Cumulative Sum)
                    df_pivot = df_time.pivot_table(index='dt_minute', columns='color_label', values='id', aggfunc='count', fill_value=0)
                    df_pivot = df_pivot.sort_index().cumsum()
                    df_pivot['time_display'] = df_pivot.index.strftime(time_fmt)
                    df_cum = df_pivot.melt(id_vars=['time_display'], var_name='color_label', value_name='cumulative_count')

                    fig_area = px.area(
                        df_cum,
                        x="time_display",
                        y="cumulative_count",
                        color="color_label",
                        color_discrete_map=plotly_color_map,
                        labels={"time_display": "Thời gian", "cumulative_count": "Sản lượng tích lũy (SP)", "color_label": "Màu"}
                    )
                    fig_area.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="#94A3B8", family="Outfit"),
                        xaxis=dict(
                            showgrid=True, 
                            gridcolor="rgba(255,255,255,0.06)",
                            type='category',
                            categoryorder='array',
                            categoryarray=df_pivot['time_display'].unique().tolist()
                        ),
                        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                        margin=dict(l=10, r=10, t=30, b=10)
                    )
                    st.plotly_chart(fig_area, use_container_width=True)

                st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

                # ----------------------------------------------------
                # 3. PHÂN BỔ KHUNG GIỜ & THỐNG KÊ HIỆU SUẤT
                # ----------------------------------------------------
                col_hr, col_summary = st.columns([1.4, 1])
                with col_hr:
                    st.markdown("<div class='section-header'>PHÂN BỔ SẢN LƯỢNG THEO KHUNG GIỜ</div>", unsafe_allow_html=True)
                    df_time['hour_str'] = df_time['dt'].dt.strftime('%H:00')
                    df_hour = df_time.groupby(['hour_str', 'color_label']).size().reset_index(name='count')
                    df_hour = df_hour.sort_values(by='hour_str')
                    
                    fig_hour = px.bar(
                        df_hour, x="hour_str", y="count", color="color_label",
                        barmode="group",
                        color_discrete_map=plotly_color_map,
                        labels={"hour_str": "Khung giờ", "count": "Sản lượng", "color_label": "Màu"}
                    )
                    fig_hour.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="#94A3B8", family="Outfit"),
                        xaxis=dict(showgrid=False),
                        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
                        margin=dict(l=10, r=10, t=10, b=10),
                        showlegend=False
                    )
                    st.plotly_chart(fig_hour, use_container_width=True)

                with col_summary:
                    st.markdown("<div class='section-header'>THỐNG KÊ HIỆU SUẤT THEO BỘ LỌC</div>", unsafe_allow_html=True)
                    total_logs = len(df_time)
                    red_c = len(df_time[df_time['color_label'] == 'RED'])
                    yel_c = len(df_time[df_time['color_label'] == 'YELLOW'])
                    grn_c = len(df_time[df_time['color_label'] == 'GREEN'])
                    first_log_time = df_time['dt'].min().strftime('%H:%M:%S - %d/%m/%Y')
                    last_log_time = df_time['dt'].max().strftime('%H:%M:%S - %d/%m/%Y')

                    st.markdown(f"""
                    <div style="background: rgba(30, 41, 59, 0.6); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 16px;">
                        <div style="color: #94A3B8; font-size: 0.82rem; margin-bottom: 4px;">Khoảng thời gian:</div>
                        <div style="color: #F8FAFC; font-weight: 600; font-size: 0.88rem;">{first_log_time}</div>
                        <div style="color: #64748B; font-size: 0.75rem; text-align: center; margin: 2px 0;">đến</div>
                        <div style="color: #38BDF8; font-weight: 600; font-size: 0.88rem; margin-bottom: 10px;">{last_log_time}</div>
                        <hr style="border: 0; border-top: 1px solid rgba(255,255,255,0.08); margin: 8px 0;" />
                        <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                            <span style="color: #94A3B8;">Tổng sản lượng:</span>
                            <strong style="color: #F8FAFC;">{total_logs:,} sp</strong>
                        </div>
                        <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                            <span style="color: #FB7185;"><span class="led-dot led-red"></span>Đỏ (RED):</span>
                            <strong>{red_c} ({red_c/total_logs*100:.1f}%)</strong>
                        </div>
                        <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                            <span style="color: #FBBF24;"><span class="led-dot led-yellow"></span>Vàng (YELLOW):</span>
                            <strong>{yel_c} ({yel_c/total_logs*100:.1f}%)</strong>
                        </div>
                        <div style="display: flex; justify-content: space-between;">
                            <span style="color: #34D399;"><span class="led-dot led-green"></span>Xanh (GREEN):</span>
                            <strong>{grn_c} ({grn_c/total_logs*100:.1f}%)</strong>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Không có dữ liệu thỏa mãn bộ lọc đã chọn.")

            # ----------------------------------------------------
            # 4. GIÁM SÁT VÒNG ĐỜI & SỨC KHỎE CƠ CẤU SERVO SG90
            # ----------------------------------------------------
            st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
            st.markdown("<div class='section-header'>GIÁM SÁT SỨC KHỎE & VÒNG ĐỜI CƠ CẤU SERVO SG90</div>", unsafe_allow_html=True)
            
            servo_data = fetch_servo_health(max_rated_cycles=10000)
            if servo_data:
                total_cyc = servo_data.get("total_cycles", 0)
                max_cyc = servo_data.get("max_rated_cycles", 10000)
                overall_wear = servo_data.get("overall_wear_pct", 0.0)
                details = servo_data.get("servo_details", {})
                imbalance = servo_data.get("imbalance_warning")

                if imbalance:
                    st.warning(f"Cảnh báo phân bổ tải trọng: {imbalance}")

                sv_col1, sv_col2, sv_col3 = st.columns(3)
                
                # Card Góc 45 độ (Đỏ)
                red_sv = details.get("RED", {})
                with sv_col1:
                    st.markdown(f"""
                    <div style="background: rgba(30, 41, 59, 0.5); border: 1px solid rgba(251, 113, 133, 0.2); border-radius: 12px; padding: 14px;">
                        <div style="color: #FB7185; font-weight: 600; font-size: 0.9rem; margin-bottom: 6px;"><span class="led-dot led-red"></span>Khay Đỏ — Góc 45°</div>
                        <div style="font-size: 1.4rem; font-weight: 700; color: #F8FAFC;">{red_sv.get('cycles', 0):,} <span style="font-size: 0.75rem; color: #94A3B8;">chu kỳ</span></div>
                        <div style="color: #94A3B8; font-size: 0.78rem; margin: 4px 0 8px 0;">Mức hao mòn: <strong>{red_sv.get('wear_pct', 0.0):.1f}%</strong></div>
                    </div>
                    """, unsafe_allow_html=True)
                    st.progress(min(1.0, red_sv.get('wear_pct', 0.0) / 100.0))

                # Card Góc 90 độ (Vàng)
                yel_sv = details.get("YELLOW", {})
                with sv_col2:
                    st.markdown(f"""
                    <div style="background: rgba(30, 41, 59, 0.5); border: 1px solid rgba(251, 191, 36, 0.2); border-radius: 12px; padding: 14px;">
                        <div style="color: #FBBF24; font-weight: 600; font-size: 0.9rem; margin-bottom: 6px;"><span class="led-dot led-yellow"></span>Khay Vàng — Góc 90°</div>
                        <div style="font-size: 1.4rem; font-weight: 700; color: #F8FAFC;">{yel_sv.get('cycles', 0):,} <span style="font-size: 0.75rem; color: #94A3B8;">chu kỳ</span></div>
                        <div style="color: #94A3B8; font-size: 0.78rem; margin: 4px 0 8px 0;">Mức hao mòn: <strong>{yel_sv.get('wear_pct', 0.0):.1f}%</strong></div>
                    </div>
                    """, unsafe_allow_html=True)
                    st.progress(min(1.0, yel_sv.get('wear_pct', 0.0) / 100.0))

                # Card Góc 135 độ (Xanh)
                grn_sv = details.get("GREEN", {})
                with sv_col3:
                    st.markdown(f"""
                    <div style="background: rgba(30, 41, 59, 0.5); border: 1px solid rgba(52, 211, 153, 0.2); border-radius: 12px; padding: 14px;">
                        <div style="color: #34D399; font-weight: 600; font-size: 0.9rem; margin-bottom: 6px;"><span class="led-dot led-green"></span>Khay Xanh — Góc 135°</div>
                        <div style="font-size: 1.4rem; font-weight: 700; color: #F8FAFC;">{grn_sv.get('cycles', 0):,} <span style="font-size: 0.75rem; color: #94A3B8;">chu kỳ</span></div>
                        <div style="color: #94A3B8; font-size: 0.78rem; margin: 4px 0 8px 0;">Mức hao mòn: <strong>{grn_sv.get('wear_pct', 0.0):.1f}%</strong></div>
                    </div>
                    """, unsafe_allow_html=True)
                    st.progress(min(1.0, grn_sv.get('wear_pct', 0.0) / 100.0))

        render_analytics_display_content()

    # ==========================================
    # TAB 3: CẤU HÌNH & XUẤT BÁO CÁO CSV (STABLE NO-REFRESH)
    # ==========================================
    with tab_config:
        col_export, col_cfg = st.columns([1, 1.2])

        with col_export:
            st.markdown("<div class='section-header'>XUẤT DỮ LIỆU SẢN XUẤT (CSV)</div>", unsafe_allow_html=True)
            st.write("Tải toàn bộ nhật ký phân loại phục vụ lưu trữ hoặc tích hợp hệ thống ERP:")
            
            csv_data = export_logs_csv_data()
            if csv_data:
                st.download_button(
                    label="Tải Báo Cáo CSV Toàn Bộ Dữ Liệu",
                    data=csv_data,
                    file_name="iot_factory_sorting_report.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            else:
                st.warning("Chưa có dữ liệu hoặc không thể tải file CSV.")

        with col_cfg:
            st.markdown("<div class='section-header'>CẤU HÌNH THAM SỐ VẬN HÀNH</div>", unsafe_allow_html=True)
            configs = fetch_configs()

            with st.form("sys_config_form"):
                threshold = st.number_input(
                    "Ngưỡng Cảnh Báo Bất Thường (Số sản phẩm cùng màu liên tiếp)", 
                    min_value=3, max_value=50, 
                    value=int(configs.get("anomaly_threshold", 10))
                )
                angle_red = st.number_input("Góc xoay Servo - Khay Đỏ (°)", min_value=0, max_value=180, value=int(configs.get("servo_red_angle", 45)))
                angle_yellow = st.number_input("Góc xoay Servo - Khay Vàng (°)", min_value=0, max_value=180, value=int(configs.get("servo_yellow_angle", 90)))
                angle_green = st.number_input("Góc xoay Servo - Khay Xanh (°)", min_value=0, max_value=180, value=int(configs.get("servo_green_angle", 135)))

                save_btn = st.form_submit_button("Lưu Cấu Hình Vận Hành", use_container_width=True)
                if save_btn:
                    update_config_value("anomaly_threshold", threshold)
                    update_config_value("servo_red_angle", angle_red)
                    update_config_value("servo_yellow_angle", angle_yellow)
                    update_config_value("servo_green_angle", angle_green)
                    st.success("Đã cập nhật cấu hình hệ thống thành công!")

    # ==========================================
    # TAB 4: QUẢN TRỊ NGƯỜI DÙNG & NHÂN SỰ (STABLE NO-REFRESH)
    # ==========================================
    with tab_users:
        st.markdown("<div class='section-header'>DANH SÁCH TÀI KHOẢN NHÂN VIÊN</div>", unsafe_allow_html=True)
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
        st.markdown("<div class='section-header'>TẠO TÀI KHOẢN MỚI</div>", unsafe_allow_html=True)
        
        with st.form("create_new_user_form"):
            cu_user = st.text_input("Tên đăng nhập mới (username)")
            cu_pass = st.text_input("Mật khẩu (tối thiểu 6 ký tự)", type="password")
            cu_name = st.text_input("Họ và tên nhân viên")
            cu_role = st.selectbox("Vai trò (Role)", ["WORKER", "MANAGER"])

            create_btn = st.form_submit_button("Đăng Ký Tài Khoản", use_container_width=True)
            if create_btn:
                if not cu_user or not cu_pass:
                    st.error("Vui lòng điền đủ Username và Password!")
                else:
                    ok, msg = create_user_account(cu_user, cu_pass, cu_name, cu_role)
                    if ok:
                        st.success(f"Tạo tài khoản `{cu_user}` thành công!")
                        st.rerun()
                    else:
                        st.error(f"Lỗi: {msg}")
