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
    fetch_servo_health, fetch_oee_metrics,
    fetch_target_vs_actual, fetch_heatmap_matrix
)

def render_chart_header(title: str, purpose: str, calculation: str, benchmark: str):
    """Hiển thị tiêu đề biểu đồ kèm nút tròn chữ (i) để xem thông tin chi tiết & tiêu chuẩn đánh giá"""
    col_t, col_i = st.columns([0.94, 0.06])
    with col_t:
        st.markdown(f"<div class='section-header' style='margin-bottom: 0;'>{title}</div>", unsafe_allow_html=True)
    with col_i:
        with st.popover("i", help="Bấm xem mục đích, công thức & tiêu chuẩn đạt chuẩn"):
            st.markdown(f"""
            <div style="font-family: 'Outfit', sans-serif; font-size: 0.86rem; line-height: 1.5; color: #E2E8F0;">
                <div style="font-size: 0.95rem; font-weight: 700; color: #38BDF8; margin-bottom: 12px; padding-bottom: 6px; border-bottom: 1px solid rgba(56, 189, 248, 0.25); letter-spacing: 0.02em;">
                    {title}
                </div>
                <div style="margin-bottom: 10px;">
                    <div style="color: #38BDF8; font-weight: 700; margin-bottom: 2px;">• Mục đích phân tích:</div>
                    <div style="color: #CBD5E1; padding-left: 10px;">{purpose}</div>
                </div>
                <div style="margin-bottom: 10px;">
                    <div style="color: #FBBF24; font-weight: 700; margin-bottom: 2px;">• Công thức & Cách tính:</div>
                    <div style="color: #CBD5E1; padding-left: 10px;">{calculation}</div>
                </div>
                <div>
                    <div style="color: #34D399; font-weight: 700; margin-bottom: 2px;">• Tiêu chuẩn đánh giá:</div>
                    <div style="color: #CBD5E1; padding-left: 10px;">{benchmark}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

def render_manager_view():
    """Giao diện dành riêng cho Quản lý / Quản trị viên (Manager / Admin View)"""
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
    status_badge = f"<span class='live-badge'><span class='live-dot'></span> LIVE SCADA ({refresh_sec}s)</span>" if auto_refresh else "<span class='scada-topbar-chip'>PAUSED</span>"
    st.markdown(f"""
    <div style="display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 12px; flex-wrap: wrap; gap: 8px;">
        <div>
            <div class="app-title-gradient">BẢNG ĐIỀU KHIỂN QUẢN LÝ SẢN XUẤT</div>
            <div class="app-subtitle" style="margin-bottom: 0;">Trung tâm phân tích hiệu suất dây chuyền, chỉ số OEE, đối chiếu mục tiêu &amp; báo cáo SCADA</div>
        </div>
        <div style="display: flex; gap: 8px; align-items: center;">
            <span class="scada-topbar-chip"><span class="led-dot led-green"></span>PLC NODE: ONLINE</span>
            {status_badge}
        </div>
    </div>
    """, unsafe_allow_html=True)

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
                    <div style="font-size: 1.5rem; font-weight: 800; color: #EF4444; line-height: 1; padding: 4px 10px; background: rgba(239,68,68,0.2); border-radius: 8px; border: 1px solid rgba(239,68,68,0.4);">!</div>
                    <div style="flex: 1;">
                        <div class="alert-title">CẢNH BÁO BẤT THƯỜNG TRÊN DÂY CHUYỀN SẢN XUẤT</div>
                        <div class="alert-desc">{anomaly} &bull; Cần kiểm tra khay cấp liệu và camera cảm biến phân loại ngay lập tức.</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            # 5 SCADA KPI Cards (Lưới 12 cột đều nhau)
            c1, c2, c3, c4, c5 = st.columns(5)
            
            with c1:
                st.markdown(f"""
                <div class="scada-kpi-card kpi-total">
                    <div class="scada-kpi-title">Tổng Sản Phẩm</div>
                    <div class="scada-kpi-val">{total:,}</div>
                    <div class="scada-kpi-sub"><span style="color: #38BDF8;">&bull;</span> Toàn ca tích lũy</div>
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

            st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

            # 2 Khối trực quan hóa SCADA: Donut Chart mỏng (Trái) & Micro-Bars phân bổ khay (Phải)
            col_pie, col_bar = st.columns([1.1, 1.4])

            with col_pie:
                render_chart_header(
                    "TỶ LỆ PHÂN LOẠI MÀU SẮC (%)",
                    "Theo dõi tỷ trọng phân bổ sản phẩm theo 3 màu Đỏ, Vàng, Xanh để kiểm soát cơ cấu lô hàng.",
                    "Tỷ lệ % = (Số lượng màu X / Tổng sản phẩm) &times; 100%.",
                    "Phân bố đồng đều theo kế hoạch đơn hàng (thường từ 25% - 40% mỗi màu nếu chia đều)."
                )
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
                        hole=0.72
                    )
                    fig_pie.add_annotation(
                        text=f"<b>{total:,}</b><br><span style='font-size: 10px; color: #94A3B8;'>SẢN PHẨM</span>",
                        showarrow=False,
                        font=dict(size=20, color="#F8FAFC", family="JetBrains Mono")
                    )
                    fig_pie.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="#94A3B8", family="Outfit"),
                        legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
                        margin=dict(l=10, r=10, t=10, b=10),
                        height=240
                    )
                    st.plotly_chart(fig_pie, use_container_width=True, config={"displayModeBar": False, "displaylogo": False})
                else:
                    st.info("Chưa có dữ liệu phân loại.")

            with col_bar:
                render_chart_header(
                    "PHÂN BỐ SẢN LƯỢNG THEO KHAY",
                    "So sánh số lượng sản phẩm vật lý thực tế đã được gạt vào 3 khay chứa Đỏ (45°), Vàng (90°), Xanh (135°).",
                    "Đếm tổng số log phân loại thành công từ Camera Edge và vi điều khiển ESP32.",
                    "Các khay chứa không bị đầy tràn hoặc bỏ trống bất thường."
                )
                
                pct_r = (counts.get('RED', 0) / total * 100) if total > 0 else 0
                pct_y = (counts.get('YELLOW', 0) / total * 100) if total > 0 else 0
                pct_g = (counts.get('GREEN', 0) / total * 100) if total > 0 else 0

                st.markdown(f"""
                <div style="background: rgba(18, 26, 43, 0.7); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 14px 18px; margin-top: 4px;">
                    <div style="font-size: 0.78rem; font-weight: 600; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px;">
                        Tỷ lệ tích lũy phân đoạn 3 khay:
                    </div>
                    <div class="micro-stacked-bar">
                        <div class="micro-bar-seg-red" style="width: {pct_r}%;" title="Đỏ: {pct_r:.1f}%"></div>
                        <div class="micro-bar-seg-yellow" style="width: {pct_y}%;" title="Vàng: {pct_y:.1f}%"></div>
                        <div class="micro-bar-seg-green" style="width: {pct_g}%;" title="Xanh: {pct_g:.1f}%"></div>
                    </div>
                    
                    <div style="display: flex; justify-content: space-between; align-items: center; margin: 12px 0 4px 0; font-size: 0.85rem;">
                        <span style="color: #FB7185;"><span class="led-dot led-red"></span>Khay Đỏ (Góc 45°)</span>
                        <strong class="mono-num" style="color: #F8FAFC;">{counts.get('RED', 0):,} <span style="font-size: 0.75rem; color: #94A3B8;">({pct_r:.1f}%)</span></strong>
                    </div>
                """, unsafe_allow_html=True)
                st.progress(min(1.0, pct_r / 100.0))

                st.markdown(f"""
                    <div style="display: flex; justify-content: space-between; align-items: center; margin: 8px 0 4px 0; font-size: 0.85rem;">
                        <span style="color: #FBBF24;"><span class="led-dot led-yellow"></span>Khay Vàng (Góc 90°)</span>
                        <strong class="mono-num" style="color: #F8FAFC;">{counts.get('YELLOW', 0):,} <span style="font-size: 0.75rem; color: #94A3B8;">({pct_y:.1f}%)</span></strong>
                    </div>
                """, unsafe_allow_html=True)
                st.progress(min(1.0, pct_y / 100.0))

                st.markdown(f"""
                    <div style="display: flex; justify-content: space-between; align-items: center; margin: 8px 0 4px 0; font-size: 0.85rem;">
                        <span style="color: #34D399;"><span class="led-dot led-green"></span>Khay Xanh (Góc 135°)</span>
                        <strong class="mono-num" style="color: #F8FAFC;">{counts.get('GREEN', 0):,} <span style="font-size: 0.75rem; color: #94A3B8;">({pct_g:.1f}%)</span></strong>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                st.progress(min(1.0, pct_g / 100.0))

            st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
            render_chart_header(
                "NHẬT KÝ PHÂN LOẠI THỜI GIAN THỰC (50 BẢN GHI GẦN NHẤT)",
                "Giám sát chi tiết từng sự kiện phân loại sản phẩm theo thời gian thực (nhãn màu, độ tin cậy AI, thời gian gạt).",
                "Ghi nhận từ luồng HTTP POST / MQTT của Edge Camera lên Cloud Database.",
                "Độ tin cậy AI (Confidence) đạt ≥ 80%; thời gian gạt khớp với chu kỳ băng chuyền."
            )
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
    # TAB 2: BÁO CÁO NĂNG SUẤT, CHỈ SỐ OEE & HEATMAP 24H
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
                "summary_label": "Toàn bộ lịch sử",
                "target_shift": 500,
                "ideal_rate": 15.0
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
                    "summary_label": f"{sel_time_preset} &bull; {sel_shift} &bull; {sel_color}",
                    "target_shift": st.session_state.analytics_filter_applied.get("target_shift", 500),
                    "ideal_rate": st.session_state.analytics_filter_applied.get("ideal_rate", 15.0)
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
                    "summary_label": "Toàn bộ lịch sử",
                    "target_shift": 500,
                    "ideal_rate": 15.0
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
        # 2. KHUNG HIỂN THỊ DỮ LIỆU PHÂN TÍCH GIAI ĐOẠN 2 (FRAGMENT)
        # ----------------------------------------------------
        @st.fragment(run_every=f"{refresh_sec*2}s" if auto_refresh else None)
        def render_analytics_display_content():
            current_filter = st.session_state.analytics_filter_applied
            
            # ----------------------------------------------------
            # 2.1. CHỈ SỐ OEE CÔNG NGHIỆP (OVERALL EQUIPMENT EFFECTIVENESS)
            # ----------------------------------------------------
            render_chart_header(
                "HIỆU SUẤT THIẾT BỊ TỔNG THỂ (OEE)",
                "Đánh giá toàn diện hiệu suất vận hành của dây chuyền phân loại theo chuẩn quốc tế MES/SCADA.",
                "OEE = Availability (A) &times; Performance (P) &times; Quality (Q).<br>&bull; A: Thời gian chạy thực tế / Thời gian kế hoạch.<br>&bull; P: Tốc độ thực tế / Tốc độ thiết kế (15.0 SP/phút).<br>&bull; Q: Tỷ lệ nhận diện tin cậy (Confidence &ge; 80%).",
                "&ge; 85%: Đẳng cấp thế giới (World Class)<br>65% - 85%: Đạt chuẩn sản xuất (Typical)<br>&lt; 65%: Cần cải tiến hiệu năng (Unacceptable)."
            )
            
            oee_data = fetch_oee_metrics(
                start_time=current_filter.get("start_time"),
                end_time=current_filter.get("end_time"),
                shift=current_filter.get("shift_param"),
                ideal_run_rate=float(current_filter.get("ideal_rate", 15.0))
            )
            
            if oee_data:
                oee_val = oee_data.get("oee", 0.0)
                a_val = oee_data.get("availability", 0.0)
                p_val = oee_data.get("performance", 0.0)
                q_val = oee_data.get("quality", 100.0)
                status_b = oee_data.get("benchmark_status", "TYPICAL")
                actual_rate = oee_data.get("actual_run_rate", 0.0)
                ideal_rate = oee_data.get("ideal_run_rate", 15.0)
                downtime_m = oee_data.get("downtime_minutes", 0.0)
                good_cnt = oee_data.get("good_count", 0)
                total_cnt = oee_data.get("total_logs", 0)

                col_gauge, col_apq = st.columns([1.1, 1.9])

                with col_gauge:
                    # Plotly OEE Gauge Chart
                    fig_gauge = go.Figure(go.Indicator(
                        mode="gauge+number",
                        value=oee_val,
                        number={'suffix': "%", 'font': {'size': 36, 'color': '#F8FAFC', 'family': 'Outfit'}},
                        title={'text': "CHỈ SỐ OEE TỔNG THỂ", 'font': {'size': 13, 'color': '#94A3B8'}},
                        gauge={
                            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "#475569"},
                            'bar': {'color': "#38BDF8", 'thickness': 0.28},
                            'bgcolor': "rgba(30, 41, 59, 0.5)",
                            'borderwidth': 1,
                            'bordercolor': "rgba(255,255,255,0.08)",
                            'steps': [
                                {'range': [0, 65], 'color': 'rgba(239, 68, 68, 0.25)'},
                                {'range': [65, 85], 'color': 'rgba(245, 158, 11, 0.25)'},
                                {'range': [85, 100], 'color': 'rgba(16, 185, 129, 0.25)'}
                            ],
                            'threshold': {
                                'line': {'color': "#34D399", 'width': 3},
                                'thickness': 0.8,
                                'value': 85.0
                            }
                        }
                    ))
                    fig_gauge.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="#94A3B8", family="Outfit"),
                        height=210,
                        margin=dict(l=20, r=20, t=30, b=10)
                    )
                    st.plotly_chart(fig_gauge, use_container_width=True)

                    # Đánh giá phân cấp chuẩn SCADA
                    if status_b == "WORLD_CLASS":
                        badge_html = '<span class="oee-badge-world-class">ĐẲNG CẤP THẾ GIỚI (WORLD CLASS &ge; 85%)</span>'
                    elif status_b == "TYPICAL":
                        badge_html = '<span class="oee-badge-typical">ĐẠT TIÊU CHUẨN SẢN XUẤT (65% - 85%)</span>'
                    else:
                        badge_html = '<span class="oee-badge-unacceptable">CẦN CẢI TIẾN HIỆU NĂNG (&lt; 65%)</span>'
                    st.markdown(f"<div style='text-align: center; margin-top: -10px;'>{badge_html}</div>", unsafe_allow_html=True)

                with col_apq:
                    # 3 Metric Cards A, P, Q
                    c_a, c_p, c_q = st.columns(3)
                    with c_a:
                        st.markdown(f"""
                        <div class="oee-metric-card">
                            <div style="color: #38BDF8; font-weight: 700; font-size: 0.88rem; margin-bottom: 4px;">Tính Sẵn Sàng (A)</div>
                            <div style="font-size: 1.6rem; font-weight: 800; color: #F8FAFC;">{a_val:.1f}%</div>
                            <div style="color: #94A3B8; font-size: 0.76rem; margin-top: 4px;">Thời gian dừng: <strong>{downtime_m} phút</strong></div>
                        </div>
                        """, unsafe_allow_html=True)
                        st.progress(min(1.0, a_val / 100.0))

                    with c_p:
                        st.markdown(f"""
                        <div class="oee-metric-card">
                            <div style="color: #C084FC; font-weight: 700; font-size: 0.88rem; margin-bottom: 4px;">Hiệu Suất (P)</div>
                            <div style="font-size: 1.6rem; font-weight: 800; color: #F8FAFC;">{p_val:.1f}%</div>
                            <div style="color: #94A3B8; font-size: 0.76rem; margin-top: 4px;">Vận tốc: <strong>{actual_rate}/{ideal_rate} sp/p</strong></div>
                        </div>
                        """, unsafe_allow_html=True)
                        st.progress(min(1.0, p_val / 100.0))

                    with c_q:
                        st.markdown(f"""
                        <div class="oee-metric-card">
                            <div style="color: #34D399; font-weight: 700; font-size: 0.88rem; margin-bottom: 4px;">Chất Lượng (Q)</div>
                            <div style="font-size: 1.6rem; font-weight: 800; color: #F8FAFC;">{q_val:.1f}%</div>
                            <div style="color: #94A3B8; font-size: 0.76rem; margin-top: 4px;">Đạt chuẩn: <strong>{good_cnt}/{total_cnt} sp</strong></div>
                        </div>
                        """, unsafe_allow_html=True)
                        st.progress(min(1.0, q_val / 100.0))

                    st.markdown("""
                    <div style="margin-top: 12px; background: rgba(15, 23, 42, 0.4); border-radius: 8px; padding: 10px 14px; font-size: 0.8rem; color: #94A3B8; border: 1px solid rgba(255,255,255,0.05);">
                        Công thức SCADA: <code>OEE = Availability &times; Performance &times; Quality</code> &nbsp;&bull;&nbsp; Định mức thiết kế: <strong>15.0 SP/phút</strong>
                    </div>
                    """, unsafe_allow_html=True)

            st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

            # ----------------------------------------------------
            # 2.2. ĐỐI CHIẾU TIẾN ĐỘ KẾ HOẠCH (TARGET VS ACTUAL)
            # ----------------------------------------------------
            render_chart_header(
                "ĐỐI CHIẾU TIẾN ĐỘ KẾ HOẠCH SẢN XUẤT (TARGET VS ACTUAL)",
                "Kiểm soát tiến độ hoàn thành chỉ tiêu ca sản xuất, dự báo thời điểm hoàn thành (ETA) và phát hiện sớm nguy cơ trễ hạn.",
                "Tiến độ % = (Thực tế / Mục tiêu ca) &times; 100%.<br>Chênh lệch = Thực tế - Mục tiêu.<br>ETA = Thời gian hiện tại + (Số lượng còn lại / Vận tốc trung bình 15 phút gần nhất).",
                "Đạt 100% mục tiêu trước khi kết thúc ca làm việc; Chênh lệch tiến độ luôn duy trì mức dương (+ SP)."
            )
            
            target_data = fetch_target_vs_actual(
                target_shift=int(current_filter.get("target_shift", 500)),
                start_time=current_filter.get("start_time"),
                end_time=current_filter.get("end_time"),
                shift=current_filter.get("shift_param")
            )

            if target_data:
                tgt_shift = target_data.get("target_shift", 500)
                act_cnt = target_data.get("actual_count", 0)
                comp_pct = target_data.get("completion_pct", 0.0)
                var_units = target_data.get("variance_units", 0)
                eta_str = target_data.get("eta_timestamp", "Chưa xác định")
                color_targets = target_data.get("color_targets", {})

                col_tgt_kpi, col_tgt_chart = st.columns([1.2, 1.8])

                with col_tgt_kpi:
                    var_color = "#34D399" if var_units >= 0 else "#FB7185"
                    var_sign = f"+{var_units}" if var_units >= 0 else f"{var_units}"
                    
                    st.markdown(f"""
                    <div class="target-metric-box">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                            <span style="color: #94A3B8; font-size: 0.85rem; font-weight: 500;">Tiến Độ Hoàn Thành Ca:</span>
                            <span style="color: #38BDF8; font-weight: 700; font-size: 1.1rem;">{comp_pct:.1f}%</span>
                        </div>
                    """, unsafe_allow_html=True)
                    st.progress(min(1.0, comp_pct / 100.0))
                    
                    st.markdown(f"""
                        <div style="display: flex; justify-content: space-between; margin: 12px 0 6px 0; font-size: 0.86rem;">
                            <span style="color: #94A3B8;">Thực tế / Mục tiêu:</span>
                            <strong style="color: #F8FAFC;">{act_cnt:,} / {tgt_shift:,} SP</strong>
                        </div>
                        <div style="display: flex; justify-content: space-between; margin-bottom: 6px; font-size: 0.86rem;">
                            <span style="color: #94A3B8;">Chênh lệch tiến độ:</span>
                            <strong style="color: {var_color};">{var_sign} SP</strong>
                        </div>
                        <div style="display: flex; justify-content: space-between; font-size: 0.86rem;">
                            <span style="color: #94A3B8;">Dự kiến cán đích (ETA):</span>
                            <strong style="color: #FBBF24;">{eta_str}</strong>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                with col_tgt_chart:
                    # So sánh Target vs Actual phân bổ từng màu
                    df_tgt = pd.DataFrame([
                        {"Màu": "Đỏ (RED)", "Thực tế": color_targets.get("RED", {}).get("actual", 0), "Mục tiêu": color_targets.get("RED", {}).get("target", 0)},
                        {"Màu": "Vàng (YELLOW)", "Thực tế": color_targets.get("YELLOW", {}).get("actual", 0), "Mục tiêu": color_targets.get("YELLOW", {}).get("target", 0)},
                        {"Màu": "Xanh (GREEN)", "Thực tế": color_targets.get("GREEN", {}).get("actual", 0), "Mục tiêu": color_targets.get("GREEN", {}).get("target", 0)}
                    ])
                    df_tgt_melt = df_tgt.melt(id_vars=["Màu"], value_vars=["Thực tế", "Mục tiêu"], var_name="Loại", value_name="Số lượng")
                    
                    fig_tgt = px.bar(
                        df_tgt_melt, x="Màu", y="Số lượng", color="Loại",
                        barmode="group",
                        color_discrete_map={"Thực tế": "#38BDF8", "Mục tiêu": "#64748B"},
                        text="Số lượng"
                    )
                    fig_tgt.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="#94A3B8", family="Outfit"),
                        xaxis=dict(showgrid=False),
                        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                        height=210,
                        margin=dict(l=10, r=10, t=30, b=10)
                    )
                    st.plotly_chart(fig_tgt, use_container_width=True)

            st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

            # ----------------------------------------------------
            # 2.3. BIỂU ĐỒ MA TRẬN NHIỆT NĂNG SUẤT 24H (HEATMAP MATRIX)
            # ----------------------------------------------------
            render_chart_header(
                "MA TRẬN NHIỆT PHÂN BỐ NĂNG SUẤT 24H (24-HOUR PRODUCTIVITY HEATMAP)",
                "Phát hiện các điểm nghẽn (Bottlenecks), thời điểm dây chuyền bị chững lại hoặc đạt đỉnh năng suất trong 24 giờ và các ngày trong tuần.",
                "Tổng hợp số lượng log gạt theo từng ô tọa độ ma trận [Ngày/Màu, Khung Giờ].",
                "Các khung giờ chính trong ca hiển thị dải màu xanh/cam liên tục (sản xuất đều đặn), không bị đứt đoạn hoặc tắt màu bất thường."
            )
            
            heatmap_data = fetch_heatmap_matrix(days=7)
            if heatmap_data:
                tab_hm1, tab_hm2 = st.tabs(["Theo 7 Ngày Trong Tuần (24h x 7 Days)", "Theo 3 Màu Sản Phẩm (24h x 3 Colors)"])
                
                # Dark SCADA Color Scale
                scada_colorscale = [
                    [0.0, "rgba(15, 23, 42, 0.9)"],
                    [0.2, "rgba(30, 41, 59, 0.8)"],
                    [0.4, "#0284C7"],
                    [0.7, "#10B981"],
                    [1.0, "#F59E0B"]
                ]

                with tab_hm1:
                    hm_days = heatmap_data.get("days_heatmap", {})
                    fig_hm1 = px.imshow(
                        hm_days.get("z_matrix", []),
                        x=hm_days.get("x_labels", []),
                        y=hm_days.get("y_labels", []),
                        color_continuous_scale=scada_colorscale,
                        labels=dict(x="Khung giờ trong ngày", y="Ngày trong tuần", color="Sản lượng (SP)"),
                        aspect="auto"
                    )
                    fig_hm1.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="#94A3B8", family="Outfit"),
                        height=270,
                        margin=dict(l=10, r=10, t=15, b=10)
                    )
                    st.plotly_chart(fig_hm1, use_container_width=True)

                with tab_hm2:
                    hm_colors = heatmap_data.get("colors_heatmap", {})
                    fig_hm2 = px.imshow(
                        hm_colors.get("z_matrix", []),
                        x=hm_colors.get("x_labels", []),
                        y=hm_colors.get("y_labels", []),
                        color_continuous_scale=scada_colorscale,
                        labels=dict(x="Khung giờ trong ngày", y="Phân loại", color="Sản lượng (SP)"),
                        aspect="auto"
                    )
                    fig_hm2.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="#94A3B8", family="Outfit"),
                        height=210,
                        margin=dict(l=10, r=10, t=15, b=10)
                    )
                    st.plotly_chart(fig_hm2, use_container_width=True)

            st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

            # ----------------------------------------------------
            # 2.4. DIỄN BIẾN NĂNG SUẤT (TIMELINE & S-CURVE)
            # ----------------------------------------------------
            render_chart_header(
                "DIỄN BIẾN SẢN LƯỢNG & TÍCH LŨY THEO THỜI GIAN",
                "Theo dõi nhịp độ sản xuất từng phút và đánh giá tốc độ tăng trưởng lũy kế sản lượng theo đường cong S-Curve.",
                "Gom nhóm sản lượng theo phút (dt.floor('min')) và tính tổng tích lũy luỹ kế (cumsum).",
                "Đường cong S-Curve đi lên dốc đều, không xuất hiện các đoạn nằm ngang kéo dài (chứng tỏ dây chuyền không bị dừng đột ngột)."
            )
            
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

                grouped = df_time.groupby(['dt_minute', 'color_label']).size().reset_index(name='count')
                grouped = grouped.sort_values(by='dt_minute', ascending=True)
                grouped['time_display'] = grouped['dt_minute'].dt.strftime(time_fmt)

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
                # 2.5. PHÂN BỔ KHUNG GIỜ & THỐNG KÊ TỔNG QUAN
                # ----------------------------------------------------
                col_hr, col_summary = st.columns([1.4, 1])
                with col_hr:
                    render_chart_header(
                        "PHÂN BỔ SẢN LƯỢNG THEO KHUNG GIỜ",
                        "So sánh sản lượng giữa các khung giờ làm việc để đánh giá tính ổn định qua từng giai đoạn trong ca.",
                        "Gom nhóm dữ liệu theo từng giờ tròn (HH:00) và đếm số lượng từng màu.",
                        "Sản lượng mỗi giờ duy trì ổn định, không sụt giảm quá 20% so với mức trung bình của ca."
                    )
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
                    render_chart_header(
                        "THỐNG KÊ HIỆU SUẤT THEO BỘ LỌC",
                        "Tổng kết nhanh tổng sản lượng và tỷ trọng các màu trong phạm vi bộ lọc đang chọn.",
                        "Đếm tổng log và tỷ lệ % từng màu trong khoảng thời gian/ca đã lọc.",
                        "Dữ liệu khớp với báo cáo ca và không có màu nào bị mất cân đối nghiêm trọng."
                    )
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
            # 2.6. GIÁM SÁT VÒNG ĐỜI & SỨC KHỎE CƠ CẤU SERVO SG90
            # ----------------------------------------------------
            st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
            render_chart_header(
                "GIÁM SÁT SỨC KHỎE & VÒNG ĐỜI CƠ CẤU SERVO SG90",
                "Bảo trì phòng ngừa (Predictive Maintenance), theo dõi mức độ hao mòn cơ khí và phát hiện hiện tượng lệch tải góc quay.",
                "Hao mòn % = (Tổng chu kỳ gạt / Định mức 10,000 chu kỳ) &times; 100%.<br>Cảnh báo lệch tải nếu 1 góc chịu &gt; 65% tải trọng.",
                "&lt; 70%: Hoạt động tốt (Healthy)<br>70% - 90%: Cảnh báo chuẩn bị thay thế (Warning)<br>&gt; 90%: Nguy cấp - cần bảo dưỡng/thay mới ngay (Critical)."
            )
            
            servo_data = fetch_servo_health(max_rated_cycles=10000)
            if servo_data:
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
            st.markdown("<div class='section-header'>CẤU HÌNH THAM SỐ VẬN HÀNH & MỤC TIÊU</div>", unsafe_allow_html=True)
            configs = fetch_configs()

            with st.form("sys_config_form"):
                target_shift_cfg = st.number_input(
                    "Mục Tiêu Sản Lượng Toàn Ca (SP / Ca)",
                    min_value=50, max_value=5000,
                    value=int(configs.get("target_total_shift", 500))
                )
                ideal_rate_cfg = st.number_input(
                    "Tốc Độ Thiết Kế Định Mức (SP / Phút)",
                    min_value=1.0, max_value=60.0,
                    value=float(configs.get("ideal_run_rate", 15.0)),
                    step=0.5
                )
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
                    update_config_value("target_total_shift", target_shift_cfg)
                    update_config_value("ideal_run_rate", ideal_rate_cfg)
                    update_config_value("anomaly_threshold", threshold)
                    update_config_value("servo_red_angle", angle_red)
                    update_config_value("servo_yellow_angle", angle_yellow)
                    update_config_value("servo_green_angle", angle_green)
                    st.session_state.analytics_filter_applied["target_shift"] = target_shift_cfg
                    st.session_state.analytics_filter_applied["ideal_rate"] = ideal_rate_cfg
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

