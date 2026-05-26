# Quiz Desktop App

Desktop-first, offline-first quiz application built with Python and PySide6.

## Quick Start (Development)

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements-dev.txt
python main.py
```

## Run Tests

```bash
pytest tests/unit -v
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

---

## Tiếng Việt

### Ứng dụng Quiz Desktop

Ứng dụng trắc nghiệm ưu tiên desktop và offline-first, xây dựng bằng Python và PySide6.

## Bắt đầu nhanh (Môi trường phát triển)

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements-dev.txt
python main.py
```

## Chạy test

```bash
pytest tests/unit -v
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
