# Release Checklist – Quiz Desktop App v1.0.0

> Ngày tạo: 24/03/2026  
> Mục đích: Kiểm tra toàn bộ điều kiện trước khi phát hành v1.0.0

---

## 1. Kiểm tra chức năng cốt lõi

### 1.1. Import
- [ ] Import file CSV hợp lệ thành công (MC, MA, BLANK, SA)
- [ ] Import file Excel (.xlsx) hợp lệ thành công
- [ ] Preview hiển thị đúng số dòng hợp lệ / cảnh báo / lỗi
- [ ] File có lỗi ERROR bị chặn toàn bộ (strict mode)
- [ ] File có WARNING nhưng không có ERROR được phép import
- [ ] Dòng hoàn toàn trống được bỏ qua
- [ ] Duplicate trong file → ERROR
- [ ] Duplicate với DB → WARNING
- [ ] Rollback hoàn toàn khi transaction thất bại

### 1.2. Quản lý ngân hàng câu hỏi
- [ ] Tạo ngân hàng mới
- [ ] Đổi tên ngân hàng
- [ ] Xóa ngân hàng (có confirmation)
- [ ] Xem danh sách câu hỏi trong ngân hàng
- [ ] Thêm câu hỏi thủ công (MC, MA, BLANK, SA)
- [ ] Thêm câu hỏi CRQ với subtype `Tự luận` và `Bài toán`
- [ ] Sửa câu hỏi
- [ ] Xóa câu hỏi (có confirmation)
- [ ] Tìm kiếm full-text hoạt động
- [ ] Lọc theo loại câu hỏi và độ khó

### 1.3. Tạo bài kiểm tra
- [ ] Tạo quiz với chế độ Kiểm tra
- [ ] Tạo quiz với chế độ Luyện tập
- [ ] Tạo quiz với chế độ Học tập
- [ ] Xuất đề Word với loại đề `Trắc nghiệm`
- [ ] Xuất đề Word với loại đề `CRQ`
- [ ] Xuất đề Word với loại đề `Hỗn hợp`
- [ ] CRQ nằm cuối đề và được đánh số lại từ 1
- [ ] CRQ-only không tạo phiếu trả lời riêng
- [ ] Mixed mode chỉ tạo phiếu trả lời cho câu trắc nghiệm
- [ ] Không tạo được quiz khi thiếu câu hỏi
- [ ] Không tạo được quiz thiếu cấu hình bắt buộc
- [ ] Chế độ Học tập bắt buộc không có thời gian

### 1.4. Làm bài
- [ ] Làm bài khởi động đúng với từng mode
- [ ] Điều hướng qua lại giữa các câu không mất đáp án
- [ ] Timer đếm ngược chính xác (Kiểm tra và Luyện tập)
- [ ] Hết giờ → tự động kết thúc
- [ ] Autosave không làm treo UI
- [ ] Nộp bài thủ công hoạt động
- [ ] Progress phản ánh số câu đã trả lời

### 1.5. Business rules theo mode
- [ ] **Kiểm tra**: không hiển thị hint, không phản hồi từng câu
- [ ] **Luyện tập**: hiển thị hint, không phản hồi từng câu trong lúc làm
- [ ] **Học tập**: phản hồi ngay sau từng câu, không có timer

### 1.6. Chấm điểm
- [ ] MC: đúng hoàn toàn thì có điểm / sai thì 0
- [ ] MA: đúng hoàn toàn thì có điểm / chọn thiếu hoặc dư thì 0
- [ ] BLANK: chuẩn hóa khoảng trắng và hoa thường theo cờ
- [ ] SA: chuẩn hóa text trước khi so khớp

### 1.7. Lịch sử
- [ ] Hiển thị danh sách bài đã làm
- [ ] Xem detail theo mode (Kiểm tra: chỉ tóm tắt; Luyện tập: tổng hợp; Học tập: từng câu)
- [ ] Xóa bài làm có confirmation
- [ ] Dashboard hiển thị thống kê đúng

### 1.8. Cài đặt
- [ ] Đổi theme sáng/tối và áp dụng
- [ ] Theme được lưu và tải lại khi khởi động
- [ ] Tạo backup thành công
- [ ] Restore từ backup với confirmation
- [ ] Sau restore app báo "cần restart"
- [ ] Mẫu xuất đề cũ `Trắc nghiệm + CRQ` được tự động chuẩn hóa thành `Hỗn hợp`

---

## 2. Kiểm tra kỹ thuật

### 2.1. Tests
- [ ] Tất cả unit tests pass
- [ ] Tất cả integration tests pass
- [ ] UI smoke tests pass
- [ ] Coverage core + modules ≥ 80%
- [ ] Performance test 1.000 dòng < 10 giây

### 2.2. Build
- [ ] `pyinstaller quiz_app.spec` chạy thành công
- [ ] `dist/QuizApp/QuizApp.exe` xuất hiện
- [ ] Kích thước build hợp lý (< 400 MB)

### 2.3. Standalone test (máy không có Python)
- [ ] App khởi động được trên máy Windows sạch
- [ ] DB được tạo tự động khi chạy lần đầu
- [ ] Import file CSV thành công
- [ ] Làm bài và lưu lịch sử thành công
- [ ] Theme đổi được và lưu lại khi restart
- [ ] Backup và restore hoạt động

### 2.4. Installer (Inno Setup)
- [ ] Compile `quiz_app.iss` thành công
- [ ] Installer có thể cài đặt bình thường
- [ ] Uninstall hoạt động không để lại rác

---

## 3. Kiểm tra dữ liệu thực tế

- [ ] Import ít nhất 1 bộ câu hỏi thực tế (≥ 50 câu) thành công
- [ ] Làm bài thực tế cho mỗi mode ít nhất 1 lần
- [ ] Kết quả chấm điểm chính xác
- [ ] Lịch sử hiển thị đúng

---

## 4. Tài liệu

- [ ] `docs/quick_start.md` hoàn chỉnh
- [ ] `docs/import_guide.md` hoàn chỉnh
- [ ] `README.md` cập nhật thông tin cài đặt và chạy
- [ ] `QUIZ_APP_ARCHITECTURE.md` CHANGELOG cập nhật đến Phase 7
- [ ] `QUIZ_APP_ROADMAP.md` Phase 7 cập nhật Done

---

## 5. Bug tracker

- [ ] Không còn bug mức **High** ở: import, grading, mode behavior, timer, autosave
- [ ] Các bug **Medium** được ghi nhận và có kế hoạch cho v1.1

---

## 6. Sign-off

| Người kiểm tra | Ngày | Kết quả |
|---|---|---|
| | | Pass / Fail |

**Ghi chú:**  
v1.0 chỉ được phát hành khi tất cả mục trong mục 1, 2, 3 đều Pass.  
Mục 4 và 5 phải hoàn thành trước ngày phát hành.
