import sqlite3
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATABASE_DIR = PROJECT_DIR / "database"
DATABASE_PATH = DATABASE_DIR / "data.db"
SCHEMA_PATH = DATABASE_DIR / "schema.sql"
TEMP_DATABASE_PATH = DATABASE_DIR / "data.db.initializing"

if DATABASE_PATH.exists():
    print("Database da ton tai; giu nguyen du lieu hien co.")
    raise SystemExit(0)
if not SCHEMA_PATH.is_file():
    raise SystemExit("Khong tim thay database/schema.sql.")

DATABASE_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DATABASE_PATH.unlink(missing_ok=True)
try:
    connection = sqlite3.connect(TEMP_DATABASE_PATH)
    try:
        connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    finally:
        connection.close()
    TEMP_DATABASE_PATH.replace(DATABASE_PATH)
except Exception:
    TEMP_DATABASE_PATH.unlink(missing_ok=True)
    raise

print("Da tao database va schema SQLite.")
