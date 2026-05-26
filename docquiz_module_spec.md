# QUIZ_MODULE_SPEC

## 1. Document Information

- Document name: `QUIZ_MODULE_SPEC.md`
- Module name: Quiz Builder Module
- Purpose: Đặc tả chức năng tạo bài kiểm tra trắc nghiệm cho ứng dụng
- Intended audience: Developer, AI Coding Agent, Product Owner, QA
- Status: Draft for implementation

---

## 2. Overview

Quiz Builder Module là module cho phép người dùng tạo, chỉnh sửa, xem trước và quản lý bài kiểm tra trắc nghiệm theo mẫu chuẩn. Module phải hỗ trợ nhiều loại câu hỏi, sinh bố cục đề thi sạch, đồng thời tự động tạo phần hướng dẫn, phiếu trả lời, đáp án và quy định chấm điểm dựa trên dữ liệu bài kiểm tra.

Module này được thiết kế để tích hợp vào ứng dụng quản lý học tập, quản lý đề thi hoặc công cụ biên soạn bài kiểm tra.

---

## 3. Goals

### 3.1. Functional goals

Module phải cho phép người dùng:

- tạo bài kiểm tra mới
- chỉnh sửa bài kiểm tra hiện có
- sao chép bài kiểm tra để dùng lại
- thêm, sửa, xóa và sắp xếp câu hỏi
- hỗ trợ nhiều loại câu hỏi trong cùng một bài kiểm tra
- xem trước bài kiểm tra theo thời gian thực
- sinh phiếu trả lời, đáp án và thang điểm
- lưu và tải lại dữ liệu bài kiểm tra

### 3.2. Product goals

Module phải:

- dễ sử dụng
- có bố cục sạch và rõ ràng
- dễ mở rộng thêm loại câu hỏi mới trong tương lai
- tách biệt rõ giữa dữ liệu, logic nghiệp vụ và trình bày giao diện

---

## 4. Out of Scope

Các chức năng sau không thuộc phạm vi bắt buộc của phiên bản đầu tiên, trừ khi được yêu cầu riêng:

- tổ chức thi trực tuyến thời gian thực
- chống gian lận thi cử
- chấm bài tự động toàn bộ với câu trả lời tự do dài
- ngân hàng câu hỏi có phân quyền nâng cao
- sinh nhiều mã đề ngẫu nhiên từ một ngân hàng lớn
- xuất DOCX/PDF nâng cao với template tùy biến phức tạp

---

## 5. Supported Question Types

Module phải hỗ trợ tối thiểu 4 loại câu hỏi sau:

### 5.1. Multiple Choice

Đặc điểm:

- mỗi câu có đúng 1 đáp án đúng
- mặc định 4 lựa chọn A, B, C, D
- có thể mở rộng thêm số lượng lựa chọn nếu cấu hình cho phép

Dữ liệu bắt buộc:

- nội dung câu hỏi
- danh sách phương án
- 1 đáp án đúng
- điểm số

### 5.2. Multiple Answer

Đặc điểm:

- mỗi câu có từ 2 đáp án đúng trở lên
- người làm bài có thể chọn nhiều phương án
- hỗ trợ chấm trọn điểm hoặc chấm từng phần

Dữ liệu bắt buộc:

- nội dung câu hỏi
- danh sách phương án
- tập đáp án đúng
- kiểu chấm điểm
- điểm số tối đa

### 5.3. Short Answer

Đặc điểm:

- người làm bài nhập câu trả lời ngắn
- dùng cho khái niệm, thuật ngữ, tên tác giả, công thức ngắn, định nghĩa ngắn

Dữ liệu bắt buộc:

- nội dung câu hỏi
- đáp án mẫu hoặc danh sách đáp án chấp nhận
- điểm số

### 5.4. Blank

Đặc điểm:

- câu hỏi có chỗ trống cần điền
- đáp án có thể là từ, cụm từ, số hoặc công thức ngắn

