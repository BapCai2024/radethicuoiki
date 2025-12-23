\
from __future__ import annotations
import os
import streamlit as st
import pandas as pd

from tool.matrix_template import load_matrix_template
from tool.question_bank import Bank
from tool.generation import build_slots, assign_questions

st.set_page_config(page_title="🧪 Tự kiểm tra", layout="wide")
st.title("🧪 Tự kiểm tra (để giảm lỗi khi chạy thật)")

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")
default_xlsx = os.path.join(TEMPLATE_DIR, "MA TRẬN - bảng dặc tả TIN 3 HK1.xlsx")

st.write("Trang này chạy các kiểm tra cơ bản: đọc ma trận, tạo slot, khóa mức TT27, và (nếu có kho câu hỏi) kiểm tra thiếu câu.")

xlsx_path = st.text_input("Template ma trận", default_xlsx)
if not os.path.exists(xlsx_path):
    st.error("Không thấy file ma trận.")
    st.stop()

tmpl = load_matrix_template(xlsx_path, total_points=10.0, step=0.25)
st.success(f"Đọc ma trận OK: {len(tmpl.lessons)} bài")

pts = st.session_state.get("points_per_qtype", tmpl.points_per_qtype)
slots = build_slots(tmpl, pts)
st.info(f"Tạo slot OK: tổng {len(slots)} câu")

bank: Bank | None = st.session_state.get("bank")
if bank is None:
    st.warning("Chưa có kho câu hỏi (upload ở trang 📚). Bỏ qua kiểm tra coverage.")
    st.stop()

grade = tmpl.grade or 3
subject = tmpl.subject or "Tin"
semester = tmpl.semester or "HK1"
slots2, warnings = assign_questions(slots, bank, grade, subject, semester, seed=123)

if warnings:
    st.error(f"Thiếu {len(warnings)} câu đúng mức (KHÔNG bù).")
    st.write("Ví dụ 20 cảnh báo đầu:")
    for w in warnings[:20]:
        st.write("- " + w)
else:
    st.success("Kho câu hỏi đủ coverage cho ma trận mẫu.")

st.write("Nếu trang này OK mà trang tạo đề vẫn lỗi, khả năng cao là do dữ liệu upload có định dạng lạ hoặc template Word khác.")
