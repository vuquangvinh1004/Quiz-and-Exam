# Cập nhật CRQ và xuất đề Word

Tài liệu này tóm tắt các thay đổi gần đây liên quan đến câu hỏi CRQ, luồng tạo bài kiểm tra và xuất đề `.docx`.

## 1. Thuật ngữ mới

- `CRQ` = `Constructed Response Questions`
- `ES` = `essay` = `Tự luận`
- `PR` = `problem` = `Bài toán`

Hai loại `ES` và `PR` được giữ riêng cho mục đích thống kê và chấm điểm, nhưng cùng thuộc family `CRQ`.

## 2. Luồng tạo câu hỏi

- Tab `Ngân hàng câu hỏi` đổi nút thêm mới thành `+ Thêm CRQ`.
- Dialog `Thêm câu hỏi` không còn chứa loại `Tự luận`.
- Dialog `Thêm CRQ` có thêm trường `Loại CRQ` với 2 subtype:
  - `Tự luận`
  - `Bài toán`
- Các trường bên dưới dùng chung cho cả hai subtype CRQ.

## 3. Luồng xuất đề Word

Trong tab `Tạo bài kiểm tra`, nhóm `Xuất đề thi (.docx)` hiện có 3 chế độ:

- `Trắc nghiệm`
- `CRQ`
- `Hỗn hợp`

Quy tắc chính:

- `CRQ` chỉ xuất câu CRQ, không tạo phiếu trả lời riêng.
- `Trắc nghiệm` chỉ xuất câu objective và tạo phiếu trả lời cho toàn bộ câu hỏi.
- `Hỗn hợp` xuất cả objective và CRQ, nhưng phiếu trả lời chỉ áp dụng cho phần objective.
- CRQ luôn nằm ở cuối phần nội dung đề.
- CRQ được đánh số riêng và bắt đầu lại từ `1`.

## 4. Preset và tương thích ngược

- Preset xuất đề được lưu cục bộ trong `data/templates/exam_export_presets`.
- Mẫu cũ dùng `Trắc nghiệm + CRQ` sẽ tự động được chuẩn hóa thành `Hỗn hợp` khi nạp lại hoặc lưu mới.
- Các preset đã lưu có thể xóa trực tiếp trong tab `Tạo bài kiểm tra`.

## 5. Ghi chú triển khai

- `question_family = CRQ` dùng cho các câu hỏi CRQ trong pipeline xuất đề.
- `crq_subtype` được dùng để phân biệt `essay` và `problem`.
- `answer sheet` chỉ sinh cho câu hỏi objective trong chế độ hỗn hợp.
- Export/print preset vẫn hỗ trợ lưu, nạp, xóa và preset mặc định theo ngữ cảnh.
