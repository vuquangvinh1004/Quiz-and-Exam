# QUIZ DESKTOP APP ARCHITECTURE

> QUAN TRỌNG CHO AI AGENT
>
> File này là nguồn chân lý cho toàn bộ dự án Quiz Desktop App.
>
> AI Agent bắt buộc phải đọc và tuân thủ file này trước khi:
> 1. Bắt đầu xây dựng bất kỳ module nào
> 2. Thêm, sửa, xóa chức năng
> 3. Thay đổi cấu trúc database
> 4. Tích hợp thư viện mới
> 5. Refactor code
> 6. Thay đổi hành vi của ba chế độ làm bài
>
> Mọi thay đổi về kiến trúc, hành vi nghiệp vụ, database schema, tech stack, cấu trúc thư mục hoặc chuẩn coding phải được ghi ngay vào phần CHANGELOG ở cuối file này.
>
> Lệnh khởi đầu bắt buộc cho AI Agent:
>
> Trước khi bắt đầu xây dựng, hãy đọc file QUIZ_APP_ARCHITECTURE.md, QUIZ_APP_ROADMAP.md và QUIZ_APP_IMPORT_FORMAT.md để hiểu kiến trúc, quy tắc phát triển, hành vi nghiệp vụ, định dạng import và lộ trình thực hiện của dự án Quiz Desktop App.

---

## 1. Tổng quan dự án

### 1.1. Mô tả

Quiz Desktop App là ứng dụng desktop chạy cục bộ, phục vụ hai năng lực cốt lõi:

1. Nhập và quản lý ngân hàng câu hỏi trắc nghiệm với bốn loại câu hỏi:
   1. Multiple Choice
   2. Multiple Answer
   3. Blank
   4. Short Answer
2. Tổ chức và chạy bài kiểm tra trong ứng dụng với ba chế độ:
   1. Kiểm tra
   2. Luyện tập
   3. Học tập

Ứng dụng được thiết kế theo định hướng desktop first, offline first, local first. Tất cả dữ liệu mặc định được lưu trên máy người dùng. Không phụ thuộc internet để thực hiện các chức năng cốt lõi của phiên bản MVP.

### 1.2. Mục tiêu sản phẩm

| Mục tiêu | Diễn giải |
|---|---|
| Quản lý câu hỏi tập trung | Có thể nhập, chỉnh sửa, phân loại, tìm kiếm và tái sử dụng câu hỏi |
| Làm bài trực tiếp trên desktop | Người dùng có thể mở bài, làm bài, theo dõi tiến độ và thời gian ngay trong ứng dụng |
| Hành vi rõ ràng theo chế độ | Mỗi chế độ phải có logic phản hồi riêng, không được lẫn lộn |
| Khả năng mở rộng | Có thể thêm loại câu hỏi, báo cáo, đồng bộ hoặc cloud trong tương lai |
| Xuất đề thi Word | Tạo file đề thi (.docx) chuẩn từ ngân hàng câu hỏi, hỗ trợ in ấn và phân phát |
| Độ ổn định cao | Không crash khi import dữ liệu lớn hoặc khi đang làm bài |

### 1.3. Phạm vi phiên bản v1.0

Phiên bản v1.0 bắt buộc phải có:

1. Import từ Excel và CSV
2. Import format chuẩn hóa bằng tài liệu QUIZ_APP_IMPORT_FORMAT.md
3. Nhập tay câu hỏi trong UI
4. Quản lý ngân hàng câu hỏi
5. Tạo cấu hình bài kiểm tra
6. Chạy bài kiểm tra trong ứng dụng
7. Thanh tiến trình
8. Bộ đếm thời gian lùi dần cho bài có giới hạn thời gian
9. Ba chế độ Kiểm tra, Luyện tập, Học tập
10. Chấm điểm và phản hồi theo đúng quy tắc nghiệp vụ
11. Lưu lịch sử làm bài
12. Lưu cấu hình ứng dụng cục bộ
13. Đóng gói thành ứng dụng desktop cài đặt được

Phiên bản v1.0 chưa bắt buộc phải có:

1. Cloud sync
2. Nhiều tài khoản người dùng
3. AI tạo câu hỏi
4. Google Forms
5. Thi online nhiều người cùng lúc
6. OCR hay scan phiếu trả lời
7. Xuất đề thi sang file Word (.docx) — dự kiến v1.1

### 1.4. Đối tượng sử dụng

1. Người học cá nhân
2. Giáo viên hoặc người biên soạn đề
3. Trung tâm đào tạo nhỏ
4. Nhóm học tập cần một phần mềm luyện tập cục bộ

---

## 2. Nguyên tắc sản phẩm và ranh giới kiến trúc

### 2.1. Nguyên tắc bắt buộc

| Nguyên tắc | Nội dung |
|---|---|
| Desktop first | Mọi luồng chính phải hoạt động tốt trên desktop trước khi nghĩ tới web hoặc mobile |
| Offline first | Không được ràng buộc chức năng cốt lõi vào internet |
| Local data ownership | Dữ liệu thuộc về người dùng và được lưu cục bộ mặc định |
| Mode integrity | Không được làm sai hành vi của ba chế độ làm bài |
| Clear separation | UI, business logic, persistence và utilities phải tách riêng |
| Maintainability | Code phải dễ kiểm thử, dễ refactor, dễ mở rộng |

### 2.2. Những điều AI Agent không được tự ý làm

1. Không tự ý chuyển dự án sang Electron, Tauri, web app, mobile app hoặc framework khác khi chưa có chỉ định cập nhật chính thức trong file này.
2. Không nhúng business logic vào event handler của UI.
3. Không lưu dữ liệu bài làm chỉ trong RAM nếu chưa có cơ chế persist rõ ràng.
4. Không thay đổi database schema mà không tạo migration plan và cập nhật changelog.
5. Không đổi tên field cốt lõi mà không có mapping tương thích ngược.
6. Không tự ý thêm API online vào chức năng cốt lõi của v1.0.
7. Không đánh dấu task là hoàn thành nếu mới có mock UI hoặc placeholder code.
8. Không hiển thị đáp án hoặc phản hồi sai chế độ trong chế độ Kiểm tra.
9. Không hiển thị đúng sai từng câu trong chế độ Luyện tập trước khi kết thúc bài.
10. Không áp dụng chấm điểm mơ hồ; mọi quy tắc chấm phải được định nghĩa rõ ở mục 7 của file này.

---

## 3. Tech stack chính thức

### 3.1. Công nghệ cốt lõi

| Thành phần | Công nghệ | Version đề xuất | Lý do lựa chọn |
|---|---|---:|---|
| Desktop framework | PySide6 | >= 6.6 | LGPL, ổn định, widget phong phú, phù hợp desktop app Python |
| Python | Python | >= 3.11 | Hiệu năng tốt, type hints tốt hơn, ecosystem ổn định |
| Database | SQLite | >= 3.40 | Serverless, local first, đủ mạnh cho MVP |
| ORM | SQLAlchemy | >= 2.0 | Rõ ràng, testable, hỗ trợ migration tốt |
| Migration | Alembic | >= 1.13 | Kiểm soát schema theo version |
| Import Excel | openpyxl, pandas | >= 3.1, >= 2.1 | Hỗ trợ đọc file tốt và kiểm tra dữ liệu |
| Logging | loguru | >= 0.7 | Logging dễ đọc, dễ xoay vòng file |
| Validation | pydantic | >= 2.0 | Kiểm tra settings và payload |
| Testing | pytest, pytest-qt, pytest-cov | >= 7.4 | Unit test, UI test, coverage |
| Packaging | PyInstaller | >= 6.0 | Đóng gói desktop app cho Windows trước |
| Export Word | python-docx | >= 1.1 | Tạo file .docx đề thi từ snapshot câu hỏi, không cần Microsoft Word |

### 3.2. Lựa chọn bị loại khỏi v1.0

| Công nghệ | Trạng thái | Lý do |
|---|---|---|
| Electron | Không dùng | Tăng dung lượng, lệch khỏi định hướng Python desktop |
| FastAPI hoặc Django | Không dùng | Ứng dụng không phải web app ở v1.0 |
| PostgreSQL | Không dùng | Dư thừa cho MVP local first |
| Redis | Không dùng | Không cần cho workload của v1.0 |
| Cloud API bắt buộc | Không dùng | Trái với nguyên tắc offline first |

### 3.3. Package tối thiểu đề xuất

```python
PySide6>=6.6.0
SQLAlchemy>=2.0.0
alembic>=1.13.0
pydantic>=2.0.0
openpyxl>=3.1.0
pandas>=2.1.0
python-dotenv>=1.0.0
loguru>=0.7.2
pytest>=7.4.0
pytest-qt>=4.2.0
pytest-cov>=4.1.0
PyInstaller>=6.0.0
python-docx>=1.1.0
```

