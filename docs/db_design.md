# Database Design — Question Bank & LAN Exam System

Internal document for the question bank and offline/LAN exam system at Vu Tien High School.

**Status:** revision 2 (supersedes `docs/data_dictionary.md`, which describes revision 1).

**Derived from:** `docs/data_dictionary.md`.
**Revised against:** `design/System Overview & Build Plan - Question Bank & LAN Exam System.md` and `design/1. Project Idea - Exam Management & Offline Exam System.md`.

**Not yet implemented.** This document defines the target model; `database/schema.sql` and `database/indexes.sql` still hold revision 1 and have not been migrated.

---

## 1. Purpose and scope

This document is the single source of truth for *what the system stores and why*. It exists because the original data dictionary was written bottom-up — one table at a time, as a transcription of the DDL — which made it impossible to answer "does the design actually support the exam room the teachers described?".

So this revision is organised around requirements: every table and field traces back to a section of the System Overview (`[1.1]`, `[2.3]`, `[III]`, …) or the Project Idea phases (`[P1-T1]`, `[P3-T6]`, …). Anything that could not be traced was either justified explicitly or removed.

Out of scope: API shapes, SQL dialect decisions, and UI behaviour. Where a rule cannot be enforced by the data model, it is listed in section 11 as a backend invariant rather than silently dropped.

---

## 2. Requirement traceability

The point of this table is to make gaps impossible to overlook. Every requirement that touches persisted state has an owner.

### 2.1 System Overview

| Ref | Requirement | Storage |
| --- | --- | --- |
| [1.1] | Classify by Subject, Grade, Topic, Lesson | `subjects`, `grades`, `topics`, `lessons`, `questions` (denormalised subject/grade/topic/lesson keys) |
| [1.1] | Classify by cognitive level | `questions.difficulty`, `exam_matrices.difficulty` |
| [1.1] | Three question types | `questions.question_type` + `question_options` + `question_accepted_answers` |
| [1.2] | Import from `.docx` / `.xlsx` using a template | `import_batches`, `questions.import_batch_id` |
| [1.2] | Attach images and formulas | `question_media` |
| [1.2] | Parse into an editable table before saving | `import_batches.status = 'pending'` → `'imported'` |
| [1.3] | Configure counts per level, generate a master paper | `exam_matrices`, `exam_versions`, `exam_version_questions` |
| [1.3] | Preview, swap a question, save | `exam_version_questions` (row-level replace) |
| [2.1] | Roster template: No., Student ID, Name, Class, DOB | `students` (+ snapshots on `session_students`) |
| [2.1] | Warn on duplicate code / missing fields | `students.student_code` UNIQUE |
| [2.1] | Add/remove students freely | `session_students`, soft delete via `removed_at` |
| [2.2] | QR code from the server's LAN IP | Not stored — derived at runtime from config |
| [2.2] | Duration, start/end time | `exams.duration_minutes` (default), `exam_sessions.duration_minutes` (override), `start_time`, `end_time` |
| [2.2] | Shuffle questions and answers, one code per student | `exam_versions.shuffle_*`, `exam_version_questions.option_order`, `session_students.version_id` |
| [2.2] | Lock the room by password or IP range | `exam_sessions.password_hash`, `allowed_ip_range` |
| [2.3] | Authenticate by candidate number against the roster | `students.student_code`, `session_students.student_code_snapshot` |
| [2.3] | One candidate number is locked to one device | `session_students.device_token`, `device_locked_at` |
| [3.1] | Countdown, progress, answer grid, flag for review | `session_students.started_at`, `answers.is_flagged`, `answers` |
| [3.1] | Auto-save on every selection, survive F5 / dropped LAN | `answers` UPSERT on `(session_student_id, question_id)` |
| [3.2] | Auto-grade on submit, per the student's own paper code | `results`, `answers.score`, `session_students.version_id` |
| [3.2] | Attendance: total / absent / in progress / submitted | `session_students.status` |
| [3.2] | Release a student to a new machine (retake) | `session_students.retake_count`, `device_token` |
| [3.3] | Export a sheet matching the input roster exactly | `session_students` snapshots, `results`, `session_students.version_id` |
| [3.3] | Score distribution, per-question correct rate | `results`, `answers.is_correct` |
| [III] | Tab/window switch detection and counts | `exam_violations` |
| [III] | Encrypt the paper, deliver page-by-page | Not stored — request-level |
| [III] | Room and IP locks, duplicate login refusal | `exam_sessions`, `session_students.device_token`, `exam_violations.violation_type = 'duplicate_login'` |

### 2.2 Project Idea phases

