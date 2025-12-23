from __future__ import annotations
import streamlit as st
from tool.ui_common import inject_css, sidebar_settings

st.set_page_config(page_title="Tool ra đề theo ma trận (TT27)", layout="wide")
inject_css()
sidebar_settings()

st.markdown('<div class="app-card">', unsafe_allow_html=True)
st.markdown("## 🧩 Tool ra đề theo ma trận (TT27)")
st.markdown('<div class="muted">Luồng chuẩn: <b>Chọn Lớp/Môn</b> → (dòng ngang) <b>Chủ đề–Bài–YCCĐ–Dạng/Mức–Điểm–Thêm</b> → xem trước → xuất <b>Đề</b> + <b>Bảng đặc tả</b>.</div>', unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

st.markdown("### Bạn làm theo thứ tự")
st.markdown("1) **🧩 Ma trận & Soạn đề**: chọn lớp/môn, xem ma trận, thêm câu theo dòng ngang hoặc sinh slot theo ma trận  \n"
            "2) **📚 Kho câu hỏi**: upload dữ liệu câu hỏi (không AI)  \n"
            "3) **📤 Xuất Word**: xuất Đề + Bảng đặc tả theo template")

st.info("Ghi chú: API AI Studio chỉ để sẵn (chưa dùng). Mức độ TT27 bị khóa cứng: Biết=M1, Hiểu=M2, VD=M3.")
