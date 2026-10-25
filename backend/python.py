import sqlite3
import json
import asyncio
import traceback
import jwt
import os
import secrets
import time
from collections import deque
from threading import Lock

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pwdlib import PasswordHash
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import HTTPException
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import Literal
from pydantic import BaseModel, Field
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi import Depends

password_hash = PasswordHash.recommended()
bearer_scheme = HTTPBearer()


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=100)
    role: str = "teacher"


class UserLogin(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)


class SubjectCreate(BaseModel):
    subject_name: str = Field(min_length=1, max_length=100)


class SubjectUpdate(BaseModel):
    subject_name: str = Field(min_length=1, max_length=100)


class GradeCreate(BaseModel):
    grade_name: str = Field(min_length=1, max_length=100)


class GradeUpdate(BaseModel):
    grade_name: str = Field(min_length=1, max_length=100)


class TopicCreate(BaseModel):
    subject_id: int
    grade_id: int
    topic_name: str = Field(min_length=1, max_length=100)


class TopicUpdate(BaseModel):
    subject_id: int
    grade_id: int
    topic_name: str = Field(min_length=1, max_length=100)


class LessonCreate(BaseModel):
    topic_id: int
    lesson_name: str = Field(min_length=1, max_length=100)
    lesson_order: int = Field(default=1, gt=0)


class LessonUpdate(BaseModel):
    topic_id: int
    lesson_name: str = Field(min_length=1, max_length=100)
    lesson_order: int = Field(gt=0)


class ClassUpdate(BaseModel):
    class_name: str = Field(min_length=1, max_length=50)
    grade_id: int
    school_year: str | None = Field(default=None, max_length=20)


SECRET_KEY = os.environ.get("EXAM_JWT_SECRET", "")
if len(SECRET_KEY) < 32:
    raise RuntimeError("EXAM_JWT_SECRET must be set to a random value of at least 32 characters")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "data.db"


def ensure_student_date_of_birth_column():
    if not DB_PATH.is_file():
        return
    conn = sqlite3.connect(DB_PATH)
    try:
        has_students = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='students'"
        ).fetchone()
        if has_students and "date_of_birth" not in {
            row[1] for row in conn.execute("PRAGMA table_info(students)")
        }:
            conn.execute("ALTER TABLE students ADD COLUMN date_of_birth TEXT")
            conn.commit()
    finally:
        conn.close()


def ensure_exam_settings_columns():
    if not DB_PATH.is_file():
        return
    conn = sqlite3.connect(DB_PATH)
    try:
        for table, columns in {
            "exams": {
                "supervising_authority": "TEXT NOT NULL DEFAULT ''",
                "school_name": "TEXT NOT NULL DEFAULT ''",
            },
            "exam_sessions": {
                "paper_code_prefix": "TEXT NOT NULL DEFAULT ''",
                "paper_code_length": "INTEGER NOT NULL DEFAULT 3",
                "paper_variant_count": "INTEGER NOT NULL DEFAULT 1",
            },
        }.items():
            exists = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
            ).fetchone()
            if not exists:
                continue
            present = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
            for name, definition in columns.items():
                if name not in present:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")
        conn.commit()
    finally:
        conn.close()


