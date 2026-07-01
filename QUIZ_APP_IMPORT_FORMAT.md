# QUIZ DESKTOP APP IMPORT FORMAT

> QUAN TRỌNG CHO AI AGENT
>
> File này là nguồn chân lý cho toàn bộ chức năng import câu hỏi của dự án Quiz Desktop App.
>
> AI Agent bắt buộc phải đọc và tuân thủ file này trước khi:
> 1. Xây dựng chức năng import CSV hoặc Excel
> 2. Viết parser cho bất kỳ loại câu hỏi nào
> 3. Tạo hoặc sửa question editor liên quan tới dữ liệu import
> 4. Thay đổi schema dữ liệu câu hỏi
> 5. Sửa logic validation, duplicate detection hoặc rollback import
> 6. Viết test cho luồng import
>
> Mọi thay đổi về header, quy tắc mapping, validation, xử lý lỗi, delimiter, encoding hoặc hành vi transaction phải được ghi ngay vào phần CHANGELOG ở cuối file này.
>
> Lệnh khởi đầu bắt buộc cho AI Agent:
>
> Trước khi xây dựng import, hãy đọc file QUIZ_APP_ARCHITECTURE.md, QUIZ_APP_ROADMAP.md và QUIZ_APP_IMPORT_FORMAT.md. Không được tự suy đoán schema import nếu chưa đối chiếu với tài liệu này.

---

## 1. Mục tiêu của tài liệu

Tài liệu này xác định định dạng import chính thức cho phiên bản v1.0 của Quiz Desktop App. Mục đích là:

1. Chuẩn hóa schema import để AI Agent không tự ý phát minh định dạng mới
2. Giảm mơ hồ khi xây dựng parser, validator và preview import
3. Đảm bảo file CSV và Excel được xử lý nhất quán
4. Tạo cơ sở cho unit test, integration test và tài liệu hướng dẫn người dùng

Đây là chuẩn áp dụng cho **import câu hỏi vào ngân hàng câu hỏi**. Tài liệu này không áp dụng cho backup, restore hoặc export lịch sử làm bài.

---

## 2. Phạm vi phiên bản v1.0

### 2.1. Định dạng file được hỗ trợ

| Định dạng | Hỗ trợ v1.0 | Ghi chú |
|---|---|---|
| `.xlsx` | Có | Ưu tiên chính thức |
| `.csv` | Có | UTF-8 hoặc UTF-8 BOM |
| `.xls` | Không | Không hỗ trợ ở v1.0 |
| `.json` | Không | Để dành cho v1.1 hoặc cao hơn |

### 2.2. Loại câu hỏi được hỗ trợ qua import

| Loại câu hỏi | Mã chính thức | Hỗ trợ v1.0 | Ghi chú |
|---|---|---|---|
| Multiple Choice | `multiple_choice` | Có | 1 đáp án đúng |
| Multiple Answer | `multiple_answer` | Có | Nhiều đáp án đúng |
| Blank | `blank` | Có | **Một ô trống duy nhất** trong v1.0 |
| Short Answer | `short_answer` | Có | Câu trả lời ngắn |

### 2.3. Giới hạn có chủ đích của v1.0

1. `blank` trong implementation hiện tại hỗ trợ **một hoặc nhiều chỗ trống**. Nếu có nhiều placeholder, `correct_answers` phải chứa số phần tử tương ứng theo đúng thứ tự và được phân tách bằng `||`.
2. Không hỗ trợ ảnh, audio, video hoặc công thức nhúng trong import v1.0.
3. Không hỗ trợ câu hỏi dạng ma trận, nối cột, kéo thả hoặc tự luận dài.
4. Không hỗ trợ chấm điểm một phần cho `multiple_answer` trong v1.0. Quy tắc chấm là đúng hoàn toàn.
5. Không hỗ trợ import trực tiếp từ nhiều sheet khác nhau trong cùng một workbook ở v1.0.

---

## 3. Quy tắc tổng quát cho file import

### 3.1. Cấu trúc file