Dữ liệu bắt buộc:

- câu dẫn có chỗ trống
- đáp án đúng hoặc danh sách đáp án tương đương
- điểm số

---

## 6. Core Features

### 6.1. Create Quiz

Người dùng có thể:

- tạo bài kiểm tra từ đầu
- tạo từ mẫu có sẵn
- sao chép bài kiểm tra cũ để chỉnh sửa

### 6.2. Edit Quiz Metadata

Người dùng có thể nhập và chỉnh sửa các trường sau:

- school
- department
- subject
- course_code
- exam_title
- exam_type
- duration_minutes
- note
- student_name_label
- student_id_label
- class_label
- date_label

### 6.3. Manage Sections

Module phải cho phép tổ chức đề theo phần, ví dụ:

- Phần A. Multiple Choice
- Phần B. Multiple Answer
- Phần C. Short Answer
- Phần D. Blank

Cho phép:

- thêm phần mới
- đổi tên phần
- đổi loại câu hỏi chính của phần
- đổi thứ tự phần
- xóa phần

### 6.4. Manage Questions

Trong mỗi phần, người dùng có thể:

- thêm câu hỏi
- sửa câu hỏi
- xóa câu hỏi
- nhân bản câu hỏi
- đổi thứ tự câu hỏi bằng kéo thả hoặc nút di chuyển
- đổi loại câu hỏi nếu cần

### 6.5. Preview Quiz

Hệ thống phải hiển thị preview theo thời gian thực, phản ánh đúng dữ liệu hiện tại của bài kiểm tra. Preview phải bao gồm:

- phần đầu đề
- hướng dẫn làm bài
- các phần câu hỏi
- phiếu trả lời nếu bật
- quy định chấm điểm nếu bật
- đáp án và thang điểm nếu bật

### 6.6. Auto-Generate Auxiliary Content

Hệ thống phải tự sinh dựa trên dữ liệu bài kiểm tra:

- hướng dẫn làm bài
- phiếu trả lời
- quy định chấm điểm
- đáp án và bảng điểm

---

## 7. User Stories

### 7.1. Instructor

- Là giảng viên, tôi muốn tạo một bài kiểm tra mới để sử dụng cho lớp học.
- Là giảng viên, tôi muốn thêm nhiều loại câu hỏi trong cùng một đề để phù hợp với mục tiêu đánh giá.
- Là giảng viên, tôi muốn hệ thống tự sinh hướng dẫn làm bài để giảm thời gian soạn thảo.
- Là giảng viên, tôi muốn xem trước toàn bộ đề thi trước khi lưu hoặc xuất.
- Là giảng viên, tôi muốn nhập đáp án và điểm số để hệ thống tạo bảng đáp án chuẩn.

### 7.2. Content Editor

- Là biên tập viên nội dung, tôi muốn nhân bản câu hỏi để soạn đề nhanh hơn.
- Là biên tập viên nội dung, tôi muốn kéo thả đổi vị trí câu hỏi để bố cục đề hợp lý.
- Là biên tập viên nội dung, tôi muốn đổi loại câu hỏi và được nhắc cập nhật dữ liệu hợp lệ.

### 7.3. QA / Reviewer

- Là người kiểm tra chất lượng, tôi muốn xác minh rằng mọi loại câu hỏi đều được render đúng.
- Là người kiểm tra chất lượng, tôi muốn xác minh rằng tổng điểm luôn đúng sau mọi thao tác chỉnh sửa.

---

## 8. Functional Requirements

### FR-01. Create New Quiz

Hệ thống phải cho phép tạo mới một bài kiểm tra.

### FR-02. Save Draft

Hệ thống phải cho phép lưu bài kiểm tra dưới dạng nháp.

### FR-03. Load Existing Quiz

Hệ thống phải cho phép tải lại bài kiểm tra đã lưu.

