# Quiz Desktop App

Desktop-first, offline-first quiz application built with Python and PySide6.

Current runtime resilience baseline:
- autosave in-progress answers
- restore the latest in-progress attempt for the same quiz
- recover countdown state for timed modes after an unexpected app close
- preserve retryable state if finalize persistence fails
- show a recovery badge when the current session was restored from autosave
- enforce stricter Kiểm tra recovery policy after resume or time-up finalize failure

Current data-import resilience baseline:
- soft/hard row budgets for large previews
- hard file-size guardrail
- soft file-size warning before hard stop
- selective duplicate lookup against the database
- batch flush during import commit
- dashboard telemetry summary for recent nhập dữ liệu/runtime warnings

Current Phase 3 analytics baseline:
- dashboard attempt analytics for completed attempts
- total attempts, average score, best score
- aggregate correct / incorrect / skipped counters
- mode breakdown for Kiểm tra / Luyện tập / Ôn tập
- recent activity summary with attempts and average score
- reporting filters by bank / quiz / time window
- custom date range for reporting
- window summary for the selected reporting range
- bank-level breakdown table with attempts / quizzes / scores / last activity
- CSV export for the currently filtered reporting snapshot

Current export/print workflow baseline:
- reusable export presets for common teacher workflows
- save / load / delete export templates from the app
- keep template storage local-first in user data
- auto-apply default presets by bank or department + subject
- exam type selector supports `Trắc nghiệm`, `CRQ`, and `Hỗn hợp`
- `CRQ` remains a family with separate `ES` and `PR` subtypes for statistics
- CRQ-only exports skip the answer sheet; mixed exports keep the answer sheet for objective questions only
- CRQ sections are rendered at the end and renumbered from 1
- legacy presets using `Trắc nghiệm + CRQ` are auto-normalized to `Hỗn hợp`
- batch export package with standard print naming
- print profile for paper size, margins, and student-info block visibility
- optional cover sheet and watermark
- optional standalone answer-key `.docx` file for teacher-facing distribution
- cover sheet template options and watermark presets
- answer-key naming policy and export-plan preview before rendering
- batch preview with planned filenames, overwrite warnings, and naming-conflict summary
- detailed dry-run package manifest with print-content preview before rendering

Current question-bank metadata baseline:
- the bank metadata dialog uses `Học phần` as the active UI label for the underlying `subject` field
- `Loại đánh giá` is a controlled dropdown with `Thường xuyên`, `Định kỳ`, `Tổng kết`
- the bank metadata dialog supports dynamic `Chuẩn đầu ra học phần` rows with `Mã CLO` and `Mô tả CLO`
- legacy `exam_title` metadata is preserved for export compatibility, but no longer shown as an active field in the bank dialog

