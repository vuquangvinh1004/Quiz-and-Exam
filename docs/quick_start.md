# Hướng dẫn sử dụng nhanh – Quiz Desktop App

> Phiên bản: 1.0.0 | Nền tảng: Windows 10/11

---

## 1. Cài đặt

### Cài từ installer (khuyến nghị)

1. Tải file `QuizApp_Setup_1.0.0.exe` từ trang phát hành.
2. Chạy file cài đặt, làm theo hướng dẫn trên màn hình.
3. Sau khi cài đặt, nhấp đôi vào biểu tượng **Quiz Desktop App** trên desktop.

### Chạy từ source (dành cho nhà phát triển)

```bash
cd quiz_desktop_app
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

---

## 2. Giao diện chính

Ứng dụng gồm thanh điều hướng bên trái và vùng nội dung bên phải:

| Mục | Chức năng |
|---|---|
| Dashboard | Tổng quan thống kê câu hỏi và bài làm |
| Ngân hàng | Quản lý ngân hàng câu hỏi và câu hỏi cụ thể |
| Import | Nhập câu hỏi từ file Excel hoặc CSV |
| Tạo bài kiểm tra | Cấu hình và khởi động bài kiểm tra |
| Làm bài | Màn hình làm bài trực tiếp |
| Lịch sử | Xem lại các bài đã làm |
| Cài đặt | Chủ đề giao diện, backup, restore |

---

## 3. Nhập câu hỏi

### Bước 1 – Chuẩn bị file

Tạo file `.xlsx` hoặc `.csv` theo định dạng chuẩn (xem [import_guide.md](import_guide.md)).

**Template nhanh cho Multiple Choice:**

```csv
question_code,question_text,question_type,category,difficulty,score,hint,explanation,option_a,option_b,option_c,option_d,option_e,option_f,correct_answers,status,tags,case_sensitive,trim_whitespace
MC001,Thủ đô Việt Nam là gì?,multiple_choice,Địa lý,easy,1,,, Hà Nội,Hồ Chí Minh,Đà Nẵng,Cần Thơ,,,A,active,,false,true
```

### Bước 2 – Import

1. Vào mục **Import** trên thanh điều hướng.
2. Nhấn **Chọn file** và chọn file của bạn.
3. Xem **preview** – dòng hợp lệ, cảnh báo, lỗi.
4. Nếu không có lỗi, nhấn **Import** để xác nhận.

> **Lưu ý:** Nếu có dòng lỗi (`ERROR`), toàn bộ file sẽ bị chặn cho đến khi sửa lỗi.

---

## 4. Tạo và làm bài kiểm tra

### Tạo bài

1. Vào **Ngân hàng** → chọn ngân hàng chứa câu hỏi cần dùng.
2. Vào **Tạo bài kiểm tra**.
3. Chọn ngân hàng câu hỏi, đặt tên bài, chọn chế độ.
4. Cấu hình số câu, thời gian, bộ lọc.
5. Nhấn **Bắt đầu** để vào màn hình làm bài.

### Ba chế độ

| Chế độ | Mô tả |
|---|---|
| **Kiểm tra** | Có thời gian. Không hiển thị đáp án. Kết quả sau khi nộp bài. |
| **Luyện tập** | Có thời gian. Có gợi ý. Kết quả tổng hợp sau khi kết thúc. |
| **Học tập** | Không thời gian. Phản hồi ngay sau từng câu. Có thể xem giải thích. |

### Trong khi làm bài

- Dùng các nút **◀ Trước** / **Tiếp ▶** để chuyển câu.
- Thanh tiến trình và đồng hồ đếm ngược hiển thị ở trên cùng.
- Nhấn **Nộp bài** để kết thúc sớm.

---

## 5. Xem lịch sử

1. Vào **Lịch sử**.
2. Danh sách bài đã làm được hiển thị với điểm và ngày làm.
3. Nhấp đôi vào một bài hoặc nhấn **Xem chi tiết** để xem chi tiết.
4. Nhấn **Xóa bài làm** để xóa một bản ghi (có xác nhận).

> Mức độ thông tin chi tiết phụ thuộc vào chế độ làm bài:
> - **Kiểm tra**: chỉ xem tóm tắt.
> - **Luyện tập**: xem tổng đúng/sai/chưa làm.
> - **Học tập**: xem chi tiết từng câu.

---

## 6. Cài đặt

### Đổi chủ đề

1. Vào **Cài đặt** → nhóm **Giao diện chung**.
2. Chọn **Sáng** hoặc **Tối** trong danh sách thả xuống.
3. Nhấn **Áp dụng**.

### Backup dữ liệu

1. Vào **Cài đặt** → nhóm **Sao lưu và Phục hồi**.
2. Nhấn **Tạo backup ngay** → chọn thư mục lưu.
3. File backup có tên `quiz_app_YYYY-MM-DD_HH-MM-SS.db`.

### Phục hồi từ backup

1. Nhấn **Phục hồi từ backup...** → chọn file `.db`.
2. Đọc kỹ cảnh báo và nhấn **Có** để xác nhận.
3. Khởi động lại ứng dụng để áp dụng dữ liệu đã phục hồi.

> ⚠️ **Phục hồi sẽ ghi đè toàn bộ dữ liệu hiện tại. Hãy tạo backup trước.**

---

## 7. Câu hỏi thường gặp

**Q: Dữ liệu lưu ở đâu?**  
A: Trong thư mục `data/database/quiz_app.db` cạnh file thực thi. Không cần internet.

**Q: Có thể import file Excel nhiều sheet không?**  
A: v1.0 chỉ đọc sheet đầu tiên (hoặc sheet tên `questions` nếu có). Nhiều sheet sẽ hỗ trợ ở v1.1.

**Q: Import thất bại với lỗi "thiếu cột bắt buộc" là sao?**  
A: Header file thiếu hoặc sai chính tả tên cột. Xem [import_guide.md](import_guide.md) để biết danh sách cột chính xác.

**Q: Bài đang làm bị ngắt giữa chừng thì sao?**  
A: Ứng dụng có autosave mỗi 30 giây. Tuy nhiên v1.0 chưa hỗ trợ tiếp tục bài bị ngắt; tính năng này sẽ có ở v1.1.