1. Dòng đầu tiên là header.
2. Header phải dùng đúng tên cột chính thức như tài liệu này.
3. Mỗi dòng dữ liệu tương ứng với **một câu hỏi**.
4. Không được gộp nhiều câu hỏi trong cùng một dòng.
5. Không dùng merged cells trong file Excel.
6. Sheet mặc định cho `.xlsx` là sheet đầu tiên. Nếu có sheet tên `questions` thì ưu tiên đọc sheet `questions`.

### 3.2. Chính sách transaction

Mặc định v1.0 sử dụng chế độ **strict import**:

1. Hệ thống phải validate toàn bộ file trước khi ghi vào database.
2. Nếu có ít nhất một dòng lỗi mức `ERROR`, toàn bộ lần import phải bị chặn.
3. Không được import một phần trong v1.0 nếu chưa có cấu hình explicit cho partial import.
4. Preview lỗi phải hiển thị đầy đủ trước khi commit.
5. Khi commit thất bại, phải rollback transaction hoàn toàn.

### 3.3. Chính sách xử lý cột thừa và cột thiếu

| Tình huống | Cách xử lý |
|---|---|
| Thiếu cột bắt buộc | Fail toàn bộ file |
| Có cột thừa không nhận diện | Cho phép preview với `WARNING`, bỏ qua khi import |
| Sai tên cột bắt buộc | Xem như thiếu cột bắt buộc |
| Header trùng tên | Fail toàn bộ file |

### 3.4. Chính sách xử lý ô trống

| Trường hợp | Cách xử lý |
|---|---|
| Dòng hoàn toàn trống | Bỏ qua |
| `question_text` trống | ERROR |
| `question_type` trống | ERROR |
| `correct_answers` trống | ERROR |
| Option trống không dùng tới | Cho phép |

---

## 4. Schema import chính thức cho v1.0

### 4.1. Danh sách cột chính thức

| Tên cột | Bắt buộc | Kiểu dữ liệu | Mô tả |
|---|---|---|---|
| `question_code` | Không | string | Mã câu hỏi do người dùng cung cấp; nếu bỏ trống, hệ thống có thể tự sinh nội bộ |
| `question_text` | Có | string | Nội dung câu hỏi |
| `question_type` | Có | enum string | `multiple_choice`, `multiple_answer`, `blank`, `short_answer` |
| `category` | Không | string | Nhóm hoặc chủ đề câu hỏi |
| `difficulty` | Không | enum string | `easy`, `medium`, `hard`; mặc định `medium` nếu trống |
| `score` | Không | number | Điểm của câu hỏi; mặc định `1.0` nếu trống |
| `hint` | Không | string | Gợi ý cho chế độ Luyện tập hoặc Ôn tập |
| `explanation` | Không | string | Giải thích sau khi có kết quả hoặc phản hồi |
| `option_a` | Không | string | Lựa chọn A |
| `option_b` | Không | string | Lựa chọn B |
| `option_c` | Không | string | Lựa chọn C |
| `option_d` | Không | string | Lựa chọn D |
| `option_e` | Không | string | Lựa chọn E |
| `option_f` | Không | string | Lựa chọn F |
| `correct_answers` | Có | string | Giá trị chuẩn hóa theo từng loại câu hỏi |
| `status` | Không | enum string | `active` hoặc `inactive`; mặc định `active` |
| `tags` | Không | string | Danh sách tag, phân tách bằng dấu phẩy |
| `case_sensitive` | Không | boolean | Chỉ áp dụng cho `blank` và `short_answer`; mặc định `false` |
| `trim_whitespace` | Không | boolean | Mặc định `true` |

### 4.2. Thứ tự cột khuyến nghị

AI Agent phải hỗ trợ map theo tên cột, không được phụ thuộc cứng vào vị trí cột. Tuy nhiên, template chính thức nên xuất theo thứ tự sau:

```text
question_code
question_text
question_type
category
difficulty
score
hint
explanation
option_a
option_b
option_c
option_d
option_e
option_f
correct_answers
status
tags
case_sensitive
trim_whitespace
```

### 4.3. Quy tắc enum và boolean

#### Giá trị hợp lệ cho `question_type`

- `multiple_choice`
- `multiple_answer`
- `blank`
- `short_answer`

