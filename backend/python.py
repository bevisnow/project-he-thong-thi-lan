import sqlite3
import json
import asyncio
import traceback

from pwdlib import PasswordHash
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import HTTPException
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import Literal
from pydantic import BaseModel, Field
from fastapi import FastAPI
from fastapi.responses import Response

password_hash = PasswordHash.recommended()

class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=100)
    role: str = "teacher"

class UserLogin(BaseModel):
    username: str
    password: str

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "data-test.db"

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(auto_submit_loop())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

async def auto_submit_loop():
    while True:
        auto_submit_expired_students()
        await asyncio.sleep(5)

app = FastAPI(title="Hệ thống thi offline", lifespan=lifespan)

BASE_DIR = Path(__file__).resolve().parent
MEDIA_DIR = BASE_DIR / "storage" / "question_media"

app.mount(
    "/media",
    StaticFiles(directory=MEDIA_DIR),
    name="media"
)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def get_utc_time():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def auto_submit_expired_students():
    conn = get_db()

    try:
        now = datetime.now(timezone.utc)
        now_text = now.strftime("%Y-%m-%d %H:%M:%S")

        rows = conn.execute("""
            SELECT
                ss.session_student_id,
                ss.started_at,
                es.end_time,
                e.duration_minutes
            FROM session_students ss
            JOIN exam_sessions es
                ON es.session_id = ss.session_id
            JOIN exams e
                ON e.exam_id = es.exam_id
            WHERE ss.status = 'in_progress'
              AND ss.submitted_at IS NULL
              AND es.status = 'ongoing'
              AND ss.started_at IS NOT NULL
        """).fetchall()

        expired_ids = []

        for row in rows:
            started_at = datetime.strptime(
                row["started_at"], "%Y-%m-%d %H:%M:%S"
            ).replace(tzinfo=timezone.utc)

            deadline = started_at + timedelta(
                minutes=row["duration_minutes"]
            )

            if row["end_time"]:
                session_end = datetime.strptime(
                    row["end_time"], "%Y-%m-%d %H:%M:%S"
                ).replace(tzinfo=timezone.utc)

                deadline = min(deadline, session_end)

            if now >= deadline:
                expired_ids.append(row["session_student_id"])

        for student_id in expired_ids:
            conn.execute("""
                UPDATE session_students
                SET status = 'submitted',
                    submitted_at = ?
                WHERE session_student_id = ?
                  AND status = 'in_progress'
                  AND submitted_at IS NULL
            """, (now_text, student_id))

        conn.commit()

        if expired_ids:
            print(
                f"Đã tự động chốt {len(expired_ids)} bài thi hết giờ.",
                flush=True
            )

    except Exception as e:
        conn.rollback()
        traceback.print_exc()

    finally:
        conn.close()       

@app.get("/")
def home():
    return {"message": "Backend đang chạy!"}


