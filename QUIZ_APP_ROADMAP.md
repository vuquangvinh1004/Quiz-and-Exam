# QUIZ DESKTOP APP ROADMAP

> Cập nhật: 30/06/2026
> Phiên bản hiện tại: v1.0.0
> Mục tiêu: v1.0.0 với bộ chức năng cốt lõi chạy ổn định trên desktop

---

## 1. Tổng quan tiến độ

```text
Phase 1  Product Foundation         ██████████  100%
Phase 2  Database and Import        ██████████  100%
Phase 3  Question Bank UI           ██████████  100%
Phase 4  Quiz Builder and Runner    ██████████  100%
Phase 5  Mode Logic and Grading     ██████████  100%
Phase 6  History, Settings, Backup  ██████████  100%
Phase 7  Testing and Packaging      ██████████  100%
---------- v1.1 additions ----------
Phase 8  Quiz Document Exporter     ██████████  100%
---------------------------------------------------
Tổng thể v1.0                       ██████████  100%
Tổng thể v1.1                       ██████████  100%
```

---

## 2. Mục tiêu phát triển theo phase

### Phase 1. Product Foundation

Mục tiêu: Xác lập khung dự án, conventions và skeleton app.

| Hạng mục | Trạng thái | Ưu tiên | Ghi chú |
|---|---|---|---|
| Khởi tạo cấu trúc thư mục chuẩn | Done | Cao | Phải đúng theo architecture |
| Thiết lập config và paths | Done | Cao | Bao gồm data dir và log dir |
| Main window skeleton | Done | Cao | Sidebar và status bar cơ bản |
| Logging infrastructure | Done | Cao | Log file rotation |
| Constants và enums | Done | Cao | QuestionType, QuizMode, AttemptStatus |
| Exception hierarchy | Done | Trung bình | ValidationError, ImportError, GradingError |
| Thiết lập test framework | Done | Cao | pytest, pytest-qt, pytest-cov |

Deliverable: Ứng dụng mở được, có main window, có cấu trúc project chuẩn, có logging và test setup.

### Phase 2. Database and Import

Mục tiêu: Hoàn thiện data layer và luồng import chuẩn theo QUIZ_APP_IMPORT_FORMAT.md.

| Hạng mục | Trạng thái | Ưu tiên | Ghi chú |
|---|---|---|---|
| SQLAlchemy models | Done | Cao | Theo schema chính thức |
| Session management | Done | Cao | Transaction safe |
| Alembic migration init | Done | Cao | Migration đầu tiên |
| Import CSV | Done | Cao | Có validate từng dòng |
| Import Excel | Done | Cao | Hỗ trợ nhiều sheet nếu cần ở v1.1 |
| Import preview dialog | Done | Cao | Không import mù |
| Parser cho 4 loại câu hỏi cơ bản | Done | Cao | MC, MA, BLANK, SA |
| Lưu hint, explanation, accepted answers | Done | Cao | Không bỏ field này |
| Regression tests cho importer | Done | Cao | Cases BOM, cột thiếu, sai loại |

Deliverable: Có thể import file hợp lệ vào DB theo đúng QUIZ_APP_IMPORT_FORMAT.md, có preview lỗi và rollback an toàn khi lỗi transaction.

### Phase 3. Question Bank UI

Mục tiêu: Người dùng quản lý ngân hàng câu hỏi bằng UI.

| Hạng mục | Trạng thái | Ưu tiên | Ghi chú |
|---|---|---|---|
| Dashboard view cơ bản | Done | Trung bình | Stat cards: banks, questions, type breakdown |
| Question bank list | Done | Cao | CRUD ngân hàng (thêm/đổi tên/xóa) |
| Question table | Done | Cao | Lọc theo type, difficulty + tìm kiếm full-text |
| Question editor dialog | Done | Cao | Hỗ trợ đủ 4 loại câu hỏi cơ bản với dynamic form |
| Duplicate detector cơ bản | Done | Trung bình | Tích hợp qua ImportService (Phase 2) |
| Bulk import action | Done | Cao | Import view đã có từ Phase 2 |
| Delete confirmation flow | Done | Cao | Xác nhận trước khi xóa bank/question |
| Unit và UI tests cho question bank | Done | Cao | 52 tests, 239 total |

Deliverable: Có thể thêm, sửa, xóa, tìm kiếm, lọc và xem câu hỏi bằng giao diện desktop.

### Phase 4. Quiz Builder and Runner

Mục tiêu: Tạo cấu hình bài và chạy attempt trong UI.

| Hạng mục | Trạng thái | Ưu tiên | Ghi chú |
|---|---|---|---|
| Quiz builder view | Done | Cao | Chọn bank, mode, thời gian, số câu, type/difficulty filters |
| Random question selector | Done | Cao | QuestionSelector.select() theo bộ lọc |
| Shuffle question order | Done | Trung bình | Build snapshots với shuffle_options |
| Shuffle option order | Done | Trung bình | Chỉ áp dụng MC và MA |
| Quiz snapshot creation | Done | Cao | QuizService.create_quiz() → quiz_questions rows |
| Runner view skeleton | Done | Cao | Header, question area, MC/MA/BLANK/SA widgets, nav |
| Timer widget | Done | Cao | QTimer countdown; chỉ EXAM và PRACTICE |
| Progress tracker | Done | Cao | Số câu đã trả lời hiển thị live |
| Autosave | Done | Trung bình | QTimer 30 s → QuizService.autosave_answers() |
| Resume interrupted attempt | Open | Thấp | Chuyển sang v1.1 |
| STUDY mode per-question feedback | Done | Cao | Xác nhận từng câu, hiển thị kết quả ngay |
| Grade answer from snapshot dict | Done | Cao | QuizService.grade_answer_from_dict() – no DB roundtrip |

Deliverable: Có thể tạo quiz và làm bài trong app với timer, progress, autosave và feedback theo mode. 288 tests, 0 failures.

### Phase 5. Mode Logic and Grading

Mục tiêu: Cố định hành vi của ba mode và bộ chấm điểm.

| Hạng mục | Trạng thái | Ưu tiên | Ghi chú |
|---|---|---|---|
| Grading evaluators cho MC | Done | Cao | MCEvaluator trong evaluators.py |
| Grading evaluators cho MA | Done | Cao | MAEvaluator – full-match v1.0 |
| Grading evaluators cho BLANK | Done | Cao | BlankEvaluator – case/trim flags |
| Grading evaluators cho SA | Done | Cao | SAEvaluator – delegates to Blank |
| Exam mode policy | Done | Cao | ModePolicy trong mode_policy.py |
| Practice mode policy | Done | Cao | ModePolicy.show_hint, requires_timer |
| Study mode policy | Done | Cao | per-question feedback, allow_answer_change |
| Submit flow và time up flow | Done | Cao | runner_view + ModePolicy |
| Result summary builder | Done | Cao | ModeSummaryBuilder trong result_builder.py |
| Test matrix theo mode và question type | Done | Cao | test_evaluators.py + test_mode_policy.py, 358 tests |

