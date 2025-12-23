from __future__ import annotations
import streamlit as st

def inject_css() -> None:
    st.markdown(r'''
    <style>
      /* Hide default multipage nav (prevents old pages from showing) */
      div[data-testid="stSidebarNav"] { display: none; }
      /* Hide the small "app" header in sidebar */
      div[data-testid="stSidebarHeader"] { display: none; }

      .block-container { padding-top: 1.1rem; padding-bottom: 2rem; }
      h1 { font-size: 2.35rem !important; }
      h2 { font-size: 1.6rem !important; }
      h3 { font-size: 1.25rem !important; }
      label, .stMarkdown, .stText, .stCaption { font-size: 1.12rem; }

      .app-hero {
        background: linear-gradient(180deg, #eff6ff 0%, #ffffff 100%);
        border: 1px solid rgba(15,23,42,0.08);
        border-radius: 18px;
        padding: 18px 18px 12px 18px;
        box-shadow: 0 10px 28px rgba(15,23,42,0.06);
      }
      .muted { color: rgba(15,23,42,0.70); font-size: 1.15rem; }
      .pill {
        display:inline-block; padding:6px 12px; border-radius:999px;
        border: 1px solid rgba(15,23,42,0.12); background:#f6f7fb;
        margin-right:8px; margin-bottom:8px; font-size: 14px;
      }
      .danger { color: #b91c1c; font-weight: 700; }
      .ok { color: #166534; font-weight: 700; }
    </style>
    ''', unsafe_allow_html=True)

def sidebar_brand() -> None:
    st.sidebar.markdown("## 🧩 Tool HỖ TRỢ RA ĐỀ")
    st.sidebar.caption("TT27: Biết=M1 • Hiểu=M2 • Vận dụng=M3 (khóa mức)")
    st.sidebar.markdown("---")
