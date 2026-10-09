PRAGMA foreign_keys = ON;

-- 1. USERS
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL
        CHECK(role IN ('admin', 'teacher')),
    is_active INTEGER NOT NULL DEFAULT 1
        CHECK(is_active IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 2. SUBJECTS
CREATE TABLE subjects (
    subject_id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_name TEXT NOT NULL UNIQUE,
    is_active INTEGER NOT NULL DEFAULT 1
        CHECK(is_active IN (0, 1))
);

-- 3. GRADES
CREATE TABLE grades (
    grade_id INTEGER PRIMARY KEY AUTOINCREMENT,
    grade_name TEXT NOT NULL UNIQUE,
    is_active INTEGER NOT NULL DEFAULT 1
        CHECK(is_active IN (0, 1))
);

-- 4. TOPICS
CREATE TABLE topics (
    topic_id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id INTEGER NOT NULL,
    grade_id INTEGER NOT NULL,
    topic_name TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1
        CHECK(is_active IN (0, 1)),

    FOREIGN KEY(subject_id)
        REFERENCES subjects(subject_id)
        ON DELETE RESTRICT,

    FOREIGN KEY(grade_id)
        REFERENCES grades(grade_id)
        ON DELETE RESTRICT,

    UNIQUE(subject_id, grade_id, topic_name)
);

-- 5. LESSONS
CREATE TABLE lessons (
    lesson_id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER NOT NULL,
    lesson_name TEXT NOT NULL,
    lesson_order INTEGER NOT NULL DEFAULT 1
        CHECK(lesson_order > 0),
    is_active INTEGER NOT NULL DEFAULT 1
        CHECK(is_active IN (0, 1)),

    FOREIGN KEY(topic_id)
        REFERENCES topics(topic_id)
        ON DELETE RESTRICT,

    UNIQUE(topic_id, lesson_name),
    UNIQUE(topic_id, lesson_order)
);

-- 6. CLASSES
CREATE TABLE classes (
    class_id INTEGER PRIMARY KEY AUTOINCREMENT,
    class_name TEXT NOT NULL,
    grade_id INTEGER NOT NULL,
    school_year TEXT,
    is_active INTEGER NOT NULL DEFAULT 1
        CHECK(is_active IN (0, 1)),

    FOREIGN KEY(grade_id)
        REFERENCES grades(grade_id)
        ON DELETE RESTRICT,

    UNIQUE(class_name, school_year)
);

-- 7. STUDENTS
CREATE TABLE students (
    student_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_code TEXT NOT NULL UNIQUE,
    full_name TEXT NOT NULL,
    class_id INTEGER NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1
        CHECK(is_active IN (0, 1)),

    FOREIGN KEY(class_id)
        REFERENCES classes(class_id)
        ON DELETE RESTRICT
);

-- 8. QUESTIONS
CREATE TABLE questions (
    question_id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id INTEGER NOT NULL,
    grade_id INTEGER NOT NULL,
    topic_id INTEGER NOT NULL,
    lesson_id INTEGER,
    created_by INTEGER NOT NULL,

    question_type TEXT NOT NULL
        CHECK(question_type IN (
            'multiple_choice',
            'true_false',
            'short_answer'
        )),

    difficulty TEXT NOT NULL
        CHECK(difficulty IN ('NB', 'TH', 'VD', 'VDC')),

    question_text TEXT NOT NULL,
    explanation TEXT,

    is_active INTEGER NOT NULL DEFAULT 1
        CHECK(is_active IN (0, 1)),

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT,

    FOREIGN KEY(subject_id)
        REFERENCES subjects(subject_id)
        ON DELETE RESTRICT,

    FOREIGN KEY(grade_id)
        REFERENCES grades(grade_id)
        ON DELETE RESTRICT,

    FOREIGN KEY(topic_id)
        REFERENCES topics(topic_id)
        ON DELETE RESTRICT,

    FOREIGN KEY(lesson_id)
        REFERENCES lessons(lesson_id)
        ON DELETE RESTRICT,

    FOREIGN KEY(created_by)
        REFERENCES users(user_id)
        ON DELETE RESTRICT
);

-- 9. QUESTION_OPTIONS
CREATE TABLE question_options (
    option_id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id INTEGER NOT NULL,
    option_key TEXT NOT NULL,
    option_text TEXT NOT NULL,

    is_correct INTEGER NOT NULL DEFAULT 0
        CHECK(is_correct IN (0, 1)),

    sort_order INTEGER NOT NULL DEFAULT 1
        CHECK(sort_order > 0),

    FOREIGN KEY(question_id)
        REFERENCES questions(question_id)
        ON DELETE CASCADE,

    UNIQUE(question_id, option_key),
    UNIQUE(question_id, sort_order)
);

-- 10. QUESTION_ACCEPTED_ANSWERS
CREATE TABLE question_accepted_answers (
    accepted_answer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id INTEGER NOT NULL,
    answer_text TEXT NOT NULL,
    is_case_sensitive INTEGER NOT NULL DEFAULT 0
        CHECK(is_case_sensitive IN (0, 1)),

    FOREIGN KEY(question_id)
        REFERENCES questions(question_id)
        ON DELETE CASCADE,

    UNIQUE(question_id, answer_text)
);

-- 11. QUESTION_MEDIA
CREATE TABLE question_media (
    media_id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id INTEGER NOT NULL,

    media_type TEXT NOT NULL
        CHECK(media_type IN ('image', 'file', 'audio')),

    file_path TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 1
        CHECK(sort_order > 0),

    FOREIGN KEY(question_id)
        REFERENCES questions(question_id)
        ON DELETE CASCADE
);

-- 12. EXAMS
CREATE TABLE exams (
    exam_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL
        CHECK(length(trim(title)) > 0),

    subject_id INTEGER NOT NULL,
    grade_id INTEGER NOT NULL,
    duration_minutes INTEGER NOT NULL
        CHECK(duration_minutes > 0),

    created_by INTEGER NOT NULL,

    status TEXT NOT NULL DEFAULT 'draft'
        CHECK(status IN ('draft', 'ready', 'archived')),

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT,

    FOREIGN KEY(subject_id)
        REFERENCES subjects(subject_id)
        ON DELETE RESTRICT,

    FOREIGN KEY(grade_id)
        REFERENCES grades(grade_id)
        ON DELETE RESTRICT,

    FOREIGN KEY(created_by)
        REFERENCES users(user_id)
        ON DELETE RESTRICT
);

-- 13. EXAM_MATRICES
CREATE TABLE exam_matrices (
    matrix_id INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_id INTEGER NOT NULL,
    topic_id INTEGER NOT NULL,
    lesson_id INTEGER,

    difficulty TEXT NOT NULL
        CHECK(difficulty IN ('NB', 'TH', 'VD', 'VDC')),

    question_type TEXT NOT NULL
        CHECK(question_type IN (
            'multiple_choice',
            'true_false',
            'short_answer'
        )),

    question_count INTEGER NOT NULL
        CHECK(question_count > 0),

    FOREIGN KEY(exam_id)
        REFERENCES exams(exam_id)
        ON DELETE CASCADE,

    FOREIGN KEY(topic_id)
        REFERENCES topics(topic_id)
        ON DELETE RESTRICT,

    FOREIGN KEY(lesson_id)
        REFERENCES lessons(lesson_id)
        ON DELETE RESTRICT
);

-- 14. EXAM_VERSIONS
CREATE TABLE exam_versions (
    version_id INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_id INTEGER NOT NULL,
    version_code TEXT NOT NULL,

    shuffle_questions INTEGER NOT NULL DEFAULT 0
        CHECK(shuffle_questions IN (0, 1)),

    shuffle_options INTEGER NOT NULL DEFAULT 0
        CHECK(shuffle_options IN (0, 1)),

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY(exam_id)
        REFERENCES exams(exam_id)
        ON DELETE CASCADE,

    UNIQUE(exam_id, version_code)
);

-- 15. EXAM_VERSION_QUESTIONS
CREATE TABLE exam_version_questions (
    version_id INTEGER NOT NULL,
    question_id INTEGER NOT NULL,
    question_order INTEGER NOT NULL,
    score REAL NOT NULL DEFAULT 0
        CHECK(score >= 0),
    option_order TEXT,

    PRIMARY KEY(version_id, question_order),
    UNIQUE(version_id, question_id),

    FOREIGN KEY(version_id)
        REFERENCES exam_versions(version_id)
        ON DELETE CASCADE,

    FOREIGN KEY(question_id)
        REFERENCES questions(question_id)
        ON DELETE RESTRICT
);

-- 16. EXAM_SESSIONS
CREATE TABLE exam_sessions (
    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_id INTEGER NOT NULL,
    session_name TEXT NOT NULL,
    version_id INTEGER NOT NULL,

    access_code TEXT UNIQUE,
    password_hash TEXT,

    start_time TEXT,
    end_time TEXT,

    status TEXT NOT NULL DEFAULT 'scheduled'
        CHECK(status IN (
            'scheduled',
            'ongoing',
            'completed',
            'cancelled'
        )),

    created_by INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY(exam_id)
        REFERENCES exams(exam_id)
        ON DELETE RESTRICT,

    FOREIGN KEY(version_id)
        REFERENCES exam_versions(version_id)
        ON DELETE RESTRICT,

    FOREIGN KEY(created_by)
        REFERENCES users(user_id)
        ON DELETE RESTRICT
);

-- 17. SESSION_STUDENTS
CREATE TABLE session_students (
    session_student_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    student_id INTEGER NOT NULL,

    student_code_snapshot TEXT NOT NULL,
    name_snapshot TEXT NOT NULL,
    class_snapshot TEXT NOT NULL,

    started_at TEXT,
    submitted_at TEXT,

    status TEXT NOT NULL DEFAULT 'registered'
        CHECK(status IN (
            'registered',
            'in_progress',
            'submitted',
            'absent',
            'disqualified'
        )),

    FOREIGN KEY(session_id)
        REFERENCES exam_sessions(session_id)
        ON DELETE CASCADE,

    FOREIGN KEY(student_id)
        REFERENCES students(student_id)
        ON DELETE RESTRICT,

    UNIQUE(session_id, student_id)
);

-- 18. ANSWERS
CREATE TABLE answers (
    answer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_student_id INTEGER NOT NULL,
    question_id INTEGER NOT NULL,

    answer_text TEXT,

    is_correct INTEGER
        CHECK(is_correct IN (0, 1) OR is_correct IS NULL),

    score REAL NOT NULL DEFAULT 0
        CHECK(score >= 0),

    answered_at TEXT,
    updated_at TEXT,

    FOREIGN KEY(session_student_id)
        REFERENCES session_students(session_student_id)
        ON DELETE CASCADE,

    FOREIGN KEY(question_id)
        REFERENCES questions(question_id)
        ON DELETE RESTRICT,

    UNIQUE(session_student_id, question_id)
);

-- 19. RESULTS
CREATE TABLE results (
    result_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_student_id INTEGER NOT NULL,

    total_score REAL NOT NULL DEFAULT 0
        CHECK(total_score >= 0),

    correct_count INTEGER NOT NULL DEFAULT 0
        CHECK(correct_count >= 0),

    incorrect_count INTEGER NOT NULL DEFAULT 0
        CHECK(incorrect_count >= 0),

    unanswered_count INTEGER NOT NULL DEFAULT 0
        CHECK(unanswered_count >= 0),

    submitted_at TEXT,
    graded_at TEXT,

    FOREIGN KEY(session_student_id)
        REFERENCES session_students(session_student_id)
        ON DELETE CASCADE,

    UNIQUE(session_student_id)
);

-- 20. EXAM_VIOLATIONS
CREATE TABLE exam_violations (
    violation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_student_id INTEGER NOT NULL,

    violation_type TEXT NOT NULL,
    description TEXT,

    occurred_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    severity TEXT NOT NULL DEFAULT 'warning'
        CHECK(severity IN ('info', 'warning', 'serious')),

    handled_by INTEGER,
    handled_at TEXT,

    FOREIGN KEY(session_student_id)
        REFERENCES session_students(session_student_id)
        ON DELETE CASCADE,

    FOREIGN KEY(handled_by)
        REFERENCES users(user_id)
        ON DELETE SET NULL
);
