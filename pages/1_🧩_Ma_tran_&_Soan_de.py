from __future__ import annotations
import os
import pandas as pd
import streamlit as st

from tool.ui_common import inject_css, sidebar_settings
from tool.matrix_template import load_matrix_template, MatrixTemplate
from tool.question_bank import Bank
from tool.utils import QTYPE_ORDER, LEVEL_ORDER, round_to_step, qtype_level_label, parse_qtype_level, safe_int
from tool.generation import DraftItem, build_slots_from_matrix, assign_auto

st.set_page_config(page_title="🧩 Ma trận & Soạn đề", layout="wide")
inject_css()
sidebar_settings()

if "draft_items" not in st.session_state:
    st.session_state["draft_items"] = []
if "used_question_ids" not in st.session_state:
    st.session_state["used_question_ids"] = set()

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")
xlsx_files = [f for f in os.listdir(TEMPLATE_DIR) if f.lower().endswith(".xlsx")]
if not xlsx_files:
    st.error("Không tìm thấy template Excel trong thư mục templates/.")
    st.stop()

st.markdown('<div class="app-card">', unsafe_allow_html=True)
st.markdown("### Thiết lập nhanh")
top = st.columns([1.0, 1.2, 1.0, 1.0, 1.2])
with top[0]:
    grade = st.selectbox("Lớp", [1,2,3,4,5], index=2)
with top[1]:
    subject = st.selectbox("Môn", ["Tin","Toán","Tiếng Việt"], index=0)
with top[2]:
    semester = st.selectbox("Học kì", ["HK1","HK2"], index=0)
with top[3]:
    exam_type = st.selectbox("Loại KT", ["CKI","GK","CKII"], index=0)
with top[4]:
    total_points = st.number_input("Tổng điểm đề", min_value=1.0, max_value=20.0, value=10.0, step=0.25)
st.markdown("</div>", unsafe_allow_html=True)

st.markdown("### Chọn template ma trận (ẩn đường dẫn)")
xlsx_name = st.selectbox("Template Excel", xlsx_files, index=0)
xlsx_path = os.path.join(TEMPLATE_DIR, xlsx_name)

try:
    matrix: MatrixTemplate = load_matrix_template(xlsx_path, total_points=float(total_points), step=0.25)
except Exception as e:
    st.error(f"Lỗi đọc template Excel: {e}")
    st.stop()

st.session_state["matrix_meta"] = {
    "grade": int(grade),
    "subject": str(subject),
    "semester": str(semester),
    "exam_type": str(exam_type),
    "title": matrix.title,
    "total_points": float(total_points),
    "xlsx_name": xlsx_name,
}

st.markdown("### Cài đặt điểm/1 câu (bước 0,25)")
pts = st.session_state.get("points_per_qtype", {"MCQ":0.5,"TF":0.5,"MATCH":1.0,"FILL":1.0,"ESSAY":1.0})
pcols = st.columns(5)
with pcols[0]:
    pts["MCQ"] = round_to_step(st.number_input("MCQ", 0.0, 10.0, float(pts.get("MCQ",0.5)), 0.25))
with pcols[1]:
    pts["TF"] = round_to_step(st.number_input("Đúng-Sai", 0.0, 10.0, float(pts.get("TF",0.5)), 0.25))
with pcols[2]:
    pts["MATCH"] = round_to_step(st.number_input("Nối cột", 0.0, 10.0, float(pts.get("MATCH",1.0)), 0.25))
with pcols[3]:
    pts["FILL"] = round_to_step(st.number_input("Điền khuyết", 0.0, 10.0, float(pts.get("FILL",1.0)), 0.25))
with pcols[4]:
    pts["ESSAY"] = round_to_step(st.number_input("Tự luận", 0.0, 10.0, float(pts.get("ESSAY",1.0)), 0.25))
st.session_state["points_per_qtype"] = pts

bank: Bank | None = st.session_state.get("bank")
bank_df = bank.filtered(int(grade), subject, semester) if bank is not None else None

topics = sorted({l.topic for l in matrix.lessons if l.topic})
lessons_by_topic = {}
for l in matrix.lessons:
    lessons_by_topic.setdefault(l.topic, set()).add(l.lesson)