| Ref | Task | Storage |
| --- | --- | --- |
| [P1-T1] | "Backbone": Lesson → Topic → Format → Level | `topics`, `lessons`, `questions` (see the conflict note in section 12) |
| [P1-T1] | `Questions`, `Exams`, `Exam_Matrix` tables | `questions`, `exams`, `exam_matrices` |
| [P2-T3] | Manual entry form, interface adapts to the type | `question_options` (4 rows), `question_accepted_answers` |
| [P2-T4] | Bulk import with a fixed column order | `import_batches`; template contract in section 7 |
| [P3-T5] | Matrix entry plus "generate N master papers" | `exam_matrices`, `exam_versions` |
| [P3-T6] | Draw by `random.sample`, then shuffle per student | `exam_version_questions`, `session_students.version_id`, `option_order` |
| [P4-T7] | Countdown, per-format rendering, 5-second auto-save | `answers`, `session_students.started_at` |
| [P4-T8] | Proctor dashboard, "start timer", "collect all" | `session_students.status`, `last_seen_at`, `exam_sessions.status` |
| [P5-T9] | Grading rules per format | `answers.score`, `answers.correct_statement_count` |
| [P5-T10] | Score sheet, Excel export, charts | `results`, `answers.is_correct` |
| [P5-T11] | Package as a single executable | No storage impact |

---

## 3. Conventions

- `INTEGER PRIMARY KEY AUTOINCREMENT` — surrogate key.
- Booleans are `INTEGER` constrained to `IN (0, 1)`.
- Timestamps are `TEXT`. The database's `CURRENT_TIMESTAMP` is UTC; app-written values must use one agreed format (`YYYY-MM-DD HH:MM:SS`).
- Catalog tables and `questions` carry `is_active` for soft delete, because the history must stay intact. Soft delete is mandatory for any row already referenced (see section 11, I6).
- Enum values are English except `difficulty`, which keeps the Ministry's Vietnamese abbreviations `NB/TH/VD/VDC`. This is deliberate: `backend/python.py:263` validates those literals, and only the UI label is translated.
- Every child row that can be regenerated (options, media, matrix lines, version questions, answers, results, violations) cascades from its parent. Rows that represent institutional history do not.

---

## 4. Entity relationships

```
subjects ─┐
grades ───┼─< topics ─< lessons
          │      │         │
          │      └────┬────┘
          │           │
          └──< questions >─── created_by ──> users
                   │
                   ├─< question_options            (choices / T-F statements)
                   ├─< question_accepted_answers   (short-answer keys)
                   ├─< question_media              (images, formulas)
                   └── import_batch_id ──> import_batches ──> users

grades ──< classes ──< students
                         │
exams >─── exam_matrices │        (one line per matrix row)
      >─── exam_versions >─── exam_version_questions >─── questions
                 │
                 └──< session_students >──── students
        exam_sessions ──┘        │
          │                      ├─< answers >──── questions
          └─ created_by ──> users├── 1 results
                                 └─< exam_violations
```

Reading notes:

- `exam_sessions` points at a **default** version; `session_students.version_id` overrides it per candidate. That single override is what makes per-student paper codes possible.
- `answers` and `results` hang off `session_students`, not off `students`. A student's work is only meaningful inside one sitting, and the snapshots preserve what the roster said at that moment.

---

## 5. Table catalog

### Group A — Identity and catalog

#### `users`

Teacher and admin accounts. Students never have accounts; they are identified against a roster.

| Field | Type | Constraints | Meaning |
| --- | --- | --- | --- |
| `user_id` | `INTEGER` | PK AUTOINCREMENT | Account id |
| `username` | `TEXT` | NOT NULL UNIQUE | Login name |
| `password_hash` | `TEXT` | NOT NULL | Hashed password |
| `full_name` | `TEXT` | NOT NULL | Full name |
| `role` | `TEXT` | NOT NULL | `admin`, `teacher` |
| `is_active` | `INTEGER` | NOT NULL DEFAULT 1 | 1 active, 0 disabled |
| `created_at` | `TEXT` | NOT NULL DEFAULT CURRENT_TIMESTAMP | Created at |

#### `subjects`, `grades`

Flat catalogs. Each has `*_id`, a NOT NULL UNIQUE name, and `is_active`.

#### `topics`

A topic belongs to a (subject, grade) pair.

| Field | Type | Constraints | Meaning |
| --- | --- | --- | --- |
| `topic_id` | `INTEGER` | PK AUTOINCREMENT | Topic id |
| `subject_id` | `INTEGER` | NOT NULL, FK → `subjects` | Subject |
| `grade_id` | `INTEGER` | NOT NULL, FK → `grades` | Grade |
| `topic_name` | `TEXT` | NOT NULL | Topic name |
| `is_active` | `INTEGER` | NOT NULL DEFAULT 1 | 1 active, 0 disabled |

Table constraints: `UNIQUE(subject_id, grade_id, topic_name)`.

#### `lessons`

A lesson belongs to one topic, and carries an explicit order because the textbook order is meaningful.

| Field | Type | Constraints | Meaning |
| --- | --- | --- | --- |
| `lesson_id` | `INTEGER` | PK AUTOINCREMENT | Lesson id |
| `topic_id` | `INTEGER` | NOT NULL, FK → `topics` | Owning topic |
| `lesson_name` | `TEXT` | NOT NULL | Lesson name |
| `lesson_order` | `INTEGER` | NOT NULL DEFAULT 1, > 0 | Position within the topic |
| `is_active` | `INTEGER` | NOT NULL DEFAULT 1 | 1 active, 0 disabled |