### FR-04. Edit Quiz Metadata

Hệ thống phải cho phép chỉnh sửa thông tin chung của bài kiểm tra.

### FR-05. Add Section

Hệ thống phải cho phép thêm một phần câu hỏi mới.

### FR-06. Edit Section

Hệ thống phải cho phép đổi tên và cập nhật thông tin phần câu hỏi.

### FR-07. Delete Section

Hệ thống phải cho phép xóa phần câu hỏi.

### FR-08. Reorder Sections

Hệ thống phải cho phép thay đổi thứ tự phần câu hỏi.

### FR-09. Add Question

Hệ thống phải cho phép thêm câu hỏi vào một phần.

### FR-10. Edit Question

Hệ thống phải cho phép chỉnh sửa nội dung và dữ liệu của câu hỏi.

### FR-11. Delete Question

Hệ thống phải cho phép xóa câu hỏi.

### FR-12. Duplicate Question

Hệ thống phải cho phép nhân bản một câu hỏi.

### FR-13. Reorder Questions

Hệ thống phải cho phép thay đổi thứ tự câu hỏi.

### FR-14. Change Question Type

Hệ thống phải cho phép đổi loại câu hỏi và yêu cầu người dùng hoàn thiện lại dữ liệu hợp lệ nếu cần.

### FR-15. Automatic Numbering

Hệ thống phải hỗ trợ:

- đánh số liên tục toàn bài
- hoặc đánh số riêng theo từng phần

### FR-16. Validation

Hệ thống phải kiểm tra dữ liệu hợp lệ trước khi lưu hoặc xuất preview.

### FR-17. Generate Instructions

Hệ thống phải tự sinh phần hướng dẫn làm bài dựa trên loại câu hỏi xuất hiện trong đề.

### FR-18. Generate Answer Sheet

Hệ thống phải tự sinh phiếu trả lời dựa trên số lượng câu hỏi và cấu trúc bài kiểm tra.

### FR-19. Generate Scoring Rules

Hệ thống phải tự sinh phần quy định chấm điểm dựa trên loại câu hỏi và cấu hình chấm.

### FR-20. Generate Answer Key

Hệ thống phải tự sinh bảng đáp án và thang điểm.

### FR-21. Real-Time Preview

Mọi thay đổi dữ liệu phải được phản ánh lên preview mà không cần tạo lại thủ công.

### FR-22. AI Content Assistance

Hệ thống có thể tích hợp lớp AI hỗ trợ soạn nội dung câu hỏi, nhưng không được làm thay đổi dữ liệu lõi nếu người dùng chưa xác nhận.

---

## 9. Non-Functional Requirements

### NFR-01. Usability

Giao diện phải trực quan, ít bước thao tác, dễ học và phù hợp với người dùng biên soạn đề.

### NFR-02. Consistency

Mọi loại câu hỏi phải tuân theo mô hình dữ liệu nhất quán.

### NFR-03. Extensibility

Kiến trúc phải cho phép bổ sung loại câu hỏi mới mà không cần viết lại toàn bộ module.

### NFR-04. Performance

Preview phải cập nhật đủ nhanh để người dùng có cảm giác thao tác tức thời trong các bài kiểm tra quy mô vừa.

### NFR-05. Reliability

Không được mất dữ liệu câu hỏi khi đổi thứ tự, đổi phần hoặc chỉnh sửa liên tiếp.

### NFR-06. Maintainability

Logic nghiệp vụ phải tách biệt khỏi giao diện và logic render.

---

## 10. Suggested UI Layout

### 10.1. Left panel

Cấu trúc bài kiểm tra:

- Thông tin chung
- Hướng dẫn
- Danh sách các phần
- Phiếu trả lời
- Quy định chấm điểm
- Đáp án và thang điểm

### 10.2. Center panel

Biểu mẫu chỉnh sửa chi tiết cho mục đang chọn.

