-- Chuyển từ schema.sql (SQLite) + indexes.sql + 2 cột khóa đăng nhập. Cần MySQL 8.0.16+ (hoặc MariaDB 10.2+) vì có CHECK.
-- Chạy: mysql -u root -p < schema_mysql.sql
CREATE DATABASE IF NOT EXISTS thi_offline CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE thi_offline;
SET NAMES utf8mb4;

CREATE USER 'thi'@'localhost' IDENTIFIED BY 'matkhau_manh';
       GRANT ALL ON thi_offline.* TO 'thi'@'localhost';

CREATE TABLE users (
    user_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    role VARCHAR(10) NOT NULL CHECK (role IN ('admin', 'teacher')),
    is_active TINYINT NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    failed_login_count INT NOT NULL DEFAULT 0,
    locked_at VARCHAR(19) NULL
) ENGINE=InnoDB;

CREATE TABLE subjects (
    subject_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    subject_name VARCHAR(100) NOT NULL UNIQUE,
    is_active TINYINT NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
) ENGINE=InnoDB;

CREATE TABLE grades (
    grade_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    grade_name VARCHAR(100) NOT NULL UNIQUE,
    is_active TINYINT NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
) ENGINE=InnoDB;

CREATE TABLE topics (
    topic_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    subject_id INT NOT NULL,
    grade_id INT NOT NULL,
    topic_name VARCHAR(100) NOT NULL,
    is_active TINYINT NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    FOREIGN KEY (subject_id) REFERENCES subjects(subject_id) ON DELETE RESTRICT,
    FOREIGN KEY (grade_id) REFERENCES grades(grade_id) ON DELETE RESTRICT,
    UNIQUE (subject_id, grade_id, topic_name)
) ENGINE=InnoDB;

CREATE TABLE lessons (
    lesson_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    topic_id INT NOT NULL,
    lesson_name VARCHAR(100) NOT NULL,
    lesson_order INT NOT NULL DEFAULT 1 CHECK (lesson_order > 0),
    is_active TINYINT NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    FOREIGN KEY (topic_id) REFERENCES topics(topic_id) ON DELETE RESTRICT,
    UNIQUE (topic_id, lesson_name),
    UNIQUE (topic_id, lesson_order)
) ENGINE=InnoDB;

CREATE TABLE classes (
    class_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    class_name VARCHAR(50) NOT NULL,
    grade_id INT NOT NULL,
    school_year VARCHAR(20) NULL,
    is_active TINYINT NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    FOREIGN KEY (grade_id) REFERENCES grades(grade_id) ON DELETE RESTRICT,
    UNIQUE (class_name, school_year)
) ENGINE=InnoDB;