@app.get("/api/db-check")
def db_check():
    if not DB_PATH.exists():
        return {
            "status": "error",
            "message": "Không tìm thấy file database",
            "path": str(DB_PATH),
        }

    conn = get_db()

    try:
        tables = conn.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """).fetchall()

        return {
            "status": "ok",
            "database": str(DB_PATH),
            "tables": [row["name"] for row in tables],
            "table_count": len(tables),
        }
    finally:
        conn.close()

@app.get("/api/questions")
def get_questions(
    subject_id: int | None = None,
    grade_id: int | None = None,
    topic_id: int | None = None,
    lesson_id: int | None = None,
    difficulty: str | None = None,
    question_type: str | None = None,
    is_active: int | None = None
):
    conn = get_db()

    if is_active is not None and is_active not in (0, 1):
        raise HTTPException(
            status_code=400,
            detail="is_active chỉ nhận giá trị 0 hoặc 1"
        )

    if difficulty is not None and difficulty not in ("NB", "TH", "VD", "VDC"):
        raise HTTPException(
            status_code=400,
            detail="difficulty chỉ nhận giá trị là NB, TH, VD, VDC"
        )

    if question_type is not None and question_type not in ("multiple_choice", "true_false", "short_answer"):
        raise HTTPException(
            status_code=400,
            detail="question_type không hợp lệ"
        )
    
    try:
        sql = """
            SELECT
                question_id,
                subject_id,
                grade_id,
                topic_id,
                lesson_id,
                question_type,
                difficulty,
                question_text,
                explanation,
                is_active
            FROM questions
            WHERE 1 = 1
        """

        params = []

        if subject_id is not None:
            sql += " AND subject_id = ?"
            params.append(subject_id)

        if grade_id is not None:
            sql += " AND grade_id = ?"
            params.append(grade_id)

        if topic_id is not None:
            sql += " AND topic_id = ?"
            params.append(topic_id)

        if lesson_id is not None:
            sql += " AND lesson_id = ?"
            params.append(lesson_id)

        if difficulty is not None:
            sql += " AND difficulty = ?"
            params.append(difficulty)

        if question_type is not None:
            sql += " AND question_type = ?"
            params.append(question_type)

        if is_active is not None:
            sql += " AND is_active = ?"
            params.append(is_active)

        sql += " ORDER BY question_id"

        rows = conn.execute(sql, params).fetchall()

        return {
            "status": "ok",
            "count": len(rows),
            "questions": [dict(row) for row in rows]
        }

    finally:
        conn.close()

@app.get("/api/questions/{question_id}")
def get_questions_detail(question_id: int):
    conn = get_db()

    try:
        row = conn.execute("""
            SELECT
            question_id,
            subject_id,
            grade_id,
            topic_id,
            lesson_id,
            created_by,
            question_type,
            difficulty,
            question_text,
            explanation,
            is_active,
            created_at
            FROM QUESTIONS
            WHERE question_id = ?

        """, (question_id,)).fetchone()

        if row is None:
            return {
                "status": "error",
                "message": "Không tìm thấy câu hỏi"
            }
        options = conn.execute(
            """
            SELECT
            option_id,
            question_id,
            option_key,
            option_text
            FROM question_options
            WHERE question_id = ?
            ORDER BY sort_order
            """,
            (question_id,)
            ).fetchall()

        accepted_answers = conn.execute(
            """
            SELECT
            accepted_answer_id,
            question_id,
            answer_text,
            is_case_sensitive
            FROM question_accepted_answers
            WHERE question_id = ?
            ORDER BY accepted_answer_id
            """, 
            (question_id,)
            ).fetchall()

        media = conn.execute(
            """
            SELECT
            media_id,
            question_id,
            media_type,
            file_path,
            sort_order
            FROM question_media
            WHERE question_id = ?
            ORDER BY sort_order
            """,
            (question_id,)
            ).fetchall()    

        media_list = [dict(item) for item in media]

        for item in media_list:
            if item["media_type"] == "image":
                item["image_url"] = f"/media/{item['file_path']}"

        return {
            "status": "ok",
            "question": dict(row),
            "options": [dict(option) for option in options],
            "accepted_answers": [dict(answer) for answer in accepted_answers],
            "media": media_list
        }

    
    finally:
        conn.close()

@app.get("/api/student/questions/{question_id}")
def get_student_question(question_id: int):
    conn = get_db()

    try:
        question = conn.execute(
            """
            SELECT  
            question_id,
            question_type,
            question_text
            FROM questions
            WHERE question_id = ?
            AND is_active = 1
            """, (question_id,)).fetchone()

        if question is None:
            raise HTTPException(
                status_code=404,
                detail="không tìm thấy câu hỏi or câu hỏi bị vô hiệu hóa"
            )

        options = conn.execute(
            """
            SELECT
            option_key,
            option_text,
            sort_order
            FROM question_options
            WHERE question_id = ?
            ORDER by sort_order
            """, (question_id,)).fetchall()

        media = conn.execute(
            """
            SELECT
            media_id,
            media_type,
            file_path,
            sort_order
            FROM question_media
            WHERE question_id = ?
            ORDER by sort_order
            """, (question_id,)).fetchall()

        
        media_list = [dict(item) for item in media]

        for item in media_list:
            if item["media_type"] == "image":
                item["image_url"] = f"/media/{item['file_path']}"

        return {
            "status": "ok",
            "question": dict(question),
            "options": [dict(option) for option in options],
            "media": media_list
        }


    finally:
        conn.close()

class QuestionOptionCreate(BaseModel):
    option_key: str
    option_text: str
    is_correct: bool = False
    sort_order: int = 1

class AcceptedAnswerCreate(BaseModel):
    answer_text: str
    is_case_sensitive: bool = False

class QuestionMediaCreate(BaseModel):
    media_type: Literal["image", "file", "audio"]
    file_path: str
    sort_order: int = 1

class QuestionCreate(BaseModel):
    subject_id: int
    grade_id: int
    topic_id: int
    question_text: str
    question_type: Literal["multiple_choice", "true_false", "short_answer"]
    difficulty: Literal["NB", "TH", "VD", "VDC"]
    lesson_id: int | None = None
    created_by: int
    explanation: str | None = None
    options: list[QuestionOptionCreate] = Field(default_factory=list)
    accepted_answers: list[AcceptedAnswerCreate] = Field(default_factory=list)
    media: list[QuestionMediaCreate] = Field(default_factory=list)

class QuestionUpdate(BaseModel):
    subject_id: int
    grade_id: int
    topic_id: int
    question_text: str
    question_type: Literal["multiple_choice", "true_false", "short_answer"]
    difficulty: Literal["NB", "TH", "VD", "VDC"]
    lesson_id: int | None = None
    explanation: str | None = None
    is_active: bool = True
    options: list[QuestionOptionCreate] = Field(default_factory=list)
    accepted_answers: list[AcceptedAnswerCreate] = Field(default_factory=list)
    media: list[QuestionMediaCreate] = Field(default_factory=list)

class QuestionPatch(BaseModel):
    subject_id: int | None = None
    grade_id: int | None = None   
    topic_id: int | None = None 
    question_text: str | None = None
    difficulty: Literal["NB", "TH", "VD", "VDC"] | None = None
    lesson_id: int | None = None
    explanation: str | None = None
    is_active: bool | None = None
    options: list[QuestionOptionCreate] | None = None
    accepted_answers: list[AcceptedAnswerCreate] | None = None
    media: list[QuestionMediaCreate] | None = None

def validate_question_data(data):
    if not data.question_text.strip():
        raise HTTPException(
            status_code=400,
            detail="nội dung câu hỏi không được để trống"
        )

    if data.question_type == "multiple_choice":
        if len(data.options) < 2:
            raise HTTPException(
                status_code=400,
                detail="câu hỏi trắc nghiệm phải có ít nhất 2 lựa chọn"
            )

        correct_count = sum(
            1 for option in data.options if option.is_correct
        )

        if correct_count != 1:
            raise HTTPException(
                status_code=400,
                detail="câu hỏi trắc nghiệm phải có đúng 1 đáp án đúng"
            )

        if data.accepted_answers:
            raise HTTPException(
                status_code=400,
                detail="câu hỏi trắc nghiệm không dùng accepted_answers"
            )

    elif data.question_type == "true_false":
        if len(data.options) != 4:
            raise HTTPException(
                status_code=400,
                detail="Câu hỏi đúng/sai phải có chính xác 4 ý"
        )

    if data.accepted_answers:
        raise HTTPException(
            status_code=400,
            detail="Câu hỏi đúng/sai không dùng accepted_answers"
        )

    sort_orders = [option.sort_order for option in data.options]
    if len(set(sort_orders)) != 4:
        raise HTTPException(
            status_code=400,
            detail="Thứ tự 4 ý không được trùng nhau"
        )

    elif data.question_type == "short_answer":
        if not data.accepted_answers:
            raise HTTPException(
                status_code=400,
                detail="câu hỏi trả lời ngắn phải có ít nhất 1 đáp án được chấp nhận"
            )

        if data.options:
            raise HTTPException(
                status_code=400,
                detail="câu hỏi trả lời ngắn không dùng options"
            )

@app.post("/api/questions")
def create_question(data: QuestionCreate):
    validate_question_data(data)

    conn = get_db()
    created_at = get_utc_time()
    try:
        cursor = conn.execute("""
        INSERT INTO questions (
        subject_id,
        grade_id,
        topic_id,
        question_text,
        question_type,
        difficulty,
        lesson_id,
        created_by,
        explanation,
        created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
        data.subject_id,
        data.grade_id,
        data.topic_id,
        data.question_text,
        data.question_type,
        data.difficulty,
        data.lesson_id,
        data.created_by,
        data.explanation,
        created_at
        ))

        question_id = cursor.lastrowid
            
        for option in data.options: 
            conn.execute(
                """
                INSERT INTO question_options (
                question_id,
                option_key,
                option_text,
                is_correct,
                sort_order
                )
                VALUES(?, ?, ?, ?, ?)
                """, (
                    question_id,
                    option.option_key,
                    option.option_text,
                    option.is_correct,
                    option.sort_order
                    )
                )

        for accepted_answer in data.accepted_answers:
            conn.execute(
                """
                INSERT INTO question_accepted_answers (
                question_id,
                answer_text,
                is_case_sensitive
                )
                VALUES(?, ?, ?)
                """, (
                    question_id,
                    accepted_answer.answer_text,
                    accepted_answer.is_case_sensitive
                )
            )

        for media in data.media:
            conn.execute(
                """
                INSERT INTO question_media (
                question_id,
                media_type,
                file_path,
                sort_order
                )
                VALUES(?, ?, ?, ?)
                """, (
                question_id,
                media.media_type,
                media.file_path,
                media.sort_order
                )
            )
        
        conn.commit()

        
        return {
            "status": "ok",
            "message": "thêm câu hỏi thành công",
            "question_id": cursor.lastrowid
        }

    except Exception as e:
        conn.rollback()
        raise e
    
    finally:
        conn.close()

