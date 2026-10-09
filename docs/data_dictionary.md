# Data dictionary — Hệ thống ngân hàng câu hỏi và thi qua mạng LAN

## Quy ước

- `INTEGER PRIMARY KEY AUTOINCREMENT`: khóa chính tự tăng.
- `NOT NULL`: bắt buộc; `DEFAULT`: giá trị mặc định; `CHECK`: giới hạn giá trị; `UNIQUE`: không cho trùng.
- Các cột thời gian trong schema hiện là `TEXT`.
- Bật `PRAGMA foreign_keys = ON` trên mỗi kết nối SQLite.

## Các bảng và field

### `users`

Tài khoản người dùng.

| Field           | Kiểu      | Khai báo/ràng buộc trên field      | Ý nghĩa                              |
| --------------- | --------- | ---------------------------------- | ------------------------------------ |
| `user_id`       | `INTEGER` | PRIMARY KEY AUTOINCREMENT          | ID tài khoản                         |
| `username`      | `TEXT`    | NOT NULL UNIQUE                    | Tên đăng nhập                        |
| `password_hash` | `TEXT`    | NOT NULL                           | Mật khẩu đã băm                      |
| `full_name`     | `TEXT`    | NOT NULL                           | Họ và tên                            |
| `role`          | `TEXT`    | NOT NULL                           | Vai trò                              |
| `is_active`     | `INTEGER` | NOT NULL DEFAULT 1                 | Trạng thái hoạt động (1 có, 0 không) |
| `created_at`    | `TEXT`    | NOT NULL DEFAULT CURRENT_TIMESTAMP | Thời điểm tạo                        |

**Ràng buộc cấp bảng:**

- `CHECK(role IN ('admin', 'teacher'))`
- `CHECK(is_active IN (0, 1))`

### `subjects`

Danh mục môn học.

| Field          | Kiểu      | Khai báo/ràng buộc trên field | Ý nghĩa                              |
| -------------- | --------- | ----------------------------- | ------------------------------------ |
| `subject_id`   | `INTEGER` | PRIMARY KEY AUTOINCREMENT     | ID môn học                           |
| `subject_name` | `TEXT`    | NOT NULL UNIQUE               | Tên môn học                          |
| `is_active`    | `INTEGER` | NOT NULL DEFAULT 1            | Trạng thái hoạt động (1 có, 0 không) |

**Ràng buộc cấp bảng:**

- `CHECK(is_active IN (0, 1))`

### `grades`

Danh mục khối lớp.

| Field        | Kiểu      | Khai báo/ràng buộc trên field | Ý nghĩa                              |
| ------------ | --------- | ----------------------------- | ------------------------------------ |
| `grade_id`   | `INTEGER` | PRIMARY KEY AUTOINCREMENT     | ID khối lớp                          |
| `grade_name` | `TEXT`    | NOT NULL UNIQUE               | Tên khối lớp                         |
| `is_active`  | `INTEGER` | NOT NULL DEFAULT 1            | Trạng thái hoạt động (1 có, 0 không) |

**Ràng buộc cấp bảng:**

- `CHECK(is_active IN (0, 1))`

### `topics`

Chủ đề theo môn học và khối lớp.

| Field        | Kiểu      | Khai báo/ràng buộc trên field | Ý nghĩa                              |
| ------------ | --------- | ----------------------------- | ------------------------------------ |
| `topic_id`   | `INTEGER` | PRIMARY KEY AUTOINCREMENT     | ID chủ đề                            |
| `subject_id` | `INTEGER` | NOT NULL                      | ID môn học                           |
| `grade_id`   | `INTEGER` | NOT NULL                      | ID khối lớp                          |
| `topic_name` | `TEXT`    | NOT NULL                      | Tên chủ đề                           |
| `is_active`  | `INTEGER` | NOT NULL DEFAULT 1            | Trạng thái hoạt động (1 có, 0 không) |

**Ràng buộc cấp bảng:**

- `CHECK(is_active IN (0, 1))`
- `FOREIGN KEY(subject_id)`
- `FOREIGN KEY(grade_id)`
- `UNIQUE(subject_id, grade_id, topic_name)`

### `lessons`

Bài học thuộc chủ đề.