#### Giá trị hợp lệ cho `difficulty`

- `easy`
- `medium`
- `hard`

#### Giá trị hợp lệ cho `status`

- `active`
- `inactive`

#### Giá trị hợp lệ cho boolean

AI Agent phải chấp nhận các giá trị sau và chuẩn hóa về boolean nội bộ:

| Nhập vào | Giá trị nội bộ |
|---|---|
| `true`, `TRUE`, `1`, `yes`, `y` | `true` |
| `false`, `FALSE`, `0`, `no`, `n` | `false` |
| ô trống ở `case_sensitive` | `false` |
| ô trống ở `trim_whitespace` | `true` |

Các giá trị boolean khác phải bị gắn cờ `ERROR`.

---

## 5. Quy tắc `correct_answers` theo từng loại câu hỏi

### 5.1. Delimiter chính thức

Trong v1.0, khi một trường chứa nhiều giá trị, delimiter chính thức là:

```text
||
```

AI Agent không được tự ý dùng `;`, `,`, `/`, `|` đơn lẻ hoặc xuống dòng làm delimiter chính thức nếu chưa cập nhật tài liệu này.

### 5.2. Multiple Choice

- `correct_answers` phải là **một** ký hiệu option duy nhất: `A`, `B`, `C`, `D`, `E` hoặc `F`
- Option được tham chiếu phải tồn tại và không rỗng

Ví dụ hợp lệ:

```text
A
```

Ví dụ không hợp lệ:

```text
A||C
G
option_a
```

### 5.3. Multiple Answer

- `correct_answers` phải là danh sách từ 2 giá trị trở lên
- Mỗi giá trị phải là một option label hợp lệ: `A`, `B`, `C`, `D`, `E`, `F`
- Không được trùng lặp
- Tất cả option được tham chiếu phải tồn tại

Ví dụ hợp lệ:

```text
A||C||D
```

Ví dụ không hợp lệ:

```text
A
A||A||C
A||G
```

### 5.4. Blank

- `question_text` phải chứa ít nhất **một** placeholder chính thức:

```text
[[blank]]
```

- `correct_answers` là một hoặc nhiều đáp án chấp nhận được, phân tách bằng `||`
- Nếu có nhiều placeholder, số lượng giá trị trong `correct_answers` phải khớp với số placeholder và sẽ được chấm theo vị trí tương ứng
- Nếu `trim_whitespace = true`, hệ thống phải bỏ khoảng trắng đầu và cuối trước khi so khớp
- Nếu `case_sensitive = false`, hệ thống phải so khớp không phân biệt hoa thường

Ví dụ hợp lệ:

```text
question_text: Thủ đô của Việt Nam là [[blank]].
correct_answers: Hà Nội||Ha Noi
```

Ví dụ hợp lệ với nhiều chỗ trống:

```text
question_text: [[blank]] là thủ đô của [[blank]].
correct_answers: Hà Nội||Việt Nam
```

Ví dụ không hợp lệ:

```text
question_text không có [[blank]]
correct_answers trống
```

### 5.5. Short Answer

- `question_text` là câu hỏi thông thường, không dùng placeholder `[[blank]]`
- `correct_answers` là một hoặc nhiều câu trả lời chấp nhận được, phân tách bằng `||`
- Quy tắc `case_sensitive` và `trim_whitespace` áp dụng tương tự `blank`

Ví dụ hợp lệ:

```text
question_text: Viết tên mô hình EOQ.
correct_answers: Economic Order Quantity||EOQ
```

---

## 6. Quy tắc validation theo từng loại câu hỏi

### 6.1. Validation chung

Mọi dòng dữ liệu đều phải qua các kiểm tra sau:

1. `question_text` không được rỗng sau khi trim
2. `question_type` phải thuộc enum hợp lệ
3. `score` phải là số dương lớn hơn 0
4. `question_code` nếu có thì không được trùng trong cùng file
5. `status`, `difficulty`, `case_sensitive`, `trim_whitespace` phải hợp lệ nếu được nhập
6. `correct_answers` không được rỗng

### 6.2. Validation cho `multiple_choice`