@app.put("/api/questions/{question_id}")
def update_question(question_id: int, data: QuestionUpdate):
    conn = get_db()
    
    updated_at = get_utc_time()

    try:
        cursor = conn.execute(
            "SELECT question_id FROM questions WHERE question_id = ?",
            (question_id,)
        )

        if cursor.fetchone() is None:
            raise HTTPException(
                status_code=404,
                detail="Không tìm thấy câu hỏi"
            )

        conn.execute(
            """
            UPDATE questions
            SET
                subject_id = ?,
                grade_id = ?,
                topic_id = ?,
                lesson_id = ?,
                question_type = ?,
                difficulty = ?,
                question_text = ?,
                explanation = ?,
                is_active = ?,
                updated_at = ?
            WHERE question_id = ?
            """,
            (
                data.subject_id,
                data.grade_id,
                data.topic_id,
                data.lesson_id,
                data.question_type,
                data.difficulty,
                data.question_text,
                data.explanation,
                data.is_active,
                updated_at,
                question_id
            )
        )
        conn.execute(
            "DELETE FROM question_options WHERE question_id = ?",
            (question_id,)
        )

        conn.execute(
            "DELETE FROM question_accepted_answers WHERE question_id = ?",
            (question_id,)
        )

        conn.execute(
            "DELETE FROM question_media WHERE question_id = ?",
            (question_id,)
        )

        for option in data.options:
            conn.execute(
                """
                INSERT INTO question_options (
                    question_id,
                    option_key,
                    option_text,
                    is_correct,
                    sort_order
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    question_id,
                    option.option_key,
                    option.option_text,
                    option.is_correct,
                    option.sort_order
                )
            )

        for answer in data.accepted_answers:
            conn.execute(
                """
                INSERT INTO question_accepted_answers (
                question_id,
                answer_text,
                is_case_sensitive
                )
                VALUES (?, ?, ?)
                """,
                (
                    question_id,
                    answer.answer_text,
                    answer.is_case_sensitive
                )
            )

        for media in data.media:
            conn.execute(
                """
                INSERT INTO question_media (
                    question_id,
                    media_type,
                    file_path,
                    sort_order
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    question_id,
                    media.media_type,
                    media.file_path,
                    media.sort_order
                )
            )

        conn.commit()

        return {
                    "status": "ok",
                    "message": "Cập nhật câu hỏi thành công",
                    "question_id": question_id
                }
    
    except HTTPException:
        conn.rollback()
        raise

    except Exception as e:
        conn.rollback()
        print("LỖI PUT:", repr(e), flush=True)
        raise HTTPException(
            status_code=500,
            detail="Có lỗi xảy ra khi cập nhật câu hỏi"
        )

    finally:
        conn.close()

