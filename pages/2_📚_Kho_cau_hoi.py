\
from __future__ import annotations
import streamlit as st
import pandas as pd

from tool.question_bank import load_bank_from_upload, Bank

st.set_page_config(page_title="📚 Kho câu hỏi", layout="wide")
st.title("📚 Kho câu hỏi (bám TT27 — khóa mức 1/2/3)")

st.write("Upload kho câu hỏi dạng **CSV/XLSX**. Tool sẽ kiểm tra cột bắt buộc và tính hợp lệ TT27.")
up = st.file_uploader("Upload kho câu hỏi", type=["csv","xlsx","xls"])

if up is None:
    st.info("Bạn có thể dùng file mẫu ở `data/sample_question_bank.csv` để thử.")
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

st.success("Kho câu hỏi hợp lệ.")
st.session_state["bank"] = bank

st.subheader("Xem nhanh dữ liệu")
st.dataframe(bank.df.head(200), use_container_width=True)

# Coverage
meta = st.session_state.get("matrix_meta", {"grade":3,"subject":"Tin","semester":"HK1"})
grade = int(meta.get("grade", 3))
subject = str(meta.get("subject", "Tin"))
semester = str(meta.get("semester", "HK1"))

st.subheader("Coverage theo (chủ đề, bài, dạng, mức)")
cov = bank.coverage_counts(grade, subject, semester)
st.dataframe(cov.sort_values(["topic","lesson","qtype","tt27_level"]), use_container_width=True)

st.info("Gợi ý: nếu ma trận yêu cầu nhiều câu ở một ô nhưng coverage thấp, trang 📝 Tạo đề sẽ báo thiếu đúng ô (không bù mức).")
