# Tool ra đề theo ma trận (TT27) — Streamlit

## Chạy nhanh
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Chuẩn bị dữ liệu
- **Template ma trận**: đặt file Excel vào `templates/` (mặc định đã kèm mẫu Tin 3 HK1).
- **Template đặc tả** (Word): đặt vào `templates/` (mặc định đã kèm `đặc tả.docx`).
- **Kho câu hỏi**: upload CSV/XLSX ở trang “📚 Kho câu hỏi”.
  - Bắt buộc có các cột tối thiểu:  
    `question_id, grade, subject, semester, topic, lesson, yccd, qtype, tt27_level, stem, answer, options`
  - `options` là JSON list (với MCQ). Với Tự luận có thể để rỗng.

## Luật TT27 (khóa mức)
- Cột **Biết/Hiểu/VD** trên ma trận tương ứng **M1/M2/M3** (TT27).
- Khi sinh đề: **không được bù câu khác mức**. Thiếu -> báo thiếu.

## Xuất file
- Xuất `Bảng đặc tả.docx` + `Đề.docx` vào thư mục `outputs/` và cho tải về trên UI.
