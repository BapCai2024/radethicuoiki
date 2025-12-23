
from __future__ import annotations

import os
import re
import json
import streamlit as st
import pandas as pd

from tool.ui_common import inject_css, sidebar_brand
from tool.utils import (
    QTYPE_ORDER, LEVEL_ORDER, LEVEL_NAME,
    round_to_step, qtype_level_label, parse_qtype_level
)
from tool.matrix_template import load_matrix_template, MatrixTemplate, LessonRow
from tool.question_bank import load_bank_from_upload, Bank
from tool.data_loader import load_catalog_csv, try_parse_catalog_from_excel
from tool.ai_provider import openai_compatible_generate, gemini_ai_studio_generate, AIError
from tool.export_docx import export_spec_from_template, export_exam_docx
from tool.catalog_builder import load_or_build_catalog

# ---------------- Page ----------------
st.set_page_config(page_title="Tool HỖ TRỢ RA ĐỀ", layout="wide")
inject_css()
sidebar_brand()

# ---------------- Session ----------------
st.session_state.setdefault("bank", None)
st.session_state.setdefault("catalog_df", None)

st.session_state.setdefault("draft_items", [])
st.session_state.setdefault("used_question_ids", set())

# Matrix editor state
st.session_state.setdefault("matrix_editor_df", None)
st.session_state.setdefault("matrix_sig", None)

# AI
st.session_state.setdefault("ai_mode", "Tắt")  # "Tắt" | "OpenAI-compatible" | "Gemini"
st.session_state.setdefault("ai_api_key", "")
st.session_state.setdefault("ai_base_url", "https://api.openai.com")
st.session_state.setdefault("ai_model", "gpt-4o-mini")
st.session_state.setdefault("gemini_model", "gemini-2.5-flash")

# points per qtype
st.session_state.setdefault("points_per_qtype", {"MCQ":0.5,"TF":0.5,"MATCH":1.0,"FILL":1.0,"ESSAY":1.0})

# ---------------- Paths ----------------
BASE_DIR = os.path.dirname(__file__)
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
DATA_DIR = os.path.join(BASE_DIR, "data")
SOURCE_DIR = os.path.join(DATA_DIR, "khgd_sources")
CATALOG_CSV = os.path.join(DATA_DIR, "yccd_catalog.csv")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs("outputs", exist_ok=True)

# ---------------- HERO ----------------
st.markdown('<div class="app-hero">', unsafe_allow_html=True)
st.markdown("# 🧩 Tool HỖ TRỢ RA ĐỀ")
st.markdown(
    '<div class="muted">'
    '✅ Dữ liệu YCCĐ đã được nạp sẵn từ bộ KHGD bạn cung cấp (có thể upload lại để thay thế).'
    '<br/>✅ TT27 khóa mức: chọn M1/M2/M3 thì chỉ lấy/tạo đúng mức đó (không nhảy mức).'
    '</div>',
    unsafe_allow_html=True
)
st.markdown("</div>", unsafe_allow_html=True)
st.write("")


# ---------------- API/AI (moved under title) ----------------
with st.expander("⚙️ API/AI (để AI tạo câu hỏi) — mở để nhập key & test", expanded=False):
    c1, c2, c3, c4 = st.columns([1.2, 2.2, 2.2, 1.2], gap="medium")
    with c1:
        mode_ui = st.selectbox("Chế độ", ["Tắt", "OpenAI-compatible", "AI Studio (Gemini)"], index=0, key="ai_mode_ui_top")
        if mode_ui == "Tắt":
            st.session_state["ai_mode"] = "Tắt"
        elif mode_ui == "OpenAI-compatible":
            st.session_state["ai_mode"] = "OpenAI-compatible"
        else:
            st.session_state["ai_mode"] = "Gemini"
    with c2:
        st.session_state["ai_api_key"] = st.text_input("API Key", type="password", value=st.session_state.get("ai_api_key",""), key="ai_key_top")
    with c3:
        if st.session_state["ai_mode"] == "OpenAI-compatible":
            st.session_state["ai_base_url"] = st.text_input("Base URL", value=st.session_state.get("ai_base_url","https://api.openai.com"), key="ai_base_top")
            st.session_state["ai_model"] = st.text_input("Model", value=st.session_state.get("ai_model","gpt-4o-mini"), key="ai_model_top")
        elif st.session_state["ai_mode"] == "Gemini":
            st.session_state["gemini_model"] = st.text_input("Gemini model", value=st.session_state.get("gemini_model","gemini-2.5-flash"), key="gem_model_top")
        else:
            st.caption("Bật AI để tool có thể tạo câu hỏi.")
    with c4:
        if st.button("✅ Test API", use_container_width=True):
            try:
                if st.session_state["ai_mode"] == "OpenAI-compatible":
                    out = openai_compatible_generate(
                        st.session_state.get("ai_base_url","https://api.openai.com"),
                        st.session_state.get("ai_api_key",""),
                        st.session_state.get("ai_model","gpt-4o-mini"),
                        "Trả lời đúng 1 từ: OK",
                        timeout=25
                    )
                elif st.session_state["ai_mode"] == "Gemini":
                    out = gemini_ai_studio_generate(
                        st.session_state.get("ai_api_key",""),
                        st.session_state.get("gemini_model","gemini-2.5-flash"),
                        "Trả lời đúng 1 từ: OK",
                        timeout=25
                    )
                else:
                    out = "AI đang tắt."
                st.success(f"Kết quả: {str(out)[:120]}")
            except Exception as e:
                st.error(f"Test lỗi: {e}")