def ensure_student_room_login_attempts():
    if not DB_PATH.is_file():
        return
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS student_room_login_attempts (
                session_student_id INTEGER PRIMARY KEY,
                failed_attempts INTEGER NOT NULL DEFAULT 0,
                locked_until TEXT,
                FOREIGN KEY(session_student_id) REFERENCES session_students(session_student_id) ON DELETE CASCADE
            )
        """)
        conn.commit()
    finally:
        conn.close()


def ensure_teacher_login_columns():
    if not DB_PATH.is_file():
        return

    conn = sqlite3.connect(DB_PATH)
    try:
        users_table = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='users'"
        ).fetchone()
        if not users_table:
            return

        columns = {row[1] for row in conn.execute("PRAGMA table_info(users)")}
        if "failed_login_count" not in columns:
            conn.execute(
                "ALTER TABLE users ADD COLUMN failed_login_count INTEGER NOT NULL DEFAULT 0"
            )
        if "locked_at" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN locked_at TEXT")
        conn.commit()
    finally:
        conn.close()


def ensure_class_owner_column():
    if not DB_PATH.is_file():
        return
    conn = sqlite3.connect(DB_PATH)
    try:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(classes)")}
        if columns and "created_by" not in columns:
            conn.execute(
                "ALTER TABLE classes ADD COLUMN created_by INTEGER REFERENCES users(user_id)"
            )
            conn.commit()
    finally:
        conn.close()


def ensure_question_visibility_column():
    if not DB_PATH.is_file():
        return
    conn = sqlite3.connect(DB_PATH)
    try:
        exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='questions'"
        ).fetchone()
        if exists and "is_public" not in {
            row[1] for row in conn.execute("PRAGMA table_info(questions)")
        }:
            conn.execute(
                "ALTER TABLE questions ADD COLUMN is_public INTEGER NOT NULL DEFAULT 0 CHECK(is_public IN (0, 1))"
            )
            conn.commit()
    finally:
        conn.close()


def rotate_short_room_codes():
    if not DB_PATH.is_file():
        return
    conn = sqlite3.connect(DB_PATH)
    try:
        if not conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='exam_sessions'"
        ).fetchone():
            return
        session_ids = conn.execute(
            "SELECT session_id FROM exam_sessions "
            "WHERE status IN ('scheduled','ongoing') AND (access_code IS NULL OR length(access_code)<16)"
        ).fetchall()
        for (session_id,) in session_ids:
            conn.execute(
                "UPDATE exam_sessions SET access_code=? WHERE session_id=?",
                (secrets.token_hex(8).upper(), session_id),
            )
        conn.commit()
    finally:
        conn.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_student_date_of_birth_column()
    ensure_exam_settings_columns()
    ensure_student_room_login_attempts()
    ensure_teacher_login_columns()
    ensure_class_owner_column()
    ensure_question_visibility_column()
    rotate_short_room_codes()
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


app = FastAPI(title="Hệ thống thi offline", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)

_RATE_LIMITS = {
    "login": (10, 60),
    "user_create": (5, 60),
    "student_join": (120, 60),
    "upload": (6, 60),
    "exam_build": (10, 60),
}
_rate_limit_hits = {}
_rate_limit_lock = Lock()
_rate_limit_checks = 0


def _rate_limit_bucket(path: str):
    if path == "/api/login":
        return "login"
    if path == "/api/users":
        return "user_create"
    if path == "/api/exam/join":
        return "student_join"
    if path.startswith("/api/exams/") and path.endswith(("/generate", "/swap")):
        return "exam_build"
    if path.endswith(("/questions/media", "/questions/import", "/students/import")):
        return "upload"
    return None

@app.middleware("http")
async def add_security_headers(request, call_next):
    path = request.url.path
    bucket = _rate_limit_bucket(path) if request.method == "POST" else None
    limited = False
    retry_after = 0
    if bucket:
        global _rate_limit_checks
        limit, window = _RATE_LIMITS[bucket]
        # Use the ASGI peer address; do not trust a client-supplied X-Forwarded-For header.
        client_ip = request.client.host if request.client else "unknown"
        key = (client_ip, bucket)
        now = time.monotonic()
        with _rate_limit_lock:
            hits = _rate_limit_hits.get(key)
            if hits is None:
                # shortcut: cap process-local IP buckets at 4,096; use a shared limiter when scaling workers.
                if len(_rate_limit_hits) >= 4096:
                    _rate_limit_hits.pop(next(iter(_rate_limit_hits)))
                hits = _rate_limit_hits[key] = deque()
            while hits and now - hits[0] >= window:
                hits.popleft()
            if len(hits) >= limit:
                limited = True
                retry_after = max(1, int(window - (now - hits[0])))
            else:
                hits.append(now)
            _rate_limit_checks += 1
            if _rate_limit_checks % 256 == 0:
                stale = [k for k, q in _rate_limit_hits.items() if not q or now - q[-1] >= window]
                for stale_key in stale:
                    _rate_limit_hits.pop(stale_key, None)

    upload_limit = (
        5 * 1024 * 1024 + 64 * 1024
        if path.endswith("/questions/media") or path.endswith("/students/import")
        else 10 * 1024 * 1024 + 64 * 1024
        if path.endswith("/questions/import")
        else None
    )
    response = None
    if limited:
        response = JSONResponse(
            status_code=429,
            content={"detail": "Bạn thao tác quá nhanh. Vui lòng thử lại sau."},
            headers={"Retry-After": str(retry_after)},
        )
    elif request.method == "POST" and upload_limit is not None:
        content_length = request.headers.get("content-length")
        if content_length is None or not content_length.isdigit():
            response = JSONResponse(status_code=411, content={"detail": "Upload cần Content-Length hợp lệ"})
        elif int(content_length) > upload_limit:
            response = JSONResponse(status_code=413, content={"detail": "Tệp tải lên vượt quá giới hạn cho phép"})

    if response is None:
        response = await call_next(request)
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob:; media-src 'self' blob:; connect-src 'self'; "
        "font-src 'self' data:; object-src 'none'; base-uri 'self'; "
        "form-action 'self'; frame-ancestors 'none'",
    )
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    if request.url.scheme == "https":
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000")
    return response


BASE_DIR = Path(__file__).resolve().parent
MEDIA_DIR = BASE_DIR / "storage" / "question_media"
FRONTEND_DIR = BASE_DIR.parent / "frontend"

app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_access_token(data: dict):
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=401,
        detail="Không thể xác thực thông tin đăng nhập",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        user_id = payload.get("sub")

        if user_id is None:
            raise credentials_exception

    except jwt.InvalidTokenError:
        raise credentials_exception

    conn = get_db()

    try:
        row = conn.execute(
            """
            SELECT user_id, username, full_name, role, is_active
            FROM users
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

        if row is None or row["is_active"] != 1:
            raise credentials_exception

        return dict(row)

    finally:
        conn.close()


