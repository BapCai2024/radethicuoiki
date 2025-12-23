from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import random
import pandas as pd

from .utils import QTYPE_ORDER, LEVEL_ORDER
from .matrix_template import MatrixTemplate
from .question_bank import Bank

@dataclass
class DraftItem:
    qno: int
    topic: str
    lesson: str
    yccd: str
    qtype: str
    level: int
    points: float
    question_id: Optional[str] = None
    stem: str = ""

def build_slots_from_matrix(matrix: MatrixTemplate, points_per_qtype: Dict[str,float]) -> List[DraftItem]:
    items: List[DraftItem] = []
    qno = 1
    for row in matrix.lessons:
        for qtype in QTYPE_ORDER:
            for level in LEVEL_ORDER:
                n = int(row.counts.get((qtype, level), 0))
                for _ in range(n):
                    items.append(DraftItem(
                        qno=qno,
                        topic=row.topic,
                        lesson=row.lesson,
                        yccd="",
                        qtype=qtype,
                        level=level,
                        points=float(points_per_qtype.get(qtype, 0.25)),
                    ))
                    qno += 1
    return items

def _pick_question(df: pd.DataFrame, topic: str, lesson: str, yccd: str, qtype: str, level: int, used: set[str], rng: random.Random):
    sub = df[
        (df["topic"].astype(str)==str(topic)) &
        (df["lesson"].astype(str)==str(lesson)) &
        (df["qtype"].astype(str).str.upper()==str(qtype).upper()) &
        (df["tt27_level"].astype(int)==int(level))
    ]
    if yccd:
        sub2 = sub[sub["yccd"].astype(str)==str(yccd)]
        if not sub2.empty:
            sub = sub2
    if sub.empty:
        return None
    idxs = list(sub.index)
    rng.shuffle(idxs)
    for idx in idxs:
        qid = str(sub.loc[idx, "question_id"])
        if qid not in used:
            return sub.loc[idx]
    return None

def assign_auto(items: List[DraftItem], bank: Bank, grade: int, subject: str, semester: str, seed: int = 42) -> Tuple[List[DraftItem], List[str]]:
    df = bank.filtered(grade, subject, semester)
    rng = random.Random(seed)
    warnings: List[str] = []
    used_ids = set(i.question_id for i in items if i.question_id)
    for it in items:
        if it.question_id:
            continue
        row = _pick_question(df, it.topic, it.lesson, it.yccd, it.qtype, it.level, used_ids, rng)
        if row is None:
            warnings.append(f"Thiếu câu: {it.topic} | {it.lesson} | {it.qtype} | M{it.level} (q#{it.qno})")
            continue
        it.question_id = str(row.get("question_id",""))
        it.stem = str(row.get("stem",""))
        it.yccd = it.yccd or str(row.get("yccd",""))
        used_ids.add(it.question_id)
    return items, warnings
