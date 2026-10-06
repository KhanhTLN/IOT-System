import os

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# Định nghĩa bảng màu công nghiệp chuẩn nhận diện 3 thùng phân loại
COLOR_PALETTE = {
    "RED": {
        "name": "Đỏ (RED)",
        "hex": "#F43F5E",
        "glow": "rgba(244, 63, 94, 0.25)",
        "bg": "rgba(244, 63, 94, 0.12)",
        "border": "#FB7185",
        "badge": "🔴 ĐỎ"
    },
    "YELLOW": {
        "name": "Vàng (YELLOW)",
        "hex": "#F59E0B",
        "glow": "rgba(245, 158, 11, 0.25)",
        "bg": "rgba(245, 158, 11, 0.12)",
        "border": "#FBBF24",
        "badge": "🟡 VÀNG"
    },
    "GREEN": {
        "name": "Xanh (GREEN)",
        "hex": "#10B981",
        "glow": "rgba(16, 185, 129, 0.25)",
        "bg": "rgba(16, 185, 129, 0.12)",
        "border": "#34D399",
        "badge": "🟢 XANH"
    }
}

THEME_COLORS = {
    "background": "#0B0F19",
    "surface": "#111827",
    "surface_card": "#1E293B",
    "surface_hover": "#334155",
    "primary": "#6366F1",
    "primary_hover": "#4F46E5",
    "accent_cyan": "#06B6D4",
    "text_main": "#F8FAFC",
    "text_muted": "#94A3B8",
    "border": "rgba(255, 255, 255, 0.08)",
}