| Field          | Kiểu      | Khai báo/ràng buộc trên field | Ý nghĩa                              |
| -------------- | --------- | ----------------------------- | ------------------------------------ |
| `lesson_id`    | `INTEGER` | PRIMARY KEY AUTOINCREMENT     | ID bài học                           |
| `topic_id`     | `INTEGER` | NOT NULL                      | ID chủ đề                            |
| `lesson_name`  | `TEXT`    | NOT NULL                      | Tên bài học                          |
| `lesson_order` | `INTEGER` | NOT NULL DEFAULT 1            | Thứ tự bài học                       |
| `is_active`    | `INTEGER` | NOT NULL DEFAULT 1            | Trạng thái hoạt động (1 có, 0 không) |

**Ràng buộc cấp bảng:**

- `CHECK(lesson_order > 0)`
- `CHECK(is_active IN (0, 1))`
- `FOREIGN KEY(topic_id)`
- `UNIQUE(topic_id, lesson_name)`
- `UNIQUE(topic_id, lesson_order)`

### `classes`

Danh mục lớp học.

| Field         | Kiểu      | Khai báo/ràng buộc trên field | Ý nghĩa                              |
| ------------- | --------- | ----------------------------- | ------------------------------------ |
| `class_id`    | `INTEGER` | PRIMARY KEY AUTOINCREMENT     | ID lớp                               |
| `class_name`  | `TEXT`    | NOT NULL                      | Tên lớp                              |
| `grade_id`    | `INTEGER` | NOT NULL                      | ID khối lớp                          |
| `school_year` | `TEXT`    | —                             | Năm học                              |
| `is_active`   | `INTEGER` | NOT NULL DEFAULT 1            | Trạng thái hoạt động (1 có, 0 không) |

**Ràng buộc cấp bảng:**

- `CHECK(is_active IN (0, 1))`
- `FOREIGN KEY(grade_id)`
- `UNIQUE(class_name, school_year)`

### `students`

Hồ sơ học sinh.

| Field          | Kiểu      | Khai báo/ràng buộc trên field | Ý nghĩa                              |
| -------------- | --------- | ----------------------------- | ------------------------------------ |
| `student_id`   | `INTEGER` | PRIMARY KEY AUTOINCREMENT     | ID học sinh                          |
| `student_code` | `TEXT`    | NOT NULL UNIQUE               | Mã học sinh                          |
| `full_name`    | `TEXT`    | NOT NULL                      | Họ và tên                            |
| `class_id`     | `INTEGER` | NOT NULL                      | ID lớp                               |
| `is_active`    | `INTEGER` | NOT NULL DEFAULT 1            | Trạng thái hoạt động (1 có, 0 không) |

**Ràng buộc cấp bảng:**

- `CHECK(is_active IN (0, 1))`
- `FOREIGN KEY(class_id)`

### `questions`

Ngân hàng câu hỏi.

| Field           | Kiểu      | Khai báo/ràng buộc trên field      | Ý nghĩa                              |
| --------------- | --------- | ---------------------------------- | ------------------------------------ |
| `question_id`   | `INTEGER` | PRIMARY KEY AUTOINCREMENT          | ID câu hỏi                           |
| `subject_id`    | `INTEGER` | NOT NULL                           | ID môn học                           |
| `grade_id`      | `INTEGER` | NOT NULL                           | ID khối lớp                          |
| `topic_id`      | `INTEGER` | NOT NULL                           | ID chủ đề                            |
| `lesson_id`     | `INTEGER` | —                                  | ID bài học                           |
| `created_by`    | `INTEGER` | NOT NULL                           | Tài khoản tạo bản ghi                |
| `question_type` | `TEXT`    | NOT NULL                           | Loại câu hỏi                         |
| `difficulty`    | `TEXT`    | NOT NULL                           | Mức độ câu hỏi                       |
| `question_text` | `TEXT`    | NOT NULL                           | Nội dung câu hỏi                     |
| `explanation`   | `TEXT`    | —                                  | Lời giải/giải thích                  |
| `is_active`     | `INTEGER` | NOT NULL DEFAULT 1                 | Trạng thái hoạt động (1 có, 0 không) |
| `created_at`    | `TEXT`    | NOT NULL DEFAULT CURRENT_TIMESTAMP | Thời điểm tạo                        |
| `updated_at`    | `TEXT`    | —                                  | Thời điểm cập nhật gần nhất          |

**Ràng buộc cấp bảng:**

- `CHECK(question_type IN (`
- `CHECK(difficulty IN ('NB', 'TH', 'VD', 'VDC'))`
- `CHECK(is_active IN (0, 1))`
- `FOREIGN KEY(subject_id)`
- `FOREIGN KEY(grade_id)`
- `FOREIGN KEY(topic_id)`
- `FOREIGN KEY(lesson_id)`
- `FOREIGN KEY(created_by)`