@app.patch("/api/questions/{question_id}")
def patch_question(question_id: int, data:QuestionPatch):
    conn = get_db()

    try:
        cursor = conn.execute(
                    "SELECT question_id FROM questions WHERE question_id = ?",
                    (question_id,)
                )
    
        if cursor.fetchone() is None:
            raise HTTPException(
                status_code=404,
                detail="Không tìm thấy câu hỏi"
            )

        fields_to_update = data.model_fields_set
        update_data = {}
        update_options = "options" in fields_to_update
        update_answers = "accepted_answers" in fields_to_update
        update_media = "media" in fields_to_update

        if 'question_text' in fields_to_update:
            update_data["question_text"] = data.question_text
        if 'difficulty' in fields_to_update:
            update_data["difficulty"] = data.difficulty
        if 'lesson_id' in fields_to_update:
            update_data["lesson_id"] = data.lesson_id
        if 'explanation' in fields_to_update:
            update_data["explanation"] = data.explanation
        if 'subject_id' in fields_to_update:
            update_data["subject_id"] = data.subject_id
        if 'grade_id' in fields_to_update:
            update_data["grade_id"] = data.grade_id
        if 'topic_id' in fields_to_update:
            update_data["topic_id"] = data.topic_id
        if 'is_active' in fields_to_update:
            update_data["is_active"] = data.is_active

        print("các trg cần cập nhật: ", update_data, flush=True)

        if not update_data and not update_options and not update_answers and not update_media:
            raise HTTPException(
                status_code=400,
                detail="không có trường nào được gửi để cập nhật"
            )

        if update_data:
            set_clause = ", ".join(
                f"{field} = ?" for field in update_data
            )
            values = list(update_data.values())
            values.append(question_id)

            sql = f"""
                UPDATE questions
                SET {set_clause}
                WHERE question_id = ?
            """
            conn.execute(sql, values)
        
        if update_options:
            conn.execute(
                "DELETE FROM question_options WHERE question_id = ?",
                (question_id,)
            )

            for option in data.options:
                conn.execute(
                    """
                    INSERT INTO question_options (
                        question_id,
                        option_key,
                        option_text,
                        is_correct,
                        sort_order
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        question_id,
                        option.option_key,
                        option.option_text,
                        option.is_correct,
                        option.sort_order
                    )
                )

            
        if update_answers:
            conn.execute(
                "DELETE FROM question_accepted_answers WHERE question_id = ?",
                (question_id,)
            )

            for answer in data.accepted_answers:
                conn.execute(
                    """
                    INSERT INTO question_accepted_answers (
                        question_id, answer_text, is_case_sensitive
                    ) VALUES (?, ?, ?)
                    """,
                    (
                        question_id,
                        answer.answer_text,
                        answer.is_case_sensitive
                    )
                )

        
        if update_media:
            conn.execute(
                "DELETE FROM question_media WHERE question_id = ?",
                (question_id,)
            )

            for media in data.media:
                conn.execute(
                    """
                    INSERT INTO question_media (
                        question_id, media_type, file_path, sort_order
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (
                        question_id,
                        media.media_type,
                        media.file_path,
                        media.sort_order
                    )
                )


        conn.commit()

        return {
            "status": "ok",
            "message": "cập nhật câu hỏi thành công",
            "question_id": question_id,
            "updated_fields": list(update_data.keys())
        }
    except HTTPException:
        conn.rollback()
        raise

    except Exception as e:
        conn.rollback()
        print("LỖI PATCH:", repr(e), flush=True)
        raise HTTPException(
            status_code=500,
            detail="Có lỗi xảy ra khi cập nhật câu hỏi"
        )
    finally:
        conn.close()

@app.delete("/api/questions/{question_id}")
def delete_question(question_id: int):
    conn = get_db()

    try:
        cursor = conn.execute(
            "DELETE FROM questions WHERE question_id = ?",
            (question_id,)
        )

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="Không tìm thấy câu hỏi cần xóa"
            )

        conn.commit()

        return {
            "status": "ok",
            "message": "Xóa câu hỏi thành công",
            "question_id": question_id
        }

    except sqlite3.IntegrityError:
        conn.rollback()
        raise HTTPException(
            status_code=409,
            detail="Không thể xóa câu hỏi vì dữ liệu đang được tham chiếu ở bảng khác"
        )

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()