### 10.3. Right panel

Khung preview bài kiểm tra theo thời gian thực.

### 10.4. Main actions

Các thao tác chính nên có:

- Tạo mới
- Lưu nháp
- Xem trước
- Thêm phần
- Thêm câu hỏi
- Nhân bản câu hỏi
- Xóa
- Kéo thả đổi thứ tự
- Bật/tắt phiếu trả lời
- Bật/tắt đáp án
- Bật/tắt quy định chấm điểm

---

## 11. Data Model

### 11.1. Quiz root schema

```json
{
  "exam_meta": {
    "school": "",
    "department": "",
    "subject": "",
    "course_code": "",
    "exam_title": "",
    "exam_type": "",
    "duration_minutes": 0,
    "note": "",
    "student_name_label": "Họ và tên",
    "student_id_label": "Mã số sinh viên/Học sinh",
    "class_label": "Lớp",
    "date_label": "Ngày kiểm tra"
  },
  "settings": {
    "show_instructions": true,
    "show_answer_sheet": true,
    "show_answer_key": true,
    "show_scoring_rules": true,
    "numbering_mode": "global",
    "layout_style": "clean"
  },
  "sections": []
}
```

### 11.2. Section schema

```json
{
  "id": "section_1",
  "section_title": "Phần A. Multiple Choice",
  "question_type": "multiple_choice",
  "questions": []
}
```

### 11.3. Question schema base

```json
{
  "id": "q1",
  "type": "multiple_choice",
  "content": "",
  "points": 1
}
```

### 11.4. Multiple Choice schema

```json
{
  "id": "q1",
  "type": "multiple_choice",
  "content": "Nội dung câu hỏi",
  "options": [
    {"key": "A", "text": "Phương án A"},
    {"key": "B", "text": "Phương án B"},
    {"key": "C", "text": "Phương án C"},
    {"key": "D", "text": "Phương án D"}
  ],
  "correct_answers": ["B"],
  "points": 0.5
}
```

### 11.5. Multiple Answer schema

```json
{
  "id": "q2",
  "type": "multiple_answer",
  "content": "Những phương án nào sau đây là đúng?",
  "options": [
    {"key": "A", "text": "Phương án A"},
    {"key": "B", "text": "Phương án B"},
    {"key": "C", "text": "Phương án C"},
    {"key": "D", "text": "Phương án D"}
  ],
  "correct_answers": ["A", "C"],
  "scoring_mode": "full",
  "points": 1
}
```

### 11.6. Short Answer schema

```json
{
  "id": "q3",
  "type": "short_answer",
  "content": "Hãy nêu khái niệm của ...",
  "accepted_answers": ["Đáp án 1", "Đáp án 2"],
  "points": 1
}
```

### 11.7. Blank schema

```json
{
  "id": "q4",
  "type": "blank",
  "content": "... là người đưa ra học thuyết này.",
  "accepted_answers": ["Tên tác giả"],
  "points": 1
}
```

---

## 12. Validation Rules

### 12.1. Quiz-level validation

- exam_title không được rỗng
- duration_minutes phải là số không âm
- phải có ít nhất 1 phần hoặc ít nhất 1 câu hỏi tùy mode cấu hình

### 12.2. Section-level validation

- section_title không được rỗng
- question_type phải thuộc danh sách hỗ trợ

### 12.3. Question-level validation

#### Multiple Choice

- nội dung không được rỗng
- phải có tối thiểu 2 phương án
- phải có đúng 1 đáp án đúng

#### Multiple Answer

- nội dung không được rỗng
- phải có tối thiểu 2 phương án
- phải có từ 2 đáp án đúng trở lên

#### Short Answer

- nội dung không được rỗng
- phải có ít nhất 1 đáp án chấp nhận

#### Blank

- nội dung không được rỗng
- phải có ít nhất 1 đáp án chấp nhận

#### Common

- points không được âm