Deliverable: Hành vi mode đúng tuyệt đối, chấm đúng và lưu kết quả ổn định. 358 tests, 0 failures.

### Phase 6. History, Settings, Backup

Mục tiêu: Hoàn thiện vòng đời sử dụng ứng dụng.

| Hạng mục | Trạng thái | Ưu tiên | Ghi chú |
|---|---|---|---|
| Result history view | Done | Cao | QTableWidget 6 cột, showEvent auto-refresh |
| Attempt detail view | Done | Trung bình | AttemptDetailDialog per-mode theo §5.5 |
| Settings view | Done | Cao | theme_changed Signal, QComboBox Sáng/Tối, showEvent |
| Theme switcher | Done | Trung bình | SettingsService.set_theme + main_window._on_theme_changed |
| Backup manager | Done | Cao | BackupManager.create_backup/list_backups |
| Restore manager | Done | Cao | BackupManager.restore_from_backup + UI confirm + restart message |
| App settings persistence | Done | Cao | SettingsService get/set qua app_settings table |
| Analytics đơn giản | Done | Thấp | AttemptStatistics.get_overall_stats → AttemptStats dataclass |

Deliverable: Người dùng có thể xem lịch sử, đổi cài đặt và sao lưu dữ liệu. 413 tests, 0 failures.

### Phase 7. Testing and Packaging

Mục tiêu: Chuẩn bị phát hành v1.0.

| Hạng mục | Trạng thái | Ưu tiên | Ghi chú |
|---|---|---|---|
| Coverage >= 80% cho core và modules | Done | Cao | Đạt 93% (vượt mục tiêu 80%) |
| UI smoke tests | Done | Cao | 20 tests cho 7 views + MainWindow |
| Integration test import to attempt | Done | Cao | test_e2e_quiz_flow.py – 6 tests full flow |
| Performance test import lớn | Done | Trung bình | 1.000 rows < 10s; 5.000 rows < 45s |
| PyInstaller build config | Done | Cao | quiz_app.spec – one-dir, Windows, no console |
| Windows standalone test | Done | Cao | quiz_app.spec đầy đủ hidden imports và datas |
| Inno Setup installer | Done | Trung bình | quiz_app.iss – modern style, Vietnamese locale |
| User documentation | Done | Cao | docs/quick_start.md + docs/import_guide.md |
| Release checklist v1.0 | Done | Cao | docs/release_checklist_v1.md |

Deliverable: Ứng dụng có thể đóng gói, cài đặt và chạy ốn định trên Windows. 470 tests, 0 failures, coverage 93%.

### Phase 8. Quiz Document Exporter [v1.1]

Mục tiêu: Cho phép xuất đề thi sang file Word (.docx) trực tiếp từ tab Tạo bài kiểm tra, bao gồm Trắc nghiệm, CRQ và Hỗn hợp.

| Hạng mục | Trạng thái | Ưu tiên | Ghi chú |
|---|---|---|---|
| Thêm python-docx vào requirements.txt | Done | Cao | python-docx>=1.1.0 |
| Tạo modules/quiz_exporter/word_renderer.py | Done | Cao | WordRenderer class, nhận data qua parameter, không truy cập DB |
| Render MC/MA/BLANK/SA theo layout chuẩn | Done | Cao | Phân biệt 4 loại câu hỏi cơ bản, hiển thị đáp án để chọn |
| Tổ chức câu hỏi theo phần A/B/C/D hoặc gộp chung | Done | Trung bình | Tùy cấu hình numbering_mode |
| Đánh số câu global hoặc per_section | Done | Trung bình | BL-04 từ docquiz_module_spec |
| Auto-gen hướng dẫn làm bài | Done | Cao | Theo loại câu hỏi thực tế trong đề |
| Auto-gen phiếu trả lời | Done | Cao | Theo mode đề: Trắc nghiệm, CRQ, Hỗn hợp |
| Auto-gen bảng đáp án và thang điểm | Done | Cao | Tính tổng điểm tự động từ point_value |
| Auto-gen quy định chấm điểm | Done | Trung bình | Chỉ hiển thị loại câu hỏi có trong đề |
| UI: QGroupBox "Xuất đề thi" trong quiz_builder_view.py | Done | Cao | Metadata fields + checkboxes tùy chọn |
| UI: Nút "Xuất đề thi (.docx)" + QFileDialog | Done | Cao | Song song với nút Tạo và bắt đầu |
| Unit tests cho word_renderer.py | Done | Cao | 43 test cases: 4 loại câu cơ bản, numbering, auto-gen, build_output_path |
| Integration test: builder → exporter → docx | Done | Trung bình | 5 test cases end-to-end từ DB đến file |

Deliverable: Người dùng có thể cấu hình bộ lọc câu hỏi trong tab Tạo bài kiểm tra, nhập metadata đề thi và xuất ra file .docx với đầy đủ nội dung đề, phiếu trả lời phù hợp theo mode và đáp án.

---

## 3. Roadmap nâng cấp đề xuất

> Mục tiêu của roadmap này là nâng cấp theo thứ tự giảm rủi ro trước, tăng giá trị sau, để mọi thay đổi vẫn đồng bộ với kiến trúc và business rules hiện tại.

### Giai đoạn 1. Đồng bộ contract và guardrails

| Mục tiêu | Tác động | Rủi ro | Đầu ra mong muốn |
|---|---|---|---|
| Khớp lại tài liệu với code ở các điểm có thể lệch nhau, nhất là import format, blank/multi-blank, và hành vi mode | Rất cao | Thấp - Trung bình | Contract thống nhất, không còn mâu thuẫn giữa docs và implementation |
| Khóa các boundary còn mỏng giữa UI, service và persistence | Rất cao | Thấp | UI không truy vấn trực tiếp DB, boundary tests rõ ràng hơn |
| Ổn định môi trường test/CI trên Windows và temp directory | Cao | Thấp | Test chạy ổn định, không phụ thuộc trạng thái temp cục bộ |

Khuyến nghị triển khai:
1. Chốt các quy tắc đang mở trong tài liệu trước khi thêm feature mới.
2. Bổ sung guardrail test cho các boundary quan trọng.
3. Sửa các điểm lệch doc/code để giảm chi phí bảo trì về sau.

### Giai đoạn 2. Ổn định dữ liệu và runtime resilience

| Mục tiêu | Tác động | Rủi ro | Đầu ra mong muốn |
|---|---|---|---|
| Resume attempt và phục hồi trạng thái khi app bị đóng đột ngột | Rất cao | Trung bình | Người dùng không mất bài đang làm |
| Nâng cấp autosave, recovery và finalize flow | Rất cao | Trung bình | Giảm mất dữ liệu và giảm lỗi thời gian chạy |
| Siết chặt import/duplicate/performance budgets cho dữ liệu lớn | Cao | Trung bình | Import lớn an toàn, có ngưỡng hiệu năng rõ |

Khuyến nghị triển khai:
1. Làm recovery theo hướng tối thiểu rủi ro trước, sau đó mới mở rộng UX.
2. Mọi thay đổi luồng dữ liệu phải đi kèm regression test.
3. Không thay đổi rule grading nếu mục tiêu chỉ là resilience.