---

## 4. Cấu trúc thư mục chuẩn

```text
quiz_desktop_app/
│
├── main.py
├── QUIZ_APP_ARCHITECTURE.md
├── QUIZ_APP_ROADMAP.md
├── README.md
├── requirements.txt
├── requirements-dev.txt
├── .env.example
├── .gitignore
│
├── config/
│   ├── __init__.py
│   ├── settings.py
│   ├── database.py
│   └── paths.py
│
├── core/
│   ├── __init__.py
│   ├── database/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── connection.py
│   │   ├── session.py
│   │   └── migrations/
│   │       └── versions/
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── entities/
│   │   │   ├── __init__.py
│   │   │   ├── question.py
│   │   │   ├── quiz.py
│   │   │   ├── attempt.py
│   │   │   └── settings.py
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── question_service.py
│   │       ├── import_service.py
│   │       ├── quiz_service.py
│   │       ├── attempt_service.py
│   │       ├── grading_service.py
│   │       ├── history_service.py
│   │       └── settings_service.py
│   └── utils/
│       ├── __init__.py
│       ├── constants.py
│       ├── validators.py
│       ├── exceptions.py
│       ├── helpers.py
│       └── logger.py
│
├── modules/
│   ├── __init__.py
│   ├── question_bank/
│   │   ├── __init__.py
│   │   ├── importer.py
│   │   ├── exporter.py
│   │   ├── duplicate_detector.py
│   │   └── search_engine.py
│   ├── quiz_builder/
│   │   ├── __init__.py
│   │   ├── selector.py
│   │   ├── randomizer.py
│   │   ├── validator.py
│   │   └── timer_policy.py
│   ├── quiz_runner/
│   │   ├── __init__.py
│   │   ├── session_manager.py
│   │   ├── progress_tracker.py
│   │   ├── navigation_manager.py
│   │   └── autosave.py
│   ├── grading/
│   │   ├── __init__.py
│   │   ├── evaluators.py
│   │   └── result_builder.py
│   ├── backup/
│   │   ├── __init__.py
│   │   ├── backup_manager.py
│   │   └── restore_manager.py
│   ├── quiz_exporter/
│   │   ├── __init__.py
│   │   └── word_renderer.py
│   └── analytics/
│       ├── __init__.py
│       ├── statistics.py
│       └── report_builder.py
│
├── ui/
│   ├── __init__.py
│   ├── main_window.py
│   ├── styles/
│   │   ├── __init__.py
│   │   ├── themes.py
│   │   └── qss_styles.py
│   ├── widgets/
│   │   ├── __init__.py
│   │   ├── progress_header.py
│   │   ├── timer_widget.py
│   │   ├── question_card.py
│   │   ├── answer_editor.py
│   │   ├── result_panel.py
│   │   └── toast_notification.py
│   ├── dialogs/
│   │   ├── __init__.py
│   │   ├── import_preview_dialog.py
│   │   ├── question_editor_dialog.py
│   │   ├── quiz_config_dialog.py
│   │   └── confirm_submit_dialog.py
│   └── views/
│       ├── __init__.py
│       ├── dashboard_view.py
│       ├── question_bank_view.py
│       ├── import_view.py
│       ├── quiz_builder_view.py
│       ├── quiz_runner_view.py
│       ├── result_history_view.py
│       └── settings_view.py
│
├── data/
│   ├── database/
│   │   └── quiz_app.db
│   ├── imports/
│   ├── exports/
│   ├── backups/
│   └── logs/
│
├── assets/
│   ├── icons/
│   ├── images/
│   └── templates/
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── unit/
│   ├── integration/
│   ├── ui/
│   └── fixtures/
│
└── docs/
    ├── import_format.md
    ├── test_modes.md
    ├── release_notes.md
    └── migration_notes.md
```

### 4.1. Quy tắc cấu trúc

1. Không đặt business logic vào `ui/`.
2. Không đặt truy cập database trực tiếp vào widget hoặc view.
3. Không đặt file tạm, file debug và script phụ ở root lâu dài; phải để trong `scripts/` nếu phát sinh.
4. Mọi file user data phải nằm dưới `data/` và được gitignore.

---

## 5. Kiến trúc module

### 5.1. Module Question Bank

Phạm vi:

1. CRUD câu hỏi
2. CRUD ngân hàng câu hỏi
3. Nhập file Excel và CSV
4. Tìm kiếm, lọc, phân loại
5. Kiểm tra trùng lặp cơ bản

Ràng buộc:

1. Import phải có bước validate trước khi ghi DB.
2. Không được import trực tiếp khi dữ liệu lỗi mà không cho người dùng xem preview lỗi.
3. Câu hỏi phải lưu được hint và explanation, dù mode hiện tại có dùng hay không.

### 5.2. Module Quiz Builder

Phạm vi:

1. Chọn nguồn câu hỏi
2. Chọn số lượng câu
3. Chọn chế độ làm bài
4. Thiết lập thời gian
5. Thiết lập trộn câu và trộn đáp án
6. Tạo cấu hình bài kiểm tra

Ràng buộc:

1. Không được tạo quiz nếu thiếu câu hỏi hoặc cấu hình mâu thuẫn.
2. Chế độ Học tập bắt buộc không giới hạn thời gian.
3. Chế độ Kiểm tra và Luyện tập phải cho phép thiết lập thời lượng bằng phút.

### 5.3. Module Quiz Runner

Phạm vi:

1. Hiển thị câu hỏi
2. Điều hướng giữa các câu
3. Thanh tiến trình
4. Đếm thời gian
5. Lưu trạng thái đang làm
6. Tự động kết thúc khi hết giờ nếu có giới hạn thời gian

Ràng buộc:

1. Timer phải chạy chính xác và không bị reset sai khi chuyển câu.
2. Progress phải phản ánh số câu đã trả lời thực tế.
3. Autosave phải không làm block UI.

### 5.4. Module Grading

Phạm vi:

1. Chấm theo từng loại câu hỏi
2. Trả về kết quả đúng, sai, bỏ trống, điểm số
3. Tách evaluator theo từng loại câu hỏi

Ràng buộc:

1. Multiple Choice chỉ chấp nhận một lựa chọn.
2. Multiple Answer phải hỗ trợ ít nhất chế độ chấm đúng hoàn toàn ở v1.0.
3. Blank và Short Answer phải hỗ trợ chuẩn hóa khoảng trắng và không phân biệt hoa thường nếu cờ cấu hình cho phép.
4. Mọi thay đổi quy tắc chấm phải cập nhật file này.

### 5.5. Module Result and History

Phạm vi:

1. Lưu lịch sử làm bài
2. Hiển thị kết quả theo mode
3. Thống kê cơ bản theo bài làm

Ràng buộc:

1. Chế độ Kiểm tra chỉ hiển thị thông báo hoàn thành trong luồng mặc định, không lộ đáp án đúng sai từng câu tại thời điểm kết thúc nếu không có cờ quản trị.
2. Chế độ Luyện tập hiển thị tổng hợp đúng, sai, chưa làm sau khi kết thúc.
3. Chế độ Học tập phản hồi ngay từng câu và có thể lưu lịch sử từng câu.

### 5.6. Module Settings and Backup

Phạm vi:

1. Lưu cài đặt theme, autosave, chuẩn so khớp đáp án, thời gian mặc định
2. Sao lưu và phục hồi DB

Ràng buộc:

1. Không lưu API key hoặc dữ liệu nhạy cảm trong plain text nếu sau này phát sinh.
2. Restore phải có xác nhận rõ ràng trước khi ghi đè dữ liệu hiện tại.

### 5.7. Module Quiz Exporter

Phạm vi:

1. Nhận danh sách câu hỏi snapshot từ QuestionSelector
2. Nhận metadata đề thi (trường, môn, tiêu đề, hình thức thi, thời gian)
3. Render nội dung câu hỏi theo 4 loại MC, MA, BLANK, SA
4. Tổ chức câu hỏi theo phần A, B, C, D (tùy cấu hình) hoặc gộp chung
5. Đánh số câu theo mode global hoặc per_section
6. Tự sinh hướng dẫn làm bài dựa trên loại câu hỏi có trong đề
7. Tự sinh phiếu trả lời
8. Tự sinh bảng đáp án và thang điểm
9. Tự sinh quy định chấm điểm
10. Xuất ra file .docx vào thư mục data/exports/

Ràng buộc:

1. Module này không được truy cập DB trực tiếp; nhận dữ liệu hoàn toàn qua parameter.
2. Không phụ thuộc vào Microsoft Word hoặc LibreOffice để tạo file.
3. Tổng điểm phải được tính tự động từ point_value của từng câu hỏi.
4. Không làm thay đổi luồng quiz runner hiện tại.
5. Giao diện xuất Word phải là opt-in (người dùng chủ động bấm nút), không auto-trigger.
6. File output đặt vào data/exports/ và tên file bao gồm tiêu đề đề và timestamp.