Table constraints: `UNIQUE(topic_id, lesson_name)`, `UNIQUE(topic_id, lesson_order)`.

#### `classes`

| Field | Type | Constraints | Meaning |
| --- | --- | --- | --- |
| `class_id` | `INTEGER` | PK AUTOINCREMENT | Class id |
| `class_name` | `TEXT` | NOT NULL | e.g. 10A1 |
| `grade_id` | `INTEGER` | NOT NULL, FK → `grades` | Grade |
| `school_year` | `TEXT` | nullable | e.g. 2025-2026 |
| `is_active` | `INTEGER` | NOT NULL DEFAULT 1 | 1 active, 0 disabled |

Class names repeat across years, so uniqueness is `(class_name, school_year)` — enforced by an expression index over `COALESCE(school_year, '')`. See section 12, note 3.

#### `students`

| Field | Type | Constraints | Meaning |
| --- | --- | --- | --- |
| `student_id` | `INTEGER` | PK AUTOINCREMENT | Student id |
| `student_code` | `TEXT` | NOT NULL UNIQUE | Student code, doubles as the candidate number (SBD) |
| `full_name` | `TEXT` | NOT NULL | Full name |
| `date_of_birth` | `TEXT` | nullable | **rev 2** — ISO `YYYY-MM-DD` |
| `class_id` | `INTEGER` | NOT NULL, FK → `classes` | Class |
| `is_active` | `INTEGER` | NOT NULL DEFAULT 1 | 1 active, 0 disabled |

`date_of_birth` is new in this revision because the roster template in [2.1] names Ngày sinh and the export in [3.3] must reproduce the input list. It cannot be recovered later, so it has to be captured at import.

### Group B — Question bank

#### `questions`

| Field | Type | Constraints | Meaning |
| --- | --- | --- | --- |
| `question_id` | `INTEGER` | PK AUTOINCREMENT | Question id |
| `subject_id` | `INTEGER` | NOT NULL, FK → `subjects` | Subject |
| `grade_id` | `INTEGER` | NOT NULL, FK → `grades` | Grade |
| `topic_id` | `INTEGER` | NOT NULL, FK → `topics` | Topic |
| `lesson_id` | `INTEGER` | nullable, FK → `lessons` | Lesson |
| `created_by` | `INTEGER` | NOT NULL, FK → `users` | Author |
| `import_batch_id` | `INTEGER` | nullable, FK → `import_batches` | **rev 2** — batch that created this row |
| `question_type` | `TEXT` | NOT NULL | `multiple_choice`, `true_false`, `short_answer` |
| `difficulty` | `TEXT` | NOT NULL | `NB`, `TH`, `VD`, `VDC` |
| `question_text` | `TEXT` | NOT NULL | Question body |
| `explanation` | `TEXT` | nullable | Worked solution, shown after grading |
| `is_active` | `INTEGER` | NOT NULL DEFAULT 1 | 1 active, 0 retired |
| `created_at` | `TEXT` | NOT NULL DEFAULT CURRENT_TIMESTAMP | Created at |
| `updated_at` | `TEXT` | nullable | Last edit |

`subject_id` and `grade_id` are derivable from `topic_id`, and `topic_id` from `lesson_id`. The redundancy is intentional: the matrix draw filters on all of them at once ([P3-T6]), and one index on the full set is much cheaper than joining through the catalog on every draw. The model cannot keep them consistent — the backend must (section 11, I1).

#### `question_options`

| Field | Type | Constraints | Meaning |
| --- | --- | --- | --- |
| `option_id` | `INTEGER` | PK AUTOINCREMENT | Option id |
| `question_id` | `INTEGER` | NOT NULL, FK → `questions` | Parent question |
| `option_key` | `TEXT` | NOT NULL | `a`, `b`, `c`, `d` |
| `option_text` | `TEXT` | NOT NULL | Choice text, or a True/False statement |
| `is_correct` | `INTEGER` | NOT NULL DEFAULT 0 | See the semantics in section 6 |
| `sort_order` | `INTEGER` | NOT NULL DEFAULT 1, > 0 | Original display order |

Table constraints: `UNIQUE(question_id, option_key)`, `UNIQUE(question_id, sort_order)`. Cascades from `questions`.

#### `question_accepted_answers`

Short-answer keys.

| Field | Type | Constraints | Meaning |
| --- | --- | --- | --- |
| `accepted_answer_id` | `INTEGER` | PK AUTOINCREMENT | Id |
| `question_id` | `INTEGER` | NOT NULL, FK → `questions` | Parent question |
| `answer_text` | `TEXT` | NOT NULL | An accepted answer |
| `is_case_sensitive` | `INTEGER` | NOT NULL DEFAULT 0 | Whether case matters |

Table constraints: `UNIQUE(question_id, answer_text)`. Cascades from `questions`.

#### `question_media`