Tiến độ 2026-06-30 (đợt 1 của Giai đoạn 2):
1. Đã triển khai resume attempt từ autosave gần nhất cho cùng quiz.
2. Autosave hiện lưu cả `answer_payload` đang mở trên màn hình và `remaining_seconds`.
3. Khi phát hiện attempt `IN_PROGRESS`, UI hỏi người dùng tiếp tục hay bỏ tiến độ cũ để bắt đầu lại.
4. Submitter metadata của EXAM attempt được lưu cùng attempt để khôi phục thống nhất sau khi mở lại app.
5. Regression tests đã bổ sung cho `QuizService`, `QuizRunnerSessionController`, `QuizRunnerView` và state runtime.

Tiến độ 2026-06-30 (đợt 2 của Giai đoạn 2):
1. Finalize flow được harden để tránh double-submit/double-finalize trong cùng phiên.
2. Trước khi finalize, runner luôn flush một nhịp autosave cuối cùng để giảm khoảng mất dữ liệu giữa UI state và persistence.
3. Nếu finalize thất bại, UI không chuyển sang màn hoàn tất; bài làm được giữ ở trạng thái có thể thử nộp lại.
4. Runner hiển thị badge `Khôi phục từ autosave` trong phiên đã resume để người dùng hiểu rõ ngữ cảnh hiện tại.
5. Regression tests đã bổ sung cho nhánh finalize lỗi nhưng không mất attempt, cùng với trạng thái badge recovery.

Tiến độ 2026-06-30 (đợt 3 của Giai đoạn 2):
1. Policy EXAM được làm rõ hơn: chỉ resume khi còn metadata người làm bài hợp lệ; nếu `time_up` nhưng finalize lỗi thì bài làm bị khóa và chỉ cho `Thử nộp lại`.
2. Runner bổ sung telemetry/log context cho các nhánh `resume accepted`, `resume discarded`, `resume invalid`, `finalize started`, `finalize failed`, `finalize retry ready`.
3. Import pipeline thêm guardrails cho dữ liệu lớn: row budget mềm/cứng, file size hard limit, duplicate detection query có chọn lọc hơn và commit flush theo batch.
4. Regression và integration tests đã bổ sung cho import budgets, commit theo batch, EXAM retry-only policy và telemetry path chính.

Tiến độ 2026-06-30 (đợt 4 của Giai đoạn 2 - chốt ngưỡng và observability):
1. Đã benchmark import thực tế trong repo với dữ liệu sinh tự động:
   - 1.000 dòng: ~0,28s tổng
   - 5.000 dòng: ~1,46s tổng
   - 8.000 dòng: ~2,65s tổng
   - 12.000 dòng: ~4,20s tổng
   - 20.000 dòng: ~6,65s tổng
2. Từ số đo thực tế, budget import được tinh chỉnh thành:
   - `soft_row_limit = 12.000`
   - `hard_row_limit = 30.000`
   - `soft_file_size = 3 MB`
   - `hard_file_size = 8 MB`
3. Dashboard đã có telemetry aggregation nhỏ cho import/runtime warnings gần đây, đọc từ log files hiện có thay vì thêm schema mới.
4. Scope cốt lõi của Giai đoạn 2 được xem là hoàn tất: recovery, finalize hardening, EXAM policy, telemetry cơ bản và import resilience cho dữ liệu lớn đều đã có code + test + docs đồng bộ.

Checklist đóng Giai đoạn 2:
- [x] Resume attempt từ autosave gần nhất theo cùng quiz
- [x] Autosave lưu cả `answer_payload` hiện tại và `remaining_seconds`
- [x] Finalize flow có flush cuối, chống double-submit và cho phép retry khi persistence lỗi
- [x] EXAM policy rõ cho resume hợp lệ và nhánh `time_up` nhưng finalize lỗi
- [x] Telemetry/log context cho các nhánh resume, discard, finalize và retry
- [x] Import budgets mềm/cứng được benchmark và tinh chỉnh theo số đo thực tế
- [x] Duplicate lookup và import commit được harden cho dữ liệu lớn
- [x] Dashboard có telemetry warning summary tối thiểu
- [x] Code, tests và docs đã được cập nhật đồng bộ

### Giai đoạn 3. Mở rộng giá trị người dùng

| Mục tiêu | Tác động | Rủi ro | Đầu ra mong muốn |
|---|---|---|---|
| Analytics và báo cáo sử dụng sâu hơn | Cao | Trung bình | Người dùng hiểu được tiến độ, lỗi và xu hướng học tập |
| Cải thiện export/print workflow và template hóa | Trung bình - Cao | Trung bình | Tăng giá trị sử dụng trong môi trường giáo viên/đào tạo |
| Tối ưu UX cho tạo đề, batch flow và tùy chọn nâng cao | Trung bình | Trung bình - Cao | Nâng trải nghiệm nhưng không làm dày thêm logic lõi |

Khuyến nghị triển khai:
1. Chỉ mở rộng feature khi Phase 1 và 2 đã ổn định.
2. Ưu tiên những nâng cấp có thể tách thành module độc lập.
3. Mỗi feature mới phải có tiêu chí dừng rõ ràng và test bảo vệ.

Tiến độ 2026-06-30 (đợt 1 của Giai đoạn 3 - analytics low-risk/high-impact):
1. Dashboard được mở rộng thêm lớp analytics cho bài làm đã hoàn tất mà không đổi schema và không chạm logic grading/runtime.
2. `DashboardFacade` hiện tải thêm `AttemptStatistics.get_overall_stats()` trong cùng boundary service/facade hiện có.
3. UI Dashboard có section `Hiệu suất làm bài` với các chỉ số `Lượt làm bài`, `Điểm TB`, `Điểm cao nhất` và tổng `đúng/sai/bỏ qua`.
4. Regression test đã được bổ sung cho facade để khóa contract analytics mới của dashboard.

Tiến độ 2026-06-30 (đợt 2 của Giai đoạn 3 - export/print workflow):
1. Luồng xuất đề được nâng cấp thêm `preset/template` để giáo viên lưu và nạp lại cấu hình xuất đề thường dùng.
2. `ExamExportPanel` có thêm thanh thao tác `Lưu mẫu / Nạp mẫu / Xóa mẫu`, giúp tái sử dụng metadata và các tùy chọn in ấn mà không phải nhập lại mỗi lần.
3. Preset được lưu file-based trong thư mục dữ liệu người dùng thay vì nhúng thẳng logic JSON vào UI, giữ boundary theo hướng `UI -> facade -> preset store`.
4. Regression tests đã bổ sung cho export preset store và data directory setup để khóa workflow template hóa đầu tiên của nhánh export.