---

## 6. Quy trình nghiệp vụ chuẩn

### 6.1. Luồng import câu hỏi

1. Người dùng chọn file Excel hoặc CSV.
2. Hệ thống kiểm tra trước các guardrails cơ bản như kích thước file và row budget.
3. Hệ thống đọc file theo luồng xử lý phù hợp, validate từng dòng và gắn duplicate findings.
4. Hệ thống hiển thị preview gồm số dòng hợp lệ, số dòng lỗi, chi tiết lỗi.
5. Người dùng xác nhận import.
6. Hệ thống ghi DB theo transaction với commit/flush theo batch khi cần.
7. Hệ thống ghi import log.

### 6.2. Luồng tạo bài kiểm tra

1. Người dùng chọn ngân hàng câu hỏi.
2. Người dùng đặt tên bài kiểm tra.
3. Người dùng chọn mode.
4. Người dùng cấu hình thời gian nếu mode có timer.
5. Người dùng chọn số câu và bộ lọc.
6. Hệ thống kiểm tra đủ điều kiện.
7. Hệ thống sinh cấu hình quiz.
8. Người dùng bắt đầu làm bài.

### 6.3. Luồng làm bài

1. Hệ thống tạo một `attempt` mới.
2. Hệ thống nạp danh sách câu hỏi snapshot cho attempt.
3. Hệ thống hiển thị câu đầu tiên.
4. Người dùng trả lời và điều hướng.
5. Hệ thống autosave theo sự kiện hoặc chu kỳ.
6. Hệ thống cập nhật progress.
7. Nếu mode có timer, timer giảm dần.
8. Khi hết giờ hoặc nộp bài, hệ thống chuyển sang xử lý kết thúc.

### 6.4. Luồng kết thúc bài

1. Hệ thống khóa thao tác chỉnh sửa câu trả lời.
2. Hệ thống chấm điểm theo mode và policy.
3. Hệ thống lưu summary và attempt answers.
4. Hệ thống hiển thị kết quả theo đúng quy tắc mode.
5. Hệ thống lưu lịch sử.

### 6.5. Luồng xuất đề thi Word

1. Người dùng cấu hình bài kiểm tra trong tab Tạo bài kiểm tra như bình thường.
2. Người dùng mở rộng nhóm "Xuất đề thi" và điền metadata (trường, môn, tiêu đề, hình thức thi).
3. Người dùng chọn các tùy chọn: kèm phiếu trả lời, kèm đáp án, kèm quy định chấm điểm, nhóm theo loại câu hỏi.
4. Người dùng nhấn nút "Xuất đề thi (.docx)".
5. Hệ thống kiểm tra metadata bắt buộc (tối thiểu tiêu đề đề thi).
6. Hệ thống gọi QuestionSelector để lấy danh sách câu hỏi theo bộ lọc hiện tại.
7. Hệ thống gọi WordRenderer.render() với danh sách câu và cấu hình xuất.
8. WordRenderer sinh file .docx và lưu tạm vào data/exports/.
9. Hệ thống mở QFileDialog.getSaveFileName() để người dùng chọn hoặc xác nhận vị trí lưu.
10. Hệ thống thông báo thành công và có thể mở thư mục chứa file.

---

## 7. Quy tắc nghiệp vụ của ba chế độ

### 7.1. Định nghĩa chuẩn

| Chế độ | Giới hạn thời gian | Hint | Phản hồi từng câu | Kết quả cuối bài |
|---|---|---|---|---|
| Kiểm tra | Có | Không | Không | Chỉ thông báo hoàn thành theo luồng mặc định |
| Luyện tập | Có | Có | Không | Hiển thị tổng hợp đúng, sai, chưa làm sau khi kết thúc |
| Học tập | Không | Có thể có | Có | Hiển thị đúng, sai ngay sau từng câu |

### 7.2. Quy tắc bắt buộc cho mode Kiểm tra

1. Bắt buộc có giới hạn thời gian.
2. Không hiển thị hint.
3. Không hiển thị đáp án đúng trong quá trình làm.
4. Không hiển thị đúng sai từng câu khi người dùng trả lời.
5. Hết giờ thì tự động kết thúc attempt.
6. Màn hình cuối mặc định chỉ hiển thị trạng thái đã hoàn thành và thông tin tóm tắt tối thiểu do quản trị cấu hình.

### 7.3. Quy tắc bắt buộc cho mode Luyện tập

1. Có giới hạn thời gian.
2. Mỗi câu có thể hiển thị hint nếu câu hỏi có hint.
3. Không hiển thị đúng sai ngay trong lúc làm.
4. Hết giờ hoặc nộp bài thì hệ thống chấm toàn bộ.
5. Màn hình kết quả phải có số câu đúng, sai, chưa làm và tổng điểm nếu có chấm điểm.

### 7.4. Quy tắc bắt buộc cho mode Học tập

1. Không có giới hạn thời gian.
2. Sau khi người dùng hoàn thành một câu và xác nhận, hệ thống phải trả về phản hồi đúng hoặc sai ngay.
3. Có thể hiển thị explanation ngay sau phản hồi.
4. Người dùng có thể tiếp tục câu kế tiếp sau khi nhận phản hồi.
5. Kết quả tổng thể vẫn có thể lưu vào lịch sử nhưng không được yêu cầu timer.

### 7.5. Quy tắc chấm điểm mặc định

| Loại câu hỏi | Quy tắc chấm mặc định v1.0 |
|---|---|
| Multiple Choice | Đúng hoàn toàn thì có điểm, sai hoặc bỏ trống thì 0 |
| Multiple Answer | Chấm đúng hoàn toàn, chọn thiếu hoặc dư thì 0 |
| Blank | So khớp với danh sách đáp án hợp lệ sau chuẩn hóa |
| Short Answer | So khớp với danh sách đáp án hợp lệ sau chuẩn hóa |

### 7.6. Quy tắc chuẩn hóa đáp án văn bản

1. Cắt khoảng trắng đầu cuối.
2. Chuẩn hóa khoảng trắng thừa giữa các từ về một khoảng trắng.
3. Cho phép cấu hình không phân biệt chữ hoa và chữ thường.
4. Có thể cấu hình bỏ qua dấu câu cuối câu với Short Answer ở v1.1, chưa bắt buộc ở v1.0.

### 7.7. Snapshot policy

Khi bắt đầu một attempt, hệ thống phải snapshot các dữ liệu sau vào phạm vi bài làm:

1. Nội dung câu hỏi
2. Danh sách đáp án
3. Hint
4. Explanation
5. Đáp án đúng
6. Point value

Mục đích là để chỉnh sửa câu hỏi trong ngân hàng sau đó không làm thay đổi attempt đang hoặc đã diễn ra.

---

## 8. Database schema chính thức

### 8.1. Tổng quan bảng dữ liệu

Phiên bản v1.0 sử dụng 8 bảng chính:

1. question_banks
2. questions
3. question_options
4. quizzes
5. quiz_questions
6. attempts
7. attempt_answers
8. app_settings

### 8.2. Schema chi tiết