CREATE TABLE students (
    student_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    student_code VARCHAR(50) NOT NULL UNIQUE,
    full_name VARCHAR(100) NOT NULL,
    class_id INT NOT NULL,
    is_active TINYINT NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    FOREIGN KEY (class_id) REFERENCES classes(class_id) ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE questions (
    question_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    subject_id INT NOT NULL,
    grade_id INT NOT NULL,
    topic_id INT NOT NULL,
    lesson_id INT NULL,
    created_by INT NOT NULL,
    question_type VARCHAR(20) NOT NULL CHECK (question_type IN ('multiple_choice', 'true_false', 'short_answer')),
    difficulty VARCHAR(5) NOT NULL CHECK (difficulty IN ('NB', 'TH', 'VD', 'VDC')),
    question_text TEXT NOT NULL,
    explanation TEXT NULL,
    is_active TINYINT NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NULL,
    FOREIGN KEY (subject_id) REFERENCES subjects(subject_id) ON DELETE RESTRICT,
    FOREIGN KEY (grade_id) REFERENCES grades(grade_id) ON DELETE RESTRICT,
    FOREIGN KEY (topic_id) REFERENCES topics(topic_id) ON DELETE RESTRICT,
    FOREIGN KEY (lesson_id) REFERENCES lessons(lesson_id) ON DELETE RESTRICT,
    FOREIGN KEY (created_by) REFERENCES users(user_id) ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE question_options (
    option_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    question_id INT NOT NULL,
    option_key VARCHAR(10) NOT NULL,
    option_text TEXT NOT NULL,
    is_correct TINYINT NOT NULL DEFAULT 0 CHECK (is_correct IN (0, 1)),
    sort_order INT NOT NULL DEFAULT 1 CHECK (sort_order > 0),
    FOREIGN KEY (question_id) REFERENCES questions(question_id) ON DELETE CASCADE,
    UNIQUE (question_id, option_key),
    UNIQUE (question_id, sort_order)
) ENGINE=InnoDB;

-- utf8mb4_bin: phân biệt hoa/thường và dấu, nếu không "Hà Nội" và "Ha Noi" bị coi là trùng nhau
CREATE TABLE question_accepted_answers (
    accepted_answer_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    question_id INT NOT NULL,
    answer_text VARCHAR(255) COLLATE utf8mb4_bin NOT NULL,
    is_case_sensitive TINYINT NOT NULL DEFAULT 0 CHECK (is_case_sensitive IN (0, 1)),
    FOREIGN KEY (question_id) REFERENCES questions(question_id) ON DELETE CASCADE,
    UNIQUE (question_id, answer_text)
) ENGINE=InnoDB;

CREATE TABLE question_media (
    media_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    question_id INT NOT NULL,
    media_type VARCHAR(10) NOT NULL CHECK (media_type IN ('image', 'file', 'audio')),
    file_path VARCHAR(255) NOT NULL,
    sort_order INT NOT NULL DEFAULT 1 CHECK (sort_order > 0),
    FOREIGN KEY (question_id) REFERENCES questions(question_id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE exams (
    exam_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL CHECK (CHAR_LENGTH(TRIM(title)) > 0),
    subject_id INT NOT NULL,
    grade_id INT NOT NULL,
    duration_minutes INT NOT NULL CHECK (duration_minutes > 0),
    created_by INT NOT NULL,
    status VARCHAR(10) NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'ready', 'archived')),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NULL,
    FOREIGN KEY (subject_id) REFERENCES subjects(subject_id) ON DELETE RESTRICT,
    FOREIGN KEY (grade_id) REFERENCES grades(grade_id) ON DELETE RESTRICT,
    FOREIGN KEY (created_by) REFERENCES users(user_id) ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE exam_matrices (
    matrix_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    exam_id INT NOT NULL,
    topic_id INT NOT NULL,
    lesson_id INT NULL,
    difficulty VARCHAR(5) NOT NULL CHECK (difficulty IN ('NB', 'TH', 'VD', 'VDC')),
    question_type VARCHAR(20) NOT NULL CHECK (question_type IN ('multiple_choice', 'true_false', 'short_answer')),
    question_count INT NOT NULL CHECK (question_count > 0),
    FOREIGN KEY (exam_id) REFERENCES exams(exam_id) ON DELETE CASCADE,
    FOREIGN KEY (topic_id) REFERENCES topics(topic_id) ON DELETE RESTRICT,
    FOREIGN KEY (lesson_id) REFERENCES lessons(lesson_id) ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE exam_versions (
    version_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    exam_id INT NOT NULL,
    version_code VARCHAR(30) NOT NULL,
    shuffle_questions TINYINT NOT NULL DEFAULT 0 CHECK (shuffle_questions IN (0, 1)),
    shuffle_options TINYINT NOT NULL DEFAULT 0 CHECK (shuffle_options IN (0, 1)),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (exam_id) REFERENCES exams(exam_id) ON DELETE CASCADE,
    UNIQUE (exam_id, version_code)
) ENGINE=InnoDB;

CREATE TABLE exam_version_questions (
    version_id INT NOT NULL,
    question_id INT NOT NULL,
    question_order INT NOT NULL,
    score DOUBLE NOT NULL DEFAULT 0 CHECK (score >= 0),
    option_order TEXT NULL,
    PRIMARY KEY (version_id, question_order),
    UNIQUE (version_id, question_id),
    FOREIGN KEY (version_id) REFERENCES exam_versions(version_id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES questions(question_id) ON DELETE RESTRICT
) ENGINE=InnoDB;

-- start_time/end_time/started_at/submitted_at giữ VARCHAR(19) (chuỗi UTC 'YYYY-MM-DD HH:MM:SS') để code Python cũ vẫn strptime được
CREATE TABLE exam_sessions (
    session_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    exam_id INT NOT NULL,
    session_name VARCHAR(255) NOT NULL,
    version_id INT NOT NULL,
    access_code VARCHAR(20) NULL UNIQUE,
    password_hash VARCHAR(255) NULL,
    start_time VARCHAR(19) NULL,
    end_time VARCHAR(19) NULL,
    status VARCHAR(10) NOT NULL DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'ongoing', 'completed', 'cancelled')),
    created_by INT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (exam_id) REFERENCES exams(exam_id) ON DELETE RESTRICT,
    FOREIGN KEY (version_id) REFERENCES exam_versions(version_id) ON DELETE RESTRICT,
    FOREIGN KEY (created_by) REFERENCES users(user_id) ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE session_students (
    session_student_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    session_id INT NOT NULL,
    student_id INT NOT NULL,
    student_code_snapshot VARCHAR(50) NOT NULL,
    name_snapshot VARCHAR(100) NOT NULL,
    class_snapshot VARCHAR(50) NOT NULL,
    started_at VARCHAR(19) NULL,
    submitted_at VARCHAR(19) NULL,
    status VARCHAR(15) NOT NULL DEFAULT 'registered' CHECK (status IN ('registered', 'in_progress', 'submitted', 'absent', 'disqualified')),
    FOREIGN KEY (session_id) REFERENCES exam_sessions(session_id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE RESTRICT,
    UNIQUE (session_id, student_id)
) ENGINE=InnoDB;

CREATE TABLE answers (
    answer_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    session_student_id INT NOT NULL,
    question_id INT NOT NULL,
    answer_text TEXT NULL,
    is_correct TINYINT NULL CHECK (is_correct IN (0, 1) OR is_correct IS NULL),
    score DOUBLE NOT NULL DEFAULT 0 CHECK (score >= 0),
    answered_at DATETIME NULL,
    updated_at DATETIME NULL,
    FOREIGN KEY (session_student_id) REFERENCES session_students(session_student_id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES questions(question_id) ON DELETE RESTRICT,
    UNIQUE (session_student_id, question_id)
) ENGINE=InnoDB;

CREATE TABLE results (
    result_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    session_student_id INT NOT NULL,
    total_score DOUBLE NOT NULL DEFAULT 0 CHECK (total_score >= 0),
    correct_count INT NOT NULL DEFAULT 0 CHECK (correct_count >= 0),
    incorrect_count INT NOT NULL DEFAULT 0 CHECK (incorrect_count >= 0),
    unanswered_count INT NOT NULL DEFAULT 0 CHECK (unanswered_count >= 0),
    submitted_at VARCHAR(19) NULL,
    graded_at DATETIME NULL,
    FOREIGN KEY (session_student_id) REFERENCES session_students(session_student_id) ON DELETE CASCADE,
    UNIQUE (session_student_id)
) ENGINE=InnoDB;

CREATE TABLE exam_violations (
    violation_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    session_student_id INT NOT NULL,
    violation_type VARCHAR(50) NOT NULL,
    description TEXT NULL,
    occurred_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    severity VARCHAR(10) NOT NULL DEFAULT 'warning' CHECK (severity IN ('info', 'warning', 'serious')),
    handled_by INT NULL,
    handled_at DATETIME NULL,
    FOREIGN KEY (session_student_id) REFERENCES session_students(session_student_id) ON DELETE CASCADE,
    FOREIGN KEY (handled_by) REFERENCES users(user_id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE INDEX idx_questions_random ON questions(subject_id, grade_id, is_active, topic_id, difficulty, question_type);
CREATE INDEX idx_exam_matrices_exam ON exam_matrices(exam_id);
CREATE INDEX idx_exam_sessions_exam ON exam_sessions(exam_id);
CREATE INDEX idx_students_class ON students(class_id);
CREATE INDEX idx_session_students_student ON session_students(student_id);
CREATE INDEX idx_exam_version_questions_question ON exam_version_questions(question_id);
CREATE INDEX idx_answers_question ON answers(question_id);
CREATE INDEX idx_exam_violations_student ON exam_violations(session_student_id);
