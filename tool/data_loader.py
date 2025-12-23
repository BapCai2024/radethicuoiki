from __future__ import annotations
import pandas as pd

REQUIRED = ["grade","subject","semester","topic","lesson","yccd"]

def load_catalog_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    for c in REQUIRED:
        if c not in df.columns:
            df[c] = ""
    df["grade"] = pd.to_numeric(df["grade"], errors="coerce").astype("Int64")
    for c in ["subject","semester","topic","lesson","yccd"]:
        df[c] = df[c].fillna("").astype(str)
    return df

def try_parse_catalog_from_excel(uploaded_file) -> pd.DataFrame:
    xls = pd.ExcelFile(uploaded_file)
    best = None
    for sh in xls.sheet_names:
        d = pd.read_excel(xls, sheet_name=sh)
        cols = [str(c).strip().lower() for c in d.columns]
        if any("ycc" in c for c in cols) and any("bài" in c or "lesson" in c for c in cols) and any("chủ" in c or "topic" in c for c in cols):
            best = d
            break
    if best is None:
        best = pd.read_excel(xls, sheet_name=xls.sheet_names[0])
    rename = {}
    for c in best.columns:
        cl = str(c).strip().lower()
        if "lớp" in cl or cl == "grade":
            rename[c] = "grade"
        elif "môn" in cl or cl == "subject":
            rename[c] = "subject"
        elif "hk" in cl or "học kì" in cl or cl == "semester":
            rename[c] = "semester"
        elif "chủ đề" in cl or cl == "topic":
            rename[c] = "topic"
        elif "bài" in cl or "nội dung" in cl or cl == "lesson":
            rename[c] = "lesson"
        elif "yêu cầu" in cl or "ycc" in cl or cl == "yccd":
            rename[c] = "yccd"
    df = best.rename(columns=rename)
    for c in REQUIRED:
        if c not in df.columns:
            df[c] = ""
    df = df[REQUIRED].copy()
    df["grade"] = pd.to_numeric(df["grade"], errors="coerce").astype("Int64")
    for c in ["subject","semester","topic","lesson","yccd"]:
        df[c] = df[c].fillna("").astype(str)
    df = df.dropna(subset=["topic","lesson"], how="all")
    return df