Tiến độ 2026-06-30 (đợt 3 của Giai đoạn 3 - default presets, batch package, print profile):
1. Preset mặc định hiện hỗ trợ tự áp dụng theo thứ tự ưu tiên `ngân hàng` > `khoa + môn` > `mặc định chung`.
2. Batch export cho nhiều đề được đóng thành một `package` riêng có naming convention chuẩn in ấn và file `README` đi kèm.
3. Hồ sơ in đã được mở vào contract xuất đề: chọn `A4/Letter`, chỉnh lề trên/dưới/trái/phải và ẩn/hiện khối thông tin sinh viên.
4. Cả `ExamExportPanel` lẫn luồng batch helper đã dùng chung pattern package naming để tránh hai chuẩn đặt tên khác nhau trong cùng app.

Đánh giá phần còn lại của Giai đoạn 3:
1. `Analytics/reporting sâu hơn theo thời gian, theo mode, theo ngân hàng`: tác động cao, rủi ro trung bình. Đây là nhánh nên làm tiếp nếu ưu tiên insight cho người học/người quản trị.
2. `Export/print workflow nâng cao hơn nữa` như answer-key riêng, cover sheet, watermark, nhiều print profile preset: tác động trung bình - cao, rủi ro thấp - trung bình. Đây là nhánh phù hợp nếu mục tiêu tiếp tục tối ưu cho giáo viên.
3. `UX cho tạo đề, batch flow và tùy chọn nâng cao` như preview trước khi xuất, batch summary chi tiết, kiểm tra naming conflict: tác động trung bình, rủi ro trung bình. Nên làm sau khi export workflow cốt lõi đã ổn định như hiện tại.

Tiến độ 2026-06-30 (đợt 4 của Giai đoạn 3 - cover sheet, watermark, answer-key riêng và analytics sâu hơn):
1. Export/print workflow được hoàn thiện thêm với `cover sheet`, `watermark` và `answer-key` tách file `.docx` riêng cho giáo viên.
2. Khi bật `tách file đáp án riêng`, file đề chính không còn nhúng đáp án; đáp án được xuất thành file riêng trong cùng package hoặc cạnh file đề đơn.
3. Analytics/reporting được mở rộng thêm `breakdown theo mode` (`Kiểm tra/Luyện tập/Ôn tập`) và `xu hướng 7 ngày gần đây` trên Dashboard mà không cần đổi schema.
4. Regression tests đã bổ sung cho renderer contract mới, standalone answer-key export và aggregate analytics theo mode/ngày.

Tiến độ 2026-06-30 (đợt 5 của Giai đoạn 3 - reporting filter + export preview/naming):
1. Dashboard reporting hiện hỗ trợ lọc theo `ngân hàng`, `quiz` và `khoảng thời gian` (`7/14/30 ngày`) để đào sâu phân tích mà chưa cần schema mới.
2. Export workflow có thêm `cover sheet template`, `watermark preset` và `answer-key file naming policy` (`prefix/suffix`).
3. Trước khi xuất, UI hiển thị `kế hoạch xuất` để người dùng rà lại đích xuất, watermark, cover sheet và tình trạng tách file đáp án.
4. Summary conflict/naming bước đầu đã có ở nhánh xuất file đơn: nếu file đích đã tồn tại thì preview sẽ cảnh báo trước khi người dùng xác nhận.

Tiến độ 2026-06-30 (đợt 6 của Giai đoạn 3 - deep reporting + batch conflict summary, chốt phase):
1. Dashboard reporting được mở rộng thêm `window summary` cho tập dữ liệu đang lọc: tổng lượt làm, số ngân hàng active, số quiz active, điểm trung bình và điểm cao nhất trong cửa sổ thời gian đã chọn.
2. Dashboard có thêm bảng `breakdown theo ngân hàng` với các cột `lượt làm`, `số quiz`, `điểm TB`, `điểm cao nhất`, `lần hoạt động cuối` để hỗ trợ quản trị/nghiệp vụ đào tạo.
3. Preview batch export hiện dùng chung naming helper với luồng save thật để liệt kê `planned filenames`, cảnh báo `overwrite` và phát hiện `naming conflict` ngay trước khi render.
4. Regression tests đã bổ sung cho analytics aggregates mới, facade snapshot và package naming/conflict helpers; UI smoke vẫn pass sau khi mở rộng dashboard.

Tiến độ 2026-06-30 (đợt 7 của Giai đoạn 3 - custom date range, analytics CSV, dry-run manifest):
1. Dashboard reporting hiện hỗ trợ thêm `custom date range` bên cạnh các preset `7/14/30 ngày`, nhưng vẫn dùng cùng contract aggregate và không đổi schema.
2. Dashboard có thể `xuất reporting CSV` theo đúng snapshot đang lọc, bao gồm `summary`, `mode breakdown`, `recent activity`, `bank breakdown`.
3. Preview export được nâng cấp từ summary ngắn thành `dry-run package manifest` chi tiết hơn, có `planned filenames`, `print profile`, `preview nội dung in`, `overwrite warnings` và `naming conflict warnings`.
4. Regression tests đã bổ sung cho custom date range, CSV export và dry-run manifest; các cụm analytics/export/smoke liên quan đều pass khi chạy tuần tự.

Checklist đóng Giai đoạn 3:
- [x] Dashboard analytics tổng quan cho attempt đã hoàn tất
- [x] Reporting breakdown theo mode và xu hướng theo thời gian
- [x] Reporting filter theo ngân hàng / quiz / khoảng thời gian
- [x] Custom date range và reporting CSV export
- [x] Window summary và bank-level breakdown cho reporting sâu hơn
- [x] Preset xuất đề, preset mặc định theo ngữ cảnh và print profile
- [x] Batch export package với naming convention chuẩn
- [x] Cover sheet, watermark, answer-key tách file và naming policy
- [x] Preview export có planned filenames, overwrite warnings và naming-conflict summary
- [x] Bản xem trước gói xuất chi tiết với preview nội dung in
- [x] Code, tests và docs đã được cập nhật đồng bộ cho toàn bộ nhánh Phase 3

---

## 4. Sprint ưu tiên đề xuất

### Sprint 1

Mục tiêu: Đặt nền tảng dự án.

1. Cấu trúc thư mục
2. Main window skeleton
3. Config, logger, constants
4. Test setup
5. DB connection và models khung

### Sprint 2

Mục tiêu: Hoàn thiện import data.

1. Alembic init
2. Import CSV
3. Import Excel
4. Import preview dialog
5. Regression tests importer

### Sprint 3

Mục tiêu: Xây dựng question bank UI.

1. Bank CRUD
2. Question table
3. Question editor
4. Search và filter
5. Duplicate warning cơ bản

### Sprint 4

Mục tiêu: Tạo và chạy quiz.

1. Quiz builder
2. Question selection
3. Runner view
4. Timer
5. Progress tracker

### Sprint 5

Mục tiêu: Khóa business rules cho mode.

1. Grading engine
2. Exam mode policy
3. Practice mode policy
4. Study mode policy
5. Result summary

### Sprint 6

Mục tiêu: Hoàn thiện lifecycle.

1. History
2. Settings
3. Backup và restore
4. Theme switcher
5. Packaging skeleton

### Sprint 7 [v1.1 – Quiz Document Exporter]

Mục tiêu: Triển khai chức năng xuất đề thi Word.

