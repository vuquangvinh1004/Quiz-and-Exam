# Security Policy

## Supported Versions

Security updates are provided for the latest commit on the `main` branch.

## Reporting a Vulnerability

Please do not open public issues for security vulnerabilities.

Send a private report with steps to reproduce, impact, and affected files to:

- GitHub Security Advisories (preferred)
- Repository owner: `vuquangvinh1004`

We will acknowledge reports within 72 hours and provide an estimated timeline for remediation.

## Sensitive Data Rules

This project is offline-first and may contain local user data during runtime.
Do not commit or publish any sensitive local data, including:

- database files (`*.db`, `*.sqlite`, `*.sqlite3`)
- logs, backups, temporary exports
- `.env` and secret keys

Automated guards are enabled in pre-commit and CI to block these files.

---

## Tiếng Việt

### Chính sách Bảo mật

## Phiên bản được hỗ trợ

Cập nhật bảo mật được áp dụng cho commit mới nhất trên nhánh `main`.

## Báo cáo lỗ hổng bảo mật

Vui lòng không tạo issue công khai cho các lỗ hổng bảo mật.

Hãy gửi báo cáo riêng tư kèm theo bước tái hiện, mức độ ảnh hưởng và các file liên quan tới:

- GitHub Security Advisories (ưu tiên)
- Chủ repository: `vuquangvinh1004`

Chúng tôi sẽ phản hồi xác nhận trong vòng 72 giờ và cung cấp thời gian dự kiến để khắc phục.

## Quy tắc dữ liệu nhạy cảm

Dự án này theo mô hình offline-first và có thể chứa dữ liệu người dùng local trong quá trình chạy.
Không commit hoặc publish bất kỳ dữ liệu local nhạy cảm nào, bao gồm:

- file database (`*.db`, `*.sqlite`, `*.sqlite3`)
- logs, backups, file export tạm
- `.env` và khóa bí mật

Cơ chế bảo vệ tự động đã được bật ở pre-commit và CI để chặn các file này.