1. Phải có ít nhất 2 option không rỗng trong `option_a` đến `option_f`
2. Phải có đúng 1 đáp án trong `correct_answers`
3. Đáp án phải tham chiếu tới option đang tồn tại
4. Không được dùng `[[blank]]` trong `question_text`

### 6.3. Validation cho `multiple_answer`

1. Phải có ít nhất 2 option không rỗng
2. Phải có ít nhất 2 đáp án đúng
3. Mọi đáp án phải tham chiếu tới option đang tồn tại
4. Không được dùng `[[blank]]` trong `question_text`

### 6.4. Validation cho `blank`

1. `question_text` phải chứa ít nhất một `[[blank]]`
2. Không được sử dụng `option_a` đến `option_f`; nếu có dữ liệu trong các cột này thì tạo `WARNING`
3. `correct_answers` phải có ít nhất một giá trị hợp lệ
4. Nếu có nhiều placeholder, số lượng đáp án trong `correct_answers` phải khớp theo từng vị trí

### 6.5. Validation cho `short_answer`

1. `question_text` không được chứa `[[blank]]`
2. Không được sử dụng `option_a` đến `option_f`; nếu có dữ liệu trong các cột này thì tạo `WARNING`
3. `correct_answers` phải có ít nhất một giá trị hợp lệ

---

## 7. Quy tắc chuẩn hóa dữ liệu trước khi lưu

AI Agent phải chuẩn hóa dữ liệu trước khi ghi DB theo các quy tắc sau:

1. Trim khoảng trắng đầu và cuối cho mọi string, trừ khi cần giữ nguyên có chủ đích trong `question_text` và `explanation`.
2. Chuẩn hóa line break về `\n`.
3. Chuẩn hóa enum về lowercase.
4. Chuẩn hóa option labels trong `correct_answers` về uppercase với `multiple_choice` và `multiple_answer`.
5. Bỏ các giá trị rỗng dư thừa trong danh sách `correct_answers`.
6. Với `tags`, tách theo dấu phẩy, trim từng tag, loại bỏ tag rỗng.
7. Không được tự ý sửa chính tả, thêm dấu hoặc suy luận nội dung đáp án.

---

## 8. Quy tắc duplicate detection

### 8.1. Duplicate trong cùng file import

| Tình huống | Mức độ |
|---|---|
| Trùng `question_code` | ERROR |
| Trùng hoàn toàn `question_text` và `question_type` | WARNING |
| Trùng `question_text`, khác `question_type` | WARNING |

### 8.2. Duplicate với dữ liệu đã có trong database

Trong v1.0, duplicate với dữ liệu đang có trong DB được xử lý như sau:

1. Nếu `question_code` đã tồn tại trong DB, phải chặn import dòng đó với `ERROR` trừ khi sau này có explicit update mode.
2. Nếu `question_text` và `question_type` trùng với DB nhưng `question_code` khác, tạo `WARNING` để người dùng quyết định.
3. v1.0 mặc định là **import only**, không phải upsert.

AI Agent không được tự ý thêm chế độ update existing question trong v1.0 nếu chưa cập nhật tài liệu kiến trúc.

---

## 9. Severity model cho preview import

Preview import phải phân loại ít nhất ba mức:

| Mức | Ý nghĩa | Ảnh hưởng |
|---|---|---|
| `INFO` | Thông tin bổ sung | Không chặn import |
| `WARNING` | Vấn đề không nghiêm trọng | Cho phép import nếu không có `ERROR` |
| `ERROR` | Lỗi nghiêm trọng | Chặn toàn bộ import theo strict mode |

Ví dụ:

- `INFO`: score để trống nên dùng mặc định 1.0
- `WARNING`: câu `short_answer` có điền dữ liệu trong `option_a`
- `ERROR`: `multiple_choice` có `correct_answers = A||B`

---

## 10. Mẫu template chính thức

### 10.1. Mẫu CSV header

```csv
question_code,question_text,question_type,category,difficulty,score,hint,explanation,option_a,option_b,option_c,option_d,option_e,option_f,correct_answers,status,tags,case_sensitive,trim_whitespace
```

### 10.2. Mẫu dữ liệu minh họa

