import streamlit as st
from services.auth_service import login_user

def render_login_view():
    """Giao diện đăng nhập chuẩn SCADA Cloud"""
    # Căn giữa trang đăng nhập
    _, center_col, _ = st.columns([1, 1.6, 1])

    with center_col:
        st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)
        
        # Header Card
        st.markdown("""
        <div style="text-align: center; margin-bottom: 28px;">
            <div style="display: inline-flex; align-items: center; justify-content: center; width: 64px; height: 64px; background: linear-gradient(135deg, rgba(99,102,241,0.2) 0%, rgba(56,189,248,0.2) 100%); border: 1px solid rgba(99,102,241,0.4); border-radius: 20px; font-size: 2rem; margin-bottom: 16px; box-shadow: 0 0 30px rgba(99,102,241,0.25);">
                🏭
            </div>
            <h1 class="app-title-gradient" style="font-size: 1.9rem; margin-bottom: 6px;">IoT Sorting Factory</h1>
            <p style="color: #94A3B8; font-size: 0.95rem; margin: 0;">
                Hệ thống giám sát phân loại & điều khiển dây chuyền (SCADA Level 4)
            </p>
        </div>
        """, unsafe_allow_html=True)

        with st.container():
            st.markdown("""
            <div style="background: rgba(17, 24, 39, 0.85); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 18px; padding: 28px; box-shadow: 0 16px 40px rgba(0,0,0,0.4);">
                <div style="font-weight: 600; font-size: 1.15rem; color: #F8FAFC; margin-bottom: 18px; display: flex; align-items: center; gap: 8px;">
                    <span>🔐</span> Đăng Nhập Hệ Thống
                </div>
            """, unsafe_allow_html=True)

            with st.form("login_form_secure"):
                username = st.text_input("Tên đăng nhập", placeholder="Nhập username (admin / worker)...")
                password = st.text_input("Mật khẩu", type="password", placeholder="Nhập mật khẩu...")
                
                st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                submit_btn = st.form_submit_button("🚀 Đăng Nhập", use_container_width=True)

                if submit_btn:
                    if not username or not password:
                        st.error("⚠️ Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu!")
                    else:
                        success, result = login_user(username, password)
                        if success:
                            st.success(f"Chào mừng {result.get('full_name', username)}!")
                            st.rerun()
                        else:
                            st.error(f"❌ {result}")

            st.markdown("""
                <div style="margin-top: 24px; padding-top: 18px; border-top: 1px solid rgba(255,255,255,0.06);">
                    <div style="font-size: 0.82rem; color: #64748B; font-weight: 500; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 0.04em;">
                        💡 Đăng nhập nhanh tài khoản mẫu:
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Nút đăng nhập nhanh
            col_worker, col_manager = st.columns(2)
            with col_worker:
                if st.button("👨‍🔧 Công Nhân (Worker)", use_container_width=True):
                    success, res = login_user("worker", "worker123")
                    if success:
                        st.rerun()
                    else:
                        st.error(res)
            with col_manager:
                if st.button("👔 Quản Lý (Manager)", use_container_width=True):
                    success, res = login_user("admin", "admin123")
                    if success:
                        st.rerun()
                    else:
                        st.error(res)