status = "🟢 AI đang bật" if st.session_state.get("ai_mode") != "Tắt" else "⚪ AI đang tắt"
st.caption(f"{status} — (Nếu muốn AI tạo câu, hãy mở expander ⚙️ ở trên để nhập key.)")


# ---------------- Helpers ----------------
DEFAULT_SUBJECTS = ["Tin","Toán","Tiếng Việt","Khoa học","Lịch sử - Địa lý","Đạo đức","Công nghệ","Âm nhạc","Mĩ thuật"]

def _norm_text(x: str) -> str:
    return str(x or "").strip()

def safe_index(options: list[str], current_value: str) -> int:
    try:
        if current_value in options:
            return options.index(current_value)
    except Exception:
        pass
    return 0

def norm_subject(s: str) -> str:
    s0 = _norm_text(s).lower()
    mapping = {
        "tin học": "Tin",
        "tin": "Tin",
        "toán": "Toán",
        "tieng viet": "Tiếng Việt",
        "tiếng việt": "Tiếng Việt",
        "khoa học": "Khoa học",
        "lịch sử và địa lý": "Lịch sử - Địa lý",
        "lịch sử - địa lý": "Lịch sử - Địa lý",
        "ls-đl": "Lịch sử - Địa lý",
        "đạo đức": "Đạo đức",
        "cong nghe": "Công nghệ",
        "công nghệ": "Công nghệ",
        "âm nhạc": "Âm nhạc",
        "am nhac": "Âm nhạc",
        "mĩ thuật": "Mĩ thuật",
        "mi thuat": "Mĩ thuật",
    }
    return mapping.get(s0, _norm_text(s))

def norm_semester(s: str) -> str:
    s0 = _norm_text(s).lower()
    if not s0:
        return ""
    if "hk1" in s0 or "hki" in s0 or "học kì i" in s0 or "hoc ki i" in s0:
        return "HK1"
    if "hk2" in s0 or "hkii" in s0 or "học kì ii" in s0 or "hoc ki ii" in s0:
        return "HK2"
    if re.search(r"\\b1\\b", s0):
        return "HK1"
    if re.search(r"\\b2\\b", s0):
        return "HK2"
    return _norm_text(s)

def ensure_catalog_loaded():
    if st.session_state["catalog_df"] is None:
        # Load CSV already committed; if missing/broken, rebuild from sources
        try:
            df = load_catalog_csv(CATALOG_CSV)
        except Exception:
            df = load_or_build_catalog(CATALOG_CSV, SOURCE_DIR)
        st.session_state["catalog_df"] = df

def prep_catalog(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=["grade","subject","semester","topic","lesson","yccd","grade_norm","subject_norm","semester_norm"])
    d = df.copy()
    d["grade_norm"] = pd.to_numeric(d.get("grade", pd.Series([], dtype="float")), errors="coerce").fillna(-1).astype(int)
    d["subject_norm"] = d.get("subject", "").fillna("").astype(str).map(norm_subject)
    d["semester_norm"] = d.get("semester", "").fillna("").astype(str).map(norm_semester)
    for c in ["topic","lesson","yccd"]:
        d[c] = d.get(c, "").fillna("").astype(str).map(_norm_text)
    return d

def cascade_filter(cat: pd.DataFrame, grade: int, subject: str, semester: str) -> pd.DataFrame:
    subj = norm_subject(subject)
    sem = norm_semester(semester)
    d1 = cat[(cat["grade_norm"] == int(grade)) | (cat["grade_norm"] == -1)]
    d2 = d1[(d1["subject_norm"].str.lower() == subj.lower()) | (d1["subject_norm"].str.strip() == "")]
    d3 = d2[(d2["semester_norm"].str.upper() == sem.upper()) | (d2["semester_norm"].str.strip() == "")]
    return d3

def reset_if_sig_changed(sig_key: str, sig_value, keys_to_clear: list[str]):
    if st.session_state.get(sig_key) != sig_value:
        for k in keys_to_clear:
            if k in st.session_state:
                del st.session_state[k]
        st.session_state[sig_key] = sig_value

def list_template_xlsx() -> list[str]:
    if not os.path.isdir(TEMPLATE_DIR):
        return []
    return [f for f in os.listdir(TEMPLATE_DIR) if f.lower().endswith(".xlsx")]

def list_template_docx() -> list[str]:
    if not os.path.isdir(TEMPLATE_DIR):
        return []
    return [f for f in os.listdir(TEMPLATE_DIR) if f.lower().endswith(".docx")]

