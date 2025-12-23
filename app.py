from __future__ import annotations
import os
import json
import streamlit as st
import pandas as pd

from tool.ui_common import inject_css, sidebar_brand
from tool.utils import QTYPE_ORDER, LEVEL_ORDER, LEVEL_NAME, round_to_step, qtype_level_label, parse_qtype_level
from tool.matrix_template import load_matrix_template
from tool.question_bank import load_bank_from_upload, Bank
from tool.data_loader import load_catalog_csv, try_parse_catalog_from_excel
from tool.ai_provider import openai_compatible_generate, gemini_ai_studio_generate, AIError
from tool.export_docx import export_spec_from_template, export_exam_docx

st.set_page_config(page_title="Tool HỖ TRỢ RA ĐỀ", layout="wide")
inject_css()
sidebar_brand()

# --- session
st.session_state.setdefault("bank", None)
st.session_state.setdefault("catalog_df", None)
st.session_state.setdefault("draft_items", [])
st.session_state.setdefault("used_question_ids", set())
st.session_state.setdefault("ai_mode", "Tắt")
st.session_state.setdefault("ai_api_key", "")
st.session_state.setdefault("ai_base_url", "https://api.openai.com")
st.session_state.setdefault("ai_model", "gpt-4o-mini")
st.session_state.setdefault("gemini_model", "gemini-1.5-flash")
st.session_state.setdefault("points_per_qtype", {"MCQ":0.5,"TF":0.5,"MATCH":1.0,"FILL":1.0,"ESSAY":1.0})

# --- hero
st.markdown('<div class="app-hero">', unsafe_allow_html=True)
st.markdown("# 🧩 Tool HỖ TRỢ RA ĐỀ")
st.markdown('<div class="muted">Chọn Lớp/Môn ở trên → dòng ngang: <b>Chủ đề – Bài – YCCĐ – Dạng/Mức – Điểm – Thêm</b> → xem trước → Xuất Word.<br/>TT27 khóa mức: chọn M1 thì chỉ lấy M1 (không nhảy mức).</div>', unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)
st.write("")

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")
xlsx_files = [f for f in os.listdir(TEMPLATE_DIR) if f.lower().endswith(".xlsx")]
docx_files = [f for f in os.listdir(TEMPLATE_DIR) if f.lower().endswith(".docx")]
default_xlsx = os.path.join(TEMPLATE_DIR, xlsx_files[0]) if xlsx_files else None

tab_soande, tab_dulieu, tab_xuat, tab_ai = st.tabs(["🧩 Soạn đề", "📚 Dữ liệu", "📤 Xuất Word", "⚙️ AI (API)"])