```csv
MC001,Thủ đô của Việt Nam là gì?,multiple_choice,Địa lý,easy,1,Gợi ý: đây là trung tâm chính trị của Việt Nam.,Đáp án đúng là Hà Nội.,Hà Nội,Hồ Chí Minh,Đà Nẵng,Cần Thơ,,,A,active,địa lý,country,false,true
MA001,Những ngôn ngữ lập trình nào là kiểu thông dịch?,multiple_answer,Công nghệ,medium,1.5,Gợi ý: nghĩ đến Python và JavaScript.,Python và JavaScript thường được xem là ngôn ngữ thông dịch trong bối cảnh nhập môn.,Python,Java,C++,JavaScript,,,A||D,active,công nghệ,programming,false,true
BL001,Chuỗi cung ứng phản ứng nhanh với nhu cầu thị trường được gọi là [[blank]].,blank,Chuỗi cung ứng,medium,1,Gợi ý: khái niệm đối lập với chậm trễ.,Khái niệm cần điền là velocity.,,,,,,,velocity||Velocity,active,scm,forecasting,false,true
SA001,Viết tên viết tắt của Economic Order Quantity.,short_answer,Logistics,easy,1,Gợi ý: gồm 3 chữ cái.,Economic Order Quantity viết tắt là EOQ.,,,,,,,EOQ,active,inventory,false,true
```

### 10.3. Template Excel

Template Excel chính thức phải dùng cùng bộ cột như CSV. AI Agent không được tự tạo một template Excel khác tên cột nếu chưa cập nhật file này.

---

## 11. Mapping đề xuất từ file import sang database

| Cột import | Đích lưu trữ đề xuất |
|---|---|
| `question_code` | `questions.question_code` |
| `question_text` | `questions.question_text` |
| `question_type` | `questions.question_type` |
| `category` | `questions.category` hoặc bảng category liên kết |
| `difficulty` | `questions.difficulty` |
| `score` | `questions.default_score` |
| `hint` | `questions.hint` |
| `explanation` | `questions.explanation` |
| `status` | `questions.status` |
| `tags` | bảng `question_tags` hoặc field JSON/text tùy thiết kế kiến trúc |
| `case_sensitive` | `questions.case_sensitive` |
| `trim_whitespace` | `questions.trim_whitespace` |
| `option_a` đến `option_f` | bảng `answer_options` |
| `correct_answers` | bảng đáp án chuẩn hóa hoặc answer key riêng |

AI Agent phải bám theo kiến trúc đã định trong `QUIZ_APP_ARCHITECTURE.md`. Tài liệu này chỉ xác định **format import**, không ép buộc một schema DB duy nhất ngoài các trường nghiệp vụ cần tồn tại.

---

## 12. Hành vi UI tối thiểu cho hộp thoại xem trước nhập dữ liệu

### 12.1. Những gì bắt buộc phải có

1. Chọn file nhập dữ liệu
2. Đọc file và hiển thị preview số dòng hợp lệ, cảnh báo, lỗi
3. Danh sách lỗi theo số dòng
4. Tóm tắt theo severity
5. Nút `Nhập câu hỏi` chỉ bật khi không có `ERROR`
6. Nút `Cancel` luôn khả dụng

### 12.2. Những gì không được làm

1. Không nhập ngay khi người dùng vừa chọn file mà không xem trước
2. Không nuốt lỗi thầm lặng
3. Không chỉ hiển thị thông báo lỗi chung chung mà không có line-level detail
4. Không auto sửa đáp án đúng hoặc kiểu câu hỏi nếu không có quy tắc rõ ràng

---

## 13. Bộ test tối thiểu mà AI Agent bắt buộc phải viết

### 13.1. Unit tests cho parser và validator

AI Agent phải có ít nhất các test sau:

