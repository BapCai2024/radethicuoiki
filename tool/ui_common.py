from __future__ import annotations
import streamlit as st

def inject_css() -> None:
    st.markdown(
        '''
        <style>
          .block-container { padding-top: 1.25rem; padding-bottom: 2rem; }
          .app-card {
            background: #ffffff;
            border: 1px solid rgba(15,23,42,0.08);
            border-radius: 16px;
            padding: 16px 16px 8px 16px;
            box-shadow: 0 6px 20px rgba(15,23,42,0.04);
          }
          .muted { color: rgba(15,23,42,0.65); font-size: 0.95rem; }
          .pill {
            display:inline-block; padding:4px 10px; border-radius:999px;
            border: 1px solid rgba(15,23,42,0.12); background:#f6f7fb;
            margin-right:6px; font-size: 12px;
          }
          .danger { color: #b91c1c; }
          .ok { color: #166534; }
        </style>
        ''',
        unsafe_allow_html=True,
    )

def sidebar_settings() -> None:
    st.sidebar.markdown("## ⚙️ Cấu hình")
    with st.sidebar.expander("🔑 AI Studio (chưa dùng, để sẵn)", expanded=False):
        st.caption("Chưa gọi AI. Chỉ lưu key để chuẩn bị triển khai sau.")
        key = st.text_input("API Key", type="password", value=st.session_state.get("ai_api_key", ""))
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Lưu key", use_container_width=True):
                st.session_state["ai_api_key"] = key.strip()
                st.success("Đã lưu (tạm trong session).")
        with col2:
            if st.button("Check", use_container_width=True):
                if not key.strip():
                    st.error("Chưa nhập key.")
                elif len(key.strip()) < 10:
                    st.warning("Key có vẻ quá ngắn (kiểm tra lại).")
                else:
                    st.success("OK (đã có key, chưa gọi API).")

    st.sidebar.markdown("---")
    st.sidebar.caption("TT27: Biết=M1 • Hiểu=M2 • VD=M3 (khóa mức)")
