# Hướng dẫn định dạng file Import – Quiz Desktop App

> Phiên bản: 1.0.0 | Tài liệu kỹ thuật đầy đủ: `QUIZ_APP_IMPORT_FORMAT.md`

---

## 1. Định dạng được hỗ trợ

| Định dạng | Hỗ trợ |
|---|---|
| `.xlsx` (Excel) | Có – khuyến nghị |
| `.csv` (UTF-8 hoặc UTF-8 BOM) | Có |
| `.xls` (Excel cũ) | Không |
| `.json` | Không (v1.1+) |

---

## 2. Header bắt buộc

File phải có dòng header ở đầu tiên với đúng tên cột:

```
question_code, question_text, question_type, category, difficulty, score,
hint, explanation, option_a, option_b, option_c, option_d, option_e, option_f,
correct_answers, status, tags, case_sensitive, trim_whitespace
```

> Map theo **tên cột**, không phụ thuộc thứ tự. Thừa cột không tên nhận diện sẽ bị bỏ qua (WARNING).

---

## 3. Các loại câu hỏi

### 3.1. Multiple Choice (`multiple_choice`)

- Cần ít nhất 2 option không trống (`option_a`, `option_b`, ...).
- `correct_answers` phải là **một** ký hiệu: `A`, `B`, `C`, `D`, `E` hoặc `F`.

```csv
MC001,Thủ đô Việt Nam là gì?,multiple_choice,Địa lý,easy,1.0,,,Hà Nội,Hồ Chí Minh,Đà Nẵng,Cần Thơ,,,A,active,,false,true
```

### 3.2. Multiple Answer (`multiple_answer`)

- Cần ít nhất 2 option.
- `correct_answers` phải có **từ 2 giá trị trở lên**, phân tách bằng `||`.

```csv
MA001,Ngôn ngữ thông dịch là?,multiple_answer,IT,medium,2.0,,,Python,Java,C,JavaScript,,,A||D,active,,false,true
```

### 3.3. Blank (`blank`)

- `question_text` phải chứa đúng **một** `[[blank]]`.
- Không dùng `option_a`–`option_f`.
- `correct_answers` là một hoặc nhiều đáp án chấp nhận, phân tách bằng `||`.

```csv
BL001,Thủ đô Việt Nam là [[blank]].,blank,Địa lý,easy,1.0,,,,,,,,,Hà Nội||Ha Noi,active,,false,true
```

### 3.4. Short Answer (`short_answer`)

- `question_text` là câu hỏi thông thường (không có `[[blank]]`).
- Không dùng `option_a`–`option_f`.
- `correct_answers` là một hoặc nhiều câu trả lời chấp nhận, phân tách bằng `||`.

```csv
SA001,Viết tắt của CPU.,short_answer,IT,easy,1.0,,,,,,,,,Central Processing Unit||CPU,active,,false,true
```

---

## 4. Giải thích các cột

| Cột | Bắt buộc | Mô tả |
|---|---|---|
| `question_code` | Không | Mã duy nhất; không được trùng trong file |
| `question_text` | **Có** | Nội dung câu hỏi |
| `question_type` | **Có** | `multiple_choice`, `multiple_answer`, `blank`, `short_answer` |
| `category` | Không | Chủ đề, nhóm |
| `difficulty` | Không | `easy`, `medium`, `hard` (mặc định `medium`) |
| `score` | Không | Điểm tối đa (mặc định `1.0`) |
| `hint` | Không | Gợi ý (dùng trong chế độ Luyện tập và Học tập) |
| `explanation` | Không | Giải thích đáp án (dùng trong chế độ Học tập) |
| `option_a`–`option_f` | Tùy loại | Các lựa chọn (MC và MA cần ít nhất 2) |
| `correct_answers` | **Có** | Đáp án đúng theo định dạng từng loại |
| `status` | Không | `active` hoặc `inactive` (mặc định `active`) |
| `tags` | Không | Danh sách tag, phân tách bằng dấu phẩy |
| `case_sensitive` | Không | `true`/`false` (mặc định `false`) – chỉ cho blank và SA |
| `trim_whitespace` | Không | `true`/`false` (mặc định `true`) |

---

## 5. Quy tắc `correct_answers`

| Loại | Ví dụ hợp lệ | Ví dụ không hợp lệ |
|---|---|---|
| `multiple_choice` | `A` | `A\|\|B`, `G` |
| `multiple_answer` | `A\|\|C\|\|D` | `A` (chỉ một), `A\|\|A` (trùng) |
| `blank` | `Paris\|\|paris` | (trống) |
| `short_answer` | `EOQ\|\|Economic Order Quantity` | (trống) |

**Delimiter chính thức:** `||` (hai thanh dọc)

---

## 6. Chính sách import

- **Strict mode**: nếu có ít nhất 1 dòng lỗi `ERROR`, toàn bộ file bị chặn.
- **Dòng hoàn toàn trống**: bỏ qua tự động.
- **Cột thừa**: bỏ qua, có `WARNING`.
- **Trùng `question_code` trong file**: `ERROR`.
- **Trùng `question_code` với DB**: `ERROR`.
- **Trùng nội dung (`question_text` + `question_type`) với DB**: `WARNING` (người dùng quyết định).

---

## 7. Lỗi thường gặp

| Lỗi | Nguyên nhân | Cách sửa |
|---|---|---|
| `ERROR: thiếu cột bắt buộc` | Header sai hoặc thiếu | Kiểm tra tên cột theo mục 2 |
| `ERROR: correct_answers rỗng` | Cột để trống | Điền đáp án theo loại câu hỏi |
| `ERROR: MC chỉ được 1 đáp án` | Dùng `A\|\|B` cho MC | Chỉ điền 1 ký tự như `A` |
| `ERROR: MA phải có ít nhất 2 đáp án` | Chỉ điền 1 đáp án | Điền ít nhất 2 cách nhau bằng `\|\|` |
| `ERROR: blank thiếu [[blank]]` | `question_text` không có placeholder | Thêm `[[blank]]` vào nội dung |
| `WARNING: blank có option_a` | Điền nhầm cột options | Xóa nội dung trong cột option |

---

## 8. Template file mẫu

Tải template mẫu (Excel) tại:  
`assets/templates/import_template.xlsx`

Hoặc dùng CSV header sau làm điểm bắt đầu:

```
question_code,question_text,question_type,category,difficulty,score,hint,explanation,option_a,option_b,option_c,option_d,option_e,option_f,correct_answers,status,tags,case_sensitive,trim_whitespace
```
