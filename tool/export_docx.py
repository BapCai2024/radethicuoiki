from __future__ import annotations
import os
from copy import deepcopy
from typing import List
from docx import Document

from .utils import QTYPE_ORDER, LEVEL_ORDER, fmt_ranges
from .generation import DraftItem
from .matrix_template import MatrixTemplate

DOCX_QTYPE_TO_COL_START = {
    "MCQ": 4,
    "TF": 7,
    "MATCH": 10,
    "FILL": 13,
    "ESSAY": 16,
}

def _delete_row(table, row_idx: int):
    tbl = table._tbl
    tr = table.rows[row_idx]._tr
    tbl.remove(tr)

def _numbers_map(items: List[DraftItem]):
    m = {}
    for it in items:
        key = (it.topic, it.lesson, it.qtype, int(it.level))
        m.setdefault(key, []).append(int(it.qno))
    return m

def export_spec_from_template(template_docx_path: str, output_path: str, matrix: MatrixTemplate, items: List[DraftItem], total_points: float = 10.0) -> str:
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
        new_tr = deepcopy(style_tr)
        table._tbl.insert(len(table.rows)-totals_rows, new_tr)

    m = _numbers_map(items)

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
            for level in LEVEL_ORDER:
                col = base + (level-1)
                nums = m.get((lesson.topic, lesson.lesson, qtype, level), [])
                txt = fmt_ranges(nums)
                cells[col].text = f"Câu {txt}" if txt else ""

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc.save(output_path)
    return output_path

def export_exam_docx(output_path: str, items: List[DraftItem], bank_df, title: str, total_points: float = 10.0) -> str:
    import json
    doc = Document()
    p = doc.add_paragraph(title)
    p.runs[0].bold = True
    doc.add_paragraph(f"Thang điểm: {total_points:g}").italic = True
    doc.add_paragraph("")

    idx = {str(r["question_id"]): r for _, r in bank_df.iterrows()}

    for it in sorted(items, key=lambda x: int(x.qno)):
        p = doc.add_paragraph()
        p.add_run(f"Câu {it.qno}. ").bold = True
        p.add_run(f"({it.points:g} điểm) ")
        if it.question_id and it.question_id in idx:
            r = idx[it.question_id]
            p.add_run(str(r.get("stem","")))
            if str(r.get("qtype","")).upper() == "MCQ":
                try:
                    opts = json.loads(r.get("options","[]")) if r.get("options") else []
                except Exception:
                    opts = []
                letters = ["A","B","C","D","E","F"]
                for j, opt in enumerate(opts[:6]):
                    doc.add_paragraph(f"{letters[j]}. {opt}")
            else:
                doc.add_paragraph("........................................................................")
        else:
            p.add_run("[CHƯA CÓ CÂU PHÙ HỢP — vui lòng bổ sung kho hoặc đổi tiêu chí]")
        doc.add_paragraph("")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc.save(output_path)
    return output_path