### `question_options`

Các phương án của câu hỏi.

| Field         | Kiểu      | Khai báo/ràng buộc trên field | Ý nghĩa                                                             |
| ------------- | --------- | ----------------------------- | ------------------------------------------------------------------- |
| `option_id`   | `INTEGER` | PRIMARY KEY AUTOINCREMENT     | ID phương án                                                        |
| `question_id` | `INTEGER` | NOT NULL                      | ID câu hỏi                                                          |
| `option_key`  | `TEXT`    | NOT NULL                      | Ký hiệu phương án                                                   |
| `option_text` | `TEXT`    | NOT NULL                      | Nội dung phương án                                                  |
| `is_correct`  | `INTEGER` | NOT NULL DEFAULT 0            | Đánh dấu đáp án đúng (1 đúng, 0 sai; nếu nullable có thể chưa chấm) |
| `sort_order`  | `INTEGER` | NOT NULL DEFAULT 1            | Thứ tự hiển thị                                                     |

**Ràng buộc cấp bảng:**

- `CHECK(is_correct IN (0, 1))`
- `CHECK(sort_order > 0)`
- `FOREIGN KEY(question_id)`
- `UNIQUE(question_id, option_key)`
- `UNIQUE(question_id, sort_order)`

### `question_accepted_answers`

Các đáp án chấp nhận cho câu trả lời ngắn.

| Field                | Kiểu      | Khai báo/ràng buộc trên field | Ý nghĩa                           |
| -------------------- | --------- | ----------------------------- | --------------------------------- |
| `accepted_answer_id` | `INTEGER` | PRIMARY KEY AUTOINCREMENT     | ID đáp án được chấp nhận          |
| `question_id`        | `INTEGER` | NOT NULL                      | ID câu hỏi                        |
| `answer_text`        | `TEXT`    | NOT NULL                      | Nội dung đáp án/câu trả lời       |
| `is_case_sensitive`  | `INTEGER` | NOT NULL DEFAULT 0            | Có phân biệt chữ hoa/thường không |

**Ràng buộc cấp bảng:**

- `CHECK(is_case_sensitive IN (0, 1))`
- `FOREIGN KEY(question_id)`
- `UNIQUE(question_id, answer_text)`

### `question_media`

Tệp media đính kèm câu hỏi.

| Field         | Kiểu      | Khai báo/ràng buộc trên field | Ý nghĩa         |
| ------------- | --------- | ----------------------------- | --------------- |
| `media_id`    | `INTEGER` | PRIMARY KEY AUTOINCREMENT     | ID tệp đính kèm |
| `question_id` | `INTEGER` | NOT NULL                      | ID câu hỏi      |
| `media_type`  | `TEXT`    | NOT NULL                      | Loại tệp media  |
| `file_path`   | `TEXT`    | NOT NULL                      | Đường dẫn tệp   |
| `sort_order`  | `INTEGER` | NOT NULL DEFAULT 1            | Thứ tự hiển thị |

**Ràng buộc cấp bảng:**

- `CHECK(media_type IN ('image', 'file', 'audio'))`
- `CHECK(sort_order > 0)`
- `FOREIGN KEY(question_id)`

### `exams`

Thông tin đề thi gốc.

| Field              | Kiểu      | Khai báo/ràng buộc trên field      | Ý nghĩa                     |
| ------------------ | --------- | ---------------------------------- | --------------------------- |
| `exam_id`          | `INTEGER` | PRIMARY KEY AUTOINCREMENT          | ID đề thi                   |
| `title`            | `TEXT`    | NOT NULL                           | Tên đề thi                  |
| `subject_id`       | `INTEGER` | NOT NULL                           | ID môn học                  |
| `grade_id`         | `INTEGER` | NOT NULL                           | ID khối lớp                 |
| `duration_minutes` | `INTEGER` | NOT NULL                           | Thời lượng làm bài (phút)   |
| `created_by`       | `INTEGER` | NOT NULL                           | Tài khoản tạo bản ghi       |
| `status`           | `TEXT`    | NOT NULL DEFAULT 'draft'           | Trạng thái                  |
| `created_at`       | `TEXT`    | NOT NULL DEFAULT CURRENT_TIMESTAMP | Thời điểm tạo               |
| `updated_at`       | `TEXT`    | —                                  | Thời điểm cập nhật gần nhất |