yccd_by_lesson = {}
if bank_df is not None and not bank_df.empty:
    for _, r in bank_df.iterrows():
        yccd_by_lesson.setdefault((str(r["topic"]), str(r["lesson"])), set()).add(str(r["yccd"]))

st.markdown("### Thao tác nhanh (cùng một dòng ngang)")
row = st.columns([1.2, 1.4, 1.4, 1.3, 0.8, 1.0])
with row[0]:
    sel_topic = st.selectbox("Chủ đề", topics, index=0 if topics else None)
with row[1]:
    lesson_opts = sorted(list(lessons_by_topic.get(sel_topic, [])))
    sel_lesson = st.selectbox("Bài học", lesson_opts, index=0 if lesson_opts else None)
with row[2]:
    yccd_opts = sorted(list(yccd_by_lesson.get((sel_topic, sel_lesson), [])))
    if yccd_opts:
        sel_yccd = st.selectbox("YCCĐ", ["(tất cả)"] + yccd_opts, index=0)
        if sel_yccd == "(tất cả)":
            sel_yccd = ""
    else:
        sel_yccd = st.text_input("YCCĐ", value="", placeholder="(chưa có dữ liệu kho)")
with row[3]:
    qtype_level_opts = [qtype_level_label(q, lv) for q in QTYPE_ORDER for lv in LEVEL_ORDER]
    sel_qtype_level = st.selectbox("Dạng/Mức (TT27)", qtype_level_opts, index=0)
with row[4]:
    qtype, level = parse_qtype_level(sel_qtype_level)
    default_pts = float(pts.get(qtype, 0.25))
    sel_points = round_to_step(st.number_input("Điểm", 0.0, 10.0, value=default_pts, step=0.25))
with row[5]:
    add_btn = st.button("➕ Thêm vào đề", use_container_width=True)

qtype, level = parse_qtype_level(sel_qtype_level)

if add_btn:
    existing = st.session_state["draft_items"]
    next_qno = 1 if not existing else max(int(x["qno"]) for x in existing) + 1

    qid = None
    stem = ""
    if bank_df is not None and not bank_df.empty:
        used = set(st.session_state.get("used_question_ids", set()))
        sub = bank_df[
            (bank_df["topic"].astype(str)==str(sel_topic)) &
            (bank_df["lesson"].astype(str)==str(sel_lesson)) &
            (bank_df["qtype"].astype(str).str.upper()==qtype) &
            (bank_df["tt27_level"].astype(int)==int(level))
        ]
        if sel_yccd:
            sub2 = sub[sub["yccd"].astype(str)==str(sel_yccd)]
            if not sub2.empty:
                sub = sub2
        if sub.empty:
            st.error("Không có câu phù hợp trong kho theo đúng (Chủ đề+Bài+YCCĐ+Dạng+Mức).")
        else:
            for _, r in sub.iterrows():
                cand = str(r["question_id"])
                if cand not in used:
                    qid = cand
                    stem = str(r.get("stem",""))
                    used.add(cand)
                    st.session_state["used_question_ids"] = used
                    break
            if qid is None:
                st.error("Các câu phù hợp đã dùng hết. Hãy bổ sung kho hoặc đổi tiêu chí.")
    else:
        st.warning("Chưa có kho câu hỏi → chỉ thêm slot (chưa có nội dung).")

    st.session_state["draft_items"].append({
        "qno": next_qno,
        "topic": sel_topic,
        "lesson": sel_lesson,
        "yccd": sel_yccd,
        "qtype": qtype,
        "level": int(level),
        "points": float(sel_points),
        "question_id": qid,
        "stem": stem,
    })
    st.success(f"Đã thêm Câu {next_qno} ({qtype}, M{level}).")

st.markdown("---")

left, right = st.columns([2.2, 1.3], gap="large")