class StudentAnswerCreate(BaseModel):
    session_student_id:int 
    question_id:int
    answer_text: str

class StudentSubmit(BaseModel):
    session_student_id: int

def check_student_can_answer(conn, session_student_id, question_id):
    row = conn.execute(
        """
        SELECT
        ss.status AS student_status,
            ss.started_at,
            ss.submitted_at,
            es.status AS session_status,
            es.start_time,
            es.end_time,
            e.duration_minutes AS duration_minutes,
            evq.score AS question_score,
            q.question_type,
            q.is_active
        FROM session_students ss
        JOIN exam_sessions es
            ON es.session_id = ss.session_id
        JOIN exams e
            ON e.exam_id = es.exam_id
        JOIN exam_version_questions evq
            ON evq.version_id = es.version_id
        JOIN questions q
            ON q.question_id = evq.question_id
        WHERE ss.session_student_id = ?
          AND evq.question_id = ?
        """,(session_student_id, question_id)).fetchone()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="không tìm thấy học sinh hoặc câu hỏi không thuộc đề này"
        )

    if row["student_status"] != "in_progress":
        raise HTTPException(
            status_code=403,
            detail="học sinh không ở trạng thái đang làm bài"
        )

    if row["submitted_at"] is not None:
        raise HTTPException(
            status_code=403,
            detail="bài thi đã được nộp, không thể sửa"
        )

    if row["session_status"] != "ongoing":
        raise HTTPException(
            status_code=403,
            detail="phiên thi chưa thể vào làm bài"
        )

    if not row["started_at"]:
        raise HTTPException(
            status_code=400,
            detail="phiên thi chưa có thời gian mở"
        )

    try:
        started_at = datetime.strptime(
            row["started_at"],
            "%Y-%m-%d %H:%M:%S"
        ).replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)

        deadline = started_at + timedelta(
            minutes=row["duration_minutes"]
        )

        if row["end_time"]:
            session_end = datetime.strptime(
                row["end_time"],
                "%Y-%m-%d %H:%M:%S"
            ).replace(tzinfo=timezone.utc)

            deadline = min(deadline, session_end)

    except (ValueError, TypeError):
        raise HTTPException(
            status_code=500,
            detail="Dữ liệu thời gian không hợp lệ"
        )

    if now >= deadline:
        raise HTTPException(
            status_code=403,
            detail="Đã hết thời gian làm bài"
        )


    if row["is_active"] != 1:
        raise HTTPException(
            status_code=403,
            detail="câu hỏi hiện không hoạt động"
        )
    
    return row

