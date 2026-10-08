import streamlit as st

def inject_custom_styles():
    """Nhúng toàn bộ CSS chuẩn công nghiệp cao cấp SCADA / Industrial IoT vào Streamlit"""
    st.markdown("""
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700;800&family=Outfit:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">

    <style>
        /* ==========================================================================
           1. BASE RESET & INDUSTRIAL DESIGN TOKENS
           ========================================================================== */
        :root {
            --scada-bg: #0B0F17;
            --scada-surface: rgba(18, 26, 43, 0.85);
            --scada-surface-card: #121A2B;
            --scada-surface-hover: rgba(30, 41, 59, 0.95);
            --scada-border: rgba(255, 255, 255, 0.08);
            --scada-border-cyan: rgba(56, 189, 248, 0.4);
            
            --scada-text-main: #F8FAFC;
            --scada-text-secondary: #94A3B8;
            --scada-text-muted: #64748B;
            
            /* Product Object Colors */
            --prod-red: #FB7185;
            --prod-yellow: #FBBF24;
            --prod-green: #34D399;
            
            /* Technical System Status Colors */
            --sys-critical: #EF4444;
            --sys-warning: #F59E0B;
            --sys-healthy: #10B981;
            --sys-cyan: #38BDF8;
        }

        html, body, [class*="css"], .stApp {
            font-family: 'Outfit', -apple-system, BlinkMacSystemFont, sans-serif !important;
            background-color: var(--scada-bg) !important;
            color: var(--scada-text-main) !important;
            letter-spacing: -0.01em;
        }

        /* Monospace Tabular Numerals for Mission-Critical SCADA Data */
        .mono-num, .kpi-mono-val, .scada-timestamp {
            font-family: 'JetBrains Mono', monospace !important;
            font-feature-settings: "tnum" 1, "zero" 1;
            letter-spacing: -0.03em;
        }

        /* ==========================================================================
           2. TOPBAR, HEADER & INDUSTRIAL STATUS BADGES
           ========================================================================== */
        .app-title-gradient {
            background: linear-gradient(135deg, #FFFFFF 0%, #E2E8F0 50%, #94A3B8 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 800;
            font-size: 1.85rem;
            letter-spacing: -0.02em;
            margin-bottom: 2px;
            line-height: 1.2;
        }

        .app-subtitle {
            color: var(--scada-text-secondary);
            font-size: 0.88rem;
            font-weight: 400;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 8px;
        }

        .scada-topbar-chip {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(30, 41, 59, 0.7);
            border: 1px solid var(--scada-border);
            border-radius: 6px;
            padding: 3px 10px;
            font-size: 0.76rem;
            color: var(--scada-text-secondary);
            font-family: 'JetBrains Mono', monospace;
        }

        .live-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(56, 189, 248, 0.12);
            color: #38BDF8;
            border: 1px solid rgba(56, 189, 248, 0.3);
            border-radius: 6px;
            padding: 2px 10px;
            font-size: 0.76rem;
            font-weight: 700;
            letter-spacing: 0.04em;
            text-transform: uppercase;
        }

        .live-dot {
            width: 7px;
            height: 7px;
            background-color: #38BDF8;
            border-radius: 50%;
            display: inline-block;
            box-shadow: 0 0 8px #38BDF8;
            animation: pulse-dot 1.8s infinite cubic-bezier(0.4, 0, 0.6, 1);
        }

        @keyframes pulse-dot {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.3; transform: scale(0.75); }
        }

        /* LED Technical Indicators */
        .led-dot {
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            margin-right: 6px;
        }
        .led-red { background-color: var(--prod-red); box-shadow: 0 0 8px var(--prod-red); }
        .led-yellow { background-color: var(--prod-yellow); box-shadow: 0 0 8px var(--prod-yellow); }
        .led-green { background-color: var(--prod-green); box-shadow: 0 0 8px var(--prod-green); }
        .led-blue { background-color: var(--sys-cyan); box-shadow: 0 0 8px var(--sys-cyan); }
        .led-gray { background-color: var(--scada-text-muted); }

        /* ==========================================================================
           3. ALERT BANNER (HIGH VISUAL WEIGHT & HAZARD STRIPING)
           ========================================================================== */
        .pulse-alert-box {
            background: linear-gradient(135deg, rgba(239, 68, 68, 0.15) 0%, rgba(153, 27, 27, 0.25) 100%);
            border: 1px solid rgba(239, 68, 68, 0.5);
            border-left: 6px solid var(--sys-critical);
            border-radius: 10px;
            padding: 14px 18px;
            color: #FECACA;
            margin-bottom: 18px;
            display: flex;
            align-items: center;
            gap: 14px;
            box-shadow: 0 0 24px rgba(239, 68, 68, 0.25);
            animation: pulse-alert-border 2.5s infinite ease-in-out;
        }

        @keyframes pulse-alert-border {
            0%, 100% { box-shadow: 0 0 16px rgba(239, 68, 68, 0.2); }
            50% { box-shadow: 0 0 28px rgba(239, 68, 68, 0.45); }
        }

        .alert-title {
            font-weight: 800;
            font-size: 0.94rem;
            color: #FFFFFF;
            letter-spacing: 0.03em;
            text-transform: uppercase;
        }

        .alert-desc {
            font-size: 0.84rem;
            color: #FCA5A5;
            margin-top: 2px;
        }

        /* ==========================================================================
           4. SCADA KPI METRIC CARDS (EQUAL-WIDTH, METALLIC TOP ACCENT)
           ========================================================================== */
        .scada-kpi-card {
            background: linear-gradient(145deg, rgba(24, 34, 53, 0.85) 0%, rgba(15, 23, 42, 0.95) 100%);
            border: 1px solid var(--scada-border);
            border-radius: 12px;
            padding: 16px 18px;
            position: relative;
            overflow: hidden;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.35);
            transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1), border-color 0.2s ease;
            height: 100%;
        }

        .scada-kpi-card:hover {
            transform: translateY(-2px);
            border-color: rgba(255, 255, 255, 0.16);
            box-shadow: 0 8px 28px rgba(0, 0, 0, 0.5);
        }

        .scada-kpi-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
        }

        .kpi-total::before { background: linear-gradient(90deg, #38BDF8, #6366F1); }
        .kpi-red::before { background: linear-gradient(90deg, #F43F5E, #FB7185); }
        .kpi-yellow::before { background: linear-gradient(90deg, #F59E0B, #FBBF24); }
        .kpi-green::before { background: linear-gradient(90deg, #10B981, #34D399); }
        .kpi-speed::before { background: linear-gradient(90deg, #8B5CF6, #C084FC); }
        .kpi-oee::before { background: linear-gradient(90deg, #10B981, #38BDF8); }

        .scada-kpi-title {
            color: var(--scada-text-secondary);
            font-size: 0.78rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            margin-bottom: 4px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .scada-kpi-val {
            color: var(--scada-text-main);
            font-size: 1.85rem;
            font-weight: 800;
            line-height: 1.1;
            font-family: 'JetBrains Mono', monospace;
            letter-spacing: -0.03em;
        }

        .scada-kpi-sub {
            color: var(--scada-text-muted);
            font-size: 0.75rem;
            margin-top: 6px;
            display: flex;
            align-items: center;
            gap: 4px;
            font-family: 'Outfit', sans-serif;
        }

        /* ==========================================================================
           5. SECTION HEADERS & GLASS CONTAINERS
           ========================================================================== */
        .section-header {
            font-size: 0.86rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: #E2E8F0;
            border-left: 3px solid var(--sys-cyan);
            padding-left: 10px;
            margin: 16px 0 10px 0;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .scada-glass-panel {
            background: var(--scada-surface);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid var(--scada-border);
            border-radius: 12px;
            padding: 16px 18px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
        }

        /* Horizontal Stacked Micro-Bars for Color Breakdown */
        .micro-stacked-bar {
            display: flex;
            height: 10px;
            border-radius: 9999px;
            overflow: hidden;
            background: rgba(15, 23, 42, 0.8);
            border: 1px solid rgba(255, 255, 255, 0.08);
            margin: 12px 0 10px 0;
        }

        .micro-bar-seg-red { background-color: var(--prod-red); }
        .micro-bar-seg-yellow { background-color: var(--prod-yellow); }
        .micro-bar-seg-green { background-color: var(--prod-green); }

        /* ==========================================================================
           6. CIRCULAR INFO BUTTON (i) FOR POPOVERS - 100% CLEAN CIRCLE
           ========================================================================== */
        div[data-testid="stPopover"],
        [data-testid="stPopover"],
        [data-testid="stPopoverButton"] {
            display: inline-flex !important;
            align-items: center !important;
            justify-content: flex-end !important;
            width: auto !important;
        }

        div[data-testid="stPopover"] button,
        [data-testid="stPopover"] button,
        [data-testid="stPopoverButton"] button,
        button[aria-haspopup="dialog"] {
            border-radius: 50% !important;
            -webkit-border-radius: 50% !important;
            width: 22px !important;
            height: 22px !important;
            min-width: 22px !important;
            min-height: 22px !important;
            max-width: 22px !important;
            max-height: 22px !important;
            aspect-ratio: 1 / 1 !important;
            padding: 0 !important;
            margin: 0 !important;
            margin-top: 10px !important;
            font-size: 0.78rem !important;
            font-weight: 800 !important;
            font-family: 'Outfit', sans-serif !important;
            background: rgba(30, 41, 59, 0.95) !important;
            border: 1.5px solid rgba(56, 189, 248, 0.5) !important;
            color: var(--sys-cyan) !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            box-shadow: 0 0 10px rgba(56, 189, 248, 0.25) !important;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
            cursor: pointer !important;
            overflow: hidden !important;
        }

        /* Ẩn triệt để icon mũi tên/chevron xuống của Streamlit Popover */
        div[data-testid="stPopover"] button svg,
        [data-testid="stPopover"] button svg,
        button[aria-haspopup="dialog"] svg,
        div[data-testid="stPopover"] button [data-testid="stIconMaterial"],
        [data-testid="stPopover"] button [data-testid="stIconMaterial"],
        div[data-testid="stPopover"] button [data-testid="stPopoverChevron"],
        [data-testid="stPopover"] button [data-testid="stPopoverChevron"],
        div[data-testid="stPopover"] button span:has(svg),
        [data-testid="stPopover"] button span:has(svg),
        [data-testid="stPopover"] button > span:nth-child(2),
        [data-testid="stPopover"] button > *:not([data-testid="stMarkdownContainer"]):not(:first-child) {
            display: none !important;
            visibility: hidden !important;
            width: 0 !important;
            height: 0 !important;
            opacity: 0 !important;
            position: absolute !important;
            pointer-events: none !important;
        }

        /* Canh giữa hoàn hảo chữ i */
        div[data-testid="stPopover"] button p,
        [data-testid="stPopover"] button p,
        div[data-testid="stPopover"] button [data-testid="stMarkdownContainer"],
        [data-testid="stPopover"] button [data-testid="stMarkdownContainer"] {
            margin: 0 !important;
            padding: 0 !important;
            font-size: 0.8rem !important;
            font-weight: 800 !important;
            font-style: normal !important;
            color: var(--sys-cyan) !important;
            line-height: 1 !important;
            text-align: center !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }

        div[data-testid="stPopover"] button:hover,
        [data-testid="stPopover"] button:hover,
        button[aria-haspopup="dialog"]:hover {
            background: rgba(56, 189, 248, 0.25) !important;
            border-color: var(--sys-cyan) !important;
            transform: scale(1.15) !important;
            box-shadow: 0 0 16px rgba(56, 189, 248, 0.6) !important;
            color: #FFFFFF !important;
        }

        div[data-testid="stPopoverBody"],
        [data-testid="stPopoverBody"] {
            background: rgba(15, 23, 42, 0.98) !important;
            backdrop-filter: blur(16px) !important;
            -webkit-backdrop-filter: blur(16px) !important;
            border: 1px solid var(--scada-border-cyan) !important;
            border-radius: 12px !important;
            box-shadow: 0 20px 45px rgba(0, 0, 0, 0.8) !important;
            padding: 16px 20px !important;
            max-width: 480px !important;
        }

        /* ==========================================================================
           7. OEE & TARGET CARDS SPEC
           ========================================================================== */
        .oee-metric-card {
            background: rgba(24, 34, 53, 0.6);
            border: 1px solid var(--scada-border);
            border-radius: 10px;
            padding: 14px;
            height: 100%;
            transition: border-color 0.2s ease;
        }
        .oee-metric-card:hover {
            border-color: var(--scada-border-cyan);
        }
        .oee-badge-world-class {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            background: rgba(16, 185, 129, 0.15);
            color: #34D399;
            border: 1px solid rgba(16, 185, 129, 0.3);
            border-radius: 6px;
            padding: 2px 8px;
            font-size: 0.74rem;
            font-weight: 700;
        }
        .oee-badge-typical {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            background: rgba(245, 158, 11, 0.15);
            color: #FBBF24;
            border: 1px solid rgba(245, 158, 11, 0.3);
            border-radius: 6px;
            padding: 2px 8px;
            font-size: 0.74rem;
            font-weight: 700;
        }
        .oee-badge-unacceptable {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            background: rgba(239, 68, 68, 0.15);
            color: #F87171;
            border: 1px solid rgba(239, 68, 68, 0.3);
            border-radius: 6px;
            padding: 2px 8px;
            font-size: 0.74rem;
            font-weight: 700;
        }

        .target-metric-box {
            background: linear-gradient(135deg, rgba(24, 34, 53, 0.7) 0%, rgba(15, 23, 42, 0.9) 100%);
            border: 1px solid rgba(99, 102, 241, 0.25);
            border-radius: 12px;
            padding: 16px;
        }

        .filter-panel-box {
            background: rgba(18, 26, 43, 0.7);
            border: 1px solid var(--scada-border);
            border-radius: 12px;
            padding: 16px 20px;
            margin-bottom: 16px;
        }

        .filter-active-status {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: rgba(24, 34, 53, 0.7);
            border: 1px solid var(--scada-border-cyan);
            border-radius: 8px;
            padding: 6px 14px;
            font-size: 0.82rem;
            color: var(--scada-text-secondary);
            margin-top: 8px;
        }
        .filter-active-val {
            color: var(--sys-cyan);
            font-weight: 600;
            font-family: 'JetBrains Mono', monospace;
        }

        /* ==========================================================================
           8. STREAMLIT FORM, BUTTON & TAB CUSTOMIZATION
           ========================================================================== */
        .stTabs [data-baseweb="tab-list"] {
            gap: 6px;
            background-color: rgba(15, 23, 42, 0.7);
            padding: 5px;
            border-radius: 10px;
            border: 1px solid var(--scada-border);
        }

        .stTabs [data-baseweb="tab"] {
            height: 38px;
            border-radius: 8px;
            color: var(--scada-text-secondary) !important;
            font-weight: 500;
            font-size: 0.88rem;
            padding: 0 16px;
            border: none !important;
            background-color: transparent;
            transition: all 0.2s ease;
        }

        .stTabs [aria-selected="true"] {
            background-color: #1E293B !important;
            color: #FFFFFF !important;
            font-weight: 600;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        }

        .stDataFrame {
            border-radius: 10px;
            overflow: hidden;
            border: 1px solid var(--scada-border);
        }

        section[data-testid="stSidebar"] {
            background-color: #0F172A !important;
            border-right: 1px solid var(--scada-border);
        }

        div[data-baseweb="input"], div[data-baseweb="select"] {
            background-color: #1A2234 !important;
            border-color: rgba(255, 255, 255, 0.1) !important;
            border-radius: 8px !important;
            color: #F8FAFC !important;
        }

        button[kind="primary"] {
            background: linear-gradient(135deg, #0284C7 0%, #0369A1 100%) !important;
            color: #FFFFFF !important;
            border: 1px solid rgba(56, 189, 248, 0.4) !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            box-shadow: 0 4px 14px rgba(2, 132, 199, 0.35) !important;
            transition: all 0.2s ease !important;
        }

        button[kind="primary"]:hover {
            transform: translateY(-1px);
            border-color: var(--sys-cyan) !important;
            box-shadow: 0 6px 20px rgba(2, 132, 199, 0.5) !important;
        }

        button[kind="secondary"] {
            background-color: #1A2234 !important;
            color: #E2E8F0 !important;
            border: 1px solid var(--scada-border) !important;
            border-radius: 8px !important;
            font-weight: 500 !important;
        }

        button[kind="secondary"]:hover {
            background-color: #243048 !important;
            border-color: rgba(255, 255, 255, 0.2) !important;
        }

        /* ==========================================================================
           9. ZERO-FLICKER & ANTI-STALE RENDERING RULES
           ========================================================================== */
        #MainMenu { visibility: hidden !important; }
        footer { visibility: hidden !important; }
        
        header[data-testid="stHeader"] {
            background-color: transparent !important;
            color: var(--scada-text-secondary) !important;
        }

        /* Nút thu gọn / mở rộng Sidebar (Sidebar Collapse/Expand Button) */
        header[data-testid="stHeader"] button,
        [data-testid="stSidebarCollapseButton"] button,
        [data-testid="stSidebarCollapsedControl"] button {
            color: #94A3B8 !important;
            background: rgba(30, 41, 59, 0.6) !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            border-radius: 8px !important;
            transition: all 0.2s ease !important;
        }

        header[data-testid="stHeader"] button:hover,
        [data-testid="stSidebarCollapseButton"] button:hover,
        [data-testid="stSidebarCollapsedControl"] button:hover {
            color: #38BDF8 !important;
            background: rgba(56, 189, 248, 0.15) !important;
            border-color: rgba(56, 189, 248, 0.4) !important;
        }

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

        section[data-testid="stMain"],
        [data-testid="stAppViewContainer"] [data-testid="stMain"],
        [data-testid="stAppViewBlockContainer"],
        [data-testid="stVerticalBlock"],
        [data-testid="stFragment"] {
            opacity: 1 !important;
            filter: none !important;
            transition: none !important;
        }

        div[data-testid="stSkeleton"] {
            opacity: 1 !important;
            filter: none !important;
        }

        [data-testid="stStatusWidget"] {
            display: none !important;
        }

        /* Custom SCADA Scrollbar */
        ::-webkit-scrollbar {
            width: 6px;
            height: 6px;
        }
        ::-webkit-scrollbar-track {
            background: #0B0F17;
        }
        ::-webkit-scrollbar-thumb {
            background: #1E293B;
            border-radius: 4px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: #334155;
        }
    </style>
    """, unsafe_allow_html=True)


def inject_anti_flicker_js():
    """Nhúng MutationObserver JS để gỡ bỏ triệt để class stale và skeleton mờ nhạt"""
    st.markdown("""
    <script>
    (function() {
        const observer = new MutationObserver(function(mutations) {
            document.querySelectorAll('[data-stale="true"]').forEach(function(el) {
                el.removeAttribute('data-stale');
                el.style.opacity = '1';
                el.style.filter = 'none';
            });
        });
        
        observer.observe(document.body, {
            attributes: true,
            attributeFilter: ['data-stale'],
            subtree: true
        });
    })();
    </script>
    """, unsafe_allow_html=True)
