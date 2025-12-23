\
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import random
import pandas as pd

from .utils import QTYPE_ORDER, LEVEL_ORDER, fmt_ranges
from .matrix_template import LessonRow, MatrixTemplate
from .question_bank import Bank

@dataclass
class Slot:
    qno: int
    topic: str
    lesson: str
    qtype: str
    level: int
    points: float
    question_id: Optional[str] = None

def build_slots(template: MatrixTemplate, points_per_qtype: Dict[str,float]) -> List[Slot]:
    """Create slots from matrix counts. Question numbering follows row order, then qtype order, then level order."""
    slots: List[Slot] = []
    qno = 1
    for row in template.lessons:
        for qtype in QTYPE_ORDER:
            for level in LEVEL_ORDER:
                n = int(row.counts.get((qtype, level), 0))
                for _ in range(n):
                    slots.append(Slot(
                        qno=qno,
                        topic=row.topic,
                        lesson=row.lesson,
                        qtype=qtype,
                        level=level,
                        points=float(points_per_qtype.get(qtype, 0.25)),
                    ))
                    qno += 1
    return slots

def assign_questions(slots: List[Slot], bank: Bank, grade: int, subject: str, semester: str, seed: int = 42) -> Tuple[List[Slot], List[str]]:
    """Assign question IDs to slots with strict TT27 lock: same qtype+level. No fallback; missing => warning."""
    rng = random.Random(seed)
    df = bank.df
    sub = df[(df["grade"]==grade) & (df["subject"].str.lower()==subject.lower()) & (df["semester"].str.lower()==semester.lower())]
    warnings: List[str] = []
    used_ids = set()
    # Pre-bucket
    buckets: Dict[Tuple[str,str,str,int], List[str]] = {}
    for _, r in sub.iterrows():
        key = (r["topic"], r["lesson"], r["qtype"], int(r["tt27_level"]))
        buckets.setdefault(key, []).append(r["question_id"])
    for k in buckets:
        rng.shuffle(buckets[k])

    for s in slots:
        key = (s.topic, s.lesson, s.qtype, int(s.level))
        cand = buckets.get(key, [])
        chosen = None
        while cand:
            qid = cand.pop()
            if qid not in used_ids:
                chosen = qid
                used_ids.add(qid)
                break
        if chosen is None:
            warnings.append(f"Thiếu câu: {s.topic} | {s.lesson} | {s.qtype} | M{s.level} (q#{s.qno})")
        s.question_id = chosen
    return slots, warnings

def slot_map_to_numbers(slots: List[Slot]) -> Dict[Tuple[str,str,str,int], List[int]]:
    m: Dict[Tuple[str,str,str,int], List[int]] = {}
    for s in slots:
        key = (s.topic, s.lesson, s.qtype, int(s.level))
        m.setdefault(key, []).append(s.qno)
    return m

def totals_by_cell(template: MatrixTemplate) -> Dict[Tuple[str,int], int]:
    tot: Dict[Tuple[str,int], int] = {}
    for row in template.lessons:
        for qtype in QTYPE_ORDER:
            for level in LEVEL_ORDER:
                tot[(qtype, level)] = tot.get((qtype, level), 0) + int(row.counts.get((qtype, level), 0))
    return tot