| Field | Type | Constraints | Meaning |
| --- | --- | --- | --- |
| `media_id` | `INTEGER` | PK AUTOINCREMENT | Id |
| `question_id` | `INTEGER` | NOT NULL, FK → `questions` | Parent question |
| `media_type` | `TEXT` | NOT NULL | `image`, `file`, `audio` |
| `file_path` | `TEXT` | NOT NULL | Path under `backend/storage/question_media/` |
| `sort_order` | `INTEGER` | NOT NULL DEFAULT 1, > 0 | Render order |

Cascades from `questions`.

#### `import_batches`

**New in this revision.** Bulk import is a headline feature ([1.2], [P2-T4]) and one bad file can create thousands of rows. Without a batch record there is no way to identify or undo one.

| Field | Type | Constraints | Meaning |
| --- | --- | --- | --- |
| `batch_id` | `INTEGER` | PK AUTOINCREMENT | Batch id |
| `file_name` | `TEXT` | NOT NULL | Original file name |
| `file_type` | `TEXT` | NOT NULL | `docx`, `xlsx` |
| `subject_id` | `INTEGER` | nullable, FK → `subjects` | Target, NULL = as declared in the file |
| `grade_id` | `INTEGER` | nullable, FK → `grades` | Target |
| `topic_id` | `INTEGER` | nullable, FK → `topics` | Target |
| `lesson_id` | `INTEGER` | nullable, FK → `lessons` | Target |
| `uploaded_by` | `INTEGER` | NOT NULL, FK → `users` | Uploader |
| `total_rows` | `INTEGER` | NOT NULL DEFAULT 0 | Rows found |
| `imported_count` | `INTEGER` | NOT NULL DEFAULT 0, ≥ 0 | Rows written |
| `failed_count` | `INTEGER` | NOT NULL DEFAULT 0, ≥ 0 | Rows rejected |
| `status` | `TEXT` | NOT NULL DEFAULT `pending` | `pending`, `imported`, `rolled_back`, `failed` |
| `error_report` | `TEXT` | nullable | Per-row validation errors |
| `created_at` | `TEXT` | NOT NULL DEFAULT CURRENT_TIMESTAMP | Uploaded at |
| `rolled_back_at` | `TEXT` | nullable | Rolled back at |

### Group C — Exam authoring

#### `exams`

The master paper definition.

| Field | Type | Constraints | Meaning |
| --- | --- | --- | --- |
| `exam_id` | `INTEGER` | PK AUTOINCREMENT | Exam id |
| `title` | `TEXT` | NOT NULL, non-blank after trim | Exam name |
| `subject_id` | `INTEGER` | NOT NULL, FK → `subjects` | Subject |
| `grade_id` | `INTEGER` | NOT NULL, FK → `grades` | Grade |
| `duration_minutes` | `INTEGER` | NOT NULL, > 0 | Default duration |
| `created_by` | `INTEGER` | NOT NULL, FK → `users` | Author |
| `status` | `TEXT` | NOT NULL DEFAULT `draft` | `draft`, `ready`, `archived` |
| `created_at` | `TEXT` | NOT NULL DEFAULT CURRENT_TIMESTAMP | Created at |
| `updated_at` | `TEXT` | nullable | Last edit |

#### `exam_matrices`

One row per matrix line — the machine-readable form of "Lesson 1 / Topic 1 / multiple choice / NB: take 2" ([1.3], [P3-T5]).

| Field | Type | Constraints | Meaning |
| --- | --- | --- | --- |
| `matrix_id` | `INTEGER` | PK AUTOINCREMENT | Line id |
| `exam_id` | `INTEGER` | NOT NULL, FK → `exams` | Owning exam |
| `topic_id` | `INTEGER` | NOT NULL, FK → `topics` | Topic to draw from |
| `lesson_id` | `INTEGER` | nullable, FK → `lessons` | Narrow to one lesson |
| `difficulty` | `TEXT` | NOT NULL | `NB`, `TH`, `VD`, `VDC` |
| `question_type` | `TEXT` | NOT NULL | `multiple_choice`, `true_false`, `short_answer` |
| `question_count` | `INTEGER` | NOT NULL, > 0 | How many to draw |

Cascades from `exams`.

#### `exam_versions`

A generated paper code (Mã đề). At least one per exam; more when teachers ask for several master papers ([P3-T6]).

| Field | Type | Constraints | Meaning |
| --- | --- | --- | --- |
| `version_id` | `INTEGER` | PK AUTOINCREMENT | Version id |
| `exam_id` | `INTEGER` | NOT NULL, FK → `exams` | Owning exam |
| `version_code` | `TEXT` | NOT NULL | Printed code, e.g. `101` |
| `shuffle_questions` | `INTEGER` | NOT NULL DEFAULT 0 | Shuffle question order |
| `shuffle_options` | `INTEGER` | NOT NULL DEFAULT 0 | Shuffle answer order |
| `created_at` | `TEXT` | NOT NULL DEFAULT CURRENT_TIMESTAMP | Generated at |

