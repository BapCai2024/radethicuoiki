\
from __future__ import annotations
import os
import streamlit as st
import pandas as pd

from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode
from tool.matrix_template import load_matrix_template, QTYPE_LABELS_VI, QTYPE_COLS
from tool.utils import QTYPE_ORDER, LEVEL_ORDER, round_to_step, safe_int

st.set_page_config(page_title="🧩 Ma trận", layout="wide")
st.title("🧩 Ma trận (giống Excel) — GV điền số câu theo ô")

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")
default_xlsx = os.path.join(TEMPLATE_DIR, "MA TRẬN - bảng dặc tả TIN 3 HK1.xlsx")

colA, colB = st.columns([2,1])
with colA:
    xlsx_path = st.text_input("Đường dẫn template ma trận (Excel)", default_xlsx)
with colB:
    total_points = st.number_input("Tổng điểm đề", min_value=1.0, max_value=20.0, value=10.0, step=0.25)

if not os.path.exists(xlsx_path):
    st.error("Không tìm thấy file Excel template. Hãy kiểm tra đường dẫn.")
    st.stop()

tmpl = load_matrix_template(xlsx_path, total_points=float(total_points), step=0.25)

st.subheader("Cài đặt điểm/1 câu (bước 0,25)")
pcols = st.columns(5)
pts = st.session_state.get("points_per_qtype", tmpl.points_per_qtype.copy())

def stepper(label, key, default):
    v = st.number_input(label, min_value=0.0, max_value=10.0, value=float(default), step=0.25, key=key)
    return round_to_step(v, 0.25)

with pcols[0]:
    pts["MCQ"] = stepper("MCQ (Nhiều lựa chọn)", "pts_mcq", pts.get("MCQ", 0.25))
with pcols[1]:
    pts["TF"] = stepper("Đúng-Sai", "pts_tf", pts.get("TF", 0.25))
with pcols[2]:
    pts["MATCH"] = stepper("Nối cột", "pts_match", pts.get("MATCH", 0.5))
with pcols[3]:
    pts["FILL"] = stepper("Điền khuyết", "pts_fill", pts.get("FILL", 0.25))
with pcols[4]:
    pts["ESSAY"] = stepper("Tự luận", "pts_essay", pts.get("ESSAY", 0.5))

st.session_state["points_per_qtype"] = pts

# Build dataframe for grid
rows = []
for lr in tmpl.lessons:
    row = {
        "TT": lr.tt,
        "Chủ đề": lr.topic,
        "Bài/Nội dung": lr.lesson,
        "Số tiết": lr.periods,
        "Tỉ lệ %": round(lr.ratio_pct, 1),
        "Điểm cần đạt": round(lr.points_target, 2),
    }
    for qtype in QTYPE_ORDER:
        for level in LEVEL_ORDER:
            key = f"{qtype}_M{level}"
            row[key] = int(lr.counts.get((qtype, level), 0))
    rows.append(row)

df = pd.DataFrame(rows)

# Totals row
totals = {"TT": "", "Chủ đề": "TỔNG", "Bài/Nội dung": "", "Số tiết": df["Số tiết"].sum(), "Tỉ lệ %": 100.0, "Điểm cần đạt": round(float(total_points),2)}
for qtype in QTYPE_ORDER:
    for level in LEVEL_ORDER:
        col = f"{qtype}_M{level}"
        totals[col] = int(df[col].sum())

# Points-per-question row (display only)
ptsrow = {"TT": "", "Chủ đề": "", "Bài/Nội dung": "Điểm/1 câu (bước 0,25)", "Số tiết": "", "Tỉ lệ %": "", "Điểm cần đạt": ""}
for qtype in QTYPE_ORDER:
    for level in LEVEL_ORDER:
        ptsrow[f"{qtype}_M{level}"] = float(pts.get(qtype, 0.25))

# Compute total points from counts
def compute_total_points(df_counts: pd.DataFrame) -> float:
    total = 0.0
    for qtype in QTYPE_ORDER:
        qsum = 0
        for level in LEVEL_ORDER:
            qsum += int(df_counts[f"{qtype}_M{level}"].sum())
        total += qsum * float(pts.get(qtype, 0.25))
    return float(total)

calc_total = compute_total_points(df)

