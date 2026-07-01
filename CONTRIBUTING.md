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

## Policy And Terminology Sync Workflow

Use this workflow whenever a change affects permissions, business workflow,
access route, data-state transitions, UI terminology, or service contract.

Before starting a sweep:

- Freeze the scope from the user request or change brief before touching files.
- List the exact screens, dialogs, docs, and glossary terms in scope.
- Mark any historical or internal-only leftovers so they are not treated as UI regressions.
- Do not expand the sweep to new areas unless the user explicitly asks for it.

Run the steps in this exact order:

1. `Docs sweep`
   - Update the main source-of-truth documents first so they reflect the real business or technical change.
   - Typical targets: `QUIZ_APP_ARCHITECTURE.md`, `QUIZ_APP_ROADMAP.md`, `QUIZ_APP_IMPORT_FORMAT.md`, `README.md`, and relevant files under `docs/`.

2. `Policy sweep`
   - Separate the active flows clearly and remove or rewrite outdated flows that should no longer be considered valid.
   - Recheck permission rules, workflow branching, route/access rules, mode behavior, and data-state transitions.

3. `Consistency sweep`
   - Align UI text, service behavior, test descriptions, comments, and documentation so they all describe the same contract.
   - Eliminate mixed wording, duplicate rules, or stale references to older behavior.

4. `Final glossary sweep`
   - Lock the final terminology that should be used consistently across UI labels, docs, service names, comments, and test notes.
   - If a term changes, update every user-facing and developer-facing reference in the same change set.
   - Run a final grep over the scoped files and only treat the sweep as done when the remaining hits are approved internal identifiers or intentionally documented history.

Minimum completion rule for this workflow:

- The code, UI text, tests, and source-of-truth docs must describe the same active behavior.
- Old terms and deprecated flows should not remain in parallel unless backward compatibility is intentional and documented.
- If the change introduces a new canonical term, that term should appear consistently in docs, service contracts, and test language before the work is considered done.
- A sweep is not complete if there are still unexplained glossary hits in the scoped files, even when the UI already looks correct.
- If a leftover term is intentionally kept, document why it remains and where the canonical term lives.

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

## Quy trình Đồng bộ Policy Và Thuật ngữ

Sử dụng quy trình này bất cứ khi nào thay đổi có liên quan tới quyền,
workflow nghiệp vụ, route truy cập, chuyển trạng thái dữ liệu, thuật ngữ UI
hoặc service contract.

Trước khi bắt đầu sweep:

- Chốt phạm vi từ yêu cầu người dùng hoặc mô tả thay đổi trước khi đụng vào file.
- Liệt kê rõ các màn hình, hộp thoại, tài liệu và nhóm thuật ngữ nằm trong phạm vi.
- Đánh dấu sẵn mọi phần còn sót mang tính lịch sử hoặc chỉ dùng nội bộ để tránh nhầm là lỗi UI.
- Không mở rộng sweep sang khu vực mới nếu chưa có yêu cầu rõ ràng từ người dùng.

Thực hiện đúng thứ tự sau:

1. `Docs sweep`
   - Cập nhật các file nguồn chân lý chính trước để phản ánh đúng thay đổi nghiệp vụ hoặc kỹ thuật.
   - Các file thường cần rà: `QUIZ_APP_ARCHITECTURE.md`, `QUIZ_APP_ROADMAP.md`, `QUIZ_APP_IMPORT_FORMAT.md`, `README.md` và các file liên quan trong `docs/`.

2. `Policy sweep`
   - Tách rõ các luồng đang còn hiệu lực và loại bỏ hoặc viết lại các luồng cũ không còn được xem là đúng.
   - Kiểm tra lại rule về quyền, phân nhánh workflow, route/quy tắc truy cập, hành vi mode và chuyển trạng thái dữ liệu.

3. `Consistency sweep`
   - Đồng bộ text UI, hành vi service, mô tả test, comment và tài liệu để tất cả cùng mô tả một contract.
   - Loại bỏ cách gọi lẫn lộn, rule trùng lặp hoặc tham chiếu cũ không còn đúng.

4. `Final glossary sweep`
   - Khóa lại thuật ngữ chuẩn sẽ được dùng xuyên suốt UI, docs, tên service, comment và test notes.
   - Nếu đổi thuật ngữ, phải cập nhật toàn bộ tham chiếu liên quan trong cùng một change set.
   - Chạy grep cuối trên các file trong phạm vi và chỉ xem sweep là hoàn tất khi các hit còn lại đều là identifier nội bộ đã chấp thuận hoặc lịch sử được ghi chú rõ.

Typical sweep scope for UI-heavy changes:

- Core workflow screens: `question_bank_view`, `question_editor_dialog`, `quiz_runner_layout`, `quiz_runner_view`, `quiz_runner_setup_mixin`.
- Supporting dialogs: `bank_meta_dialog`, `question_pool_picker_dialog`, `import_preview_dialog`, `submission_settings_dialog`.
- Operational screens: `dashboard_view`, `import_view`, `settings_view`, `main_window`, `result_history_view`.
- Export/print surfaces: `exam_export_panel`, `word_renderer`, naming/manifest helpers, preview dialogs.
- Update order during a sweep:
  1. Align the user-facing labels in the affected screens.
  2. Align helper text, placeholders, table headers, tooltips, and status messages.
  3. Align tests and comments that mention the same contract.
  4. Align docs/README/import format/roadmap entries that describe the same behavior.
  5. Run a final grep for deprecated terms before considering the sweep complete.

Điều kiện tối thiểu để xem là hoàn tất quy trình:

- Code, UI text, test và các file nguồn chân lý phải cùng mô tả một hành vi đang có hiệu lực.
- Không để thuật ngữ cũ hoặc luồng cũ tồn tại song song nếu không có chủ đích tương thích ngược và chưa được ghi rõ.
- Nếu xuất hiện thuật ngữ chuẩn mới, thuật ngữ đó phải được dùng nhất quán trong docs, service contract và ngôn ngữ test trước khi xem là xong.
- Một sweep chưa thể xem là xong nếu vẫn còn các hit thuật ngữ chưa được giải thích trong các file thuộc phạm vi, dù UI đã nhìn có vẻ đúng.
- Nếu giữ lại một thuật ngữ cũ vì có chủ đích, phải ghi rõ vì sao nó còn tồn tại và thuật ngữ chuẩn nằm ở đâu.

## Bảo mật và Quyền riêng tư

Không commit dữ liệu local hoặc thông tin bí mật.
Ví dụ bị chặn bao gồm:

- `data/**`, backups, logs
- `*.db`, `*.sqlite`, `*.sqlite3`
- `.env`, keys, credentials

Repository đã có cơ chế bảo vệ tự động ở pre-commit và CI để ngăn rò rỉ dữ liệu ngoài ý muốn.
