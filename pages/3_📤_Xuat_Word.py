from __future__ import annotations
import os
import streamlit as st

from tool.ui_common import inject_css, sidebar_settings
from tool.matrix_template import load_matrix_template
from tool.generation import DraftItem
from tool.export_docx import export_spec_from_template, export_exam_docx

st.set_page_config(page_title="📤 Xuất Word", layout="wide")
inject_css()
sidebar_settings()

st.markdown("## 📤 Xuất Word (Đề + Bảng đặc tả)")

meta = st.session_state.get("matrix_meta")
items = st.session_state.get("draft_items", [])
bank = st.session_state.get("bank")

if meta is None:
    st.warning("Hãy vào trang 🧩 Ma trận & Soạn đề để chọn Lớp/Môn và template trước.")
    st.stop()

if not items:
    st.warning("Chưa có câu trong 'Đề hiện tại'. Hãy thêm câu hoặc sinh slot theo ma trận.")
    st.stop()

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")
docx_files = [f for f in os.listdir(TEMPLATE_DIR) if f.lower().endswith(".docx")]
if not docx_files:
    st.error("Không thấy template Word trong templates/.")
    st.stop()

st.markdown("### Chọn template Word (ẩn đường dẫn)")
spec_name = st.selectbox("Template Bảng đặc tả", docx_files, index=0)
spec_path = os.path.join(TEMPLATE_DIR, spec_name)

xlsx_path = os.path.join(TEMPLATE_DIR, meta["xlsx_name"])
matrix = load_matrix_template(xlsx_path, total_points=float(meta["total_points"]), step=0.25)

out_dir = os.path.join(os.path.dirname(__file__), "..", "outputs")
os.makedirs(out_dir, exist_ok=True)

col1, col2 = st.columns(2)
with col1:
    if st.button("Xuất Bảng đặc tả.docx", type="primary", use_container_width=True):
        try:
            out_path = os.path.join(out_dir, "Bang_dac_ta.docx")
            draft_objs = [DraftItem(**x) for x in items]
            export_spec_from_template(spec_path, out_path, matrix, draft_objs, total_points=float(meta["total_points"]))
            with open(out_path, "rb") as f:
                st.download_button("⬇️ Tải Bang_dac_ta.docx", f, file_name="Bang_dac_ta.docx", use_container_width=True)
            st.success("Đã xuất Bảng đặc tả.")
        except Exception as e:
            st.error(f"Lỗi xuất đặc tả: {e}")

with col2:
    if st.button("Xuất De.docx", use_container_width=True):
        if bank is None:
            st.error("Chưa có kho câu hỏi. Vào trang 📚 để upload.")
        else:
            try:
                out_path = os.path.join(out_dir, "De.docx")
                draft_objs = [DraftItem(**x) for x in items]
                title = str(meta.get("title","ĐỀ KIỂM TRA"))
                df = bank.filtered(int(meta["grade"]), meta["subject"], meta["semester"])
                export_exam_docx(out_path, draft_objs, df, title=title, total_points=float(meta["total_points"]))
                with open(out_path, "rb") as f:
                    st.download_button("⬇️ Tải De.docx", f, file_name="De.docx", use_container_width=True)
                st.success("Đã xuất Đề.")
            except Exception as e:
                st.error(f"Lỗi xuất đề: {e}")