---

## 13. Business Logic Rules

### BL-01. Instruction generation

Phần hướng dẫn làm bài phải được sinh dựa trên tập loại câu hỏi thực tế có trong đề.

### BL-02. Scoring rules generation

Phần quy định chấm điểm phải chỉ hiển thị các dạng câu hỏi có xuất hiện trong đề.

### BL-03. Answer sheet generation

Phiếu trả lời phải cập nhật tự động khi thêm, xóa, sắp xếp lại hoặc đổi loại câu hỏi.

### BL-04. Numbering

Nếu `numbering_mode = global` thì đánh số liên tục toàn bài.
Nếu `numbering_mode = per_section` thì đánh số lại từ đầu trong mỗi phần.

### BL-05. Type conversion safety

Khi đổi loại câu hỏi, hệ thống phải đánh dấu dữ liệu cũ là cần rà soát nếu không còn hợp lệ.

### BL-06. Answer integrity

Đáp án phải luôn bám theo câu hỏi hiện tại sau khi nhân bản, đổi chỗ hoặc chỉnh sửa.

### BL-07. Total score

Tổng điểm bài kiểm tra phải được tính tự động từ toàn bộ câu hỏi.

---

## 14. Rendering Requirements

### 14.1. Edit mode

Hiển thị giao diện biên tập, bao gồm form dữ liệu và preview.

### 14.2. Preview mode

Hiển thị bản xem trước sạch, nghiêm túc, phù hợp in ấn hoặc sao chép sang tài liệu khác.

Preview phải hỗ trợ hiển thị:

- phần đầu đề
- hướng dẫn làm bài
- phần A/B/C/D
- phiếu trả lời
- quy định chấm điểm
- đáp án và thang điểm

### 14.3. Clean layout rules

- khoảng cách giữa các phần phải đồng đều
- số câu không bị lặp hoặc nhảy sai
- không hiển thị dữ liệu rỗng không cần thiết
- tiêu đề phần phải rõ ràng
- nội dung câu hỏi phải dễ đọc

---

## 15. AI Assistance Requirements

### 15.1. Allowed AI assistance

AI Agent có thể hỗ trợ:

- tạo câu hỏi mẫu theo môn học
- viết lại câu hỏi cho rõ hơn
- sinh phương án nhiễu
- kiểm tra lỗi chính tả
- chuẩn hóa văn phong giữa các câu
- gợi ý đáp án
- gợi ý điểm số

### 15.2. Restricted AI behavior

AI không được:

- tự ý xóa dữ liệu khi người dùng chưa xác nhận
- tự ý thay đổi cấu trúc schema
- tự ý ghi đè đáp án hiện có mà không báo cho người dùng
- sinh câu hỏi ngoài phạm vi môn học nếu không được yêu cầu

---

## 16. Acceptance Criteria

### AC-01

Người dùng tạo được bài kiểm tra mới với tối thiểu 10 câu Multiple Choice.

### AC-02

Người dùng tạo được bài kiểm tra hỗn hợp gồm 4 loại câu hỏi.

### AC-03

Hệ thống tự sinh hướng dẫn làm bài phù hợp với loại câu hỏi đang có.

### AC-04

Hệ thống tự sinh phiếu trả lời đúng với số lượng và thứ tự câu hỏi.

### AC-05

Hệ thống tự sinh đáp án và thang điểm đúng dữ liệu hiện tại.

### AC-06

Khi xóa một câu ở giữa, hệ thống đánh số lại chính xác.

### AC-07

Khi đổi loại câu hỏi, hệ thống yêu cầu dữ liệu mới hợp lệ.

### AC-08

Preview hiển thị ổn định, bố cục sạch, không lỗi render cơ bản.

### AC-09

Tổng điểm luôn cập nhật đúng sau mọi thao tác chỉnh sửa.

---

## 17. Test Scenarios

### TS-01. Single-type quiz