## Quick Start (Development)

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements-dev.txt
python main.py
```

## Run Tests

```bash
.venv\Scripts\python.exe -m pytest tests/unit -v
```

## Project Structure

```text
quiz_desktop_app/
├── main.py              Application entry point
├── config/              Settings, paths, database config
├── core/
│   ├── database/        SQLAlchemy models, Alembic migrations, session
│   ├── domain/          Entities and service layer stubs
│   └── utils/           Constants, exceptions, logger, helpers, validators
├── modules/             Business logic modules (import, grading, runner, …)
├── ui/                  PySide6 views, widgets, dialogs, styles
├── tests/               Unit, integration and UI tests
└── data/                User data (gitignored)
```

## Tech Stack

| Component | Library |
| --- | --- |
| Desktop UI | PySide6 ≥ 6.6 |
| Database | SQLite via SQLAlchemy ≥ 2.0 |
| Migrations | Alembic ≥ 1.13 |
| Settings | pydantic-settings ≥ 2.0 |
| Logging | loguru ≥ 0.7 |
| Testing | pytest + pytest-qt + pytest-cov |
| Packaging | PyInstaller ≥ 6.0 |

## Import Format

See [QUIZ_APP_IMPORT_FORMAT.md](QUIZ_APP_IMPORT_FORMAT.md) for the official
CSV / Excel import schema.

## Architecture

See [QUIZ_APP_ARCHITECTURE.md](QUIZ_APP_ARCHITECTURE.md) for the full design
document including database schema, mode rules and coding standards.

## Software Design Philosophy

This project follows strategic design principles adapted from
`philosophy_of_software_design.md` to keep long-term complexity under control.

1. Prioritize reducing complexity over short-term implementation speed.
2. Prefer deep modules: small interfaces, stronger internal implementation.
3. Avoid pass-through classes and methods that do not add abstraction value.
4. Pull complexity downward into services/modules, not UI event handlers.
5. Keep business rules in a single source of truth to prevent leakage.
6. Use targeted exception handling; broad catches must log context and recovery.
7. Add regression and architecture guardrail tests when making risky changes.

For full project-level policy, see:

- [QUIZ_APP_ARCHITECTURE.md](QUIZ_APP_ARCHITECTURE.md)
- [QUIZ_APP_ROADMAP.md](QUIZ_APP_ROADMAP.md)
- [docs/crq_export_changes.md](docs/crq_export_changes.md)

---

## Tiếng Việt

### Ứng dụng Quiz Desktop

Ứng dụng trắc nghiệm ưu tiên desktop và offline-first, xây dựng bằng Python và PySide6.

Mốc resilience runtime hiện tại:
- autosave câu trả lời đang làm
- khôi phục attempt `IN_PROGRESS` mới nhất cho cùng quiz
- phục hồi đồng hồ đếm ngược của mode có timer sau khi app đóng đột ngột
- giữ phiên làm bài ở trạng thái có thể thử nộp lại nếu finalize lỗi
- hiển thị badge báo đây là phiên được khôi phục từ autosave
- siết policy Kiểm tra cho resume và nhánh `time_up` nhưng finalize lỗi

Mốc resilience import hiện tại:
- row budget mềm/cứng cho preview dữ liệu lớn
- hard guardrail theo kích thước file
- soft warning theo kích thước file trước khi chặn hẳn
- duplicate lookup có chọn lọc theo candidate rows
- flush theo batch khi commit import
- dashboard telemetry summary cho import/runtime warnings gần đây

Mốc analytics Phase 3 hiện tại:
- dashboard có analytics tổng quan cho các attempt đã hoàn tất
- hiển thị lượt làm bài, điểm trung bình, điểm cao nhất
- tổng hợp số câu đúng / sai / bỏ qua trên toàn bộ lịch sử đã hoàn tất
- có breakdown theo mode Kiểm tra / Luyện tập / Ôn tập
- có summary xu hướng theo cửa sổ thời gian được chọn
- có filter theo ngân hàng / quiz / khoảng thời gian
- có `custom date range` cho reporting
- có window summary cho tập dữ liệu đang lọc
- có bảng breakdown theo ngân hàng với lượt làm / quiz / điểm / lần hoạt động cuối
- có thể xuất `reporting CSV` theo đúng bộ lọc đang chọn

Mốc export/print workflow hiện tại:
- có preset xuất đề để tái sử dụng cấu hình thường dùng của giáo viên
- hỗ trợ lưu / nạp / xóa mẫu xuất đề ngay trong app
- preset được lưu cục bộ trong dữ liệu người dùng để thuận tiện sao lưu
- có preset mặc định tự áp dụng theo ngân hàng hoặc theo cặp khoa + môn
- bộ chọn loại đề hỗ trợ `Trắc nghiệm`, `CRQ`, `Hỗn hợp`
- `CRQ` là family riêng; `ES` và `PR` vẫn được giữ riêng để thống kê
- đề chỉ CRQ không sinh phiếu trả lời riêng
- đề hỗn hợp chỉ sinh phiếu trả lời cho phần trắc nghiệm
- phần CRQ luôn nằm cuối đề và được đánh số lại từ 1
- preset cũ `Trắc nghiệm + CRQ` tự được chuẩn hóa thành `Hỗn hợp`
- batch export nhiều đề được đóng thành package có naming convention chuẩn
- print profile hỗ trợ chọn khổ giấy, chỉnh lề và ẩn/hiện block thông tin sinh viên
- hỗ trợ cover sheet và watermark cho luồng in ấn/phát hành nội bộ
- có thể tách file đáp án `.docx` riêng cho giáo viên
- có cover sheet template, watermark preset và chính sách đặt tên file đáp án
- có bước preview/xác nhận kế hoạch xuất trước khi render thật
- preview batch có liệt kê file dự kiến, cảnh báo ghi đè và summary naming conflict
- có `dry-run package manifest` chi tiết hơn, kèm preview nội dung in và print profile trước khi render

Mốc metadata ngân hàng hiện tại:
- dialog metadata ngân hàng dùng nhãn `Học phần` cho field dữ liệu nền `subject`
- `Loại đánh giá` là combobox chuẩn với `Thường xuyên`, `Định kỳ`, `Tổng kết`
- hỗ trợ danh sách động `Chuẩn đầu ra học phần` gồm `Mã CLO` và `Mô tả CLO`
- metadata `exam_title` cũ vẫn được giữ để tương thích với nhánh export nhưng không còn là field đang dùng trong dialog ngân hàng

## Bắt đầu nhanh (Môi trường phát triển)

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements-dev.txt
python main.py
```

