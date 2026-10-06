import sys
import os
import streamlit as st

# Thêm đường dẫn dashboard vào sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from styles import inject_custom_styles, inject_anti_flicker_js
from services.auth_service import (
    init_session, sync_from_local_storage,
    verify_token, clear_token_from_storage
)
from views.login_view import render_login_view
from views.worker_view import render_worker_view
from views.manager_view import render_manager_view

# Cấu hình Trang Streamlit
st.set_page_config(
    page_title="IoT Factory SCADA Dashboard",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 1. Nhúng toàn bộ Theme CSS cao cấp & Anti-Flicker Observer
inject_custom_styles()
inject_anti_flicker_js()


# 2. Khởi tạo Session State
init_session()

# 3. Phục hồi phiên đăng nhập tức thì từ Cookie trình duyệt hoặc Query Param khi F5
if not st.session_state.get("token"):
    cookie_token = st.context.cookies.get("iot_auth_token") if hasattr(st, "context") and hasattr(st.context, "cookies") else None
    url_token = st.query_params.get("auth_token")
    
    token_to_verify = cookie_token or url_token
    if token_to_verify:
        is_valid, user_data = verify_token(token_to_verify)
        if is_valid:
            st.session_state["token"] = token_to_verify
            st.session_state["user"] = user_data
            st.query_params["page"] = "dashboard"
            st.query_params.pop("auth_token", None)
        else:
            clear_token_from_storage()
            st.query_params["page"] = "login"
            st.query_params.pop("auth_token", None)

# 4. Điều hướng trạng thái màn hình (URL Sync: ?page=login vs ?page=dashboard)
if not st.session_state.get("token"):
    st.query_params["page"] = "login"
    sync_from_local_storage()
    render_login_view()
    st.stop()

# Đảm bảo URL khi đã đăng nhập luôn là ?page=dashboard
st.query_params["page"] = "dashboard"

# 5. Phân quyền hiển thị màn hình Dashboard (Level 4 RBAC)
current_user = st.session_state.get("user", {})
user_role = str(current_user.get("role", "WORKER")).upper()

if user_role == "MANAGER":
    render_manager_view()
else:
    render_worker_view()