Tạo đề chỉ gồm Multiple Choice, 10 câu, mỗi câu 0.5 điểm.
Kỳ vọng:

- sinh đúng hướng dẫn
- sinh đúng phiếu trả lời
- tổng điểm = 5.0

### TS-02. Mixed-type quiz

Tạo đề gồm cả 4 loại câu hỏi.
Kỳ vọng:

- hiển thị đủ các phần hướng dẫn
- hiển thị đúng quy định chấm điểm
- render đúng từng loại câu

### TS-03. Delete middle question

Xóa câu ở giữa bài.
Kỳ vọng:

- số câu cập nhật đúng
- phiếu trả lời cập nhật đúng
- đáp án không lệch câu

### TS-04. Change question type

Đổi từ Multiple Choice sang Multiple Answer.
Kỳ vọng:

- hệ thống báo yêu cầu cập nhật đáp án hợp lệ
- không giữ trạng thái 1 đáp án đúng theo logic cũ nếu không còn hợp lệ

### TS-05. Reorder question

Đổi thứ tự câu bằng kéo thả.
Kỳ vọng:

- preview cập nhật đúng
- đáp án đi theo câu đúng

---

## 18. Implementation Phases

### Phase 1. Data schema

- định nghĩa schema quiz, section, question
- định nghĩa validation rules

### Phase 2. Metadata editor

- xây dựng form thông tin chung
- xây dựng thiết lập bài kiểm tra

### Phase 3. Section and question management

- thêm sửa xóa phần
- thêm sửa xóa câu hỏi
- kéo thả đổi thứ tự

### Phase 4. Type-specific editors

- xây dựng form động cho từng loại câu hỏi

### Phase 5. Preview engine

- xây dựng renderer preview sạch
- hỗ trợ đánh số và bố cục

### Phase 6. Auto-generation logic

- hướng dẫn làm bài
- phiếu trả lời
- quy định chấm điểm
- đáp án và thang điểm

### Phase 7. AI assistance layer

- sinh câu hỏi mẫu
- kiểm lỗi chính tả
- gợi ý phương án

### Phase 8. QA and integration

- test các kịch bản chính
- test mất dữ liệu
- test tính đúng của numbering và score

---

## 19. Technical Guidelines

- không hard-code nội dung mẫu vào logic lõi
- tách component editor theo loại câu hỏi
- dùng một lớp chuyển đổi dữ liệu sang preview thay vì render trực tiếp từ form rời rạc
- giữ dữ liệu nguồn ở một state thống nhất
- tách validation, calculation và rendering thành các lớp riêng

---

## 20. Deliverables

Phiên bản hoàn chỉnh của module phải bao gồm:

- dữ liệu schema chuẩn
- UI biên tập
- UI preview
- validation logic
- auto-generation logic
- khả năng lưu/tải dữ liệu
- test cases cơ bản
- tài liệu mô tả API nội bộ nếu có

---

## 21. Definition of Done

Module được xem là hoàn thành khi:

- hỗ trợ đầy đủ 4 loại câu hỏi bắt buộc
- người dùng có thể tạo, sửa, lưu, tải và xem trước bài kiểm tra
- hệ thống tự sinh hướng dẫn, phiếu trả lời, đáp án và thang điểm
- tổng điểm và đánh số câu luôn chính xác
- dữ liệu ổn định khi đổi loại câu, đổi thứ tự, xóa hoặc nhân bản câu hỏi
- giao diện đủ sạch để dùng thực tế trong quy trình soạn đề

---

## 22. Future Extensions

Các hướng mở rộng sau nên được tính đến trong thiết kế:

- true/false
- matching
- essay
- import từ Excel hoặc CSV
- export DOCX/PDF
- tạo nhiều mã đề
- ngân hàng câu hỏi dùng chung
- random hóa thứ tự câu và phương án
- tích hợp phân quyền người dùng