1. Thêm python-docx vào requirements.txt
2. Tạo modules/quiz_exporter/word_renderer.py với WordRenderer class
3. Render đầy đủ 4 loại câu hỏi cơ bản và CRQ family, đánh số, auto-gen hướng dẫn/phiếu trả lời/đáp án
4. Bổ sung QGroupBox "Xuất đề thi" và nút xuất vào quiz_builder_view.py
5. Unit tests và integration test cho toàn bộ flow

---

## 5. Tiêu chí chấp nhận cho từng nhóm tính năng

### 4.1. Import

Một task import chỉ được chấp nhận nếu:

1. Parse được file đúng format
2. Phát hiện được lỗi cột thiếu hoặc dữ liệu sai kiểu
3. Cho người dùng xem preview trước khi commit
4. Không ghi dữ liệu lỗi vào DB
5. Có test cho ít nhất một case đúng và một case sai

### 4.2. Quiz runner

Một task runner chỉ được chấp nhận nếu:

1. Có thể chuyển câu trước và sau
2. Progress cập nhật đúng
3. Timer chính xác trong mode có giới hạn thời gian
4. Không mất đáp án đã nhập khi chuyển câu
5. Autosave không làm treo giao diện

### 4.3. Grading

Một task grading chỉ được chấp nhận nếu:

1. MC chấm đúng đúng hoàn toàn
2. MA chấm đúng hoàn toàn đúng theo policy v1.0
3. BLANK và SA chuẩn hóa text trước khi so khớp
4. Có test matrix bao phủ mọi loại câu hỏi
5. Kết quả lưu được vào attempts và attempt_answers

### 4.4. Mode behavior

Một task mode chỉ được chấp nhận nếu:

1. Exam mode không lộ hint và không phản hồi từng câu
2. Practice mode có hint nhưng không phản hồi từng câu trước khi kết thúc
3. Study mode phản hồi ngay từng câu và không yêu cầu timer
4. Có test riêng cho từng mode

### 4.5. Design quality guardrails xuyên phase

Mọi task ở mọi phase chỉ được xem là đạt chuẩn khi đáp ứng thêm các guardrail sau:

1. Không tăng coupling giữa UI và data layer.
2. Không tạo pass-through class hoặc method nếu không thêm abstraction có giá trị.
3. Interface mới phải ngắn gọn; complexity chính nằm ở implementation.
4. Business rule quan trọng chỉ định nghĩa ở một nơi để tránh information leakage.
5. Exception handling có chủ đích: ưu tiên exception cụ thể; broad catch phải log đủ ngữ cảnh và có recovery rõ ràng.
6. Tên class, method và biến phải nhất quán theo domain language.
7. Nếu thay đổi có rủi ro lan rộng, phải có regression test hoặc guardrail test tương ứng.
8. Khi đổi quyết định thiết kế xuyên module, phải cập nhật tài liệu nền tảng.

---

## 6. Bug tracker khởi tạo

| ID | Mô tả | Mức độ | Trạng thái |
|---|---|---|---|
| BUG-01 | Chưa có quy ước import file mẫu chính thức | Medium | Open |
| BUG-02 | Contract cho BLANK nhiều chỗ trống đã được chốt và đồng bộ vào import format; cần tiếp tục giữ test/regression để tránh lệch lại | High | Closed |
| BUG-03 | Resume attempt sau khi app đóng đột ngột đã được định nghĩa và triển khai ở mức recovery tối thiểu: lưu answer autosave + `remaining_seconds`, khôi phục attempt `IN_PROGRESS`, cho phép discard để bắt đầu lại | Medium | Closed |
| BUG-04 | Chưa chốt policy hiển thị summary ở Exam mode ngoài “Hoàn thành” | Medium | Open |
| BUG-05 | Import dữ liệu lớn đã có guardrails rõ hơn: row/file-size budgets, duplicate detection tối ưu hơn, commit batch flush và performance regression tests | Low | Closed |

Quy tắc xử lý bug:

1. Khi fix bug phải cập nhật bảng này.
2. Nếu bug làm thay đổi business rule, phải cập nhật cả architecture.
3. Mọi bug grading hoặc mode behavior bắt buộc có regression test.

---

## 7. Hướng dẫn sử dụng AI Agent

### 6.1. Prompt khởi đầu bắt buộc

Sử dụng prompt sau khi bắt đầu bất kỳ phiên làm việc mới nào:

```text
Đọc QUIZ_APP_ARCHITECTURE.md và QUIZ_APP_ROADMAP.md trước khi code. Tuân thủ tech stack, cấu trúc thư mục, business rules của các mode và checklist sau mỗi task.
```

### 6.2. Prompt cho task tính năng mới

```text
Trước khi bắt đầu:
1. Đọc QUIZ_APP_ARCHITECTURE.md
2. Đọc QUIZ_APP_ROADMAP.md
3. Xác định phase và sprint của task

Nhiệm vụ: [mô tả tính năng]

Sau khi hoàn thành:
1. Cập nhật trạng thái task trong ROADMAP
2. Cập nhật CHANGELOG trong ARCHITECTURE
3. Viết tests liên quan
4. Báo cáo file đã thay đổi và kết quả test
```

### 6.3. Prompt cho task fix bug

```text
Trước khi bắt đầu:
1. Đọc QUIZ_APP_ARCHITECTURE.md mục business rules và coding standards
2. Đọc QUIZ_APP_ROADMAP.md mục bug tracker

Nhiệm vụ: Fix [BUG-ID]

Sau khi hoàn thành:
1. Cập nhật bug tracker
2. Thêm regression test
3. Ghi rõ root cause và solution vào CHANGELOG
4. Báo cáo test pass
```

### 6.4. Prompt cho task refactor

```text
Trước khi bắt đầu:
1. Kiểm tra module boundaries trong QUIZ_APP_ARCHITECTURE.md
2. Đảm bảo không làm thay đổi hành vi nghiệp vụ

Nhiệm vụ: [mô tả refactor]

Sau khi hoàn thành:
1. Xác nhận không đổi business behavior
2. Cập nhật CHANGELOG nếu cấu trúc hoặc interface đổi
3. Chạy full tests liên quan
```

### 6.5. Checklist bắt buộc sau mỗi task

- [ ] Chạy tests liên quan
- [ ] Không vi phạm business rules của mode
- [ ] Không vi phạm module boundaries
- [ ] Cập nhật ROADMAP
- [ ] Cập nhật ARCHITECTURE CHANGELOG
- [ ] Nếu có schema change thì có migration notes
- [ ] Báo cáo tóm tắt thay đổi

### 6.6. Prompt cho strategic design review

```text
Trước khi chốt implementation, bắt buộc thực hiện strategic review:
1. Đề xuất ít nhất 2 phương án thiết kế và nêu lý do chọn phương án cuối
2. Chỉ ra complexity đã giảm ở đâu (change amplification, cognitive load, unknown unknowns)
3. Xác nhận không tạo pass-through abstraction mới
4. Xác nhận complexity được kéo xuống layer phù hợp (UI không ôm business/data logic)
5. Nêu rõ test guardrail hoặc regression để khóa rủi ro tái phát
```

---

