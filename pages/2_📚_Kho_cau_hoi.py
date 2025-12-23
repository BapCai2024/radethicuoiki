from __future__ import annotations
import streamlit as st
from tool.ui_common import inject_css, sidebar_settings
from tool.question_bank import load_bank_from_upload

st.set_page_config(page_title="📚 Kho câu hỏi", layout="wide")
inject_css()
sidebar_settings()

st.markdown("## 📚 Kho câu hỏi")
st.markdown('<div class="muted">Upload CSV/XLSX. Tool sẽ kiểm tra cột bắt buộc và mức TT27 (1/2/3).</div>', unsafe_allow_html=True)

up = st.file_uploader("Upload kho câu hỏi", type=["csv","xlsx","xls"])
if up is None:
    st.info("Bạn có thể test nhanh bằng file mẫu: data/sample_question_bank.csv")
    st.stop()

try:
    bank = load_bank_from_upload(up)
except Exception as e:
    st.error(f"Lỗi đọc file: {e}")
    st.stop()

ok, errs = bank.validate()
if not ok:
    st.error("Kho câu hỏi chưa đạt yêu cầu:")
    for er in errs:
        st.write(f"- {er}")
    st.stop()

st.session_state["bank"] = bank
st.success("✅ Kho câu hỏi hợp lệ và đã nạp vào hệ thống.")

meta = st.session_state.get("matrix_meta")
if meta:
    st.caption(f"Đang lọc theo: Lớp {meta['grade']} • {meta['subject']} • {meta['semester']}")
    df = bank.filtered(int(meta["grade"]), meta["subject"], meta["semester"])
else:
    df = bank.df.copy()

st.subheader("Xem nhanh (200 dòng đầu)")
st.dataframe(df.head(200), use_container_width=True, height=420)