Table constraints: `UNIQUE(exam_id, version_code)`, `UNIQUE(exam_id, version_id)`. The second one is new and exists solely so a session can use a composite foreign key (section 11, I3).

#### `exam_version_questions`

The frozen question list of one paper code. Frozen is the important word: editing the bank later must not silently change a paper that has already been sat.

| Field | Type | Constraints | Meaning |
| --- | --- | --- | --- |
| `version_id` | `INTEGER` | NOT NULL, FK → `exam_versions` | Version |
| `question_id` | `INTEGER` | NOT NULL, FK → `questions` | Question |
| `question_order` | `INTEGER` | NOT NULL | Position in this paper |
| `score` | `REAL` | NOT NULL DEFAULT 0, ≥ 0 | Maximum score for this question |
| `option_order` | `TEXT` | nullable | Display order of option keys, e.g. `["c","a","d","b"]`; NULL = original order |

Table constraints: `PRIMARY KEY(version_id, question_order)`, `UNIQUE(version_id, question_id)`. Cascades from `exam_versions`.

### Group D — Exam delivery

#### `exam_sessions`

One exam room / sitting ([2.1]–[2.3], [P4-T8]).

| Field | Type | Constraints | Meaning |
| --- | --- | --- | --- |
| `session_id` | `INTEGER` | PK AUTOINCREMENT | Session id |
| `exam_id` | `INTEGER` | NOT NULL | Exam, bound with `version_id` (composite FK) |
| `session_name` | `TEXT` | NOT NULL | e.g. "Ca 1 — 12A1" |
| `version_id` | `INTEGER` | NOT NULL | **Default** paper code for the room |
| `access_code` | `TEXT` | UNIQUE, nullable | Join code for the room |
| `password_hash` | `TEXT` | nullable | Room password |
| `allowed_ip_range` | `TEXT` | nullable | **rev 2** — CIDR list, e.g. `192.168.1.0/24,10.0.0.5` |
| `duration_minutes` | `INTEGER` | nullable, > 0 | **rev 2** — per-sitting override; NULL = inherit from the exam |
| `start_time` | `TEXT` | nullable | Opened at |
| `end_time` | `TEXT` | nullable | Closed / collected at |
| `status` | `TEXT` | NOT NULL DEFAULT `scheduled` | `scheduled`, `ongoing`, `completed`, `cancelled` |
| `created_by` | `INTEGER` | NOT NULL, FK → `users` | Creator |
| `created_at` | `TEXT` | NOT NULL DEFAULT CURRENT_TIMESTAMP | Created at |

The composite FK `(exam_id, version_id)` → `exam_versions(exam_id, version_id)` is new. Revision 1 stored both ids with nothing tying them together, so a session could point at a version belonging to a different exam.

#### `session_students`

One candidate in one sitting, with snapshots so a result sheet can be reproduced after the roster changes ([2.1], [2.3], [3.2], [3.3]).

| Field | Type | Constraints | Meaning |
| --- | --- | --- | --- |
| `session_student_id` | `INTEGER` | PK AUTOINCREMENT | Row id |
| `session_id` | `INTEGER` | NOT NULL, FK → `exam_sessions` | Sitting |
| `student_id` | `INTEGER` | NOT NULL, FK → `students` | Student |
| `version_id` | `INTEGER` | nullable, FK → `exam_versions` | **rev 2** — this student's paper code; NULL = session default |
| `student_code_snapshot` | `TEXT` | NOT NULL | Candidate number at registration |
| `name_snapshot` | `TEXT` | NOT NULL | Name at registration |
| `class_snapshot` | `TEXT` | NOT NULL | Class at registration |
| `device_token` | `TEXT` | nullable | **rev 2** — device bound on first login |
| `device_locked_at` | `TEXT` | nullable | **rev 2** — when the binding was made |
| `last_seen_at` | `TEXT` | nullable | **rev 2** — heartbeat for the proctor screen |
| `retake_count` | `INTEGER` | NOT NULL DEFAULT 0, ≥ 0 | **rev 2** — teacher releases for this student |
| `started_at` | `TEXT` | nullable | Timer start, per student |
| `submitted_at` | `TEXT` | nullable | Submitted at |
| `removed_at` | `TEXT` | nullable | **rev 2** — soft-delete marker |
| `status` | `TEXT` | NOT NULL DEFAULT `registered` | `registered`, `in_progress`, `submitted`, `absent`, `disqualified`, `removed` |

Table constraints: `UNIQUE(session_id, student_id)`. Cascades from `exam_sessions`.

`version_id` is the field that makes the overview's "one paper code per student" ([2.2]) and "grade against the student's own code" ([3.2]) expressible. Revision 1 pinned one version per room, so the Mã đề column in the [3.3] export had nothing to print.

#### `answers`

One row per candidate per question, written and rewritten by auto-save ([3.1], [P4-T7]).

