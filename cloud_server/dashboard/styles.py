import streamlit as st

def inject_custom_styles():
    """Nhúng toàn bộ CSS chuẩn công nghiệp cao cấp vào ứng dụng Streamlit"""
    st.markdown("""
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">

    <style>
        /* Base Reset & Typography */
        html, body, [class*="css"], .stApp {
            font-family: 'Outfit', -apple-system, BlinkMacSystemFont, sans-serif !important;
            background-color: #0B0F19 !important;
            color: #F8FAFC !important;
        }

        /* Top Header & Gradient Text */
        .app-title-gradient {
            background: linear-gradient(135deg, #FFFFFF 0%, #CBD5E1 50%, #94A3B8 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 800;
            font-size: 2.1rem;
            letter-spacing: -0.02em;
            margin-bottom: 4px;
        }

        .app-subtitle {
            color: #94A3B8;
            font-size: 0.95rem;
            font-weight: 400;
            margin-bottom: 20px;
        }

        /* Glassmorphism Cards */
        .glass-card {
            background: rgba(17, 24, 39, 0.75);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
            transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
        }

        .glass-card:hover {
            border-color: rgba(99, 102, 241, 0.3);
            box-shadow: 0 12px 40px 0 rgba(0, 0, 0, 0.45);
        }

        /* KPI Stat Cards */
        .kpi-card {
            background: linear-gradient(145deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.9) 100%);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 14px;
            padding: 18px 20px;
            position: relative;
            overflow: hidden;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
            transition: transform 0.2s ease, border-color 0.2s ease;
        }

        .kpi-card:hover {
            transform: translateY(-2px);
            border-color: rgba(255, 255, 255, 0.15);
        }

        .kpi-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
        }

        .kpi-total::before { background: linear-gradient(90deg, #6366F1, #38BDF8); }
        .kpi-red::before { background: linear-gradient(90deg, #F43F5E, #FB7185); }
        .kpi-yellow::before { background: linear-gradient(90deg, #F59E0B, #FBBF24); }
        .kpi-green::before { background: linear-gradient(90deg, #10B981, #34D399); }
        .kpi-speed::before { background: linear-gradient(90deg, #8B5CF6, #C084FC); }

        .kpi-title {
            color: #94A3B8;
            font-size: 0.82rem;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 6px;
        }

        .kpi-value {
            color: #F8FAFC;
            font-size: 1.85rem;
            font-weight: 700;
            line-height: 1.1;
            font-family: 'JetBrains Mono', monospace;
        }

        .kpi-sub {
            color: #64748B;
            font-size: 0.78rem;
            margin-top: 6px;
            display: flex;
            align-items: center;
            gap: 4px;
        }

        /* Role Badges */
        .role-badge-manager {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(99, 102, 241, 0.15);
            color: #818CF8;
            border: 1px solid rgba(99, 102, 241, 0.3);
            padding: 4px 12px;
            border-radius: 9999px;
            font-size: 0.8rem;
            font-weight: 600;
            letter-spacing: 0.02em;
        }

        .role-badge-worker {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(16, 185, 129, 0.15);
            color: #34D399;
            border: 1px solid rgba(16, 185, 129, 0.3);
            padding: 4px 12px;
            border-radius: 9999px;
            font-size: 0.8rem;
            font-weight: 600;
            letter-spacing: 0.02em;
        }

        /* Anomaly Alert Box */
        .pulse-alert-box {
            background: linear-gradient(135deg, rgba(239, 68, 68, 0.12) 0%, rgba(153, 27, 27, 0.2) 100%);
            border: 1px solid rgba(239, 68, 68, 0.4);
            border-left: 5px solid #EF4444;
            border-radius: 12px;
            padding: 16px 20px;
            color: #FECACA;
            margin-bottom: 24px;
            display: flex;
            align-items: center;
            gap: 16px;
            box-shadow: 0 0 24px rgba(239, 68, 68, 0.15);
            animation: pulse-glow 2s infinite ease-in-out;
        }

        @keyframes pulse-glow {
            0%, 100% { box-shadow: 0 0 16px rgba(239, 68, 68, 0.15); }
            50% { box-shadow: 0 0 28px rgba(239, 68, 68, 0.3); }
        }

        .alert-title {
            font-weight: 700;
            font-size: 1.05rem;
            color: #F87171;
            margin-bottom: 2px;
        }

        .alert-desc {
            font-size: 0.88rem;
            color: #E2E8F0;
        }

        /* Streamlit Tabs Customization */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background-color: rgba(15, 23, 42, 0.6);
            padding: 6px;
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }

        .stTabs [data-baseweb="tab"] {
            height: 42px;
            border-radius: 8px;
            color: #94A3B8 !important;
            font-weight: 500;
            font-size: 0.92rem;
            padding: 0 18px;
            border: none !important;
            background-color: transparent;
            transition: all 0.2s ease;
        }

        .stTabs [aria-selected="true"] {
            background-color: #1E293B !important;
            color: #FFFFFF !important;
            font-weight: 600;
            box-shadow: 0 2px 10px rgba(0,0,0,0.25);
        }

        /* Dataframe styling */
        .stDataFrame {
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid rgba(255, 255, 255, 0.06);
        }

        /* Sidebar Styling */
        section[data-testid="stSidebar"] {
            background-color: #0F172A !important;
            border-right: 1px solid rgba(255, 255, 255, 0.06);
        }

        /* Form Inputs */
        div[data-baseweb="input"], div[data-baseweb="select"] {
            background-color: #1E293B !important;
            border-color: rgba(255, 255, 255, 0.1) !important;
            border-radius: 10px !important;
            color: #F8FAFC !important;
        }

        /* Primary Button */
        button[kind="primary"] {
            background: linear-gradient(135deg, #6366F1 0%, #4F46E5 100%) !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 10px !important;
            font-weight: 600 !important;
            box-shadow: 0 4px 14px rgba(99, 102, 241, 0.3) !important;
            transition: all 0.2s ease !important;
        }

        button[kind="primary"]:hover {
            transform: translateY(-1px);
            box-shadow: 0 6px 20px rgba(99, 102, 241, 0.45) !important;
        }

        /* Secondary / Outline Button */
        button[kind="secondary"] {
            background-color: #1E293B !important;
            color: #E2E8F0 !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            border-radius: 10px !important;
            font-weight: 500 !important;
        }

        button[kind="secondary"]:hover {
            background-color: #334155 !important;
            border-color: rgba(255, 255, 255, 0.2) !important;
        }

        /* Industrial Minimalism & LED Indicators */
        .section-header {
            font-size: 0.92rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: #E2E8F0;
            border-left: 3px solid #38BDF8;
            padding-left: 10px;
            margin: 18px 0 12px 0;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .led-dot {
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            margin-right: 6px;
        }
        .led-red { background-color: #F43F5E; box-shadow: 0 0 8px #F43F5E; }
        .led-yellow { background-color: #F59E0B; box-shadow: 0 0 8px #F59E0B; }
        .led-green { background-color: #10B981; box-shadow: 0 0 8px #10B981; }
        .led-blue { background-color: #38BDF8; box-shadow: 0 0 8px #38BDF8; }
        .led-gray { background-color: #64748B; }

        .filter-panel-box {
            background: rgba(15, 23, 42, 0.7);
            border: 1px solid rgba(255, 255, 255, 0.07);
            border-radius: 12px;
            padding: 16px 20px;
            margin-bottom: 20px;
        }

        .filter-active-status {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: rgba(30, 41, 59, 0.7);
            border: 1px solid rgba(56, 189, 248, 0.25);
            border-radius: 8px;
            padding: 6px 14px;
            font-size: 0.82rem;
            color: #94A3B8;
            margin-top: 10px;
        }
        .filter-active-val {
            color: #38BDF8;
            font-weight: 600;
        }

        /* Hide Streamlit Default Elements for a clean native look */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}

        /* VÔ HIỆU HÓA HOÀN TOÀN MỌI TRẠNG THÁI STALE / DIMMING CỦA STREAMLIT */
        [data-stale="true"],
        [data-stale="true"] *,
        [data-testid="stFragment"][data-stale="true"],
        [data-testid="stFragment"][data-stale="true"] *,
        [data-testid="stMain"][data-stale="true"],
        [data-testid="stMain"][data-stale="true"] *,
        [data-testid="stAppViewBlockContainer"][data-stale="true"],
        [data-testid="stAppViewBlockContainer"][data-stale="true"] *,
        [data-testid="stVerticalBlock"][data-stale="true"],
        [data-testid="stVerticalBlock"][data-stale="true"] *,
        div[class*="st-emotion-cache"][data-stale="true"],
        div[class*="st-emotion-cache"][data-stale="true"] *,
        .element-container[data-stale="true"],
        .element-container[data-stale="true"] * {
            opacity: 1 !important;
            filter: none !important;
            -webkit-filter: none !important;
            transition: none !important;
        }

        /* Khóa độ sáng tất cả các container con */
        section[data-testid="stMain"],
        [data-testid="stAppViewContainer"] [data-testid="stMain"],
        [data-testid="stAppViewBlockContainer"],
        [data-testid="stVerticalBlock"],
        [data-testid="stFragment"] {
            opacity: 1 !important;
            filter: none !important;
            transition: none !important;
        }

        /* Vô hiệu hóa lớp phủ skeleton mờ xám */
        div[data-testid="stSkeleton"],
        div.st-emotion-cache-18ni7ap,
        div.st-emotion-cache-16txtl3,
        div.st-emotion-cache-1wmy9hl,
        .st-emotion-cache-1r6slb0 {
            opacity: 1 !important;
            filter: none !important;
        }

        /* Ẩn Running Status Widget góc phải */
        [data-testid="stStatusWidget"] {
            display: none !important;
        }

        /* Live feed pulsing badge */
        .live-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(16, 185, 129, 0.12);
            color: #34D399;
            border: 1px solid rgba(16, 185, 129, 0.25);
            padding: 4px 10px;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
            letter-spacing: 0.03em;
        }

        .live-dot {
            width: 7px;
            height: 7px;
            background-color: #10B981;
            border-radius: 50%;
            display: inline-block;
            box-shadow: 0 0 8px #10B981;
            animation: live-blink 1.5s infinite ease-in-out;
        }

        @keyframes live-blink {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.4; transform: scale(0.8); }
        }
    </style>
    """, unsafe_allow_html=True)

def inject_anti_flicker_js():
    """MutationObserver JavaScript để gỡ bỏ data-stale ngay lập tức khỏi DOM"""
    import streamlit.components.v1 as components
    js_code = """
    <script>
        (function() {
            function clearStale() {
                try {
                    const doc = window.parent.document;
                    const stales = doc.querySelectorAll('[data-stale="true"]');
                    stales.forEach(function(el) {
                        el.removeAttribute('data-stale');
                        el.style.opacity = '1';
                        el.style.filter = 'none';
                    });
                } catch(e) {}
            }

            try {
                const doc = window.parent.document;
                const observer = new MutationObserver(function(mutations) {
                    clearStale();
                });
                observer.observe(doc.body, { attributes: true, subtree: true, attributeFilter: ['data-stale'] });
                clearStale();
            } catch(e) {}
        })();
    </script>
    """
    components.html(js_code, height=0, width=0)

