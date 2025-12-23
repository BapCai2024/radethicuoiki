# Tool HỖ TRỢ RA ĐỀ — V3

## Bạn đang bị lỗi gì?
- Ảnh bạn gửi là lỗi `ModuleNotFoundError: st_aggrid` do **page cũ** vẫn import `st_aggrid`.
- V3 **không dùng st_aggrid** và còn **ẩn luôn menu multipage** để không còn dòng "Ma trận" / "Kho câu hỏi" ở sidebar.

## Dữ liệu đầy đủ (YCCĐ)
- Bạn gửi KHGD dạng `.rar` nên **Streamlit Cloud không giải nén**.
- Hãy xuất dữ liệu YCCĐ ra **Excel/CSV** hoặc nén `.zip` rồi upload ở tab **📚 Dữ liệu**.
- Sau khi nạp, dropdown Chủ đề/Bài/YCCĐ sẽ đầy đủ theo dữ liệu của bạn.

## AI (API)
- Tab ⚙️ AI hỗ trợ:
  - OpenAI-compatible (base_url + key + model)
  - AI Studio (Gemini) (key + model)
- Khi kho thiếu câu đúng (dạng + mức TT27), tool sẽ tạo câu bằng AI (khóa mức).

## Chạy local
```bash
pip install -r requirements.txt
streamlit run app.py
```


### Sửa lỗi Gemini 404
- Model `gemini-1.5-flash` có thể không còn hỗ trợ generateContent. V3.1 đổi mặc định sang `gemini-2.5-flash` theo danh sách model của Gemini API.