| Field | Type | Constraints | Meaning |
| --- | --- | --- | --- |
| `answer_id` | `INTEGER` | PK AUTOINCREMENT | Row id |
| `session_student_id` | `INTEGER` | NOT NULL, FK → `session_students` | Candidate in sitting |
| `question_id` | `INTEGER` | NOT NULL, FK → `questions` | Question |
| `answer_text` | `TEXT` | nullable | Encoded per type — see section 6 |
| `is_correct` | `INTEGER` | nullable, `0`/`1`/NULL | NULL = not yet graded |
| `is_flagged` | `INTEGER` | NOT NULL DEFAULT 0 | **rev 2** — flagged for review |
| `correct_statement_count` | `INTEGER` | nullable, 0–4 | **rev 2** — correct statements in a True/False item |
| `score` | `REAL` | NOT NULL DEFAULT 0, ≥ 0 | Awarded score |
| `answered_at` | `TEXT` | nullable | First write; never changes |
| `updated_at` | `TEXT` | nullable | Last write |

Table constraints: `UNIQUE(session_student_id, question_id)` — this is what makes the auto-save an UPSERT. Cascades from `session_students`.

`is_flagged` was missing in revision 1, so the yellow "review later" marker was lost whenever the page reloaded, contradicting the promise in [3.1] that state survives an F5.

#### `results`

Per-candidate rollup, written at submit or at collect-all ([3.2], [3.3], [P5-T10]).

| Field | Type | Constraints | Meaning |
| --- | --- | --- | --- |
| `result_id` | `INTEGER` | PK AUTOINCREMENT | Row id |
| `session_student_id` | `INTEGER` | NOT NULL UNIQUE, FK → `session_students` | Candidate in sitting |
| `total_score` | `REAL` | NOT NULL DEFAULT 0, ≥ 0 | Total score |
| `correct_count` | `INTEGER` | NOT NULL DEFAULT 0, ≥ 0 | Fully correct questions |
| `incorrect_count` | `INTEGER` | NOT NULL DEFAULT 0, ≥ 0 | Wrong questions |
| `unanswered_count` | `INTEGER` | NOT NULL DEFAULT 0, ≥ 0 | Unanswered questions |
| `submitted_at` | `TEXT` | nullable | Submitted at |
| `graded_at` | `TEXT` | nullable | Graded at |

The Mã đề column of the export comes from `session_students.version_id`, so it is deliberately not duplicated here.

#### `exam_violations`

Anti-cheating log ([III]).

| Field | Type | Constraints | Meaning |
| --- | --- | --- | --- |
| `violation_id` | `INTEGER` | PK AUTOINCREMENT | Row id |
| `session_student_id` | `INTEGER` | NOT NULL, FK → `session_students` | Candidate in sitting |
| `violation_type` | `TEXT` | NOT NULL | Enumerated — see section 8 |
| `description` | `TEXT` | nullable | Detail |
| `occurred_at` | `TEXT` | NOT NULL DEFAULT CURRENT_TIMESTAMP | Detected at |
| `severity` | `TEXT` | NOT NULL DEFAULT `warning` | `info`, `warning`, `serious` |
| `handled_by` | `INTEGER` | nullable, FK → `users` | Handled by |
| `handled_at` | `TEXT` | nullable | Handled at |

One row per detected event, so the count shown to the proctor is a `GROUP BY`, not a stored counter. `violation_type` was free text in revision 1 while every other enum was constrained; it is enumerated now (section 12, note 6).

---

## 6. Question-type modelling

This is the part revision 1 left implicit, and it is the part most likely to cause bugs, so it is specified here explicitly.

A question of any type lives in one `questions` row. What differs is where the answer lives and what `answer_text` contains.

| | `multiple_choice` | `true_false` | `short_answer` |
| --- | --- | --- | --- |
| Answer key location | `question_options.is_correct` | `question_options.is_correct` | `question_accepted_answers` |
| Row count | exactly 4 options | exactly 4 statements, keys `a`–`d` | ≥ 1 accepted answer |
| Meaning of `is_correct` | 1 on the single correct option | the statement's truth value: 1 = True, 0 = False | unused |
| Student answer in `answers.answer_text` | the chosen key, e.g. `b` | JSON verdicts, e.g. `{"a":1,"b":0,"c":1,"d":0}` | the raw text or number typed |
| Grading | all-or-nothing | partial credit by count | string match |

`is_correct` carries two meanings depending on the parent's type — "this is the chosen option" versus "this statement is true". That overload is a deliberate trade: it keeps one option table instead of two, and the semantics are unambiguous once the parent type is known.

Partial credit for True/False (0.1 / 0.25 / 0.5 / 1.0 by number of correct statements, [P5-T9]) requires knowing *how many* statements were right, which a single `is_correct` flag cannot express. That is why `answers.correct_statement_count` exists — without it the count could only be recovered by re-parsing the JSON.

Short-answer matching: trim both sides, then compare case-insensitively unless `is_case_sensitive = 1`. Number formatting (`0.5` vs `0,5`) is normalised by the backend, not stored.

---

## 7. Import template contract

The `.docx` / `.xlsx` template described in [1.2] and [P2-T4] maps onto storage as follows.

