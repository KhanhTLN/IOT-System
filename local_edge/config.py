import os
import numpy as np
from pathlib import Path
from dotenv import load_dotenv

# Tự động tìm nạp file .env từ thư mục gốc hoặc thư mục hiện tại
env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

# ==========================================
# 1. CAMERA & VIDEO CONFIGURATION
# ==========================================
# 0: Webcam mặc định, hoặc đường dẫn file video "test_video.mp4"
CAMERA_SOURCE = int(os.getenv("CAMERA_ID", "0")) if os.getenv("CAMERA_ID", "0").isdigit() else os.getenv("CAMERA_ID", "0")
FRAME_WIDTH = int(os.getenv("FRAME_WIDTH", "640"))
FRAME_HEIGHT = int(os.getenv("FRAME_HEIGHT", "480"))
FPS_LIMIT = int(os.getenv("FPS_LIMIT", "30"))

# ==========================================
# 2. HSV COLOR THRESHOLDS (Mặt nạ màu sắc)
# ==========================================
# Không gian màu HSV trong OpenCV: H: 0-179, S: 0-255, V: 0-255
COLOR_THRESHOLDS = {
    "RED": [
        # Màu đỏ trải ở cả 2 đầu dải Hue (0-10 và 160-179)
        {"lower": np.array([0, 120, 70]), "upper": np.array([10, 255, 255])},
        {"lower": np.array([160, 120, 70]), "upper": np.array([179, 255, 255])}
    ],
    "YELLOW": [
        {"lower": np.array([15, 100, 100]), "upper": np.array([35, 255, 255])}
    ],
    "GREEN": [
        {"lower": np.array([36, 60, 60]), "upper": np.array([85, 255, 255])}
    ]
}

# Màu sắc hiển thị BGR trên khung hình giao diện OpenCV
DISPLAY_COLORS = {
    "RED": (0, 0, 255),       # Đỏ BGR
    "YELLOW": (0, 220, 255),   # Vàng BGR
    "GREEN": (0, 255, 0),     # Xanh lá BGR
    "TEXT": (255, 255, 255),   # Trắng
    "ROI_LINE": (255, 165, 0) # Cam ROI
}

# ==========================================
# 3. DETECTION & TRIGGER CONFIGURATION
# ==========================================
# Diện tích contour tối thiểu để coi là vật thể hợp lệ (tránh nhiễu hạt)
MIN_CONTOUR_AREA = int(os.getenv("MIN_CONTOUR_AREA", "1200"))

# Vùng nhận diện ROI (Tọa độ tỷ lệ theo khung hình: [ymin, ymax, xmin, xmax])
# Mặc định vùng trung tâm băng chuyền
ROI_X_START = 0.20
ROI_X_END = 0.80
ROI_Y_START = 0.25
ROI_Y_END = 0.75

# Thời gian nghỉ chống kích hoạt trùng lặp cho cùng 1 vật thể (Debounce Cooldown tính bằng giây)
TRIGGER_COOLDOWN_SECONDS = float(os.getenv("TRIGGER_COOLDOWN_SECONDS", "2.0"))

# ==========================================
# 4. MQTT BROKER CONFIGURATION
# ==========================================
MQTT_BROKER = os.getenv("MQTT_BROKER", "broker.hivemq.com")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_SERVO_TOPIC = os.getenv("MQTT_SERVO_TOPIC", "factory/servo/control")
MQTT_STATUS_TOPIC = os.getenv("MQTT_STATUS_TOPIC", "factory/edge/status")
MQTT_CLIENT_ID = os.getenv("MQTT_CLIENT_ID", "iot_edge_cv_detector")

# ==========================================
# 5. CLOUD BACKEND REST API CONFIGURATION
# ==========================================
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_LOGS_ENDPOINT = f"{API_BASE_URL}/api/v1/logs"
HTTP_TIMEOUT_SECONDS = float(os.getenv("HTTP_TIMEOUT_SECONDS", "2.5"))