**Ràng buộc cấp bảng:**

- `CHECK(length(trim(title)) > 0)`
- `CHECK(duration_minutes > 0)`
- `CHECK(status IN ('draft', 'ready', 'archived'))`
- `FOREIGN KEY(subject_id)`
- `FOREIGN KEY(grade_id)`
- `FOREIGN KEY(created_by)`

### `exam_matrices`

Ma trận số câu theo chủ đề/bài học, độ khó và loại câu.

| Field            | Kiểu      | Khai báo/ràng buộc trên field | Ý nghĩa         |
| ---------------- | --------- | ----------------------------- | --------------- |
| `matrix_id`      | `INTEGER` | PRIMARY KEY AUTOINCREMENT     | ID dòng ma trận |
| `exam_id`        | `INTEGER` | NOT NULL                      | ID đề thi       |
| `topic_id`       | `INTEGER` | NOT NULL                      | ID chủ đề       |
| `lesson_id`      | `INTEGER` | —                             | ID bài học      |
| `difficulty`     | `TEXT`    | NOT NULL                      | Mức độ câu hỏi  |
| `question_type`  | `TEXT`    | NOT NULL                      | Loại câu hỏi    |
| `question_count` | `INTEGER` | NOT NULL                      | Số câu cần lấy  |

**Ràng buộc cấp bảng:**

- `CHECK(difficulty IN ('NB', 'TH', 'VD', 'VDC'))`
- `CHECK(question_type IN (`
- `CHECK(question_count > 0)`
- `FOREIGN KEY(exam_id)`
- `FOREIGN KEY(topic_id)`
- `FOREIGN KEY(lesson_id)`

### `exam_versions`

Các phiên bản/mã đề.

| Field               | Kiểu      | Khai báo/ràng buộc trên field      | Ý nghĩa                     |
| ------------------- | --------- | ---------------------------------- | --------------------------- |
| `version_id`        | `INTEGER` | PRIMARY KEY AUTOINCREMENT          | ID phiên bản đề             |
| `exam_id`           | `INTEGER` | NOT NULL                           | ID đề thi                   |
| `version_code`      | `TEXT`    | NOT NULL                           | Mã phiên bản đề             |
| `shuffle_questions` | `INTEGER` | NOT NULL DEFAULT 0                 | Có xáo trộn câu hỏi không   |
| `shuffle_options`   | `INTEGER` | NOT NULL DEFAULT 0                 | Có xáo trộn phương án không |
| `created_at`        | `TEXT`    | NOT NULL DEFAULT CURRENT_TIMESTAMP | Thời điểm tạo               |

**Ràng buộc cấp bảng:**

- `CHECK(shuffle_questions IN (0, 1))`
- `CHECK(shuffle_options IN (0, 1))`
- `FOREIGN KEY(exam_id)`
- `UNIQUE(exam_id, version_code)`

### `exam_version_questions`

Câu hỏi và thứ tự trong phiên bản đề.

| Field            | Kiểu      | Khai báo/ràng buộc trên field | Ý nghĩa                      |
| ---------------- | --------- | ----------------------------- | ---------------------------- |
| `version_id`     | `INTEGER` | NOT NULL                      | ID phiên bản đề              |
| `question_id`    | `INTEGER` | NOT NULL                      | ID câu hỏi                   |
| `question_order` | `INTEGER` | NOT NULL                      | Thứ tự câu trong đề          |
| `score`          | `REAL`    | NOT NULL DEFAULT 0            | Điểm của câu trả lời/câu hỏi |
| `option_order`   | `TEXT`    | —                             | Thứ tự phương án đã xáo trộn |

**Ràng buộc cấp bảng:**

- `CHECK(score >= 0)`
- `PRIMARY KEY(version_id, question_order)`
- `UNIQUE(version_id, question_id)`
- `FOREIGN KEY(version_id)`
- `FOREIGN KEY(question_id)`

### `exam_sessions`

Các đợt tổ chức thi.