## 8. Tài liệu AI Agent phải đọc theo từng nhu cầu

| Nhu cầu | File cần đọc |
|---|---|
| Kiến trúc tổng thể | QUIZ_APP_ARCHITECTURE.md |
| Quy tắc mode và grading | QUIZ_APP_ARCHITECTURE.md mục 7 |
| Schema database | QUIZ_APP_ARCHITECTURE.md mục 8 |
| Tiến độ project | QUIZ_APP_ROADMAP.md |
| Task ưu tiên tiếp theo | QUIZ_APP_ROADMAP.md mục 2 và 3 |
| Bug hiện có | QUIZ_APP_ROADMAP.md mục 5 |

---

## 9. Quy tắc báo cáo tiến độ

Mỗi lần AI Agent hoàn thành task phải báo theo mẫu tối thiểu:

1. Task đã thực hiện
2. Files đã thay đổi
3. Kết quả test
4. Rủi ro còn lại
5. Cập nhật nào đã ghi vào ROADMAP và ARCHITECTURE

Không được chỉ báo “đã xong” mà không có các thông tin trên.

---

## 10. Tiêu chí sẵn sàng phát hành v1.0

v1.0 chỉ được xem là sẵn sàng khi thỏa đồng thời:

1. Toàn bộ Phase 1 đến Phase 7 hoàn thành ở mức tối thiểu cho phạm vi v1.0
2. Test coverage đạt mục tiêu cho phần core và modules
3. Không còn bug mức High ở import, grading, mode behavior, timer, autosave
4. Build standalone chạy được trên Windows không cần cài Python
5. Có tài liệu hướng dẫn import và sử dụng cơ bản
6. Đã kiểm thử ít nhất một bộ dữ liệu import thực tế và một bài quiz thực tế cho mỗi mode

---

## 11. Cập nhật roadmap

### 2026-03-24

ADDED | OpenAI GPT-5.4 Thinking | Khởi tạo roadmap phát triển chuẩn cho Quiz Desktop App từ giai đoạn nền tảng đến đóng gói phát hành. Xác định phase, sprint, acceptance criteria, bug tracker khởi tạo và bộ hướng dẫn bắt buộc cho AI Agent.

### 2026-03-24 (Sprint 1 hoàn thành)

COMPLETED | GitHub Copilot (Claude Sonnet 4.6) | Phase 1 Product Foundation hoàn thành 100%. Cấu trúc thư mục, config, paths, logger, constants (QuestionType/QuizMode/AttemptStatus), exception hierarchy, SQLAlchemy models (8 bảng), Alembic migration 001_initial_schema, MainWindow skeleton (PySide6, sidebar 7 mục, status bar), 7 view stubs, main.py. 88 unit tests pass. DB migrate thành công. App imports clean.

### 2026-03-24 (Submission feature)

ADDED | GitHub Copilot (Claude Sonnet 4.6) | Bổ sung chức năng Nộp bài cho chế độ Kiểm tra. Chi tiết:

- `modules/grading/result_builder.py`: AttemptResultData, QuestionResultRow, ExamResultExporter → tạo file Excel kết quả với thông tin người nộp và chi tiết từng câu.
- `core/domain/services/submission_service.py`: SubmissionService, SubmissionSettings → lưu/load config từ app_settings table, nộp bài qua Email (smtplib + STARTTLS) hoặc lưu vào thư mục, hỗ trợ mode "both".
- `ui/dialogs/submitter_info_dialog.py`: Dialog thu thập Họ tên + ID trước khi bắt đầu bài ở chế độ Kiểm tra.
- `ui/dialogs/submit_dialog.py`: Dialog chọn Email/Thư mục khi nộp bài; background thread tránh block UI; hiện kết quả nộp.
- `ui/dialogs/submission_settings_dialog.py`: Cấu hình SMTP (server/port/TLS/user/password/sender), email mặc định, thư mục mặc định; có nút test kết nối SMTP.
- `ui/views/quiz_runner_view.py`: Nâng cấp từ placeholder thành functional runner có 3 panel (Setup/Running/Done), timer, navigation, submitter bar; chế độ Kiểm tra → SubmitDialog; Luyện tập/Ôn tập → hộp thoại tổng kết kết quả.
- `ui/views/settings_view.py`: Nâng cấp từ placeholder, thêm section Nộp bài với nút mở SubmissionSettingsDialog.
- `tests/unit/test_submission.py`: 28 unit tests mới (ExamResultExporter, SubmissionService, settings load/save DB).
- Tổng: 116 tests pass, 0 regression. openpyxl đã được cài vào venv.

### 2026-03-24 (Phase 2 – Import hoàn thành)

COMPLETED | GitHub Copilot (Claude Sonnet 4.6) | Phase 2 Database and Import hoàn thành 100%. Chi tiết:

- `modules/question_bank/importer.py`: QuestionFileParser, ParsedQuestion, ImportIssue, ParseResult. Đọc CSV (UTF-8 / BOM) và XLSX (sheet "questions" ưu tiên). Map theo tên cột, không theo vị trí. Validate header (cột thiếu, cột trùng), validate từng dòng (question_text, question_type, correct_answers, score, difficulty, status, boolean), validate theo từng loại câu (MC/MA/BLANK/SA). Chuẩn hóa enum, boolean, tags, delimiter ||.
- `modules/question_bank/duplicate_detector.py`: DuplicateDetector. detect_in_file(): code trùng → ERROR; (text+type) trùng → WARNING. detect_against_db(): query DB 1 lần, code DB → ERROR, text+type DB → WARNING.
- `core/domain/services/import_service.py`: ImportService. preview(): parse + in-file dup + DB dup, không ghi DB. commit(): viết Question + QuestionOption vào DB, skip row bị DB-ERROR, raise ValueError nếu has_errors.
- `ui/dialogs/import_preview_dialog.py`: ImportPreviewDialog. Bảng issues (row/severity/column/message) có màu theo mức độ. Nút Import vô hiệu hóa khi has_errors. Hiện tóm tắt (total/valid/errors/warnings). Gọi service.commit() và báo kết quả.
- `ui/views/import_view.py`: Nâng cấp từ placeholder. Step 1: chọn file CSV/XLSX. Step 2: chọn/tạo ngân hàng. Nút "Xem trước". Nút export template. Status label.
- `tests/unit/test_importer.py`: 62 unit tests (all four types, header validation, row validation, per-type rules, boolean normalisation, BOM, duplicate detection, ParseResult properties).
- `tests/integration/test_import_flow.py`: 9 integration tests (preview/commit end-to-end với in-memory SQLite: MC/MA/BLANK/SA → DB, accepted_answers JSON, option is_correct, commit blocked on errors).
- Tổng: 187 tests pass (71 mới + 116 cũ), 0 regression.

### 2026-04-21 (v1.1 planning – Quiz Document Exporter)