## Chạy test

```bash
.venv\Scripts\python.exe -m pytest tests/unit -v
```

## Cấu trúc dự án

```text
quiz_desktop_app/
├── main.py              Điểm vào ứng dụng
├── config/              Cấu hình, đường dẫn, database
├── core/
│   ├── database/        SQLAlchemy models, Alembic migrations, session
│   ├── domain/          Thực thể và lớp dịch vụ
│   └── utils/           Hằng số, exceptions, logger, helpers, validators
├── modules/             Các module nghiệp vụ (import, grading, runner, ...)
├── ui/                  PySide6 views, widgets, dialogs, styles
├── tests/               Unit, integration và UI tests
└── data/                Dữ liệu người dùng (được gitignore)
```

## Công nghệ sử dụng

| Thành phần | Thư viện |
| --- | --- |
| Desktop UI | PySide6 >= 6.6 |
| Database | SQLite qua SQLAlchemy >= 2.0 |
| Migrations | Alembic >= 1.13 |
| Settings | pydantic-settings >= 2.0 |
| Logging | loguru >= 0.7 |
| Testing | pytest + pytest-qt + pytest-cov |
| Packaging | PyInstaller >= 6.0 |

## Định dạng Import

Xem [QUIZ_APP_IMPORT_FORMAT.md](QUIZ_APP_IMPORT_FORMAT.md) cho schema import
CSV / Excel chính thức.

## Kiến trúc

Xem [QUIZ_APP_ARCHITECTURE.md](QUIZ_APP_ARCHITECTURE.md) cho tài liệu thiết kế đầy đủ,
bao gồm schema database, quy tắc mode và chuẩn coding.

## Triết lý Thiết kế Phần mềm

Dự án này tuân theo các nguyên tắc thiết kế chiến lược được điều chỉnh từ
`philosophy_of_software_design.md` để kiểm soát complexity dài hạn.

1. Ưu tiên giảm complexity hơn tốc độ triển khai ngắn hạn.
2. Ưu tiên deep module: interface nhỏ, năng lực xử lý nội bộ mạnh.
3. Tránh pass-through class/method không tạo giá trị trừu tượng.
4. Kéo complexity xuống services/modules, không đẩy lên UI handlers.
5. Giữ business rules trong một nguồn sự thật để tránh rò rỉ.
6. Xử lý exception có mục tiêu; broad catch phải có log ngữ cảnh và đường phục hồi.
7. Bổ sung regression test và architecture guardrail test cho thay đổi rủi ro.

Để xem chính sách cấp dự án, tham khảo:

- [QUIZ_APP_ARCHITECTURE.md](QUIZ_APP_ARCHITECTURE.md)
- [QUIZ_APP_ROADMAP.md](QUIZ_APP_ROADMAP.md)
- [docs/crq_export_changes.md](docs/crq_export_changes.md)