| Field           | Kiểu      | Khai báo/ràng buộc trên field      | Ý nghĩa               |
| --------------- | --------- | ---------------------------------- | --------------------- |
| `session_id`    | `INTEGER` | PRIMARY KEY AUTOINCREMENT          | ID phiên thi          |
| `exam_id`       | `INTEGER` | NOT NULL                           | ID đề thi             |
| `session_name`  | `TEXT`    | NOT NULL                           | Tên phiên thi         |
| `version_id`    | `INTEGER` | NOT NULL                           | ID phiên bản đề       |
| `access_code`   | `TEXT`    | UNIQUE                             | Mã truy cập phiên thi |
| `password_hash` | `TEXT`    | —                                  | Mật khẩu đã băm       |
| `start_time`    | `TEXT`    | —                                  | Thời điểm bắt đầu     |
| `end_time`      | `TEXT`    | —                                  | Thời điểm kết thúc    |
| `status`        | `TEXT`    | NOT NULL DEFAULT 'scheduled'       | Trạng thái            |
| `created_by`    | `INTEGER` | NOT NULL                           | Tài khoản tạo bản ghi |
| `created_at`    | `TEXT`    | NOT NULL DEFAULT CURRENT_TIMESTAMP | Thời điểm tạo         |

**Ràng buộc cấp bảng:**

- `CHECK(status IN (`
- `FOREIGN KEY(exam_id)`
- `FOREIGN KEY(version_id)`
- `FOREIGN KEY(created_by)`

### `session_students`

Học sinh tham gia phiên thi và thông tin snapshot.

| Field                   | Kiểu      | Khai báo/ràng buộc trên field | Ý nghĩa                          |
| ----------------------- | --------- | ----------------------------- | -------------------------------- |
| `session_student_id`    | `INTEGER` | PRIMARY KEY AUTOINCREMENT     | ID học sinh trong phiên thi      |
| `session_id`            | `INTEGER` | NOT NULL                      | ID phiên thi                     |
| `student_id`            | `INTEGER` | NOT NULL                      | ID học sinh                      |
| `student_code_snapshot` | `TEXT`    | NOT NULL                      | Bản chụp mã học sinh lúc đăng ký |
| `name_snapshot`         | `TEXT`    | NOT NULL                      | Bản chụp họ tên lúc đăng ký      |
| `class_snapshot`        | `TEXT`    | NOT NULL                      | Bản chụp lớp lúc đăng ký         |
| `started_at`            | `TEXT`    | —                             | Thời điểm bắt đầu làm bài        |
| `submitted_at`          | `TEXT`    | —                             | Thời điểm nộp bài                |
| `status`                | `TEXT`    | NOT NULL DEFAULT 'registered' | Trạng thái                       |

**Ràng buộc cấp bảng:**

- `CHECK(status IN (`
- `FOREIGN KEY(session_id)`
- `FOREIGN KEY(student_id)`
- `UNIQUE(session_id, student_id)`

### `answers`

Câu trả lời của học sinh.

| Field                | Kiểu      | Khai báo/ràng buộc trên field | Ý nghĩa                                                             |
| -------------------- | --------- | ----------------------------- | ------------------------------------------------------------------- |
| `answer_id`          | `INTEGER` | PRIMARY KEY AUTOINCREMENT     | ID bản ghi câu trả lời                                              |
| `session_student_id` | `INTEGER` | NOT NULL                      | ID học sinh trong phiên thi                                         |
| `question_id`        | `INTEGER` | NOT NULL                      | ID câu hỏi                                                          |
| `answer_text`        | `TEXT`    | —                             | Nội dung đáp án/câu trả lời                                         |
| `is_correct`         | `INTEGER` | —                             | Đánh dấu đáp án đúng (1 đúng, 0 sai; nếu nullable có thể chưa chấm) |
| `score`              | `REAL`    | NOT NULL DEFAULT 0            | Điểm của câu trả lời/câu hỏi                                        |
| `answered_at`        | `TEXT`    | —                             | Thời điểm ghi nhận câu trả lời lần đầu                              |
| `updated_at`         | `TEXT`    | —                             | Thời điểm cập nhật gần nhất                                         |

**Ràng buộc cấp bảng:**

- `CHECK(is_correct IN (0, 1) OR is_correct IS NULL)`
- `CHECK(score >= 0)`
- `FOREIGN KEY(session_student_id)`
- `FOREIGN KEY(question_id)`
- `UNIQUE(session_student_id, question_id)`

### `results`

Kết quả tổng hợp.