with tab_soande:
    st.subheader("Thiết lập đề")
    top = st.columns([1.0, 1.2, 1.0, 1.0, 1.2])
    with top[0]:
        grade = st.selectbox("Lớp", [1,2,3,4,5], index=2)
    with top[1]:
        subject = st.selectbox("Môn", ["Tin","Toán","Tiếng Việt","Khoa học","Lịch sử - Địa lý","Đạo đức","Công nghệ","Âm nhạc","Mĩ thuật"], index=0)
    with top[2]:
        semester = st.selectbox("Học kì", ["HK1","HK2"], index=0)
    with top[3]:
        exam_type = st.selectbox("Loại KT", ["GK","CKI","CKII"], index=1)
    with top[4]:
        total_points = st.number_input("Tổng điểm", min_value=1.0, max_value=20.0, value=10.0, step=0.25)

    st.markdown("### Điểm/1 câu (bước 0,25)")
    pts = st.session_state["points_per_qtype"]
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

    # load catalog once
    if st.session_state["catalog_df"] is None:
        try:
            st.session_state["catalog_df"] = load_catalog_csv(os.path.join("data","yccd_catalog.csv"))
        except Exception:
            st.session_state["catalog_df"] = pd.DataFrame(columns=["grade","subject","semester","topic","lesson","yccd"])

    catalog = st.session_state["catalog_df"].copy()
    fcat = catalog[
        (catalog["grade"].fillna(-1).astype(int) == int(grade)) &
        (catalog["subject"].str.lower() == str(subject).lower()) &
        (catalog["semester"].str.lower() == str(semester).lower())
    ].copy()

    fallback_topics = sorted(fcat["topic"].dropna().astype(str).unique().tolist()) if not fcat.empty else []
    matrix = None
    if not fallback_topics and default_xlsx:
        try:
            matrix = load_matrix_template(default_xlsx, total_points=float(total_points))
            fallback_topics = sorted({l.topic for l in matrix.lessons if l.topic})
            st.info("Đang dùng dữ liệu tạm từ template ma trận (chưa có YCCĐ). Muốn đủ YCCĐ → tab 📚 Dữ liệu.")
        except Exception as e:
            st.error(f"Lỗi đọc ma trận: {e}")

    st.markdown("### Thao tác nhanh (cùng một dòng ngang)")
    row = st.columns([1.2, 1.6, 1.6, 1.4, 0.9, 1.0])
    with row[0]:
        sel_topic = st.selectbox("Chủ đề", fallback_topics, index=0 if fallback_topics else None)
    with row[1]:
        if not fcat.empty:
            lessons = sorted(fcat.loc[fcat["topic"].astype(str)==str(sel_topic),"lesson"].dropna().astype(str).unique().tolist())
        else:
            lessons = sorted([l.lesson for l in (matrix.lessons if matrix else []) if l.topic==sel_topic])
        sel_lesson = st.selectbox("Bài học", lessons, index=0 if lessons else None)
    with row[2]:
        if not fcat.empty:
            yccds = sorted(fcat.loc[(fcat["topic"].astype(str)==str(sel_topic)) & (fcat["lesson"].astype(str)==str(sel_lesson)),"yccd"].dropna().astype(str).unique().tolist())
            yccds = [y for y in yccds if y.strip()]
        else:
            yccds = []
        if yccds:
            sel_yccd = st.selectbox("YCCĐ", ["(tất cả)"] + yccds, index=0)
            if sel_yccd == "(tất cả)":
                sel_yccd = ""
        else:
            sel_yccd = st.text_input("YCCĐ", value="", placeholder="(chưa có YCCĐ)")
    with row[3]:
        qtype_level_opts = [qtype_level_label(q, lv) for q in QTYPE_ORDER for lv in LEVEL_ORDER]
        sel_qtype_level = st.selectbox("Dạng/Mức (TT27)", qtype_level_opts, index=0)
    qtype, level = parse_qtype_level(sel_qtype_level)
    with row[4]:
        default_pts = float(pts.get(qtype, 0.25))
        sel_points = round_to_step(st.number_input("Điểm", 0.0, 10.0, value=default_pts, step=0.25))
    with row[5]:
        add_btn = st.button("➕ Thêm", use_container_width=True)

    bank: Bank | None = st.session_state["bank"]
    bank_df = bank.filtered(int(grade), subject, semester) if bank is not None else None

    def pick_from_bank():
        if bank_df is None or bank_df.empty:
            return None, {}
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
            raise AIError("AI đang tắt.")
        lvl_name = LEVEL_NAME.get(int(level), f"M{level}")
        prompt = f"""Hãy tạo 01 câu hỏi cho học sinh tiểu học (CTGDPT 2018, TT27).
Lớp: {grade}
Môn: {subject}
Học kì: {semester}
Chủ đề: {sel_topic}
Bài học: {sel_lesson}
YCCĐ: {sel_yccd or '(tổng hợp)'}
Dạng: {qtype}
Mức độ (TT27): {lvl_name}
Điểm: {sel_points}

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
                model=st.session_state.get("gemini_model","gemini-1.5-flash"),
                prompt=prompt,
                timeout=45,
            )
        obj = json.loads(txt)
        return obj

    if add_btn:
        items = st.session_state["draft_items"]
        next_qno = 1 if not items else max(int(x.get("qno",0)) for x in items) + 1

        qid, payload = pick_from_bank()
        stem = payload.get("stem","")
        options = payload.get("options","")
        answer = payload.get("answer","")
        guide = payload.get("marking_guide","")
        yccd_final = sel_yccd or payload.get("yccd","")

        if qid is None:
            try:
                obj = generate_with_ai()
                stem = obj.get("stem","")
                opts = obj.get("options", [])
                options = json.dumps(opts, ensure_ascii=False) if isinstance(opts, list) else str(opts)
                answer = obj.get("answer","")
                guide = obj.get("marking_guide","")
                qid = f"AI_{grade}_{subject}_{semester}_{qtype}_M{level}_{next_qno:03d}"
                st.success("Đã tạo câu bằng AI (do kho không có câu phù hợp).")
            except Exception as e:
                st.warning(f"Kho không có câu phù hợp và AI chưa tạo được: {e}")
                qid = None

        st.session_state["draft_items"].append({
            "qno": next_qno,
            "topic": sel_topic,
            "lesson": sel_lesson,
            "yccd": yccd_final,
            "qtype": qtype,
            "level": int(level),
            "points": float(sel_points),
            "question_id": qid,
            "stem": stem,
            "options": options,
            "answer": answer,
            "marking_guide": guide,
        })

    st.markdown("---")
    left, right = st.columns([2.1, 1.2], gap="large")

    with left:
        st.markdown("### Ma trận (GV xem để bám theo)")
        if default_xlsx:
            try:
                matrix2 = load_matrix_template(default_xlsx, total_points=float(total_points))
                rows = []
                for lr in matrix2.lessons:
                    r = {"TT": lr.tt, "Chủ đề": lr.topic, "Bài": lr.lesson, "Số tiết": lr.periods}
                    for q in QTYPE_ORDER:
                        for lv in LEVEL_ORDER:
                            r[qtype_level_label(q, lv)] = int(lr.counts.get((q, lv), 0))
                    rows.append(r)
                dfm = pd.DataFrame(rows)
                st.dataframe(dfm, use_container_width=True, height=460, hide_index=True)
            except Exception as e:
                st.error(f"Lỗi hiển thị ma trận: {e}")
        else:
            st.info("Chưa có template ma trận trong templates/.")

    with right:
        st.markdown("### 📌 Đề hiện tại")
        items = st.session_state["draft_items"]
        total_q = len(items)
        total_pts = sum(float(x.get("points",0)) for x in items) if items else 0.0
        m1 = sum(1 for x in items if int(x.get("level",1))==1)
        m2 = sum(1 for x in items if int(x.get("level",1))==2)
        m3 = sum(1 for x in items if int(x.get("level",1))==3)

        st.markdown(
            f'<span class="pill">Tổng câu: <b>{total_q}</b></span>'
            f'<span class="pill">Tổng điểm: <b>{total_pts:.2f}</b></span><br/>'
            f'<span class="pill">M1: <b>{m1}</b></span>'
            f'<span class="pill">M2: <b>{m2}</b></span>'
            f'<span class="pill">M3: <b>{m3}</b></span>',
            unsafe_allow_html=True
        )
        if abs(total_pts - float(total_points)) > 1e-6:
            st.markdown(f'<div class="danger">⚠️ Lệch tổng điểm: {total_pts-float(total_points):+.2f}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="ok">✅ Tổng điểm khớp</div>', unsafe_allow_html=True)

        colA, colB = st.columns(2)
        with colA:
            if st.button("🗑️ Xóa hết", use_container_width=True):
                st.session_state["draft_items"] = []
                st.session_state["used_question_ids"] = set()
        with colB:
            if st.button("📌 Lưu tạm", use_container_width=True):
                st.success("Đã lưu tạm trong session. (Muốn lưu file JSON → mình sẽ thêm ở bản sau)")

        if items:
            show = pd.DataFrame([{
                "Câu": x.get("qno"),
                "Dạng": x.get("qtype"),
                "Mức": f"M{x.get('level')}",
                "Điểm": x.get("points"),
                "Bài": x.get("lesson"),
                "ID": x.get("question_id") or "(trống)",
            } for x in items]).sort_values("Câu")
            st.dataframe(show, use_container_width=True, height=300, hide_index=True)
        else:
            st.info("Chưa có câu nào.")

with tab_dulieu:
    st.subheader("Nạp dữ liệu (YCCĐ + Kho câu hỏi)")
    st.info("File KHGD bạn gửi là .rar (Streamlit Cloud không giải nén được). Hãy xuất ra Excel/CSV hoặc nén .zip rồi upload.")

    col1, col2 = st.columns(2, gap="large")
    with col1:
        st.markdown("### YCCĐ (Chủ đề – Bài – YCCĐ)")
        upl = st.file_uploader("Upload file YCCĐ (CSV/XLSX)", type=["csv","xlsx","xls"], key="upl_yccd")
        if upl is not None:
            try:
                if upl.name.lower().endswith(".csv"):
                    df = pd.read_csv(upl)
                else:
                    df = try_parse_catalog_from_excel(upl)
                st.session_state["catalog_df"] = df
                os.makedirs("data", exist_ok=True)
                df.to_csv(os.path.join("data","yccd_catalog.csv"), index=False, encoding="utf-8-sig")
                st.success("Đã nạp YCCĐ và lưu vào data/yccd_catalog.csv")
                st.dataframe(df.head(200), use_container_width=True, height=260)
            except Exception as e:
                st.error(f"Lỗi nạp YCCĐ: {e}")
        else:
            try:
                df = load_catalog_csv(os.path.join("data","yccd_catalog.csv"))
                st.session_state["catalog_df"] = df
                st.caption("Đang dùng catalog hiện có trong data/yccd_catalog.csv")
                st.dataframe(df.head(120), use_container_width=True, height=260)
            except Exception:
                st.warning("Chưa có catalog.")

    with col2:
        st.markdown("### Kho câu hỏi")
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
                    st.success("Đã nạp kho câu hỏi.")
                    st.dataframe(bank.df.head(200), use_container_width=True, height=260)
            except Exception as e:
                st.error(f"Lỗi nạp kho câu hỏi: {e}")
        else:
            st.caption("Bạn có thể thử file mẫu: data/sample_question_bank.csv")

with tab_xuat:
    st.subheader("Xuất Word")
    items = st.session_state.get("draft_items", [])
    if not items:
        st.warning("Chưa có câu trong đề. Hãy tạo ở tab 🧩 Soạn đề.")
    else:
        if not docx_files or not xlsx_files:
            st.error("Thiếu template trong thư mục templates/.")
        else:
            spec_name = st.selectbox("Template Bảng đặc tả", docx_files, index=0)
            matrix_name = st.selectbox("Template Ma trận (ẩn đường dẫn)", xlsx_files, index=0)
            title = st.text_input("Tiêu đề đề (hiển thị trong Word)", value="ĐỀ KIỂM TRA CUỐI KÌ")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Xuất Bảng đặc tả.docx", type="primary", use_container_width=True):
                    try:
                        matrix = load_matrix_template(os.path.join(TEMPLATE_DIR, matrix_name), total_points=float(total_points))
                        out_path = os.path.join("outputs","Bang_dac_ta.docx")
                        export_spec_from_template(os.path.join(TEMPLATE_DIR, spec_name), out_path, matrix, items)
                        with open(out_path, "rb") as f:
                            st.download_button("⬇️ Tải Bang_dac_ta.docx", f, file_name="Bang_dac_ta.docx", use_container_width=True)
                        st.success("Đã xuất Bảng đặc tả.")
                    except Exception as e:
                        st.error(f"Lỗi xuất đặc tả: {e}")
            with col2:
                if st.button("Xuất De.docx", use_container_width=True):
                    try:
                        out_path = os.path.join("outputs","De.docx")
                        export_exam_docx(out_path, title=title, total_points=float(total_points), items=items)
                        with open(out_path, "rb") as f:
                            st.download_button("⬇️ Tải De.docx", f, file_name="De.docx", use_container_width=True)
                        st.success("Đã xuất Đề.")
                    except Exception as e:
                        st.error(f"Lỗi xuất đề: {e}")

with tab_ai:
    st.subheader("Cấu hình AI (API)")
    st.caption("Bật AI để: khi kho câu hỏi không có câu phù hợp, tool tự tạo câu theo YCCĐ + TT27. Nếu AI lỗi, tool chỉ báo (không crash).")

    mode_ui = st.selectbox("Chế độ", ["Tắt", "OpenAI-compatible", "AI Studio (Gemini)"], index=0)
    if mode_ui == "Tắt":
        st.session_state["ai_mode"] = "Tắt"
    elif mode_ui == "OpenAI-compatible":
        st.session_state["ai_mode"] = "OpenAI-compatible"
    else:
        st.session_state["ai_mode"] = "Gemini"

    st.session_state["ai_api_key"] = st.text_input("API Key", type="password", value=st.session_state.get("ai_api_key",""))

    if st.session_state["ai_mode"] == "OpenAI-compatible":
        st.session_state["ai_base_url"] = st.text_input("Base URL", value=st.session_state.get("ai_base_url","https://api.openai.com"))
        st.session_state["ai_model"] = st.text_input("Model", value=st.session_state.get("ai_model","gpt-4o-mini"))
    elif st.session_state["ai_mode"] == "Gemini":
        st.session_state["gemini_model"] = st.text_input("Gemini model", value=st.session_state.get("gemini_model","gemini-1.5-flash"))

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Test API", use_container_width=True):
            try:
                if st.session_state["ai_mode"] == "OpenAI-compatible":
                    out = openai_compatible_generate(st.session_state["ai_base_url"], st.session_state["ai_api_key"], st.session_state["ai_model"], "Trả lời đúng 1 từ: OK", timeout=25)
                elif st.session_state["ai_mode"] == "Gemini":
                    out = gemini_ai_studio_generate(st.session_state["ai_api_key"], st.session_state["gemini_model"], "Trả lời đúng 1 từ: OK", timeout=25)
                else:
                    out = "AI đang tắt."
                st.success(f"Kết quả: {out[:80]}")
            except Exception as e:
                st.error(f"Test lỗi: {e}")
    with col2:
        st.info("Gợi ý: Với Streamlit Cloud, nên lưu key trong Secrets (Settings → Secrets) để an toàn.")
