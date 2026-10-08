import os

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# Định nghĩa bảng màu công nghiệp chuẩn nhận diện 3 thùng phân loại (Desaturated Industrial SCADA)
COLOR_PALETTE = {
    "RED": {
        "name": "Đỏ (RED)",
        "hex": "#FB7185",
        "glow": "rgba(251, 113, 133, 0.25)",
        "bg": "rgba(251, 113, 133, 0.12)",
        "border": "#FB7185",
        "badge": "🔴 ĐỎ"
    },
    "YELLOW": {
        "name": "Vàng (YELLOW)",
        "hex": "#FBBF24",
        "glow": "rgba(251, 191, 36, 0.25)",
        "bg": "rgba(251, 191, 36, 0.12)",
        "border": "#FBBF24",
        "badge": "🟡 VÀNG"
    },
    "GREEN": {
        "name": "Xanh (GREEN)",
        "hex": "#34D399",
        "glow": "rgba(52, 211, 153, 0.25)",
        "bg": "rgba(52, 211, 153, 0.12)",
        "border": "#34D399",
        "badge": "🟢 XANH"
    }
}

# Bảng màu tín hiệu kỹ thuật & trạng thái hệ thống SCADA (Tách rời với màu sản phẩm)
TECHNICAL_STATUS_COLORS = {
    "critical": "#EF4444",        # Dừng khẩn / Lỗi / Kẹt mẻ
    "warning": "#F59E0B",         # Cảnh báo / Hao mòn cao
    "healthy": "#10B981",         # Hoạt động tốt / Đạt chuẩn
    "live_feed": "#38BDF8",       # Luồng dữ liệu trực tiếp / Cyan
    "neutral": "#64748B",         # Trạng thái tĩnh / Muted
}

THEME_COLORS = {
    "background": "#0B0F17",      # Deep Slate (Chống mỏi mắt)
    "surface": "rgba(18, 26, 43, 0.85)", # Glass Card
    "surface_card": "#121A2B",
    "surface_hover": "rgba(30, 41, 59, 0.95)",
    "primary": "#38BDF8",         # Cyan Neon
    "primary_hover": "#0284C7",
    "accent_indigo": "#6366F1",
    "text_main": "#F8FAFC",
    "text_secondary": "#94A3B8",
    "text_muted": "#64748B",
    "border": "rgba(255, 255, 255, 0.08)",
    "border_highlight": "rgba(56, 189, 248, 0.4)",
}