# Alerts
alerts = []
if abs(calc_total - float(total_points)) > 1e-6:
    diff = calc_total - float(total_points)
    if diff > 0:
        alerts.append(f"Vượt tổng điểm: +{diff:.2f}")
    else:
        alerts.append(f"Thiếu tổng điểm: {diff:.2f}")
if any(df[col].lt(0).any() for col in df.columns if "_M" in col):
    alerts.append("Có ô số câu âm (không hợp lệ).")

st.subheader("Ma trận nhập liệu")
left, right = st.columns([3.5, 1.5])

with left:
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_default_column(resizable=True, filter=True, sortable=True)
    gb.configure_column("TT", pinned="left", width=70)
    gb.configure_column("Chủ đề", pinned="left", width=240)
    gb.configure_column("Bài/Nội dung", pinned="left", width=320)
    gb.configure_column("Số tiết", pinned="left", width=90)
    gb.configure_column("Tỉ lệ %", pinned="left", width=90)
    gb.configure_column("Điểm cần đạt", pinned="left", width=110)

    # Configure grouped headers
    # Group TNKQ subtypes and TL by building columnDefs manually
    col_defs = gb.build()["columnDefs"]

    # Make qtype columns editable integers
    for qtype in QTYPE_ORDER:
        for level in LEVEL_ORDER:
            col = f"{qtype}_M{level}"
            gb.configure_column(col, editable=True, type=["numericColumn"], width=95)

    # Build final grid options with column groups
    grid_opts = gb.build()
    # Replace leaf columns with grouped columns
    pinned_left = [c for c in grid_opts["columnDefs"] if c["field"] in ["TT","Chủ đề","Bài/Nội dung","Số tiết","Tỉ lệ %","Điểm cần đạt"]]
    qcols = []
    for qtype in QTYPE_ORDER:
        children = []
        for level in LEVEL_ORDER:
            field = f"{qtype}_M{level}"
            header = {1:"Biết (M1)",2:"Hiểu (M2)",3:"VD (M3)"}[level]
            children.append({"headerName": header, "field": field, "editable": True, "width": 95, "type": ["numericColumn"]})
        qcols.append({"headerName": QTYPE_LABELS_VI.get(qtype, qtype), "children": children})
    grid_opts["columnDefs"] = pinned_left + qcols

    # Pinned bottom rows
    grid_opts["pinnedBottomRowData"] = [totals, ptsrow]

    grid_response = AgGrid(
        df,
        gridOptions=grid_opts,
        update_mode=GridUpdateMode.VALUE_CHANGED,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        fit_columns_on_grid_load=False,
        allow_unsafe_jscode=True,
        height=520
    )
    edited_df = pd.DataFrame(grid_response["data"])

with right:
    st.markdown("### Tóm tắt & Cảnh báo")
    st.write(f"**Tổng câu:** {int(edited_df[[c for c in edited_df.columns if '_M' in c]].sum().sum())}")
    st.write(f"**Tổng điểm (tính theo điểm/1 câu):** {compute_total_points(edited_df):.2f} / {float(total_points):.2f}")
    # Level totals
    m1 = int(edited_df[[c for c in edited_df.columns if c.endswith('_M1')]].sum().sum())
    m2 = int(edited_df[[c for c in edited_df.columns if c.endswith('_M2')]].sum().sum())
    m3 = int(edited_df[[c for c in edited_df.columns if c.endswith('_M3')]].sum().sum())
    st.write(f"**TT27:** M1={m1}  •  M2={m2}  •  M3={m3}")
    if alerts:
        for a in alerts:
            st.error(a)
    else:
        st.success("Không có cảnh báo lớn.")

    st.markdown("### Lưu ma trận")
    if st.button("Lưu vào session (dùng cho trang Tạo đề)"):
        # Persist matrix counts back to template-like structure
        st.session_state["matrix_df"] = edited_df.copy()
        st.session_state["matrix_meta"] = {
            "title": tmpl.title,
            "grade": tmpl.grade or 3,
            "subject": tmpl.subject or "Tin",
            "semester": tmpl.semester or "HK1",
            "total_points": float(total_points),
        }
        st.success("Đã lưu ma trận vào session_state. Sang trang 📝 Tạo đề & Xuất Word.")