def pick_best_matrix_template(grade: int, subject: str, semester: str) -> str | None:
    files = list_template_xlsx()
    if not files:
        return None
    best = None
    best_score = -1
    for f in files:
        p = os.path.join(TEMPLATE_DIR, f)
        try:
            mx = load_matrix_template(p, total_points=10.0)
            score = 0
            if mx.grade == int(grade):
                score += 3
            if (mx.subject or "").lower() == norm_subject(subject).lower():
                score += 3
            if (mx.semester or "").upper() == norm_semester(semester).upper():
                score += 2
            if score > best_score:
                best_score = score
                best = p
        except Exception:
            continue
    return best

def matrix_to_editor_df(mx: MatrixTemplate) -> pd.DataFrame:
    rows = []
    for lr in mx.lessons:
        r = {
            "TT": lr.tt,
            "Chủ đề": lr.topic,
            "Bài": lr.lesson,
            "Số tiết": lr.periods,
        }
        for q in QTYPE_ORDER:
            for lv in LEVEL_ORDER:
                r[qtype_level_label(q, lv)] = int(lr.counts.get((q, lv), 0))
        rows.append(r)
    return pd.DataFrame(rows)

def editor_df_to_matrix(mx: MatrixTemplate, df_ed: pd.DataFrame) -> MatrixTemplate:
    # apply edited counts back to matrix in-memory (do not write file)
    lookup = {int(r.tt): r for r in mx.lessons}
    for _, row in df_ed.iterrows():
        try:
            tt = int(row.get("TT"))
        except Exception:
            continue
        lr = lookup.get(tt)
        if not lr:
            continue
        for q in QTYPE_ORDER:
            for lv in LEVEL_ORDER:
                col = qtype_level_label(q, lv)
                v = row.get(col, 0)
                try:
                    lr.counts[(q, lv)] = int(float(v))
                except Exception:
                    lr.counts[(q, lv)] = 0
    return mx

# ---------------- Tabs ----------------
tab_soande, tab_dulieu, tab_xuat = st.tabs(["🧩 Soạn đề", "📚 Dữ liệu", "📤 Xuất Word"])

# ================= TAB: DATA =================
with tab_dulieu:
    st.subheader("Nạp dữ liệu (YCCĐ + Kho câu hỏi)")
    st.info("Bạn có thể upload lại YCCĐ (CSV/XLSX) để thay thế dữ liệu đã nạp sẵn trong tool.")

    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.markdown("### 1) YCCĐ (Chủ đề – Bài – YCCĐ)")
        upl = st.file_uploader("Upload file YCCĐ (CSV/XLSX)", type=["csv","xlsx","xls"], key="upl_yccd")
        if upl is not None:
            try:
                if upl.name.lower().endswith(".csv"):
                    df = pd.read_csv(upl)
                else:
                    df = try_parse_catalog_from_excel(upl)
                st.session_state["catalog_df"] = df
                os.makedirs(DATA_DIR, exist_ok=True)
                df.to_csv(CATALOG_CSV, index=False, encoding="utf-8-sig")
                st.success("✅ Đã nạp YCCĐ và lưu lại data/yccd_catalog.csv (trong môi trường chạy).")
                st.dataframe(df.head(250), use_container_width=True, height=320)
            except Exception as e:
                st.error(f"Lỗi nạp YCCĐ: {e}")
        else:
            ensure_catalog_loaded()
            df = st.session_state["catalog_df"]
            if df is not None and not df.empty:
                st.caption("Đang dùng dữ liệu YCCĐ đã tích hợp sẵn.")
                st.dataframe(df.head(250), use_container_width=True, height=320)
            else:
                st.warning("Chưa có dữ liệu YCCĐ.")

    with col2:
        st.markdown("### 2) Kho câu hỏi (không bắt buộc)")
        upq = st.file_uploader("Upload kho câu hỏi (CSV/XLSX)", type=["csv","xlsx","xls"], key="upl_bank")
        if upq is not None:
            try:
                bank = load_bank_from_upload(upq)
                ok, errs = bank.validate()
                if not ok:
                    st.error("Kho câu hỏi chưa đạt yêu cầu:")
                    for er in errs:
                        st.write("- " + er)
                else:
                    st.session_state["bank"] = bank
                    st.success("✅ Đã nạp kho câu hỏi.")
                    st.dataframe(bank.df.head(200), use_container_width=True, height=320)
            except Exception as e:
                st.error(f"Lỗi nạp kho câu hỏi: {e}")
        else:
            st.caption("Bạn có thể chạy hoàn toàn bằng AI nếu không có kho.")