```sql
CREATE TABLE question_banks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    school TEXT,
    department TEXT,
    subject TEXT,
    course_code TEXT,
    exam_title TEXT,
    assessment_type TEXT,
    course_learning_outcomes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name)
);

CREATE TABLE questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bank_id INTEGER NOT NULL,
    question_code TEXT UNIQUE,
    question_type TEXT NOT NULL CHECK(question_type IN ('MC', 'MA', 'BLANK', 'SA')),
    content TEXT NOT NULL,
    hint TEXT,
    explanation TEXT,
    difficulty TEXT,
    category TEXT,
    tags TEXT,
    accepted_answers TEXT,
    point_value REAL DEFAULT 1.0,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (bank_id) REFERENCES question_banks(id) ON DELETE CASCADE
);

CREATE TABLE question_options (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id INTEGER NOT NULL,
    option_key TEXT NOT NULL,
    option_text TEXT NOT NULL,
    is_correct BOOLEAN DEFAULT 0,
    sort_order INTEGER NOT NULL,
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE,
    UNIQUE(question_id, option_key)
);

CREATE TABLE quizzes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    bank_id INTEGER NOT NULL,
    mode TEXT NOT NULL CHECK(mode IN ('EXAM', 'PRACTICE', 'STUDY')),
    time_limit_minutes INTEGER,
    shuffle_questions BOOLEAN DEFAULT 1,
    shuffle_options BOOLEAN DEFAULT 1,
    show_hint_in_practice BOOLEAN DEFAULT 1,
    show_explanation_in_study BOOLEAN DEFAULT 1,
    total_questions INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (bank_id) REFERENCES question_banks(id) ON DELETE CASCADE
);

CREATE TABLE quiz_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quiz_id INTEGER NOT NULL,
    question_id INTEGER NOT NULL,
    question_order INTEGER NOT NULL,
    snapshot_content TEXT NOT NULL,
    snapshot_type TEXT NOT NULL,
    snapshot_hint TEXT,
    snapshot_explanation TEXT,
    snapshot_point_value REAL DEFAULT 1.0,
    snapshot_options TEXT,
    snapshot_accepted_answers TEXT,
    FOREIGN KEY (quiz_id) REFERENCES quizzes(id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE,
    UNIQUE(quiz_id, question_order)
);

CREATE TABLE attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quiz_id INTEGER NOT NULL,
    mode TEXT NOT NULL CHECK(mode IN ('EXAM', 'PRACTICE', 'STUDY')),
    status TEXT NOT NULL CHECK(status IN ('IN_PROGRESS', 'SUBMITTED', 'TIME_UP', 'COMPLETED')),
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    submitted_at TIMESTAMP,
    duration_seconds INTEGER,
    answered_count INTEGER DEFAULT 0,
    correct_count INTEGER DEFAULT 0,
    incorrect_count INTEGER DEFAULT 0,
    skipped_count INTEGER DEFAULT 0,
    score REAL DEFAULT 0,
    max_score REAL DEFAULT 0,
    remaining_seconds INTEGER,
    metadata TEXT,
    FOREIGN KEY (quiz_id) REFERENCES quizzes(id) ON DELETE CASCADE
);

CREATE TABLE attempt_answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    attempt_id INTEGER NOT NULL,
    quiz_question_id INTEGER NOT NULL,
    answer_payload TEXT,
    is_answered BOOLEAN DEFAULT 0,
    is_correct BOOLEAN,
    score_awarded REAL DEFAULT 0,
    feedback_state TEXT,
    answered_at TIMESTAMP,
    FOREIGN KEY (attempt_id) REFERENCES attempts(id) ON DELETE CASCADE,
    FOREIGN KEY (quiz_question_id) REFERENCES quiz_questions(id) ON DELETE CASCADE,
    UNIQUE(attempt_id, quiz_question_id)
);

CREATE TABLE app_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    setting_key TEXT NOT NULL UNIQUE,
    setting_value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 8.3. Giải thích dữ liệu cốt lõi

| Trường | Ý nghĩa |
|---|---|
| questions.accepted_answers | JSON string cho BLANK hoặc SA, hoặc null nếu là MC và MA |
| question_options.is_correct | Nguồn đúng sai cho MC và MA |
| quiz_questions.snapshot_options | JSON snapshot options tại thời điểm tạo quiz |
| attempt_answers.answer_payload | JSON câu trả lời user, phù hợp từng loại câu hỏi |
| attempts.remaining_seconds | Phục vụ resume attempt nếu có autosave |
| attempts.extra_data | JSON metadata của attempt đang làm, hiện dùng để giữ `submitter_name` và `submitter_id` cho recovery ở EXAM mode |
| question_banks.subject | Metadata học phần của ngân hàng; trong dialog ngân hàng hiển thị nhãn UI là `Học phần` |
| question_banks.assessment_type | Metadata `Loại đánh giá` của ngân hàng, hiện hỗ trợ `Thường xuyên`, `Định kỳ`, `Tổng kết` |
| question_banks.course_learning_outcomes | JSON list các `Chuẩn đầu ra học phần` gồm `code` và `description` |

### 8.4. Dạng dữ liệu answer_payload theo loại câu hỏi

| Loại | Ví dụ payload |
|---|---|
| MC | `{"selected": "B"}` |
| MA | `{"selected": ["A", "C"]}` |
| BLANK | `{"values": ["supply chain"]}` hoặc `{"values": ["A", "B"]}` |
| SA | `{"text": "forecast error"}` |

### 8.5. Migration policy

1. Mọi thay đổi schema phải có migration file.
2. Không sửa schema trực tiếp trong DB production local của người dùng mà không có lộ trình migrate.
3. Mọi breaking change phải có mục “Data Migration Notes” trong changelog và docs.

---

## 9. UI và UX pattern chính thức

### 9.1. Cấu trúc main window

```text
┌───────────────────────────────────────────────────────────────┐
│ Quiz Desktop App                               [ _ ][ □ ][ X ]│
├───────────────┬───────────────────────────────────────────────┤
│ Dashboard     │ Nội dung module hiện tại                     │
│ Ngân hàng     │                                               │
│ Import        │                                               │
│ Tạo bài kiểm  │                                               │
│ Làm bài       │                                               │
│ Lịch sử       │                                               │
│ Cài đặt       │                                               │
├───────────────┴───────────────────────────────────────────────┤
│ Status: Ready | DB: OK | Autosave: ON | Theme: Light         │
└───────────────────────────────────────────────────────────────┘
```

### 9.2. Màn hình làm bài bắt buộc có

1. Tên bài kiểm tra
2. Chế độ làm bài
3. Thanh tiến trình
4. Đồng hồ đếm ngược nếu áp dụng
5. Nội dung câu hỏi
6. Khu vực trả lời phù hợp với loại câu hỏi
7. Nút trước, tiếp theo, nộp bài
8. Danh sách số câu hoặc navigator
9. Trạng thái đã trả lời, chưa trả lời, đang xem

### 9.3. Quy tắc UX bắt buộc

1. Các thao tác dài như import file lớn, backup, restore phải có progress indicator.
2. Không block UI thread bằng xử lý lâu.
3. Mọi lỗi phải có thông báo dễ hiểu cho người dùng.
4. Với hành động phá hủy như xóa ngân hàng, restore DB, nộp bài sớm, phải có confirm dialog.
5. Study mode phải cho cảm giác phản hồi nhanh và ít áp lực hơn exam mode.
6. Nếu phát hiện attempt `IN_PROGRESS` cho cùng quiz, màn hình làm bài phải cho người dùng chọn `tiếp tục` từ autosave gần nhất hoặc `bắt đầu lại` sau khi discard tiến độ cũ.
7. Autosave phải lưu được cả câu trả lời đang mở trên màn hình hiện tại, không chỉ các câu đã chuyển trang.

### 9.3.a. Question bank metadata dialog contract

1. Dialog `Thêm/Sửa ngân hàng câu hỏi` hiện dùng nhãn `Học phần` cho field dữ liệu `subject`.
2. Field `Loại đánh giá` là metadata riêng của ngân hàng và chỉ cho phép các giá trị chuẩn:
   - `Thường xuyên`
   - `Định kỳ`
   - `Tổng kết`
3. `Chuẩn đầu ra học phần` được lưu dưới dạng danh sách các row có:
   - `Mã CLO`
   - `Mô tả CLO`
4. Mỗi row `CLO` chỉ hợp lệ khi có đủ cả `Mã CLO` và `Mô tả CLO`; row rỗng hoàn toàn được phép bỏ qua.
5. Metadata `exam_title` cũ vẫn được giữ cho compatibility ở nhánh export, nhưng không còn là field active trong dialog metadata ngân hàng mới.

### 9.4. Runtime resilience contract

1. Autosave chính thức gồm hai phần: `attempt_answers.answer_payload` và `attempts.remaining_seconds`.
2. `remaining_seconds` chỉ có ý nghĩa với mode có timer (`EXAM`, `PRACTICE`); `STUDY` có thể để `NULL`.
3. Resume flow phải ưu tiên khôi phục attempt `IN_PROGRESS` mới nhất theo cùng `quiz_id`.
4. Với EXAM mode, metadata nhận diện người làm bài phải được lưu cùng attempt để resume không yêu cầu nhập lại.
5. Nếu người dùng chọn bắt đầu lại thay vì resume, attempt dở phải bị discard trước khi tạo attempt mới để tránh nhiều bản ghi `IN_PROGRESS` cho cùng quiz trong cùng luồng UI.
6. Trước khi finalize attempt, runner phải flush một nhịp autosave cuối để giảm lệch giữa UI runtime state và DB.
7. Nếu finalize persistence thất bại, UI phải giữ phiên làm bài trong trạng thái có thể retry; không được chuyển sang màn “đã hoàn thành”.
8. Phiên được khôi phục từ autosave phải có tín hiệu UI rõ ràng để tránh người dùng tưởng rằng họ đang ở phiên mới hoàn toàn.
9. Với EXAM mode, attempt resume chỉ hợp lệ khi còn đủ submitter metadata; nếu `time_up` nhưng finalize thất bại thì câu trả lời phải bị khóa và UI chỉ cho phép `Thử nộp lại`.

### 9.5. Import resilience contract

1. Import preview phải có guardrails cho dữ liệu lớn, ít nhất gồm row budget mềm/cứng và hard file-size limit.
2. Khi vượt soft budget, preview vẫn được phép tiếp tục nhưng phải phát cảnh báo rõ ràng trong `ParseResult`.
3. Khi vượt hard budget, preview phải bị chặn bằng `ERROR` cấp file để tránh import trong trạng thái rủi ro.
4. DB duplicate detection phải ưu tiên query có chọn lọc theo candidate rows thay vì nạp toàn bộ bảng câu hỏi khi không cần thiết.
5. Import commit phải hỗ trợ flush theo batch để giảm áp lực ORM/session khi nhập dữ liệu lớn.
6. Import preview và commit phải ghi log đủ ngữ cảnh để điều tra file lớn, duplicate-heavy hoặc các nhánh thất bại.
7. Baseline Phase 2 hiện tại được hiệu chỉnh theo benchmark cục bộ:
   - soft row limit: `12.000`
   - hard row limit: `30.000`
   - soft file-size warning: `3 MB`
   - hard file-size stop: `8 MB`

### 9.6. Telemetry warning summary

1. Dashboard phải có một vùng telemetry nhẹ để hiển thị import/runtime warnings gần đây.
2. Trong Phase 2, telemetry summary được phép đọc từ log files hiện có; không bắt buộc thêm DB table riêng.
3. Summary tối thiểu phải tách được `import warnings` và `runtime warnings`.
4. Chỉ những event có giá trị chẩn đoán hành vi/rủi ro mới nên đi vào summary; không dùng cho metrics noise tần suất cao.

### 9.7. Dashboard analytics contract

1. Dashboard được phép hiển thị analytics tổng quan cho bài làm đã hoàn tất nếu dữ liệu lấy qua service/facade, không query trực tiếp trong UI.
2. Baseline Phase 3 hiện tại gồm các chỉ số tổng quan từ `AttemptStatistics`: `total_attempts`, `avg_score_pct`, `best_score_pct`, `total_correct`, `total_incorrect`, `total_skipped`.
3. Chỉ các attempt đã hoàn tất nghiệp vụ (`SUBMITTED`, `TIME_UP`, `COMPLETED`) mới được tính vào analytics dashboard; `IN_PROGRESS` phải bị loại trừ để tránh méo số liệu.
4. Việc mở rộng dashboard analytics trong giai đoạn đầu phải tránh thay đổi schema nếu chưa thật sự cần thiết; ưu tiên tận dụng aggregate query và contract đã có.
5. Baseline summary theo khoảng thời gian hiện tại phải giữ được các chỉ số: `total_attempts`, `active_banks`, `active_quizzes`, `avg_score_pct`, `best_score_pct`.
6. Dashboard được phép hiển thị bảng breakdown theo ngân hàng nếu dữ liệu vẫn đi qua analytics module/facade; UI không tự tổng hợp từ raw attempts.
7. Reporting analytics hiện cho phép hai dạng chọn thời gian:
   - `time window preset` (`7`, `14`, `30` ngày)
   - `custom date range` (`start_date`, `end_date`) cho cùng contract aggregate/reporting
8. Nếu export analytics ra file, file chuẩn hiện tại là `reporting CSV`; nội dung phải phản ánh đúng snapshot đang lọc tại thời điểm export.

### 9.8. Export preset/template contract

1. Export/print workflow được phép có lớp `preset/template` để người dùng lưu và nạp lại cấu hình xuất đề thường dùng.
2. Preset export phải đi qua facade hoặc service chuyên trách; UI không tự xử lý JSON/file schema như business contract chính.
3. Preset tối thiểu phải bao gồm metadata đầu đề và các tùy chọn render quan trọng: `exam_type`, `numbering_mode`, `group_by_type`, `show_instructions`, `show_answer_sheet`, `show_scoring_rules`, `show_answer_key`.
4. User-defined export presets nên được lưu ở vùng dữ liệu người dùng (`data/templates/...`) để phù hợp với desktop/local-first và hỗ trợ sao lưu cùng dữ liệu ứng dụng.
5. Việc template hóa Phase 3 không được kéo logic render ra khỏi `WordRenderer`; preset chỉ cấu hình workflow, không thay đổi contract snapshot/render lõi.
6. Preset mặc định được phép tự áp dụng theo ngữ cảnh; thứ tự ưu tiên hiện tại là `bank` > `department_subject` > `global`.

### 9.9. Batch export and print profile contract

1. Khi xuất nhiều đề, app nên tạo một package thư mục riêng với naming convention chuẩn hóa thay vì đổ file lẫn vào thư mục cha.
2. Batch package tối thiểu phải có:
   - thư mục package có timestamp
   - tên file đề theo quy ước thống nhất
   - file `README` hoặc manifest tóm tắt gói xuất
3. Print profile phải là contract riêng của renderer, không trộn lẫn với logic chọn câu hỏi.
4. Baseline print profile hiện tại gồm:
   - `page_size`: `A4` hoặc `LETTER`
   - `top/bottom/left/right margins`
   - `show_student_info_block`
5. Ẩn block thông tin sinh viên chỉ ảnh hưởng layout in ấn đầu trang; không được làm thay đổi nội dung câu hỏi, đáp án hay logic chấm điểm.
6. Export workflow nâng cao hiện cho phép:
   - `cover sheet` trước phần nội dung đề
   - `watermark` dạng text trong header
   - `answer-key` tách file `.docx` riêng khi cần phát đề và giữ đáp án tách biệt cho giáo viên
7. Export workflow có thể thêm bước preview/xác nhận kế hoạch xuất trước khi render thật để giảm lỗi naming hoặc phát hành nhầm cấu hình.
8. Baseline naming policy cho file đáp án tách riêng hiện hỗ trợ hai dạng:
   - `suffix`: `<ten_file>_DAP_AN.docx`
   - `prefix`: `DAP_AN_<ten_file>.docx`
9. Preview export hiện tại được phép hiển thị `planned filenames`, `overwrite warnings` và `duplicate naming warnings` miễn là dùng chung naming helper với luồng save thật.
10. Baseline preview cho export hiện mở rộng thành `dry-run package manifest`, trong đó có thể hiển thị:
   - `planned filenames`
   - `section/print profile summary`
   - `print-content preview`
   - `overwrite warnings`
   - `naming conflict warnings`

### 9.10. Dashboard reporting deepening contract

1. Dashboard có thể mở rộng reporting sâu hơn miễn là vẫn đi qua facade/service layer và dùng aggregate query.
2. Baseline mở rộng hiện tại gồm:
   - mode breakdown: `EXAM`, `PRACTICE`, `STUDY`
   - recent activity window: xu hướng 7 ngày gần đây với `attempt count` và `avg score %`
3. Reporting Phase 3 vẫn không được tính `IN_PROGRESS` attempt vào các số liệu hiệu suất.
4. Nếu cần tăng chiều sâu thêm theo ngân hàng, theo người làm bài hoặc theo khoảng thời gian linh hoạt, nên ưu tiên mở rộng analytics module trước khi thêm UI controls phức tạp.
5. Baseline filter UI hiện tại cho reporting sâu hơn gồm:
   - `bank`
   - `quiz`
   - `time window` preset (`7`, `14`, `30` ngày) hoặc `custom date range`
6. Baseline reporting deepening hiện tại còn bao gồm:
   - `window summary` cho tập dữ liệu đang lọc
   - `bank breakdown` với `attempt count`, `quiz count`, `avg score %`, `best score %`, `last activity`
7. Nếu người dùng export analytics từ dashboard, file `reporting CSV` phải dùng cùng filter state với reporting snapshot đang hiển thị.

---

## 10. Quy tắc phát triển cho AI Agent

### 10.1. Coding standards

1. Tuân thủ PEP 8.
2. Bắt buộc dùng type hints.
3. Bắt buộc có docstring cho class và function public.
4. Mỗi file chỉ nên có một trách nhiệm chính.
5. Max line length đề xuất là 100.

### 10.2. Architecture standards

1. UI chỉ gọi service layer, không gọi thẳng SQLAlchemy model trong view.
2. Service layer không phụ thuộc widget cụ thể.
3. Mọi enum mode và question type phải đặt trong `core/utils/constants.py` hoặc entity layer.
4. Không được copy logic chấm điểm ở nhiều nơi; phải tập trung tại module grading.
5. Không được định nghĩa lại business rule bằng văn bản trong code comment nếu khác file này.

### 10.3. Testing requirements

| Loại test | Bắt buộc cho v1.0 |
|---|---|
| Unit tests cho grading | Có |
| Unit tests cho import parser | Có |
| Integration tests cho tạo quiz và attempt | Có |
| UI tests cho quiz runner chính | Có |
| Coverage target | Tối thiểu 80% cho phần core và modules |

### 10.4. Error handling

1. Không được `except Exception` rồi bỏ qua im lặng.
2. Mọi lỗi import phải trả về danh sách lỗi chi tiết theo dòng.
3. Mọi lỗi DB phải rollback transaction.
4. Mọi lỗi trong timer hoặc autosave phải được log rõ ràng.

### 10.5. Logging policy

Bắt buộc log các nhóm sự kiện sau:

1. App start và app shutdown
2. Import job start và finish
3. Quiz start, submit, time up
4. Backup và restore
5. Database migration
6. Error và warning

### 10.6. Definition of Done bắt buộc

Một task chỉ được xem là hoàn thành khi thỏa tất cả điều kiện sau:

1. Code chạy được
2. Không phá hành vi hiện có
3. Có test phù hợp
4. Test pass
5. Có cập nhật ROADMAP
6. Có cập nhật CHANGELOG trong file này
7. Nếu thay đổi hiển thị hoặc hành vi với người dùng thì phải cập nhật README hoặc docs liên quan

### 10.7. Strategic design philosophy (áp dụng xuyên suốt)

Mục này chuyển các nguyên tắc trong `philosophy_of_software_design.md` thành quy tắc thực thi cho dự án.

1. Ưu tiên giảm complexity hơn tốc độ giao hàng ngắn hạn.
2. Ưu tiên module sâu (deep module): interface nhỏ, implementation xử lý được nhiều việc.
3. Không tạo class/method chỉ để pass-through nếu không thêm abstraction hoặc policy.
4. Kéo complexity xuống dưới (service/module), không đẩy lên UI hoặc caller.
5. Tránh information leakage: một quyết định thiết kế chỉ nên nằm ở một nơi.
6. Thiết kế API cho common case thật đơn giản; special case phải được cô lập.
7. Giảm `except Exception` diện rộng; khi cần phải log rõ context và hành động recovery.
8. Mọi thay đổi lớn phải cân nhắc ít nhất 2 phương án trước khi chọn.
9. Tăng tính obvious của code: tên rõ nghĩa, flow dễ đọc, comment giải thích "why" thay vì "what".
10. Dành tối thiểu 10-20% effort cho làm sạch thiết kế trong mỗi chu kỳ phát triển.

### 10.8. Design review checklist (bắt buộc cho feature và refactor)

Trước khi merge, reviewer và agent phải trả lời được các câu hỏi sau:

1. Thay đổi này có giảm change amplification không?
2. Có giảm cognitive load cho người bảo trì tiếp theo không?
3. Có làm xuất hiện unknown unknown mới không?
4. Có tạo pass-through method/class hoặc interface duplication không cần thiết không?
5. Có logic nào nên kéo xuống service/module để giảm độ nặng của UI không?
6. Có business rule nào bị copy ở nhiều nơi thay vì tập trung một chỗ không?
7. Có broad exception mới nào xuất hiện mà chưa được giới hạn scope và log ngữ cảnh không?
8. Có test guardrail/regression tương ứng để ngăn tái phát không?

---

## 11. Kế hoạch đóng gói và phát hành

### 11.1. Mục tiêu phát hành v1.0

1. Windows là nền tảng ưu tiên đầu tiên.
2. Có file `.exe` hoặc installer hoàn chỉnh.
3. Có thư mục dữ liệu local được khởi tạo tự động.
4. Có hướng dẫn backup dữ liệu trước khi update.

### 11.2. Công cụ đóng gói

1. PyInstaller cho build standalone
2. Inno Setup cho installer Windows

### 11.3. Ràng buộc phát hành

1. Không phát hành nếu test regression quan trọng chưa pass.
2. Không phát hành nếu migration chưa được kiểm tra trên database mẫu cũ.
3. Không phát hành nếu mode Kiểm tra còn lộ đáp án hoặc phản hồi sai quy tắc.

---

## 12. Checklist bắt buộc trước khi AI Agent code

- [ ] Đã đọc file này từ đầu đến cuối
- [ ] Đã đọc QUIZ_APP_ROADMAP.md
- [ ] Hiểu rõ ba mode Kiểm tra, Luyện tập, Học tập
- [ ] Không thay đổi business rule khi chưa cập nhật tài liệu
- [ ] Có kế hoạch test cho task sắp làm
- [ ] Biết file nào sẽ bị tác động
- [ ] Biết có cần migration hay không

---

## 13. CHANGELOG

Quy tắc ghi chú:

1. Format: `YYYY-MM-DD | [Agent] | [Category] | Description`
2. Categories: ADDED, CHANGED, FIXED, REMOVED, DEPRECATED
3. Nếu có thay đổi schema, phải ghi thêm dòng “Migration Notes”

### 2026-03-24

ADDED | OpenAI GPT-5.4 Thinking | INITIAL | Khởi tạo tài liệu kiến trúc chuẩn cho Quiz Desktop App dựa trên yêu cầu sản phẩm gồm import câu hỏi, ngân hàng câu hỏi, quiz runner và ba chế độ làm bài. Xác lập tech stack, module boundaries, database schema, business rules, coding standards, testing requirements và quy tắc bắt buộc cho AI Agent.

### 2026-03-24 (Sprint 1 – Foundation)

ADDED | GitHub Copilot (Claude Sonnet 4.6) | SPRINT_1 | Triển khai Phase 1 (Product Foundation): khởi tạo toàn bộ cấu trúc thư mục chuẩn theo §4; config/settings.py (pydantic-settings), config/paths.py, config/database.py; core/utils/constants.py (QuestionType, QuizMode, AttemptStatus, Difficulty, BLANK_PLACEHOLDER, MULTI_VALUE_DELIMITER), core/utils/exceptions.py (exception hierarchy), core/utils/logger.py (loguru), core/utils/helpers.py, core/utils/validators.py; core/database/models.py (8 bảng SQLAlchemy 2.0 mapped_column theo schema §8), core/database/connection.py, core/database/session.py; Alembic init + migration 001_initial_schema; ui/main_window.py (sidebar 7 mục + stacked widget + status bar); 7 view stubs; main.py entry point; tests/conftest.py + 88 unit tests pass (test_constants, test_exceptions, test_helpers, test_validators, test_models, test_paths).

CHANGED | GitHub Copilot (Claude Sonnet 4.6) | SCHEMA_NOTE | Trường `metadata` trong bảng `attempts` đổi tên thành `extra_data` vì `metadata` là reserved attribute trong SQLAlchemy DeclarativeBase. Không ảnh hưởng business logic vì trường này chỉ là JSON blob tùy chọn.

### 2026-04-21 (v1.1 planning – Quiz Document Exporter)

ADDED | GitHub Copilot (Claude Sonnet 4.6) | ARCH_PLAN | Bổ sung kiến trúc cho tính năng xuất đề thi Word (v1.1). Chi tiết:
- §1.2: Thêm mục tiêu sản phẩm "Xuất đề thi Word".
- §1.3: Thêm mục 7 "Xuất đề thi sang file Word (.docx) — dự kiến v1.1" vào danh sách chưa bắt buộc ở v1.0.
- §3.1: Thêm python-docx >= 1.1 vào tech stack chính thức.
- §3.3: Thêm python-docx>=1.1.0 vào package list.
- §4: Thêm modules/quiz_exporter/ (word_renderer.py) vào cấu trúc thư mục chuẩn.
- §5.7: Định nghĩa Module Quiz Exporter — scope 10 điểm, ràng buộc 6 điểm, nguyên tắc tách biệt khỏi DB và quiz runner.
- §6.5: Định nghĩa luồng nghiệp vụ xuất đề thi Word (10 bước).
- Không thay đổi schema DB, không thay đổi business rules của ba mode làm bài.

### 2026-04-21 (Sprint 7 – HOÀN THÀNH)

DONE | GitHub Copilot (Claude Sonnet 4.6) | SPRINT_7_IMPL | Triển khai hoàn chỉnh module Quiz Document Exporter. Kiến trúc thực tế khớp với §5.7 và §6.5. Chi tiết:
- `modules/quiz_exporter/__init__.py` + `word_renderer.py`: Triển khai WordRenderer, ExamMeta, ExportConfig, build_output_path. Không có truy cập DB; nhận dữ liệu hoàn toàn qua tham số.
- `ui/views/quiz_builder_view.py`: Thêm Group 4 export UI (QGroupBox checkable) và _on_export() method. Module-level helpers _wrap_layout() và _open_folder() theo nguyên tắc helper nhỏ tách biệt.
- `tests/unit/test_word_renderer.py`: 43 unit tests — 43 passed.
- `tests/integration/test_export_flow.py`: 5 integration tests — 5 passed.
- Sửa lỗi import: `docx.util.Inches` → `docx.shared.Inches` (python-docx 1.2.0).
- Không thay đổi schema DB, không thay đổi business rules của ba mode làm bài.

### 2026-05-06 (Refactor Phase 1 – Layer Boundary Hardening)

CHANGED | GitHub Copilot (GPT-5.3-Codex) | ARCH_REFACTOR | Thực hiện Giai đoạn 1 theo hướng giảm information leakage từ UI sang data layer. Chi tiết:
- `core/domain/services/question_service.py`: bổ sung DTO + API thống kê cho Dashboard (`get_question_type_breakdown`, `get_usage_banks`, `get_question_usage_rows`, `build_usage_summary`, `get_question_by_id`).
- `ui/views/dashboard_view.py`: bỏ toàn bộ truy vấn SQLAlchemy trực tiếp trong view, chuyển sang gọi `QuestionService`.
- `ui/views/import_view.py`: chuyển thao tác tạo/tải ngân hàng sang `QuestionService`, thêm xử lý lỗi nhất quán qua helper.
- `ui/utils/error_handler.py`: thêm helper dùng chung cho critical error dialog + logging.
- `tests/unit/test_ui_layer_boundaries.py`: thêm guardrail test cho Dashboard để tránh tái đưa SQLAlchemy/query trực tiếp vào UI.

FIXED | GitHub Copilot (GPT-5.3-Codex) | CONSISTENCY | Chuẩn hóa xử lý lỗi ở một số luồng UI bằng helper dùng chung để giảm khác biệt thông báo/lưu log.

CHANGED | GitHub Copilot (GPT-5.3-Codex) | PR_02_CONTINUATION | Hoàn tất phần còn lại của PR-02: áp dụng helper lỗi dùng chung cho `QuestionBankView`, `QuizBuilderView`, `ResultHistoryView` để thống nhất pattern logging + dialog ở các luồng exception chính của UI.

CHANGED | GitHub Copilot (GPT-5.3-Codex) | PR_03_STATE_EXTRACTION | Tách session/state runtime khỏi `QuizRunnerView`: thêm `modules/quiz_runner/session_state.py` (`QuizRunnerState`) và `modules/quiz_runner/session_controller.py` (`QuizRunnerSessionController`). `QuizRunnerView` chuyển sang dùng state container + controller cho load quiz, prepare attempt, autosave, finalize, load submission settings.

CHANGED | GitHub Copilot (GPT-5.3-Codex) | GUARDRAIL_UI_ALL | Mở rộng guardrail test từ riêng Dashboard sang toàn bộ `ui/**/*.py`: chặn trực tiếp `session.query(...)` và import `sqlalchemy` trong UI layer để ngăn tái phát query-layer leakage.

CHANGED | GitHub Copilot (GPT-5.3-Codex) | PR_04_ANSWER_RENDERER | Bóc tách phần answer rendering khỏi `QuizRunnerView` sang component riêng `ui/widgets/quiz_answer_renderer.py` (`QuizAnswerRenderer`). `QuizRunnerView` chuyển sang gọi API component để render/restore/payload/lock input nhằm giảm độ dài file và giảm cognitive load.

ADDED | GitHub Copilot (GPT-5.3-Codex) | TEST_RUNNER_CONTROLLER | Bổ sung unit test cho `QuizRunnerSessionController` tại `tests/unit/test_quiz_runner_session_controller.py` bao phủ các nhánh chính: load_quiz_info, prepare_attempt, autosave (skip/call), finalize_attempt, load_submission_settings (success/fallback).

CHANGED | GitHub Copilot (GPT-5.3-Codex) | PR_05_RESULT_PRESENTER | Bóc tách phần feedback/result rendering khỏi `QuizRunnerView` sang component riêng `ui/widgets/quiz_result_presenter.py` (`QuizResultPresenter`) để giảm thêm độ dài file và tách biệt presentation logic.

ADDED | GitHub Copilot (GPT-5.3-Codex) | TEST_ANSWER_RENDERER | Bổ sung unit test cho `QuizAnswerRenderer` tại `tests/unit/test_quiz_answer_renderer.py` (MC/MA/BLANK/SA payload + lock/unlock input).

CHANGED | GitHub Copilot (GPT-5.3-Codex) | PHASE_1_DONE | Hoàn thành Giai đoạn 1 (Layer Boundary + Error Consistency + Runner Decomposition nền tảng): UI không còn truy vấn SQLAlchemy trực tiếp, error handling đã có helper dùng chung, QuizRunner đã tách state/session controller/answer renderer/result presenter và có guardrail test + unit test tương ứng.

CHANGED | GitHub Copilot (GPT-5.3-Codex) | QUIZ_TAB_REDESIGN_2026_05_26 | Thiết kế lại 2 tab chính theo hướng giảm complexity và tách rõ boundary nghiệp vụ: tab `Tạo bài kiểm tra` tập trung tạo đề và xuất đề; tab `Làm bài` tự cấu hình ngân hàng/chế độ/thời gian/bộ lọc trước khi bắt đầu. Bổ sung chọn pool câu hỏi (tất cả/theo Chương/theo Loại/chọn tay), tạo nhiều đề cùng lúc theo quota đồng thời (Chương/Loại/Độ khó), và cảnh báo UI khi quota vượt khả dụng.

CHANGED | GitHub Copilot (GPT-5.3-Codex) | QUIZ_CHAPTER_ALIAS_2026_05_26 | Chuẩn hóa hiển thị `Chương` trong UI question bank/editor bằng alias từ trường dữ liệu hiện hữu `questions.category` để tránh migration schema trong giai đoạn này.

CHANGED | GitHub Copilot (GPT-5.3-Codex) | UI_VIETNAMESE_ACCENTS_2026_05_26 | Chuẩn hóa text hiển thị tiếng Việt có dấu cho các màn hình mới thêm (pool picker, quota flow, runtime setup) để đảm bảo UX nhất quán.

CHANGED | GitHub Copilot (GPT-5.3-Codex) | DESIGN_PHILOSOPHY_ALIGNMENT | Bổ sung §10.7 và §10.8 để chuẩn hóa triết lý thiết kế chiến lược theo "A Philosophy of Software Design": ưu tiên deep modules, giảm pass-through abstraction, kéo complexity xuống dưới, hạn chế broad exception và bắt buộc design review checklist trước khi merge.

### 2026-06-30 (Roadmap alignment)

CHANGED | OpenAI GPT-5.4 Thinking | ROADMAP_ALIGNMENT | Bổ sung roadmap nâng cấp 3 giai đoạn trong `QUIZ_APP_ROADMAP.md` để ưu tiên đồng bộ contract, ổn định dữ liệu/runtime và sau đó mở rộng giá trị người dùng. Đây là thay đổi tài liệu định hướng, không đổi schema database, không đổi business rules của các mode, và không mở rộng phạm vi v1.0/v1.1.

CHANGED | OpenAI GPT-5.4 Thinking | PHASE_2_RUNTIME_RESILIENCE | Chính thức hóa contract runtime resilience cho quiz runner:
- `attempts.extra_data` dùng để giữ metadata recovery của attempt, hiện chuẩn hóa cho `submitter_name` và `submitter_id`.
- Autosave được định nghĩa là lưu đồng thời `attempt_answers.answer_payload` và `attempts.remaining_seconds`.
- Resume flow ưu tiên attempt `IN_PROGRESS` mới nhất theo `quiz_id`, cho phép người dùng chọn tiếp tục hoặc discard để bắt đầu lại.
- `QuizRunnerView` phải autosave cả câu trả lời đang mở trên màn hình hiện tại trước khi flush xuống persistence.

CHANGED | OpenAI GPT-5.4 Thinking | PHASE_2_FINALIZE_FAILSAFE | Mở rộng runtime contract cho nhánh submit/finalize:
- Runner phải chống double-finalize trong cùng phiên UI.
- Trước khi finalize phải có một đợt flush autosave cuối cùng.
- Nếu ghi kết quả thất bại, runner phải khôi phục trạng thái cho phép retry thay vì đưa attempt sang cảm giác “đã xong”.
- UI runner có badge hiển thị khi phiên hiện tại là phiên resume từ autosave.

CHANGED | OpenAI GPT-5.4 Thinking | PHASE_2_EXAM_POLICY_AND_IMPORT_RESILIENCE | Mở rộng contract Phase 2 theo hai hướng:
- EXAM runtime policy: chỉ resume khi metadata người làm bài còn hợp lệ; nếu `time_up` nhưng finalize persistence lỗi thì câu trả lời bị khóa và UI chỉ cho phép `Thử nộp lại`.
- Telemetry/runtime logging: runner ghi log theo event cho các nhánh resume/discard/invalid/finalize/retry để hỗ trợ chẩn đoán.
- Import resilience: parser có row budgets mềm/cứng và hard file-size limit; duplicate detection thu hẹp query theo candidate rows; import commit flush theo batch để giảm áp lực ORM cho dữ liệu lớn.

CHANGED | OpenAI GPT-5.4 Thinking | PHASE_2_BUDGET_TUNING_AND_TELEMETRY_SUMMARY | Chốt contract Phase 2 theo số đo thực tế và observability:
- Import budget mặc định được tinh chỉnh theo benchmark cục bộ đến 20.000 dòng, thay cho ngưỡng cảnh báo quá sớm trước đó.
- Dashboard có telemetry warning summary đọc từ log files để hiển thị import/runtime warnings gần đây mà chưa cần migration schema mới.

CHANGED | OpenAI GPT-5.4 Thinking | PHASE_3_DASHBOARD_ATTEMPT_ANALYTICS | Khởi động Giai đoạn 3 theo lát cắt rủi ro thấp nhưng tác động cao:
- `DashboardFacade` tải thêm analytics tổng quan cho bài làm đã hoàn tất qua `AttemptStatistics`.
- `DashboardView` hiển thị section `Hiệu suất làm bài` với các chỉ số lượt làm bài, điểm trung bình, điểm cao nhất và tổng đúng/sai/bỏ qua.
- Không thay đổi schema database, không đổi grading rules, không đưa query trực tiếp vào UI.

CHANGED | OpenAI GPT-5.4 Thinking | PHASE_3_EXPORT_PRESET_WORKFLOW | Mở nhánh export/print workflow theo hướng template hóa an toàn:
- `ExamExportPanel` có thêm thao tác lưu, nạp và xóa preset xuất đề để tái sử dụng cấu hình in ấn thường dùng.
- Thêm `ExportTemplateFacade` và `ExportPresetStore` để giữ boundary `UI -> facade -> file-based preset store`.
- Preset được lưu trong `data/templates/exam_export_presets/`, không đổi schema database và không thay đổi contract render của `WordRenderer`.

CHANGED | OpenAI GPT-5.4 Thinking | PHASE_3_EXPORT_DEFAULTS_BATCH_AND_PRINT_PROFILE | Tiếp tục nhánh export/print workflow theo đúng thứ tự tác động/rủi ro:
- preset mặc định hỗ trợ tự áp dụng theo `ngân hàng`, `khoa + môn` hoặc `mặc định chung`;
- batch export nhiều đề tạo package riêng có naming convention chuẩn in ấn và file `README`;
- `WordRenderer` nhận thêm print profile cho `A4/Letter`, margins và tùy chọn ẩn/hiện block thông tin sinh viên;
- vẫn giữ nguyên boundary: UI gọi facade/store hoặc renderer contract, không trộn file I/O và print schema trực tiếp vào business logic chọn câu.

CHANGED | OpenAI GPT-5.4 Thinking | PHASE_3_EXPORT_COVER_WATERMARK_AND_DEEPER_REPORTING | Tiếp tục hoàn thiện Giai đoạn 3 theo hai nhánh đã ưu tiên:
- export/print workflow có thêm `cover sheet`, `watermark` và khả năng tách `answer-key` thành file `.docx` riêng;
- dashboard reporting mở rộng thêm `mode breakdown` và `recent 7-day activity` mà không đổi schema;
- các thay đổi vẫn giữ pattern `UI -> facade/service -> renderer/analytics module` và được khóa bằng regression tests tương ứng.

CHANGED | OpenAI GPT-5.4 Thinking | PHASE_3_FILTERED_REPORTING_AND_EXPORT_PREVIEW | Tiếp tục Giai đoạn 3 với các bước hợp lý tiếp theo:
- dashboard reporting có filter theo `ngân hàng`, `quiz` và `khoảng thời gian`;
- export workflow có `cover sheet template`, `watermark preset`, `answer-key naming policy` và bước preview/xác nhận kế hoạch xuất;
- mục tiêu vẫn là tăng giá trị sử dụng thực tế nhưng không đưa query/file-schema trực tiếp trở lại UI layer.

DONE | OpenAI GPT-5.4 Thinking | PHASE_3_DEEP_REPORTING_AND_BATCH_CONFLICT_SUMMARY | Hoàn tất các lát cắt còn lại có tác động cao của Giai đoạn 3:
- dashboard reporting bổ sung `window summary` và `bank breakdown` cho tập dữ liệu đã lọc theo `ngân hàng / quiz / khoảng thời gian`;
- analytics vẫn chỉ dùng aggregate query qua `AttemptStatistics` và `DashboardFacade`, không đổi schema và không kéo raw query về UI;
- batch export preview dùng chung naming helper với luồng save thật để hiển thị `planned filenames`, cảnh báo ghi đè và summary naming conflict trước khi render;
- contract export/analytics mới được khóa bằng regression tests cho analytics aggregates, facade snapshot và batch naming helpers.

DONE | OpenAI GPT-5.4 Thinking | PHASE_3_CUSTOM_RANGE_CSV_AND_DRY_RUN_MANIFEST | Mở rộng nốt các đường giá trị cao còn lại của Giai đoạn 3:
- dashboard reporting hỗ trợ thêm `custom date range` cùng contract với các preset `7/14/30 ngày`;
- dashboard có thể `xuất reporting CSV` theo đúng snapshot đang lọc, không tự dựng contract khác ngoài facade/analytics module;
- export preview được nâng từ summary ngắn thành `dry-run package manifest` có `planned filenames`, `print profile`, `print-content preview`, `overwrite warnings`, `naming conflict warnings`;
- tài liệu và thuật ngữ được đồng bộ theo workflow `Docs sweep -> Policy sweep -> Consistency sweep -> Final glossary sweep`.

CHANGED | OpenAI GPT-5.4 Thinking | QUESTION_BANK_METADATA_DIALOG_REDESIGN | Thiết kế lại metadata dialog cho `Ngân hàng câu hỏi`:
- `subject` tiếp tục là field dữ liệu nền nhưng nhãn UI active trong dialog đổi thành `Học phần`;
- thêm `assessment_type` như metadata riêng của ngân hàng với ba giá trị chuẩn `Thường xuyên`, `Định kỳ`, `Tổng kết`;
- thêm `course_learning_outcomes` dưới dạng JSON list các row `code/description`;
- `exam_title` cũ được giữ lại cho compatibility ở nhánh export nhưng không còn là field active trong dialog metadata ngân hàng.

### 2026-06-30 (Phase 1 implementation started)

CHANGED | OpenAI GPT-5.4 Thinking | PHASE_1_CONTRACT_AND_GUARDRAILS | Bắt đầu triển khai Giai đoạn 1 của roadmap nâng cấp theo hướng giảm rủi ro nhưng tăng độ đồng bộ hệ thống. Thay đổi chính:
- thêm `QuizBuilderFacade` để kéo session orchestration ra khỏi `QuizBuilderView`;
- bổ sung guardrail test chặn UI builder quay lại import ORM model hoặc mở session trực tiếp;
- cấu hình pytest dùng thư mục tạm trong workspace để giảm lỗi môi trường Windows;
- đồng bộ contract BLANK nhiều chỗ trống trong tài liệu import với implementation hiện tại.

CHANGED | OpenAI GPT-5.4 Thinking | PHASE_1_UI_BOUNDARY_CONTINUED | Tiếp tục kéo session orchestration ra khỏi UI ở các luồng export và runner setup:
- `ExamExportPanel` không còn tự mở DB session; thay vào đó dùng `QuizBuilderFacade` để lấy detached questions đã eager-load options;
- `QuizRunnerSetupMixin` không còn tự mở DB session; dùng `QuizBuilderFacade` cho available count, selection và create quiz;
- thêm guardrail test để khóa boundary này trong `tests/unit/test_ui_layer_boundaries.py`.

DONE | OpenAI GPT-5.4 Thinking | PHASE_1_UI_SESSION_BOUNDARY_CLOSED | Hoàn tất dọn session direct access ở các file UI nghi ngờ còn lại:
- `ResultHistoryView` dùng `HistoryFacade` thay cho direct session orchestration;
- `MainWindow` dùng `SettingsFacade` để đọc theme đã persist;
- `BankCombo` dùng `QuestionBankFacade` để nạp metadata ngân hàng;
- thêm guardrail test khóa boundary cho các điểm trên.

ADDED | OpenAI GPT-5.4 Thinking | POLICY_AND_TERMINOLOGY_SYNC_WORKFLOW | Bổ sung quy trình chuẩn trong `CONTRIBUTING.md` để đồng bộ policy và thuật ngữ mỗi khi thay đổi feature hoặc contract:
- `Docs sweep`
- `Policy sweep`
- `Consistency sweep`
- `Final glossary sweep`
- Quy trình này áp dụng cho các thay đổi liên quan tới quyền, workflow nghiệp vụ, route truy cập, trạng thái dữ liệu, thuật ngữ UI hoặc service contract.

Migration Notes: Không có thay đổi schema, không cần migration.

---

END OF ARCHITECTURE DOCUMENT

Last Updated: 2026-06-30
Version: 1.1.1