| Template column | Destination |
| --- | --- |
| Tên bài (Lesson) | `lessons.lesson_name` — resolved or created under the target topic |
| Tên chủ đề (Topic) | `topics.topic_name` |
| Định dạng (Format) | `questions.question_type` |
| Mức độ (Level) | `questions.difficulty` |
| Câu hỏi (Question) | `questions.question_text` |
| Đáp án (Answer) | see below |
| — | `questions.import_batch_id` ← the batch just created |

Tag conventions in the source file ([1.2]): `[Question]` / `[Answer]` delimit a question, and `*` marks the correct option. Answers resolve by type in the same way as section 6.

Import is a two-step flow, which is why `import_batches.status` starts at `pending`: parse the file into `pending`, let the teacher edit in the web table, then set `imported` and write the `questions` rows. A batch can later be flipped to `rolled_back`, and its rows are found via `questions.import_batch_id`.

---

## 8. Enum reference

| Field | Table(s) | Values |
| --- | --- | --- |
| `role` | `users` | `admin`, `teacher` |
| `question_type` | `questions`, `exam_matrices` | `multiple_choice`, `true_false`, `short_answer` |
| `difficulty` | `questions`, `exam_matrices` | `NB`, `TH`, `VD`, `VDC` (Nhận biết, Thông hiểu, Vận dụng, Vận dụng cao) |
| `media_type` | `question_media` | `image`, `file`, `audio` |
| `file_type` | `import_batches` | `docx`, `xlsx` |
| `status` | `import_batches` | `pending`, `imported`, `rolled_back`, `failed` |
| `status` | `exams` | `draft`, `ready`, `archived` |
| `status` | `exam_sessions` | `scheduled`, `ongoing`, `completed`, `cancelled` |
| `status` | `session_students` | `registered`, `in_progress`, `submitted`, `absent`, `disqualified`, `removed` |
| `violation_type` | `exam_violations` | `tab_switch`, `window_blur`, `fullscreen_exit`, `copy_attempt`, `paste_attempt`, `duplicate_login`, `device_change`, `other` |
| `severity` | `exam_violations` | `info`, `warning`, `serious` |

API payloads use these exact values. Vietnamese labels belong in the UI layer only.

---

## 9. Candidate lifecycle

The statuses above are only meaningful as a sequence, so the intended transitions are:

```
registered ──login──> in_progress ──submit/time-up──> submitted
     │                     │
     │                     └──teacher retake──> in_progress   (retake_count += 1)
     │
     ├──never arrives──> absent
     ├──teacher removes──> removed        (soft delete, removed_at set)
     └──teacher disqualifies──> disqualified
```

Two consequences worth stating plainly:

- **A retake is not a status change.** It clears `device_token` / `device_locked_at`, increments `retake_count`, and resets that student's `answers` and `results`. The backend must do this atomically (section 11, I8).
- **Removal must be soft.** `answers` and `results` cascade from `session_students`, so a hard DELETE during a sitting destroys submitted work. `removed_at` plus `status = 'removed'` is the supported path; hard deletion is reserved for tearing down a whole session.

---

## 10. Per-student paper codes

Revision 1 could express only one paper code per room. The overview needs one per candidate, in two different ways ([P3-T6]):

- **Large bank, no master papers:** every candidate gets a freshly drawn, shuffled paper. Each candidate's `session_students.version_id` points at their own `exam_versions` row.
- **Small bank, fixed master papers:** the teacher generates N master papers, and each candidate is assigned one of them with a shuffled order. Many candidates share a `version_id`, and the per-candidate variation lives in `exam_version_questions.option_order` (or in a per-candidate version, depending on how the generator is built).

Resolution rule everywhere: **`COALESCE(session_students.version_id, exam_sessions.version_id)`**. The session value is the room default and keeps revision 1 behaviour working; the student value is the override.

The FK on `session_students.version_id` proves the version exists, but not that it belongs to the session's exam. That check is the backend's (section 11, I3).

---

## 11. Invariants the database cannot enforce

SQLite cannot express a rule that spans rows or tables, so these are requirements on the backend. Each one is a real failure mode, not a theoretical one.

| # | Invariant | Ref |
| --- | --- | --- |
| I1 | `questions.subject_id` / `grade_id` must match the subject and grade of `topic_id`, and `topic_id` must match the topic of `lesson_id` | [1.1] |
| I2 | `exam_matrices.topic_id` / `lesson_id` must belong to the exam's subject and grade | [1.3] |
| I3 | `session_students.version_id` must be a version of the session's exam | [2.2] |
| I4 | `multiple_choice` has exactly 4 options with exactly one `is_correct`; `true_false` has exactly 4 statements `a`–`d`; `short_answer` has ≥ 1 accepted answer | [1.1] |
| I5 | A draw must satisfy every `exam_matrices` line (count, difficulty, type, topic/lesson) and exclude `is_active = 0` | [1.3] |
| I6 | Rows referenced by history are never hard-deleted — retire them with `is_active = 0` | — |
| I7 | `answers.score` must follow the per-type rule and must not exceed the version's `exam_version_questions.score` | [3.2] |
| I8 | A retake atomically bumps `retake_count`, clears the device binding, and resets that student's answers and results | [3.2] |
| I9 | Only the first device to claim an SBD wins; later attempts log `duplicate_login` and are refused | [2.3] |
| I10 | `answered_at` is written once and never updated; `updated_at` on every write | [3.1] |
| I11 | App-written timestamps use one format; the countdown and the export must agree on it | [3.1] |

