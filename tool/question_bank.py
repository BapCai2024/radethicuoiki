\
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import json
import pandas as pd

REQUIRED_COLS = [
    "question_id","grade","subject","semester","topic","lesson","yccd",
    "qtype","tt27_level","stem","answer","options"
]

ALLOWED_QTYPES = {"MCQ","TF","MATCH","FILL","ESSAY"}
ALLOWED_LEVELS = {1,2,3}

@dataclass
class Bank:
    df: pd.DataFrame

    def normalize(self) -> "Bank":
        df = self.df.copy()
        # Standardize types
        df["grade"] = pd.to_numeric(df["grade"], errors="coerce").astype("Int64")
        df["tt27_level"] = pd.to_numeric(df["tt27_level"], errors="coerce").astype("Int64")
        for col in ["subject","semester","topic","lesson","yccd","qtype","stem","answer","options","marking_guide"]:
            if col in df.columns:
                df[col] = df[col].fillna("").astype(str)
        df["qtype"] = df["qtype"].str.upper().str.strip()
        return Bank(df=df)

    def validate(self) -> Tuple[bool, List[str]]:
        errs: List[str] = []
        df = self.df
        for c in REQUIRED_COLS:
            if c not in df.columns:
                errs.append(f"Thiếu cột bắt buộc: {c}")
        if errs:
            return False, errs

        # qtype & level validity
        bad_q = sorted(set(df.loc[~df["qtype"].isin(ALLOWED_QTYPES), "qtype"].tolist()))
        if bad_q:
            errs.append(f"qtype không hợp lệ: {bad_q} (chỉ nhận {sorted(ALLOWED_QTYPES)})")
        bad_l = df.loc[~df["tt27_level"].isin(list(ALLOWED_LEVELS)), "tt27_level"]
        if len(bad_l) > 0:
            errs.append("tt27_level chỉ nhận 1/2/3 (TT27). Có dòng bị thiếu/sai.")
        # options JSON for MCQ
        mcq = df[df["qtype"]=="MCQ"]
        for idx, val in mcq["options"].head(200).items():
            try:
                arr = json.loads(val) if val else []
                if not isinstance(arr, list) or len(arr) < 3:
                    errs.append(f"MCQ options phải là JSON list >=3 lựa chọn (row {idx}).")
                    break
            except Exception:
                errs.append(f"MCQ options phải là JSON hợp lệ (row {idx}).")
                break
        return (len(errs)==0), errs

    def coverage_counts(self, grade: int, subject: str, semester: str) -> pd.DataFrame:
        df = self.df
        sub = df[(df["grade"]==grade) & (df["subject"].str.lower()==subject.lower()) & (df["semester"].str.lower()==semester.lower())]
        if sub.empty:
            return pd.DataFrame(columns=["topic","lesson","qtype","tt27_level","available"])
        g = sub.groupby(["topic","lesson","qtype","tt27_level"]).size().reset_index(name="available")
        return g

def load_bank_from_upload(uploaded_file) -> Bank:
    name = uploaded_file.name.lower()
    if name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    elif name.endswith(".xlsx") or name.endswith(".xls"):
        df = pd.read_excel(uploaded_file)
    else:
        raise ValueError("Chỉ hỗ trợ CSV hoặc XLSX")
    if "marking_guide" not in df.columns:
        df["marking_guide"] = ""
    return Bank(df=df).normalize()