def check_student_can_submit(conn, session_student_id):
    row = conn.execute(
        """
        SELECT
            ss.status AS student_status,
            ss.started_at,
            ss.submitted_at,
            es.status AS session_status,
            es.end_time,
            e.duration_minutes
        FROM session_students ss
        JOIN exam_sessions es
            ON es.session_id = ss.session_id
        JOIN exams e
            ON e.exam_id = es.exam_id
        WHERE ss.session_student_id = ?
        """,
        (session_student_id,)
    ).fetchone()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy học sinh trong phiên thi"
        )

    if row["student_status"] != "in_progress":
        raise HTTPException(
            status_code=403,
            detail="Học sinh không ở trạng thái đang làm bài"
        )

    if row["submitted_at"] is not None:
        raise HTTPException(
            status_code=403,
            detail="Bài thi đã được nộp trước đó"
        )

    if row["session_status"] != "ongoing":
        raise HTTPException(
            status_code=403,
            detail="Phiên thi không còn hoạt động"
        )

    if not row["started_at"]:
        raise HTTPException(
            status_code=400,
            detail="Học sinh chưa bắt đầu làm bài"
        )

    try:
        started_at = datetime.strptime(
            row["started_at"],
            "%Y-%m-%d %H:%M:%S"
        ).replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)

        deadline = started_at + timedelta(
            minutes=row["duration_minutes"]
        )

        if row["end_time"]:
            session_end = datetime.strptime(
                row["end_time"],
                "%Y-%m-%d %H:%M:%S"
            ).replace(tzinfo=timezone.utc)

            deadline = min(deadline, session_end)

    except (ValueError, TypeError):
        raise HTTPException(
            status_code=500,
            detail="Dữ liệu thời gian không hợp lệ"
        )

    return row, now >= deadline