def require_admin(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Chỉ quản trị viên được phép thực hiện thao tác này")
    return current_user



def read_upload_limited(upload, max_bytes: int, label: str):
    data = upload.file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(413, f"{label} vượt quá giới hạn cho phép")
    return data


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

            deadline = started_at + timedelta(minutes=row["duration_minutes"])

            if row["end_time"]:
                session_end = datetime.strptime(
                    row["end_time"], "%Y-%m-%d %H:%M:%S"
                ).replace(tzinfo=timezone.utc)

                deadline = min(deadline, session_end)

            if now >= deadline:
                expired_ids.append(row["session_student_id"])

        for student_id in expired_ids:
            conn.execute(
                """
                UPDATE session_students
                SET status = 'submitted',
                    submitted_at = ?
                WHERE session_student_id = ?
                  AND status = 'in_progress'
                  AND submitted_at IS NULL
            """,
                (now_text, student_id),
            )

        join_cutoff = (now - timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S")
        expired_sessions = conn.execute(
            """
            SELECT session_id
            FROM exam_sessions
            WHERE status='ongoing'
              AND end_time IS NOT NULL
              AND end_time<=?
            """,
            (now_text,),
        ).fetchall()

        conn.execute(
            """
            UPDATE session_students
            SET status='absent'
            WHERE status='registered'
              AND session_id IN (
                  SELECT session_id FROM exam_sessions
                  WHERE status='ongoing'
                    AND start_time IS NOT NULL
                    AND start_time<=?
              )
            """,
            (join_cutoff,),
        )

        for (session_id,) in expired_sessions:
            conn.execute(
                """
                UPDATE session_students
                SET status='absent'
                WHERE session_id=? AND status='registered'
                """,
                (session_id,),
            )

        conn.execute(
            """
            UPDATE exam_sessions
            SET status='completed'
            WHERE status='ongoing'
              AND end_time IS NOT NULL
              AND end_time<=?
            """,
            (now_text,),
        )

        conn.commit()

        if expired_ids or expired_sessions:
            print(
                f"Đã tự động chốt {len(expired_ids)} bài và "
                f"{len(expired_sessions)} phòng thi hết giờ.",
                flush=True,
            )

    except Exception as e:
        conn.rollback()
        traceback.print_exc()

    finally:
        conn.close()


@app.get("/")
def home():
    return FileResponse(
        FRONTEND_DIR / "index.html", headers={"Cache-Control": "no-store"}
    )


@app.get("/api/db-check", dependencies=[Depends(require_admin)])
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


@app.get("/api/users", dependencies=[Depends(require_admin)])
def get_users():
    conn = get_db()

    try:
        rows = conn.execute("""
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
            "users": [dict(row) for row in rows],
        }

    finally:
        conn.close()


@app.get("/api/users/{user_id}", dependencies=[Depends(get_current_user)])
def get_user_detail(user_id: int, current_user: dict = Depends(get_current_user)):

    if current_user["role"] != "admin" and current_user["user_id"] != user_id:
        raise HTTPException(
            status_code=403, detail="Bạn không có quyền xem thông tin người dùng này"
        )

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
            """,
            (user_id,),
        ).fetchone()

        if row is None:
            raise HTTPException(status_code=404, detail="không tìm thấy ng dùng")

        return {"status": "ok", "user": dict(row)}

    finally:
        conn.close()


@app.post("/api/users", dependencies=[Depends(require_admin)])
def create_user(user: UserCreate):
    if user.role != "teacher":
        raise HTTPException(status_code=400, detail="chỉ tạo được tài khoản giáo viên")
    hashed_password = password_hash.hash(user.password)
    conn = get_db()

    try:
        existing_user = conn.execute(
            "SELECT user_id FROM users WHERE username = ?", (user.username,)
        ).fetchone()

        if existing_user is not None:
            raise HTTPException(status_code=409, detail="Tên đăng nhập đã tồn tại")

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
            (user.username, hashed_password, user.full_name, user.role),
        )

        conn.commit()

        return {
            "status": "ok",
            "message": "Tạo tài khoản thành công",
            "user_id": cursor.lastrowid,
            "username": user.username,
        }

    except HTTPException:
        raise

    except Exception:
        traceback.print_exc()

        conn.rollback()
        raise HTTPException(status_code=500, detail="Có lỗi xảy ra khi tạo tài khoản")

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
            is_active,
            failed_login_count,
            locked_at
            FROM users
            WHERE username = ?
            """,
            (user.username,),
        ).fetchone()
        if row and row["locked_at"]:
            locked_at = datetime.strptime(
                row["locked_at"], "%Y-%m-%d %H:%M:%S"
            ).replace(tzinfo=timezone.utc)
            unlock_at = locked_at + timedelta(minutes=15)
            now = datetime.now(timezone.utc)
            if now < unlock_at:
                minutes_left = max(1, int((unlock_at - now).total_seconds() // 60) + 1)
                raise HTTPException(
                    status_code=423,
                    detail=(
                        "Đăng nhập sai quá 5 lần. "
                        f"Thử lại sau khoảng {minutes_left} phút."
                    ),
                )

            conn.execute(
                "UPDATE users SET failed_login_count=0, locked_at=NULL, "
                "is_active=1 WHERE user_id=?",
                (row["user_id"],),
            )

        if row is None or not password_hash.verify(user.password, row["password_hash"]):
            if row and row["role"] != "admin":
                conn.execute(
                    "UPDATE users SET failed_login_count=failed_login_count+1 "
                    "WHERE user_id=?",
                    (row["user_id"],),
                )
                failed_attempts = conn.execute(
                    "SELECT failed_login_count FROM users WHERE user_id=?",
                    (row["user_id"],),
                ).fetchone()[0]

                if failed_attempts >= 5:
                    conn.execute(
                        "UPDATE users SET locked_at=? WHERE user_id=?",
                        (get_utc_time(), row["user_id"]),
                    )
                    conn.commit()
                    raise HTTPException(
                        status_code=423,
                        detail="Đăng nhập sai quá 5 lần. Tài khoản tạm khóa 15 phút.",
                    )
                conn.commit()
            raise HTTPException(
                status_code=401, detail="tên đăng nhập hoặc mật khẩu không đúng"
            )

        if row["is_active"] != 1:
            raise HTTPException(status_code=403, detail="tài khoản đã bị vô hiệu hóa")

        conn.execute(
            "UPDATE users SET failed_login_count=0, locked_at=NULL " "WHERE user_id=?",
            (row["user_id"],),
        )
        conn.commit()

        access_token = create_access_token(
            data={"sub": str(row["user_id"]), "role": row["role"]}
        )

        return {
            "status": "ok",
            "message": "Đăng nhập thành công",
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "user_id": row["user_id"],
                "username": row["username"],
                "full_name": row["full_name"],
                "role": row["role"],
            },
        }

    finally:
        conn.close()


@app.get("/api/subjects", dependencies=[Depends(get_current_user)])
def get_subjects():
    conn = get_db()

    try:
        rows = conn.execute("""
            SELECT
            subject_id,
            subject_name,
            is_active
            FROM subjects
            ORDER BY subject_id
            """).fetchall()

        return {"count": len(rows), "subjects": [dict(row) for row in rows]}

    finally:
        conn.close()


@app.get("/api/subjects/{subject_id}", dependencies=[Depends(get_current_user)])
def get_subject_detail(subject_id: int):
    conn = get_db()

    try:
        row = conn.execute(
            """
            SELECT 
            subject_id,
            subject_name,
            is_active
            FROM subjects
            WHERE subject_id = ?
            """,
            (subject_id,),
        ).fetchone()

        if row is None:
            raise HTTPException(status_code=404, detail="không tìm thấy môn học")

        return dict(row)

    finally:
        conn.close()


@app.post("/api/subjects", status_code=201, dependencies=[Depends(get_current_user)])
def create_subject(subject: SubjectCreate):
    subject_name = subject.subject_name.strip()

    if not subject_name:
        raise HTTPException(status_code=422, detail="tên môn học không được để trống")

    conn = get_db()

    try:
        cursor = conn.execute(
            """
            INSERT INTO subjects (subject_name)
            VALUES (?)
        """,
            (subject_name,),
        )

        conn.commit()

        return {
            "message": "tạo môn học thành công",
            "subject_id": cursor.lastrowid,
            "subject_name": subject_name,
        }

    except sqlite3.IntegrityError:
        conn.rollback()
        raise HTTPException(status_code=409, detail="tên môn học đã tồn tại")

    finally:
        conn.close()


@app.put("/api/subjects/{subject_id}", dependencies=[Depends(get_current_user)])
def update_subject(subject_id: int, subject: SubjectUpdate):
    subject_name = subject.subject_name.strip()

    if not subject_name:
        raise HTTPException(status_code=422, detail="tên môn học không được để trống")

    conn = get_db()
    try:
        existing = conn.execute(
            """
            SELECT subject_id
            FROM subjects
            WHERE subject_id = ?
        """,
            (subject_id,),
        ).fetchone()

        if existing is None:
            raise HTTPException(status_code=404, detail="không tìm thấy môn học")

        conn.execute(
            """
            UPDATE subjects
            SET subject_name = ?
            WHERE subject_id = ?
        """,
            (subject_name, subject_id),
        )

        conn.commit()

        return {
            "message": "cập nhật môn học thành công",
            "subject_id": subject_id,
            "subject_name": subject_name,
        }

    except sqlite3.IntegrityError:
        conn.rollback()
        raise HTTPException(status_code=409, detail="tên môn học đã tồn tại")

    finally:
        conn.close()


@app.delete("/api/subjects/{subject_id}", dependencies=[Depends(get_current_user)])
def delete_subject(subject_id: int):
    conn = get_db()
    try:
        subject = conn.execute(
            """
            SELECT subject_id, is_active
            FROM subjects
            WHERE subject_id = ?
        """,
            (subject_id,),
        ).fetchone()

        if subject is None:
            raise HTTPException(status_code=404, detail="không tìm thấy môn học")

        if subject["is_active"] == 0:
            raise HTTPException(status_code=400, detail="môn học đã ngừng hoạt động")

        conn.execute(
            """
            UPDATE subjects
            SET is_active = 0
            WHERE subject_id = ?
        """,
            (subject_id,),
        )

        conn.commit()

        return {
            "message": "ngừng hoạt động môn học thành công",
            "subject_id": subject_id,
        }

    finally:
        conn.close()


@app.get("/api/grades", dependencies=[Depends(get_current_user)])
def get_grades():
    conn = get_db()

    try:
        rows = conn.execute("""
            SELECT
            grade_id,
            grade_name,
            is_active
            FROM grades
            ORDER BY grade_id
            """).fetchall()

        return {"count": len(rows), "grades": [dict(row) for row in rows]}

    finally:
        conn.close()


@app.get("/api/grades/{grade_id}", dependencies=[Depends(get_current_user)])
def get_grade_detail(grade_id: int):
    conn = get_db()

    try:
        row = conn.execute(
            """
            SELECT
            grade_id,
            grade_name,
            is_active
            FROM grades
            WHERE grade_id = ?
            """,
            (grade_id,),
        ).fetchone()

        if row is None:
            raise HTTPException(status_code=404, detail="không tìm thấy khối lớp")

        return dict(row)

    finally:
        conn.close()


@app.post("/api/grades", status_code=201, dependencies=[Depends(get_current_user)])
def create_grade(grade: GradeCreate):
    grade_name = grade.grade_name.strip()

    if not grade_name:
        raise HTTPException(status_code=422, detail="tên khối lớp không được để trống")

    conn = get_db()

    try:
        cursor = conn.execute(
            """
            INSERT INTO grades (grade_name)
            VALUES (?)
        """,
            (grade_name,),
        )

        conn.commit()

        return {
            "message": "tạo khối lớp thành công",
            "grade_id": cursor.lastrowid,
            "grade_name": grade_name,
        }

    except sqlite3.IntegrityError:
        conn.rollback()
        raise HTTPException(status_code=409, detail="tên khối lớp đã tồn tại")

    finally:
        conn.close()


@app.put("/api/grades/{grade_id}", dependencies=[Depends(get_current_user)])
def update_grade(grade_id: int, grade: GradeUpdate):
    grade_name = grade.grade_name.strip()

    if not grade_name:
        raise HTTPException(status_code=422, detail="tên khối lớp không được để trống")

    conn = get_db()
    try:
        existing = conn.execute(
            """
            SELECT grade_id
            FROM grades
            WHERE grade_id = ?
        """,
            (grade_id,),
        ).fetchone()

        if existing is None:
            raise HTTPException(status_code=404, detail="không tìm thấy khối lớp")

        conn.execute(
            """
            UPDATE grades
            SET grade_name = ?
            WHERE grade_id = ?
        """,
            (grade_name, grade_id),
        )

        conn.commit()

        return {
            "message": "cập nhật khối lớp thành công",
            "grade_id": grade_id,
            "grade_name": grade_name,
        }

    except sqlite3.IntegrityError:
        conn.rollback()
        raise HTTPException(status_code=409, detail="tên khối lớp đã tồn tại")

    finally:
        conn.close()


@app.delete("/api/grades/{grade_id}", dependencies=[Depends(get_current_user)])
def delete_grade(grade_id: int):
    conn = get_db()
    try:
        grade = conn.execute(
            """
            SELECT grade_id, is_active
            FROM grades
            WHERE grade_id = ?
        """,
            (grade_id,),
        ).fetchone()

        if grade is None:
            raise HTTPException(status_code=404, detail="không tìm thấy khối lớp")

        if grade["is_active"] == 0:
            raise HTTPException(status_code=400, detail="khối lớp đã ngừng hoạt động")

        conn.execute(
            """
            UPDATE grades
            SET is_active = 0
            WHERE grade_id = ?
        """,
            (grade_id,),
        )

        conn.commit()

        return {
            "message": "ngừng hoạt động khối lớp thành công",
            "grade_id": grade_id,
            "is_active": 0,
        }

    finally:
        conn.close()


@app.get("/api/topics", dependencies=[Depends(get_current_user)])
def get_topics(subject_id: int | None = None, grade_id: int | None = None):
    conn = get_db()

    try:
        query = """
            SELECT 
            topic_id, 
            subject_id, 
            grade_id,
            topic_name, 
            is_active
            FROM topics
            WHERE 1 = 1
            """
        params = []

        if subject_id is not None:
            query += " AND subject_id = ?"
            params.append(subject_id)

        if grade_id is not None:
            query += " AND grade_id = ?"
            params.append(grade_id)

        query += " ORDER BY topic_id"

        rows = conn.execute(query, params).fetchall()

        return {"count": len(rows), "topics": [dict(row) for row in rows]}

    finally:
        conn.close()


@app.get("/api/topics/{topic_id}", dependencies=[Depends(get_current_user)])
def get_detail_topic(topic_id: int):
    conn = get_db()

    try:
        row = conn.execute(
            """
            SELECT
            topic_id,
            subject_id,
            grade_id,
            topic_name,
            is_active
            FROM topics
            WHERE topic_id = ?
            """,
            (topic_id,),
        ).fetchone()

        if row is None:
            raise HTTPException(status_code=404, detail="không tìm thấy chủ đề")

        return dict(row)

    finally:
        conn.close()


@app.post("/api/topics", status_code=201, dependencies=[Depends(get_current_user)])
def create_topic(topic: TopicCreate):
    topic_name = topic.topic_name.strip()

    if not topic_name:
        raise HTTPException(status_code=422, detail="tên chủ đề không được để trống")

    conn = get_db()
    try:
        subject = conn.execute(
            """
            SELECT subject_id
            FROM subjects
            WHERE subject_id = ? AND is_active = 1
        """,
            (topic.subject_id,),
        ).fetchone()

        if subject is None:
            raise HTTPException(
                status_code=400, detail="Môn học không tồn tại hoặc đã ngừng hoạt động"
            )

        grade = conn.execute(
            """
            SELECT grade_id
            FROM grades
            WHERE grade_id = ? AND is_active = 1
        """,
            (topic.grade_id,),
        ).fetchone()

        if grade is None:
            raise HTTPException(
                status_code=400, detail="khối lớp không tồn tại hoặc đã ngừng hoạt động"
            )

        cursor = conn.execute(
            """
            INSERT INTO topics (subject_id, grade_id, topic_name)
            VALUES (?, ?, ?)
        """,
            (topic.subject_id, topic.grade_id, topic_name),
        )

        conn.commit()

        return {
            "message": "tạo chủ đề thành công",
            "topic_id": cursor.lastrowid,
            "subject_id": topic.subject_id,
            "grade_id": topic.grade_id,
            "topic_name": topic_name,
        }

    except sqlite3.IntegrityError:
        conn.rollback()
        raise HTTPException(
            status_code=409,
            detail="chủ đề này đã tồn tại trong môn học và khối lớp đã chọn",
        )

    finally:
        conn.close()


@app.put("/api/topics/{topic_id}", dependencies=[Depends(get_current_user)])
def update_topic(topic_id: int, topic: TopicUpdate):
    topic_name = topic.topic_name.strip()

    if not topic_name:
        raise HTTPException(status_code=422, detail="tên chủ đề không được để trống")

    conn = get_db()
    try:
        existing = conn.execute(
            """
            SELECT topic_id
            FROM topics
            WHERE topic_id = ?
        """,
            (topic_id,),
        ).fetchone()

        if existing is None:
            raise HTTPException(status_code=404, detail="không tìm thấy chủ đề")

        subject = conn.execute(
            """
            SELECT subject_id
            FROM subjects
            WHERE subject_id = ? AND is_active = 1
        """,
            (topic.subject_id,),
        ).fetchone()

        if subject is None:
            raise HTTPException(
                status_code=400, detail="môn học không tồn tại hoặc đã ngừng hoạt động"
            )

        grade = conn.execute(
            """
            SELECT grade_id
            FROM grades
            WHERE grade_id = ? AND is_active = 1
        """,
            (topic.grade_id,),
        ).fetchone()

        if grade is None:
            raise HTTPException(
                status_code=400, detail="khối lớp không tồn tại hoặc đã ngừng hoạt động"
            )

        conn.execute(
            """
            UPDATE topics
            SET subject_id = ?,
                grade_id = ?,
                topic_name = ?
            WHERE topic_id = ?
        """,
            (topic.subject_id, topic.grade_id, topic_name, topic_id),
        )

        conn.commit()

        return {
            "message": "cập nhật chủ đề thành công",
            "topic_id": topic_id,
            "subject_id": topic.subject_id,
            "grade_id": topic.grade_id,
            "topic_name": topic_name,
        }

    except sqlite3.IntegrityError:
        conn.rollback()
        raise HTTPException(
            status_code=409, detail="chủ đề đã tồn tại trong môn học và khối lớp này"
        )

    finally:
        conn.close()


@app.delete("/api/topics/{topic_id}", dependencies=[Depends(get_current_user)])
def delete_topic(topic_id: int):
    conn = get_db()
    try:
        topic = conn.execute(
            """
            SELECT topic_id, is_active
            FROM topics
            WHERE topic_id = ?
        """,
            (topic_id,),
        ).fetchone()

        if topic is None:
            raise HTTPException(status_code=404, detail="không tìm thấy chủ đề")

        if topic["is_active"] == 0:
            raise HTTPException(status_code=400, detail="chủ đề đã ngừng hoạt động")

        conn.execute(
            """
            UPDATE topics
            SET is_active = 0
            WHERE topic_id = ?
        """,
            (topic_id,),
        )

        conn.commit()

        return {
            "message": "ngừng hoạt động chủ đề thành công",
            "topic_id": topic_id,
            "is_active": 0,
        }

    finally:
        conn.close()


@app.get("/api/lessons", dependencies=[Depends(get_current_user)])
def get_lessons(topic_id: int | None = None):
    conn = get_db()

    try:
        query = """
            SELECT 
            lesson_id, 
            topic_id, 
            lesson_name,
            lesson_order, 
            is_active
            FROM lessons
        """
        params = []

        if topic_id is not None:
            query += " WHERE topic_id = ?"
            params.append(topic_id)

        query += " ORDER BY lesson_id"

        rows = conn.execute(query, params).fetchall()

        return {"count": len(rows), "lessons": [dict(row) for row in rows]}

    finally:
        conn.close()


@app.get("/api/lessons/{lesson_id}", dependencies=[Depends(get_current_user)])
def get_lesson_detail(lesson_id: int):
    conn = get_db()

    try:
        row = conn.execute(
            """
            SELECT
            lesson_id,
            topic_id,
            lesson_name,
            lesson_order,
            is_active
            FROM lessons
            WHERE lesson_id = ?
            """,
            (lesson_id,),
        ).fetchone()

        if row is None:
            raise HTTPException(status_code=404, detail="không tìm thấy bài học")

        return dict(row)

    finally:
        conn.close()


@app.post("/api/lessons", status_code=201, dependencies=[Depends(get_current_user)])
def create_lesson(lesson: LessonCreate):
    lesson_name = lesson.lesson_name.strip()

    if not lesson_name:
        raise HTTPException(status_code=422, detail="tên bài học không được để trống")

    conn = get_db()
    try:
        topic = conn.execute(
            """
            SELECT topic_id
            FROM topics
            WHERE topic_id = ? AND is_active = 1
        """,
            (lesson.topic_id,),
        ).fetchone()

        if topic is None:
            raise HTTPException(
                status_code=400, detail="chủ đề không tồn tại hoặc đã ngừng hoạt động"
            )

        cursor = conn.execute(
            """
            INSERT INTO lessons (
                topic_id,
                lesson_name,
                lesson_order
            )
            VALUES (?, ?, ?)
        """,
            (lesson.topic_id, lesson_name, lesson.lesson_order),
        )

        conn.commit()

        return {
            "message": "tạo bài học thành công",
            "lesson_id": cursor.lastrowid,
            "topic_id": lesson.topic_id,
            "lesson_name": lesson_name,
            "lesson_order": lesson.lesson_order,
        }

    except sqlite3.IntegrityError as e:
        conn.rollback()

        if "UNIQUE constraint failed" in str(e):
            raise HTTPException(
                status_code=409,
                detail="tên bài học hoặc thứ tự bài học đã tồn tại trong chủ đề này",
            )

        raise HTTPException(
            status_code=409, detail="không thể tạo bài học do dữ liệu vi phạm ràng buộc"
        )

    finally:
        conn.close()


@app.put("/api/lessons/{lesson_id}", dependencies=[Depends(get_current_user)])
def update_lesson(lesson_id: int, lesson: LessonUpdate):
    lesson_name = lesson.lesson_name.strip()

    if not lesson_name:
        raise HTTPException(status_code=422, detail="Tên bài học không được để trống")

    conn = get_db()
    try:
        existing = conn.execute(
            """
            SELECT lesson_id
            FROM lessons
            WHERE lesson_id = ?
        """,
            (lesson_id,),
        ).fetchone()

        if existing is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy bài học")

        topic = conn.execute(
            """
            SELECT topic_id
            FROM topics
            WHERE topic_id = ? AND is_active = 1
        """,
            (lesson.topic_id,),
        ).fetchone()

        if topic is None:
            raise HTTPException(
                status_code=400, detail="Chủ đề không tồn tại hoặc đã ngừng hoạt động"
            )

        conn.execute(
            """
            UPDATE lessons
            SET topic_id = ?,
                lesson_name = ?,
                lesson_order = ?
            WHERE lesson_id = ?
        """,
            (lesson.topic_id, lesson_name, lesson.lesson_order, lesson_id),
        )

        conn.commit()

        return {
            "message": "Cập nhật bài học thành công",
            "lesson_id": lesson_id,
            "topic_id": lesson.topic_id,
            "lesson_name": lesson_name,
            "lesson_order": lesson.lesson_order,
        }

    except sqlite3.IntegrityError:
        conn.rollback()
        raise HTTPException(
            status_code=409,
            detail="Tên bài học hoặc thứ tự bài học đã tồn tại trong chủ đề này",
        )

    finally:
        conn.close()


@app.delete("/api/lessons/{lesson_id}", dependencies=[Depends(get_current_user)])
def delete_lesson(lesson_id: int):
    conn = get_db()
    try:
        lesson = conn.execute(
            """
            SELECT lesson_id, is_active
            FROM lessons
            WHERE lesson_id = ?
        """,
            (lesson_id,),
        ).fetchone()

        if lesson is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy bài học")

        if lesson["is_active"] == 0:
            raise HTTPException(status_code=400, detail="Bài học đã ngừng hoạt động")

        conn.execute(
            """
            UPDATE lessons
            SET is_active = 0
            WHERE lesson_id = ?
        """,
            (lesson_id,),
        )

        conn.commit()

        return {
            "message": "Ngừng hoạt động bài học thành công",
            "lesson_id": lesson_id,
            "is_active": 0,
        }

    finally:
        conn.close()


@app.get("/api/classes")
def get_classes(grade_id: int | None = None, user=Depends(get_current_user)):
    conn = get_db()

    try:
        query = """
            SELECT 
            class_id, 
            class_name, 
            grade_id,
            school_year, 
            is_active
            FROM classes
        """
        clauses, params = [], []
        if user["role"] != "admin":
            clauses.append("created_by = ?")
            params.append(user["user_id"])

        if grade_id is not None:
            clauses.append("grade_id = ?")
            params.append(grade_id)

        if clauses:
            query += " WHERE " + " AND ".join(clauses)

        query += " ORDER BY class_id"

        rows = conn.execute(query, params).fetchall()

        return {"count": len(rows), "classes": [dict(row) for row in rows]}

    finally:
        conn.close()


@app.get("/api/classes/{class_id}")
def get_class_detail(class_id: int, user=Depends(get_current_user)):
    conn = get_db()

    try:
        row = conn.execute(
            """
            SELECT 
            class_id,
            class_name,
            grade_id,
            school_year,
            is_active
            FROM classes
            WHERE class_id = ? AND (? = 'admin' OR created_by = ?)
            """,
            (class_id, user["role"], user["user_id"]),
        ).fetchone()

        if row is None:
            raise HTTPException(status_code=404, detail="không tìm thấy lớp học")

        return dict(row)

    finally:
        conn.close()


@app.put("/api/classes/{class_id}")
def update_class(class_id: int, class_data: ClassUpdate, user=Depends(get_current_user)):
    class_name = class_data.class_name.strip()
    school_year = (
        class_data.school_year.strip()
        if class_data.school_year and class_data.school_year.strip()
        else None
    )

    if not class_name:
        raise HTTPException(status_code=422, detail="Tên lớp không được để trống")

    conn = get_db()
    try:
        existing = conn.execute(
            """
            SELECT class_id, created_by
            FROM classes
            WHERE class_id = ? AND (? = 'admin' OR created_by = ?)
        """,
            (class_id, user["role"], user["user_id"]),
        ).fetchone()

        if existing is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy lớp học")

        grade = conn.execute(
            """
            SELECT grade_id
            FROM grades
            WHERE grade_id = ? AND is_active = 1
        """,
            (class_data.grade_id,),
        ).fetchone()

        if grade is None:
            raise HTTPException(
                status_code=400, detail="Khối lớp không tồn tại hoặc đã ngừng hoạt động"
            )

        conn.execute(
            """
            UPDATE classes
            SET class_name = ?,
                grade_id = ?,
                school_year = ?
            WHERE class_id = ?
        """,
            (class_name, class_data.grade_id, school_year, class_id),
        )

        conn.commit()

        return {
            "message": "Cập nhật lớp học thành công",
            "class_id": class_id,
            "class_name": class_name,
            "grade_id": class_data.grade_id,
            "school_year": school_year,
        }

    except sqlite3.IntegrityError:
        conn.rollback()
        raise HTTPException(
            status_code=409, detail="Lớp học với tên và năm học này đã tồn tại"
        )

    finally:
        conn.close()


@app.get("/api/students")
def get_students(user=Depends(get_current_user)):
    conn = get_db()

    try:
        rows = conn.execute("""
            SELECT 
            s.student_id, 
            s.student_code, 
            s.full_name,
            s.date_of_birth,
            s.class_id, 
            s.is_active
            FROM students s JOIN classes c ON c.class_id = s.class_id
            WHERE (? = 'admin' OR c.created_by = ?)
            ORDER BY s.student_id
            """, (user["role"], user["user_id"])).fetchall()

        return {"count": len(rows), "students": [dict(row) for row in rows]}

    finally:
        conn.close()


@app.get("/api/students/{student_id}")
def get_student_detail(student_id: int, user=Depends(get_current_user)):
    conn = get_db()

    try:
        row = conn.execute(
            """
            SELECT 
            s.student_id, 
            s.student_code, 
            s.full_name,
            s.date_of_birth,
            s.class_id, 
            s.is_active
            FROM students s JOIN classes c ON c.class_id = s.class_id
            WHERE s.student_id = ? AND (? = 'admin' OR c.created_by = ?)
            """,
            (student_id, user["role"], user["user_id"]),
        ).fetchone()

        if row is None:
            raise HTTPException(status_code=404, detail="không tìm thấy học sinh")

        return dict(row)

    finally:
        conn.close()


from exam_routes import router
from question_bank import router as question_router

app.include_router(router)
app.include_router(question_router)
app.mount("/ui", StaticFiles(directory=FRONTEND_DIR, html=True), name="legacy_ui")
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="ui")