1. Nhập dữ liệu thành công cho từng loại câu hỏi: `multiple_choice`, `multiple_answer`, `blank`, `short_answer`
2. Fail khi thiếu cột bắt buộc
3. Fail khi `question_type` không hợp lệ
4. Fail khi `multiple_choice` có nhiều hơn 1 đáp án đúng
5. Fail khi `multiple_answer` chỉ có 1 đáp án đúng
6. Fail khi `blank` không có `[[blank]]`
7. Chấp nhận `blank` có nhiều hơn 1 `[[blank]]` khi số đáp án khớp theo vị trí
8. Fail khi `short_answer` có `[[blank]]`
9. Fail khi `score <= 0`
10. Fail khi `question_code` trùng trong cùng file
11. Cảnh báo khi `short_answer` hoặc `blank` có dữ liệu trong option columns
12. Chấp nhận file CSV UTF-8 BOM
13. Bỏ qua dòng trống hoàn toàn
14. Rollback toàn bộ khi strict mode gặp ít nhất một `ERROR`

### 13.2. Integration tests

1. Nhập dữ liệu file hợp lệ và kiểm tra dữ liệu thực sự đã được lưu DB
2. Nhập dữ liệu file có lỗi và kiểm tra DB không bị ghi một phần
3. Kiểm tra preview summary khớp với số lượng `INFO`, `WARNING`, `ERROR`
4. Kiểm tra mapping `option_a` đến `option_f` vào cấu trúc answer options

---

## 14. Acceptance criteria cho module import

Module import chỉ được coi là hoàn thành khi đạt đủ các điều kiện sau:

1. Nhập dữ liệu được cả `.xlsx` và `.csv`
2. Hỗ trợ đủ 4 loại câu hỏi v1.0
3. Áp dụng đúng strict validation như tài liệu này
4. Có preview lỗi trước khi commit
5. Có rollback transaction hoàn toàn khi import lỗi
6. Có test tự động cho các case chính và case lỗi
7. Không có khác biệt hành vi giữa CSV và Excel với cùng dữ liệu logic
8. Không tự ý phát minh schema thứ hai ngoài schema chính thức của tài liệu này

---

## 15. Prompt chuẩn mà AI Agent phải tự nhắc trước khi làm module import

```text
Đọc QUIZ_APP_ARCHITECTURE.md, QUIZ_APP_ROADMAP.md và QUIZ_APP_IMPORT_FORMAT.md trước khi code.
Không được tự suy đoán schema import.
Không được thay đổi delimiter, header hoặc validation rule nếu chưa cập nhật tài liệu.
Phải viết preview lỗi, strict transaction và test đầy đủ cho importer.
```

---

## 16. Checklist review trước khi merge

| Câu hỏi kiểm tra | Đạt hay chưa |
|---|---|
| Importer có map theo tên cột thay vì vị trí cột không? |  |
| Có đọc đúng CSV UTF-8 BOM không? |  |
| Có preview lỗi theo từng dòng không? |  |
| Có rollback toàn bộ khi có `ERROR` không? |  |
| Có test cho cả 4 loại câu hỏi không? |  |
| Có chặn `multiple_choice` nhiều đáp án đúng không? |  |
| Có chặn `blank` thiếu `[[blank]]` không? |  |
| Có chặn `short_answer` chứa `[[blank]]` không? |  |
| Có giữ đúng delimiter `||` không? |  |
| Có cập nhật changelog nếu thay đổi format không? |  |

---

## 17. CHANGELOG

### 2026-03-24

1. Tạo mới tài liệu `QUIZ_APP_IMPORT_FORMAT.md`
2. Chuẩn hóa schema import chính thức cho v1.0
3. Khóa delimiter chính thức là `||`
4. Khóa placeholder chính thức cho câu `blank` là `[[blank]]`
5. Xác định strict import là hành vi mặc định của v1.0
6. Bổ sung test matrix và acceptance criteria cho module import

### 2026-05-26

1. Bổ sung quy ước UI: trường hiển thị `Chương` là alias của cột import `category`.
2. Không thay đổi schema import, delimiter, hoặc header trong lần cập nhật này.

### 2026-06-30

1. Đồng bộ lại contract import BLANK với implementation hiện tại: hỗ trợ một hoặc nhiều placeholder `[[blank]]`.
2. Chuẩn hóa quy tắc chấm nhiều chỗ trống theo vị trí tương ứng của `correct_answers`.
3. Cập nhật acceptance criteria và test matrix để phản ánh contract mới.