---

## 12. Notes on specific decisions

1. **Hierarchy direction — needs confirmation.** The System Overview lists classification as Subject → Grade → Topic → Lesson, and this design follows it (`topics` owns `lessons`). But `design/1. Project Idea...` describes the opposite in both places it appears: "Chủ đề thuộc bài học" (topics belong to lessons) and a `Chapters_Lessons` table with topics nested underneath. These cannot both be right. The schema follows the newer overview; if the textbook actually nests topics under lessons, `topics` and `lessons` are inverted and the question bank will be filed the wrong way round. **Resolve before the question bank is populated.**
2. **`difficulty` stays in Vietnamese.** `backend/python.py:263` rejects anything other than `NB/TH/VD/VDC`, and `python.py:509` types it as a `Literal`. Changing the values is an API break with no data-model benefit, so only the display label is translated.
3. **Classes uniqueness.** Revision 1 used `UNIQUE(class_name, school_year)`, which does not dedupe when `school_year IS NULL` because SQLite treats NULLs as distinct — so "10A1" with no year could be inserted repeatedly. An expression index over `COALESCE(school_year, '')` fixes it without making the column NOT NULL.
4. **Duration belongs to the session, with the exam as default.** [2.2] configures duration per exam room. In revision 1 duration lived only on `exams`, so changing it for one sitting mutated the exam and every other sitting using it.
5. **`exam_id` + `version_id` on sessions.** `exam_id` is derivable from `version_id`, but it is kept because reporting filters by exam without joining, and it is now protected by the composite FK rather than left to chance.
6. **`violation_type` is enumerated.** Free text made per-type reporting unstable and was inconsistent with every other enum in the schema. New detectors extend the list in section 8.
7. **Hierarchy of redundancy in `questions`.** Documented in section 5 (Group B). It is a deliberate performance choice for the matrix draw; the cost is invariant I1.
8. **What was cut from revision 1:** nothing. Every revision 1 table and field survived; this revision only adds.

---

## 13. Open questions

- **Hierarchy direction** (note 1) — blocking, must be settled before import.
- **Master-paper vs per-candidate version:** for the small-bank case, do we generate a `exam_versions` row per candidate, or share versions and vary `option_order` per candidate? This affects storage volume on a 40-machine room and should be decided before the generator is written.
- **`absent` marking:** is it automatic at `end_time`, or does the teacher set it? Affects the proctor screen design.
- **Room password vs access code:** `access_code` and `password_hash` coexist on `exam_sessions`, but no requirement distinguishes their roles. Confirm whether both are needed.
- **Behaviour when the LAN drops mid-exam:** [3.1] promises answers survive, but `last_seen_at` and the countdown need a rule for time actually lost to an outage.

---

## 14. Changelog vs `data_dictionary.md`

| # | Change | Reason |
| --- | --- | --- |
| 1 | New table `import_batches`; `questions.import_batch_id` | Bulk import was untracked and unrollbackable |
| 2 | `students.date_of_birth` | Roster template and export both require Ngày sinh |
| 3 | `session_students.version_id` | Per-candidate paper codes were not representable |
| 4 | `session_students.device_token`, `device_locked_at`, `last_seen_at`, `retake_count` | One-device lock, retake release, live monitoring |
| 5 | `session_students.removed_at`, `status += 'removed'` | Removal cascaded away submitted answers |
| 6 | `answers.is_flagged` | Flag-for-review was lost on reload |
| 7 | `answers.correct_statement_count` | True/False partial credit was not auditable |
| 8 | `exam_sessions.duration_minutes` | Duration was not configurable per sitting |
| 9 | `exam_sessions.allowed_ip_range` | IP-range room lock had nowhere to live |
| 10 | Composite FK `(exam_id, version_id)` + `UNIQUE(exam_id, version_id)` | A session could point at another exam's version |
| 11 | `exam_violations.violation_type` enumerated | Free text, inconsistent with every other enum |
| 12 | Classes uniqueness via `COALESCE` expression index | NULL year defeated the UNIQUE |

**Totals:** 21 tables, 159 fields (revision 1: 20 tables, 132 fields). The 27 new fields are: 15 on the new `import_batches`, plus 12 added columns — `students.date_of_birth`, `questions.import_batch_id`, `exam_sessions.duration_minutes` / `allowed_ip_range`, `session_students.version_id` / `device_token` / `device_locked_at` / `last_seen_at` / `retake_count` / `removed_at`, `answers.is_flagged` / `correct_statement_count`.
