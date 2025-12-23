from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple
import json
import pandas as pd
from .utils import normalize_subject, normalize_semester

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
        bad_q = sorted(set(df.loc[~df["qtype"].isin(ALLOWED_QTYPES), "qtype"].tolist()))
        if bad_q:
            errs.append(f"qtype không hợp lệ: {bad_q} (chỉ nhận {sorted(ALLOWED_QTYPES)})")
        bad_l = df.loc[~df["tt27_level"].isin(list(ALLOWED_LEVELS)), "tt27_level"]
        if len(bad_l) > 0:
            errs.append("tt27_level chỉ nhận 1/2/3 (TT27). Có dòng bị thiếu/sai.")
        mcq = df[df["qtype"]=="MCQ"]
        for idx, val in mcq["options"].head(200).items():
            try:
                arr = json.loads(val) if val else []
                if not isinstance(arr, list) or len(arr) < 3:
                    errs.append(f"MCQ options phải là JSON list >=3 (row {idx}).")
                    break
            except Exception:
                errs.append(f"MCQ options phải là JSON hợp lệ (row {idx}).")
                break
        return (len(errs)==0), errs

    def filtered(self, grade: int, subject: str, semester: str) -> pd.DataFrame:
        df = self.df
        return df[
            (df["grade"]==grade) &
            (df["subject"].str.lower()==str(subject).lower()) &
            (df["semester"].str.lower()==str(semester).lower())
        ].copy()

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