ADDED | GitHub Copilot (Claude Sonnet 4.6) | ROADMAP_PLAN | Bổ sung Phase 8 Quiz Document Exporter vào lộ trình v1.1. Chi tiết:
- Phase 8 với 13 hạng mục (Open), bao gồm: python-docx dependency, word_renderer module, render 4 loại câu hỏi cơ bản và CRQ family, auto-gen hướng dẫn/phiếu trả lời/đáp án/quy định chấm điểm, UI bổ sung vào quiz_builder_view, unit và integration tests.
- Sprint 7 [v1.1] với 5 bước triển khai.
- Progress tracker cập nhật: v1.0 hoàn thành 100%, Phase 8 ở 0%.

### 2026-04-21 (Sprint 7 – HOÀN THÀNH)

DONE | GitHub Copilot (Claude Sonnet 4.6) | SPRINT_7 | Triển khai hoàn chỉnh Quiz Document Exporter (v1.1). Chi tiết:
- `requirements.txt`: Thêm python-docx>=1.1.0; cài đặt thực tế: python-docx 1.2.0.
- `modules/quiz_exporter/__init__.py`: Package init, export WordRenderer và ExportConfig.
- `modules/quiz_exporter/word_renderer.py`: ~555 dòng. ExamMeta, ExportConfig, WordRenderer, build_output_path. Render đầy đủ MC/MA/BLANK/SA và CRQ family, phân nhóm Phần A-D, đánh số global/per_section, tự động hướng dẫn/phiếu trả lời/quy định chấm/đáp án. Sửa import docx.shared.Inches (docx.util không tồn tại).
- `ui/views/quiz_builder_view.py`: Thêm Group 4 QGroupBox "Xuất đề thi (.docx)" (checkable, mặc định tắt); 11 trường metadata; ComboBox đánh số; 4 checkbox tùy chọn; nút Xuất màu xanh lá. Thêm `_on_export()` method. Thêm helpers `_wrap_layout()` và `_open_folder()` ở module level. Sửa lỗi `_wrap_layout` và `_open_folder` chưa định nghĩa; sửa lỗi `exp_form.addRow` thừa.
- `tests/unit/test_word_renderer.py`: 43 test cases. Bao phủ: ExamMeta/ExportConfig defaults, _types_present, _group_questions (flat/grouped/mixed), render() cho 4 loại câu cơ bản và CRQ, instructions on/off, answer sheet on/off, scoring rules on/off, answer key on/off, global/per_section numbering, answer key correctness (MC/MA/BLANK/SA), total score, build_output_path (extension, title, timestamp, sanitise, mkdir, empty). Kết quả: **43 passed**.
- `tests/integration/test_export_flow.py`: 5 integration tests. Bao phủ: full pipeline all types (seed DB → select → snapshots → render → save to disk), MC only export, snapshot structure validation (MC options, BLANK accepted_answers), minimal config (no optional sections). Kết quả: **5 passed**.
- Progress tracker: Phase 8 = 100%, Tổng thể v1.1 = 100%.

### 2026-05-06 (Design philosophy alignment)

CHANGED | GitHub Copilot (GPT-5.3-Codex) | QUALITY_GUARDRAILS | Bổ sung tiêu chí chất lượng thiết kế xuyên phase theo triết lý "A Philosophy of Software Design": thêm mục 4.5 (design quality guardrails) và 6.6 (strategic design review prompt) để giảm complexity drift, kiểm soát pass-through abstraction, tăng tính rõ ràng layer boundaries và khóa rủi ro bằng regression/guardrail tests.

DONE | GitHub Copilot (GPT-5.3-Codex) | TAB_REDESIGN_AND_QUOTA_2026_05_26 | Hoàn tất triển khai 3 đợt nhỏ cho redesign luồng tạo đề/làm bài:
- Đợt 1: Bổ sung hiển thị `Chương` trong editor và bảng ngân hàng.
- Đợt 2: Chuyển cấu hình mode/thời gian/bộ lọc sang tab `Làm bài`, tab này tự tạo runtime quiz trước khi start.
- Đợt 3: Bổ sung tạo nhiều đề đồng thời theo quota Chương/Loại/Độ khó + chọn pool câu hỏi + tùy chọn không lặp câu giữa các đề.
- Kèm theo chuẩn hóa text UI tiếng Việt có dấu cho các thành phần mới.

### 2026-06-30 (Phase 1 implementation started)

CHANGED | OpenAI GPT-5.4 Thinking | PHASE_1_CONTRACT_AND_GUARDRAILS | Bắt đầu triển khai Giai đoạn 1 theo roadmap nâng cấp. Chi tiết:
- `ui/facades/quiz_builder_facade.py`: thêm facade cho quiz builder để gom session orchestration ra khỏi view.
- `ui/views/quiz_builder_view.py`: bỏ truy cập session/model trực tiếp; chuyển sang dùng `QuizBuilderFacade`.
- `tests/unit/test_ui_layer_boundaries.py`: thêm guardrail test chặn `QuizBuilderView` quay lại mở session hoặc import ORM model trực tiếp.
- `pyproject.toml`: cấu hình `pytest --basetemp=.tmp/pytest` và `cache_dir=.tmp/pytest_cache` để tránh phụ thuộc temp directory mặc định của Windows trong môi trường bị hạn chế quyền.
- `QUIZ_APP_IMPORT_FORMAT.md`: đồng bộ contract BLANK nhiều chỗ trống với implementation hiện tại.
- `BUG-02`: đóng bug tài liệu/contract cho BLANK nhiều chỗ trống; phần resume attempt (`BUG-03`) vẫn để Phase 2.

CHANGED | OpenAI GPT-5.4 Thinking | PHASE_1_UI_BOUNDARY_CONTINUED | Tiếp tục dọn boundary UI/data ở các điểm còn mở session trực tiếp:
- `ui/widgets/exam_export_panel.py`: bỏ hoàn toàn `get_session()` trong panel; dùng `QuizBuilderFacade` để lấy candidate questions đã eager-load options, sau đó build typed export snapshots ngoài UI data layer.
- `ui/views/quiz_runner_setup_mixin.py`: bỏ hoàn toàn `get_session()` trong luồng setup runtime quiz; dùng `QuizBuilderFacade` để đếm câu phù hợp, lấy detached questions, và tạo quiz từ typed snapshots.
- `ui/views/quiz_runner_view.py`: khởi tạo `QuizBuilderFacade` dùng chung cho setup mixin.
- `tests/unit/test_ui_layer_boundaries.py`: thêm guardrail test cho `ExamExportPanel` và `QuizRunnerSetupMixin`.

DONE | OpenAI GPT-5.4 Thinking | PHASE_1_UI_SESSION_BOUNDARY_CLOSED | Hoàn tất dọn session direct access ở các file UI nghi ngờ thuộc Phase 1:
- `ui/views/result_history_view.py`: chuyển load detail/delete attempt sang `HistoryFacade`.
- `ui/main_window.py`: chuyển persisted theme load sang `SettingsFacade`.
- `ui/widgets/bank_combo.py`: chuyển bank reload sang `QuestionBankFacade`.
- `tests/unit/test_ui_layer_boundaries.py`: thêm guardrail test cho `ResultHistoryView`, `MainWindow`, `BankCombo`.
- Kết quả xác nhận: cụm test boundary/smoke/history/question-bank liên quan pass.