with left:
    st.markdown("### Ma trận (GV nhìn & chỉnh số câu theo ô)")
    data = []
    for lr in matrix.lessons:
        rowd = {
            "TT": lr.tt,
            "Chủ đề": lr.topic,
            "Bài/Nội dung": lr.lesson,
            "Số tiết": lr.periods,
            "Tỉ lệ %": round(lr.ratio_pct, 1),
            "Điểm cần đạt": round(lr.points_target, 2),
        }
        for q in QTYPE_ORDER:
            for lv in LEVEL_ORDER:
                rowd[qtype_level_label(q, lv)] = int(lr.counts.get((q, lv), 0))
        data.append(rowd)
    df = pd.DataFrame(data)

    count_cols = [c for c in df.columns if "•" in c]
    disabled_cols = [c for c in df.columns if c not in count_cols]

    edited = st.data_editor(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            **{c: st.column_config.NumberColumn(c, min_value=0, step=1) for c in count_cols},
            **{c: st.column_config.TextColumn(c, disabled=True) for c in disabled_cols},
        },
        disabled=disabled_cols,
        height=520,
    )

    if st.button("💾 Lưu ma trận (để sinh slot theo ma trận)", type="primary"):
        st.session_state["matrix_df"] = edited.copy()
        st.success("Đã lưu ma trận.")

with right:
    st.markdown("### 📌 Đề hiện tại")
    items = st.session_state["draft_items"]

    total_q = len(items)
    total_pts = sum(float(x["points"]) for x in items) if items else 0.0
    m1 = sum(1 for x in items if int(x["level"])==1)
    m2 = sum(1 for x in items if int(x["level"])==2)
    m3 = sum(1 for x in items if int(x["level"])==3)

    st.markdown(
        f'<span class="pill">Tổng câu: <b>{total_q}</b></span>'
        f'<span class="pill">Tổng điểm: <b>{total_pts:.2f}</b></span><br/>'
        f'<span class="pill">M1: <b>{m1}</b></span>'
        f'<span class="pill">M2: <b>{m2}</b></span>'
        f'<span class="pill">M3: <b>{m3}</b></span>',
        unsafe_allow_html=True,
    )

    if abs(total_pts - float(total_points)) > 1e-6:
        diff = total_pts - float(total_points)
        st.markdown(f'<div class="danger">⚠️ Lệch tổng điểm: {diff:+.2f}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="ok">✅ Tổng điểm khớp</div>', unsafe_allow_html=True)

    colA, colB = st.columns(2)
    with colA:
        if st.button("🧮 Sinh slot theo ma trận", use_container_width=True):
            mdf = st.session_state.get("matrix_df")
            base_matrix = matrix
            if mdf is not None:
                for lr in base_matrix.lessons:
                    match = mdf[mdf["TT"]==lr.tt]
                    if match.empty:
                        continue
                    r = match.iloc[0]
                    for q in QTYPE_ORDER:
                        for lv in LEVEL_ORDER:
                            lr.counts[(q, lv)] = safe_int(r.get(qtype_level_label(q, lv)), 0)

            slots = build_slots_from_matrix(base_matrix, pts)
            if bank is not None:
                slots, warns = assign_auto(slots, bank, int(grade), subject, semester, seed=42)
                if warns:
                    st.warning(f"Thiếu {len(warns)} câu theo đúng ô (không bù mức).")
            st.session_state["draft_items"] = [x.__dict__ for x in slots]
            st.session_state["used_question_ids"] = set([x.question_id for x in slots if x.question_id])
            st.success("Đã tạo đề theo ma trận.")
    with colB:
        if st.button("🗑️ Xóa toàn bộ", use_container_width=True):
            st.session_state["draft_items"] = []
            st.session_state["used_question_ids"] = set()
            st.success("Đã xóa.")

    if not items:
        st.info("Chưa có câu nào.")
    else:
        show = pd.DataFrame([{
            "Câu": x["qno"],
            "Chủ đề": x["topic"],
            "Bài": x["lesson"],
            "Dạng": x["qtype"],
            "Mức": f"M{x['level']}",
            "Điểm": x["points"],
            "ID": x["question_id"] or "(trống)",
        } for x in items]).sort_values("Câu")
        st.dataframe(show, use_container_width=True, height=260, hide_index=True)

        del_q = st.number_input("Xóa câu số", min_value=1, max_value=max(int(x["qno"]) for x in items), value=1, step=1)
        if st.button("Xóa câu đã chọn"):
            new_items = [x for x in items if int(x["qno"]) != int(del_q)]
            new_items = sorted(new_items, key=lambda x: int(x["qno"]))
            for i, x in enumerate(new_items, start=1):
                x["qno"] = i
            st.session_state["draft_items"] = new_items
            st.success("Đã xóa và đánh số lại.")
