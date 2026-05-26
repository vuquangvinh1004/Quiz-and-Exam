# Contributing

Thank you for contributing to this project.

## Development Setup

1. Create and activate a virtual environment.
2. Install dependencies:
   - `pip install -r requirements.txt`
   - `pip install -r requirements-dev.txt`
3. Run the app:
   - `python main.py`

## Quality Checks

Before opening a pull request:

1. Run lint and format checks:

   - `ruff check .`
   - `ruff format --check .`

2. Run tests:

   - `python -m pytest tests/unit tests/integration -q`
   - `python -m pytest tests/ui -q`

## Pull Request Guidelines

- Keep changes focused and reviewable.
- Add or update tests for logic changes.
- Update docs when behavior, architecture, or workflows change.
- Follow existing naming and structure conventions.

## Security and Privacy

Do not commit local data or secrets.
Blocked examples include:

- `data/**`, backups, logs
- `*.db`, `*.sqlite`, `*.sqlite3`
- `.env`, keys, credentials

The repository includes automated guards in pre-commit and CI to prevent accidental leaks.

---

## Tiếng Việt

### Hướng dẫn Đóng góp

Cảm ơn bạn đã đóng góp cho dự án.

## Thiết lập môi trường phát triển

1. Tạo và kích hoạt môi trường ảo.
2. Cài đặt dependencies:
   - `pip install -r requirements.txt`
   - `pip install -r requirements-dev.txt`
3. Chạy ứng dụng:
   - `python main.py`

## Kiểm tra chất lượng

Trước khi mở pull request:

1. Chạy kiểm tra lint và format:

   - `ruff check .`
   - `ruff format --check .`

2. Chạy test:

   - `python -m pytest tests/unit tests/integration -q`
   - `python -m pytest tests/ui -q`

## Quy tắc Pull Request

- Giữ thay đổi tập trung, dễ review.
- Thêm hoặc cập nhật test cho các thay đổi logic.
- Cập nhật tài liệu khi thay đổi hành vi, kiến trúc hoặc workflow.
- Tuân thủ quy ước đặt tên và cấu trúc hiện có của dự án.

## Bảo mật và Quyền riêng tư

Không commit dữ liệu local hoặc thông tin bí mật.
Ví dụ bị chặn bao gồm:

- `data/**`, backups, logs
- `*.db`, `*.sqlite`, `*.sqlite3`
- `.env`, keys, credentials

Repository đã có cơ chế bảo vệ tự động ở pre-commit và CI để ngăn rò rỉ dữ liệu ngoài ý muốn.
