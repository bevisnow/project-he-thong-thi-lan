from pathlib import Path
import sqlite3
import json

from fastapi import HTTPException
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Literal
from pydantic import BaseModel, Field
from fastapi import FastAPI
from fastapi.responses import Response

# Đường dẫn database tính từ vị trí file main.py
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "data-test.db"

app = FastAPI(title="Hệ thống thi offline LAN")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def get_vietnam_time():
    return datetime.now(
        ZoneInfo("Asia/Bangkok")
    ).strftime("%Y-%m-%d %H:%M:%S")

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
        
        return {
            "status": "ok",
            "question": dict(row),
            "options": [dict(option) for option in options],
            "accepted_answers": [dict(answer) for answer in accepted_answers],
            "media": [dict(item) for item in media]
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
    created_at = get_vietnam_time()
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
    
    updated_at = get_vietnam_time()

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