# ================= TAB: SOẠN ĐỀ =================
with tab_soande:
    ensure_catalog_loaded()
    cat_prepped = prep_catalog(st.session_state["catalog_df"])

    st.subheader("Thiết lập đề")

    top = st.columns([1.0, 1.25, 1.0, 1.0, 1.2])

    with top[0]:
        grade = st.selectbox("Lớp", [1,2,3,4,5], index=2, key="grade_sel")

    # Subjects depend on grade (incl. wildcard grade=-1)
    d_grade = cat_prepped[(cat_prepped["grade_norm"]==int(grade)) | (cat_prepped["grade_norm"]==-1)]
    dyn_subjects = sorted([s for s in d_grade["subject_norm"].dropna().astype(str).unique().tolist() if s.strip()])
    subject_options = []
    for s in DEFAULT_SUBJECTS + dyn_subjects:
        s = _norm_text(s)
        if s and s not in subject_options:
            subject_options.append(s)

    with top[1]:
        reset_if_sig_changed("sig_grade", int(grade), ["subject_sel","semester_sel","topic_sel","lesson_sel","yccd_sel","yccd_free"])
        subject = st.selectbox("Môn", subject_options, index=safe_index(subject_options, st.session_state.get("subject_sel","Tin")), key="subject_sel")

    # Semesters depend on grade+subject (incl. wildcard blank)
    d_gs = d_grade[(d_grade["subject_norm"].str.lower()==norm_subject(subject).lower()) | (d_grade["subject_norm"].str.strip()=="")]
    dyn_semesters = sorted([s for s in d_gs["semester_norm"].dropna().astype(str).unique().tolist() if s.strip()])
    sem_options = ["HK1","HK2"]
    for s in dyn_semesters:
        if s not in sem_options:
            sem_options.append(s)

    with top[2]:
        reset_if_sig_changed("sig_subject", norm_subject(subject).lower(), ["semester_sel","topic_sel","lesson_sel","yccd_sel","yccd_free"])
        semester = st.selectbox("Học kì", sem_options, index=safe_index(sem_options, st.session_state.get("semester_sel","HK1")), key="semester_sel")

    with top[3]:
        exam_type = st.selectbox("Loại KT", ["GK","CKI","CKII"], index=1)

    with top[4]:
        total_points = st.number_input("Tổng điểm", min_value=1.0, max_value=20.0, value=10.0, step=0.25)

    
    # ================== MATRIX (hidden by default) ==================
    st.markdown("### Tạo đề theo ma trận (ẩn bảng — chỉ mở khi cần chỉnh)")
    mtx_path = pick_best_matrix_template(int(grade), subject, semester)

    mx = None
    if not mtx_path:
        st.info("Không có template ma trận cho lựa chọn hiện tại. Bạn vẫn có thể soạn theo luồng Chủ đề → Bài → YCCĐ và dùng AI tạo câu.")
    else:
        try:
            mx = load_matrix_template(mtx_path, total_points=float(total_points))
        except Exception as e:
            mx = None
            st.error(f"Lỗi đọc ma trận: {e}")

    # Init editor df when switching grade/subject/semester or first load
    sig = (int(grade), norm_subject(subject), norm_semester(semester), os.path.basename(mtx_path) if mtx_path else "")
    if mx is not None:
        if st.session_state.get("matrix_sig") != sig or st.session_state.get("matrix_editor_df") is None:
            st.session_state["matrix_editor_df"] = matrix_to_editor_df(mx)
            st.session_state["matrix_sig"] = sig

    df_ed = st.session_state.get("matrix_editor_df")
    df_new = df_ed

    # Compact controls (no big table)
    cc1, cc2, cc3, cc4, cc5 = st.columns([1.2, 1.2, 1.8, 1.8, 1.2], gap="small")
    with cc1:
        show_matrix = st.toggle("Hiện bảng ma trận", value=False)
    with cc2:
        ai_batch = int(st.number_input("AI tạo/lượt", min_value=0, max_value=50, value=10, step=1,
                                       help="Để tránh lag/time-out, AI sẽ tạo tối đa N câu trống mỗi lần bấm."))
    with cc3:
        replace_by_matrix = st.button("⚡ Tạo mới theo ma trận", use_container_width=True, disabled=(mx is None or df_new is None))
    with cc4:
        append_by_matrix = st.button("➕ Thêm theo ma trận", use_container_width=True, disabled=(mx is None or df_new is None))
    with cc5:
        gen_ai_missing = st.button("✨ AI tạo tiếp", use_container_width=True, disabled=(ai_batch <= 0))

    # Optional: show editable matrix in expander
    if show_matrix and mx is not None and df_ed is not None:
        with st.expander("🧩 Bảng ma trận (GV chỉnh số câu theo ô) — có thể kéo ngang", expanded=True):
            col_cfg = {
                "TT": st.column_config.NumberColumn("TT", disabled=True),
                "Chủ đề": st.column_config.TextColumn("Chủ đề", disabled=True),
                "Bài": st.column_config.TextColumn("Bài", disabled=True),
                "Số tiết": st.column_config.NumberColumn("Số tiết", disabled=True),
            }
            for q in QTYPE_ORDER:
                for lv in LEVEL_ORDER:
                    col = qtype_level_label(q, lv)
                    col_cfg[col] = st.column_config.NumberColumn(col, min_value=0, step=1)

            df_new = st.data_editor(
                df_ed,
                use_container_width=True,
                hide_index=True,
                column_config=col_cfg,
                height=420,
            )
            st.session_state["matrix_editor_df"] = df_new

    def _build_items_from_matrix(mx_local: MatrixTemplate, df_local: pd.DataFrame, replace: bool):
        # Apply edits to matrix
        mx_local = editor_df_to_matrix(mx_local, df_local)

        if replace:
            st.session_state["draft_items"] = []
            st.session_state["used_question_ids"] = set()

        ensure_catalog_loaded()
        filtered = cascade_filter(cat_prepped, int(grade), subject, semester)

        # index yccd per (topic, lesson)
        ymap = {}
        if not filtered.empty:
            for (t, l), gdf in filtered.groupby(["topic","lesson"]):
                ymap[(str(t), str(l))] = gdf["yccd"].dropna().astype(str).tolist()

        bank: Bank | None = st.session_state["bank"]
        bank_df = bank.filtered(int(grade), norm_subject(subject), norm_semester(semester)) if bank is not None else None

        def pick_from_bank(topic_: str, lesson_: str, qtype_: str, level_: int, yccd_: str):
            if bank_df is None or bank_df.empty:
                return None, {}
            sub = bank_df[
                (bank_df["topic"].astype(str)==str(topic_)) &
                (bank_df["lesson"].astype(str)==str(lesson_)) &
                (bank_df["qtype"].astype(str).str.upper()==qtype_) &
                (bank_df["tt27_level"].astype(int)==int(level_))
            ]
            if yccd_:
                sub2 = sub[sub["yccd"].astype(str)==str(yccd_)]
                if not sub2.empty:
                    sub = sub2
            if sub.empty:
                return None, {}
            used = set(st.session_state.get("used_question_ids", set()))
            for _, r in sub.iterrows():
                qid = str(r.get("question_id",""))
                if qid and qid not in used:
                    used.add(qid)
                    st.session_state["used_question_ids"] = used
                    return qid, {
                        "stem": str(r.get("stem","")),
                        "options": str(r.get("options","")),
                        "answer": str(r.get("answer","")),
                        "marking_guide": str(r.get("marking_guide","")),
                        "yccd": str(r.get("yccd","")),
                    }
            return None, {}

        pts = st.session_state["points_per_qtype"]
        items = st.session_state["draft_items"]
        next_qno = 1 if not items else max(int(x.get("qno",0)) for x in items) + 1

        added = 0
        for lr in mx_local.lessons:
            t = lr.topic
            l = lr.lesson
            ylist = ymap.get((str(t), str(l)), [])
            yidx = 0
            for q in QTYPE_ORDER:
                for lv in LEVEL_ORDER:
                    cnt = int(lr.counts.get((q, lv), 0) or 0)
                    for _ in range(cnt):
                        yccd_pick = ""
                        if ylist:
                            yccd_pick = ylist[yidx % len(ylist)]
                            yidx += 1

                        qid, payload = pick_from_bank(t, l, q, lv, yccd_pick)
                        stem = payload.get("stem","")
                        options = payload.get("options","")
                        answer = payload.get("answer","")
                        guide = payload.get("marking_guide","")

                        items.append({
                            "qno": next_qno,
                            "topic": t,
                            "lesson": l,
                            "yccd": yccd_pick or payload.get("yccd",""),
                            "qtype": q,
                            "level": int(lv),
                            "points": float(pts.get(q, 0.25)),
                            "question_id": qid,
                            "stem": stem,
                            "options": options,
                            "answer": answer,
                            "marking_guide": guide,
                        })
                        next_qno += 1
                        added += 1

        st.session_state["draft_items"] = items
        return added

    def _ai_fill_missing(limit_n: int):
        if limit_n <= 0:
            return 0
        mode = st.session_state.get("ai_mode","Tắt")
        if mode == "Tắt":
            st.warning("AI đang tắt. Mở ⚙️ API/AI dưới tiêu đề để bật và nhập key.")
            return 0

        items = st.session_state.get("draft_items", [])
        missing_idx = [i for i,x in enumerate(items) if not str(x.get("stem","")).strip()]
        if not missing_idx:
            st.info("Không có câu trống để AI tạo.")
            return 0

        todo = missing_idx[:limit_n]
        prog = st.progress(0.0)
        done = 0

        for k, i in enumerate(todo, start=1):
            x = items[i]
            qtype_ = x.get("qtype","MCQ")
            lv = int(x.get("level",1))
            pts_one = float(x.get("points",0.25))
            lvl_name = LEVEL_NAME.get(int(lv), f"M{lv}")
            prompt = f"""Hãy tạo 01 câu hỏi cho học sinh tiểu học (CTGDPT 2018, TT27).
Lớp: {grade}
Môn: {subject}
Học kì: {semester}
Chủ đề: {x.get('topic','')}
Bài học: {x.get('lesson','')}
YCCĐ: {x.get('yccd','') or '(tổng hợp)'}
Dạng: {qtype_}
Mức độ (TT27): {lvl_name}
Điểm: {pts_one}

Trả về JSON đúng cấu trúc:
{{"stem":"...","options":["A...","B...","C...","D..."],"answer":"A","marking_guide":"..." }}
Nếu không phải MCQ thì options = [] .
Chỉ trả JSON, không thêm chữ khác."""
            try:
                if mode == "OpenAI-compatible":
                    txt = openai_compatible_generate(
                        base_url=st.session_state.get("ai_base_url","https://api.openai.com"),
                        api_key=st.session_state.get("ai_api_key",""),
                        model=st.session_state.get("ai_model","gpt-4o-mini"),
                        prompt=prompt,
                        timeout=45,
                    )
                else:
                    txt = gemini_ai_studio_generate(
                        api_key=st.session_state.get("ai_api_key",""),
                        model=st.session_state.get("gemini_model","gemini-2.5-flash"),
                        prompt=prompt,
                        timeout=45,
                    )
                obj = json.loads(txt)
                x["stem"] = obj.get("stem","")
                opts = obj.get("options", [])
                x["options"] = json.dumps(opts, ensure_ascii=False) if isinstance(opts, list) else str(opts)
                x["answer"] = obj.get("answer","")
                x["marking_guide"] = obj.get("marking_guide","")
                if not x.get("question_id"):
                    x["question_id"] = f"AI_{grade}_{norm_subject(subject)}_{norm_semester(semester)}_{qtype_}_M{lv}_{x.get('qno',0):03d}"
                done += 1
            except Exception as e:
                # keep blank; continue
                x["marking_guide"] = f"(AI lỗi: {e})"
            prog.progress(k/len(todo))
        st.session_state["draft_items"] = items
        return done

    if (replace_by_matrix or append_by_matrix) and mx is not None and df_new is not None:
        added = _build_items_from_matrix(mx, df_new, replace=bool(replace_by_matrix))
        st.success(f"✅ Đã tạo {added} dòng câu theo ma trận. (AI sẽ tạo nội dung theo lô để tránh lag.)")
        if ai_batch > 0:
            created = _ai_fill_missing(ai_batch)
            if created:
                st.success(f"✨ AI đã tạo {created} câu trong lượt này. Bạn có thể bấm 'AI tạo tiếp' để tạo thêm.")

    if gen_ai_missing:
        created = _ai_fill_missing(ai_batch)
        if created:
            st.success(f"✨ AI đã tạo {created} câu trong lượt này.")
