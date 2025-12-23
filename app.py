\
from __future__ import annotations
import os
import streamlit as st

st.set_page_config(page_title="Tool ra đề theo ma trận (TT27)", layout="wide")

st.title("Tool ra đề theo ma trận (TT27)")
st.write("Màn hình chính là **ma trận giống Excel**. Giáo viên điền số câu theo từng ô; mức độ **khóa cứng TT27** (M1/M2/M3).")

st.info("Bắt đầu theo thứ tự: ① 🧩 Ma trận → ② 📚 Kho câu hỏi → ③ 📝 Tạo đề & Xuất Word.")

st.markdown("### Tệp mẫu đang dùng")
tmpl_dir = os.path.join(os.path.dirname(__file__), "templates")
for name in os.listdir(tmpl_dir):
    st.write(f"- `{name}`")

st.markdown("### Lưu ý quan trọng")
st.markdown("- Điểm/1 câu chỉnh theo **bước 0,25**.\n- Thiếu câu đúng ô (dạng+mức+bài) → **báo thiếu**, không tự bù bằng mức khác.\n- Có trang **🧪 Tự kiểm tra** để phát hiện lỗi cấu hình sớm.")
