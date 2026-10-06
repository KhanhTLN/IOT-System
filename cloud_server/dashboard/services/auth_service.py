import requests
import streamlit as st
import streamlit.components.v1 as components
from config import API_BASE_URL

def init_session():
    """Khởi tạo cấu trúc Session State"""
    if "token" not in st.session_state:
        st.session_state["token"] = None
    if "user" not in st.session_state:
        st.session_state["user"] = None

def save_token_to_storage(token: str):
    """Lưu JWT Token vào cả Browser Cookie và LocalStorage để F5 không bao giờ bị mất phiên"""
    js_code = f"""
    <script>
        try {{
            localStorage.setItem("iot_auth_token", "{token}");
            document.cookie = "iot_auth_token={token}; path=/; max-age=604800; SameSite=Lax";
        }} catch(e) {{
            console.error("Storage save error:", e);
        }}
    </script>
    """
    components.html(js_code, height=0, width=0)

def clear_token_from_storage():
    """Xóa Token khỏi cả Cookie và LocalStorage khi Logout"""
    js_code = """
    <script>
        try {
            localStorage.removeItem("iot_auth_token");
            document.cookie = "iot_auth_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 UTC;";
        } catch(e) {
            console.error("Storage remove error:", e);
        }
    </script>
    """
    components.html(js_code, height=0, width=0)

def sync_from_local_storage():
    """Tự động khôi phục phiên nếu trình duyệt có lưu token"""
    js_code = """
    <script>
        try {
            const token = localStorage.getItem("iot_auth_token");
            if (token && token !== "null" && token.length > 10) {
                const url = new URL(window.parent.location.href);
                if (url.searchParams.get("auth_token") !== token) {
                    url.searchParams.set("auth_token", token);
                    window.parent.location.href = url.href;
                }
            }
        } catch(e) {
            console.error("Storage sync error:", e);
        }
    </script>
    """
    components.html(js_code, height=0, width=0)

def login_user(username: str, password: str):
    """Gửi yêu cầu đăng nhập lên backend"""
    try:
        res = requests.post(
            f"{API_BASE_URL}/api/v1/auth/login",
            json={"username": username, "password": password},
            timeout=5
        )
        if res.status_code == 200:
            data = res.json()
            st.session_state["token"] = data["access_token"]
            st.session_state["user"] = data["user"]
            save_token_to_storage(data["access_token"])
            return True, data["user"]
        else:
            err = res.json().get("detail", "Sai tên đăng nhập hoặc mật khẩu!")
            return False, err
    except Exception as e:
        return False, f"Không thể kết nối đến Backend: {e}"

def verify_token(token: str):
    """Kiểm tra tính hợp lệ của token"""
    try:
        res = requests.get(
            f"{API_BASE_URL}/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=4
        )
        if res.status_code == 200:
            return True, res.json()
        return False, None
    except Exception:
        return False, None

def logout_user():
    """Xóa sạch phiên đăng nhập và LocalStorage"""
    st.session_state.clear()
    st.query_params.clear()
    clear_token_from_storage()
    st.rerun()
