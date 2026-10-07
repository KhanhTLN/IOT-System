import requests
import streamlit as st
from config import API_BASE_URL
from services.auth_service import logout_user

def get_headers(use_auth=True):
    headers = {"Content-Type": "application/json"}
    token = st.session_state.get("token")
    if use_auth and token:
        headers["Authorization"] = f"Bearer {token}"
    return headers

def request_api(method: str, endpoint: str, json_data=None, params=None, use_auth=True, raw_response=False):
    """Thực hiện HTTP request an toàn và xử lý mã trạng thái"""
    url = f"{API_BASE_URL}{endpoint}"
    headers = get_headers(use_auth)
    try:
        if method == "GET":
            res = requests.get(url, headers=headers, params=params, timeout=5)
        elif method == "POST":
            res = requests.post(url, headers=headers, json=json_data, timeout=5)
        else:
            return None

        # Tự động Logout nếu Token hết hạn (401)
        if res.status_code == 401 and use_auth:
            logout_user()
            return None

        if raw_response:
            return res

        return res
    except Exception as e:
        print(f"[API Client Error] {method} {endpoint}: {e}")
        return None

def fetch_stats(start_time=None, end_time=None, shift=None):
    """Lấy dữ liệu thống kê Level 4 từ Backend với bộ lọc tùy chọn"""
    params = {}
    if start_time:
        params["start_time"] = str(start_time)
    if end_time:
        params["end_time"] = str(end_time)
    if shift and shift not in ["ALL", "TAT_CA", ""]:
        params["shift"] = str(shift)
        
    res = request_api("GET", "/api/v1/stats", params=params, use_auth=False)
    if res and res.status_code == 200:
        return res.json()
    return {}

def fetch_logs(limit=50, offset=0, color_label=None, start_time=None, end_time=None, shift=None):
    """Lấy danh sách lịch sử phân loại với bộ lọc màu sắc, thời gian và ca"""
    params = {"limit": limit, "offset": offset}
    if color_label and color_label not in ["ALL", "TAT_CA", ""]:
        params["color_label"] = str(color_label)
    if start_time:
        params["start_time"] = str(start_time)
    if end_time:
        params["end_time"] = str(end_time)
    if shift and shift not in ["ALL", "TAT_CA", ""]:
        params["shift"] = str(shift)

    res = request_api("GET", "/api/v1/logs", params=params, use_auth=False)
    if res and res.status_code == 200:
        return res.json()
    return []

def fetch_servo_health(max_rated_cycles=10000):
    """Lấy dữ liệu phân tích sức khỏe và vòng đời động cơ Servo SG90"""
    res = request_api("GET", f"/api/v1/analytics/servo-health?max_rated_cycles={max_rated_cycles}", use_auth=False)
    if res and res.status_code == 200:
        return res.json()
    return {}

def fetch_configs():
    """Lấy cấu hình hệ thống (ngưỡng bất thường, góc servo)"""
    res = request_api("GET", "/api/v1/config", use_auth=False)
    if res and res.status_code == 200:
        return res.json()
    return {}

def update_config_value(key: str, value: str):
    """Cập nhật cấu hình hệ thống (Chỉ MANAGER)"""
    res = request_api("POST", "/api/v1/config", json_data={"key": key, "value": str(value)}, use_auth=True)
    return res and res.status_code == 200

def fetch_all_users():
    """Lấy danh sách toàn bộ tài khoản (Chỉ MANAGER)"""
    res = request_api("GET", "/api/v1/users", use_auth=True)
    if res and res.status_code == 200:
        return res.json()
    return []

def create_user_account(username, password, full_name, role):
    """Tạo mới tài khoản người dùng (Chỉ MANAGER)"""
    res = request_api("POST", "/api/v1/auth/register", json_data={
        "username": username,
        "password": password,
        "full_name": full_name,
        "role": role
    }, use_auth=True)
    if res and res.status_code == 201:
        return True, "Tạo tài khoản thành công!"
    err = res.json().get("detail", "Lỗi tạo tài khoản") if res else "Không thể kết nối Backend"
    return False, err

def export_logs_csv_data():
    """Tải file báo cáo CSV từ Backend (Chỉ MANAGER)"""
    res = request_api("GET", "/api/v1/export/csv", use_auth=True, raw_response=True)
    if res and res.status_code == 200:
        return res.content
    return None