# ================== Points per qtype ==================
    st.markdown("### Điểm/1 câu (bước 0,25)")
    pts = st.session_state["points_per_qtype"]
    pcols = st.columns(5)
    with pcols[0]:
        pts["MCQ"] = round_to_step(st.number_input("MCQ", 0.0, 10.0, float(pts.get("MCQ",0.5)), 0.25), 0.25)
    with pcols[1]:
        pts["TF"] = round_to_step(st.number_input("Đúng-Sai", 0.0, 10.0, float(pts.get("TF",0.5)), 0.25), 0.25)
    with pcols[2]:
        pts["MATCH"] = round_to_step(st.number_input("Nối cột", 0.0, 10.0, float(pts.get("MATCH",1.0)), 0.25), 0.25)
    with pcols[3]:
        pts["FILL"] = round_to_step(st.number_input("Điền khuyết", 0.0, 10.0, float(pts.get("FILL",1.0)), 0.25), 0.25)
    with pcols[4]:
        pts["ESSAY"] = round_to_step(st.number_input("Tự luận", 0.0, 10.0, float(pts.get("ESSAY",1.0)), 0.25), 0.25)
    st.session_state["points_per_qtype"] = pts

    # ================== CASCADE ==================
    reset_if_sig_changed("sig_gss", (int(grade), norm_subject(subject).lower(), norm_semester(semester)), ["topic_sel","lesson_sel","yccd_sel","yccd_free"])
    filtered = cascade_filter(cat_prepped, int(grade), subject, semester)

    topics = sorted([t for t in filtered["topic"].dropna().astype(str).unique().tolist() if t.strip()])
    st.markdown("### Thao tác nhanh (cùng một dòng ngang)")
    if not topics:
        st.warning("Không có luồng dữ liệu theo Lớp/Môn/HK đang chọn. Nếu bạn đã upload YCCĐ, hãy kiểm tra cột Lớp/Môn/Học kì trong file.")
    row = st.columns([1.2, 1.7, 2.0, 1.6, 0.9, 1.0])

    with row[0]:
        topic = st.selectbox("Chủ đề", topics if topics else [""], index=safe_index(topics, st.session_state.get("topic_sel","")) if topics else 0, key="topic_sel")
    reset_if_sig_changed("sig_topic", topic, ["lesson_sel","yccd_sel","yccd_free"])

    lesson_options = sorted([x for x in filtered.loc[filtered["topic"].astype(str)==str(topic), "lesson"].dropna().astype(str).unique().tolist() if x.strip()])
    with row[1]:
        lesson = st.selectbox("Bài học", lesson_options if lesson_options else [""], index=safe_index(lesson_options, st.session_state.get("lesson_sel","")) if lesson_options else 0, key="lesson_sel")
    reset_if_sig_changed("sig_lesson", lesson, ["yccd_sel","yccd_free"])

    yccd_options = sorted([x for x in filtered.loc[(filtered["topic"].astype(str)==str(topic)) & (filtered["lesson"].astype(str)==str(lesson)), "yccd"].dropna().astype(str).unique().tolist() if x.strip()])
    with row[2]:
        if yccd_options:
            yccd = st.selectbox("YCCĐ", ["(tất cả)"] + yccd_options, index=safe_index(["(tất cả)"] + yccd_options, st.session_state.get("yccd_sel","(tất cả)")), key="yccd_sel")
            if yccd == "(tất cả)":
                yccd = ""
        else:
            yccd = st.text_input("YCCĐ", value="", placeholder="(chưa có YCCĐ)", key="yccd_free")

    with row[3]:
        qtype_level_opts = [qtype_level_label(q, lv) for q in QTYPE_ORDER for lv in LEVEL_ORDER]
        sel_qtype_level = st.selectbox("Dạng/Mức (TT27)", qtype_level_opts, index=0, key="qtype_level_sel")
    qtype, level = parse_qtype_level(sel_qtype_level)

    with row[4]:
        default_pts = float(pts.get(qtype, 0.25))
        points = round_to_step(st.number_input("Điểm", 0.0, 10.0, value=default_pts, step=0.25, key="points_one"), 0.25)

    with row[5]:
        add_btn = st.button("➕ Thêm", use_container_width=True)

    # ================== Question pick / AI ==================
    bank: Bank | None = st.session_state["bank"]
    bank_df = bank.filtered(int(grade), norm_subject(subject), norm_semester(semester)) if bank is not None else None

    def pick_from_bank():
        if bank_df is None or bank_df.empty:
            return None, {}
        sub = bank_df[
            (bank_df["topic"].astype(str)==str(topic)) &
            (bank_df["lesson"].astype(str)==str(lesson)) &
            (bank_df["qtype"].astype(str).str.upper()==qtype) &
            (bank_df["tt27_level"].astype(int)==int(level))
        ]
        if yccd:
            sub2 = sub[sub["yccd"].astype(str)==str(yccd)]
            if not sub2.empty:
                sub = sub2
        if sub.empty:
            return None, {}
        used = set(st.session_state.get("used_question_ids", set()))
        for _, r in sub.iterrows():
            qid = str(r.get("question_id",""))
            if qid and qid not in used:
                used.add(qid)
                st.session_state["used_question_ids"] = used
                return qid, {
                    "stem": str(r.get("stem","")),
                    "options": str(r.get("options","")),
                    "answer": str(r.get("answer","")),
                    "marking_guide": str(r.get("marking_guide","")),
                    "yccd": str(r.get("yccd","")),
                }
        return None, {}

    def generate_with_ai():
        mode = st.session_state.get("ai_mode","Tắt")
        if mode == "Tắt":
            raise AIError("AI đang tắt. Mở mục ⚙️ API/AI dưới tiêu đề để bật và nhập key.")
        lvl_name = LEVEL_NAME.get(int(level), f"M{level}")
        prompt = f"""Hãy tạo 01 câu hỏi cho học sinh tiểu học (CTGDPT 2018, TT27).
Lớp: {grade}
Môn: {subject}
Học kì: {semester}
Chủ đề: {topic}
Bài học: {lesson}
YCCĐ: {yccd or '(tổng hợp)'}
Dạng: {qtype}
Mức độ (TT27): {lvl_name}
Điểm: {points}

Trả về JSON đúng cấu trúc:
{{"stem":"...","options":["A...","B...","C...","D..."],"answer":"A","marking_guide":"..." }}
Nếu không phải MCQ thì options = [] .
Chỉ trả JSON, không thêm chữ khác."""

        if mode == "OpenAI-compatible":
            txt = openai_compatible_generate(
                base_url=st.session_state.get("ai_base_url","https://api.openai.com"),
                api_key=st.session_state.get("ai_api_key",""),
                model=st.session_state.get("ai_model","gpt-4o-mini"),
                prompt=prompt,
                timeout=45,
            )
        else:
            txt = gemini_ai_studio_generate(
                api_key=st.session_state.get("ai_api_key",""),
                model=st.session_state.get("gemini_model","gemini-2.5-flash"),
                prompt=prompt,
                timeout=45,
            )
        return json.loads(txt)

    if add_btn:
        items = st.session_state["draft_items"]
        next_qno = 1 if not items else max(int(x.get("qno",0)) for x in items) + 1

        qid, payload = pick_from_bank()
        stem = payload.get("stem","")
        options = payload.get("options","")
        answer = payload.get("answer","")
        guide = payload.get("marking_guide","")
        yccd_final = yccd or payload.get("yccd","")

        if qid is None:
            # do NOT auto call AI if AI is off; allow user to click AI later
            try:
                obj = generate_with_ai()
                stem = obj.get("stem","")
                opts = obj.get("options", [])
                options = json.dumps(opts, ensure_ascii=False) if isinstance(opts, list) else str(opts)
                answer = obj.get("answer","")
                guide = obj.get("marking_guide","")
                qid = f"AI_{grade}_{norm_subject(subject)}_{norm_semester(semester)}_{qtype}_M{level}_{next_qno:03d}"
                st.success("✅ Đã tạo câu bằng AI (do kho không có câu phù hợp).")
            except Exception as e:
                st.warning(f"Kho không có câu phù hợp và AI chưa tạo được: {e}")
                qid = None

        st.session_state["draft_items"].append({
            "qno": next_qno,
            "topic": topic,
            "lesson": lesson,
            "yccd": yccd_final,
            "qtype": qtype,
            "level": int(level),
            "points": float(points),
            "question_id": qid,
            "stem": stem,
            "options": options,
            "answer": answer,
            "marking_guide": guide,
        })

    st.markdown("---")
    left, right = st.columns([2.1, 1.2], gap="large")

    with left:
        st.markdown("### Danh sách câu (xem & kiểm tra nhanh)")
        items = st.session_state["draft_items"]
        if items:
            show = pd.DataFrame([{
                "Câu": x.get("qno"),
                "Chủ đề": x.get("topic"),
                "Bài": x.get("lesson"),
                "YCCĐ": x.get("yccd"),
                "Dạng": x.get("qtype"),
                "Mức": f"M{x.get('level')}",
                "Điểm": x.get("points"),
                "ID": x.get("question_id") or "",
                "Nội dung": (x.get("stem") or "")[:80] + ("..." if (x.get("stem") or "") and len(x.get("stem") or "")>80 else "")
            } for x in items]).sort_values("Câu")
            st.dataframe(show, use_container_width=True, height=520, hide_index=True)
        else:
            st.info("Chưa có câu nào.")

    with right:
        st.markdown("### 📌 Tổng hợp")
        items = st.session_state["draft_items"]
        total_q = len(items)
        total_pts = sum(float(x.get("points",0)) for x in items) if items else 0.0

        st.markdown(
            f'<span class="pill">Tổng câu: <b>{total_q}</b></span>'
            f'<span class="pill">Tổng điểm: <b>{total_pts:.2f}</b></span>',
            unsafe_allow_html=True
        )

        colA, colB = st.columns(2)
        with colA:
            if st.button("🗑️ Xóa hết", use_container_width=True):
                st.session_state["draft_items"] = []
                st.session_state["used_question_ids"] = set()
        with colB:
            if st.button("🔁 Reset luồng chọn", use_container_width=True):
                for k in ["topic_sel","lesson_sel","yccd_sel","yccd_free"]:
                    if k in st.session_state:
                        del st.session_state[k]
                st.success("Đã reset luồng chọn.")