@app.post("/api/student/answers")
def save_student_answer(data: StudentAnswerCreate):
    conn = get_db()

    try:
        row = check_student_can_answer(
            conn,
            data.session_student_id,
            data.question_id
        )

        
        answer_text = data.answer_text.strip()

        if not answer_text:
            raise HTTPException(
                status_code=400,
                detail="Đáp án không được để trống"
            )

        question_type = row["question_type"]
        question_score = row["question_score"]

        is_correct = None
        score = 0.0

        if question_type == "multiple_choice":
            option = conn.execute("""
                SELECT is_correct
                FROM question_options
                WHERE question_id = ? AND option_key = ?
            """, (
                data.question_id,
                answer_text
            )).fetchone()

            if option is None:
                raise HTTPException(
                    status_code=400,
                    detail="Lựa chọn không hợp lệ"
                )

            is_correct = int(option["is_correct"] == 1)
            score = question_score if is_correct else 0.0
    
        elif question_type == "true_false":
            try:
                student_answers = json.loads(answer_text)
            except (json.JSONDecodeError, TypeError):
                raise HTTPException(
                    status_code=400,
                    detail="Đáp án đúng/sai phải có định dạng JSON"
                )

            if (
                not isinstance(student_answers, dict)
                or set(student_answers.keys()) != {"A", "B", "C", "D"}
                or any(
                    type(student_answers[key]) is not bool
                    for key in ("A", "B", "C", "D")
                )
            ):
                raise HTTPException(
                    status_code=400,
                    detail="Cần trả lời đủ bốn mệnh đề A, B, C, D bằng true hoặc false"
                )

            options = conn.execute("""
                SELECT option_key, is_correct
                FROM question_options
                WHERE question_id = ?
            """, (data.question_id,)).fetchall()

            correct_map = {
                item["option_key"]: bool(item["is_correct"])
                for item in options
            }

            if set(correct_map.keys()) != {"A", "B", "C", "D"}:
                raise HTTPException(
                    status_code=500,
                    detail="Dữ liệu đáp án đúng/sai của câu hỏi không hợp lệ"
                )

            correct_count = sum(
                student_answers[key] == correct_map[key]
                for key in ("A", "B", "C", "D")
            )

            fractions = {
                0: 0.0,
                1: 0.1,
                2: 0.25,
                3: 0.5,
                4: 1.0
            }

            is_correct = int(correct_count == 4)
            score = question_score * fractions[correct_count]

            answer_text = json.dumps(
                student_answers,
                sort_keys=True,
                separators=(",", ":")
            )

        elif question_type == "short_answer":
            accepted_answers = conn.execute("""
                SELECT answer_text, is_case_sensitive
                FROM question_accepted_answers
                WHERE question_id = ?
            """, (data.question_id,)).fetchall()

            if not accepted_answers:
                raise HTTPException(
                    status_code=500,
                    detail="Câu hỏi chưa có đáp án được chấp nhận"
                )

            is_correct = int(any(
                answer_text == item["answer_text"]
                if item["is_case_sensitive"]
                else answer_text.casefold()
                     == item["answer_text"].strip().casefold()
                for item in accepted_answers
            ))

            score = question_score if is_correct else 0.0

        else:
            raise HTTPException(
                status_code=400,
                detail="Loại câu hỏi không được hỗ trợ"
            )


        answered_at = get_utc_time()

        conn.execute(
            """
            INSERT INTO answers (
                session_student_id,
                question_id,
                answer_text,
                is_correct,
                score,
                answered_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ? ,?)
            ON CONFLICT(session_student_id, question_id)
            DO UPDATE SET
                answer_text = excluded.answer_text,
                updated_at = excluded.updated_at,
                is_correct = excluded.is_correct,
                score = excluded.score
        """, (
            (
                data.session_student_id,
                data.question_id,
                answer_text,
                is_correct,
                score,
                answered_at,
                answered_at
)
        ))

        conn.commit()

        return {
            "status": "ok",
            "message": "Lưu đáp án thành công",
            "question_id": data.question_id
        }

    except HTTPException:
        conn.rollback()
        raise

    except Exception as e:
        conn.rollback()
        print("LỖI LƯU ĐÁP ÁN:", repr(e), flush=True)
        raise HTTPException(
            status_code=500,
            detail="Có lỗi xảy ra khi lưu đáp án"
        )

    finally:
        conn.close()