| Field                | Kiểu      | Khai báo/ràng buộc trên field | Ý nghĩa                     |
| -------------------- | --------- | ----------------------------- | --------------------------- |
| `result_id`          | `INTEGER` | PRIMARY KEY AUTOINCREMENT     | ID kết quả                  |
| `session_student_id` | `INTEGER` | NOT NULL                      | ID học sinh trong phiên thi |
| `total_score`        | `REAL`    | NOT NULL DEFAULT 0            | Tổng điểm                   |
| `correct_count`      | `INTEGER` | NOT NULL DEFAULT 0            | Số câu đúng                 |
| `incorrect_count`    | `INTEGER` | NOT NULL DEFAULT 0            | Số câu sai                  |
| `unanswered_count`   | `INTEGER` | NOT NULL DEFAULT 0            | Số câu chưa trả lời         |
| `submitted_at`       | `TEXT`    | —                             | Thời điểm nộp bài           |
| `graded_at`          | `TEXT`    | —                             | Thời điểm chấm điểm         |

**Ràng buộc cấp bảng:**

- `CHECK(total_score >= 0)`
- `CHECK(correct_count >= 0)`
- `CHECK(incorrect_count >= 0)`
- `CHECK(unanswered_count >= 0)`
- `FOREIGN KEY(session_student_id)`
- `UNIQUE(session_student_id)`

### `exam_violations`

Nhật ký vi phạm trong phiên thi.

| Field                | Kiểu      | Khai báo/ràng buộc trên field      | Ý nghĩa                     |
| -------------------- | --------- | ---------------------------------- | --------------------------- |
| `violation_id`       | `INTEGER` | PRIMARY KEY AUTOINCREMENT          | ID sự kiện vi phạm          |
| `session_student_id` | `INTEGER` | NOT NULL                           | ID học sinh trong phiên thi |
| `violation_type`     | `TEXT`    | NOT NULL                           | Loại vi phạm                |
| `description`        | `TEXT`    | —                                  | Mô tả chi tiết              |
| `occurred_at`        | `TEXT`    | NOT NULL DEFAULT CURRENT_TIMESTAMP | Thời điểm xảy ra vi phạm    |
| `severity`           | `TEXT`    | NOT NULL DEFAULT 'warning'         | Mức độ nghiêm trọng         |
| `handled_by`         | `INTEGER` | —                                  | Tài khoản xử lý vi phạm     |
| `handled_at`         | `TEXT`    | —                                  | Thời điểm xử lý vi phạm     |

**Ràng buộc cấp bảng:**

- `CHECK(severity IN ('info', 'warning', 'serious'))`
- `FOREIGN KEY(session_student_id)`
- `FOREIGN KEY(handled_by)`

## Giá trị enum theo CHECK

| Field           | Bảng                         | Giá trị                                                            |
| --------------- | ---------------------------- | ------------------------------------------------------------------ |
| `role`          | `users`                      | `admin`, `teacher`                                                 |
| `question_type` | `questions`, `exam_matrices` | `multiple_choice`, `true_false`, `short_answer`                    |
| `difficulty`    | `questions`, `exam_matrices` | `NB`, `TH`, `VD`, `VDC`                                            |
| `media_type`    | `question_media`             | `image`, `file`, `audio`                                           |
| `status`        | `exams`                      | `draft`, `ready`, `archived`                                       |
| `status`        | `exam_sessions`              | `scheduled`, `ongoing`, `completed`, `cancelled`                   |
| `status`        | `session_students`           | `registered`, `in_progress`, `submitted`, `absent`, `disqualified` |
| `severity`      | `exam_violations`            | `info`, `warning`, `serious`                                       |

## Lưu ý BE/FE

1. FE/BE phải dùng đúng tên field và đúng giá trị enum như schema; có thể hiển thị nhãn tiếng Việt nhưng giá trị gửi API nên theo quy ước thống nhất.
2. `answers.answer_text` là câu học sinh trả lời; đáp án trắc nghiệm đúng nằm ở `question_options.is_correct`, đáp án ngắn được chấp nhận nằm ở `question_accepted_answers`.
3. `answered_at` và `updated_at` không tự cập nhật; backend phải gán khi INSERT/UPDATE.
4. Schema chưa tự đảm bảo các quan hệ nghiệp vụ như `questions.subject_id/grade_id` khớp với `topic_id/lesson_id`, hoặc `exam_sessions.exam_id` khớp với `exam_versions.exam_id`; backend cần xác thực.
5. `option_order` là `TEXT`; thống nhất định dạng lưu/đọc giữa BE và FE, ví dụ JSON.
6. Nên giữ dữ liệu lịch sử bằng `is_active = 0` khi phù hợp thay vì xóa các bản ghi đang được tham chiếu.

## Thống kê: 20 bảng, 132 field được trích xuất từ các khai báo `CREATE TABLE`.