# ================= TAB: EXPORT =================
with tab_xuat:
    st.subheader("Xuất Word")
    items = st.session_state.get("draft_items", [])
    docx_files = list_template_docx()
    xlsx_files = list_template_xlsx()

    if not items:
        st.warning("Chưa có câu trong đề. Hãy tạo ở tab 🧩 Soạn đề.")
    else:
        if not docx_files or not xlsx_files:
            st.error("Thiếu template trong thư mục templates/.")
        else:
            # Ẩn hẳn phần chọn template nếu chỉ có 1 bộ (mặc định)
            spec_name = docx_files[0]
            matrix_name = xlsx_files[0]
            if len(docx_files) > 1:
                spec_name = st.selectbox("Template Bảng đặc tả", docx_files, index=0)
            if len(xlsx_files) > 1:
                matrix_name = st.selectbox("Template Ma trận", xlsx_files, index=0)

            title = st.text_input("Tiêu đề đề (hiển thị trong Word)", value="ĐỀ KIỂM TRA CUỐI KÌ")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Xuất Bảng đặc tả.docx", type="primary", use_container_width=True):
                    try:
                        matrix = load_matrix_template(os.path.join(TEMPLATE_DIR, matrix_name), total_points=float(10.0))
                        out_path = os.path.join("outputs","Bang_dac_ta.docx")
                        export_spec_from_template(os.path.join(TEMPLATE_DIR, spec_name), out_path, matrix, items)
                        with open(out_path, "rb") as f:
                            st.download_button("⬇️ Tải Bang_dac_ta.docx", f, file_name="Bang_dac_ta.docx", use_container_width=True)
                        st.success("✅ Đã xuất Bảng đặc tả.")
                    except Exception as e:
                        st.error(f"Lỗi xuất đặc tả: {e}")
            with col2:
                if st.button("Xuất De.docx", use_container_width=True):
                    try:
                        out_path = os.path.join("outputs","De.docx")
                        export_exam_docx(out_path, title=title, total_points=float(10.0), items=items)
                        with open(out_path, "rb") as f:
                            st.download_button("⬇️ Tải De.docx", f, file_name="De.docx", use_container_width=True)
                        st.success("✅ Đã xuất Đề.")
                    except Exception as e:
                        st.error(f"Lỗi xuất đề: {e}")

# ================= TAB: AI =================