@app.post("/api/student/submit")
def submit_student_exam(data: StudentSubmit):
    conn = get_db()

    try:
        row, is_time_up = check_student_can_submit(
            conn,
            data.session_student_id
        )

        submitted_at = get_utc_time()

        
        cursor = conn.execute(
            """
            UPDATE session_students
            SET
                status = 'submitted',
                submitted_at = ?
            WHERE session_student_id = ?
              AND status = 'in_progress'
              AND submitted_at IS NULL
            """,
            (submitted_at, data.session_student_id)
        )

        if cursor.rowcount != 1:
            conn.rollback()
            raise HTTPException(
                status_code=409,
                detail="Không thể cập nhật trạng thái nộp bài"
            )

        conn.commit()

        return{
            "status": "ok",
            "message": (
                "đã hết giờ, hệ thống đã chốt bài thi"
                if is_time_up
                else "nộp bài thành công"
            ),
            "session_student_id": data.session_student_id,
            "student_status": "submitted",
            "submitted_at": submitted_at,
            "time_up": is_time_up
        }

    except HTTPException:
        conn.rollback()
        raise

    except Exception as e:
        conn.rollback()
        print("LỖI NỘP BÀI: ", repr(e), flush=True)
        raise HTTPException(
            status_code=500,
            detail="có lỗi xảy ra khi nộp bài"
        )

    finally:
        conn.close()

@app.get("/api/users")
def get_users():
    conn = get_db()

    try:
        rows = conn.execute(
            """
            SELECT
            user_id,
            username,
            full_name,
            role,
            is_active,
            created_at
            FROM users
            ORDER BY user_id
            """).fetchall()

        return {
            "status": "ok",
            "count": len(rows),
            "users": [dict(row) for row in rows]
        }

    finally:
        conn.close()

@app.get("/api/users/{user_id}")
def get_user_detail(user_id: int):
    conn = get_db()

    try:
        row = conn.execute(
            """
            SELECT
            user_id,
            username,
            full_name,
            role,
            is_active,
            created_at
            FROM users
            WHERE user_id = ?
            """, (user_id,)).fetchone()

        if row is None:
            raise HTTPException(
                status_code=404,
                detail="không tìm thấy ng dùng"
            )

        return {
            "status": "ok",
            "user": dict(row)
        }

    finally:
        conn.close()

@app.post("/api/users")
def create_user(user: UserCreate):
    if user.role != "teacher":
        raise HTTPException(
            status_code=400,
            detail="chỉ tạo được tài khoản giáo viên"
        )
    hashed_password = password_hash.hash(user.password)
    conn = get_db()

    try:
        existing_user = conn.execute(
            "SELECT user_id FROM users WHERE username = ?",
            (user.username,)
        ).fetchone()

        if existing_user is not None:
            raise HTTPException(
                status_code=409,
                detail="Tên đăng nhập đã tồn tại"
            )

        # Thêm tài khoản vào database
        cursor = conn.execute(
            """
            INSERT INTO users (
                username,
                password_hash,
                full_name,
                role
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                user.username,
                hashed_password,
                user.full_name,
                user.role
            )
        )

        conn.commit()

        return {
            "status": "ok",
            "message": "Tạo tài khoản thành công",
            "user_id": cursor.lastrowid,
            "username": user.username
        }

    except HTTPException:
        raise

    except Exception:
        conn.rollback()
        raise HTTPException(
            status_code=500,
            detail="Có lỗi xảy ra khi tạo tài khoản"
        )

    finally:
        conn.close()

@app.post("/api/login")
def logion(user: UserLogin):
    conn = get_db()

    try:
        row = conn.execute(
            """
            SELECT
            user_id,
            username,
            password_hash,
            full_name,
            role,
            is_active
            FROM users
            WHERE username = ?
            """, (user.username,)).fetchone()
        if row is None or not password_hash.verify(
            user.password,
            row["password_hash"]
        ):
            raise HTTPException(
                status_code=401,
                detail="tên đăng nhập hoặc mật khẩu không đúng"
            )

        if row["is_active"] != 1:
            raise HTTPException(
                status_code=403,
                detail="tài khoản đã bị vô hiệu hóa"
            )

        return {
            "status": "ok",
            "message": "Đăng nhập thành công",
            "user": {
                "user_id": row["user_id"],
                "username": row["username"],
                "full_name": row["full_name"],
                "role": row["role"]
            }
        }
    finally:
        conn.close()