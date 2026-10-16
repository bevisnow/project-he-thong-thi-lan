# SYSTEM OVERVIEW & BUILD PLAN — QUESTION BANK & LAN EXAM SYSTEM

## I. SYSTEM OVERVIEW

- **Project name:** Internal Question Bank & Exam Organization System (LAN exam system).
- **Objective:** Help teachers manage exam questions by topic, generate exam papers flexibly according to a knowledge matrix, and organize exams over the local network (LAN) quickly and accurately.
- **Proposed technology stack:**
  - **Backend:** Python (FastAPI/Flask).
  - **Database:** SQLite.
  - **Frontend:** HTML, CSS, JavaScript.
  - **LAN protocol:** Local HTTPS.

## II. DETAILED PLAN BY SUBSYSTEM

### PART 1: Question Bank & Master Paper Management

#### 1.1. Question Bank Database Management

- Classified by Subject, Grade, Topic, Lesson.
- Classified by cognitive level: _Knowledge, Comprehension, Application, Advanced Application_.
- Supports question types: 4-option multiple choice, True/False, Short answer.

#### 1.2. Data Entry

**- Import from file (.docx, .xlsx):**

- The system provides a sample template file.
- Teachers compose questions in the exact template format (e.g. using `[Question]` / `[Answer]` tags and marking the correct answer with `*`) and upload them to the web.

**- Automatic recognition & editing on the web:**

- Automatically parse the uploaded file content into a visual editing table.
- Allow teachers to directly edit content, add/remove questions, and attach images/mathematical formulas in the interface before officially saving to the bank.

#### 1.3. Creating Master Exam Papers by Matrix

- Teachers configure master paper generation parameters:
  - Select subject, topic.
  - Set the number of questions for each level (e.g. 10 Knowledge + 10 Comprehension + 5 Application).
- The system automatically draws random questions from the question bank that meet the matrix to form one Master Paper.
- Teachers can preview the master paper, swap individual questions if not satisfied, and click "save master paper".

### PART 2: CREATING AN EXAM ROOM OVER LAN & MANAGING CANDIDATES

#### 2.1. Managing & Importing the Candidate List

**- Download sample Excel file:** The system provides a standard `.xlsx` file with the fields: No., Student ID / Candidate Number, Full Name, Class, Date of Birth.

**- Upload & automatic cross-check:**

- Teachers upload the list of participating classes to the exam room.
- The system validates: warns about duplicate Student IDs / Candidate Numbers or missing required information.
- Displays a preview table for the teacher to confirm.

**- Flexible customization:** Teachers can quickly add/remove students freely (make-up exams, combined exams) directly in the web interface.

#### 2.2. Initializing & Configuring the Exam Room

**- QR Code & Local HTTPS:**

- The system automatically retrieves the internal IP address of the server.
- Generates a **QR Code** on the teacher's screen / projector so students can scan and enter the exam immediately.

**- Exam room parameter configuration:**

- Exam duration (minutes), start/end time.
- Shuffling options: automatically shuffle question order, shuffle answers, and generate a separate paper code for each student.
- Lock the exam room with a password or an IP range restriction.

#### 2.3. Candidate Login & Authentication Flow

- Students scanning the QR Code are redirected to the authentication page.

**- Authentication by Candidate Number / Student ID:**

- Students enter their **Candidate Number / Student ID** (or select from the Class list).
- The system cross-checks against the Excel list imported in step 2.1:
  - Valid: displays _"Welcome [Full Name] - Class [Class Name]"_. The student clicks "Start exam".
  - Invalid: shows an error.

**- Duplicate login prevention:** Once a candidate number is in use, that account is locked to the current device. Another machine attempting to log in with the same candidate number is denied access.

### PART 3: EXAM TAKING, GRADING & MONITORING

#### 3.1. Student Exam Interface & Experience

**- Screen layout:**

- **Main area (left/center):** displays the question, images, formulas, and answer options.
- **Control panel (right side):**
  - Countdown timer for the exam duration.
  - Progress: [questions answered] / [total questions].
  - Question list panel for quick navigation (Gray: not answered | Green: answered | Yellow: flagged for review).
  - A **"Flag question"** button to come back and review later.

**- Instant auto-save:**

- Every time a student selects an answer, the client immediately sends a request to the database to save the state.
- If the LAN connection drops or the student accidentally presses F5 / closes the browser, reopening the system restores the selected answers and the remaining time.

#### 3.2. Grading & Teacher Monitoring Screen

**- Automatic grading:** As soon as a student clicks "submit" (or papers are collected at time-up), the server automatically grades based on the master paper answer key corresponding to that student's paper code.

**- Attendance monitoring:** The teacher screen updates live statuses based on the Excel list:

- Statistics: total number of students | not yet started (absent) | in progress | submitted.
- A detailed list of absent students' names for quick roll call.

**- Incident handling permission:** Click "retake" for a student whose power failed or machine broke, so the student can switch to a new machine and continue.

#### 3.3. Reporting & Result Export

- Export an Excel file (.xlsx) containing the results of the entire exam session, matching the original student list exactly:
  - Consolidated score sheet: No., Student ID, Full Name, Class, Paper Code, Correct Count, Score, Submission Time.
  - A score distribution analysis page and per-question correct/incorrect rates to help teachers evaluate exam quality.

## III. SECURITY & ANTI-CHEATING ENHANCEMENTS

- **Tab exit / tab switch detection:** Detects when a student switches tabs or hides the browser, shows a warning on the student's screen, and reports the violation count to the teacher's monitoring screen.
1. **One candidate number / one device:** Ensures exams cannot be taken on someone else's behalf or from another device.
2. **Encrypting the exam sent to the client:** Question content is loaded page-by-page / question-by-question to prevent students from pressing F12 to retrieve the entire exam.
