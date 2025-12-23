\
from __future__ import annotations
import os
import streamlit as st
import pandas as pd

from tool.utils import QTYPE_ORDER, LEVEL_ORDER, safe_int, round_to_step
from tool.matrix_template import load_matrix_template, MatrixTemplate, LessonRow
from tool.question_bank import Bank
from tool.generation import build_slots, assign_questions, slot_map_to_numbers
from tool.export_docx import export_spec_from_template, export_exam_docx

st.set_page_config(page_title="📝 Tạo đề & Xuất Word", layout="wide")
st.title("📝 Tạo đề & Xuất Word")

meta = st.session_state.get("matrix_meta")
matrix_df = st.session_state.get("matrix_df")
pts = st.session_state.get("points_per_qtype")

if meta is None or matrix_df is None or pts is None:
    st.warning("Bạn cần vào trang 🧩 Ma trận và bấm 'Lưu vào session' trước.")
    st.stop()

bank: Bank | None = st.session_state.get("bank")
if bank is None:
    st.warning("Bạn cần upload kho câu hỏi ở trang 📚 Kho câu hỏi trước.")
    st.stop()

grade = int(meta["grade"])
subject = str(meta["subject"])
semester = str(meta["semester"])
total_points = float(meta["total_points"])

st.subheader("1) Tạo slot từ ma trận (khóa mức TT27)")
seed = st.number_input("Seed (để tạo đề tái lập / đổi đề)", min_value=1, max_value=10_000_000, value=42, step=1)

# Rebuild MatrixTemplate from matrix_df
lessons = []
for _, r in matrix_df.iterrows():
    # skip totals-like rows if any (our grid excludes pinned rows, but keep safe)
    if str(r.get("Chủ đề","")).strip().upper() == "TỔNG":
        continue
    tt_val = r.get("TT")
    try:
        tt = int(tt_val)
    except Exception:
        continue
    counts = {}
    for qtype in QTYPE_ORDER:
        for level in LEVEL_ORDER:
            counts[(qtype, level)] = safe_int(r.get(f"{qtype}_M{level}"), 0)
    lessons.append(LessonRow(
        tt=tt,
        topic=str(r.get("Chủ đề","")),
        lesson=str(r.get("Bài/Nội dung","")),
        periods=safe_int(r.get("Số tiết"), 0),
        ratio_pct=float(r.get("Tỉ lệ %") or 0),
        points_target=float(r.get("Điểm cần đạt") or 0),
        counts=counts
    ))

matrix = MatrixTemplate(
    title=str(meta["title"]),
    grade=grade,
    subject=subject,
    semester=semester,
    lessons=lessons,
    points_per_qtype=pts,
    total_points=total_points
)

slots = build_slots(matrix, pts)
st.write(f"Tổng số slot (tổng câu): **{len(slots)}**")

slots, warnings = assign_questions(slots, bank, grade, subject, semester, seed=int(seed))

if warnings:
    st.error("Thiếu câu đúng ô (tool KHÔNG bù mức khác):")
    for w in warnings[:50]:
        st.write(f"- {w}")
    if len(warnings) > 50:
        st.write(f"... và {len(warnings)-50} cảnh báo nữa.")
else:
    st.success("Đủ câu cho tất cả ô theo ma trận.")

st.subheader("2) Xem trước đề (có khóa mức)")
# Show preview table
preview = pd.DataFrame([{
    "Câu": s.qno,
    "Chủ đề": s.topic,
    "Bài": s.lesson,
    "Dạng": s.qtype,
    "Mức(TT27)": s.level,
    "Điểm": s.points,
    "question_id": s.question_id or "(thiếu)",
} for s in slots])
st.dataframe(preview, use_container_width=True, height=360)

st.subheader("3) Xuất Word")
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")
spec_template = os.path.join(TEMPLATE_DIR, "đặc tả.docx")
out_dir = os.path.join(os.path.dirname(__file__), "..", "outputs")
os.makedirs(out_dir, exist_ok=True)

col1, col2 = st.columns(2)
with col1:
    if st.button("Xuất Bảng đặc tả (docx)"):
        try:
            out_path = os.path.join(out_dir, "Bang_dac_ta.docx")
            export_spec_from_template(
                template_docx_path=spec_template,
                output_path=out_path,
                matrix=matrix,
                slots=slots,
                points_per_qtype=pts,
                total_points=total_points
            )
            with open(out_path, "rb") as f:
                st.download_button("Tải Bang_dac_ta.docx", f, file_name="Bang_dac_ta.docx")
            st.success("Đã xuất Bảng đặc tả.")
        except Exception as e:
            st.error(f"Lỗi xuất đặc tả: {e}")

with col2:
    if st.button("Xuất Đề (docx)"):
        try:
            out_path = os.path.join(out_dir, "De.docx")
            export_exam_docx(
                output_path=out_path,
                slots=slots,
                bank_df=bank.df,
                title=matrix.title,
                total_points=total_points
            )
            with open(out_path, "rb") as f:
                st.download_button("Tải De.docx", f, file_name="De.docx")
            st.success("Đã xuất Đề.")
        except Exception as e:
            st.error(f"Lỗi xuất đề: {e}")
