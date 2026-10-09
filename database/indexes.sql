-- Indexes

-- Phục vụ tìm câu hỏi theo môn, khối, trạng thái,
-- chủ đề, độ khó và loại câu hỏi
CREATE INDEX idx_questions_random
ON questions(
    subject_id,
    grade_id,
    is_active,
    topic_id,
    difficulty,
    question_type
);

-- Phục vụ lấy các ma trận của một đề
CREATE INDEX idx_exam_matrices_exam
ON exam_matrices(exam_id);

-- Phục vụ tìm phiên thi theo đề
CREATE INDEX idx_exam_sessions_exam
ON exam_sessions(exam_id);

-- Phục vụ tìm học sinh theo lớp
CREATE INDEX idx_students_class
ON students(class_id);

-- Phục vụ tìm các phiên thi của một học sinh
CREATE INDEX idx_session_students_student
ON session_students(student_id);

-- Phục vụ tìm câu hỏi thuộc các phiên bản đề
CREATE INDEX idx_exam_version_questions_question
ON exam_version_questions(question_id);

-- Phục vụ truy vấn câu trả lời theo câu hỏi
CREATE INDEX idx_answers_question
ON answers(question_id);

-- Phục vụ truy vấn vi phạm theo học sinh trong phiên thi
CREATE INDEX idx_exam_violations_student
ON exam_violations(session_student_id);
