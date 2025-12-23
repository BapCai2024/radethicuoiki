from __future__ import annotations
from typing import List, Tuple

QTYPE_ORDER = ["MCQ", "TF", "MATCH", "FILL", "ESSAY"]
LEVEL_ORDER = [1, 2, 3]
LEVEL_NAME = {1: "Biết (M1)", 2: "Hiểu (M2)", 3: "VD (M3)"}

def round_to_step(x: float, step: float = 0.25) -> float:
    if step <= 0:
        return float(x)
    return round(round(float(x) / step) * step + 1e-12, 10)

def safe_int(x, default: int = 0) -> int:
    try:
        if x is None or x == "":
            return default
        return int(float(x))
    except Exception:
        return default

def fmt_ranges(nums: List[int]) -> str:
    nums = sorted(set(int(n) for n in nums if n is not None))
    if not nums:
        return ""
    ranges: List[Tuple[int, int]] = []
    s = e = nums[0]
    for n in nums[1:]:
        if n == e + 1:
            e = n
        else:
            ranges.append((s, e))
            s = e = n
    ranges.append((s, e))
    parts = []
    for a, b in ranges:
        parts.append(f"{a}" if a == b else f"{a}–{b}")
    return "; ".join(parts)

def qtype_level_label(qtype: str, level: int) -> str:
    return f"{qtype} • {LEVEL_NAME.get(int(level), f'M{level}')}"

def parse_qtype_level(label: str) -> tuple[str, int]:
    left = (label.split("•")[0] or "").strip().upper()
    if "(M1)" in label: return left, 1
    if "(M2)" in label: return left, 2
    if "(M3)" in label: return left, 3
    for d in ["1","2","3"]:
        if f"M{d}" in label: return left, int(d)
    return left, 1
