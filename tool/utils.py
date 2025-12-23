from __future__ import annotations
from typing import List, Tuple
import re
import unicodedata

QTYPE_ORDER = ["MCQ", "TF", "MATCH", "FILL", "ESSAY"]
LEVEL_ORDER = [1, 2, 3]
LEVEL_NAME = {1: "Biết (M1)", 2: "Hiểu (M2)", 3: "Vận dụng (M3)"}

def normalize_key(s: str) -> str:
    """Normalize Vietnamese strings for matching (remove accents, lower, collapse spaces)."""
    s = "" if s is None else str(s)
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = s.lower().strip()
    s = re.sub(r"[\-_/]+", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s

SUBJECT_ALIASES = {
    "tin": "Tin",
    "tin hoc": "Tin",
    "tinhoc": "Tin",
    "informatique": "Tin",
    "toan": "Toán",
    "tieng viet": "Tiếng Việt",
    "tiengviet": "Tiếng Việt",
    "khoa hoc": "Khoa học",
    "lich su dia ly": "Lịch sử - Địa lý",
    "lich su - dia ly": "Lịch sử - Địa lý",
    "lsdl": "Lịch sử - Địa lý",
    "dao duc": "Đạo đức",
    "cong nghe": "Công nghệ",
    "am nhac": "Âm nhạc",
    "mi thuat": "Mĩ thuật",
    "my thuat": "Mĩ thuật",
}

def normalize_subject(s: str) -> str:
    k = normalize_key(s)
    return SUBJECT_ALIASES.get(k, str(s).strip())

def normalize_semester(s: str) -> str:
    k = normalize_key(s)
    # recognize HK2 first
    if "hk2" in k or "hkii" in k or "hoc ki ii" in k or "hoc ky ii" in k or re.search(r"\b2\b", k):
        return "HK2"
    if "hk1" in k or "hki" in k or "hoc ki i" in k or "hoc ky i" in k or re.search(r"\b1\b", k):
        return "HK1"
    # fallback: keep original if already looks like HK*
    if str(s).upper().strip().startswith("HK"):
        return str(s).upper().strip()
    return "HK1"


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
        if f"M{d}" in label:
            return left, int(d)
    return left, 1