ADDED | OpenAI GPT-5.4 Thinking | POLICY_AND_TERMINOLOGY_SYNC_WORKFLOW | Bổ sung quy trình đồng bộ policy và thuật ngữ vào `CONTRIBUTING.md` với thứ tự bắt buộc:
- `Docs sweep`
- `Policy sweep`
- `Consistency sweep`
- `Final glossary sweep`
- Áp dụng cho các thay đổi liên quan tới quyền, workflow nghiệp vụ, route truy cập, trạng thái dữ liệu, thuật ngữ UI và service contract.

CHANGED | OpenAI GPT-5.4 Thinking | PHASE_2_RESUME_AUTOSAVE_RECOVERY_STARTED | Bắt đầu Giai đoạn 2 với lát cắt `resume attempt + autosave/recovery`:
- `core/domain/services/quiz_service.py`: thêm contract runtime cho recovery (`AttemptResumeDTO`), lưu `remaining_seconds`, lưu submitter metadata vào `attempts.extra_data`, hỗ trợ load resumable attempt, autosave progress và discard attempt dở.
- `modules/quiz_runner/session_controller.py`: thêm `PreparedAttemptSession`, orchestration cho prepare/resume/delete/autosave progress thay vì chỉ autosave answer rời rạc.
- `modules/quiz_runner/session_state.py` và `ui/views/quiz_runner_state_proxy.py`: mở rộng state với `remaining_seconds`.
- `modules/quiz_runner/timer_controller.py`: expose `remaining_seconds` hiện tại để persistence/resume nhất quán.
- `ui/views/quiz_runner_view.py`: thêm flow hỏi resume hay restart khi phát hiện attempt `IN_PROGRESS`; autosave lưu cả câu trả lời hiện đang mở và thời gian còn lại; resume khôi phục answer/timer/submitter metadata.
- `tests/unit/test_quiz_service.py`, `tests/unit/test_quiz_runner_session_controller.py`, `tests/unit/test_quiz_runner_view_autosave.py`, `tests/unit/test_quiz_runner_view_lifecycle.py`, `tests/unit/test_quiz_runner_state.py`: thêm regression tests cho toàn bộ contract recovery mới.

CHANGED | OpenAI GPT-5.4 Thinking | PHASE_2_FINALIZE_HARDENING_AND_RECOVERY_UX | Tiếp tục Giai đoạn 2 với lớp hardening tiếp theo cho runner runtime:
- `modules/quiz_runner/session_state.py` và `ui/views/quiz_runner_state_proxy.py`: thêm state `resumed_from_autosave` và `finalizing`.
- `ui/views/quiz_runner_layout.py`: thêm badge UI `Khôi phục từ autosave` ở runner header.
- `ui/views/quiz_runner_view.py`: khóa double-submit khi đang finalize, flush autosave cuối trước khi submit, recovery nhánh finalize failure để người dùng có thể thử nộp lại thay vì mất phiên làm bài, và hiển thị badge resume xuyên suốt phiên đã khôi phục.
- `tests/unit/test_quiz_runner_view_lifecycle.py` và `tests/unit/test_quiz_runner_state.py`: thêm regression tests cho recovery badge và nhánh finalize fail-safe.

CHANGED | OpenAI GPT-5.4 Thinking | PHASE_2_EXAM_POLICY_TELEMETRY_IMPORT_BUDGETS | Hoàn tất các bước tiếp theo của Giai đoạn 2 theo thứ tự ưu tiên:
- `modules/quiz_runner/mode_policy.py`: bổ sung policy helpers cho submitter identity, điều kiện resume hợp lệ và nhánh khóa câu trả lời khi `time_up` nhưng finalize EXAM thất bại.
- `ui/views/quiz_runner_view.py`: thêm log context theo event (`resume_accepted`, `resume_discarded`, `resume_invalid`, `finalize_started`, `finalize_failed`, `finalize_retry_ready`, ...); EXAM resume không hợp lệ sẽ bị discard theo policy; nhánh `time_up + finalize fail` chuyển sang trạng thái chỉ cho `Thử nộp lại`.
- `modules/question_bank/importer.py`: thêm row budgets mềm/cứng và hard file-size limit cho import lớn; xử lý CSV/XLSX theo hướng ít giữ dữ liệu trung gian hơn.
- `modules/question_bank/duplicate_detector.py`: thu hẹp DB duplicate lookup theo candidate codes/texts thay vì load toàn bộ bảng câu hỏi.
- `core/domain/services/import_service.py`: thêm telemetry cho preview/commit, commit flush theo batch và bỏ per-row flush để giảm chi phí ORM.
- `tests/unit/test_mode_policy.py`, `tests/unit/test_quiz_runner_view_lifecycle.py`, `tests/unit/test_importer.py`, `tests/integration/test_import_flow.py`, `tests/integration/test_performance_import.py`: bổ sung coverage cho policy mới, log path chính và import resilience cho dữ liệu lớn.

DONE | OpenAI GPT-5.4 Thinking | PHASE_2_BUDGET_TUNING_AND_WARNING_DASHBOARD | Chốt Giai đoạn 2 bằng số đo thực tế và observability tối thiểu:
- Benchmark import thực tế đã được chạy đến 20.000 dòng trên môi trường hiện tại; kết quả cho thấy ngưỡng cũ cảnh báo quá sớm.
- `modules/question_bank/importer.py`: tinh chỉnh budget mặc định thành `soft_row_limit=12_000`, `hard_row_limit=30_000`, `soft_file_size=3 MB`, `hard_file_size=8 MB`; bổ sung soft file-size warning.
- `core/domain/services/telemetry_service.py`: thêm service đọc log file và gom warning summary cho import/runtime.
- `ui/facades/dashboard_facade.py` và `ui/views/dashboard_view.py`: thêm dashboard section `Telemetry cảnh báo gần đây` với 2 stat cards và danh sách event gần nhất.
- `tests/unit/test_telemetry_service.py`: thêm regression tests cho telemetry aggregation từ log file.
- Kết quả xác nhận: cụm test importer/import-flow/performance/smoke/telemetry liên quan pass.

CHANGED | OpenAI GPT-5.4 Thinking | QUESTION_BANK_METADATA_DIALOG_REDESIGN | Thiết kế lại dialog `Thêm/Sửa ngân hàng câu hỏi` theo metadata học phần:
- đổi nhãn `Môn học` thành `Học phần` trong dialog metadata ngân hàng;
- sửa field `Môn học` thành `Học phần`; thay field `Tiêu đề bài thi` bằng combobox `Loại đánh giá` với các giá trị chuẩn `Thường xuyên`, `Định kỳ`, `Tổng kết`;
- bổ sung danh sách động `Chuẩn đầu ra học phần` gồm `Mã CLO` và `Mô tả CLO`, cho phép thêm/bớt row;
- giữ `exam_title` cũ ở persistence để không làm hỏng compatibility của nhánh export, nhưng field này không còn là field active trong dialog mới.

---

END OF ROADMAP DOCUMENT

Last Updated: 2026-06-30
Version: 1.1.1
