# Tool HỖ TRỢ RA ĐỀ — V4 (KHGD full dữ liệu)

## Có gì mới ở V4?
- ✅ **Tích hợp sẵn dữ liệu YCCĐ** trích từ KHGD bạn gửi (Lớp 2–5, nhiều môn).  
- ✅ Dropdown **Lớp → Môn → HK → Chủ đề → Bài → YCCĐ** chạy đúng “luồng dữ liệu”.
- ✅ Có **Ma trận dạng bảng** (giống file ma trận) cho template có sẵn; GV chỉnh số câu theo TT27 và bấm **Tạo đề theo ma trận**.
- ✅ **Điểm bước 0,25**.
- ✅ **TT27 khóa mức**: khi chọn M1/M2/M3 thì lọc (hoặc tạo AI) đúng mức đó.

## Dữ liệu
- File `data/yccd_catalog.csv` đã được tạo sẵn.
- Nguồn gốc nằm trong `data/khgd_sources/` (các file xlsx bạn cung cấp) để có thể rebuild nếu cần.
- Nếu bạn muốn thay bằng dữ liệu khác: vào tab **📚 Dữ liệu** → upload YCCĐ (CSV/XLSX).

## AI tạo câu hỏi: có bắt buộc kho không?
- **Không bắt buộc**. Bạn có thể chạy 100% bằng AI.
- Tuy nhiên, **kho câu hỏi giúp ổn định** (ít phụ thuộc API, ít lag), và tool sẽ ưu tiên kho trước.

## Chạy local
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy Streamlit Cloud (GitHub)
- Đẩy toàn bộ repo lên GitHub
- Streamlit Cloud trỏ vào repo → chọn `app.py`

## Lưu ý Gemini 404
- Nếu bạn gặp lỗi “model not found”, vào tab **⚙️ AI (API)** và đổi `Gemini model` theo danh sách model đang hỗ trợ trong AI Studio.
