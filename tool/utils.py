\
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Dict
import math

QTYPE_ORDER = ["MCQ", "TF", "MATCH", "FILL", "ESSAY"]
LEVEL_ORDER = [1, 2, 3]

def round_to_step(x: float, step: float = 0.25) -> float:
    """Round to nearest step (e.g., 0.25) with stable float handling."""
    if step <= 0:
        return float(x)
    return round(round(x / step) * step + 1e-12, 10)

def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

def fmt_ranges(nums: List[int]) -> str:
    """Format a list like [1,2,3,5,7,8] -> '1–3; 5; 7–8'"""
    nums = sorted(set(int(n) for n in nums if n is not None))
    if not nums:
        return ""
    ranges: List[Tuple[int,int]] = []
    s = e = nums[0]
    for n in nums[1:]:
        if n == e + 1:
            e = n
        else:
            ranges.append((s,e))
            s = e = n
    ranges.append((s,e))
    parts = []
    for a,b in ranges:
        if a == b:
            parts.append(f"{a}")
        else:
            parts.append(f"{a}–{b}")
    return "; ".join(parts)

def safe_int(x, default: int = 0) -> int:
    try:
        if x is None or x == "":
            return default
        return int(float(x))
    except Exception:
        return default
