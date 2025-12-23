from __future__ import annotations
from typing import List
import os, json
from copy import deepcopy
from docx import Document
from .utils import QTYPE_ORDER, LEVEL_ORDER, fmt_ranges
from .matrix_template import MatrixTemplate

DOCX_QTYPE_TO_COL_START = {"MCQ": 4, "TF": 7, "MATCH": 10, "FILL": 13, "ESSAY": 16}

def _delete_row(table, row_idx: int):
    tbl = table._tbl
    tr = table.rows[row_idx]._tr
    tbl.remove(tr)

def export_spec_from_template(template_docx_path: str, output_path: str, matrix: MatrixTemplate, items: List[dict]) -> str:
    doc = Document(template_docx_path)
    table = doc.tables[0]

    header_rows = 4
    totals_rows = 3
    current_rows = len(table.rows)
    data_start = header_rows
    data_end = current_rows - totals_rows

    for ridx in range(data_end-1, data_start-1, -1):
        _delete_row(table, ridx)

    style_tr = deepcopy(table.rows[header_rows-1]._tr)
    for _ in matrix.lessons:
        table._tbl.insert(len(table.rows)-totals_rows, deepcopy(style_tr))

    m = {}
    for it in items:
        key = (it.get("topic",""), it.get("lesson",""), it.get("qtype",""), int(it.get("level",1)))
        m.setdefault(key, []).append(int(it.get("qno",0)))

    for i, lesson in enumerate(matrix.lessons):
        r = data_start + i
        cells = table.rows[r].cells
        cells[0].text = str(lesson.tt)
        cells[1].text = lesson.topic or ""
        cells[2].text = lesson.lesson or ""
        if len(cells) > 3 and ("…" in cells[3].text or "." in cells[3].text):
            cells[3].text = ""

        for qtype in QTYPE_ORDER:
            base = DOCX_QTYPE_TO_COL_START[qtype]
            for lv in LEVEL_ORDER:
                col = base + (lv-1)
                nums = m.get((lesson.topic, lesson.lesson, qtype, lv), [])
                txt = fmt_ranges(nums)
                cells[col].text = f"Câu {txt}" if txt else ""

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc.save(output_path)
    return output_path

def export_exam_docx(output_path: str, title: str, total_points: float, items: List[dict]) -> str:
    doc = Document()
    p = doc.add_paragraph(title)
    p.runs[0].bold = True
    doc.add_paragraph(f"Thang điểm: {total_points:g}").italic = True
    doc.add_paragraph("")

    for it in sorted(items, key=lambda x: int(x.get("qno",0))):
        qno = int(it.get("qno",0))
        pts = it.get("points", 0)
        stem = (it.get("stem","") or "").strip()
        qtype = (it.get("qtype","") or "").upper()
        options = it.get("options","")

        p = doc.add_paragraph()
        p.add_run(f"Câu {qno}. ").bold = True
        p.add_run(f"({pts:g} điểm) ")
        p.add_run(stem if stem else "[Chưa có nội dung câu]")

        if qtype == "MCQ" and options:
            try:
                opts = json.loads(options) if isinstance(options, str) else options
            except Exception:
                opts = []
            letters = ["A","B","C","D","E","F"]
            for i2, opt in enumerate(list(opts)[:6]):
                doc.add_paragraph(f"{letters[i2]}. {opt}")
        else:
            doc.add_paragraph("........................................................................")
        doc.add_paragraph("")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc.save(output_path)
    return output_path
